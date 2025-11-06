"""
Simple script to extract municipality names and URLs from AM Legal regions pages.
Clicks into each municipality page to find the actual code URL.

Outputs a CSV file with columns:
  - name: Full municipality name
  - slug: URL-safe slug for file naming
  - base_url: Municipality home page URL
  - code_url: Full URL to codes (use this with amlegal.py)
  - status: 'ready' or 'no_code_found'

Usage: python list_amlegal_cities.py <URL> <NAME> [--output-dir DIR]
Example: python list_amlegal_cities.py "https://codelibrary.amlegal.com/regions/ut" ut_cities
Example: python list_amlegal_cities.py "https://codelibrary.amlegal.com/regions/ut" ut_cities --output-dir output
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def extract_municipality_list(url: str, output_name: str, output_dir: str = "output"):
    """
    Extract list of municipalities from AM Legal regions page.

    Args:
        url: The AM Legal regions URL (e.g., https://codelibrary.amlegal.com/regions/ut)
        output_name: Name for the output file (without extension)
        output_dir: Directory to save the CSV file (defaults to "output")
    """
    municipalities = []

    with sync_playwright() as p:
        print(f"Launching browser and navigating to {url}")
        # Launch in non-headless mode to bypass Cloudflare bot detection
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        # Add more realistic browser context to avoid detection
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            # Navigate to the page
            page.goto(url, wait_until="domcontentloaded")

            # Wait for content to load - but continue even if networkidle times out
            print("Waiting for content to load...")
            print("  ℹ️  If you see a Cloudflare challenge, please complete it manually...")
            try:
                page.wait_for_load_state("networkidle", timeout=60000)
            except Exception as e:
                print(f"  ⚠ Network idle timeout (continuing anyway): {str(e)[:50]}")

            # Give extra time for Cloudflare challenge and dynamic content
            import time
            print("  Waiting 10 seconds for page to fully load...")
            time.sleep(10)

            # Create output directory structure: output_dir/amlegal_city_lists/
            output_path = Path(output_dir) / "amlegal_city_lists"
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

            municipalities = municipalities_extracted
            print(f"Found {len(municipalities)} municipalities")

            # For AM Legal, the URLs should already be the code URLs
            # But let's verify and clean them up
            print("\nVerifying code URLs...")
            for i, muni in enumerate(municipalities):
                try:
                    print(f"  {i + 1}/{len(municipalities)}: {muni['name']}")

                    # AM Legal URLs typically go directly to the code
                    # Format: https://codelibrary.amlegal.com/codes/{state}/{city}/latest/{code_name}
                    code_url = muni['url']

                    # Verify the URL by navigating to it
                    try:
                        page.goto(code_url, wait_until="domcontentloaded", timeout=10000)
                        page.wait_for_load_state("networkidle", timeout=5000)

                        # Get the final URL after any redirects
                        final_url = page.url

                        muni['code_url'] = final_url

                        if final_url != code_url:
                            print(f"    ✓ Found (redirected): {final_url}")
                        else:
                            print(f"    ✓ Found: {final_url}")

                    except Exception as e:
                        print(f"    ⚠ Could not verify URL (timeout/error): {code_url}")
                        muni['code_url'] = code_url

                    # Small delay to be nice to the server
                    import time
                    time.sleep(0.5)

                except Exception as e:
                    print(f"    ✗ Error: {str(e)}")
                    muni['code_url'] = muni['url']

            # If we didn't find anything, print helpful debug info
            if not municipalities:
                print("\nNo municipalities found with standard selectors.")
                print("Check the debug HTML and screenshot for manual inspection.")

        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            browser.close()

    # Save to CSV
    if municipalities:
        import csv
        import re

        # Create output directory structure: output_dir/amlegal_city_lists/
        output_path = Path(output_dir) / "amlegal_city_lists"
        output_path.mkdir(parents=True, exist_ok=True)

        csv_file = output_path / f"{output_name}.csv"
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'slug', 'base_url', 'code_url', 'status'])
            writer.writeheader()

            for muni in sorted(municipalities, key=lambda x: x['name']):
                # Create a URL-safe slug from the name
                slug = re.sub(r'[^a-z0-9]+', '-', muni['name'].lower()).strip('-')

                writer.writerow({
                    'name': muni['name'],
                    'slug': slug,
                    'base_url': url,  # The regions page
                    'code_url': muni.get('code_url', ''),
                    'status': 'ready' if muni.get('code_url') else 'no_code_found'
                })

        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total municipalities: {len(municipalities)}")
        print(f"✓ Saved to {csv_file}")

        # Show sample municipalities
        if municipalities:
            print(f"\nSample municipalities:")
            for muni in sorted(municipalities, key=lambda x: x['name'])[:5]:
                print(f"  - {muni['name']}: {muni.get('code_url', 'N/A')}")
    else:
        print("\n✗ No municipalities found. Check the debug HTML file and screenshot.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python list_amlegal_cities.py <URL> <NAME> [--output-dir DIR]")
        print('Example: python list_amlegal_cities.py "https://codelibrary.amlegal.com/regions/ut" ut_cities')
        print('Example: python list_amlegal_cities.py "https://codelibrary.amlegal.com/regions/ut" ut_cities --output-dir output')
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
