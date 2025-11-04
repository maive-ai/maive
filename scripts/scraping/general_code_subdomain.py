import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def clean_html_content(html_content):
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

    # Remove stylesheet links
    for link in soup.find_all("link", rel="stylesheet"):
        link.decompose()

    # Remove empty paragraphs and divs
    for tag in soup.find_all(["p", "div", "span"]):
        if not tag.get_text(strip=True) and not tag.find_all(True):
            tag.decompose()

    # Clean attributes - keep only essential ones
    for tag in soup.find_all(True):
        new_attrs = {}
        if "id" in tag.attrs:
            new_attrs["id"] = tag.attrs["id"]
        if "href" in tag.attrs:
            new_attrs["href"] = tag.attrs["href"]
        if "target" in tag.attrs:
            new_attrs["target"] = tag.attrs["target"]
        # Keep semantic mco- classes that indicate content type
        if "class" in tag.attrs:
            classes = (
                tag.attrs["class"]
                if isinstance(tag.attrs["class"], list)
                else [tag.attrs["class"]]
            )
            mco_classes = [c for c in classes if c.startswith("mco-")]
            if mco_classes:
                new_attrs["class"] = mco_classes
        tag.attrs = new_attrs

    # Convert back to string
    cleaned_html = str(soup)

    # Remove HTML comments
    cleaned_html = re.sub(r"<!--.*?-->", "", cleaned_html, flags=re.DOTALL)

    # Remove excessive whitespace
    cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html)

    return cleaned_html.strip()


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


def flatten_toc(
    nodes: List[Dict[str, Any]], parent_path: List[str] = None
) -> List[Dict[str, Any]]:
    """Flatten the nested TOC structure into a list with paths."""
    parent_path = parent_path or []
    flat_list = []

    for node in nodes:
        current_path = parent_path + [node["text"]]
        has_children = bool(node.get("children"))

        flat_list.append(
            {
                "value": node["text"],  # The text/title is the value
                "path": current_path,
                "url": node.get("url"),
                "depth": len(current_path) - 1,
                "has_children": has_children,
            }
        )

        if has_children:
            flat_list.extend(flatten_toc(node["children"], current_path))

    return flat_list


def download_content():
    """
    Download HTML content and save TOC structure.
    Only processes leaf nodes (items without children).
    """
    import sys

    # Check command line arguments
    if len(sys.argv) < 3:
        print("Usage: python scrape_and_merge.py <URL> <NAME> [--output-dir DIR]")
        print(
            "Example: python scrape_and_merge.py https://library.municode.com/ut/parkcity/codes/code_of_ordinances parkcity"
        )
        return

    base_url = sys.argv[1]
    output_name = sys.argv[2]

    # Parse optional output directory
    output_dir_path = "output"
    if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
        if len(sys.argv) > 4:
            output_dir_path = sys.argv[4]

    print(f"Using URL: {base_url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    hierarchical_toc = None
    flat_toc = None
    leaf_nodes = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set to True for production
        context = browser.new_context()
        page = context.new_page()

        print(f"Navigating to {base_url} to extract TOC...")
        page.goto(base_url, wait_until="networkidle", timeout=60000)

        # Click the Contents button to open the modal
        print("Opening Contents modal...")
        page.click('a.nav-link[data-target="#contents"]')
        page.wait_for_timeout(1000)

        # Wait for TOC to load (can take a while on some sites)
        print("Waiting for TOC to load (this may take up to 60 seconds)...")
        page.wait_for_selector('.contents-toc li[role="treeitem"]', timeout=60000)

        # Click the "Expand All" button
        print("Clicking Expand All button...")
        page.click("button.contents-expand")
        page.wait_for_timeout(2000)

        # Extract the TOC structure
        print("Extracting TOC structure...")
        toc_data = extract_toc_structure(page)

        if "error" in toc_data:
            print(f"Error: {toc_data['error']}")
            browser.close()
            return

        hierarchical_toc = toc_data["items"]
        print(f"Found {toc_data['totalItems']} total items in TOC")

        # Flatten the TOC
        flat_toc = flatten_toc(hierarchical_toc)

        # Filter to only leaf nodes
        leaf_nodes = [item for item in flat_toc if not item.get("has_children", False)]
        print(f"Found {len(leaf_nodes)} leaf nodes to scrape HTML")

        # Now scrape HTML for each leaf node
        for i, item in enumerate(leaf_nodes):
            identifier = item.get("url", "").split("/")[-1]
            page_url = item["url"]

            try:
                # Find the specific article by id matching the identifier
                article_selector = f'article[id="{identifier}"]'

                # Check if article exists on current page first
                if page.locator(article_selector).count() > 0:
                    content_html = page.locator(article_selector).evaluate(
                        "el => el.outerHTML"
                    )
                    print(
                        f"  ✓ {i + 1}/{len(leaf_nodes)}: Found on current page - {item['value']}"
                    )
                else:
                    # Navigate to the page to find the article
                    print(f"  → {i + 1}/{len(leaf_nodes)}: Navigating to {page_url}")
                    page.goto(page_url, wait_until="networkidle", timeout=60000)
                    page.wait_for_selector("article", timeout=60000)

                    # Try to find the specific article again
                    if page.locator(article_selector).count() > 0:
                        content_html = page.locator(article_selector).evaluate(
                            "el => el.outerHTML"
                        )
                        print(
                            f"  ✓ {i + 1}/{len(leaf_nodes)}: Found after navigation - {item['value']}"
                        )
                    else:
                        # Fallback: get the first article if specific one not found
                        content_html = page.locator("article").first.evaluate(
                            "el => el.outerHTML"
                        )
                        print(
                            f"  ✓ {i + 1}/{len(leaf_nodes)}: Using fallback - {item['value']}"
                        )

                # Clean the HTML
                cleaned_html = clean_html_content(content_html)

                # Add the HTML to the item
                item["html"] = cleaned_html

                # Add a small delay to be respectful to the server
                time.sleep(0.5)

            except Exception as e:
                print(f"  ✗ {i + 1}/{len(leaf_nodes)}: {item['value'][:80]} - {str(e)}")

                # Add error information to the item
                item["html_error"] = str(e)

        browser.close()

    # Create output directory if it doesn't exist
    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with date and name
    date_str = datetime.now().strftime("%m-%d-%Y")
    output_filename = f"{date_str}_{output_name}.json"
    output_path = output_dir / output_filename

    # Save only the flattened TOC with HTML content
    if flat_toc:
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
    print(f"  Total TOC items: {len(flat_toc) if flat_toc else 0}")
    print(f"  Leaf nodes (with HTML): {total_leaf_nodes}")

    print(f"  Successfully scraped HTML: {items_with_html}/{total_leaf_nodes}")
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
            print(f"    - {item.get('value', 'Unknown')}")
        if len(missing_html) > 5:
            print(f"    ... and {len(missing_html) - 5} more")


if __name__ == "__main__":
    download_content()
