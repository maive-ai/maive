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
    read_municipalities_from_csv,
    save_scraped_output,
    setup_browser_and_page_async,
)

# Suppress RuntimeWarning from playwright_stealth (harmless in async context)
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited.*"
)


class AMLegalContentScraper:
    """Scraper for AMLegal content by clicking TOC links."""

    def clean_amlegal_html(self, html_content):
        """
        Clean AMLegal HTML to keep only essential content.

        Args:
            html_content: HTML string to clean

        Returns:
            Minimal HTML with only content and essential structure
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
                "pagination",
            ],
        )

    async def expand_all_nodes(self, page: Page) -> None:
        """Expand all nodes in the TOC tree."""
        expanded_count = 0
        max_concurrent = 10

        round_num = 0
        while True:
            round_num += 1

            # Find all collapsed nodes
            collapsed_buttons = await page.query_selector_all(
                '.toc-entry--has-children button.toc-caret[aria-expanded="false"]'
            )

            if not collapsed_buttons:
                print(f"No more nodes to expand after {round_num} rounds")
                break

            print(f"Round {round_num}: Found {len(collapsed_buttons)} nodes to expand")

            # Click all nodes in batches
            for i in range(0, len(collapsed_buttons), max_concurrent):
                batch = collapsed_buttons[i : i + max_concurrent]

                # Click all in this batch
                for button in batch:
                    try:
                        if await button.is_visible():
                            await button.click()
                            expanded_count += 1
                    except:
                        pass

                # Wait for loading spinners to disappear
                await page.wait_for_function(
                    '() => document.querySelectorAll(".toc-entry__loading").length === 0',
                    timeout=60000,
                )

                await page.wait_for_timeout(500)

        print(f"Expansion complete: {expanded_count} nodes expanded")

    async def collect_toc_links(self, page: Page) -> List[Dict[str, Any]]:
        """Collect all TOC links after expansion."""
        return await page.evaluate("""
            () => {
                const links = [];
                // Get all TOC links that have a docId
                const tocLinks = document.querySelectorAll('.codenav__toc a.toc-link[data-docid]');

                tocLinks.forEach(link => {
                    // Check if this is a leaf node (parent doesn't have .toc-entry--has-children)
                    const entry = link.closest('.toc-entry');
                    const isLeaf = !entry.classList.contains('toc-entry--has-children');

                    if (isLeaf) {
                        links.push({
                            text: link.innerText.trim(),
                            docId: link.dataset.docid,
                            codeUuid: link.dataset.codeuuid || null,
                            element: link,  // We'll need to click this
                            href: link.href
                        });
                    }
                });

                return links;
            }
        """)

    async def scrape_content(self, page: Page, doc_id: str) -> str:
        """
        Extract content for a specific doc_id from the loaded page.

        Args:
            page: The Playwright page object
            doc_id: The document ID to extract content for

        Returns:
            The cleaned HTML content
        """
        # Wait for content to load in #codecontent
        await page.wait_for_selector("#codecontent", timeout=60000)

        # Wait for the specific element with rid-{doc_id}
        rid_selector = f"#rid-{doc_id}"
        try:
            await page.wait_for_selector(rid_selector, timeout=60000)
        except:
            print(f"    ⚠ Element {rid_selector} not found")
            return None

        # Extract the parent section containing this rid
        section_html = await page.evaluate(f"""
            () => {{
                const ridElement = document.querySelector('{rid_selector}');
                if (!ridElement) return null;

                // Find the parent section (curr-section or section-N or has id like section-N)
                let parent = ridElement.parentElement;
                while (parent) {{
                    // Check for class names or id pattern
                    if (parent.classList.contains('curr-section') ||
                        Array.from(parent.classList).some(c => c.startsWith('section-')) ||
                        (parent.id && parent.id.startsWith('section-'))) {{
                        return parent.outerHTML;
                    }}
                    parent = parent.parentElement;
                }}

                // If no section found, just return the rid element itself
                return ridElement.outerHTML;
            }}
        """)

        if section_html:
            return self.clean_amlegal_html(section_html)
        return None

    async def extract_toc_structure(self, page: Page) -> Dict[str, Any]:
        """Extract the hierarchical TOC structure from the page."""
        return await page.evaluate("""
            () => {
                function extractNodeData(entryElement) {
                    // Get the link element
                    const link = entryElement.querySelector(':scope > .toc-entry__wrap > a.toc-link');
                    if (!link) return null;

                    const text = link.innerText.trim();
                    const url = link.href;
                    const _docId = link.dataset.docid || null;
                    const _codeUuid = link.dataset.codeuuid || null;

                    // Get children if expanded
                    const children = [];
                    const collapseDiv = entryElement.querySelector(':scope > .collapse.show');
                    if (collapseDiv) {
                        const childEntries = collapseDiv.querySelectorAll(':scope > .toc-entry');
                        childEntries.forEach(child => {
                            const childData = extractNodeData(child);
                            if (childData) {
                                children.push(childData);
                            }
                        });
                    }

                    // Check if it has children - either by class or by actual children found
                    const hasChildren = entryElement.classList.contains('toc-entry--has-children') || children.length > 0;

                    return {
                        text: text,
                        _docId: _docId,
                        _codeUuid: _codeUuid,
                        url: url,
                        hasChildren: hasChildren,
                        children: children
                    };
                }

                // Find the main TOC container
                const tocContainer = document.querySelector('.codenav__toc');
                if (!tocContainer) {
                    return { error: 'TOC container not found' };
                }

                const tocItems = [];

                // Handle the special code container (toc-entry--code)
                const codeContainer = tocContainer.querySelector('.toc-entry--code');
                if (codeContainer) {
                    // Get the actual content entries inside the code container
                    const codeContent = codeContainer.querySelector('.collapse.show');
                    if (codeContent) {
                        const contentEntries = codeContent.querySelectorAll(':scope > .toc-entry');
                        contentEntries.forEach(entry => {
                            const itemData = extractNodeData(entry);
                            if (itemData) {
                                tocItems.push(itemData);
                            }
                        });
                    }
                } else {
                    // Fallback: if no code container, get all top-level entries
                    const topLevelEntries = tocContainer.querySelectorAll(':scope > .toc-entry');
                    topLevelEntries.forEach(entry => {
                        const itemData = extractNodeData(entry);
                        if (itemData) {
                            tocItems.push(itemData);
                        }
                    });
                }

                return {
                    items: tocItems,
                    totalItems: document.querySelectorAll('.codenav__toc .toc-entry').length
                };
            }
        """)

    # Using shared flatten_toc from scraper_utils

    async def _inject_navigation_helpers(self, page: Page) -> None:
        """Inject JavaScript helper functions for programmatic navigation."""
        await page.evaluate("""
            () => {
                window.navigateToDoc = function(docId) {
                    const link = document.querySelector(`a.toc-link[data-docid="${docId}"]`);
                    if (link) {
                        link.click();
                        return true;
                    }
                    return false;
                };

                window.navigateByHash = function(docId) {
                    const link = document.querySelector(`a.toc-link[data-docid="${docId}"]`);
                    if (link && link.href) {
                        window.location.href = link.href;
                        return true;
                    }
                    return false;
                };
            }
        """)

    async def _process_leaf_node(
        self, page: Page, item: Dict[str, Any], index: int, total: int, scraped_ids: set
    ) -> tuple[bool, Dict[str, Any] | None]:
        """
        Process a single leaf node, extracting content if available.

        Returns:
            Tuple of (success, failed_item if failed else None)
        """
        if not item.get("_docId"):
            item["html_error"] = "No docId for this item"
            print(f"  ⚠ Skipping {index + 1}/{total}: {item['value'][:80]} - no docId")
            return False, None

        if item["_docId"] in scraped_ids:
            print(
                f"  ✓ Skipping {index + 1}/{total}: {item['value'][:80]} - already scraped"
            )
            return True, None

        try:
            rid_selector = f"#rid-{item['_docId']}"
            is_already_present = await page.evaluate(
                f'document.querySelector("{rid_selector}") !== null'
            )

            if is_already_present:
                print(
                    f"  ⚡ {index + 1}/{total}: {item['value'][:80]} - already loaded"
                )
            else:
                link_selector = f'a.toc-link[data-docid="{item["_docId"]}"]'
                await page.click(link_selector)
                await page.wait_for_selector(rid_selector, timeout=15000)

            html_content = await self.scrape_content(page, item["_docId"])

            if html_content:
                item["html"] = html_content
                scraped_ids.add(item["_docId"])
                return True, None
            else:
                print(
                    f"  ⚠ No content for {index + 1}/{total}: {item['value'][:80]} - will retry"
                )
                return False, item

        except asyncio.TimeoutError:
            print(
                f"  ⏳ Timeout for {index + 1}/{total}: {item['value'][:80]} - will retry"
            )
            return False, item
        except Exception as e:
            print(
                f"  ⚠ Error for {index + 1}/{total}: {item['value'][:80]} - {str(e)[:50]}"
            )
            return False, item

    async def _retry_failed_item(
        self, page: Page, item: Dict[str, Any], index: int, total: int
    ) -> bool:
        """Retry scraping a failed item with longer timeout."""
        try:
            success = await page.evaluate(f'window.navigateToDoc("{item["_docId"]}")')
            if not success:
                link_selector = f'a.toc-link[data-docid="{item["_docId"]}"]'
                await page.click(link_selector)

            rid_selector = f"#rid-{item['_docId']}"
            await page.wait_for_selector(rid_selector, timeout=30000)

            html_content = await self.scrape_content(page, item["_docId"])

            if html_content:
                item["html"] = html_content
                return True
            else:
                item["html_error"] = "No content found after retry"
                print(
                    f"  ✗ Retry {index + 1}/{total}: {item['value'][:80]} - still no content"
                )
                return False

        except asyncio.TimeoutError:
            item["html_error"] = "Timeout on retry"
            print(f"  ✗ Retry {index + 1}/{total}: {item['value'][:80]} - timeout")
            return False
        except Exception as e:
            item["html_error"] = str(e)
            print(
                f"  ✗ Retry {index + 1}/{total}: {item['value'][:80]} - {str(e)[:50]}"
            )
            return False

    async def _scrape_leaf_nodes(
        self, page: Page, leaf_nodes: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Scrape all leaf nodes, collecting failures for retry."""
        failed_items = []
        scraped_ids = set()

        for i, item in enumerate(leaf_nodes):
            success, failed_item = await self._process_leaf_node(
                page, item, i, len(leaf_nodes), scraped_ids
            )
            if not success and failed_item:
                failed_items.append(failed_item)

            await page.wait_for_timeout(200)

        return failed_items

    async def _retry_failed_nodes(
        self, page: Page, failed_items: List[Dict[str, Any]]
    ) -> None:
        """Retry scraping failed items."""
        if not failed_items:
            return

        print(f"\nRetrying {len(failed_items)} failed items...")
        for i, item in enumerate(failed_items):
            await self._retry_failed_item(page, item, i, len(failed_items))
            await page.wait_for_timeout(500)

        recovered = sum(1 for item in failed_items if "html" in item)
        if recovered < len(failed_items):
            print(
                f"\nRetry complete: {recovered}/{len(failed_items)} recovered, "
                f"{len(failed_items) - recovered} still failed"
            )

    async def scrape_all_content(
        self, url: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Main scraping function that clicks through TOC and collects content."""
        async with async_playwright() as p:
            browser, page = await setup_browser_and_page_async(p)

            try:
                print(f"Navigating to {url}")
                await page.goto(url, wait_until="domcontentloaded")

                print("Waiting for TOC to load...")
                await page.wait_for_selector(".codenav__toc", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=10000)

                await self.expand_all_nodes(page)

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
                print(f"Found {len(leaf_nodes)} leaf nodes to process")

                await self._inject_navigation_helpers(page)

                failed_items = await self._scrape_leaf_nodes(page, leaf_nodes)
                await self._retry_failed_nodes(page, failed_items)

                for item in flat_toc:
                    item.pop("_docId", None)
                    item.pop("_codeUuid", None)

                return hierarchical_toc, flat_toc, leaf_nodes

            except Exception as e:
                print(f"Error: {e}")
                return [], [], []

            finally:
                await browser.close()


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
        csv_file: Optional CSV file path for state extraction
    """
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    scraper = AMLegalContentScraper()
    hierarchical_toc, flat_toc, _ = await scraper.scrape_all_content(url)

    if not flat_toc:
        print("Failed to extract content")
        raise Exception("Failed to extract content")

    metadata = create_output_metadata(
        url=url,
        output_name=output_name,
        scraper_name="amlegal.py",
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


def scrape_from_csv(csv_path: str, output_dir_path: str = "output"):
    """
    Scrape multiple municipalities from a CSV file.

    CSV format expected:
        name,slug,base_url,code_url,status

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
        "amlegal.py", supports_async=True
    )

    if mode == "csv":
        scrape_from_csv(url_or_csv, output_dir_path)
    else:  # single mode
        asyncio.run(
            scrape_single_municipality(url_or_csv, output_name, output_dir_path)
        )
