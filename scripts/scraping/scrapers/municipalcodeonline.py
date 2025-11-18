import asyncio
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import Page, async_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_utils import (
    clean_html_content,
    create_output_metadata,
    flatten_toc,
    parse_scraper_cli_args,
    print_scraping_statistics,
    read_municipalities_from_csv,
    save_scraped_output,
    setup_browser_and_page_async,
)

# Suppress RuntimeWarning from playwright_stealth (harmless in async context)
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited.*"
)


class MunicipalCodeOnlineScraper:
    """Scraper for MunicipalCodeOnline.com sites using Kendo TreeView."""

    def clean_html_content(self, html_content):
        """
        Clean HTML content to remove unnecessary elements and attributes.

        Args:
            html_content: HTML string to clean

        Returns:
            Cleaned HTML string
        """
        return clean_html_content(
            html_content,
            remove_ui_classes=[
                "navbar",
                "nav-",
                "header",
                "footer",
                "breadcrumb",
                "btn",
                "modal",
                "dropdown",
                "sidebar",
                "menu",
                "toolbar",
                "k-link",
            ],
        )

    async def expand_all_treeview(self, page: Page) -> None:
        """Expand all nodes in the Kendo TreeView using the API."""
        print("Expanding all tree nodes...")

        # Use Kendo API to expand all items
        result = await page.evaluate("""
            () => {
                const tocElement = document.querySelector('#TOC');
                if (!tocElement) return { error: 'TOC element not found' };

                const treeView = $(tocElement).data('kendoTreeView');
                if (!treeView) return { error: 'TreeView widget not found' };

                // Expand all items
                treeView.expand('.k-item');

                return { success: true };
            }
        """)

        if result.get("error"):
            print(f"  Warning: {result['error']}")
        else:
            # Wait for expansion to complete
            await page.wait_for_timeout(3000)
            print("  ✓ All nodes expanded")

    async def extract_toc_structure(self, page: Page) -> Dict[str, Any]:
        """Extract the hierarchical TOC structure from the Kendo TreeView."""
        return await page.evaluate("""
            () => {
                function extractNodeData(liElement) {
                    // Get the span element with the text
                    const span = liElement.querySelector(':scope > div > .k-in');
                    if (!span) return null;

                    const text = span.textContent.trim();

                    // Get the value from checkbox if exists
                    const checkbox = liElement.querySelector(':scope > div > .k-checkbox input');
                    const _value = checkbox ? checkbox.value : text;

                    // Check if it has children by looking for nested ul
                    const childUl = liElement.querySelector(':scope > ul.k-group');
                    const children = [];

                    if (childUl) {
                        const childItems = childUl.querySelectorAll(':scope > li[role="treeitem"]');
                        childItems.forEach(child => {
                            const childData = extractNodeData(child);
                            if (childData) children.push(childData);
                        });
                    }

                    return {
                        text: text,
                        _value: _value,
                        hasChildren: children.length > 0,
                        children: children
                    };
                }

                const tree = document.querySelector('[role="tree"]');
                if (!tree) {
                    return { error: 'Tree not found' };
                }

                const tocItems = [];
                const topLevelItems = tree.querySelectorAll(':scope > li[role="treeitem"]');

                topLevelItems.forEach(item => {
                    const itemData = extractNodeData(item);
                    if (itemData) tocItems.push(itemData);
                });

                return {
                    items: tocItems,
                    totalItems: document.querySelectorAll('[role="treeitem"]').length
                };
            }
        """)

    # Using shared flatten_toc from scraper_utils

    async def scrape_content(self, page: Page, item_value: str) -> str:
        """
        Extract content for a specific item by clicking on it.

        Args:
            page: The Playwright page object
            item_value: The checkbox value to identify the tree item

        Returns:
            The cleaned HTML content
        """
        # Click the tree item
        click_result = await page.evaluate(f"""
            () => {{
                // Find the tree item by checkbox value
                const checkbox = document.querySelector('input[name="checkedNodes"][value="{item_value}"]');
                if (!checkbox) return {{ error: 'Checkbox not found' }};

                // Find the span to click
                const span = checkbox.closest('div').querySelector('.k-in');
                if (!span) return {{ error: 'Span not found' }};

                // Click the span
                span.click();
                return {{ success: true }};
            }}
        """)

        if click_result.get("error"):
            return None

        # Wait for content to load
        await page.wait_for_timeout(1000)

        # Extract content from #contents div (inside the right pane of the Kendo Splitter)
        content_html = await page.evaluate("""
            () => {
                const contents = document.querySelector('#contents');
                if (!contents) return null;
                return contents.innerHTML;
            }
        """)

        if content_html:
            return self.clean_html_content(content_html)
        return None

    async def _scrape_leaf_node_content(
        self, page: Page, item: Dict[str, Any], index: int, total: int
    ) -> None:
        """
        Scrape content for a single leaf node.

        Args:
            page: Playwright page object
            item: TOC item dictionary
            index: Current index (0-based)
            total: Total number of items
        """
        if not item.get("_value"):
            item["html_error"] = "No value for this item"
            print(f"  ⚠ {index + 1}/{total}: No value - {item['value'][:80]}")
            return

        try:
            html_content = await self.scrape_content(page, item["_value"])

            if html_content:
                item["html"] = html_content
                print(f"  ✓ {index + 1}/{total}: {item['value'][:80]}")
            else:
                item["html_error"] = "No content found"
                print(f"  ⚠ {index + 1}/{total}: No content - {item['value'][:80]}")

        except Exception as e:
            item["html_error"] = str(e)
            print(f"  ✗ {index + 1}/{total}: {item['value'][:80]} - {str(e)[:50]}")

        await page.wait_for_timeout(200)

    async def _scrape_all_leaf_nodes(
        self, page: Page, leaf_nodes: List[Dict[str, Any]]
    ) -> None:
        """
        Scrape HTML content for all leaf nodes.

        Args:
            page: Playwright page object
            leaf_nodes: List of leaf node dictionaries
        """
        for i, item in enumerate(leaf_nodes):
            await self._scrape_leaf_node_content(page, item, i, len(leaf_nodes))

    async def scrape_all_content(
        self, url: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Main scraping function that extracts TOC and content.

        Args:
            url: URL to scrape

        Returns:
            Tuple of (hierarchical_toc, flat_toc, leaf_nodes)
        """
        async with async_playwright() as p:
            browser, page = await setup_browser_and_page_async(p)

            try:
                print(f"Navigating to {url}")
                await page.goto(url, wait_until="networkidle", timeout=60000)

                print("Waiting for Kendo TreeView to load...")
                await page.wait_for_selector('[role="tree"]', timeout=60000)
                await page.wait_for_timeout(3000)

                await self.expand_all_treeview(page)

                print("Extracting TOC structure...")
                toc_data = await self.extract_toc_structure(page)

                if "error" in toc_data:
                    print(f"Error: {toc_data['error']}")
                    return [], [], []

                hierarchical_toc = toc_data["items"]
                print(f"Found {toc_data['totalItems']} total items in TOC")

                flat_toc = flatten_toc(hierarchical_toc)

                leaf_nodes = [
                    item for item in flat_toc if not item.get("has_children", False)
                ]
                print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

                await self._scrape_all_leaf_nodes(page, leaf_nodes)

                for item in flat_toc:
                    item.pop("_value", None)

                return hierarchical_toc, flat_toc, leaf_nodes

            except Exception as e:
                print(f"Error: {e}")
                return [], [], []

            finally:
                await browser.close()


# Using shared print_scraping_statistics from scraper_utils


async def scrape_single_municipality(
    url: str,
    output_name: str,
    output_dir_path: str = "output",
    csv_file: str | None = None,
):
    """
    Scrape HTML content from a single municipality's code.

    Args:
        url: Full URL to the municipality code
        output_name: Name for the output file (without extension)
        output_dir_path: Directory to save output (default: "output")
        csv_file: Optional path to CSV file for state extraction
    """
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    scraper = MunicipalCodeOnlineScraper()

    hierarchical_toc, flat_toc, _ = await scraper.scrape_all_content(url)

    if not flat_toc:
        print("Failed to extract content")
        raise Exception("Failed to extract content")

    metadata = create_output_metadata(
        url=url,
        output_name=output_name,
        scraper_name="municipalcodeonline.py",
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


def scrape_from_csv(csv_path: str, output_dir_path: str = "output"):
    """
    Scrape multiple municipalities from a CSV file.

    Args:
        csv_path: Path to CSV file containing municipality list
        output_dir_path: Directory to save outputs (default: "output")
    """
    try:
        municipalities = read_municipalities_from_csv(csv_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if not municipalities:
        print(f"Error: No ready municipalities found in {csv_path}")
        return

    print(f"\n{'=' * 60}")
    print("BATCH SCRAPING MODE")
    print(f"{'=' * 60}")
    print(f"CSV file: {csv_path}")
    print(f"Found {len(municipalities)} municipalities to scrape")
    print(f"Output directory: {output_dir_path}")
    print(f"{'=' * 60}\n")

    for i, muni in enumerate(municipalities, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(municipalities)}] Scraping: {muni['name']}")
        print(f"{'=' * 60}")

        try:
            asyncio.run(
                scrape_single_municipality(
                    url=muni["code_url"],
                    output_name=muni["slug"],
                    output_dir_path=output_dir_path,
                    csv_file=csv_path,
                )
            )
            print(f"✓ Completed: {muni['name']}")
        except Exception as e:
            print(f"✗ Failed: {muni['name']}")
            print(f"  Error: {str(e)}")

    print(f"\n{'=' * 60}")
    print("BATCH SCRAPING COMPLETE")
    print(f"Processed {len(municipalities)} municipalities")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    mode, url_or_csv, output_name, output_dir_path = parse_scraper_cli_args(
        "municipalcodeonline.py", supports_async=True
    )

    if mode == "csv":
        scrape_from_csv(url_or_csv, output_dir_path)
    else:  # single mode
        asyncio.run(
            scrape_single_municipality(url_or_csv, output_name, output_dir_path)
        )
