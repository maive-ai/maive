"""
Scraper for ecode360.com (React/Material-UI interface)
Clicks chapters and parses individual section content from the returned HTML.
For URLs like: https://ecode360.com/HU4729
"""

import random
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_utils import (
    clean_html_content,
    create_output_metadata,
    flatten_toc,
    parse_scraper_cli_args,
    read_municipalities_from_csv,
    save_scraped_output,
    setup_browser_and_page,
)

# Using shared clean_html_content from scraper_utils


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

        # Short delay for expansion to complete
        page.wait_for_timeout(300)
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


# Using shared flatten_toc from scraper_utils


def parse_sections_from_html(html_content: str) -> Dict[str, str]:
    """
    Parse individual sections from chapter HTML.
    Returns dict mapping section_number -> cleaned HTML for that section.
    Handles subsections by merging them with their parent section.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    sections = {}
    current_section_number = None
    current_section_parts = []

    # Find all divs that look like section headers (have numeric IDs)
    all_section_divs = [
        div for div in soup.find_all("div", id=True) if div.get("id", "").isdigit()
    ]

    # Track which div IDs are nested inside content divs to avoid duplicates
    nested_div_ids = set()
    for div in all_section_divs:
        content_id = f"{div.get('id')}_content"
        content_div = soup.find("div", id=content_id)
        if content_div:
            # Find all nested divs with numeric IDs inside this content div
            nested_divs = content_div.find_all("div", id=True)
            for nested_div in nested_divs:
                nested_id = nested_div.get("id")
                if nested_id and nested_id.isdigit():
                    nested_div_ids.add(nested_id)

    # Filter out nested divs to avoid duplicates
    section_divs = [
        div for div in all_section_divs if div.get("id") not in nested_div_ids
    ]

    for div in section_divs:
        section_id = div.get("id")

        # Find the corresponding content div
        content_id = f"{section_id}_content"
        content_div = soup.find("div", id=content_id)

        # Create a container with both the header and content using BeautifulSoup
        container = soup.new_tag("div")
        container.append(div.__copy__())
        if content_div:
            container.append(content_div.__copy__())

        # Extract section number from the HTML text (e.g., "Section 105.010")
        section_text = div.get_text()
        section_number = extract_section_number(section_text)

        if section_number:
            # This is a new section with a section number
            # Save the previous section if any
            if current_section_number and current_section_parts:
                combined_html = "".join(current_section_parts)
                sections[current_section_number] = clean_html_content(combined_html)

            # Start new section
            current_section_number = section_number
            current_section_parts = [str(container)]
        else:
            # This is a subsection without a section number (shouldn't happen after filtering)
            # Append to current section if we have one
            if current_section_number:
                current_section_parts.append(str(container))
            # else: orphan subsection, ignore it

    # Don't forget the last section
    if current_section_number and current_section_parts:
        combined_html = "".join(current_section_parts)
        sections[current_section_number] = clean_html_content(combined_html)

    return sections


def extract_section_number(text: str) -> str:
    """Extract section number from text like 'Section 105.010' or '§ 123-45'."""
    import re

    # Try common patterns
    patterns = [
        r"Section\s+([\d.-]+)",  # "Section 105.010"
        r"§\s*(\d+[-.\d]+)",  # "§ 123-45" or "§ 123.45"
        r"Sec\.\s*([\d.-]+)",  # "Sec. 123.45"
        r"^([\d.-]+)\s",  # "123.45 Title"
        r"(\d+[-.\d]+)",  # Any number pattern as fallback
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return None


def _check_cloudflare(page) -> bool:
    """Check if Cloudflare challenge is present."""
    return page.evaluate("""
        () => {
            const title = document.title.toLowerCase();
            const body = document.body.innerText.toLowerCase();
            return title.includes('just a moment') ||
                   body.includes('checking your browser') ||
                   body.includes('cloudflare') ||
                   document.querySelector('#challenge-form') !== null;
        }
    """)


def _wait_for_cloudflare(page) -> bool:
    """Wait for Cloudflare challenge to resolve. Returns True if successful."""
    try:
        page.wait_for_selector("#code-toc-widget", timeout=30000)
        print("✓ Cloudflare challenge passed!")
        return True
    except Exception:
        print("✗ Cloudflare challenge did not resolve. Exiting.")
        return False


def _click_chapter_node(page, chapter_text: str, debug: bool = False) -> Dict[str, Any]:
    """Click a chapter node in the TOC. Returns result dict with success status."""
    return page.evaluate(
        """
        ({chapterText, debug}) => {
            const allLabels = document.querySelectorAll('.MuiTreeItem-label');

            if (debug) {
                console.log(`Found ${allLabels.length} labels`);
                for (let i = 0; i < Math.min(3, allLabels.length); i++) {
                    const label = allLabels[i];
                    const prefix = label.querySelector('.toc-label-prefix')?.textContent?.trim() || '';
                    const text = label.querySelector('.toc-label-text')?.textContent?.trim() || '';
                    const fullText = label.textContent?.trim() || '';
                    console.log(`  Label ${i}: prefix='${prefix}' text='${text}' fullText='${fullText}'`);
                }
            }

            for (let label of allLabels) {
                const prefix = label.querySelector('.toc-label-prefix')?.textContent?.trim() || '';
                const text = label.querySelector('.toc-label-text')?.textContent?.trim() || '';
                const fullText = prefix && text ? `${prefix} ${text}` : (prefix || text);

                if (fullText === chapterText) {
                    label.click();
                    return {success: true, method: 'prefix+text', matched: fullText};
                }
            }

            for (let label of allLabels) {
                if (label.textContent?.trim() === chapterText) {
                    label.click();
                    return {success: true, method: 'direct', matched: label.textContent.trim()};
                }
            }

            const samples = [];
            for (let i = 0; i < Math.min(5, allLabels.length); i++) {
                samples.push(allLabels[i].textContent?.trim());
            }

            return {success: false, samples: samples, totalLabels: allLabels.length};
        }
    """,
        {"chapterText": chapter_text, "debug": debug},
    )


def _get_content_hash(page) -> str | None:
    """Get hash of current content to detect changes."""
    return page.evaluate("""
        () => {
            const contentDiv = document.getElementById('childContent');
            if (!contentDiv) return null;
            return contentDiv.innerHTML.substring(0, 200);
        }
    """)


def _extract_chapter_content(page) -> str | None:
    """Extract HTML content from the current chapter."""
    return page.evaluate("""
        () => {
            const contentDiv = document.getElementById('childContent');
            return contentDiv ? contentDiv.outerHTML : null;
        }
    """)


def _scrape_chapter(
    page, chapter: Dict[str, Any], index: int, total: int, debug: bool = False
) -> Dict[str, str] | None:
    """
    Scrape a single chapter, returning sections dict or None if failed.

    Returns:
        Dict mapping section_id -> HTML, or None if scraping failed
    """
    chapter_text = chapter["value"]

    try:
        if index > 0 and index % 10 == 0:
            if _check_cloudflare(page):
                print(
                    f"\n⚠️  Cloudflare challenge detected at chapter {index}. Waiting..."
                )
                if not _wait_for_cloudflare(page):
                    return None

        content_before = _get_content_hash(page)
        content_html = None
        max_click_attempts = 3

        for attempt in range(max_click_attempts):
            if debug and attempt > 0:
                print(f"\n  DEBUG: Retry attempt {attempt + 1} for: '{chapter_text}'")
            elif debug:
                print(f"\n  DEBUG: Attempting to click chapter: '{chapter_text}'")

            clicked_result = _click_chapter_node(page, chapter_text, debug)

            if not clicked_result["success"]:
                break

            if debug:
                print(
                    f"    DEBUG: Clicked successfully using {clicked_result['method']} method"
                )

            page.wait_for_timeout(500 + random.randint(0, 300))

            content_after = _get_content_hash(page)

            if content_after != content_before:
                if debug:
                    print("    DEBUG: Content changed after click")
                content_html = _extract_chapter_content(page)
                break
            elif debug:
                print("    DEBUG: Content did NOT change, will retry...")

        if not clicked_result or not clicked_result["success"]:
            if debug:
                print(
                    f"    DEBUG: Failed to click. Found {clicked_result.get('totalLabels', 0) if clicked_result else 0} labels."
                )
                if clicked_result:
                    print(
                        f"    DEBUG: Sample labels: {clicked_result.get('samples', [])[:3]}"
                    )
            print(f"  ✗ {index + 1}/{total}: Could not click - {chapter_text[:60]}")
            return None

        if content_html:
            sections = parse_sections_from_html(content_html)
            print(
                f"  ✓ {index + 1}/{total}: {chapter_text[:60]} ({len(sections)} sections)"
            )
            return sections
        else:
            print(f"  ✗ {index + 1}/{total}: No content - {chapter_text[:60]}")
            return None

    except Exception as e:
        print(f"  ✗ {index + 1}/{total}: {chapter_text[:60]} - {str(e)}")
        return None


def _scrape_all_chapters(
    page, clickable_nodes: List[Dict[str, Any]], debug: bool = False
) -> Dict[str, Dict[str, str]]:
    """
    Scrape all clickable chapters.

    Returns:
        Dict mapping section_id -> {"html": ..., "chapter": ...}
    """
    chapter_sections_map = {}

    print("Scraping clickable nodes...")
    for i, chapter in enumerate(clickable_nodes):
        sections = _scrape_chapter(page, chapter, i, len(clickable_nodes), debug)

        if sections:
            for section_id, section_html in sections.items():
                chapter_sections_map[section_id] = {
                    "html": section_html,
                    "chapter": chapter["value"],
                }

        time.sleep(3.0 + random.uniform(0, 2.0))

    return chapter_sections_map


def _match_sections_by_number(
    flat_toc: List[Dict[str, Any]], chapter_sections_map: Dict[str, Dict[str, str]]
) -> int:
    """
    Match scraped sections to TOC items by section number (first pass).

    Args:
        flat_toc: Flattened TOC list
        chapter_sections_map: Dict mapping section_id -> {"html": ..., "chapter": ...}

    Returns:
        Number of sections matched
    """
    matched_count = 0

    for item in flat_toc:
        if item.get("has_children"):
            continue

        toc_section_number = extract_section_number(item["value"])

        if toc_section_number and toc_section_number in chapter_sections_map:
            item["html"] = chapter_sections_map[toc_section_number]["html"]
            matched_count += 1

    return matched_count


def _find_chapter_sections(
    flat_toc: List[Dict[str, Any]], chapter: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Find all leaf sections under a specific chapter node.

    Args:
        flat_toc: Flattened TOC list
        chapter: Chapter node dictionary

    Returns:
        List of leaf section items under this chapter
    """
    chapter_sections = []
    in_chapter = False
    chapter_depth = chapter["depth"]
    chapter_text = chapter["value"]

    for item in flat_toc:
        if item["value"] == chapter_text and item["depth"] == chapter_depth:
            in_chapter = True
            continue

        if in_chapter and item["depth"] <= chapter_depth:
            break

        if in_chapter and not item.get("has_children") and "html" not in item:
            chapter_sections.append(item)

    return chapter_sections


def _get_assigned_section_numbers(flat_toc: List[Dict[str, Any]]) -> set[str]:
    """
    Get set of section numbers that have already been assigned HTML.

    Args:
        flat_toc: Flattened TOC list

    Returns:
        Set of assigned section numbers
    """
    assigned_sections = set()

    for item in flat_toc:
        if "html" in item:
            toc_num = extract_section_number(item["value"])
            if toc_num:
                assigned_sections.add(toc_num)

    return assigned_sections


def _match_sections_by_order(
    flat_toc: List[Dict[str, Any]],
    clickable_nodes: List[Dict[str, Any]],
    chapter_sections_map: Dict[str, Dict[str, str]],
) -> int:
    """
    Match remaining sections by order within parent nodes (second pass).

    Args:
        flat_toc: Flattened TOC list
        clickable_nodes: List of clickable chapter nodes
        chapter_sections_map: Dict mapping section_id -> {"html": ..., "chapter": ...}

    Returns:
        Number of sections matched by order
    """
    matched_count = 0
    assigned_sections = _get_assigned_section_numbers(flat_toc)

    for chapter in clickable_nodes:
        chapter_text = chapter["value"]
        chapter_sections = _find_chapter_sections(flat_toc, chapter)

        scraped_for_chapter = []
        for section_num, data in chapter_sections_map.items():
            if data["chapter"] == chapter_text and section_num not in assigned_sections:
                scraped_for_chapter.append(data["html"])

        for i, toc_section in enumerate(chapter_sections):
            if i < len(scraped_for_chapter):
                toc_section["html"] = scraped_for_chapter[i]
                matched_count += 1
            else:
                toc_section["html_error"] = "No matching scraped content"

    return matched_count


def _mark_unmatched_sections(flat_toc: List[Dict[str, Any]]) -> None:
    """
    Mark remaining leaf nodes without content as having errors.

    Args:
        flat_toc: Flattened TOC list
    """
    for item in flat_toc:
        if (
            not item.get("has_children")
            and "html" not in item
            and "html_error" not in item
        ):
            item["html_error"] = "Section content not found"


def _match_sections_to_toc(
    flat_toc: List[Dict[str, Any]],
    clickable_nodes: List[Dict[str, Any]],
    chapter_sections_map: Dict[str, Dict[str, str]],
) -> tuple[int, int]:
    """
    Match scraped sections to TOC items using two-pass matching strategy.

    Args:
        flat_toc: Flattened TOC list
        clickable_nodes: List of clickable chapter nodes
        chapter_sections_map: Dict mapping section_id -> {"html": ..., "chapter": ...}

    Returns:
        Tuple of (matched_by_number, matched_by_order)
    """
    print(f"\nAssigning scraped content to {len(flat_toc)} TOC items...")
    print(f"  Scraped sections in map: {len(chapter_sections_map)}")

    matched_by_number = _match_sections_by_number(flat_toc, chapter_sections_map)
    print(f"  Matched by section number: {matched_by_number}")

    matched_by_order = _match_sections_by_order(
        flat_toc, clickable_nodes, chapter_sections_map
    )
    print(f"  Matched by order (fallback): {matched_by_order}")

    _mark_unmatched_sections(flat_toc)

    total_matches = matched_by_number + matched_by_order
    print(f"  Total successful matches: {total_matches}")

    return matched_by_number, matched_by_order


def _calculate_statistics(
    flat_toc: List[Dict[str, Any]],
) -> tuple[int, int, int, float]:
    """
    Calculate statistics about scraped content.

    Args:
        flat_toc: Flattened TOC list

    Returns:
        Tuple of (total_leaf_nodes, items_with_html, items_with_errors, success_rate)
    """
    total_leaf_nodes = sum(
        1 for item in flat_toc if not item.get("has_children", False)
    )
    items_with_html = sum(
        1 for item in flat_toc if "html" in item and not item.get("has_children", False)
    )
    items_with_errors = sum(1 for item in flat_toc if "html_error" in item)
    success_rate = (
        (items_with_html / total_leaf_nodes * 100) if total_leaf_nodes > 0 else 0
    )

    return total_leaf_nodes, items_with_html, items_with_errors, success_rate


def _print_unassigned_sections(
    chapter_sections_map: Dict[str, Dict[str, str]],
    flat_toc: List[Dict[str, Any]],
    matched_by_number: int,
) -> None:
    """
    Print warning about scraped sections that weren't assigned to TOC.

    Args:
        chapter_sections_map: Dict mapping section_id -> {"html": ..., "chapter": ...}
        flat_toc: Flattened TOC list
        matched_by_number: Number of sections matched by number
    """
    assigned_section_nums = set()
    for item in flat_toc:
        if "html" in item:
            num = extract_section_number(item["value"])
            if num:
                assigned_section_nums.add(num)

    unassigned = [
        num for num in chapter_sections_map.keys() if num not in assigned_section_nums
    ]

    if unassigned:
        print(f"\n⚠️  Warning: {len(unassigned)} scraped sections not matched to TOC:")
        for num in sorted(unassigned[:10]):
            chapter = chapter_sections_map[num]["chapter"]
            print(f"    - Section {num} (from {chapter[:40]}...)")
        if len(unassigned) > 10:
            print(f"    ... and {len(unassigned) - 10} more")

    print(
        f"  Unassigned scraped sections: {len(chapter_sections_map) - matched_by_number}"
    )


def _print_error_breakdown(flat_toc: List[Dict[str, Any]]) -> None:
    """
    Print breakdown of errors by type.

    Args:
        flat_toc: Flattened TOC list
    """
    from collections import defaultdict

    # Use defaultdict to avoid manual key existence checks
    error_types = defaultdict(list)
    for item in flat_toc:
        if "html_error" in item:
            error = item["html_error"]
            error_types[error].append(item["value"])

    if error_types:
        print("\nError Breakdown:")
        for error_type, items in error_types.items():
            print(f"  {error_type}: {len(items)} sections")
            for item_val in items[:5]:
                print(f"    - {item_val[:70]}")
            if len(items) > 5:
                print(f"    ... and {len(items) - 5} more")


def _print_chapter_statistics(flat_toc: List[Dict[str, Any]]) -> None:
    """
    Print success rate statistics by top-level chapter.

    Args:
        flat_toc: Flattened TOC list
    """
    from collections import defaultdict

    # Use defaultdict with lambda for nested dict initialization
    chapter_stats = defaultdict(lambda: {"total": 0, "success": 0})
    for item in flat_toc:
        if not item.get("has_children", False):
            chapter = (
                item["path"][0]
                if item.get("path") and len(item["path"]) > 0
                else "Unknown"
            )
            chapter_stats[chapter]["total"] += 1
            if "html" in item:
                chapter_stats[chapter]["success"] += 1

    print("\nSuccess Rate by Chapter:")
    for chapter, stats in sorted(chapter_stats.items()):
        rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✓" if rate > 80 else "⚠" if rate > 50 else "✗"
        print(
            f"  {status} {chapter[:50]:50s} {stats['success']:4d}/{stats['total']:4d} ({rate:5.1f}%)"
        )


def _print_validation_report(
    flat_toc: List[Dict[str, Any]],
    chapter_sections_map: Dict[str, Dict[str, str]],
    matched_by_number: int,
) -> tuple[int, int, int, float]:
    """
    Print detailed validation report.

    Args:
        flat_toc: Flattened TOC list
        chapter_sections_map: Dict mapping section_id -> {"html": ..., "chapter": ...}
        matched_by_number: Number of sections matched by number

    Returns:
        Tuple of (total_leaf_nodes, items_with_html, items_with_errors, success_rate)
    """
    print("\n" + "=" * 80)
    print("VALIDATION REPORT")
    print("=" * 80)

    total_leaf_nodes, items_with_html, items_with_errors, success_rate = (
        _calculate_statistics(flat_toc)
    )

    print("\nOverall Statistics:")
    print(f"  Total leaf sections in TOC: {total_leaf_nodes}")
    print(f"  Successfully scraped: {items_with_html} ({success_rate:.1f}%)")
    print(f"  Failed/Missing: {items_with_errors} ({100 - success_rate:.1f}%)")

    _print_unassigned_sections(chapter_sections_map, flat_toc, matched_by_number)
    _print_error_breakdown(flat_toc)
    _print_chapter_statistics(flat_toc)

    print("=" * 80 + "\n")

    return total_leaf_nodes, items_with_html, items_with_errors, success_rate


def _print_final_summary(flat_toc: List[Dict[str, Any]], output_path: Path) -> None:
    """
    Print final summary statistics.

    Args:
        flat_toc: Flattened TOC list
        output_path: Path to saved output file
    """
    total_leaf_nodes, items_with_html, items_with_errors, success_rate = (
        _calculate_statistics(flat_toc)
    )

    print(f"\nSaved to: {output_path}")

    print(f"\n{'=' * 80}")
    print("✓ SCRAPING COMPLETE!")
    print(f"{'=' * 80}")
    print(f"  Total TOC items: {len(flat_toc)}")
    print(f"  Leaf nodes: {total_leaf_nodes}")
    print(
        f"  Successfully scraped: {items_with_html}/{total_leaf_nodes} ({success_rate:.1f}%)"
    )
    if items_with_errors > 0:
        print(
            f"  Errors: {items_with_errors} ({items_with_errors / total_leaf_nodes * 100:.1f}%)"
        )
    print(f"{'=' * 80}\n")


def scrape_single_jurisdiction(
    url: str,
    output_name: str,
    output_dir_path: str = "output",
    debug: bool = False,
    csv_file: str | None = None,
):
    """Scrape HTML content from a single jurisdiction's code."""
    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")
    if debug:
        print("DEBUG MODE ENABLED")

    with sync_playwright() as p:
        browser, page = setup_browser_and_page(p)

        print(f"\nNavigating to {url}...")
        page.goto(url, wait_until="networkidle", timeout=60000)

        print("Checking for Cloudflare challenge...")
        page.wait_for_timeout(2000)

        if _check_cloudflare(page):
            print(
                "⚠️  Cloudflare challenge detected. Waiting up to 30 seconds for it to resolve..."
            )
            if not _wait_for_cloudflare(page):
                browser.close()
                return

        print("Waiting for TOC widget to load...")
        page.wait_for_selector("#code-toc-widget", timeout=60000)
        page.wait_for_selector(".MuiTreeView-root.toc-tree-widget", timeout=60000)
        page.wait_for_timeout(500)

        expand_all_toc_nodes(page)

        print("\nExtracting TOC structure...")
        toc_data = extract_toc_structure(page)

        if "error" in toc_data:
            print(f"Error: {toc_data['error']}")
            browser.close()
            return

        hierarchical_toc = toc_data["items"]
        print(f"Found {toc_data['totalItems']} total items in TOC")

        flat_toc = flatten_toc(hierarchical_toc)
        clickable_nodes = [
            item for item in flat_toc if item.get("has_children") and item["depth"] >= 1
        ]
        print(f"Found {len(clickable_nodes)} clickable nodes to scrape\n")

        chapter_sections_map = _scrape_all_chapters(page, clickable_nodes, debug)

        browser.close()

        matched_by_number, matched_by_order = _match_sections_to_toc(
            flat_toc, clickable_nodes, chapter_sections_map
        )

        _print_validation_report(flat_toc, chapter_sections_map, matched_by_number)

        metadata = create_output_metadata(
            url=url,
            output_name=output_name,
            scraper_name="ecode360.py",
            scraper_version="1.0",
            csv_file=csv_file,
        )

        output_path = save_scraped_output(
            sections=flat_toc,
            metadata=metadata,
            output_dir_path=output_dir_path,
            output_name=output_name,
        )

        _print_final_summary(flat_toc, output_path)


def scrape_from_csv(
    csv_path: str, output_dir_path: str = "output", debug: bool = False
):
    """Scrape multiple jurisdictions from a CSV file."""
    try:
        jurisdictions = read_municipalities_from_csv(csv_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    if not jurisdictions:
        print(f"Error: No ready jurisdictions found in {csv_path}")
        return

    print(f"\n{'=' * 60}")
    print("BATCH SCRAPING MODE")
    print(f"{'=' * 60}")
    print(f"CSV file: {csv_path}")
    print(f"Found {len(jurisdictions)} jurisdictions to scrape")
    print(f"Output directory: {output_dir_path}")
    print(f"{'=' * 60}\n")

    for i, juris in enumerate(jurisdictions, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(jurisdictions)}] Scraping: {juris['name']}")
        print(f"{'=' * 60}")

        try:
            scrape_single_jurisdiction(
                url=juris["code_url"],
                output_name=juris["slug"],
                output_dir_path=output_dir_path,
                debug=debug,
                csv_file=csv_path,
            )
            print(f"✓ Completed: {juris['name']}")
        except Exception as e:
            print(f"✗ Failed: {juris['name']}")
            print(f"  Error: {str(e)}")

    print(f"\n{'=' * 60}")
    print("BATCH SCRAPING COMPLETE")
    print(f"Processed {len(jurisdictions)} jurisdictions")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    import sys

    # Check for --debug flag (special for ecode360)
    debug = "--debug" in sys.argv
    if debug:
        sys.argv.remove("--debug")

    mode, url_or_csv, output_name, output_dir_path = parse_scraper_cli_args(
        "ecode360.py"
    )

    if mode == "csv":
        scrape_from_csv(url_or_csv, output_dir_path)
    else:  # single mode
        scrape_single_jurisdiction(
            url_or_csv, output_name, output_dir_path, debug=debug
        )
