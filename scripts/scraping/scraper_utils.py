"""
Shared utility functions for all scrapers
"""

import csv
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from playwright.async_api import Browser as AsyncBrowser
from playwright.async_api import Page as AsyncPage
from playwright.async_api import Playwright as AsyncPlaywright
from playwright.sync_api import Browser, Page, Playwright
from playwright_stealth.stealth import Stealth


def extract_state_from_url(url: str) -> str | None:
    """
    Extract state code from URL using various patterns.

    Examples:
        https://library.municode.com/ut/virgin/... -> 'ut'
        https://ecode360.com/DA4058 -> None (no state in URL)
        https://lindon.municipal.codes/ -> None (no state in URL)

    Args:
        url: Source URL

    Returns:
        Two-letter state code or None
    """
    # Try municode pattern: library.municode.com/{state}/city/...
    match = re.search(r"municode\.com/([a-z]{2})/", url)
    if match:
        return match.group(1)

    # Try amlegal pattern: codelibrary.amlegal.com/codes/{state}_{city}/...
    match = re.search(r"amlegal\.com/codes/([a-z]{2})_", url)
    if match:
        return match.group(1)

    return None


def extract_state_from_csv(csv_file_path: str | Path) -> str | None:
    """
    Extract state code from CSV file path.

    Examples:
        city_lists/ut/ut_municode.csv -> 'ut'
        output/utah_analysis/ut_missing_municode.csv -> 'ut'

    Args:
        csv_file_path: Path to CSV file

    Returns:
        Two-letter state code or None
    """
    path = Path(csv_file_path)

    # Try to find state in directory path
    for part in path.parts:
        if len(part) == 2 and part.islower() and part.isalpha():
            return part

    # Try to extract from filename: ut_municode.csv -> 'ut'
    filename_parts = path.stem.split("_")
    if len(filename_parts) > 0:
        potential_state = filename_parts[0]
        if (
            len(potential_state) == 2
            and potential_state.islower()
            and potential_state.isalpha()
        ):
            return potential_state

    return None


def get_state(url: str, csv_file: str | Path | None = None) -> str | None:
    """
    Get state code from URL or CSV file path.

    Tries URL first, then falls back to CSV path if provided.

    Args:
        url: Source URL
        csv_file: Optional CSV file path to extract state from

    Returns:
        Two-letter state code or None
    """
    # Try URL first
    state = extract_state_from_url(url)
    if state:
        return state

    # Fall back to CSV path
    if csv_file:
        return extract_state_from_csv(csv_file)

    return None


def setup_browser_and_page(playwright: Playwright) -> tuple[Browser, Page]:
    """
    Set up browser context and page with stealth configuration.

    Args:
        playwright: Playwright instance

    Returns:
        Tuple of (browser, page) objects
    """
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )
    page = context.new_page()

    stealth = Stealth()
    stealth.apply_stealth_sync(page)

    return browser, page


def navigate_and_wait_for_content(
    page: Page,
    url: str,
    state_code: str,
    networkidle_timeout: int = 60000,
    sleep_seconds: int = 10,
    cloudflare_message: bool = True,
) -> None:
    """
    Navigate to URL and wait for content to load.

    Args:
        page: Playwright page object
        url: URL to navigate to
        state_code: State code for logging
        networkidle_timeout: Timeout for networkidle state in milliseconds
        sleep_seconds: Additional seconds to wait after networkidle
        cloudflare_message: Whether to print Cloudflare challenge message
    """
    page.goto(url, wait_until="domcontentloaded")

    print(f"[{state_code}] Waiting for content to load...")
    if cloudflare_message:
        print(
            f"[{state_code}]   ℹ️  If you see a Cloudflare challenge, please complete it manually..."
        )
    try:
        page.wait_for_load_state("networkidle", timeout=networkidle_timeout)
    except Exception as e:
        print(
            f"[{state_code}]   ⚠ Network idle timeout (continuing anyway): {str(e)[:50]}"
        )

    if sleep_seconds > 0:
        print(
            f"[{state_code}]   Waiting {sleep_seconds} seconds for page to fully load..."
        )
        time.sleep(sleep_seconds)


def save_debug_files(
    page: Page, output_path: Path, output_name: str, state_code: str
) -> None:
    """
    Save HTML content and screenshot for debugging.

    Args:
        page: Playwright page object
        output_path: Directory to save debug files
        output_name: Base name for output files
        state_code: State code for logging
    """
    output_path.mkdir(parents=True, exist_ok=True)

    html_content = page.content()
    debug_file = output_path / f"{output_name}_debug.html"
    debug_file.write_text(html_content, encoding="utf-8")
    print(f"[{state_code}] Saved page HTML to {debug_file}")

    screenshot_file = output_path / f"{output_name}_screenshot.png"
    page.screenshot(path=str(screenshot_file), full_page=True)
    print(f"[{state_code}] Saved screenshot to {screenshot_file}")


def create_slug_from_name(name: str, remove_prefixes: bool = False) -> str:
    """
    Create a URL-safe slug from a name.

    Args:
        name: Name to convert to slug
        remove_prefixes: Whether to remove common prefixes like "City of ", "Town of ", etc.

    Returns:
        URL-safe slug
    """
    name_for_slug = name

    if remove_prefixes:
        for prefix in ["City of ", "Town of ", "Village of ", "County of "]:
            # Use str.removeprefix() for cleaner code (Python 3.9+)
            new_name = name_for_slug.removeprefix(prefix)
            if new_name != name_for_slug:
                name_for_slug = new_name
                break

    return re.sub(r"[^a-z0-9]+", "-", name_for_slug.lower()).strip("-")


async def setup_browser_and_page_async(
    playwright: AsyncPlaywright,
) -> tuple[AsyncBrowser, AsyncPage]:
    """
    Set up browser context and page with stealth configuration (async version).

    Args:
        playwright: Async Playwright instance

    Returns:
        Tuple of (browser, page) objects
    """
    browser = await playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
    )
    page = await context.new_page()

    stealth = Stealth()
    stealth.apply_stealth_sync(page)

    return browser, page


def read_municipalities_from_csv(csv_path: str | Path) -> List[Dict[str, str]]:
    """
    Read municipalities/jurisdictions from CSV file.

    Expected CSV format:
        name,slug,base_url,code_url,status

    Args:
        csv_path: Path to CSV file

    Returns:
        List of dictionaries with municipality data
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # Use list comprehension for more Pythonic filtering
        return [
            row
            for row in reader
            if row.get("status") == "ready" and row.get("code_url")
        ]


def create_output_metadata(
    url: str,
    output_name: str,
    scraper_name: str,
    scraper_version: str,
    csv_file: str | Path | None = None,
) -> Dict[str, Any]:
    """
    Create standardized metadata for scraped output.

    Args:
        url: Source URL
        output_name: Name/slug for the output
        scraper_name: Name of the scraper (e.g., "amlegal.py")
        scraper_version: Version of the scraper
        csv_file: Optional CSV file path for state extraction

    Returns:
        Dictionary with metadata structure
    """
    # Use UTC timezone for consistent timestamps across systems
    scraped_at = datetime.now(timezone.utc).isoformat()
    state = get_state(url, csv_file)

    return {
        "scraped_at": scraped_at,
        "city_slug": output_name,
        "state": state,
        "source_url": url,
        "scraper": scraper_name,
        "scraper_version": scraper_version,
    }


def save_scraped_output(
    sections: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    output_dir_path: str | Path,
    output_name: str,
) -> Path:
    """
    Save scraped sections with metadata to JSON file.

    Args:
        sections: List of section dictionaries
        metadata: Metadata dictionary
        output_dir_path: Directory to save output
        output_name: Base name for output file (without extension)

    Returns:
        Path to the created output file
    """
    output_dir = Path(output_dir_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"{output_name}.json"
    output_path = output_dir / output_filename

    output_data = {
        "metadata": metadata,
        "sections": sections,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    return output_path


def clean_html_content(
    html_content: str,
    remove_ui_classes: List[str] | None = None,
    preserve_classes: List[str] | None = None,
    preserve_data_attrs: List[str] | None = None,
) -> str:
    """
    Clean HTML content to keep only essential elements and structure.

    Args:
        html_content: HTML string to clean
        remove_ui_classes: List of CSS class patterns to remove (e.g., ['navbar', 'btn', 'modal'])
        preserve_classes: List of class prefixes to preserve (e.g., ['mco-', 'chunk-'])
        preserve_data_attrs: List of data-* attributes to preserve (e.g., ['data-nodedepth'])

    Returns:
        Cleaned HTML string
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style tags
    for tag in soup.find_all(["script", "style"]):
        tag.decompose()

    # Remove stylesheet links
    for link in soup.find_all("link", rel="stylesheet"):
        link.decompose()

    # Remove UI elements by class if specified
    if remove_ui_classes:
        for element in soup.find_all(class_=remove_ui_classes):
            element.decompose()

    # Remove empty paragraphs, divs, and spans
    for tag in soup.find_all(["p", "div", "span"]):
        if not tag.get_text(strip=True) and not tag.find_all(True):
            tag.decompose()

    # Clean attributes - keep only essential ones
    always_preserve = ["id", "href", "target"]
    for tag in soup.find_all(True):
        new_attrs = {}

        # Preserve essential attributes
        for attr in always_preserve:
            if attr in tag.attrs:
                new_attrs[attr] = tag.attrs[attr]

        # Preserve specified data-* attributes
        if preserve_data_attrs:
            for data_attr in preserve_data_attrs:
                if data_attr in tag.attrs:
                    new_attrs[data_attr] = tag.attrs[data_attr]

        # Preserve semantic classes if specified
        if preserve_classes and "class" in tag.attrs:
            classes = (
                tag.attrs["class"]
                if isinstance(tag.attrs["class"], list)
                else [tag.attrs["class"]]
            )
            # Use list comprehension for cleaner filtering
            preserved = [
                cls
                for cls in classes
                for prefix in preserve_classes
                if cls.startswith(prefix) or (len(prefix) <= 2 and cls == prefix)
            ]
            # Remove duplicates while preserving order (dict.fromkeys trick)
            if preserved:
                new_attrs["class"] = list(dict.fromkeys(preserved))

        tag.attrs = new_attrs

    # Convert back to string
    cleaned_html = str(soup)

    # Remove HTML comments
    cleaned_html = re.sub(r"<!--.*?-->", "", cleaned_html, flags=re.DOTALL)

    # Remove excessive whitespace
    cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html)

    return cleaned_html.strip()


def flatten_toc(
    nodes: List[Dict[str, Any]], parent_path: List[str] | None = None
) -> List[Dict[str, Any]]:
    """
    Flatten a nested TOC structure into a list with hierarchical paths.

    Args:
        nodes: List of TOC nodes (each with 'text'/'title' and optional 'children')
        parent_path: Current path in the hierarchy (used for recursion)

    Returns:
        Flattened list of TOC items with path, depth, and has_children info
    """
    parent_path = parent_path or []
    flat_list = []

    for node in nodes:
        # Support both 'text' and 'title' as the node label
        node_text = node.get("text") or node.get("title", "")
        current_path = parent_path + [node_text]
        has_children = bool(node.get("children"))

        flat_item = {
            "value": node_text,
            "path": current_path,
            "url": node.get("url") or node.get("href"),  # Support both 'url' and 'href'
            "depth": len(current_path) - 1,
            "has_children": has_children,
        }

        # Preserve any internal fields (like _nodeId, _docId, _value) that start with underscore
        for key, value in node.items():
            if key.startswith("_"):
                flat_item[key] = value

        # Copy other important fields like 'html' if they exist
        if "html" in node:
            flat_item["html"] = node["html"]
        if "html_error" in node:
            flat_item["html_error"] = node["html_error"]

        flat_list.append(flat_item)

        # Recursively process children
        if has_children:
            flat_list.extend(flatten_toc(node["children"], current_path))

    return flat_list


def escape_css_selector(selector_id: str) -> str:
    """
    Escape special characters in CSS selector IDs.

    Args:
        selector_id: CSS selector ID to escape

    Returns:
        Escaped CSS selector safe for use in querySelector
    """
    # Escape dots, colons, brackets, and other special CSS characters
    # In CSS selectors, these characters need to be escaped with backslashes
    return re.sub(r'([.:\[\](),\'"])', r"\\\1", selector_id)


def print_scraping_statistics(flat_toc: List[Dict[str, Any]]) -> None:
    """
    Print standardized statistics about scraped content.

    Args:
        flat_toc: Flattened TOC list with scraped content
    """
    items_with_html = sum(1 for item in flat_toc if "html" in item)
    items_with_errors = sum(1 for item in flat_toc if "html_error" in item)
    total_leaf_nodes = sum(
        1 for item in flat_toc if not item.get("has_children", False)
    )

    print("\n✓ Complete!")
    print(f"  Total TOC items: {len(flat_toc) if flat_toc else 0}")
    print(f"  Leaf nodes (with HTML): {total_leaf_nodes}")
    print(f"  Successfully scraped: {items_with_html}/{total_leaf_nodes}")
    if items_with_errors > 0:
        print(f"  Errors: {items_with_errors}")

    # Show warnings for missing HTML
    missing_html = [
        item
        for item in flat_toc
        if not item.get("has_children", False) and "html" not in item
    ]
    if missing_html:
        print(f"\n⚠ Warning: {len(missing_html)} leaf nodes have no HTML content:")
        for item in missing_html[:5]:
            print(f"    - {item.get('value', 'Unknown')}")
        if len(missing_html) > 5:
            print(f"    ... and {len(missing_html) - 5} more")


def run_batch_scraper(
    csv_path: str,
    output_dir_path: str,
    scraper_function,
    scraper_name: str = "scraper",
) -> None:
    """
    Run a scraper function on multiple municipalities from a CSV file.

    Args:
        csv_path: Path to CSV file containing municipality list
        output_dir_path: Directory to save outputs
        scraper_function: Function to call for each municipality (takes url, output_name, output_dir_path, csv_file)
        scraper_name: Name of scraper for logging
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
    print(f"Scraper: {scraper_name}")
    print(f"CSV file: {csv_path}")
    print(f"Found {len(municipalities)} municipalities to scrape")
    print(f"Output directory: {output_dir_path}")
    print(f"{'=' * 60}\n")

    for i, muni in enumerate(municipalities, 1):
        print(f"\n{'=' * 60}")
        print(f"[{i}/{len(municipalities)}] Scraping: {muni['name']}")
        print(f"{'=' * 60}")

        try:
            scraper_function(
                url=muni["code_url"],
                output_name=muni["slug"],
                output_dir_path=output_dir_path,
                csv_file=csv_path,
            )
            print(f"✓ Completed: {muni['name']}")
        except Exception as e:
            print(f"✗ Failed: {muni['name']}")
            print(f"  Error: {str(e)}")

    print(f"\n{'=' * 60}")
    print("BATCH SCRAPING COMPLETE")
    print(f"Processed {len(municipalities)} municipalities")
    print(f"{'=' * 60}\n")


def extract_url_path_segment(url: str, segment_index: int = -1) -> str:
    """
    Extract a specific segment from a URL path.

    Args:
        url: URL to parse
        segment_index: Index of path segment to extract (default: -1 for last segment)

    Returns:
        Extracted path segment (e.g., "section123" from "/code/section123")
    """
    from urllib.parse import urlparse

    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]

    if not path_parts:
        return ""

    # Handle fragment (after #) if present
    if parsed.fragment:
        return parsed.fragment

    return path_parts[segment_index] if abs(segment_index) <= len(path_parts) else ""


def parse_scraper_cli_args(
    script_name: str, supports_async: bool = False
) -> tuple[str, str | None, str | None, str]:
    """
    Parse command-line arguments for scraper scripts using argparse.

    Supports two modes:
    1. Single mode: <URL> <NAME> [--output-dir DIR]
    2. Batch mode: --csv <CSV_FILE> [--output-dir DIR]

    Args:
        script_name: Name of the script (e.g., "municode.py")
        supports_async: Whether the scraper uses async (currently unused but kept for future)

    Returns:
        Tuple of (mode, url_or_csv, output_name, output_dir_path)
        - mode: "csv" or "single"
        - url_or_csv: URL (single mode) or CSV path (csv mode)
        - output_name: Output name (single mode only, None for csv mode)
        - output_dir_path: Output directory path
    """
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog=script_name,
        description=f"Scrape municipal code content using {script_name}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  Single mode:  python {script_name} https://example.com/code example-city
  Batch mode:   python {script_name} --csv ut_cities.csv --output-dir output
        """,
    )

    # Create mutually exclusive group for single vs batch mode
    mode_group = parser.add_mutually_exclusive_group(required=True)

    # Batch mode
    mode_group.add_argument(
        "--csv",
        metavar="CSV_FILE",
        help="CSV file containing municipality list (enables batch mode)",
    )

    # Single mode arguments (URL and NAME are positional but optional via nargs)
    mode_group.add_argument(
        "url", nargs="?", help="Full URL to the municipality code (single mode)"
    )

    parser.add_argument(
        "output_name",
        nargs="?",
        help="Name for the output file without extension (single mode)",
    )

    # Common optional argument
    parser.add_argument(
        "--output-dir",
        dest="output_dir_path",
        default="output",
        help="Directory to save output files (default: output)",
    )

    args = parser.parse_args()

    # Determine mode and validate arguments
    if args.csv:
        return ("csv", args.csv, None, args.output_dir_path)
    elif args.url and args.output_name:
        return ("single", args.url, args.output_name, args.output_dir_path)
    else:
        parser.error("Single mode requires both URL and NAME arguments")


def parse_lister_cli_args(script_name: str) -> tuple[list[str], str | None]:
    """
    Parse command-line arguments for lister scripts.

    Supports scraping one or more states: <STATE1> [STATE2...] [--output-dir DIR]

    Args:
        script_name: Name of the script (e.g., "list_municode_cities.py")

    Returns:
        Tuple of (states, output_dir_path)
        - states: List of state codes
        - output_dir_path: Output directory path or None for default
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog=script_name,
        description=f"Extract municipality/jurisdiction list using {script_name}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  Single state:    python {script_name} UT
  Multiple states: python {script_name} UT MO KS
  With output dir: python {script_name} UT MO --output-dir output/city_lists
        """,
    )

    parser.add_argument(
        "states",
        nargs="+",
        help="One or more state codes (e.g., UT, MO, KS)",
    )

    parser.add_argument(
        "--output-dir",
        dest="output_dir_path",
        default=None,
        help="Directory to save output files (default: scripts/scraping/output/city_lists)",
    )

    args = parser.parse_args()

    # Normalize state codes to uppercase
    states = [state.upper() for state in args.states]

    return states, args.output_dir_path


def group_items_by_field(
    items: List[Dict[str, Any]], field_name: str, default_value: str = "unknown"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group items by a specific field value.

    Args:
        items: List of dictionaries to group
        field_name: Field name to group by (e.g., "platform")
        default_value: Default value if field is missing

    Returns:
        Dictionary mapping field values to lists of items
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for item in items:
        group_key = item.get(field_name, default_value)
        groups[group_key].append(item)

    return dict(groups)


def run_parallel_lister(
    states: List[str],
    lister_function,
    output_dir: str | None,
    item_type: str = "items",
) -> None:
    """
    Run a lister function on multiple states in parallel.

    Args:
        states: List of state codes (e.g., ['UT', 'MO', 'KS'])
        lister_function: Function to call for each state (takes state_code, output_dir)
        output_dir: Directory to save outputs
        item_type: Name of items being scraped (e.g., "municipalities", "jurisdictions")
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed

    print(f"\n{'=' * 60}")
    print("PARALLEL SCRAPING MODE")
    print(f"{'=' * 60}")
    print(f"States to scrape: {', '.join(states)}")
    print(f"Output directory: {output_dir or 'default'}")
    print(f"{'=' * 60}\n")

    # Run each state in a separate process
    with ProcessPoolExecutor(max_workers=len(states)) as executor:
        future_to_state = {
            executor.submit(lister_function, state, output_dir): state
            for state in states
        }

        results = {}
        for future in as_completed(future_to_state):
            state = future_to_state[future]
            try:
                state_code, count = future.result()
                results[state_code] = count
                print(f"\n✓ Completed {state_code}: {count} {item_type}")
            except Exception as e:
                print(f"\n✗ Failed {state}: {str(e)}")
                results[state] = 0

    # Print final summary
    print(f"\n{'=' * 60}")
    print("ALL STATES COMPLETE")
    print(f"{'=' * 60}")
    for state in states:
        count = results.get(state.upper(), 0)
        print(f"  {state.upper()}: {count} {item_type}")
    print(f"  Total: {sum(results.values())} {item_type}")
    print(f"{'=' * 60}\n")

