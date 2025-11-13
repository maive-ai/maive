"""View and filter error summary from eval runs.

Usage:
    # View all false positives
    uv run python -m evals.estimate_deviation.view_errors --type fp

    # View all false negatives
    uv run python -m evals.estimate_deviation.view_errors --type fn

    # View errors for a specific dataset entry
    uv run python -m evals.estimate_deviation.view_errors --dataset-id abc123

    # View latest N errors
    uv run python -m evals.estimate_deviation.view_errors --latest 10

    # Export to readable markdown
    uv run python -m evals.estimate_deviation.view_errors --format markdown > errors.md
"""

import argparse
import json
from pathlib import Path

ERROR_LOG_FILE = Path(__file__).parent / "error_summary.jsonl"


def format_entry_text(entry: dict) -> str:
    """Format error entry as readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"ERROR TYPE: {entry['error_type']} (Severity: {entry['severity']})")
    lines.append(f"Dataset ID: {entry['dataset_id']}")
    lines.append(f"Timestamp: {entry['timestamp']}")
    lines.append("")

    if entry["error_type"] == "FALSE_POSITIVE":
        pred = entry["predicted_deviation"]
        lines.append("PREDICTED (WRONG):")
        lines.append(f"  Class: {pred['class']}")
        lines.append(f"  Explanation: {pred['explanation']}")
        if pred.get("occurrences"):
            lines.append("  Occurrences:")
            for occ in pred["occurrences"]:
                lines.append(
                    f"    - Conversation {occ['conversation_idx']}: {occ['timestamp']}"
                )
        if pred.get("line_item"):
            item = pred["line_item"]
            lines.append(
                f"  Line Item: {item['display_name']} (Qty: {item['quantity']}, Cost: ${item['unit_cost']})"
            )
        lines.append("")
        lines.append("EXPECTED DEVIATIONS:")
        for exp in entry["expected_deviations"]:
            lines.append(f"  - [{exp['class']}] {exp['explanation']}")

    elif entry["error_type"] == "FALSE_NEGATIVE":
        exp = entry["expected_deviation"]
        lines.append("EXPECTED (MISSED):")
        lines.append(f"  Class: {exp['class']}")
        lines.append(f"  Explanation: {exp['explanation']}")
        if exp.get("occurrences"):
            lines.append("  Occurrences:")
            for occ in exp["occurrences"]:
                lines.append(
                    f"    - Conversation {occ['conversation_idx']}: {occ['timestamp']}"
                )
        lines.append("")
        lines.append("PREDICTED DEVIATIONS:")
        for pred in entry["predicted_deviations"]:
            lines.append(f"  - [{pred['class']}] {pred['explanation']}")

    lines.append("")
    metrics = entry["metrics"]
    lines.append(
        f"Metrics: Precision={metrics['precision']:.2f}, TP={metrics['tp']}, FP={metrics['fp']}, FN={metrics['fn']}"
    )
    lines.append("")

    return "\n".join(lines)


def format_entry_markdown(entry: dict) -> str:
    """Format error entry as markdown."""
    lines = []
    lines.append(f"## {entry['error_type']} - {entry['dataset_id']}")
    lines.append("")
    lines.append(f"**Severity:** {entry['severity']} | **Time:** {entry['timestamp']}")
    lines.append("")

    if entry["error_type"] == "FALSE_POSITIVE":
        pred = entry["predicted_deviation"]
        lines.append("### Predicted (WRONG)")
        lines.append(f"- **Class:** `{pred['class']}`")
        lines.append(f"- **Explanation:** {pred['explanation']}")
        if pred.get("occurrences"):
            lines.append("- **Occurrences:**")
            for occ in pred["occurrences"]:
                lines.append(
                    f"  - Conversation {occ['conversation_idx']}: `{occ['timestamp']}`"
                )
        if pred.get("line_item"):
            item = pred["line_item"]
            lines.append(
                f"- **Line Item:** {item['display_name']} (Qty: {item['quantity']}, Cost: ${item['unit_cost']})"
            )
        lines.append("")
        lines.append("### Expected Deviations")
        for exp in entry["expected_deviations"]:
            lines.append(f"- `[{exp['class']}]` {exp['explanation']}")

    elif entry["error_type"] == "FALSE_NEGATIVE":
        exp = entry["expected_deviation"]
        lines.append("### Expected (MISSED)")
        lines.append(f"- **Class:** `{exp['class']}`")
        lines.append(f"- **Explanation:** {exp['explanation']}")
        if exp.get("occurrences"):
            lines.append("- **Occurrences:**")
            for occ in exp["occurrences"]:
                lines.append(
                    f"  - Conversation {occ['conversation_idx']}: `{occ['timestamp']}`"
                )
        lines.append("")
        lines.append("### Predicted Deviations")
        for pred in entry["predicted_deviations"]:
            lines.append(f"- `[{pred['class']}]` {pred['explanation']}")

    lines.append("")
    metrics = entry["metrics"]
    lines.append(
        f"**Metrics:** Precision={metrics['precision']:.2f}, TP={metrics['tp']}, FP={metrics['fp']}, FN={metrics['fn']}"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="View error summary from eval runs")
    parser.add_argument(
        "--type",
        "-t",
        choices=["fp", "fn", "all"],
        default="all",
        help="Filter by error type: fp (false positives), fn (false negatives), or all",
    )
    parser.add_argument(
        "--dataset-id",
        "-d",
        type=str,
        help="Filter by specific dataset ID",
    )
    parser.add_argument(
        "--latest",
        "-n",
        type=int,
        help="Show only the latest N errors",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format",
    )

    args = parser.parse_args()

    if not ERROR_LOG_FILE.exists():
        print(f"No error log found at {ERROR_LOG_FILE}")
        print("Run an evaluation first to generate errors.")
        return

    # Load and filter entries
    entries = []
    with open(ERROR_LOG_FILE, "r") as f:
        for line in f:
            entry = json.loads(line)

            # Apply filters
            if args.type != "all":
                if args.type == "fp" and entry["error_type"] != "FALSE_POSITIVE":
                    continue
                if args.type == "fn" and entry["error_type"] != "FALSE_NEGATIVE":
                    continue

            if args.dataset_id and entry["dataset_id"] != args.dataset_id:
                continue

            entries.append(entry)

    # Limit to latest N
    if args.latest:
        entries = entries[-args.latest :]

    # Format output
    if args.format == "markdown":
        print("# Evaluation Error Summary")
        print("")
        print(f"Total Errors: {len(entries)}")
        print("")
        for entry in entries:
            print(format_entry_markdown(entry))
    elif args.format == "json":
        print(json.dumps(entries, indent=2))
    else:  # text
        print(f"Showing {len(entries)} errors from {ERROR_LOG_FILE}")
        print("")
        for entry in entries:
            print(format_entry_text(entry))

    # Summary
    if entries and args.format != "json":
        fp_count = sum(1 for e in entries if e["error_type"] == "FALSE_POSITIVE")
        fn_count = sum(1 for e in entries if e["error_type"] == "FALSE_NEGATIVE")
        print(f"\nSummary: {fp_count} false positives, {fn_count} false negatives")


if __name__ == "__main__":
    main()
