import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def clean_html_content(html_content):
    """
    Clean HTML content to remove unnecessary elements and attributes.

    Args:
        html_content: HTML string to clean

    Returns:
        Cleaned HTML string
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style tags
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Remove stylesheet links
    for link in soup.find_all("link", rel="stylesheet"):
        link.decompose()

    # Remove empty paragraphs and divs
    for tag in soup.find_all(["p", "div", "span"]):
        if not tag.get_text(strip=True) and not tag.find_all(True):
            tag.decompose()

    # Clean attributes - keep only essential ones
    for tag in soup.find_all(True):
        new_attrs = {}
        if "id" in tag.attrs:
            new_attrs["id"] = tag.attrs["id"]
        if "href" in tag.attrs:
            new_attrs["href"] = tag.attrs["href"]
        if "target" in tag.attrs:
            new_attrs["target"] = tag.attrs["target"]
        # Keep semantic mco- classes that indicate content type
        if "class" in tag.attrs:
            classes = (
                tag.attrs["class"]
                if isinstance(tag.attrs["class"], list)
                else [tag.attrs["class"]]
            )
            mco_classes = [c for c in classes if c.startswith("mco-")]
            if mco_classes:
                new_attrs["class"] = mco_classes
        tag.attrs = new_attrs

    # Convert back to string
    cleaned_html = str(soup)

    # Remove HTML comments
    cleaned_html = re.sub(r"<!--.*?-->", "", cleaned_html, flags=re.DOTALL)

    # Remove excessive whitespace
    cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html)

    return cleaned_html.strip()


def extract_toc_structure(page):
    """Extract the hierarchical TOC structure from the page."""
    return page.evaluate("""
        () => {
            function extractNodeData(tocItemElement) {
                // Get the link element
                const linkElement = tocItemElement.querySelector('a');
                if (!linkElement) return null;

                const text = linkElement.textContent.trim();
                const href = linkElement.getAttribute('href');
                
                // Build full URL
                const baseUrl = window.location.origin;
                const url = href ? baseUrl + href : null;

                // Check for children by looking for the corresponding div
                const children = [];
                const id = linkElement.getAttribute('id');
                
                if (id) {
                    const childDiv = document.getElementById('div' + id);
                    if (childDiv) {
                        const childTocItems = childDiv.querySelectorAll(':scope > p.tocItem');
                        childTocItems.forEach(child => {
                            const childData = extractNodeData(child);
                            if (childData) children.push(childData);
                        });
                    }
                }

                return { text, url, children };
            }

            const archiveTOC = document.getElementById('archiveTOC');
            if (!archiveTOC) {
                return { items: [], totalItems: 0 };
            }

            const tocItems = [];
            const topLevelItems = archiveTOC.querySelectorAll(':scope > p.tocItem');

            topLevelItems.forEach(item => {
                const itemData = extractNodeData(item);
                if (itemData) tocItems.push(itemData);
            });

            return {
                items: tocItems,
                totalItems: archiveTOC.querySelectorAll('p.tocItem').length
            };
        }
    """)


def flatten_toc(
    nodes: List[Dict[str, Any]], parent_path: List[str] = None
) -> List[Dict[str, Any]]:
    """Flatten the nested TOC structure into a list with paths."""
    parent_path = parent_path or []
    flat_list = []

    for node in nodes:
        current_path = parent_path + [node["text"]]
        has_children = bool(node.get("children"))

        flat_list.append(
            {
                "value": node["text"],  # The text/title is the value
                "path": current_path,
                "url": node.get("url"),
                "depth": len(current_path) - 1,
                "has_children": has_children,
            }
        )

        if has_children:
            flat_list.extend(flatten_toc(node["children"], current_path))

    return flat_list


def expand_all_nodes(page):
    """Expand all nodes in the TOC tree by clicking on them."""
    round_num = 0
    total_expanded = 0

    while True:
        round_num += 1

        # Find all expandable spans (with + indicator)
        expandable_spans = page.query_selector_all("#archiveTOC .tocItemSpan.ajx")

        # Filter to only those with + (collapsed state)
        collapsed_spans = [
            span for span in expandable_spans if span.text_content().strip() == "+"
        ]

        if not collapsed_spans:
            print(f"No more nodes to expand after {round_num} rounds")
            break

        print(f"Round {round_num}: Found {len(collapsed_spans)} collapsed nodes")

        # Click each collapsed node
        for span in collapsed_spans:
            try:
                span.click()
                total_expanded += 1
                page.wait_for_timeout(50)
            except Exception as e:
                print(f"  Error clicking span: {e}")

        # Wait a bit for all expansions to complete
        page.wait_for_timeout(500)

    print(f"Expansion complete: {total_expanded} nodes expanded")
    return total_expanded



def scrape_from_csv(csv_path: str, output_dir_path: str = "output"):
    """
    Scrape multiple jurisdictions from a CSV file.

    CSV format expected:
        name,slug,base_url,code_url,status

    Args:
        csv_path: Path to CSV file containing jurisdiction list
        output_dir_path: Directory to save outputs (default: "output")
    """
    import csv
    from pathlib import Path

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return

    # Read all jurisdictions from CSV
    jurisdictions = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'ready' and row.get('code_url'):
                jurisdictions.append(row)

    if not jurisdictions:
        print(f"Error: No ready jurisdictions found in {csv_path}")
        return

    print(f"\n{'='*60}")
    print(f"BATCH SCRAPING MODE")
    print(f"{'='*60}")
    print(f"CSV file: {csv_path}")
    print(f"Found {len(jurisdictions)} jurisdictions to scrape")
    print(f"Output directory: {output_dir_path}")
    print(f"{'='*60}\n")

    # Scrape each jurisdiction
    for i, juris in enumerate(jurisdictions, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(jurisdictions)}] Scraping: {juris['name']}")
        print(f"{'='*60}")

        try:
            # Call the single scraping function directly
            scrape_single_jurisdiction(
                url=juris['code_url'],
                output_name=juris['slug'],
                output_dir_path=output_dir_path
            )
            print(f"✓ Completed: {juris['name']}")
        except Exception as e:
            print(f"✗ Failed: {juris['name']}")
            print(f"  Error: {str(e)}")
            # Continue with next jurisdiction

    print(f"\n{'='*60}")
    print(f"BATCH SCRAPING COMPLETE")
    print(f"Processed {len(jurisdictions)} jurisdictions")
    print(f"{'='*60}\n")


def scrape_single_jurisdiction(url: str, output_name: str, output_dir_path: str = "output"):
    """
    Scrape HTML content from a single jurisdiction's code.

    Args:
        url: Full URL to the jurisdiction code
        output_name: Name for the output file
        output_dir_path: Directory to save output (default: "output")
    """
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    hierarchical_toc = None
    flat_toc = None
    leaf_nodes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for production
        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to {url} to extract TOC...")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait for TOC to load (can take a while on some sites)
        print("Waiting for TOC to load (this may take up to 60 seconds)...")
        page.wait_for_selector("#archiveTOC", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=10000)

        # Expand all nodes
        print("Expanding TOC nodes...")
        expand_all_nodes(page)

        # Extract the TOC structure
        print("Extracting TOC structure...")
        toc_data = extract_toc_structure(page)

        if "error" in toc_data:
            print(f"Error: {toc_data['error']}")
            browser.close()
            return

        hierarchical_toc = toc_data["items"]
        print(f"Found {toc_data['totalItems']} total items in TOC")

        # Flatten the TOC
        flat_toc = flatten_toc(hierarchical_toc)

        # Filter to only leaf nodes
        leaf_nodes = [item for item in flat_toc if not item.get("has_children", False)]
        print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

        # Now scrape HTML for each leaf node
        for i, item in enumerate(leaf_nodes):
            if not item["url"]:
                print(f"  ✗ {i + 1}/{len(leaf_nodes)}: No URL - {item['value'][:80]}")
                continue

            # Extract section ID from URL fragment (handle URLs with hashbang like #!/...#section)
            # URL format: /UT/Syracuse/#!/Syracuse07/Syracuse0730.html#7.30.010
            url_parts = item["url"].split("#")
            section_id = None
            if len(url_parts) >= 3:
                # Has both hashbang and section anchor
                section_id = url_parts[-1]
            elif len(url_parts) == 2 and not url_parts[1].startswith("!"):
                # Has only section anchor (no hashbang)
                section_id = url_parts[1]

            try:
                # Navigate to the specific leaf node URL
                page.goto(item["url"], wait_until="networkidle", timeout=60000)
                page.wait_for_selector("#mainContent", timeout=60000)
                page.wait_for_timeout(300)

                # Try to find the specific section by ID
                if section_id:
                    # Extract content from this section to the next section header using getElementById
                    content_html = page.evaluate(f"""
                        () => {{
                            const sectionHeader = document.getElementById('{section_id}');
                            if (!sectionHeader) return null;

                            const container = document.createElement('div');
                            let currentElement = sectionHeader;

                            // Add the header itself
                            container.appendChild(currentElement.cloneNode(true));

                            // Collect siblings until we hit another h2 or h3 header
                            currentElement = currentElement.nextElementSibling;
                            while (currentElement) {{
                                const tagName = currentElement.tagName.toLowerCase();
                                if (tagName === 'h2' || tagName === 'h3') {{
                                    break;
                                }}
                                container.appendChild(currentElement.cloneNode(true));
                                currentElement = currentElement.nextElementSibling;
                            }}

                            return container.outerHTML;
                        }}
                    """)

                    if not content_html:
                        # Section not found on first try, reload and try again
                        print(
                            f"  ↻ {i + 1}/{len(leaf_nodes)}: Retrying - {item['value'][:80]}"
                        )
                        page.reload(wait_until="networkidle", timeout=60000)
                        page.wait_for_selector("#mainContent", timeout=60000)
                        page.wait_for_timeout(500)

                        content_html = page.evaluate(f"""
                            () => {{
                                const sectionHeader = document.getElementById('{section_id}');
                                if (!sectionHeader) return null;

                                const container = document.createElement('div');
                                let currentElement = sectionHeader;
                                container.appendChild(currentElement.cloneNode(true));

                                currentElement = currentElement.nextElementSibling;
                                while (currentElement) {{
                                    const tagName = currentElement.tagName.toLowerCase();
                                    if (tagName === 'h2' || tagName === 'h3') break;
                                    container.appendChild(currentElement.cloneNode(true));
                                    currentElement = currentElement.nextElementSibling;
                                }}

                                return container.outerHTML;
                            }}
                        """)

                    if content_html:
                        cleaned_html = clean_html_content(content_html)
                        item["html"] = cleaned_html
                        print(f"  ✓ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]}")
                    else:
                        # Section still not found after retry - mark as error
                        item["html_error"] = (
                            f"Section ID '{section_id}' not found on page"
                        )
                        print(
                            f"  ✗ {i + 1}/{len(leaf_nodes)}: Section not found - {item['value'][:80]}"
                        )
                else:
                    # No section ID - this shouldn't happen for leaf nodes, mark as error
                    item["html_error"] = "No section ID in URL"
                    print(
                        f"  ✗ {i + 1}/{len(leaf_nodes)}: No section ID - {item['value'][:80]}"
                    )

                # Add a small delay to be respectful to the server
                time.sleep(0.5)

            except Exception as e:
                print(f"  ✗ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - {str(e)}")

                # Add error information to the item
                item["html_error"] = str(e)

        browser.close()

    # Create output directory if it doesn't exist
    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename (no date prefix - overwrites existing)
    output_filename = f"{output_name}.json"
    output_path = output_dir / output_filename

    # Wrap content with metadata
    if flat_toc:
        scraped_at = datetime.now().isoformat()
        output_data = {
            "metadata": {
                "scraped_at": scraped_at,
                "city_slug": output_name,
                "source_url": url,
                "scraper": "general_code_publish.py",
                "scraper_version": "2.0"
            },
            "sections": flat_toc
        }

        # Save with metadata wrapper
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved flattened TOC with HTML to: {output_path}")

    # Report statistics
    items_with_html = sum(1 for item in flat_toc if "html" in item)
    items_with_errors = sum(1 for item in flat_toc if "html_error" in item)
    total_leaf_nodes = sum(
        1 for item in flat_toc if not item.get("has_children", False)
    )

    print("\n✓ Complete!")
    print(f"  Total TOC items: {len(flat_toc) if flat_toc else 0}")
    print(f"  Leaf nodes (with HTML): {total_leaf_nodes}")

    print(f"  Successfully scraped HTML: {items_with_html}/{total_leaf_nodes}")
    if items_with_errors > 0:
        print(f"  Errors: {items_with_errors}")

    # Report on any leaf nodes without HTML
    missing_html = [
        item
        for item in flat_toc
        if not item.get("has_children", False) and "html" not in item
    ]
    if missing_html:
        print(f"\n⚠ Warning: {len(missing_html)} leaf nodes have no HTML content:")
        for item in missing_html[:5]:  # Show first 5
            print(f"    - {item.get('value', 'Unknown')}")
        if len(missing_html) > 5:
            print(f"    ... and {len(missing_html) - 5} more")


if __name__ == "__main__":
    import sys

    # Check for CSV mode
    if len(sys.argv) >= 2 and sys.argv[1] == "--csv":
        if len(sys.argv) < 3:
            print("Usage: python general_code_publish.py --csv <CSV_FILE> [--output-dir DIR]")
            print("Example: python general_code_publish.py --csv ut_ecode360.csv --output-dir output")
            sys.exit(1)

        csv_path = sys.argv[2]

        # Parse optional output directory
        output_dir_path = "output"
        if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
            if len(sys.argv) > 4:
                output_dir_path = sys.argv[4]

        scrape_from_csv(csv_path, output_dir_path)

    # Single jurisdiction mode
    elif len(sys.argv) >= 3:
        url = sys.argv[1]
        output_name = sys.argv[2]

        # Parse optional output directory
        output_dir_path = "output"
        if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
            if len(sys.argv) > 4:
                output_dir_path = sys.argv[4]

        scrape_single_jurisdiction(url, output_name, output_dir_path)

    # Show usage
    else:
        print("Usage:")
        print("  Single mode:  python general_code_publish.py <URL> <NAME> [--output-dir DIR]")
        print("  Batch mode:   python general_code_publish.py --csv <CSV_FILE> [--output-dir DIR]")
        print()
        print("Examples:")
        print("  python general_code_publish.py https://ecode360.com/HU4729 huntington")
        print("  python general_code_publish.py --csv ut_ecode360.csv --output-dir output/codes/ut")
        sys.exit(1)
