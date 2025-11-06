"""
Scraper for ecode360.com (React/Material-UI interface)
Clicks chapters and parses individual section content from the returned HTML.
For URLs like: https://ecode360.com/HU4729
"""

import json
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def clean_html_content(html_content):
    """Clean HTML content to remove unnecessary elements and attributes."""
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
        tag.attrs = new_attrs

    # Convert back to string
    cleaned_html = str(soup)
    cleaned_html = re.sub(r"<!--.*?-->", "", cleaned_html, flags=re.DOTALL)
    cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html)

    return cleaned_html.strip()


def expand_all_toc_nodes(page):
    """Expand all collapsed nodes in the Material-UI TreeView."""
    print("Expanding all TOC nodes...")
    round_num = 0
    total_expanded = 0
    max_rounds = 20

    while round_num < max_rounds:
        round_num += 1

        collapsed_count = page.evaluate("""
            () => {
                const treeItems = document.querySelectorAll('.MuiTreeItem-root[aria-expanded="false"]');
                return treeItems.length;
            }
        """)

        if collapsed_count == 0:
            print(f"  ✓ All nodes expanded after {round_num} rounds")
            break

        print(f"  Round {round_num}: Found {collapsed_count} collapsed nodes")

        page.evaluate("""
            () => {
                const collapsedItems = document.querySelectorAll('.MuiTreeItem-root[aria-expanded="false"]');
                collapsedItems.forEach(item => {
                    const iconContainer = item.querySelector('.MuiTreeItem-iconContainer');
                    if (iconContainer) {
                        iconContainer.click();
                    }
                });
            }
        """)

        # Longer delay to avoid bot detection
        page.wait_for_timeout(1000 + random.randint(200, 500))
        total_expanded += collapsed_count

    print(f"  Total expansions: {total_expanded}")
    return total_expanded


def extract_toc_structure(page):
    """Extract the hierarchical TOC structure from the Material-UI TreeView."""
    return page.evaluate("""
        () => {
            const treeView = document.querySelector('.MuiTreeView-root.toc-tree-widget');
            if (!treeView) {
                return { items: [], totalItems: 0 };
            }

            const allTreeItems = treeView.querySelectorAll('.MuiTreeItem-root');
            const flatItems = [];

            allTreeItems.forEach(item => {
                const labelContent = item.querySelector(':scope > .MuiTreeItem-content .MuiTreeItem-label');
                if (!labelContent) return;

                const prefixEl = labelContent.querySelector('.toc-label-prefix');
                const textEl = labelContent.querySelector('.toc-label-text');
                const prefix = prefixEl?.textContent?.trim() || '';
                const text = textEl?.textContent?.trim() || '';
                const fullText = prefix && text ? `${prefix} ${text}` : (prefix || text);

                const prefixClasses = prefixEl?.className || '';
                const levelMatch = prefixClasses.match(/toc-label-prefix-(\\d+)/);
                const level = levelMatch ? parseInt(levelMatch[1]) : 0;

                const isExpandable = item.getAttribute('aria-expanded') !== null;

                flatItems.push({
                    text: fullText,
                    level: level,
                    isExpandable: isExpandable
                });
            });

            function buildHierarchy(flatList) {
                const result = [];
                const stack = [{ children: result, level: -1 }];

                flatList.forEach(item => {
                    while (stack.length > 1 && stack[stack.length - 1].level >= item.level) {
                        stack.pop();
                    }

                    const node = {
                        text: item.text,
                        children: []
                    };

                    stack[stack.length - 1].children.push(node);

                    if (item.isExpandable) {
                        stack.push({ ...node, level: item.level });
                    }
                });

                return result;
            }

            return {
                items: buildHierarchy(flatItems),
                totalItems: allTreeItems.length
            };
        }
    """)


def extract_toc_with_section_ids(page):
    """Extract TOC structure with section IDs from href attributes."""
    return page.evaluate("""
        () => {
            const treeView = document.querySelector('.MuiTreeView-root.toc-tree-widget');
            if (!treeView) {
                return { items: [], totalItems: 0 };
            }

            const allTreeItems = treeView.querySelectorAll('.MuiTreeItem-root');
            const flatItems = [];

            allTreeItems.forEach(item => {
                const labelContent = item.querySelector(':scope > .MuiTreeItem-content .MuiTreeItem-label');
                if (!labelContent) return;

                const prefixEl = labelContent.querySelector('.toc-label-prefix');
                const textEl = labelContent.querySelector('.toc-label-text');
                const prefix = prefixEl?.textContent?.trim() || '';
                const text = textEl?.textContent?.trim() || '';
                const fullText = prefix && text ? `${prefix} ${text}` : (prefix || text);

                const prefixClasses = prefixEl?.className || '';
                const levelMatch = prefixClasses.match(/toc-label-prefix-(\\d+)/);
                const level = levelMatch ? parseInt(levelMatch[1]) : 0;

                const link = labelContent.querySelector('a');
                const href = link?.getAttribute('href');

                // Extract section ID from href (e.g., "#47329488")
                let sectionId = null;
                if (href && href.startsWith('#')) {
                    sectionId = href.substring(1);
                }

                const isExpandable = item.getAttribute('aria-expanded') !== null;

                flatItems.push({
                    text: fullText,
                    level: level,
                    isExpandable: isExpandable,
                    sectionId: sectionId
                });
            });

            // Build hierarchy
            function buildHierarchy(flatList) {
                const result = [];
                const stack = [{ children: result, level: -1 }];

                flatList.forEach(item => {
                    while (stack.length > 1 && stack[stack.length - 1].level >= item.level) {
                        stack.pop();
                    }

                    const node = {
                        text: item.text,
                        sectionId: item.sectionId,
                        children: []
                    };

                    stack[stack.length - 1].children.push(node);

                    if (item.isExpandable) {
                        stack.push({ ...node, level: item.level });
                    }
                });

                return result;
            }

            return {
                items: buildHierarchy(flatItems),
                totalItems: allTreeItems.length
            };
        }
    """)


def flatten_toc(nodes: List[Dict[str, Any]], parent_path: List[str] = None) -> List[Dict[str, Any]]:
    """Flatten the nested TOC structure into a list with paths."""
    parent_path = parent_path or []
    flat_list = []

    for node in nodes:
        current_path = parent_path + [node["text"]]
        has_children = bool(node.get("children"))

        flat_list.append({
            "value": node["text"],
            "path": current_path,
            "url": None,  # We don't use URLs in this scraper
            "depth": len(current_path) - 1,
            "has_children": has_children,
        })

        if has_children:
            flat_list.extend(flatten_toc(node["children"], current_path))

    return flat_list


def parse_sections_from_html(html_content: str) -> Dict[str, str]:
    """
    Parse individual sections from chapter HTML.
    Returns dict mapping section_id -> cleaned HTML for that section.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    sections = {}

    # Find all divs that look like section headers (have numeric IDs)
    for div in soup.find_all("div", id=True):
        section_id = div.get("id")

        # Skip if not a numeric ID (section IDs are numeric)
        if not section_id or not section_id.isdigit():
            continue

        # Find the corresponding content div
        content_id = f"{section_id}_content"
        content_div = soup.find("div", id=content_id)

        # Create a container with both the header and content
        container = BeautifulSoup("<div></div>", "html.parser").div
        container.append(div.__copy__())
        if content_div:
            container.append(content_div.__copy__())

        # Clean and store
        section_html = clean_html_content(str(container))
        sections[section_id] = section_html

    return sections


def scrape_single_jurisdiction(url: str, output_name: str, output_dir_path: str = "output"):
    """Scrape HTML content from a single jurisdiction's code."""
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        # Use realistic browser context to avoid bot detection
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print(f"\nNavigating to {url}...")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Wait for TOC widget - with extra delay to avoid bot detection
        print("Waiting for TOC widget to load...")
        page.wait_for_selector("#code-toc-widget", timeout=60000)
        page.wait_for_selector(".MuiTreeView-root.toc-tree-widget", timeout=60000)
        page.wait_for_timeout(3000 + random.randint(500, 1500))

        # Expand all nodes
        expand_all_toc_nodes(page)

        # Extract TOC structure
        print("\nExtracting TOC structure...")
        toc_data = extract_toc_structure(page)

        if "error" in toc_data:
            print(f"Error: {toc_data['error']}")
            browser.close()
            return

        hierarchical_toc = toc_data["items"]
        print(f"Found {toc_data['totalItems']} total items in TOC")

        # Flatten the TOC
        flat_toc = flatten_toc(hierarchical_toc)

        # Find chapters (depth 2 items with children)
        chapters = [item for item in flat_toc if item.get("has_children") and item["depth"] == 2]
        print(f"Found {len(chapters)} chapters to scrape\n")

        # Scrape each chapter
        print("Scraping chapters...")
        chapter_sections_map = {}  # Maps section_id -> HTML

        for i, chapter in enumerate(chapters):
            chapter_text = chapter["value"]

            try:
                # Click the chapter in TOC
                clicked = page.evaluate("""
                    (chapterText) => {
                        const allLabels = document.querySelectorAll('.MuiTreeItem-label');
                        for (let label of allLabels) {
                            const prefix = label.querySelector('.toc-label-prefix')?.textContent?.trim() || '';
                            const text = label.querySelector('.toc-label-text')?.textContent?.trim() || '';
                            const fullText = prefix && text ? `${prefix} ${text}` : (prefix || text);

                            if (fullText === chapterText) {
                                label.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """, chapter_text)

                if not clicked:
                    print(f"  ✗ {i + 1}/{len(chapters)}: Could not click - {chapter_text[:60]}")
                    continue

                # Wait for content to load - longer delay to avoid bot detection
                page.wait_for_timeout(2000 + random.randint(500, 1500))

                # Extract entire #childContent
                content_html = page.evaluate("""
                    () => {
                        const contentDiv = document.getElementById('childContent');
                        return contentDiv ? contentDiv.outerHTML : null;
                    }
                """)

                if content_html:
                    # Parse individual sections from the chapter HTML
                    sections = parse_sections_from_html(content_html)
                    # Store sections with chapter reference
                    for section_id, section_html in sections.items():
                        chapter_sections_map[section_id] = {
                            "html": section_html,
                            "chapter": chapter_text
                        }
                    print(f"  ✓ {i + 1}/{len(chapters)}: {chapter_text[:60]} ({len(sections)} sections)")
                else:
                    print(f"  ✗ {i + 1}/{len(chapters)}: No content - {chapter_text[:60]}")

                # Longer delay between chapters to avoid bot detection
                time.sleep(1.5 + random.uniform(0.5, 2.0))

            except Exception as e:
                print(f"  ✗ {i + 1}/{len(chapters)}: {chapter_text[:60]} - {str(e)}")

        browser.close()

        # Assign scraped HTML to TOC items by matching chapter structure
        print(f"\nAssigning scraped content to {len(flat_toc)} TOC items...")
        print(f"  Scraped sections in map: {len(chapter_sections_map)}")

        # Group TOC items by chapter
        matches = 0
        for chapter in chapters:
            chapter_text = chapter["value"]

            # Find all leaf sections under this chapter
            chapter_sections = []
            in_chapter = False
            chapter_depth = chapter["depth"]

            for item in flat_toc:
                # Check if this is our chapter
                if item["value"] == chapter_text and item["depth"] == chapter_depth:
                    in_chapter = True
                    continue

                # If we're in the chapter and hit another chapter at same depth, stop
                if in_chapter and item["depth"] <= chapter_depth:
                    break

                # Collect leaf sections in this chapter
                if in_chapter and not item.get("has_children"):
                    chapter_sections.append(item)

            # Get scraped sections for this chapter
            scraped_for_chapter = {
                sid: data for sid, data in chapter_sections_map.items()
                if data["chapter"] == chapter_text
            }

            # Assign by order (since we don't have IDs in TOC)
            if len(scraped_for_chapter) > 0:
                section_htmls = [data["html"] for data in scraped_for_chapter.values()]
                for i, toc_section in enumerate(chapter_sections):
                    if i < len(section_htmls):
                        toc_section["html"] = section_htmls[i]
                        matches += 1
                    else:
                        toc_section["html_error"] = "No matching scraped content"

        # Mark remaining leaf nodes without content
        for item in flat_toc:
            if not item.get("has_children") and "html" not in item and "html_error" not in item:
                item["html_error"] = "Section content not found"

        print(f"  Successful matches: {matches}")

        # Create output
        output_dir = Path(output_dir_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_filename = f"{output_name}.json"
        output_path = output_dir / output_filename

        scraped_at = datetime.now().isoformat()
        output_data = {
            "metadata": {
                "scraped_at": scraped_at,
                "city_slug": output_name,
                "source_url": url,
                "scraper": "ecode360.py",
                "scraper_version": "1.0"
            },
            "sections": flat_toc
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {output_path}")

        # Report statistics
        items_with_html = sum(1 for item in flat_toc if "html" in item)
        items_with_errors = sum(1 for item in flat_toc if "html_error" in item)
        total_leaf_nodes = sum(1 for item in flat_toc if not item.get("has_children", False))

        print("\n✓ Complete!")
        print(f"  Total TOC items: {len(flat_toc)}")
        print(f"  Leaf nodes: {total_leaf_nodes}")
        print(f"  Successfully scraped: {items_with_html}/{total_leaf_nodes}")
        if items_with_errors > 0:
            print(f"  Errors: {items_with_errors}")


def scrape_from_csv(csv_path: str, output_dir_path: str = "output"):
    """Scrape multiple jurisdictions from a CSV file."""
    import csv

    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return

    jurisdictions = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('status') == 'ready' and row.get('code_url'):
                jurisdictions.append(row)

    if not jurisdictions:
        print(f"Error: No ready jurisdictions found in {csv_path}")
        return

    print(f"\n{'='*60}")
    print(f"BATCH SCRAPING MODE")
    print(f"{'='*60}")
    print(f"CSV file: {csv_path}")
    print(f"Found {len(jurisdictions)} jurisdictions to scrape")
    print(f"Output directory: {output_dir_path}")
    print(f"{'='*60}\n")

    for i, juris in enumerate(jurisdictions, 1):
        print(f"\n{'='*60}")
        print(f"[{i}/{len(jurisdictions)}] Scraping: {juris['name']}")
        print(f"{'='*60}")

        try:
            scrape_single_jurisdiction(
                url=juris['code_url'],
                output_name=juris['slug'],
                output_dir_path=output_dir_path
            )
            print(f"✓ Completed: {juris['name']}")
        except Exception as e:
            print(f"✗ Failed: {juris['name']}")
            print(f"  Error: {str(e)}")

    print(f"\n{'='*60}")
    print(f"BATCH SCRAPING COMPLETE")
    print(f"Processed {len(jurisdictions)} jurisdictions")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "--csv":
        if len(sys.argv) < 3:
            print("Usage: python ecode360.py --csv <CSV_FILE> [--output-dir DIR]")
            print("Example: python ecode360.py --csv ut_ecode360.csv --output-dir output")
            sys.exit(1)

        csv_path = sys.argv[2]
        output_dir_path = "output"
        if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
            if len(sys.argv) > 4:
                output_dir_path = sys.argv[4]

        scrape_from_csv(csv_path, output_dir_path)

    elif len(sys.argv) >= 3:
        url = sys.argv[1]
        output_name = sys.argv[2]
        output_dir_path = "output"
        if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
            if len(sys.argv) > 4:
                output_dir_path = sys.argv[4]

        scrape_single_jurisdiction(url, output_name, output_dir_path)

    else:
        print("Usage:")
        print("  Single mode:  python ecode360.py <URL> <NAME> [--output-dir DIR]")
        print("  Batch mode:   python ecode360.py --csv <CSV_FILE> [--output-dir DIR]")
        print()
        print("Examples:")
        print("  python ecode360.py https://ecode360.com/HU4729 huntington")
        print("  python ecode360.py --csv ut_ecode360.csv --output-dir output/codes/ut")
        sys.exit(1)
