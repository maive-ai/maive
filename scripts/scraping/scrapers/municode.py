import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import Page, sync_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_utils import (
    clean_html_content,
    create_output_metadata,
    escape_css_selector,
    flatten_toc,
    parse_scraper_cli_args,
    print_scraping_statistics,
    run_batch_scraper,
    save_scraped_output,
    setup_browser_and_page,
)


def clean_municode_html(html_content):
    """
    Clean Municode HTML to keep only essential content.

    Args:
        html_content: HTML string to clean

    Returns:
        Minimal HTML with only content and essential structure
    """
    # First, handle Municode-specific structure extraction
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove Angular-specific custom tags (but keep their content)
    for tag in soup.find_all(
        lambda t: t.name and (t.name.startswith("mcc-") or t.name.startswith("ng-"))
    ):
        tag.unwrap()

    # Try to extract main content wrapper
    content_wrapper = soup.find("div", class_="chunk-content-wrapper")
    if content_wrapper:
        content_div = content_wrapper.find("div", class_="chunk-content")
        if content_div:
            # Build new div with BeautifulSoup instead of string concatenation
            new_div = soup.new_tag("div")

            # Copy attributes from chunk div if present
            chunk_div = soup.find("div", class_="chunk")
            if chunk_div:
                if chunk_div.get("id"):
                    new_div["id"] = chunk_div["id"]
                if chunk_div.get("data-nodedepth"):
                    new_div["data-nodedepth"] = chunk_div["data-nodedepth"]

            # Add title if present
            title_div = soup.find("div", class_="chunk-title")
            if title_div:
                h3 = soup.new_tag("h3")
                h3.string = title_div.get_text(strip=True)
                new_div.append(h3)

            # Add content
            if content_div:
                for child in content_div.children:
                    new_div.append(child)

            html_content = str(new_div)

    # Remove any Angular comment markers
    html_content = html_content.replace("<!---->", "")

    # Use shared HTML cleaning utility
    return clean_html_content(
        html_content,
        remove_ui_classes=[
            "mcc_codes_content_action_bar",
            "btn-group",
            "action-dropdown",
            "action-bar",
            "anchor-offset",
        ],
        preserve_classes=["chunk-", "b"],
        preserve_data_attrs=["data-nodedepth"],
    )


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


def _prepare_municode_toc_node(node: Dict[str, Any]) -> Dict[str, Any]:
    """Add Municode-specific fields to TOC node."""
    # Store nodeId as internal field for later use
    if node.get("nodeId"):
        node["_nodeId"] = node["nodeId"]
    # Normalize hasChildren to children key
    if "hasChildren" in node and not node.get("children"):
        node["has_children"] = node["hasChildren"]
    return node


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


def _load_chunks_area(page: Page, first_leaf_node: Dict[str, Any]) -> None:
    """
    Load chunks area by clicking the first leaf node.

    Args:
        page: Playwright page object
        first_leaf_node: First leaf node dictionary with _nodeId
    """
    if not first_leaf_node.get("_nodeId"):
        return

    first_link_selector = (
        f'#genTocList a.toc-item-heading[href*="nodeId={first_leaf_node["_nodeId"]}"]'
    )
    try:
        page.click(first_link_selector)
        page.wait_for_selector("ul.chunks", timeout=60000)
        print("Chunks area loaded successfully")
    except Exception as e:
        print(f"Warning: Could not load chunks area: {e}")


def _scrape_chunk_content(
    page: Page, item: Dict[str, Any], index: int, total: int
) -> None:
    """
    Scrape content for a single chunk item.

    Args:
        page: Playwright page object
        item: TOC item dictionary
        index: Current index (0-based)
        total: Total number of items
    """
    if not item.get("_nodeId"):
        item["html_error"] = "No nodeId for this item"
        print(f"  ⚠ {index + 1}/{total}: {item['value'][:80]} - no nodeId")
        return

    link_selector = f'#genTocList a.toc-item-heading[href*="nodeId={item["_nodeId"]}"]'

    try:
        page.click(link_selector)

        escaped_node_id = escape_css_selector(item["_nodeId"])
        chunk_selector = f"#c_{escaped_node_id}"
        page.wait_for_selector(chunk_selector, timeout=60000)

        page.wait_for_function(
            '() => document.querySelectorAll(".loading, .spinner").length === 0',
            timeout=60000,
        )

        time.sleep(0.5)

        chunk_html = page.locator(chunk_selector).evaluate("el => el.outerHTML")

        cleaned_html = clean_municode_html(chunk_html)
        cleaned_html = cleaned_html.replace('\\"', '"')

        item["html"] = cleaned_html

    except Exception as e:
        print(
            f"  ⚠ {index + 1}/{total}: {item['value'][:80]} - Failed to load chunk: {str(e)}"
        )
        item["html_error"] = f"Failed to load chunk: {str(e)}"

    time.sleep(0.3)


def _scrape_all_leaf_nodes(page: Page, leaf_nodes: List[Dict[str, Any]]) -> None:
    """
    Scrape HTML content for all leaf nodes.

    Args:
        page: Playwright page object
        leaf_nodes: List of leaf node dictionaries
    """
    for i, item in enumerate(leaf_nodes):
        try:
            _scrape_chunk_content(page, item, i, len(leaf_nodes))
        except Exception as e:
            print(f"  ✗ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - {str(e)}")
            item["html_error"] = str(e)


# Using shared print_scraping_statistics from scraper_utils


def scrape_single_municipality(
    url: str,
    output_name: str,
    output_dir_path: str = "output",
    csv_file: str | None = None,
):
    """
    Scrape HTML content from a single municipality's code.

    Args:
        url: Full URL to the municipality code
        output_name: Name for the output file
        output_dir_path: Directory to save output (default: "output")
        csv_file: Optional CSV file path to extract state from
    """
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    flat_toc = None

    with sync_playwright() as p:
        browser, page = setup_browser_and_page(p)

        try:
            print(f"Navigating to {url}")
            page.goto(url, wait_until="domcontentloaded")

            print("Waiting for Angular TOC to load...")
            page.wait_for_selector("#genTocList", timeout=60000)
            page.wait_for_selector("a.toc-item-heading", timeout=60000)
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

            # Rename nodeId to _nodeId before flattening (flatten_toc only preserves fields starting with _)
            def add_underscore_to_nodeid(nodes):
                """Recursively rename nodeId to _nodeId in TOC structure."""
                for node in nodes:
                    if "nodeId" in node:
                        node["_nodeId"] = node.pop("nodeId")
                    if "children" in node:
                        add_underscore_to_nodeid(node["children"])

            add_underscore_to_nodeid(hierarchical_toc)

            flat_toc = flatten_toc(hierarchical_toc)

            leaf_nodes = [
                item for item in flat_toc if not item.get("has_children", False)
            ]
            print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

            if leaf_nodes:
                _load_chunks_area(page, leaf_nodes[0])

            _scrape_all_leaf_nodes(page, leaf_nodes)

            for item in flat_toc:
                item.pop("_nodeId", None)

            print("\n✓ Scraping complete!")

        except Exception as e:
            print(f"Error: {e}")
            return

        finally:
            browser.close()

    if flat_toc:
        metadata = create_output_metadata(
            url=url,
            output_name=output_name,
            scraper_name="municode.py",
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

    if flat_toc:
        print_scraping_statistics(flat_toc)


def scrape_from_csv(csv_path: str, output_dir_path: str = "output"):
    """
    Scrape multiple municipalities from a CSV file.

    Args:
        csv_path: Path to CSV file containing municipality list
        output_dir_path: Directory to save outputs (default: "output")
    """
    run_batch_scraper(
        csv_path=csv_path,
        output_dir_path=output_dir_path,
        scraper_function=scrape_single_municipality,
        scraper_name="municode.py",
    )


if __name__ == "__main__":
    mode, url_or_csv, output_name, output_dir_path = parse_scraper_cli_args(
        "municode.py"
    )

    if mode == "csv":
        scrape_from_csv(url_or_csv, output_dir_path)
    else:  # single mode
        scrape_single_municipality(url_or_csv, output_name, output_dir_path)
