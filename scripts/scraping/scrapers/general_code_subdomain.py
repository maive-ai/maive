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

# Using shared clean_html_content from scraper_utils


def extract_toc_structure(page):
    """Extract the hierarchical TOC structure from the page."""
    return page.evaluate("""
        () => {
            function extractNodeData(liElement) {
                const linkElement = liElement.querySelector(':scope > a.tocitem-link');
                if (!linkElement) return null;

                // Get number and name
                const numElement = linkElement.querySelector('.num');
                const nameElement = linkElement.querySelector('.name');
                const num = numElement ? numElement.innerText.trim() : '';
                const name = nameElement ? nameElement.innerText.trim() : '';
                const text = num && name ? `${num} - ${name}` : (num || name);

                // Get identifier and URL
                const identifier = liElement.getAttribute('data-identifier');
                const href = linkElement.getAttribute('href');
                const baseUrl = window.location.origin;
                const url = href ? baseUrl + href : null;

                // Get children
                const children = [];
                const childItems = liElement.querySelectorAll(':scope > ul.tocitem-branch > li.tocitem');
                childItems.forEach(child => {
                    const childData = extractNodeData(child);
                    if (childData) children.push(childData);
                });

                return { text, value: identifier, url, children };
            }

            const topLevelItems = document.querySelectorAll('.contents-product.active .contents-toc > li[role="treeitem"]');
            const tocItems = [];

            topLevelItems.forEach(item => {
                const itemData = extractNodeData(item);
                if (itemData) tocItems.push(itemData);
            });

            return {
                items: tocItems,
                totalItems: document.querySelectorAll('.contents-product.active .contents-toc li.tocitem').length
            };
        }
    """)


# Using shared flatten_toc from scraper_utils


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
        scraper_name="general_code_subdomain.py",
    )


# Using extract_url_path_segment from scraper_utils


def _scrape_article_content(
    page: Page, item: Dict[str, Any], identifier: str, index: int, total: int
) -> None:
    """
    Scrape content for a single article item.

    Args:
        page: Playwright page object
        item: TOC item dictionary
        identifier: Article identifier
        index: Current index (0-based)
        total: Total number of items
    """
    article_selector = f'article[id="{identifier}"]'

    try:
        if page.locator(article_selector).count() > 0:
            content_html = page.locator(article_selector).evaluate("el => el.outerHTML")
            print(f"  ✓ {index + 1}/{total}: Found on current page - {item['value']}")
        else:
            print(f"  → {index + 1}/{total}: Navigating to {item['url']}")
            page.goto(item["url"], wait_until="networkidle", timeout=60000)
            page.wait_for_selector("article", timeout=60000)

            if page.locator(article_selector).count() > 0:
                content_html = page.locator(article_selector).evaluate(
                    "el => el.outerHTML"
                )
                print(
                    f"  ✓ {index + 1}/{total}: Found after navigation - {item['value']}"
                )
            else:
                content_html = page.locator("article").first.evaluate(
                    "el => el.outerHTML"
                )
                print(f"  ✓ {index + 1}/{total}: Using fallback - {item['value']}")

        cleaned_html = clean_html_content(content_html, preserve_classes=["mco-"])
        item["html"] = cleaned_html

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
        if not item.get("url"):
            print(f"  ✗ {i + 1}/{len(leaf_nodes)}: No URL - {item['value'][:80]}")
            continue

        identifier = extract_url_path_segment(item["url"])
        _scrape_article_content(page, item, identifier, i, len(leaf_nodes))


# Using shared print_scraping_statistics from scraper_utils


def scrape_single_jurisdiction(
    url: str,
    output_name: str,
    output_dir_path: str = "output",
    csv_file: str | None = None,
):
    """
    Scrape a single jurisdiction.

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

            print("Opening Contents modal...")
            page.click('a.nav-link[data-target="#contents"]')
            page.wait_for_timeout(1000)

            print("Waiting for TOC to load (this may take up to 60 seconds)...")
            page.wait_for_selector('.contents-toc li[role="treeitem"]', timeout=60000)

            print("Clicking Expand All button...")
            page.click("button.contents-expand")
            page.wait_for_timeout(2000)

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
            scraper_name="general_code_subdomain.py",
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
        "general_code_subdomain.py"
    )

    if mode == "csv":
        scrape_from_csv(url_or_csv, output_dir_path)
    else:  # single mode
        scrape_single_jurisdiction(url_or_csv, output_name, output_dir_path)
