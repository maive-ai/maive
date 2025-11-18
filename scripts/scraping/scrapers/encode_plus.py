"""
Scraper for Municode ordinance documents.
Extracts table of contents and content for each section using depth-first search.
"""

import asyncio
import sys
import traceback
import warnings
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_utils import (
    clean_html_content,
    create_output_metadata,
    flatten_toc,
    save_scraped_output,
    setup_browser_and_page_async,
)

# Suppress RuntimeWarning from playwright_stealth (harmless in async context)
warnings.filterwarnings(
    "ignore", category=RuntimeWarning, message=".*coroutine.*was never awaited.*"
)


class MunicodeOrdinanceScraper:
    """Scrapes ordinance documents from Municode sites."""

    def clean_municode_html(self, html_content: str) -> str:
        """
        Clean Municode HTML to keep only essential content.

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

    async def scrape_content(self, page: Page, secid: str) -> str | None:
        """
        Extract content for a specific secid from the loaded page.

        Args:
            page: The Playwright page object
            secid: The section ID to extract content for

        Returns:
            The cleaned HTML content
        """
        secid_selector = f"#secid-{secid}"

        # Extract the section HTML
        section_html = await page.evaluate(
            f"""
            () => {{
                const secElement = document.querySelector('{secid_selector}');
                if (!secElement) return null;
                return secElement.outerHTML;
            }}
        """
        )

        if section_html:
            return self.clean_municode_html(section_html)
        return None

    async def _get_node_info(self, page: Page, li_id: str) -> dict[str, Any] | None:
        """
        Extract node information from the DOM.

        Args:
            page: Playwright page object
            li_id: The ID of the li element

        Returns:
            Dictionary with node information or None if failed
        """
        try:
            return await page.evaluate(
                f"""
                () => {{
                    try {{
                        const li = document.getElementById('{li_id}');
                        if (!li) return null;

                        const secid = li.id.replace('secid-x', '');

                        const contentLink = li.querySelector(':scope > a[onclick*="SelectTOC"]');
                        const titleSpan = contentLink?.querySelector('span.toc-item');
                        const title = titleSpan ? titleSpan.innerText.trim() : '';

                        const iconImg = li.querySelector(':scope > img.icon, :scope > a > img.icon');
                        const isLeaf = iconImg && iconImg.classList.contains('isLeaf');

                        const href = contentLink?.getAttribute('href') || '';
                        const baseUrl = window.location.origin;
                        const fullUrl = href ? (href.startsWith('http') ? href : baseUrl + href) : '';

                        const expander = li.querySelector(':scope > a[onclick*="ZP.TOCView.Expand"] img.expander');
                        const hasExpander = !!expander;
                        const isExpanded = expander?.src?.includes('minus_sign.gif') || false;

                        let childLis = li.querySelectorAll(':scope > ul > li[id^="secid-x"]');

                        if (childLis.length === 0) {{
                            const nextSibling = li.nextElementSibling;
                            if (nextSibling && nextSibling.tagName === 'LI') {{
                                const nestedUl = nextSibling.querySelector(':scope > ul');
                                if (nestedUl) {{
                                    childLis = nestedUl.querySelectorAll(':scope > li[id^="secid-x"]');
                                }}
                            }}
                        }}

                        const hasChildrenInDOM = childLis.length > 0;

                        return {{
                            secid,
                            title,
                            isLeaf,
                            href: fullUrl,
                            hasExpander,
                            isExpanded,
                            hasChildrenInDOM,
                            childCount: childLis.length
                        }};
                    }} catch (e) {{
                        return {{ error: e.toString() }};
                    }}
                }}
            """
            )
        except Exception as e:
            return {"error": str(e)}

    async def _expand_node_if_needed(
        self, page: Page, li_id: str, node_info: dict[str, Any], indent: str
    ) -> None:
        """
        Expand a node if it has an expander and isn't already expanded.

        Args:
            page: Playwright page object
            li_id: The ID of the li element
            node_info: Node information dictionary
            indent: Indentation string for logging
        """
        if not node_info.get("hasExpander") or node_info.get("isExpanded"):
            return

        try:
            expander_selector = (
                f'#{li_id} > a[onclick*="ZP.TOCView.Expand"] img.expander'
            )
            print(f"{indent}  → Expanding...")

            await page.click(expander_selector, timeout=5000)

            new_child_count = 0
            for attempt in range(5):
                await page.wait_for_timeout(300)

                new_child_count = await page.evaluate(
                    f"""
                    () => {{
                        const li = document.getElementById('{li_id}');
                        if (!li) return 0;

                        let directUl = li.querySelector(':scope > ul');

                        if (!directUl) {{
                            const nextSibling = li.nextElementSibling;
                            if (nextSibling && nextSibling.tagName === 'LI') {{
                                directUl = nextSibling.querySelector(':scope > ul');
                            }}
                        }}

                        if (!directUl) return 0;

                        const childLis = directUl.querySelectorAll(':scope > li[id^="secid-x"]');
                        return childLis.length;
                    }}
                """
                )

                if new_child_count > 0:
                    break

            print(f"{indent}  → Expanded ({new_child_count} children loaded)")

        except asyncio.TimeoutError:
            print(f"{indent}  ⏳ Timeout expanding")
        except Exception as e:
            print(f"{indent}  ⚠ Expand failed: {str(e)[:100]}")

    async def _get_child_ids(self, page: Page, li_id: str) -> list[str]:
        """
        Get child IDs for a node.

        Args:
            page: Playwright page object
            li_id: The ID of the li element

        Returns:
            List of child IDs
        """
        try:
            return await page.evaluate(
                f"""
                () => {{
                    try {{
                        const li = document.getElementById('{li_id}');
                        if (!li) return [];

                        let directUl = li.querySelector(':scope > ul');

                        if (!directUl) {{
                            const nextSibling = li.nextElementSibling;
                            if (nextSibling && nextSibling.tagName === 'LI') {{
                                directUl = nextSibling.querySelector(':scope > ul');
                            }}
                        }}

                        if (!directUl) return [];

                        const childLis = directUl.querySelectorAll(':scope > li[id^="secid-x"]') || [];
                        return Array.from(childLis).map(child => child.id);
                    }} catch (e) {{
                        return [];
                    }}
                }}
            """
            )
        except Exception:
            return []

    async def build_toc_structure_dfs(
        self, page: Page, li_id: str, depth: int = 0, max_depth: int = 20
    ) -> dict[str, Any] | None:
        """
        Build TOC structure using depth-first search WITHOUT scraping content.

        Args:
            page: Playwright page object
            li_id: The ID of the li element (e.g., "secid-x1")
            depth: Current depth in the tree
            max_depth: Maximum depth to prevent infinite recursion

        Returns:
            TOC entry with children
        """
        indent = "  " * depth

        if depth > max_depth:
            print(f"{indent}⚠ Max depth {max_depth} reached, stopping recursion")
            return None

        node_info = await self._get_node_info(page, li_id)

        if not node_info or node_info.get("error"):
            error = (
                node_info.get("error", "Node not found")
                if node_info
                else "Node not found"
            )
            print(f"{indent}⚠ Node {li_id} issue: {error}")
            return None

        title = node_info["title"][:70] if node_info.get("title") else "NO TITLE"
        has_children = node_info.get("hasChildrenInDOM", False) or node_info.get(
            "hasExpander", False
        )
        child_count = node_info.get("childCount", 0)

        print(f"{indent}[D{depth}] {title} (children: {child_count})")

        toc_entry = {
            "secid": node_info["secid"],
            "title": node_info["title"],
            "isLeaf": node_info["isLeaf"],
            "href": node_info["href"],
            "children": [],
        }

        await self._expand_node_if_needed(page, li_id, node_info, indent)

        try:
            child_ids = await self._get_child_ids(page, li_id)

            if child_ids:
                print(f"{indent}  → Processing {len(child_ids)} children...")

                for idx, child_id in enumerate(child_ids):
                    try:
                        child_entry = await self.build_toc_structure_dfs(
                            page, child_id, depth + 1, max_depth
                        )
                        if child_entry:
                            toc_entry["children"].append(child_entry)
                    except KeyboardInterrupt:
                        raise
                    except Exception as e:
                        print(
                            f"{indent}  ⚠ Child {idx + 1}/{len(child_ids)} failed: {str(e)[:100]}"
                        )
                        continue
            elif has_children or child_count > 0:
                print(f"{indent}  ⚠ Expected children but found none after expansion")

        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"{indent}  ⚠ Get children failed: {str(e)[:100]}")

        return toc_entry

    # Using shared flatten_toc from scraper_utils

    async def scrape_node_content(
        self, page: Page, secid: str, title: str
    ) -> str | None:
        """Scrape content for a specific node by clicking it."""
        try:
            # Click the node to load its content
            link_selector = f"a[onclick*=\"SelectTOC('{secid}'\"]"

            # Wait for network to be idle after clicking
            await page.click(link_selector, timeout=10000)

            # Wait for network idle (important for dynamic content loading)
            # Increase timeout to 30 seconds
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except Exception:
                # If networkidle times out, still wait longer
                await page.wait_for_timeout(2000)

            # Also wait for the specific content element to appear
            secid_selector = f"#secid-{secid}"
            try:
                await page.wait_for_selector(secid_selector, timeout=30000)
            except Exception:
                # Give it one more chance
                await page.wait_for_timeout(1000)

            # Scrape the content
            html_content = await self.scrape_content(page, secid)
            return html_content

        except Exception as e:
            print(f"    ⚠ Failed to scrape content for {title[:50]}: {str(e)[:100]}")
            return None

    def collect_all_nodes(
        self, hierarchical_toc: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Flatten hierarchical TOC to get all nodes in a list."""
        all_nodes = []

        def traverse(nodes: list[dict[str, Any]]) -> None:
            for node in nodes:
                all_nodes.append(node)
                if node.get("children"):
                    traverse(node["children"])

        traverse(hierarchical_toc)
        return all_nodes

    async def _get_top_level_ids(self, page: Page) -> list[str]:
        """
        Get all top-level TOC item IDs.

        Args:
            page: Playwright page object

        Returns:
            List of top-level li IDs
        """
        return await page.evaluate(
            """
            () => {
                const rootUl = document.querySelector('#toc-list ul.toc-level0');
                if (!rootUl) return [];
                const topLevelLis = rootUl.querySelectorAll(':scope > li[id^="secid-x"]');
                return Array.from(topLevelLis).map(li => li.id);
            }
        """
        )

    async def _build_hierarchical_toc(
        self, page: Page, top_level_ids: list[str]
    ) -> list[dict[str, Any]]:
        """
        Build hierarchical TOC structure from top-level IDs.

        Args:
            page: Playwright page object
            top_level_ids: List of top-level li IDs

        Returns:
            List of hierarchical TOC entries
        """
        hierarchical_toc = []

        for i, top_id in enumerate(top_level_ids, 1):
            print(f"\n[{i}/{len(top_level_ids)}] Building TOC for {top_id}...")
            try:
                entry = await self.build_toc_structure_dfs(page, top_id, depth=0)
                if entry:
                    hierarchical_toc.append(entry)
                    print(f"✓ Completed {top_id}")
                else:
                    print(f"⚠ No entry returned for {top_id}")
            except Exception as e:
                print(f"✗ ERROR processing {top_id}: {str(e)}")
                traceback.print_exc()
                print("\nContinuing to next item...")
                continue

        return hierarchical_toc

    async def _scrape_all_node_content(
        self, page: Page, all_nodes: list[dict[str, Any]]
    ) -> None:
        """
        Scrape content for all nodes.

        Args:
            page: Playwright page object
            all_nodes: List of all nodes to scrape
        """
        for i, node in enumerate(all_nodes, 1):
            try:
                print(f"[{i}/{len(all_nodes)}] Scraping: {node['title'][:60]}...")
                html_content = await self.scrape_node_content(
                    page, node["secid"], node["title"]
                )
                if html_content:
                    node["html"] = html_content
                    print(f"  ✓ {len(html_content)} chars")
                else:
                    print("  ⚠ No content found")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"  ✗ Error: {str(e)[:100]}")
                continue

    async def scrape_all_content(
        self, url: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Main scraping function using depth-first search.

        Args:
            url: URL to scrape

        Returns:
            Tuple of (hierarchical_toc, flat_toc)
        """
        async with async_playwright() as p:
            browser, page = await setup_browser_and_page_async(p)

            try:
                print(f"Navigating to {url}")
                await page.goto(url, wait_until="domcontentloaded")

                print("Waiting for TOC to load...")
                await page.wait_for_selector("#toc-list", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=10000)

                top_level_ids = await self._get_top_level_ids(page)

                print(f"\nFound {len(top_level_ids)} top-level items")
                print("Starting depth-first traversal...\n")

                print("=" * 70)
                print("STEP 1: Building TOC structure...")
                print("=" * 70)
                hierarchical_toc = await self._build_hierarchical_toc(
                    page, top_level_ids
                )

                print("\n" + "=" * 70)
                print("STEP 2: Scraping content for all nodes...")
                print("=" * 70)

                all_nodes = self.collect_all_nodes(hierarchical_toc)
                print(f"\nFound {len(all_nodes)} total nodes to scrape\n")

                await self._scrape_all_node_content(page, all_nodes)

                flat_toc = flatten_toc(hierarchical_toc)

                return hierarchical_toc, flat_toc

            except Exception as e:
                print(f"Error: {e}")
                traceback.print_exc()
                return [], []

            finally:
                await browser.close()


async def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape Municode ordinance documents")
    parser.add_argument(
        "url",
        help="URL of the Municode page to scrape (e.g., https://library.municode.com/regs/orem-ut/doc-viewer.aspx)",
    )
    parser.add_argument("name", help="Name for the output file")
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory path (default: output)",
        default="output",
    )

    args = parser.parse_args()
    output_name = args.name

    scraper = MunicodeOrdinanceScraper()

    # Scrape all content using DFS
    hierarchical_toc, flat_toc = await scraper.scrape_all_content(args.url)

    if flat_toc:
        metadata = create_output_metadata(
            url=args.url,
            output_name=output_name,
            scraper_name="encode_plus.py",
            scraper_version="2.0",
            csv_file=None,
        )

        output_path = save_scraped_output(
            sections=flat_toc,
            metadata=metadata,
            output_dir_path=args.output_dir,
            output_name=output_name,
        )

        print(f"\nSaved to: {output_path}")

        items_with_html = sum(1 for item in flat_toc if "html" in item)

        print("\n✓ Complete!")
        print(f"  Total TOC items: {len(flat_toc)}")
        print(f"  Successfully scraped: {items_with_html}/{len(flat_toc)}")
    else:
        print("Failed to extract content")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
