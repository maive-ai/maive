"""
Scraper for Municode ordinance documents.
Extracts table of contents and content for each section using depth-first search.
"""

import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright


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

    async def build_toc_structure_dfs(
        self, page: Page, li_id: str, depth: int = 0, max_depth: int = 20
    ) -> dict[str, Any] | None:
        """
        Build TOC structure using depth-first search WITHOUT scraping content.
        Just expands nodes and records the hierarchy.

        Args:
            page: Playwright page object
            li_id: The ID of the li element (e.g., "secid-x1")
            depth: Current depth in the tree
            max_depth: Maximum depth to prevent infinite recursion

        Returns:
            TOC entry with children
        """
        indent = "  " * depth

        # Safety check for max depth
        if depth > max_depth:
            print(f"{indent}⚠ Max depth {max_depth} reached, stopping recursion")
            return None

        # Get node info
        try:
            node_info = await page.evaluate(
                f"""
                () => {{
                    try {{
                        const li = document.getElementById('{li_id}');
                        if (!li) return null;

                        const secid = li.id.replace('secid-x', '');

                        // Get title
                        const contentLink = li.querySelector(':scope > a[onclick*="SelectTOC"]');
                        const titleSpan = contentLink?.querySelector('span.toc-item');
                        const title = titleSpan ? titleSpan.innerText.trim() : '';

                        // Check if it's a leaf
                        const iconImg = li.querySelector(':scope > img.icon, :scope > a > img.icon');
                        const isLeaf = iconImg && iconImg.classList.contains('isLeaf');

                        // Get href
                        const href = contentLink?.getAttribute('href') || '';

                        // Check if it has an expander
                        const expander = li.querySelector(':scope > a[onclick*="ZP.TOCView.Expand"] img.expander');
                        const hasExpander = !!expander;
                        const isExpanded = expander?.src?.includes('minus_sign.gif') || false;

                        // Check if it has children in the DOM (even if not expanded)
                        // Children can be in ':scope > ul' OR in the next sibling li that contains a ul
                        let childLis = li.querySelectorAll(':scope > ul > li[id^="secid-x"]');

                        // Also check next sibling for nested ul (Municode structure)
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
                            href,
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
            print(f"{indent}⚠ JS evaluation failed for {li_id}: {str(e)[:100]}")
            return None

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

        # Create TOC entry
        toc_entry = {
            "secid": node_info["secid"],
            "title": node_info["title"],
            "isLeaf": node_info["isLeaf"],
            "href": node_info["href"],
            "children": [],
        }

        # If this node has an expander and isn't expanded, expand it first
        if node_info.get("hasExpander") and not node_info.get("isExpanded"):
            try:
                expander_selector = (
                    f'#{li_id} > a[onclick*="ZP.TOCView.Expand"] img.expander'
                )
                print(f"{indent}  → Expanding...")

                # Click the expander
                await page.click(expander_selector, timeout=5000)

                # Wait for children to appear in the DOM
                # Try multiple times with increasing waits
                new_child_count = 0
                for attempt in range(5):
                    await page.wait_for_timeout(300)

                    new_child_count = await page.evaluate(
                        f"""
                        () => {{
                            const li = document.getElementById('{li_id}');
                            if (!li) return 0;

                            // Look for direct children
                            let directUl = li.querySelector(':scope > ul');

                            // Also check next sibling for nested ul (Municode structure)
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

        # Always check for children (might have been loaded after expansion)
        try:
            # Get child IDs
            child_ids = await page.evaluate(
                f"""
                () => {{
                    try {{
                        const li = document.getElementById('{li_id}');
                        if (!li) return [];

                        // Look for direct ul child first
                        let directUl = li.querySelector(':scope > ul');

                        // Also check next sibling for nested ul (Municode structure)
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

            if child_ids and len(child_ids) > 0:
                print(f"{indent}  → Processing {len(child_ids)} children...")

                # Process each child recursively
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

    def flatten_toc(
        self, nodes: list[dict[str, Any]], parent_path: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Flatten the nested TOC structure into a list with paths."""
        if parent_path is None:
            parent_path = []

        flat_list = []

        for node in nodes:
            current_path = parent_path + [node["title"]]

            flat_item = {
                "value": node["title"],
                "path": current_path,
                "url": node.get("href"),
                "depth": len(current_path) - 1,
                "has_children": len(node.get("children", [])) > 0,
            }

            # Copy HTML content if it exists
            if "html" in node:
                flat_item["html"] = node["html"]

            flat_list.append(flat_item)

            # Recursively process children
            if node.get("children"):
                flat_list.extend(self.flatten_toc(node["children"], current_path))

        return flat_list

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

    async def scrape_all_content(
        self, url: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Main scraping function using depth-first search."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            page = await browser.new_page()

            try:
                print(f"Navigating to {url}")
                await page.goto(url, wait_until="domcontentloaded")

                # Wait for TOC to load
                print("Waiting for TOC to load...")
                await page.wait_for_selector("#toc-list", timeout=60000)
                await page.wait_for_load_state("networkidle", timeout=10000)

                # Get all top-level li elements
                top_level_ids = await page.evaluate(
                    """
                    () => {
                        const rootUl = document.querySelector('#toc-list ul.toc-level0');
                        if (!rootUl) return [];
                        const topLevelLis = rootUl.querySelectorAll(':scope > li[id^="secid-x"]');
                        return Array.from(topLevelLis).map(li => li.id);
                    }
                """
                )

                print(f"\nFound {len(top_level_ids)} top-level items")
                print("Starting depth-first traversal...\n")

                # STEP 1: Build TOC structure first (no content scraping)
                print("=" * 70)
                print("STEP 1: Building TOC structure...")
                print("=" * 70)
                hierarchical_toc = []
                for i, top_id in enumerate(top_level_ids, 1):
                    print(f"\n[{i}/{len(top_level_ids)}] Building TOC for {top_id}...")
                    try:
                        entry = await self.build_toc_structure_dfs(
                            page, top_id, depth=0
                        )
                        if entry:
                            hierarchical_toc.append(entry)
                            print(f"✓ Completed {top_id}")
                        else:
                            print(f"⚠ No entry returned for {top_id}")
                    except Exception as e:
                        print(f"✗ ERROR processing {top_id}: {str(e)}")
                        import traceback

                        traceback.print_exc()
                        print("\nContinuing to next item...")
                        continue

                # STEP 2: Scrape content for all nodes
                print("\n" + "=" * 70)
                print("STEP 2: Scraping content for all nodes...")
                print("=" * 70)

                all_nodes = self.collect_all_nodes(hierarchical_toc)
                print(f"\nFound {len(all_nodes)} total nodes to scrape\n")

                for i, node in enumerate(all_nodes, 1):
                    try:
                        print(
                            f"[{i}/{len(all_nodes)}] Scraping: {node['title'][:60]}..."
                        )
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

                # Flatten the TOC
                flat_toc = self.flatten_toc(hierarchical_toc)

                return hierarchical_toc, flat_toc

            except Exception as e:
                print(f"Error: {e}")
                import traceback

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
        # Create output directory
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with date
        date_str = datetime.now().strftime("%m-%d-%Y")
        output_filename = f"{date_str}_{output_name}.json"
        output_path = output_dir / output_filename

        # Save flattened TOC with HTML content
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(flat_toc, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {output_path}")

        # Report statistics
        items_with_html = sum(1 for item in flat_toc if "html" in item)

        print("\n✓ Complete!")
        print(f"  Total TOC items: {len(flat_toc)}")
        print(f"  Successfully scraped: {items_with_html}/{len(flat_toc)}")
    else:
        print("Failed to extract content")
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
