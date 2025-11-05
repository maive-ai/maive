import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright


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
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style tags
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # Remove navigation and UI elements
        for element in soup.find_all(
            class_=[
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
            ]
        ):
            element.decompose()

        # Remove empty divs and spans
        for tag in soup.find_all(["span", "div"]):
            if not tag.get_text(strip=True) and not tag.find_all(True):
                tag.decompose()

        # Keep only essential attributes
        for tag in soup.find_all(True):
            new_attrs = {}
            if "id" in tag.attrs:
                new_attrs["id"] = tag.attrs["id"]
            if "href" in tag.attrs:
                new_attrs["href"] = tag.attrs["href"]
            tag.attrs = new_attrs

        # Remove HTML comments
        cleaned_html = str(soup)
        cleaned_html = re.sub(r"<!--.*?-->", "", cleaned_html, flags=re.DOTALL)

        # Remove excessive whitespace
        cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html)

        return cleaned_html.strip()

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

        if result.get('error'):
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
                    const value = checkbox ? checkbox.value : text;

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
                        value: value,
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

    def flatten_toc(
        self, nodes: List[Dict[str, Any]], parent_path: List[str] = None
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
                "url": None,  # MunicipalCodeOnline doesn't use URLs in tree
                "depth": len(current_path) - 1,
                "has_children": node.get("hasChildren", False),
            }

            # Keep internal value for clicking
            flat_item["_value"] = node.get("value")

            flat_list.append(flat_item)

            # Recursively process children
            if node.get("children"):
                flat_list.extend(self.flatten_toc(node["children"], current_path))

        return flat_list

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

        if click_result.get('error'):
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

    async def scrape_all_content(
        self, url: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Main scraping function that extracts TOC and content."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False, args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()

            try:
                print(f"Navigating to {url}")
                await page.goto(url, wait_until="networkidle", timeout=60000)

                # Wait for tree to load
                print("Waiting for Kendo TreeView to load...")
                await page.wait_for_selector('[role="tree"]', timeout=60000)
                await page.wait_for_timeout(3000)

                # Expand all nodes
                await self.expand_all_treeview(page)

                # Extract the hierarchical TOC structure
                print("Extracting TOC structure...")
                toc_data = await self.extract_toc_structure(page)

                if "error" in toc_data:
                    print(f"Error: {toc_data['error']}")
                    return [], [], []

                hierarchical_toc = toc_data["items"]
                print(f"Found {toc_data['totalItems']} total items in TOC")

                # Flatten the TOC
                flat_toc = self.flatten_toc(hierarchical_toc)

                # Filter to only leaf nodes for HTML scraping
                leaf_nodes = [
                    item for item in flat_toc if not item.get("has_children", False)
                ]
                print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

                # Scrape HTML for each leaf node
                for i, item in enumerate(leaf_nodes):
                    if not item.get("_value"):
                        item["html_error"] = "No value for this item"
                        print(
                            f"  ⚠ {i + 1}/{len(leaf_nodes)}: No value - {item['value'][:80]}"
                        )
                        continue

                    try:
                        html_content = await self.scrape_content(page, item["_value"])

                        if html_content:
                            item["html"] = html_content
                            print(f"  ✓ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]}")
                        else:
                            item["html_error"] = "No content found"
                            print(
                                f"  ⚠ {i + 1}/{len(leaf_nodes)}: No content - {item['value'][:80]}"
                            )

                    except Exception as e:
                        item["html_error"] = str(e)
                        print(
                            f"  ✗ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - {str(e)[:50]}"
                        )

                    # Small delay between clicks
                    await page.wait_for_timeout(200)

                # Clean up internal fields before returning
                for item in flat_toc:
                    item.pop("_value", None)

                # Return hierarchical TOC, flat TOC, and leaf nodes with HTML
                return hierarchical_toc, flat_toc, leaf_nodes

            except Exception as e:
                print(f"Error: {e}")
                return [], [], []

            finally:
                await browser.close()


async def scrape_single_municipality(
    url: str, output_name: str, output_dir_path: str = "output"
):
    """
    Scrape HTML content from a single municipality's code.

    Args:
        url: Full URL to the municipality code
        output_name: Name for the output file (without extension)
        output_dir_path: Directory to save output (default: "output")
    """
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    scraper = MunicipalCodeOnlineScraper()

    # Scrape all content and TOC in one pass
    hierarchical_toc, flat_toc, _ = await scraper.scrape_all_content(url)

    if flat_toc:
        # Create output directory if it doesn't exist
        output_dir = Path(output_dir_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename (no date prefix - overwrites existing)
        output_filename = f"{output_name}.json"
        output_path = output_dir / output_filename

        # Wrap content with metadata
        scraped_at = datetime.now().isoformat()
        output_data = {
            "metadata": {
                "scraped_at": scraped_at,
                "city_slug": output_name,
                "source_url": url,
                "scraper": "municipalcodeonline.py",
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
        print(f"  Total TOC items: {len(flat_toc)}")
        print(f"  Leaf nodes (with HTML): {total_leaf_nodes}")
        print(f"  Successfully scraped: {items_with_html}/{total_leaf_nodes}")
        if items_with_errors > 0:
            print(f"  Errors: {items_with_errors}")
    else:
        print("Failed to extract content")
        raise Exception("Failed to extract content")


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
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("status") == "ready" and row.get("code_url"):
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
            asyncio.run(
                scrape_single_municipality(
                    url=muni["code_url"],
                    output_name=muni["slug"],
                    output_dir_path=output_dir_path,
                )
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
            print(
                "Usage: python municipalcodeonline.py --csv <CSV_FILE> [--output-dir DIR]"
            )
            print(
                "Example: python municipalcodeonline.py --csv ut_municipalcodeonline_cities.csv --output-dir output"
            )
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

        asyncio.run(scrape_single_municipality(url, output_name, output_dir_path))

    # Show usage
    else:
        print("Usage:")
        print(
            "  Single mode:  python municipalcodeonline.py <URL> <NAME> [--output-dir DIR]"
        )
        print(
            "  Batch mode:   python municipalcodeonline.py --csv <CSV_FILE> [--output-dir DIR]"
        )
        print()
        print("Examples:")
        print(
            "  python municipalcodeonline.py https://alpine.municipalcodeonline.com/book?type=ordinances alpine"
        )
        print(
            "  python municipalcodeonline.py --csv ut_municipalcodeonline_cities.csv --output-dir output"
        )
        sys.exit(1)
