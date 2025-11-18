"""
Simple script to extract jurisdiction names and URLs from General Code library pages.

Outputs a CSV file with columns:
  - name: Full jurisdiction name
  - slug: URL-safe slug for file naming
  - base_url: The General Code library page
  - code_url: Full URL to codes (use with appropriate scraper)
  - platform: Which platform hosts the code (ecode360, municipal_codes, codepublishing)
  - status: 'ready' or 'no_code_found'

Usage:
  Single state:    python list_generalcode_cities.py <STATE> [--output-dir DIR]
  Multiple states: python list_generalcode_cities.py <STATE1> <STATE2> ... [--output-dir DIR]

Examples:
  python list_generalcode_cities.py MO
  python list_generalcode_cities.py KS MO NE --output-dir output/city_lists
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
    group_items_by_field,
    navigate_and_wait_for_content,
    parse_lister_cli_args,
    run_parallel_lister,
    save_debug_files,
    setup_browser_and_page,
)

# Get the scripts root directory (2 levels up from this file)
SCRIPTS_ROOT = Path(__file__).parent.parent.parent
DEFAULT_OUTPUT_DIR = SCRIPTS_ROOT / "scraping" / "output" / "city_lists"


def _extract_jurisdictions_from_page(page: Page) -> list[dict[str, str]]:
    """
    Extract jurisdiction names and URLs from the General Code library page.

    Args:
        page: Playwright page object

    Returns:
        List of dictionaries with 'name', 'url', and 'platform' keys
    """
    return page.evaluate("""
        () => {
            const jurisdictions = [];
            const seen = new Set();

            const links = document.querySelectorAll('a[href]');

            links.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                const isEcode360 = href.includes('ecode360.com/');
                const isMunicipalCodes = href.includes('.municipal.codes/');
                const isCodePublishing = href.includes('codepublishing.com/');
                const isGeneralCode = href.includes('.generalcode.com/') && !href.includes('www.generalcode.com');

                if ((isEcode360 || isMunicipalCodes || isCodePublishing || isGeneralCode) &&
                    text && text.length > 1 && text.length < 100) {

                    const excludePatterns = [
                        'search', 'help', 'login', 'skip to', 'back to',
                        'contact', 'about', 'privacy', 'terms', 'home',
                        'register', 'sign in', 'forgot', 'library',
                        'sitemap', 'accessibility', 'select location',
                        'general code', 'ecode360', 'municipal codes'
                    ];

                    const shouldExclude = excludePatterns.some(pattern =>
                        text.toLowerCase().includes(pattern)
                    );

                    if (!shouldExclude && !seen.has(text)) {
                        seen.add(text);

                        let platform = 'unknown';
                        if (isEcode360) platform = 'ecode360';
                        else if (isMunicipalCodes) platform = 'municipal_codes';
                        else if (isCodePublishing) platform = 'codepublishing';
                        else if (isGeneralCode) platform = 'generalcode';

                        jurisdictions.push({
                            name: text,
                            url: href,
                            platform: platform
                        });
                    }
                }
            });

            return jurisdictions;
        }
    """)


def _verify_jurisdiction_url(
    page: Page, juris: dict[str, str], state_code: str, index: int, total: int
) -> None:
    """
    Verify URL for a single jurisdiction.

    Args:
        page: Playwright page object
        juris: Jurisdiction dictionary with 'name', 'url', and 'platform' keys
        state_code: State code for logging
        index: Current index (0-based)
        total: Total number of jurisdictions
    """
    try:
        print(
            f"[{state_code}]   {index + 1}/{total}: {juris['name']} ({juris['platform']})"
        )

        try:
            page.goto(juris["url"], wait_until="domcontentloaded", timeout=10000)
            page.wait_for_load_state("networkidle", timeout=5000)

            final_url = page.url
            juris["code_url"] = final_url

            if final_url != juris["url"]:
                print(f"[{state_code}]     ✓ Found (redirected): {final_url}")
            else:
                print(f"[{state_code}]     ✓ Found: {final_url}")

        except Exception:
            print(
                f"[{state_code}]     ⚠ Could not verify URL (timeout/error): {juris['url']}"
            )
            juris["code_url"] = juris["url"]

        time.sleep(0.5)

    except Exception as e:
        print(f"[{state_code}]     ✗ Error: {str(e)}")
        juris["code_url"] = juris["url"]


def _verify_all_jurisdiction_urls(
    page: Page, jurisdictions: list[dict[str, str]], state_code: str
) -> None:
    """
    Verify URLs for all jurisdictions.

    Args:
        page: Playwright page object
        jurisdictions: List of jurisdiction dictionaries
        state_code: State code for logging
    """
    print(f"[{state_code}] Verifying code URLs...")
    for i, juris in enumerate(jurisdictions):
        _verify_jurisdiction_url(page, juris, state_code, i, len(jurisdictions))


def _group_jurisdictions_by_platform(
    jurisdictions: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    """
    Group jurisdictions by platform.

    Args:
        jurisdictions: List of jurisdiction dictionaries

    Returns:
        Dictionary mapping platform names to lists of jurisdictions
    """
    # Use shared grouping utility
    return group_items_by_field(jurisdictions, "platform", default_value="unknown")


def _write_jurisdiction_csv(
    csv_file: Path,
    jurisdictions: list[dict[str, str]],
    base_url: str,
    state_code: str,
    description: str,
) -> None:
    """
    Write jurisdictions to a CSV file.

    Args:
        csv_file: Path to CSV file
        jurisdictions: List of jurisdiction dictionaries
        base_url: Base URL for the regions page
        state_code: State code for logging
        description: Description of the jurisdictions being written
    """
    if not jurisdictions:
        return

    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "slug",
                "base_url",
                "code_url",
                "platform",
                "status",
            ],
        )
        writer.writeheader()

        for juris in sorted(jurisdictions, key=lambda x: x["name"]):
            slug = create_slug_from_name(juris["name"], remove_prefixes=True)
            writer.writerow(
                {
                    "name": juris["name"],
                    "slug": slug,
                    "base_url": base_url,
                    "code_url": juris.get("code_url", ""),
                    "platform": juris.get("platform", "unknown"),
                    "status": "ready" if juris.get("code_url") else "no_code_found",
                }
            )

    print(f"[{state_code}] ✓ Saved {len(jurisdictions)} {description} to {csv_file}")


def _save_jurisdictions_to_csv(
    jurisdictions: list[dict[str, str]],
    output_path: Path,
    output_name: str,
    base_url: str,
    state_code: str,
) -> None:
    """
    Save jurisdictions to CSV files grouped by platform.

    Args:
        jurisdictions: List of jurisdiction dictionaries
        output_path: Directory to save CSV files
        output_name: Base name for CSV files
        base_url: Base URL for the regions page
        state_code: State code for logging
    """
    output_path.mkdir(parents=True, exist_ok=True)
    groups = _group_jurisdictions_by_platform(jurisdictions)

    # Write CSV for each platform group if it has jurisdictions
    if "ecode360" in groups and groups["ecode360"]:
        _write_jurisdiction_csv(
            output_path / f"{output_name}_ecode360.csv",
            groups["ecode360"],
            base_url,
            state_code,
            "eCode360 jurisdictions",
        )
    if "municipal_codes" in groups and groups["municipal_codes"]:
        _write_jurisdiction_csv(
            output_path / f"{output_name}_municipal_codes.csv",
            groups["municipal_codes"],
            base_url,
            state_code,
            "Municipal.codes jurisdictions",
        )
    if "codepublishing" in groups and groups["codepublishing"]:
        _write_jurisdiction_csv(
            output_path / f"{output_name}_codepublishing.csv",
            groups["codepublishing"],
            base_url,
            state_code,
            "CodePublishing jurisdictions",
        )
    if "generalcode" in groups and groups["generalcode"]:
        _write_jurisdiction_csv(
            output_path / f"{output_name}_generalcode.csv",
            groups["generalcode"],
            base_url,
            state_code,
            "General Code subdomain jurisdictions",
        )
    if "other" in groups and groups["other"]:
        _write_jurisdiction_csv(
            output_path / f"{output_name}_other.csv",
            groups["other"],
            base_url,
            state_code,
            "Other platform jurisdictions",
        )

    # Write combined CSV
    csv_file = output_path / f"{output_name}_all.csv"
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "name",
                "slug",
                "base_url",
                "code_url",
                "platform",
                "status",
            ],
        )
        writer.writeheader()

        for juris in sorted(jurisdictions, key=lambda x: x["name"]):
            slug = create_slug_from_name(juris["name"], remove_prefixes=True)
            writer.writerow(
                {
                    "name": juris["name"],
                    "slug": slug,
                    "base_url": base_url,
                    "code_url": juris.get("code_url", ""),
                    "platform": juris.get("platform", "unknown"),
                    "status": "ready" if juris.get("code_url") else "no_code_found",
                }
            )

    print(
        f"[{state_code}] ✓ Saved {len(jurisdictions)} total jurisdictions to {csv_file}"
    )


def _print_summary(jurisdictions: list[dict[str, str]], state_code: str) -> None:
    """
    Print summary statistics about extracted jurisdictions.

    Args:
        jurisdictions: List of jurisdiction dictionaries
        state_code: State code for logging
    """
    groups = _group_jurisdictions_by_platform(jurisdictions)

    print(f"\n[{state_code}] {'=' * 60}")
    print(f"[{state_code}] SUMMARY")
    print(f"[{state_code}] {'=' * 60}")
    print(f"[{state_code}] Total jurisdictions: {len(jurisdictions)}")
    print(f"[{state_code}] By Platform:")
    print(
        f"[{state_code}]   🔷 eCode360:              {len(groups.get('ecode360', []))} (use general_code_publish.py)"
    )
    print(
        f"[{state_code}]   🔶 Municipal.codes:       {len(groups.get('municipal_codes', []))} (use general_code_subdomain.py)"
    )
    print(
        f"[{state_code}]   🔸 CodePublishing:        {len(groups.get('codepublishing', []))} (use general_code_publish.py)"
    )
    print(
        f"[{state_code}]   🟦 General Code subdomain: {len(groups.get('generalcode', []))} (use general_code_subdomain.py)"
    )
    if groups.get("other"):
        print(f"[{state_code}]   🔗 Other platforms:       {len(groups['other'])}")


def extract_jurisdiction_list(state_code: str, output_dir: str = None):
    """
    Extract list of jurisdictions from General Code library page.

    Args:
        state_code: Two-letter state code (e.g., 'MO')
        output_dir: Directory to save the CSV file (defaults to scripts/output/city_lists)
    """
    if output_dir is None:
        output_dir = str(DEFAULT_OUTPUT_DIR)

    state_code = state_code.upper()
    state_lower = state_code.lower()

    # Construct the URL and output name from state code
    url = f"https://www.generalcode.com/source-library/?state={state_code}"
    output_name = f"{state_lower}_cities"

    jurisdictions = []
    output_path = Path(output_dir) / state_lower

    with sync_playwright() as p:
        print(f"[{state_code}] Launching browser and navigating to {url}")
        browser, page = setup_browser_and_page(p)

        try:
            navigate_and_wait_for_content(
                page,
                url,
                state_code,
                networkidle_timeout=30000,
                sleep_seconds=10,
                cloudflare_message=True,
            )
            save_debug_files(page, output_path, output_name, state_code)

            jurisdictions = _extract_jurisdictions_from_page(page)
            print(f"[{state_code}] Found {len(jurisdictions)} jurisdictions")

            if jurisdictions:
                _verify_all_jurisdiction_urls(page, jurisdictions, state_code)
            else:
                print(f"[{state_code}] No jurisdictions found with standard selectors.")
                print(
                    f"[{state_code}] Check the debug HTML and screenshot for manual inspection."
                )

        except Exception as e:
            print(f"[{state_code}] Error: {e}")
            traceback.print_exc()

        finally:
            browser.close()

    if jurisdictions:
        output_path = Path(output_dir) / state_lower
        _save_jurisdictions_to_csv(
            jurisdictions, output_path, output_name, url, state_code
        )
        _print_summary(jurisdictions, state_code)
    else:
        print(
            f"[{state_code}] ✗ No jurisdictions found. Check the debug HTML file and screenshot."
        )

    return state_code, len(jurisdictions) if jurisdictions else 0


def scrape_states_parallel(states: list[str], output_dir: str = None):
    """
    Scrape multiple states in parallel.

    Args:
        states: List of state codes (e.g., ['KS', 'MO', 'NE'])
        output_dir: Directory to save outputs (defaults to scripts/output/city_lists)
    """
    if output_dir is None:
        output_dir = str(DEFAULT_OUTPUT_DIR)

    run_parallel_lister(
        states=states,
        lister_function=extract_jurisdiction_list,
        output_dir=output_dir,
        item_type="jurisdictions",
    )


if __name__ == "__main__":
    states, output_dir_path = parse_lister_cli_args("list_generalcode_cities.py")

    # Run single or parallel mode
    if len(states) == 1:
        print(f"Using state code: {states[0]}")
        print(f"Output directory: {output_dir_path or 'default'}")
        extract_jurisdiction_list(states[0], output_dir_path)
    else:
        scrape_states_parallel(states, output_dir_path)
