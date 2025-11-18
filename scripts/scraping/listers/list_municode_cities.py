"""
Simple script to extract municipality names and full code URLs from Municode library pages.
Clicks into each municipality page to find the actual code/ordinance document URL.

Outputs a CSV file with columns:
  - name: Full municipality name
  - slug: URL-safe slug for file naming
  - base_url: Municipality home page URL
  - code_url: Full URL to codes/ordinances (use this with municode.py)
  - status: 'ready' or 'no_code_found'

Usage:
  Single state:    python list_municode_cities.py <STATE> [--output-dir DIR]
  Multiple states: python list_municode_cities.py <STATE1> <STATE2> ... [--output-dir DIR]

Examples:
  python list_municode_cities.py MO
  python list_municode_cities.py KS MO NE --output-dir output/city_lists
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


def _extract_municipalities_from_page(page: Page) -> list[dict[str, str]]:
    """
    Extract municipality names and URLs from the Municode library page.

    Args:
        page: Playwright page object

    Returns:
        List of dictionaries with 'name' and 'url' keys
    """
    return page.evaluate("""
        () => {
            const municipalities = [];
            const seen = new Set();

            const links = document.querySelectorAll('a');
            links.forEach(link => {
                const href = link.href;
                const text = link.textContent.trim();

                const excludePatterns = [
                    'search', 'help', 'login', 'skip to', 'municode library',
                    'order a', 'contact', 'about', 'privacy', 'terms'
                ];

                const shouldExclude = excludePatterns.some(pattern =>
                    text.toLowerCase().includes(pattern)
                );

                const isSingleLetter = text.length === 1 && /^[A-Z]$/i.test(text);

                if (href && href.includes('library.municode.com') &&
                    text && text.length > 1 && text.length < 100 &&
                    !shouldExclude && !isSingleLetter) {

                    if (!seen.has(text)) {
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


def _find_code_url_on_page(page: Page) -> str | None:
    """
    Find the code URL on a municipality page.

    Args:
        page: Playwright page object

    Returns:
        Code URL string or None if not found
    """
    return page.evaluate("""
        () => {
            const patterns = [
                'code of ordinances',
                'municipal code',
                'city code',
                'county code',
                'land development code',
                'zoning code',
                'development code'
            ];

            const links = document.querySelectorAll('a');
            for (const link of links) {
                const text = link.textContent.toLowerCase().trim();
                const href = link.href;

                for (const pattern of patterns) {
                    if (text.includes(pattern) && href.includes('/codes/')) {
                        return href;
                    }
                }

                for (const pattern of patterns) {
                    if (text.includes(pattern) && href.includes('municipalcodeonline.com')) {
                        return href;
                    }
                }
            }

            for (const link of links) {
                if (link.href.includes('/codes/') &&
                    !link.href.includes('/search') &&
                    !link.href.includes('/compare')) {
                    return link.href;
                }
            }

            for (const link of links) {
                if (link.href.includes('municipalcodeonline.com/book')) {
                    return link.href;
                }
            }

            return null;
        }
    """)


def _determine_platform(final_url: str) -> str:
    """
    Determine platform based on final URL.

    Args:
        final_url: Final URL after redirects

    Returns:
        Platform string: 'library', 'self_publishing', or 'other'
    """
    if "library.municode.com" in final_url and "/codes/" in final_url:
        return "library"
    elif "municipalcodeonline.com" in final_url:
        return "self_publishing"
    else:
        return "other"


def _verify_municipality_code_url(
    page: Page, muni: dict[str, str], state_code: str, index: int, total: int
) -> None:
    """
    Verify and extract code URL for a single municipality.

    Args:
        page: Playwright page object
        muni: Municipality dictionary with 'name' and 'url' keys
        state_code: State code for logging
        index: Current index (0-based)
        total: Total number of municipalities
    """
    try:
        print(f"[{state_code}]   {index + 1}/{total}: {muni['name']}")

        page.goto(muni["url"], wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=10000)

        code_url = _find_code_url_on_page(page)

        if code_url:
            try:
                page.goto(code_url, wait_until="domcontentloaded", timeout=10000)
                page.wait_for_load_state("networkidle", timeout=5000)

                final_url = page.url
                muni["code_url"] = final_url
                muni["platform"] = _determine_platform(final_url)

                redirected = ", redirected" if final_url != code_url else ""
                platform_name = (
                    "Library"
                    if muni["platform"] == "library"
                    else "Self-Publishing"
                    if muni["platform"] == "self_publishing"
                    else "Other"
                )
                print(
                    f"[{state_code}]     ✓ Found ({platform_name}{redirected}): {final_url}"
                )
            except Exception:
                print(
                    f"[{state_code}]     ⚠ Could not verify URL (timeout/error): {code_url}"
                )
                muni["code_url"] = code_url
                muni["platform"] = "unknown"
        else:
            print(f"[{state_code}]     ⚠ No code URL found")
            muni["code_url"] = None
            muni["platform"] = None

        time.sleep(0.5)

    except Exception as e:
        print(f"[{state_code}]     ✗ Error: {str(e)}")
        muni["code_url"] = None
        muni["platform"] = None


def _verify_all_code_urls(
    page: Page, municipalities: list[dict[str, str]], state_code: str
) -> None:
    """
    Verify code URLs for all municipalities.

    Args:
        page: Playwright page object
        municipalities: List of municipality dictionaries
        state_code: State code for logging
    """
    print(f"\n[{state_code}] Extracting full code URLs...")
    for i, muni in enumerate(municipalities):
        _verify_municipality_code_url(page, muni, state_code, i, len(municipalities))


def _group_municipalities_by_platform(
    municipalities: list[dict[str, str]],
) -> dict[str, list[dict[str, str]]]:
    """
    Group municipalities by platform.

    Args:
        municipalities: List of municipality dictionaries

    Returns:
        Dictionary mapping platform names to lists of municipalities
    """
    groups = group_items_by_field(municipalities, "platform", default_value="unknown")
    # Add special "no_code" category for municipalities without code_url
    groups["no_code"] = [m for m in municipalities if not m.get("code_url")]
    return groups


def _write_municipality_csv(
    csv_file: Path,
    municipalities: list[dict[str, str]],
    state_code: str,
    description: str,
) -> None:
    """
    Write municipalities to a CSV file.

    Args:
        csv_file: Path to CSV file
        municipalities: List of municipality dictionaries
        state_code: State code for logging
        description: Description of the municipalities being written
    """
    if not municipalities:
        return

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
                    "base_url": muni["url"],
                    "code_url": muni.get("code_url", ""),
                    "status": "ready",
                }
            )

    print(f"[{state_code}] ✓ Saved {len(municipalities)} {description} to {csv_file}")


def _save_municipalities_to_csv(
    municipalities: list[dict[str, str]],
    output_path: Path,
    output_name: str,
    state_code: str,
) -> None:
    """
    Save municipalities to CSV files grouped by platform.

    Args:
        municipalities: List of municipality dictionaries
        output_path: Directory to save CSV files
        output_name: Base name for CSV files
        state_code: State code for logging
    """
    output_path.mkdir(parents=True, exist_ok=True)
    groups = _group_municipalities_by_platform(municipalities)

    # Write CSV for each platform group if it has municipalities
    if "library" in groups and groups["library"]:
        _write_municipality_csv(
            output_path / f"{output_name}_library.csv",
            groups["library"],
            state_code,
            "Municode Library municipalities",
        )
    if "self_publishing" in groups and groups["self_publishing"]:
        _write_municipality_csv(
            output_path / f"{output_name}_self_publishing.csv",
            groups["self_publishing"],
            state_code,
            "Self-Publishing municipalities",
        )
    if "other" in groups and groups["other"]:
        _write_municipality_csv(
            output_path / f"{output_name}_other.csv",
            groups["other"],
            state_code,
            "Other platform municipalities",
        )


def _print_summary(municipalities: list[dict[str, str]], state_code: str) -> None:
    """
    Print summary statistics about extracted municipalities.

    Args:
        municipalities: List of municipality dictionaries
        state_code: State code for logging
    """
    groups = _group_municipalities_by_platform(municipalities)

    print(f"\n[{state_code}] {'=' * 60}")
    print(f"[{state_code}] SUMMARY")
    print(f"[{state_code}] {'=' * 60}")
    print(f"[{state_code}] Total municipalities: {len(municipalities)}")
    print(f"\n[{state_code}] By Platform:")
    print(
        f"[{state_code}]   📚 Municode Library:      {len(groups.get('library', []))} (ready for municode.py)"
    )
    print(
        f"[{state_code}]   ✏️  Self-Publishing:       {len(groups.get('self_publishing', []))} (needs different scraper)"
    )
    if groups.get("other"):
        print(f"[{state_code}]   🔗 Other platforms:       {len(groups['other'])}")
    print(
        f"[{state_code}]   ❌ No code found:         {len(groups.get('no_code', []))}"
    )

    if groups.get("library"):
        print(f"\n[{state_code}] Sample Municode Library municipalities:")
        for muni in sorted(groups["library"], key=lambda x: x["name"])[:3]:
            print(f"[{state_code}]   - {muni['name']}: {muni['code_url']}")

    if groups.get("self_publishing"):
        print(f"\n[{state_code}] Sample Self-Publishing municipalities:")
        for muni in sorted(groups["self_publishing"], key=lambda x: x["name"])[:3]:
            print(f"[{state_code}]   - {muni['name']}: {muni['code_url']}")


def extract_municipality_list(state_code: str, output_dir: str = None):
    """
    Extract list of municipalities from Municode library page.

    Args:
        state_code: Two-letter state code (e.g., 'MO')
        output_dir: Directory to save the CSV file (defaults to scripts/output/city_lists)
    """
    if output_dir is None:
        output_dir = str(DEFAULT_OUTPUT_DIR)

    state_code = state_code.upper()
    state_lower = state_code.lower()

    # Construct URL and output name from state code
    url = f"https://library.municode.com/{state_lower}"
    output_name = f"{state_lower}_cities"

    municipalities = []

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
                sleep_seconds=3,
                cloudflare_message=False,
            )
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
        output_path = Path(output_dir) / state_lower
        _save_municipalities_to_csv(
            municipalities, output_path, output_name, state_code
        )
        _print_summary(municipalities, state_code)
    else:
        print(
            f"\n[{state_code}] ✗ No municipalities found. Check the debug HTML file if generated."
        )

    return state_code, len(municipalities) if municipalities else 0


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
        lister_function=extract_municipality_list,
        output_dir=output_dir,
        item_type="municipalities",
    )


if __name__ == "__main__":
    states, output_dir_path = parse_lister_cli_args("list_municode_cities.py")

    # Run single or parallel mode
    if len(states) == 1:
        print(f"Using state code: {states[0]}")
        print(f"Output directory: {output_dir_path or 'default'}")
        extract_municipality_list(states[0], output_dir_path)
    else:
        scrape_states_parallel(states, output_dir_path)
