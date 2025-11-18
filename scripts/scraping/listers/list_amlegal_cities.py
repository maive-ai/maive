"""
Simple script to extract municipality names and URLs from AM Legal regions pages.
Clicks into each municipality page to find the actual code URL.

Outputs a CSV file with columns:
  - name: Full municipality name
  - slug: URL-safe slug for file naming
  - base_url: Municipality home page URL
  - code_url: Full URL to codes (use this with amlegal.py)
  - status: 'ready' or 'no_code_found'

Usage:
  Single state:    python list_amlegal_cities.py <STATE> [--output-dir DIR]
  Multiple states: python list_amlegal_cities.py <STATE1> <STATE2> ... [--output-dir DIR]

Examples:
  python list_amlegal_cities.py UT
  python list_amlegal_cities.py UT MO KS --output-dir output/city_lists
"""

import csv
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper_utils import (
    create_slug_from_name,
    navigate_and_wait_for_content,
    parse_lister_cli_args,
    run_parallel_lister,
    save_debug_files,
    setup_browser_and_page,
)

# Get the scripts root directory (2 levels up from this file)
SCRIPTS_ROOT = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT_DIR = SCRIPTS_ROOT / "scraping" / "output" / "city_lists"


def _extract_municipalities_from_page(page: Page) -> list[dict[str, str]]:
    """
    Extract municipality names and URLs from the page.

    Args:
        page: Playwright page object

    Returns:
        List of dictionaries with 'name' and 'url' keys
    """
    return page.evaluate("""
        () => {
            const municipalities = [];
            const seen = new Set();

            // AM Legal uses specific structure - look for links in the regions page
            // Try multiple selectors to find the city links
            const selectors = [
                'a[href*="codelibrary.amlegal.com/codes/"]',  // Direct code links
                '.region-list a',  // If there's a region list
                '.municipality-link',  // Common class name
                'ul li a',  // Generic list items
                'a'  // Fallback to all links
            ];

            let links = [];
            for (const selector of selectors) {
                links = document.querySelectorAll(selector);
                if (links.length > 0) {
                    console.log(`Found ${links.length} links with selector: ${selector}`);
                    break;
                }
            }

            links.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                // Filter to only AM Legal code library links with /codes/ in the URL
                // This ensures we only get actual municipality code pages
                if (href && href.includes('codelibrary.amlegal.com/codes/') &&
                    text && text.length > 1 && text.length < 100) {

                    // Filter out common non-municipality items
                    const excludePatterns = [
                        'search', 'help', 'login', 'skip to', 'back to',
                        'contact', 'about', 'privacy', 'terms', 'home',
                        'register', 'sign in', 'forgot', 'regions',
                        'sitemap', 'accessibility', 'select location'
                    ];

                    const shouldExclude = excludePatterns.some(pattern =>
                        text.toLowerCase().includes(pattern)
                    );

                    // Avoid duplicates and single letters
                    const isSingleLetter = text.length === 1 && /^[A-Z]$/i.test(text);

                    if (!shouldExclude && !isSingleLetter && !seen.has(text)) {
                        seen.add(text);
                        municipalities.push({
                            name: text,
                            url: href
                        });
                    }
                }
            });

            return municipalities;
        }
    """)


def _verify_code_url(page: Page, muni: dict[str, str], state_code: str) -> None:
    """
    Verify a single municipality code URL by navigating to it.

    Args:
        page: Playwright page object
        muni: Municipality dictionary with 'name' and 'url' keys
        state_code: State code for logging
    """
    code_url = muni["url"]

    try:
        page.goto(code_url, wait_until="domcontentloaded", timeout=10000)
        page.wait_for_load_state("networkidle", timeout=5000)

        final_url = page.url
        muni["code_url"] = final_url

        if final_url != code_url:
            print(f"[{state_code}]     ✓ Found (redirected): {final_url}")
        else:
            print(f"[{state_code}]     ✓ Found: {final_url}")

    except Exception:
        print(f"[{state_code}]     ⚠ Could not verify URL (timeout/error): {code_url}")
        muni["code_url"] = code_url

    time.sleep(0.5)


def _verify_all_code_urls(
    page: Page, municipalities: list[dict[str, str]], state_code: str
) -> None:
    """
    Verify all municipality code URLs.

    Args:
        page: Playwright page object
        municipalities: List of municipality dictionaries
        state_code: State code for logging
    """
    print(f"\n[{state_code}] Verifying code URLs...")
    for i, muni in enumerate(municipalities):
        try:
            print(f"[{state_code}]   {i + 1}/{len(municipalities)}: {muni['name']}")
            _verify_code_url(page, muni, state_code)
        except Exception as e:
            print(f"[{state_code}]     ✗ Error: {str(e)}")
            muni["code_url"] = muni["url"]


def _save_municipalities_to_csv(
    municipalities: list[dict[str, str]],
    output_path: Path,
    output_name: str,
    base_url: str,
    state_code: str,
) -> Path:
    """
    Save municipalities to CSV file.

    Args:
        municipalities: List of municipality dictionaries
        output_path: Directory to save CSV file
        output_name: Base name for CSV file
        base_url: Base URL for the regions page
        state_code: State code for logging

    Returns:
        Path to the created CSV file
    """
    output_path.mkdir(parents=True, exist_ok=True)
    csv_file = output_path / f"{output_name}.csv"

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["name", "slug", "base_url", "code_url", "status"]
        )
        writer.writeheader()

        for muni in sorted(municipalities, key=lambda x: x["name"]):
            slug = create_slug_from_name(muni["name"])
            writer.writerow(
                {
                    "name": muni["name"],
                    "slug": slug,
                    "base_url": base_url,
                    "code_url": muni.get("code_url", ""),
                    "status": "ready" if muni.get("code_url") else "no_code_found",
                }
            )

    return csv_file


def _print_summary(
    municipalities: list[dict[str, str]], csv_file: Path, state_code: str
) -> None:
    """
    Print summary information about extracted municipalities.

    Args:
        municipalities: List of municipality dictionaries
        csv_file: Path to the CSV file
        state_code: State code for logging
    """
    print(f"\n[{state_code}] {'=' * 60}")
    print(f"[{state_code}] SUMMARY")
    print(f"[{state_code}] {'=' * 60}")
    print(f"[{state_code}] Total municipalities: {len(municipalities)}")
    print(f"[{state_code}] ✓ Saved to {csv_file}")

    if municipalities:
        print(f"\n[{state_code}] Sample municipalities:")
        for muni in sorted(municipalities, key=lambda x: x["name"])[:5]:
            print(f"[{state_code}]   - {muni['name']}: {muni.get('code_url', 'N/A')}")


def extract_municipality_list(state_code: str, output_dir: str = None):
    """
    Extract list of municipalities from AM Legal regions page.

    Args:
        state_code: Two-letter state code (e.g., 'UT')
        output_dir: Directory to save the CSV file (defaults to scripts/output/city_lists)
    """
    if output_dir is None:
        output_dir = str(DEFAULT_OUTPUT_DIR)

    state_code = state_code.upper()
    state_lower = state_code.lower()

    url = f"https://codelibrary.amlegal.com/regions/{state_lower}"
    output_name = f"{state_lower}_cities"
    output_path = Path(output_dir) / state_lower

    municipalities = []

    with sync_playwright() as p:
        print(f"[{state_code}] Launching browser and navigating to {url}")
        browser, page = setup_browser_and_page(p)

        try:
            navigate_and_wait_for_content(page, url, state_code)
            save_debug_files(page, output_path, output_name, state_code)

            municipalities = _extract_municipalities_from_page(page)
            print(f"[{state_code}] Found {len(municipalities)} municipalities")

            if municipalities:
                _verify_all_code_urls(page, municipalities, state_code)
            else:
                print(
                    f"\n[{state_code}] No municipalities found with standard selectors."
                )
                print(
                    f"[{state_code}] Check the debug HTML and screenshot for manual inspection."
                )

        except Exception as e:
            print(f"[{state_code}] Error: {e}")
            traceback.print_exc()
        finally:
            browser.close()

    if municipalities:
        csv_file = _save_municipalities_to_csv(
            municipalities, output_path, output_name, url, state_code
        )
        _print_summary(municipalities, csv_file, state_code)
    else:
        print(
            f"\n[{state_code}] ✗ No municipalities found. Check the debug HTML file and screenshot."
        )

    return state_code, len(municipalities) if municipalities else 0


def scrape_states_parallel(states: list[str], output_dir: str = None):
    """
    Scrape multiple states in parallel.

    Args:
        states: List of state codes (e.g., ['UT', 'MO', 'KS'])
        output_dir: Directory to save outputs (defaults to scripts/output/city_lists)
    """
    if output_dir is None:
        output_dir = str(DEFAULT_OUTPUT_DIR)

    run_parallel_lister(
        states=states,
        lister_function=extract_municipality_list,
        output_dir=output_dir,
        item_type="municipalities",
    )


if __name__ == "__main__":
    states, output_dir_path = parse_lister_cli_args("list_amlegal_cities.py")

    # Run single or parallel mode
    if len(states) == 1:
        print(f"Using state code: {states[0]}")
        print(f"Output directory: {output_dir_path or 'default'}")
        extract_municipality_list(states[0], output_dir_path)
    else:
        scrape_states_parallel(states, output_dir_path)
