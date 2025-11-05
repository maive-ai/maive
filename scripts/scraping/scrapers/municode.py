import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def clean_municode_html(html_content):
    """
    Aggressively clean Municode HTML to keep only essential content.

    Args:
        html_content: HTML string to clean

    Returns:
        Minimal HTML with only content and essential structure
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style tags
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Remove stylesheet links
    for link in soup.find_all("link", rel="stylesheet"):
        link.decompose()

    # Remove action bar elements and other UI components
    for element in soup.find_all(
        class_=[
            "mcc_codes_content_action_bar",
            "btn-group",
            "action-dropdown",
            "action-bar",
            "anchor-offset",
        ]
    ):
        element.decompose()

    # Remove empty spans and divs
    for tag in soup.find_all(["span", "div"]):
        if not tag.get_text(strip=True) and not tag.find_all(True):
            tag.decompose()

    # Remove Angular-specific custom tags (but keep their content)
    for tag in soup.find_all(
        lambda t: t.name and (t.name.startswith("mcc-") or t.name.startswith("ng-"))
    ):
        tag.unwrap()

    # Aggressively clean attributes - keep ONLY id and essential data
    for tag in soup.find_all(True):
        # Keep only id attribute and data-nodedepth/data-nodetype for structure
        new_attrs = {}
        if "id" in tag.attrs:
            new_attrs["id"] = tag.attrs["id"]
        if "data-nodedepth" in tag.attrs:
            new_attrs["data-nodedepth"] = tag.attrs["data-nodedepth"]
        if "href" in tag.attrs:
            new_attrs["href"] = tag.attrs["href"]
        if "target" in tag.attrs:
            new_attrs["target"] = tag.attrs["target"]
        # Keep semantic classes like 'b0' that indicate formatting
        if "class" in tag.attrs and tag.name in ["p", "div", "span"]:
            classes = (
                tag.attrs["class"]
                if isinstance(tag.attrs["class"], list)
                else [tag.attrs["class"]]
            )
            # Keep single-letter classes like 'b0' or structural classes
            semantic_classes = [
                c for c in classes if len(c) <= 2 or c.startswith("chunk-")
            ]
            if semantic_classes:
                new_attrs["class"] = semantic_classes
        tag.attrs = new_attrs

    # Find the main content wrapper and extract just the content
    content_wrapper = soup.find("div", class_="chunk-content-wrapper")
    if content_wrapper:
        content_div = content_wrapper.find("div", class_="chunk-content")
        if content_div:
            # Get the title from the chunk-title div
            title_div = soup.find("div", class_="chunk-title")
            title_html = (
                f"<h3>{title_div.get_text(strip=True)}</h3>" if title_div else ""
            )

            # Get the outer chunk div's attributes
            chunk_div = soup.find("div", class_="chunk")
            chunk_attrs = ""
            if chunk_div:
                if chunk_div.get("id"):
                    chunk_attrs = f' id="{chunk_div["id"]}"'
                if chunk_div.get("data-nodedepth"):
                    chunk_attrs += f' data-nodedepth="{chunk_div["data-nodedepth"]}"'

            # Reconstruct minimal HTML
            content_html = (
                str(content_div.decode_contents())
                if content_div.decode_contents()
                else ""
            )
            cleaned_html = f"<div{chunk_attrs}>{title_html}{content_html}</div>"
            return cleaned_html

    # Fallback: convert back to string if structure is different
    cleaned_html = str(soup)

    # Remove HTML comments (including Angular's empty comments)
    cleaned_html = re.sub(r"<!--.*?-->", "", cleaned_html, flags=re.DOTALL)
    # Remove any leftover Angular comment markers
    cleaned_html = cleaned_html.replace("<!---->", "")

    # Remove excessive whitespace
    cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html)

    return cleaned_html.strip()


def extract_toc_structure(page):
    """Extract the hierarchical TOC structure from the Angular-based page."""
    return page.evaluate("""
        () => {
            function extractNodeData(liElement) {
                // Get the anchor link
                const link = liElement.querySelector('a.toc-item-heading');
                if (!link) return null;

                const text = link.querySelector('span')?.innerText.trim() || '';
                const url = link.href;

                // Extract nodeId from URL
                const nodeIdMatch = url.match(/nodeId=([^&]+)/);
                const nodeId = nodeIdMatch ? nodeIdMatch[1] : null;

                // Check if it has children (has expand button)
                const hasChildren = !!liElement.querySelector('button.toc-item-expand');

                // Get children if expanded
                const children = [];
                const childList = liElement.querySelector('ul.gen-toc-nav');
                if (childList) {
                    const childItems = childList.querySelectorAll(':scope > li');
                    childItems.forEach(child => {
                        const childData = extractNodeData(child);
                        if (childData) {
                            children.push(childData);
                        }
                    });
                }

                return {
                    text: text,
                    nodeId: nodeId,
                    url: url,
                    hasChildren: hasChildren,
                    children: children
                };
            }

            // Find the main TOC list
            const tocList = document.querySelector('#genTocList');
            if (!tocList) {
                return { error: 'TOC list not found' };
            }

            // Get all top-level items
            const topLevelItems = tocList.querySelectorAll(':scope > li');
            const tocItems = [];

            topLevelItems.forEach(item => {
                const itemData = extractNodeData(item);
                if (itemData) {
                    tocItems.push(itemData);
                }
            });

            return {
                items: tocItems,
                totalItems: document.querySelectorAll('#genTocList li').length
            };
        }
    """)


def flatten_toc(
    nodes: List[Dict[str, Any]], parent_path: List[str] = None
) -> List[Dict[str, Any]]:
    """Flatten the nested TOC structure into a list with paths."""
    if parent_path is None:
        parent_path = []

    flat_list = []

    for node in nodes:
        current_path = parent_path + [node["text"]]

        flat_item = {
            "value": node["text"],
            "path": current_path,
            "url": node.get("url"),
            "depth": len(current_path) - 1,
            "has_children": node.get("hasChildren", False),
        }

        # Keep nodeId internally for scraping, but it won't be in final output
        flat_item["_nodeId"] = node.get("nodeId")

        flat_list.append(flat_item)

        # Recursively process children
        if node.get("children"):
            flat_list.extend(flatten_toc(node["children"], current_path))

    return flat_list


def expand_all_nodes(page):
    """Expand all nodes in the Angular TOC tree."""
    expanded_count = 0
    max_concurrent = 10

    round_num = 0
    while True:
        round_num += 1

        # Find all expandable nodes (buttons with chevron-right icons)
        expand_buttons = page.query_selector_all(
            "button.toc-item-expand i.fa-chevron-right"
        )

        if not expand_buttons:
            print(f"No more nodes to expand after {round_num} rounds")
            break

        print(f"Round {round_num}: Found {len(expand_buttons)} nodes to expand")

        # Get the parent buttons (the actual clickable elements)
        clickable_buttons = []
        for icon in expand_buttons:
            button = icon.evaluate_handle('el => el.closest("button")')
            if button:
                clickable_buttons.append(button)

        # Click all nodes in batches
        for i in range(0, len(clickable_buttons), max_concurrent):
            batch = clickable_buttons[i : i + max_concurrent]

            # Click all in this batch
            for button in batch:
                try:
                    if button.is_visible():
                        button.click()
                        expanded_count += 1
                except:
                    pass

            # Wait a bit for them to load
            page.wait_for_timeout(500)

    print(f"Expansion complete: {expanded_count} nodes expanded")


def scrape_single_municipality(url: str, output_name: str, output_dir_path: str = "output"):
    """
    Scrape HTML content from a single municipality's code.

    Args:
        url: Full URL to the municipality code
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

        try:
            print(f"Navigating to {url}")
            page.goto(url, wait_until="domcontentloaded")

            # Wait for TOC to load
            print("Waiting for Angular TOC to load...")
            page.wait_for_selector("#genTocList", timeout=60000)
            page.wait_for_selector("a.toc-item-heading", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=10000)

            # Expand all nodes
            print("Expanding TOC nodes...")
            expand_all_nodes(page)

            # Extract the TOC structure
            print("Extracting TOC structure...")
            toc_data = extract_toc_structure(page)

            if "error" in toc_data:
                print(f"Error: {toc_data['error']}")
                return

            hierarchical_toc = toc_data["items"]
            print(f"Found {toc_data['totalItems']} total items in TOC")

            # Flatten the TOC
            flat_toc = flatten_toc(hierarchical_toc)

            # Filter to only leaf nodes for HTML scraping
            leaf_nodes = [
                item for item in flat_toc if not item.get("has_children", False)
            ]
            print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

            # Before clicking TOC links, we need to ensure chunks are loaded
            # Click the first leaf node to load the chunks area
            if leaf_nodes and leaf_nodes[0].get("_nodeId"):
                first_link_selector = f'#genTocList a.toc-item-heading[href*="nodeId={leaf_nodes[0]["_nodeId"]}"]'
                try:
                    page.click(first_link_selector)
                    # Wait for chunks container to appear
                    page.wait_for_selector("ul.chunks", timeout=60000)
                    print("Chunks area loaded successfully")
                except Exception as e:
                    print(f"Warning: Could not load chunks area: {e}")

            # Now scrape HTML for each leaf node by clicking TOC links
            for i, item in enumerate(leaf_nodes):
                try:
                    if item.get("_nodeId"):
                        # Click the TOC link for this item
                        # Find the link with the specific nodeId in the URL
                        link_selector = f'#genTocList a.toc-item-heading[href*="nodeId={item["_nodeId"]}"]'

                        try:
                            # Click the TOC link
                            page.click(link_selector)

                            # Wait for the specific chunk to appear
                            chunk_selector = f"#c_{item['_nodeId']}"
                            page.wait_for_selector(chunk_selector, timeout=60000)

                            # Wait for any loading to complete
                            page.wait_for_function(
                                '() => document.querySelectorAll(".loading, .spinner").length === 0',
                                timeout=60000,
                            )

                            # Small delay to ensure content is fully rendered
                            time.sleep(0.5)

                            # Get the chunk HTML directly
                            chunk_html = page.locator(chunk_selector).evaluate(
                                "el => el.outerHTML"
                            )

                            # Clean the HTML content
                            cleaned_html = clean_municode_html(chunk_html)

                            # Unescape any escaped quotes to ensure valid HTML
                            cleaned_html = cleaned_html.replace('\\"', '"')

                            item["html"] = cleaned_html

                        except Exception as e:
                            print(
                                f"  ⚠ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - Failed to load chunk: {str(e)}"
                            )
                            item["html_error"] = f"Failed to load chunk: {str(e)}"
                    else:
                        item["html_error"] = "No nodeId for this item"
                        print(
                            f"  ⚠ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - no nodeId"
                        )

                except Exception as e:
                    print(
                        f"  ✗ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - {str(e)}"
                    )
                    item["html_error"] = str(e)

                # Small delay between clicks
                time.sleep(0.3)

        except Exception as e:
            print(f"Error: {e}")
            return

        finally:
            browser.close()

        # Clean up internal fields before saving
        for item in flat_toc:
            item.pop("_nodeId", None)

        print("\n✓ Scraping complete!")

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
                "scraper": "municode.py",
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
    print(f"  Successfully scraped: {items_with_html}/{total_leaf_nodes}")
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
            print(f"    - {item['value']}")
        if len(missing_html) > 5:
            print(f"    ... and {len(missing_html) - 5} more")


def scrape_from_csv(csv_path: str, output_dir_path: str = "output"):
    """
    Scrape multiple municipalities from a CSV file.

    CSV format expected:
        name,slug,base_url,code_url,status

    Args:
        csv_path: Path to CSV file containing municipality list
        output_dir_path: Directory to save outputs (default: "output")
    """
    import csv
    from pathlib import Path

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return

    # Read all municipalities from CSV
    municipalities = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'ready' and row.get('code_url'):
                municipalities.append(row)

    if not municipalities:
        print(f"Error: No ready municipalities found in {csv_path}")
        return

    print(f"\n{'='*60}")
    print(f"BATCH SCRAPING MODE")
    print(f"{'='*60}")
    print(f"CSV file: {csv_path}")
    print(f"Found {len(municipalities)} municipalities to scrape")
    print(f"Output directory: {output_dir_path}")
    print(f"{'='*60}\n")

    # Scrape each municipality
    for i, muni in enumerate(municipalities, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(municipalities)}] Scraping: {muni['name']}")
        print(f"{'='*60}")

        try:
            scrape_single_municipality(
                url=muni['code_url'],
                output_name=muni['slug'],
                output_dir_path=output_dir_path
            )
            print(f"✓ Completed: {muni['name']}")
        except Exception as e:
            print(f"✗ Failed: {muni['name']}")
            print(f"  Error: {str(e)}")
            # Continue with next municipality

    print(f"\n{'='*60}")
    print(f"BATCH SCRAPING COMPLETE")
    print(f"Processed {len(municipalities)} municipalities")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys

    # Check for CSV mode
    if len(sys.argv) >= 2 and sys.argv[1] == "--csv":
        if len(sys.argv) < 3:
            print("Usage: python municode.py --csv <CSV_FILE> [--output-dir DIR]")
            print("Example: python municode.py --csv ut_final_library.csv --output-dir output")
            sys.exit(1)

        csv_path = sys.argv[2]

        # Parse optional output directory
        output_dir_path = "output"
        if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
            if len(sys.argv) > 4:
                output_dir_path = sys.argv[4]

        scrape_from_csv(csv_path, output_dir_path)

    # Single municipality mode
    elif len(sys.argv) >= 3:
        url = sys.argv[1]
        output_name = sys.argv[2]

        # Parse optional output directory
        output_dir_path = "output"
        if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
            if len(sys.argv) > 4:
                output_dir_path = sys.argv[4]

        scrape_single_municipality(url, output_name, output_dir_path)

    # Show usage
    else:
        print("Usage:")
        print("  Single mode:  python municode.py <URL> <NAME> [--output-dir DIR]")
        print("  Batch mode:   python municode.py --csv <CSV_FILE> [--output-dir DIR]")
        print()
        print("Examples:")
        print("  python municode.py https://library.municode.com/ut/coalville/codes/development_code coalville")
        print("  python municode.py --csv ut_final_library.csv --output-dir output")
        sys.exit(1)
