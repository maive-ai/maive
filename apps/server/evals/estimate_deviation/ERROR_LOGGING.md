# Error Logging System

The evaluation framework automatically logs all errors (especially **false positives**) to an easy-to-read file for analysis.

## Quick Start

```bash
# Run evaluation (clears previous errors)
uv run python -m evals.estimate_deviation.run_braintrust_eval --clear-error-log

# View all false positives
uv run python -m evals.estimate_deviation.view_errors --type fp

# Export to markdown for reporting
uv run python -m evals.estimate_deviation.view_errors --format markdown > errors.md
```

## How It Works

### Automatic Logging

The evaluation automatically logs errors as they're detected:

- **FALSE POSITIVES** (Severity: HIGH) - Predicted deviations that were wrong
- **FALSE NEGATIVES** (Severity: MEDIUM) - Expected deviations that were missed

Errors are written to: `apps/server/evals/estimate_deviation/error_summary.jsonl`

### What's Logged

For each false positive, the log includes:
- Full predicted deviation (class, explanation, occurrences, line items)
- All expected deviations for context
- Metrics (precision, TP/FP/FN counts)
- Dataset ID for tracing back to source data

For each false negative, the log includes:
- Full expected deviation (class, explanation, occurrences)
- All predicted deviations for context
- Same metrics as above

## Viewing Errors

### Command Line Tool

```bash
# View all errors (text format)
uv run python -m evals.estimate_deviation.view_errors

# Show only false positives
uv run python -m evals.estimate_deviation.view_errors --type fp

# Show only false negatives
uv run python -m evals.estimate_deviation.view_errors --type fn

# View specific dataset entry
uv run python -m evals.estimate_deviation.view_errors --dataset-id abc123

# Show latest 10 errors only
uv run python -m evals.estimate_deviation.view_errors --latest 10

# Export to markdown
uv run python -m evals.estimate_deviation.view_errors --format markdown > errors.md

# Export to JSON for processing
uv run python -m evals.estimate_deviation.view_errors --format json > errors.json
```

### Using jq (JSON query tool)

```bash
# View all false positives with jq
cat error_summary.jsonl | jq 'select(.error_type == "FALSE_POSITIVE")'

# Count errors by type
cat error_summary.jsonl | jq -s 'group_by(.error_type) | map({type: .[0].error_type, count: length})'

# View errors for specific dataset
cat error_summary.jsonl | jq 'select(.dataset_id == "abc123")'

# Get all predicted explanations that were false positives
cat error_summary.jsonl | jq -r 'select(.error_type == "FALSE_POSITIVE") | .predicted_deviation.explanation'
```

## Evaluation Flags

### Clear Error Log

```bash
# Clear previous errors before running
uv run python -m evals.estimate_deviation.run_braintrust_eval --clear-error-log
```

This is recommended when starting a new evaluation run to avoid mixing results from different experiments.

### Max Concurrency

```bash
# Run with higher parallelism (default: 10)
uv run python -m evals.estimate_deviation.run_braintrust_eval --max-concurrency 20
```

Errors are logged safely even with parallel execution.

## File Format

The log file (`error_summary.jsonl`) is in JSON Lines format - each line is a valid JSON object:

```json
{
  "timestamp": "2025-01-12T10:30:45.123456",
  "dataset_id": "abc123",
  "error_type": "FALSE_POSITIVE",
  "severity": "HIGH",
  "predicted_deviation": {
    "class": "missing_line_item",
    "explanation": "Customer mentioned needing skylights but they are not in the estimate",
    "occurrences": [
      {"conversation_idx": 0, "timestamp": "00:05:23"}
    ],
    "line_item": {
      "display_name": "Velux Skylight 2x4",
      "quantity": 2,
      "unit_cost": 450.0
    }
  },
  "expected_deviations": [
    {
      "class": "quantity_mismatch",
      "explanation": "Customer said 3 skylights but estimate has 2"
    }
  ],
  "metrics": {
    "precision": 0.67,
    "tp": 2,
    "fp": 1,
    "fn": 1
  }
}
```

## Best Practices

1. **Clear log between runs**: Use `--clear-error-log` to avoid confusion
2. **Focus on false positives first**: These are marked HIGH severity for a reason
3. **Use markdown export for reports**: Great for sharing with the team
4. **Filter by dataset ID**: When debugging specific examples
5. **Continuous monitoring**: Errors append in real-time during evaluation

## Integration with Braintrust

The error log complements Braintrust's web UI:
- Braintrust shows aggregate metrics and trends
- Error log shows **specific failure details** for debugging
- Use error log to identify patterns in failures
- Cross-reference dataset IDs between both systems

## Example Workflow

```bash
# 1. Start fresh evaluation
uv run python -m evals.estimate_deviation.run_braintrust_eval --clear-error-log -c 10

# 2. Review false positives
uv run python -m evals.estimate_deviation.view_errors --type fp

# 3. Export for team review
uv run python -m evals.estimate_deviation.view_errors --format markdown > weekly_errors.md

# 4. Analyze patterns
cat error_summary.jsonl | jq 'select(.error_type == "FALSE_POSITIVE") | .predicted_deviation.class' | sort | uniq -c
```
