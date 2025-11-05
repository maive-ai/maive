"""
Simple script to extract municipality names and full code URLs from Municode library pages.
Clicks into each municipality page to find the actual code/ordinance document URL.

Outputs a CSV file with columns:
  - name: Full municipality name
  - slug: URL-safe slug for file naming
  - base_url: Municipality home page URL
  - code_url: Full URL to codes/ordinances (use this with municode.py)
  - status: 'ready' or 'no_code_found'

Usage: python list_municode_cities.py <URL> <NAME> [--output-dir DIR]
Example: python list_municode_cities.py "https://library.municode.com/ut#P" ut_cities
Example: python list_municode_cities.py "https://library.municode.com/ut#P" ut_cities --output-dir output
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def extract_municipality_list(url: str, output_name: str, output_dir: str = "output"):
    """
    Extract list of municipalities from Municode library page.

    Args:
        url: The Municode library URL (e.g., https://library.municode.com/ut#P)
        output_name: Name for the output file (without extension)
        output_dir: Directory to save the CSV file (defaults to "output")
    """
    municipalities = []

    with sync_playwright() as p:
        print(f"Launching browser and navigating to {url}")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to the page
            page.goto(url, wait_until="domcontentloaded")

            # Wait for content to load
            print("Waiting for content to load...")
            page.wait_for_load_state("networkidle", timeout=30000)

            # Give extra time for any dynamic content
            import time
            time.sleep(3)

            # Create output directory structure: output_dir/municode_city_lists/
            output_path = Path(output_dir) / "municode_city_lists"
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

            # Extract municipality names AND URLs
            municipalities_extracted = page.evaluate("""
                () => {
                    const municipalities = [];
                    const seen = new Set();

                    // Try getting all links that might be municipality links
                    const links = document.querySelectorAll('a');
                    links.forEach(link => {
                        const href = link.href;
                        const text = link.textContent.trim();

                        // Filter out common non-municipality items
                        const excludePatterns = [
                            'search', 'help', 'login', 'skip to', 'municode library',
                            'order a', 'contact', 'about', 'privacy', 'terms'
                        ];

                        const shouldExclude = excludePatterns.some(pattern =>
                            text.toLowerCase().includes(pattern)
                        );

                        // Exclude single letters (likely alphabet navigation)
                        const isSingleLetter = text.length === 1 && /^[A-Z]$/i.test(text);

                        // If link goes to a municipality page and has reasonable text
                        if (href && href.includes('library.municode.com') &&
                            text && text.length > 1 && text.length < 100 &&
                            !shouldExclude && !isSingleLetter) {

                            // Avoid duplicates
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

            municipalities = municipalities_extracted
            print(f"Found {len(municipalities)} municipalities")

            # Now click into each municipality to get the full code URL
            print("\nExtracting full code URLs...")
            for i, muni in enumerate(municipalities):
                try:
                    print(f"  {i + 1}/{len(municipalities)}: {muni['name']}")

                    # Navigate to the municipality page
                    page.goto(muni['url'], wait_until="domcontentloaded")
                    page.wait_for_load_state("networkidle", timeout=10000)

                    # Look for the main code/ordinance link
                    # Common patterns: "Code of Ordinances", "Municipal Code", etc.
                    code_url = page.evaluate("""
                        () => {
                            // Look for common code document patterns
                            const patterns = [
                                'code of ordinances',
                                'municipal code',
                                'city code',
                                'county code',
                                'land development code',
                                'zoning code',
                                'development code'
                            ];

                            // Search for links containing these patterns
                            const links = document.querySelectorAll('a');
                            for (const link of links) {
                                const text = link.textContent.toLowerCase().trim();
                                const href = link.href;

                                // Check for library.municode.com /codes/ pattern
                                for (const pattern of patterns) {
                                    if (text.includes(pattern) && href.includes('/codes/')) {
                                        return href;
                                    }
                                }

                                // Check for municipalcodeonline.com pattern
                                for (const pattern of patterns) {
                                    if (text.includes(pattern) && href.includes('municipalcodeonline.com')) {
                                        return href;
                                    }
                                }
                            }

                            // Fallback: find any link with /codes/ in URL
                            for (const link of links) {
                                if (link.href.includes('/codes/') &&
                                    !link.href.includes('/search') &&
                                    !link.href.includes('/compare')) {
                                    return link.href;
                                }
                            }

                            // Fallback: find any municipalcodeonline.com link
                            for (const link of links) {
                                if (link.href.includes('municipalcodeonline.com/book')) {
                                    return link.href;
                                }
                            }

                            return null;
                        }
                    """)

                    if code_url:
                        # Navigate to the code URL to check for redirects
                        try:
                            page.goto(code_url, wait_until="domcontentloaded", timeout=10000)
                            page.wait_for_load_state("networkidle", timeout=5000)

                            # Get the final URL after any redirects
                            final_url = page.url
                            muni['code_url'] = final_url

                            # Determine platform based on FINAL URL
                            if 'library.municode.com' in final_url and '/codes/' in final_url:
                                muni['platform'] = 'library'
                                if final_url != code_url:
                                    print(f"    ✓ Found (Library, redirected): {final_url}")
                                else:
                                    print(f"    ✓ Found (Library): {final_url}")
                            elif 'municipalcodeonline.com' in final_url:
                                muni['platform'] = 'self_publishing'
                                if final_url != code_url:
                                    print(f"    ✓ Found (Self-Publishing, redirected): {final_url}")
                                else:
                                    print(f"    ✓ Found (Self-Publishing): {final_url}")
                            else:
                                muni['platform'] = 'other'
                                print(f"    ✓ Found (Other): {final_url}")
                        except Exception as e:
                            print(f"    ⚠ Could not verify URL (timeout/error): {code_url}")
                            muni['code_url'] = code_url
                            muni['platform'] = 'unknown'
                    else:
                        print(f"    ⚠ No code URL found")
                        muni['code_url'] = None
                        muni['platform'] = None

                    # Small delay to be nice to the server
                    import time
                    time.sleep(0.5)

                except Exception as e:
                    print(f"    ✗ Error: {str(e)}")
                    muni['code_url'] = None
                    muni['platform'] = None

            # If we didn't find anything, try to get the page content for debugging
            if not municipalities:
                print("\nNo municipalities found with standard selectors.")
                print("Attempting to extract all text content for manual inspection...")

                # Save the full page HTML for debugging
                html_content = page.content()
                debug_file = output_file.replace('.txt', '_debug.html')
                Path(debug_file).write_text(html_content, encoding='utf-8')
                print(f"Saved page HTML to {debug_file} for inspection")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

    # Save to files
    if municipalities:
        import csv
        import re

        # Create output directory structure: output_dir/municode_city_lists/
        output_path = Path(output_dir) / "municode_city_lists"
        output_path.mkdir(parents=True, exist_ok=True)

        # Split municipalities by platform
        library_munis = [m for m in municipalities if m.get('platform') == 'library']
        self_pub_munis = [m for m in municipalities if m.get('platform') == 'self_publishing']
        other_munis = [m for m in municipalities if m.get('platform') == 'other']
        no_code_munis = [m for m in municipalities if not m.get('code_url')]

        def write_csv(filename, munis_list, description):
            if not munis_list:
                return

            csv_file = output_path / filename
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['name', 'slug', 'base_url', 'code_url', 'status'])
                writer.writeheader()

                for muni in sorted(munis_list, key=lambda x: x['name']):
                    # Create a URL-safe slug from the name
                    slug = re.sub(r'[^a-z0-9]+', '-', muni['name'].lower()).strip('-')

                    writer.writerow({
                        'name': muni['name'],
                        'slug': slug,
                        'base_url': muni['url'],
                        'code_url': muni.get('code_url', ''),
                        'status': 'ready'
                    })

            print(f"✓ Saved {len(munis_list)} {description} to {csv_file}")

        # Write separate CSV files
        write_csv(f"{output_name}_library.csv", library_munis, "Municode Library municipalities")
        write_csv(f"{output_name}_self_publishing.csv", self_pub_munis, "Self-Publishing municipalities")
        if other_munis:
            write_csv(f"{output_name}_other.csv", other_munis, "Other platform municipalities")

        # Print statistics
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total municipalities: {len(municipalities)}")
        print(f"\nBy Platform:")
        print(f"  📚 Municode Library:      {len(library_munis)} (ready for municode.py)")
        print(f"  ✏️  Self-Publishing:       {len(self_pub_munis)} (needs different scraper)")
        if other_munis:
            print(f"  🔗 Other platforms:       {len(other_munis)}")
        print(f"  ❌ No code found:         {len(no_code_munis)}")

        # Show sample from each platform
        if library_munis:
            print(f"\nSample Municode Library municipalities:")
            for muni in sorted(library_munis, key=lambda x: x['name'])[:3]:
                print(f"  - {muni['name']}: {muni['code_url']}")

        if self_pub_munis:
            print(f"\nSample Self-Publishing municipalities:")
            for muni in sorted(self_pub_munis, key=lambda x: x['name'])[:3]:
                print(f"  - {muni['name']}: {muni['code_url']}")
    else:
        print("\n✗ No municipalities found. Check the debug HTML file if generated.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python list_municode_cities.py <URL> <NAME> [--output-dir DIR]")
        print('Example: python list_municode_cities.py "https://library.municode.com/ut#P" ut_cities')
        print('Example: python list_municode_cities.py "https://library.municode.com/ut#P" ut_cities --output-dir output')
        sys.exit(1)

    url = sys.argv[1]
    output_name = sys.argv[2]

    # Parse optional output directory
    output_dir_path = "output"
    if len(sys.argv) > 3 and sys.argv[3] == "--output-dir":
        if len(sys.argv) > 4:
            output_dir_path = sys.argv[4]

    print(f"Using URL: {url}")
    print(f"Output name: {output_name}")
    print(f"Output directory: {output_dir_path}")

    extract_municipality_list(url, output_name, output_dir_path)
