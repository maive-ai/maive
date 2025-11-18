#!/usr/bin/env python3
"""
Comprehensive quality check tool for scraped municipal code database.

Features:
- Analyze all scraped files and generate quality report
- Find missing jurisdictions from city_lists/
- Create snapshots for before/after comparison
- Compare snapshots to track improvements
- Optional deletion of BAD quality files
"""

import argparse
import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


# Paths
BASE_DIR = Path("output")
CODES_DIR = BASE_DIR / "codes"
CITY_LISTS_DIR = BASE_DIR / "city_lists"
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
MISSING_DIR = BASE_DIR / "missing_jurisdictions"
QUALITY_REPORT = BASE_DIR / "scraper_quality_report.json"

# Scraper type mapping from CSV file types
SCRAPER_MAPPING = {
    'amlegal': 'amlegal.py',
    'municode': 'municode.py',
    'library': 'municode.py',
    'ecode360': 'ecode360.py',
    'codepublishing': 'general_code_publish.py',
    'municipal_codes': 'general_code_subdomain.py',
    'encode_plus': 'encode_plus.py',
    'self_publishing': 'municipalcodeonline.py',
    'all': 'various',
}


def check_file(file_path: Path) -> dict:
    """Check if a single JSON file looks complete."""
    result = {
        'file': file_path.name,
        'state': file_path.parent.name,
        'valid_json': False,
        'has_metadata': False,
        'has_sections': False,
        'section_count': 0,
        'sections_with_html': 0,
        'sections_with_errors': 0,
        'leaf_node_count': 0,
        'leaf_nodes_with_html': 0,
        'file_size_mb': file_path.stat().st_size / (1024 * 1024),
        'scraper': 'unknown',
        'status': 'UNKNOWN',
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        result['valid_json'] = True

        # Check for metadata
        if 'metadata' in data:
            result['has_metadata'] = True
            result['scraper'] = data['metadata'].get('scraper', 'unknown')

        # Check for sections
        if 'sections' in data:
            result['has_sections'] = True
            sections = data['sections']
            result['section_count'] = len(sections)

            # Count sections with HTML content and track leaf nodes
            for section in sections:
                if 'html' in section:
                    result['sections_with_html'] += 1
                if 'html_error' in section:
                    result['sections_with_errors'] += 1

                # A leaf node is one that either:
                # 1. Explicitly has has_children=False, or
                # 2. Doesn't have the has_children field (implicitly a leaf)
                # Parent nodes have has_children=True
                has_children = section.get('has_children', False)
                if not has_children:
                    result['leaf_node_count'] += 1
                    if 'html' in section:
                        result['leaf_nodes_with_html'] += 1

        # Determine overall status using leaf node quality when available
        if result['section_count'] == 0:
            result['status'] = 'EMPTY'
        elif result['sections_with_html'] == 0:
            result['status'] = 'BAD'
        else:
            # Use leaf node quality if we can identify leaf nodes
            if result['leaf_node_count'] > 0:
                leaf_quality = (result['leaf_nodes_with_html'] / result['leaf_node_count']) * 100
                # Use leaf quality for status determination
                if leaf_quality >= 80:
                    result['status'] = 'GOOD'
                elif leaf_quality >= 30:
                    result['status'] = 'PARTIAL'
                else:
                    result['status'] = 'BAD'
            else:
                # Fall back to overall percentage if no leaf node info
                html_percentage = (result['sections_with_html'] / result['section_count']) * 100
                error_percentage = (result['sections_with_errors'] / result['section_count']) * 100

                if html_percentage >= 80 and error_percentage < 20:
                    result['status'] = 'GOOD'
                elif html_percentage >= 30:
                    result['status'] = 'PARTIAL'
                else:
                    result['status'] = 'BAD'

    except json.JSONDecodeError:
        result['status'] = 'BAD'
    except Exception:
        result['status'] = 'BAD'

    return result


def analyze_codes_directory() -> Tuple[List[dict], dict]:
    """Analyze all files in codes/ directory and return results."""
    if not CODES_DIR.exists():
        print(f"Error: {CODES_DIR} does not exist")
        return [], {}

    # Find all JSON files
    json_files = sorted(CODES_DIR.rglob('*.json'))

    print(f"\n{'='*80}")
    print(f"CHECKING {len(json_files)} FILES")
    print(f"{'='*80}\n")
    print("Processing", end='', flush=True)

    results = []
    for i, file_path in enumerate(json_files):
        result = check_file(file_path)
        results.append(result)

        # Progress indicator
        if (i + 1) % 50 == 0:
            print(f"...{i+1}", end='', flush=True)
        elif (i + 1) % 10 == 0:
            print(".", end='', flush=True)

    print(f"...{len(json_files)}\n")

    # Organize results
    by_status = defaultdict(list)
    by_scraper = defaultdict(list)
    by_state = defaultdict(list)

    for r in results:
        by_status[r['status']].append(r)
        by_scraper[r['scraper']].append(r)
        by_state[r['state']].append(r)

    organized = {
        'by_status': by_status,
        'by_scraper': by_scraper,
        'by_state': by_state,
    }

    return results, organized


def print_quality_report(results: List[dict], organized: dict):
    """Print comprehensive quality report."""
    by_status = organized['by_status']
    by_scraper = organized['by_scraper']
    by_state = organized['by_state']

    # Overall Summary
    print(f"\n{'='*80}")
    print(f"OVERALL SUMMARY")
    print(f"{'='*80}")

    total_sections = sum(r['section_count'] for r in results)
    total_with_html = sum(r['sections_with_html'] for r in results)
    total_with_errors = sum(r['sections_with_errors'] for r in results)
    total_size_mb = sum(r['file_size_mb'] for r in results)

    print(f"Total files: {len(results)}")
    print(f"Total size: {total_size_mb:.1f} MB")
    print(f"Total sections: {total_sections:,}")
    print(f"  With HTML: {total_with_html:,} ({(total_with_html/total_sections*100) if total_sections else 0:.1f}%)")
    print(f"  With errors: {total_with_errors:,} ({(total_with_errors/total_sections*100) if total_sections else 0:.1f}%)")

    # Status breakdown
    print(f"\n{'='*80}")
    print(f"BY STATUS")
    print(f"{'='*80}")

    status_order = ['GOOD', 'PARTIAL', 'BAD', 'EMPTY', 'UNKNOWN']
    status_symbols = {
        'GOOD': '✓',
        'PARTIAL': '⚠',
        'BAD': '✗',
        'EMPTY': '○',
        'UNKNOWN': '?'
    }

    for status in status_order:
        files = by_status.get(status, [])
        if files:
            count = len(files)
            pct = (count / len(results)) * 100
            sections = sum(r['section_count'] for r in files)
            with_html = sum(r['sections_with_html'] for r in files)
            html_pct = (with_html / sections * 100) if sections else 0

            symbol = status_symbols.get(status, '?')
            print(f"{symbol} {status:8s}: {count:4d} files ({pct:5.1f}%) | "
                  f"{sections:6,} sections, {with_html:6,} with HTML ({html_pct:5.1f}%)")

    # Scraper breakdown
    print(f"\n{'='*80}")
    print(f"BY SCRAPER")
    print(f"{'='*80}")

    for scraper in sorted(by_scraper.keys()):
        files = by_scraper[scraper]
        count = len(files)
        sections = sum(r['section_count'] for r in files)
        with_html = sum(r['sections_with_html'] for r in files)
        with_errors = sum(r['sections_with_errors'] for r in files)
        html_pct = (with_html / sections * 100) if sections else 0
        error_pct = (with_errors / sections * 100) if sections else 0

        # Count by status
        good = len([r for r in files if r['status'] == 'GOOD'])
        partial = len([r for r in files if r['status'] == 'PARTIAL'])
        bad = len([r for r in files if r['status'] == 'BAD'])

        print(f"\n{scraper}")
        print(f"  Files: {count} (✓{good} ⚠{partial} ✗{bad})")
        print(f"  Sections: {sections:,} total, {with_html:,} with HTML ({html_pct:.1f}%), {with_errors:,} errors ({error_pct:.1f}%)")

    # State breakdown
    print(f"\n{'='*80}")
    print(f"BY STATE")
    print(f"{'='*80}")

    for state in sorted(by_state.keys()):
        files = by_state[state]
        count = len(files)
        sections = sum(r['section_count'] for r in files)
        with_html = sum(r['sections_with_html'] for r in files)
        html_pct = (with_html / sections * 100) if sections else 0

        good = len([r for r in files if r['status'] == 'GOOD'])
        partial = len([r for r in files if r['status'] == 'PARTIAL'])
        bad = len([r for r in files if r['status'] == 'BAD'])

        print(f"{state:4s}: {count:3d} files (✓{good:3d} ⚠{partial:3d} ✗{bad:3d}) | "
              f"{sections:6,} sections, {html_pct:5.1f}% with HTML")

    # Worst files
    print(f"\n{'='*80}")
    print(f"WORST 10 FILES (by HTML content %)")
    print(f"{'='*80}")

    sorted_by_html_pct = sorted(
        [r for r in results if r['section_count'] > 0],
        key=lambda r: (r['sections_with_html'] / r['section_count']) if r['section_count'] else 0
    )

    for r in sorted_by_html_pct[:10]:
        html_pct = (r['sections_with_html'] / r['section_count'] * 100) if r['section_count'] else 0
        leaf_info = ""
        if r.get('leaf_node_count', 0) > 0:
            leaf_pct = (r['leaf_nodes_with_html'] / r['leaf_node_count'] * 100)
            leaf_info = f" [Leaf: {r['leaf_nodes_with_html']}/{r['leaf_node_count']} ({leaf_pct:5.1f}%)]"
        print(f"  {r['state']}/{r['file']:45s} | {r['scraper']:15s} | "
              f"{r['sections_with_html']:4d}/{r['section_count']:4d} sections ({html_pct:5.1f}%){leaf_info}")

    # Best files
    print(f"\n{'='*80}")
    print(f"BEST 10 FILES (largest, >80% HTML content)")
    print(f"{'='*80}")

    good_files = [r for r in results if r['section_count'] > 0 and
                  (r['sections_with_html'] / r['section_count']) > 0.8]
    sorted_by_size = sorted(good_files, key=lambda r: r['section_count'], reverse=True)

    for r in sorted_by_size[:10]:
        html_pct = (r['sections_with_html'] / r['section_count'] * 100) if r['section_count'] else 0
        leaf_info = ""
        if r.get('leaf_node_count', 0) > 0:
            leaf_pct = (r['leaf_nodes_with_html'] / r['leaf_node_count'] * 100)
            leaf_info = f" [Leaf: {r['leaf_nodes_with_html']}/{r['leaf_node_count']} ({leaf_pct:5.1f}%)]"
        print(f"  {r['state']}/{r['file']:45s} | {r['scraper']:15s} | "
              f"{r['sections_with_html']:4d}/{r['section_count']:4d} sections ({html_pct:5.1f}%){leaf_info}")

    print(f"\n{'='*80}\n")


def save_quality_report(results: List[dict], organized: dict) -> Path:
    """Save detailed quality report to JSON."""
    by_status = organized['by_status']
    by_scraper = organized['by_scraper']

    total_sections = sum(r['section_count'] for r in results)
    total_with_html = sum(r['sections_with_html'] for r in results)
    total_with_errors = sum(r['sections_with_errors'] for r in results)

    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_files': len(results),
            'total_sections': total_sections,
            'total_with_html': total_with_html,
            'total_with_errors': total_with_errors,
            'html_percentage': (total_with_html/total_sections*100) if total_sections else 0,
            'error_percentage': (total_with_errors/total_sections*100) if total_sections else 0,
        },
        'by_status': {status: len(files) for status, files in by_status.items()},
        'by_scraper': {
            scraper: {
                'count': len(files),
                'sections': sum(r['section_count'] for r in files),
                'with_html': sum(r['sections_with_html'] for r in files),
                'with_errors': sum(r['sections_with_errors'] for r in files),
            }
            for scraper, files in by_scraper.items()
        },
        'files': results
    }

    QUALITY_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(QUALITY_REPORT, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"Detailed report saved to: {QUALITY_REPORT}")
    return QUALITY_REPORT


def get_scraped_jurisdictions() -> Dict[str, Set[str]]:
    """Get all jurisdiction slugs that currently exist in codes/ directory."""
    scraped = defaultdict(set)

    if not CODES_DIR.exists():
        return scraped

    for state_dir in CODES_DIR.iterdir():
        if state_dir.is_dir():
            state = state_dir.name
            for file in state_dir.glob("*.json"):
                slug = file.stem
                scraped[state].add(slug)

    return scraped


def parse_city_list_filename(filename: str) -> Tuple[str, str]:
    """Parse city list filename to extract state and scraper type."""
    name = filename.replace('.csv', '')
    parts = name.split('_')
    state = parts[0]

    scraper_type = 'various'
    for key, scraper in SCRAPER_MAPPING.items():
        if key in name:
            scraper_type = scraper
            break

    return state, scraper_type


def load_city_list(csv_path: Path) -> List[Dict]:
    """Load a city list CSV file."""
    cities = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cities.append(row)
    return cities


def load_all_expected_jurisdictions(state_filter: str = None) -> Dict[str, Dict[str, List[Dict]]]:
    """Load all expected jurisdictions from city_lists/ organized by state and scraper."""
    expected = defaultdict(lambda: defaultdict(list))

    if not CITY_LISTS_DIR.exists():
        return expected

    for state_dir in CITY_LISTS_DIR.iterdir():
        if not state_dir.is_dir():
            continue

        state = state_dir.name
        if state_filter and state != state_filter:
            continue

        # Recursively search for CSV files in subdirectories
        for csv_file in state_dir.rglob("*.csv"):
            # Infer scraper from directory name
            parent_dir_name = csv_file.parent.name
            scraper_type = 'unknown'

            for key, scraper in SCRAPER_MAPPING.items():
                if key in parent_dir_name.lower():
                    scraper_type = scraper
                    break

            cities = load_city_list(csv_file)
            expected[state][scraper_type].extend(cities)

    return expected


def print_coverage_report(state_filter: str = None):
    """Print comprehensive coverage report comparing expected vs scraped jurisdictions."""
    scraped = get_scraped_jurisdictions()
    expected = load_all_expected_jurisdictions(state_filter)

    if not expected:
        print(f"\nNo city lists found in {CITY_LISTS_DIR}")
        return

    print(f"\n{'='*80}")
    print(f"COVERAGE REPORT{f' FOR {state_filter.upper()}' if state_filter else ' (ALL STATES)'}")
    print(f"{'='*80}\n")

    states_to_process = [state_filter] if state_filter else sorted(expected.keys())

    for state in states_to_process:
        if state not in expected:
            continue

        scrapers_expected = expected[state]
        scraped_in_state = scraped.get(state, set())

        # Calculate totals
        total_expected_raw = sum(len(cities) for cities in scrapers_expected.values())

        # Get unique expected (by slug)
        unique_expected_slugs = set()
        slug_to_scraper = {}  # Track which scraper each slug belongs to
        for scraper_type, cities in scrapers_expected.items():
            for city in cities:
                slug = city.get('slug', '')
                if slug:
                    unique_expected_slugs.add(slug)
                    if slug not in slug_to_scraper:
                        slug_to_scraper[slug] = scraper_type

        total_expected = len(unique_expected_slugs)
        total_scraped = len(scraped_in_state)
        coverage_pct = (total_scraped / total_expected * 100) if total_expected > 0 else 0

        print(f"{'─'*80}")
        print(f"STATE: {state.upper()}")
        print(f"{'─'*80}")
        print(f"Expected:  {total_expected:3d} unique jurisdictions")
        print(f"Scraped:   {total_scraped:3d} jurisdictions")
        print(f"Coverage:  {coverage_pct:5.1f}%")
        print(f"Missing:   {total_expected - total_scraped:3d} jurisdictions\n")

        # By scraper breakdown
        print("By Scraper:")
        for scraper_type in sorted(scrapers_expected.keys()):
            cities = scrapers_expected[scraper_type]
            expected_slugs = {c.get('slug', '') for c in cities if c.get('slug')}
            scraped_for_scraper = len(expected_slugs & scraped_in_state)
            expected_count = len(expected_slugs)
            scraper_cov_pct = (scraped_for_scraper / expected_count * 100) if expected_count > 0 else 0

            status = '✓' if scraper_cov_pct >= 95 else '⚠' if scraper_cov_pct >= 80 else '✗'
            print(f"  {status} {scraper_type:30s}: {scraped_for_scraper:3d}/{expected_count:3d} "
                  f"({scraper_cov_pct:5.1f}%)")

        # List missing jurisdictions
        missing_slugs = unique_expected_slugs - scraped_in_state
        if missing_slugs:
            print(f"\nMissing Jurisdictions ({len(missing_slugs)}):")
            # Organize by scraper
            missing_by_scraper = defaultdict(list)
            for slug in sorted(missing_slugs):
                scraper = slug_to_scraper.get(slug, 'unknown')
                # Find the city details
                city_name = slug
                for scraper_type, cities in scrapers_expected.items():
                    for city in cities:
                        if city.get('slug') == slug:
                            city_name = city.get('name', slug)
                            break
                missing_by_scraper[scraper].append((slug, city_name))

            for scraper in sorted(missing_by_scraper.keys()):
                cities = missing_by_scraper[scraper]
                print(f"\n  {scraper} ({len(cities)} missing):")
                for slug, name in sorted(cities)[:10]:  # Show first 10
                    print(f"    - {name} ({slug})")
                if len(cities) > 10:
                    print(f"    ... and {len(cities) - 10} more")

        print()

    print(f"{'='*80}\n")


def print_poor_quality_files(results: List[dict], state_filter: str = None):
    """Print files with PARTIAL or BAD quality status."""
    poor_files = [
        r for r in results
        if r['status'] in ['PARTIAL', 'BAD'] and (state_filter is None or r['state'] == state_filter)
    ]

    if not poor_files:
        msg = f"No poor quality files found"
        if state_filter:
            msg += f" for state {state_filter.upper()}"
        print(f"\n{msg}\n")
        return

    # Calculate HTML percentage for each file and sort (worst first)
    for f in poor_files:
        if f['section_count'] > 0:
            f['html_pct'] = (f['sections_with_html'] / f['section_count']) * 100
        else:
            f['html_pct'] = 0.0

    poor_files.sort(key=lambda x: x['html_pct'])

    print(f"\n{'='*80}")
    print(f"POOR QUALITY FILES{f' FOR {state_filter.upper()}' if state_filter else ''}")
    print(f"{'='*80}")
    print(f"Total: {len(poor_files)} files (PARTIAL or BAD status)\n")

    print(f"{'File':<50} | {'Scraper':<20} | {'Status':<8} | {'HTML %':>8} | {'Sections':>12}")
    print(f"{'-'*50}-+-{'-'*20}-+-{'-'*8}-+-{'-'*8}-+-{'-'*12}")

    for f in poor_files:
        filename = f"{f['state']}/{f['file']}"
        sections_str = f"{f['sections_with_html']}/{f['section_count']}"
        status_icon = '⚠' if f['status'] == 'PARTIAL' else '✗'
        print(f"{filename:<50} | {f['scraper']:<20} | {status_icon} {f['status']:<6} | {f['html_pct']:>7.1f}% | {sections_str:>12}")

    print(f"\n{'='*80}\n")


def find_missing_jurisdictions() -> Dict[str, Dict[str, List[Dict]]]:
    """Find all jurisdictions in city_lists/ that don't exist in codes/."""
    scraped = get_scraped_jurisdictions()
    missing = defaultdict(lambda: defaultdict(list))

    if not CITY_LISTS_DIR.exists():
        print(f"Warning: {CITY_LISTS_DIR} does not exist")
        return missing

    print(f"\n{'='*80}")
    print("FINDING MISSING JURISDICTIONS")
    print(f"{'='*80}\n")

    for state_dir in CITY_LISTS_DIR.iterdir():
        if not state_dir.is_dir():
            continue

        state = state_dir.name
        scraped_in_state = scraped.get(state, set())

        print(f"  {state.upper()}: {len(scraped_in_state)} jurisdictions currently scraped")

        # Use rglob to recursively search for CSV files in subdirectories
        for csv_file in state_dir.rglob("*.csv"):
            # Infer scraper from directory name
            parent_dir_name = csv_file.parent.name
            scraper_type = 'unknown'

            for key, scraper in SCRAPER_MAPPING.items():
                if key in parent_dir_name.lower():
                    scraper_type = scraper
                    break

            cities = load_city_list(csv_file)

            for city in cities:
                slug = city.get('slug', '')
                if slug and slug not in scraped_in_state:
                    city['scraper'] = scraper_type  # Add scraper info
                    missing[state][scraper_type].append(city)

        total_missing = sum(len(cities) for cities in missing[state].values())
        if total_missing > 0:
            print(f"    Found {total_missing} missing jurisdictions")
            for scraper, cities in missing[state].items():
                if cities:
                    print(f"      - {scraper}: {len(cities)} missing")

    return missing


def write_missing_city_lists(missing: Dict[str, Dict[str, List[Dict]]]) -> int:
    """Write CSV files for missing jurisdictions."""
    MISSING_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"WRITING MISSING JURISDICTION LISTS")
    print(f"{'='*80}\n")

    total_written = 0

    for state, scrapers in missing.items():
        state_dir = MISSING_DIR / state
        state_dir.mkdir(exist_ok=True)

        for scraper_type, cities in scrapers.items():
            if not cities:
                continue

            scraper_slug = scraper_type.replace('.py', '').replace('_', '-')
            filename = f"{state}_missing_{scraper_slug}.csv"
            output_path = state_dir / filename

            # Collect all unique fieldnames
            fieldnames = set()
            for city in cities:
                fieldnames.update(city.keys())
            fieldnames = sorted(list(fieldnames))

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(cities)

            print(f"  Wrote {len(cities)} jurisdictions to {state}/{filename}")
            total_written += len(cities)

    print(f"\nTotal missing jurisdictions: {total_written}")
    print(f"Output location: {MISSING_DIR}/\n")

    return total_written


def delete_bad_files(results: List[dict], dry_run: bool = True) -> Tuple[int, int]:
    """Delete all BAD quality files from the codes directory."""
    bad_files = [r for r in results if r['status'] == 'BAD']

    deleted = 0
    failed = 0

    print(f"\n{'='*80}")
    print(f"{'[DRY RUN] ' if dry_run else ''}DELETING BAD QUALITY FILES")
    print(f"{'='*80}\n")
    print(f"Total files to delete: {len(bad_files)}\n")

    for file_info in bad_files:
        state = file_info['state']
        filename = file_info['file']
        file_path = CODES_DIR / state / filename

        if file_path.exists():
            if dry_run:
                size_mb = file_info.get('file_size_mb', 0)
                html_pct = (file_info['sections_with_html'] / file_info['section_count'] * 100
                           if file_info['section_count'] > 0 else 0)
                print(f"  Would delete: {state}/{filename} "
                      f"({size_mb:.2f}MB, {html_pct:.1f}% HTML content, "
                      f"scraper: {file_info['scraper']})")
            else:
                os.remove(file_path)
                print(f"  Deleted: {state}/{filename}")
            deleted += 1
        else:
            print(f"  Warning: File not found: {state}/{filename}")
            failed += 1

    if dry_run:
        print(f"\n⚠️  This was a DRY RUN. No files were actually deleted.")
        print("   Run with --delete-bad flag to actually delete files.")

    return deleted, failed


def create_snapshot(states: List[str] = None) -> Path:
    """Create a timestamped snapshot of current data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    state_suffix = f"_{'_'.join(states)}" if states else "_all"
    snapshot_dir = SNAPSHOTS_DIR / f"snapshot_{timestamp}{state_suffix}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print("CREATING SNAPSHOT")
    print(f"{'='*80}\n")

    # Copy codes
    codes_snapshot = snapshot_dir / "codes"
    codes_snapshot.mkdir(exist_ok=True)

    file_count = 0
    total_size = 0

    for state_dir in CODES_DIR.iterdir():
        if not state_dir.is_dir():
            continue

        state = state_dir.name
        if states and state not in states:
            continue

        state_snapshot = codes_snapshot / state
        state_snapshot.mkdir(exist_ok=True)

        for json_file in state_dir.glob("*.json"):
            shutil.copy2(json_file, state_snapshot / json_file.name)
            file_count += 1
            total_size += json_file.stat().st_size

    print(f"✓ Copied {file_count} code files")
    print(f"  Total size: {total_size / 1024 / 1024:.2f} MB")

    # Copy quality report if it exists
    if QUALITY_REPORT.exists():
        shutil.copy2(QUALITY_REPORT, snapshot_dir / "quality_report.json")
        print(f"✓ Copied quality report")

    # Save snapshot metadata
    metadata = {
        'timestamp': timestamp,
        'date': datetime.now().isoformat(),
        'states': states or 'all',
        'file_count': file_count,
        'total_size_mb': total_size / 1024 / 1024,
    }

    metadata_file = snapshot_dir / "snapshot_metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n✅ Snapshot saved to: {snapshot_dir}\n")

    return snapshot_dir


def compare_snapshots(baseline_dir: Path, current_dir: Path = None):
    """Compare two snapshots and print detailed comparison."""
    print(f"\n{'='*80}")
    print("SNAPSHOT COMPARISON")
    print(f"{'='*80}\n")

    # Load baseline
    baseline_report = baseline_dir / "quality_report.json"
    if not baseline_report.exists():
        print(f"Error: Baseline quality report not found: {baseline_report}")
        return

    with open(baseline_report) as f:
        baseline_data = json.load(f)

    # Load current (either from snapshot or current state)
    if current_dir:
        current_report = current_dir / "quality_report.json"
        if not current_report.exists():
            print(f"Error: Current quality report not found: {current_report}")
            return
        with open(current_report) as f:
            current_data = json.load(f)
    else:
        # Use current quality report
        if not QUALITY_REPORT.exists():
            print("Error: No current quality report. Run analysis first.")
            return
        with open(QUALITY_REPORT) as f:
            current_data = json.load(f)

    b_sum = baseline_data['summary']
    c_sum = current_data['summary']

    print(f"Baseline: {baseline_data.get('generated_at', 'unknown')}")
    print(f"Current:  {current_data.get('generated_at', 'unknown')}")

    print(f"\n{'='*80}")
    print("OVERALL METRICS")
    print(f"{'='*80}")

    # Files
    files_diff = c_sum['total_files'] - b_sum['total_files']
    files_symbol = "📈" if files_diff > 0 else "📉" if files_diff < 0 else "➡️"
    print(f"\n  Total Files:")
    print(f"    Baseline: {b_sum['total_files']}")
    print(f"    Current:  {c_sum['total_files']}")
    print(f"    Change:   {files_diff:+d} {files_symbol}")

    # Sections
    sections_diff = c_sum['total_sections'] - b_sum['total_sections']
    sections_symbol = "📈" if sections_diff > 0 else "📉" if sections_diff < 0 else "➡️"
    print(f"\n  Total Sections:")
    print(f"    Baseline: {b_sum['total_sections']:,}")
    print(f"    Current:  {c_sum['total_sections']:,}")
    print(f"    Change:   {sections_diff:+,} {sections_symbol}")

    # HTML content
    html_diff = c_sum['total_with_html'] - b_sum['total_with_html']
    html_pct_diff = c_sum['html_percentage'] - b_sum['html_percentage']
    html_symbol = "✅" if html_diff > 0 else "❌" if html_diff < 0 else "➡️"
    print(f"\n  Sections with HTML Content:")
    print(f"    Baseline: {b_sum['total_with_html']:,} ({b_sum['html_percentage']:.1f}%)")
    print(f"    Current:  {c_sum['total_with_html']:,} ({c_sum['html_percentage']:.1f}%)")
    print(f"    Change:   {html_diff:+,} ({html_pct_diff:+.1f}%) {html_symbol}")

    # Errors
    errors_diff = c_sum['total_with_errors'] - b_sum['total_with_errors']
    errors_symbol = "✅" if errors_diff < 0 else "⚠️" if errors_diff > 0 else "➡️"
    print(f"\n  Sections with Errors:")
    print(f"    Baseline: {b_sum['total_with_errors']:,}")
    print(f"    Current:  {c_sum['total_with_errors']:,}")
    print(f"    Change:   {errors_diff:+,} {errors_symbol}")

    # Verdict
    print(f"\n{'='*80}")
    print("VERDICT")
    print(f"{'='*80}\n")

    score = 0
    if html_diff > 0:
        score += 2
    if html_pct_diff > 0:
        score += 2
    if files_diff > 0:
        score += 1
    if errors_diff < 0:
        score += 1

    if score >= 5:
        verdict = "🎉 SIGNIFICANT IMPROVEMENT!"
    elif score >= 3:
        verdict = "✅ IMPROVEMENT"
    elif score >= 0:
        verdict = "➡️  MINOR CHANGE"
    else:
        verdict = "⚠️  REGRESSION"

    print(f"  {verdict}")
    print(f"  Score: {score}/6\n")


def main():
    parser = argparse.ArgumentParser(
        description='Comprehensive quality check tool for scraped municipal code database'
    )
    parser.add_argument(
        '--find-missing',
        action='store_true',
        help='Find missing jurisdictions from city_lists/'
    )
    parser.add_argument(
        '--delete-bad',
        action='store_true',
        help='Actually delete BAD quality files (default is dry-run)'
    )
    parser.add_argument(
        '--create-snapshot',
        action='store_true',
        help='Create a snapshot of current data'
    )
    parser.add_argument(
        '--compare-snapshot',
        type=str,
        metavar='PATH',
        help='Compare with a previous snapshot directory'
    )
    parser.add_argument(
        '--states',
        type=str,
        nargs='+',
        help='Limit to specific states (for snapshots)'
    )
    parser.add_argument(
        '--state',
        type=str,
        metavar='STATE',
        help='Filter reports to a specific state (e.g., ut, mo)'
    )
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Show coverage report comparing expected vs scraped jurisdictions from city_lists/'
    )
    parser.add_argument(
        '--show-poor-quality',
        action='store_true',
        help='Show files with PARTIAL or BAD quality status (use with --state to filter)'
    )

    args = parser.parse_args()

    print("="*80)
    print("MUNICIPAL CODE DATABASE QUALITY CHECK")
    print("="*80)

    # Analyze codes directory
    results, organized = analyze_codes_directory()

    if not results:
        print("No files found to analyze.")
        return

    # Print quality report
    print_quality_report(results, organized)

    # Save quality report
    save_quality_report(results, organized)

    # Find missing jurisdictions
    if args.find_missing:
        missing = find_missing_jurisdictions()
        write_missing_city_lists(missing)

    # Delete bad files
    if args.delete_bad:
        delete_bad_files(results, dry_run=False)

    # Create snapshot
    if args.create_snapshot:
        create_snapshot(states=args.states)

    # Compare with snapshot
    if args.compare_snapshot:
        baseline_path = Path(args.compare_snapshot)
        if baseline_path.exists():
            compare_snapshots(baseline_path)
        else:
            print(f"Error: Snapshot not found: {baseline_path}")

    # Show coverage report
    if args.coverage:
        print_coverage_report(state_filter=args.state)

    # Show poor quality files
    if args.show_poor_quality:
        print_poor_quality_files(results, state_filter=args.state)

    print("\n✅ Done!\n")


if __name__ == '__main__':
    main()
