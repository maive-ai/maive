import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright


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
                "pagination",
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
                    const docId = link.dataset.docid || null;
                    const codeUuid = link.dataset.codeuuid || null;

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
                        docId: docId,
                        codeUuid: codeUuid,
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
                "url": node.get("url"),
                "depth": len(current_path) - 1,
                "has_children": node.get("hasChildren", False),
            }

            # Keep docId and codeUuid internally for scraping, but they won't be in final output
            flat_item["_docId"] = node.get("docId")
            flat_item["_codeUuid"] = node.get("codeUuid")

            flat_list.append(flat_item)

            # Recursively process children
            if node.get("children"):
                flat_list.extend(self.flatten_toc(node["children"], current_path))

        return flat_list

    async def scrape_all_content(
        self, url: str
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Main scraping function that clicks through TOC and collects content."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False, args=["--disable-blink-features=AutomationControlled"]
            )
            page = await browser.new_page()

            try:
                print(f"Navigating to {url}")
                await page.goto(url, wait_until="domcontentloaded")

                # Wait for TOC to load
                print("Waiting for TOC to load...")
                await page.wait_for_selector(".codenav__toc", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=10000)

                # Expand all nodes first
                await self.expand_all_nodes(page)

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

                # Inject a helper function for programmatic navigation
                await page.evaluate("""
                    () => {
                        window.navigateToDoc = function(docId) {
                            // Find and click the link programmatically
                            const link = document.querySelector(`a.toc-link[data-docid="${docId}"]`);
                            if (link) {
                                link.click();
                                return true;
                            }
                            return false;
                        };

                        // Alternative: trigger navigation by updating URL hash
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

                # Process items in two passes - skip failures and retry them at the end
                failed_items = []

                # FIRST PASS: Process all items, collect failures
                for i, item in enumerate(leaf_nodes):
                    if not item.get("_docId"):
                        item["html_error"] = "No docId for this item"
                        print(
                            f"  ⚠ Skipping {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - no docId"
                        )
                        continue

                    try:
                        # Try with shorter timeout on first pass
                        link_selector = f'a.toc-link[data-docid="{item["_docId"]}"]'
                        await page.click(link_selector)

                        # Wait for the specific rid element to appear (shorter timeout)
                        rid_selector = f"#rid-{item['_docId']}"
                        await page.wait_for_selector(rid_selector, timeout=15000)

                        # Extract the content
                        html_content = await self.scrape_content(page, item["_docId"])

                        if html_content:
                            item["html"] = html_content
                        else:
                            failed_items.append(item)
                            print(
                                f"  ⚠ No content for {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - will retry"
                            )

                    except asyncio.TimeoutError:
                        failed_items.append(item)
                        print(
                            f"  ⏳ Timeout for {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - will retry"
                        )
                    except Exception as e:
                        failed_items.append(item)
                        print(
                            f"  ⚠ Error for {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - {str(e)[:50]}"
                        )

                    # Small delay between clicks
                    await page.wait_for_timeout(200)

                # SECOND PASS: Retry failed items
                if failed_items:
                    print(f"\nRetrying {len(failed_items)} failed items...")
                    for i, item in enumerate(failed_items):
                        try:
                            # Use JavaScript navigation for retry
                            success = await page.evaluate(
                                f'window.navigateToDoc("{item["_docId"]}")'
                            )
                            if not success:
                                # Fallback to regular click
                                link_selector = (
                                    f'a.toc-link[data-docid="{item["_docId"]}"]'
                                )
                                await page.click(link_selector)

                            # Wait with longer timeout on retry
                            rid_selector = f"#rid-{item['_docId']}"
                            await page.wait_for_selector(rid_selector, timeout=30000)

                            # Extract the content
                            html_content = await self.scrape_content(
                                page, item["_docId"]
                            )

                            if html_content:
                                item["html"] = html_content
                            else:
                                item["html_error"] = "No content found after retry"
                                print(
                                    f"  ✗ Retry {i + 1}/{len(failed_items)}: {item['value'][:80]} - still no content"
                                )

                        except asyncio.TimeoutError:
                            item["html_error"] = "Timeout on retry"
                            print(
                                f"  ✗ Retry {i + 1}/{len(failed_items)}: {item['value'][:80]} - timeout"
                            )
                        except Exception as e:
                            item["html_error"] = str(e)
                            print(
                                f"  ✗ Retry {i + 1}/{len(failed_items)}: {item['value'][:80]} - {str(e)[:50]}"
                            )

                        # Small delay between retries
                        await page.wait_for_timeout(500)

                    recovered = sum(1 for item in failed_items if "html" in item)
                    if recovered < len(failed_items):
                        print(
                            f"\nRetry complete: {recovered}/{len(failed_items)} recovered, {len(failed_items) - recovered} still failed"
                        )

                # Clean up internal fields before returning
                for item in flat_toc:
                    item.pop("_docId", None)
                    item.pop("_codeUuid", None)

                # Return hierarchical TOC, flat TOC, and leaf nodes with HTML
                return hierarchical_toc, flat_toc, leaf_nodes

            except Exception as e:
                print(f"Error: {e}")
                return [], [], []

            finally:
                await browser.close()


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape AMLegal content by clicking TOC links"
    )
    parser.add_argument("url", help="URL of the AMLegal page to scrape")
    parser.add_argument("name", help="Name for the output file")
    parser.add_argument(
        "--output-dir", help="Output directory path (default: output)", default="output"
    )

    args = parser.parse_args()
    output_name = args.name

    scraper = AMLegalContentScraper()

    # Scrape all content and TOC in one pass
    hierarchical_toc, flat_toc, _ = await scraper.scrape_all_content(args.url)

    if flat_toc:
        # Create output directory if it doesn't exist
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with date and name
        date_str = datetime.now().strftime("%m-%d-%Y")
        output_filename = f"{date_str}_{output_name}.json"
        output_path = output_dir / output_filename

        # Save only the flattened TOC with HTML content
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(flat_toc, f, indent=2, ensure_ascii=False)
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
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
