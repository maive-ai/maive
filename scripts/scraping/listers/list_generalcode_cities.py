"""
Simple script to extract jurisdiction names and URLs from General Code library pages.

Outputs a CSV file with columns:
  - name: Full jurisdiction name
  - slug: URL-safe slug for file naming
  - base_url: The General Code library page
  - code_url: Full URL to codes (use with appropriate scraper)
  - platform: Which platform hosts the code (ecode360, municipal_codes, codepublishing)
  - status: 'ready' or 'no_code_found'

Usage: python list_generalcode_cities.py <STATE_CODE> <NAME> [--output-dir DIR]
Example: python list_generalcode_cities.py UT ut_cities
Example: python list_generalcode_cities.py UT ut_cities --output-dir output
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def extract_jurisdiction_list(state_code: str, output_name: str, output_dir: str = "output"):
    """
    Extract list of jurisdictions from General Code library page.

    Args:
        state_code: Two-letter state code (e.g., 'UT')
        output_name: Name for the output file (without extension)
        output_dir: Directory to save the CSV file (defaults to "output")
    """
    # Construct the URL
    url = f"https://www.generalcode.com/source-library/?state={state_code}"

    jurisdictions = []

    with sync_playwright() as p:
        print(f"Launching browser and navigating to {url}")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to the page
            page.goto(url, wait_until="domcontentloaded")

            # Wait for content to load - but continue even if networkidle times out
            print("Waiting for content to load...")
            try:
                page.wait_for_load_state("networkidle", timeout=30000)
            except Exception as e:
                print(f"  ⚠ Network idle timeout (continuing anyway): {str(e)[:50]}")

            # Give extra time for any dynamic content
            import time
            print("  Waiting a few seconds for page to fully load...")
            time.sleep(3)

            # Create output directory structure: output_dir/generalcode_city_lists/
            output_path = Path(output_dir) / "generalcode_city_lists"
            output_path.mkdir(parents=True, exist_ok=True)

            # Save page content for debugging
            html_content = page.content()
            debug_file = output_path / f"{output_name}_debug.html"
            debug_file.write_text(html_content, encoding='utf-8')
            print(f"Saved page HTML to {debug_file}")

            # Also take a screenshot
            screenshot_file = output_path / f"{output_name}_screenshot.png"
            page.screenshot(path=str(screenshot_file), full_page=True)
            print(f"Saved screenshot to {screenshot_file}")

            # Extract jurisdiction names AND URLs
            jurisdictions_extracted = page.evaluate("""
                () => {
                    const jurisdictions = [];
                    const seen = new Set();

                    // Find all links that point to code hosting platforms
                    const links = document.querySelectorAll('a[href]');

                    links.forEach(link => {
                        const href = link.href;
                        const text = link.textContent.trim();

                        // Check if this is a code hosting link
                        const isEcode360 = href.includes('ecode360.com/');
                        const isMunicipalCodes = href.includes('.municipal.codes/');
                        const isCodePublishing = href.includes('codepublishing.com/');
                        const isGeneralCode = href.includes('.generalcode.com/') && !href.includes('www.generalcode.com');

                        if ((isEcode360 || isMunicipalCodes || isCodePublishing || isGeneralCode) &&
                            text && text.length > 1 && text.length < 100) {

                            // Filter out common non-jurisdiction items
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

                            // Avoid duplicates
                            if (!shouldExclude && !seen.has(text)) {
                                seen.add(text);

                                // Determine platform
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

            jurisdictions = jurisdictions_extracted
            print(f"Found {len(jurisdictions)} jurisdictions")

            # Verify each URL
            print("\nVerifying code URLs...")
            for i, juris in enumerate(jurisdictions):
                try:
                    print(f"  {i + 1}/{len(jurisdictions)}: {juris['name']} ({juris['platform']})")

                    # Verify the URL by navigating to it
                    try:
                        page.goto(juris['url'], wait_until="domcontentloaded", timeout=10000)
                        page.wait_for_load_state("networkidle", timeout=5000)

                        # Get the final URL after any redirects
                        final_url = page.url
                        juris['code_url'] = final_url

                        if final_url != juris['url']:
                            print(f"    ✓ Found (redirected): {final_url}")
                        else:
                            print(f"    ✓ Found: {final_url}")

                    except Exception as e:
                        print(f"    ⚠ Could not verify URL (timeout/error): {juris['url']}")
                        juris['code_url'] = juris['url']

                    # Small delay to be nice to the server
                    import time
                    time.sleep(0.5)

                except Exception as e:
                    print(f"    ✗ Error: {str(e)}")
                    juris['code_url'] = juris['url']

            # If we didn't find anything, print helpful debug info
            if not jurisdictions:
                print("\nNo jurisdictions found with standard selectors.")
                print("Check the debug HTML and screenshot for manual inspection.")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

    # Save to CSV
    if jurisdictions:
        import csv
        import re

        # Create output directory structure: output_dir/generalcode_city_lists/
        output_path = Path(output_dir) / "generalcode_city_lists"
        output_path.mkdir(parents=True, exist_ok=True)

        # Group by platform
        ecode360_juris = [j for j in jurisdictions if j.get('platform') == 'ecode360']
        municipal_codes_juris = [j for j in jurisdictions if j.get('platform') == 'municipal_codes']
        codepublishing_juris = [j for j in jurisdictions if j.get('platform') == 'codepublishing']
        generalcode_juris = [j for j in jurisdictions if j.get('platform') == 'generalcode']
        other_juris = [j for j in jurisdictions if j.get('platform') == 'unknown']

        def write_csv(filename, juris_list, description):
            if not juris_list:
                return

            csv_file = output_path / filename
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'slug', 'base_url', 'code_url', 'platform', 'status'])
                writer.writeheader()

                for juris in sorted(juris_list, key=lambda x: x['name']):
                    # Create a URL-safe slug from the name
                    # Remove common prefixes
                    name_for_slug = juris['name']
                    for prefix in ['City of ', 'Town of ', 'Village of ', 'County of ']:
                        if name_for_slug.startswith(prefix):
                            name_for_slug = name_for_slug[len(prefix):]
                            break

                    slug = re.sub(r'[^a-z0-9]+', '-', name_for_slug.lower()).strip('-')

                    writer.writerow({
                        'name': juris['name'],
                        'slug': slug,
                        'base_url': url,
                        'code_url': juris.get('code_url', ''),
                        'platform': juris.get('platform', 'unknown'),
                        'status': 'ready' if juris.get('code_url') else 'no_code_found'
                    })

            print(f"✓ Saved {len(juris_list)} {description} to {csv_file}")

        # Write separate CSV files by platform
        write_csv(f"{output_name}_ecode360.csv", ecode360_juris, "eCode360 jurisdictions")
        write_csv(f"{output_name}_municipal_codes.csv", municipal_codes_juris, "Municipal.codes jurisdictions")
        write_csv(f"{output_name}_codepublishing.csv", codepublishing_juris, "CodePublishing jurisdictions")
        write_csv(f"{output_name}_generalcode.csv", generalcode_juris, "General Code subdomain jurisdictions")
        if other_juris:
            write_csv(f"{output_name}_other.csv", other_juris, "Other platform jurisdictions")

        # Write combined CSV
        csv_file = output_path / f"{output_name}_all.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'slug', 'base_url', 'code_url', 'platform', 'status'])
            writer.writeheader()

            for juris in sorted(jurisdictions, key=lambda x: x['name']):
                # Create a URL-safe slug from the name
                name_for_slug = juris['name']
                for prefix in ['City of ', 'Town of ', 'Village of ', 'County of ']:
                    if name_for_slug.startswith(prefix):
                        name_for_slug = name_for_slug[len(prefix):]
                        break

                slug = re.sub(r'[^a-z0-9]+', '-', name_for_slug.lower()).strip('-')

                writer.writerow({
                    'name': juris['name'],
                    'slug': slug,
                    'base_url': url,
                    'code_url': juris.get('code_url', ''),
                    'platform': juris.get('platform', 'unknown'),
                    'status': 'ready' if juris.get('code_url') else 'no_code_found'
                })

        print(f"✓ Saved {len(jurisdictions)} total jurisdictions to {csv_file}")

        # Print statistics
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total jurisdictions: {len(jurisdictions)}")
        print(f"\nBy Platform:")
        print(f"  🔷 eCode360:              {len(ecode360_juris)} (use general_code_publish.py)")
        print(f"  🔶 Municipal.codes:       {len(municipal_codes_juris)} (use general_code_subdomain.py)")
        print(f"  🔸 CodePublishing:        {len(codepublishing_juris)} (use general_code_publish.py)")
        print(f"  🟦 General Code subdomain: {len(generalcode_juris)} (use general_code_subdomain.py)")
        if other_juris:
            print(f"  🔗 Other platforms:       {len(other_juris)}")

        # Show sample from each platform
        if ecode360_juris:
            print(f"\nSample eCode360 jurisdictions:")
            for juris in sorted(ecode360_juris, key=lambda x: x['name'])[:3]:
                print(f"  - {juris['name']}: {juris['code_url']}")

        if municipal_codes_juris:
            print(f"\nSample Municipal.codes jurisdictions:")
            for juris in sorted(municipal_codes_juris, key=lambda x: x['name'])[:3]:
                print(f"  - {juris['name']}: {juris['code_url']}")

        if codepublishing_juris:
            print(f"\nSample CodePublishing jurisdictions:")
            for juris in sorted(codepublishing_juris, key=lambda x: x['name'])[:3]:
                print(f"  - {juris['name']}: {juris['code_url']}")

        if generalcode_juris:
            print(f"\nSample General Code subdomain jurisdictions:")
            for juris in sorted(generalcode_juris, key=lambda x: x['name'])[:3]:
                print(f"  - {juris['name']}: {juris['code_url']}")
    else:
        print("\n✗ No jurisdictions found. Check the debug HTML file and screenshot.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python list_generalcode_cities.py <STATE_CODE> <NAME> [--output-dir DIR]")
        print('Example: python list_generalcode_cities.py UT ut_cities')
        print('Example: python list_generalcode_cities.py UT ut_cities --output-dir output')
        sys.exit(1)

    state_code = sys.argv[1].upper()
    output_name = sys.argv[2]

    # Parse optional output directory
    output_dir_path = "output"
    if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
        if len(sys.argv) > 4:
            output_dir_path = sys.argv[4]

    print(f"Using state code: {state_code}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    extract_jurisdiction_list(state_code, output_name, output_dir_path)
