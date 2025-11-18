import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from playwright.sync_api import Page, sync_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_utils import (
    clean_html_content,
    create_output_metadata,
    extract_url_path_segment,
    flatten_toc,
    parse_scraper_cli_args,
    print_scraping_statistics,
    run_batch_scraper,
    save_scraped_output,
    setup_browser_and_page,
)

# No need for local clean_html_content - using shared utility


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


# Using shared flatten_toc from scraper_utils


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

    Args:
        csv_path: Path to CSV file containing jurisdiction list
        output_dir_path: Directory to save outputs (default: "output")
    """
    run_batch_scraper(
        csv_path=csv_path,
        output_dir_path=output_dir_path,
        scraper_function=scrape_single_jurisdiction,
        scraper_name="general_code_publish.py",
    )


# URL parsing handled by extract_url_path_segment from scraper_utils


def _extract_section_content(page: Page, section_id: str) -> str | None:
    """
    Extract content for a specific section by ID.

    Args:
        page: Playwright page object
        section_id: Section ID to extract

    Returns:
        HTML content string or None if not found
    """
    return page.evaluate(
        f"""
        () => {{
            const sectionHeader = document.getElementById('{section_id}');
            if (!sectionHeader) return null;

            const container = document.createElement('div');
            let currentElement = sectionHeader;

            container.appendChild(currentElement.cloneNode(true));

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
    """
    )


def _scrape_section_content(
    page: Page, item: Dict[str, Any], index: int, total: int
) -> None:
    """
    Scrape content for a single section item.

    Args:
        page: Playwright page object
        item: TOC item dictionary
        index: Current index (0-based)
        total: Total number of items
    """
    if not item["url"]:
        print(f"  ✗ {index + 1}/{total}: No URL - {item['value'][:80]}")
        return

    # Extract anchor ID from hash-bang URLs (e.g., "#!/path/file.html#1.01" -> "1.01")
    # For hash-bang URLs, we need the part after the last # in the fragment
    from urllib.parse import urlparse
    parsed = urlparse(item["url"])

    if parsed.fragment and "#" in parsed.fragment:
        # Hash-bang URL: extract the anchor ID after the last #
        section_id = parsed.fragment.split("#")[-1]
    else:
        # Regular URL: use the fragment as-is
        section_id = extract_url_path_segment(item["url"])

    if not section_id:
        item["html_error"] = "No section ID in URL"
        print(f"  ✗ {index + 1}/{total}: No section ID - {item['value'][:80]}")
        return

    try:
        page.goto(item["url"], wait_until="networkidle", timeout=60000)
        page.wait_for_selector("#mainContent", timeout=60000)
        page.wait_for_timeout(300)

        content_html = _extract_section_content(page, section_id)

        if not content_html:
            print(f"  ↻ {index + 1}/{total}: Retrying - {item['value'][:80]}")
            page.reload(wait_until="networkidle", timeout=60000)
            page.wait_for_selector("#mainContent", timeout=60000)
            page.wait_for_timeout(500)

            content_html = _extract_section_content(page, section_id)

        if content_html:
            cleaned_html = clean_html_content(content_html, preserve_classes=["mco-"])
            item["html"] = cleaned_html
            print(f"  ✓ {index + 1}/{total}: {item['value'][:80]}")
        else:
            item["html_error"] = f"Section ID '{section_id}' not found on page"
            print(f"  ✗ {index + 1}/{total}: Section not found - {item['value'][:80]}")

        time.sleep(0.5)

    except Exception as e:
        print(f"  ✗ {index + 1}/{total}: {item['value'][:80]} - {str(e)}")
        item["html_error"] = str(e)


def _scrape_all_leaf_nodes(page: Page, leaf_nodes: List[Dict[str, Any]]) -> None:
    """
    Scrape HTML content for all leaf nodes.

    Args:
        page: Playwright page object
        leaf_nodes: List of leaf node dictionaries
    """
    for i, item in enumerate(leaf_nodes):
        _scrape_section_content(page, item, i, len(leaf_nodes))


# Using shared print_scraping_statistics from scraper_utils


def scrape_single_jurisdiction(
    url: str,
    output_name: str,
    output_dir_path: str = "output",
    csv_file: str | None = None,
):
    """
    Scrape HTML content from a single jurisdiction's code.

    Args:
        url: Full URL to the jurisdiction code
        output_name: Name for the output file
        output_dir_path: Directory to save output (default: "output")
        csv_file: Optional CSV file path for state extraction
    """
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    with sync_playwright() as p:
        browser, page = setup_browser_and_page(p)

        try:
            print(f"Navigating to {url} to extract TOC...")
            page.goto(url, wait_until="networkidle", timeout=60000)

            print("Waiting for TOC to load (this may take up to 60 seconds)...")
            page.wait_for_selector("#archiveTOC", timeout=60000)
            page.wait_for_load_state("networkidle", timeout=10000)

            print("Expanding TOC nodes...")
            expand_all_nodes(page)

            print("Extracting TOC structure...")
            toc_data = extract_toc_structure(page)

            if "error" in toc_data:
                print(f"Error: {toc_data['error']}")
                return

            hierarchical_toc = toc_data["items"]
            print(f"Found {toc_data['totalItems']} total items in TOC")

            flat_toc = flatten_toc(hierarchical_toc)

            leaf_nodes = [
                item for item in flat_toc if not item.get("has_children", False)
            ]
            print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

            _scrape_all_leaf_nodes(page, leaf_nodes)

        finally:
            browser.close()

    if flat_toc:
        metadata = create_output_metadata(
            url=url,
            output_name=output_name,
            scraper_name="general_code_publish.py",
            scraper_version="2.0",
            csv_file=csv_file,
        )

        output_path = save_scraped_output(
            sections=flat_toc,
            metadata=metadata,
            output_dir_path=output_dir_path,
            output_name=output_name,
        )

        print(f"\nSaved flattened TOC with HTML to: {output_path}")

    print_scraping_statistics(flat_toc)


if __name__ == "__main__":
    mode, url_or_csv, output_name, output_dir_path = parse_scraper_cli_args(
        "general_code_publish.py"
    )

    if mode == "csv":
        scrape_from_csv(url_or_csv, output_dir_path)
    else:  # single mode
        scrape_single_jurisdiction(url_or_csv, output_name, output_dir_path)
