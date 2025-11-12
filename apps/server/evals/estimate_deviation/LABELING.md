# Discrepancy Detection Evaluation Guide

This guide documents the Braintrust-powered evaluation workflow for the discrepancy detection system.

## Overview

The evaluation system uses:
- **Braintrust** for experiment tracking, dataset management, and eval orchestration
- **Pydantic models** for type-safe data structures
- **Ground truth labels** stored in Braintrust datasets (with local YAML backups)
- **Automated scorers** for classification metrics

## Workflow: Prelabel → Label → Eval

```
┌─────────────────────────────────────────┐
│ 1. PRELABEL: Run workflow with tracing │
│    Generates predictions logged to BT   │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 2. LABEL: Review and correct in BT UI  │
│    Add corrected labels to dataset      │
└─────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────┐
│ 3. EVAL: Run automated evaluation      │
│    Compare predictions vs ground truth  │
└─────────────────────────────────────────┘
```

## Deviation Classes

See `classes.json` for the complete taxonomy. Key classes:

### Level 1 (Always Evaluated)
- `product_or_component_undocumented` - Item discussed but not in estimate or form
- `product_or_component_not_in_estimate` - Item in form but missing from estimate

### Level 2
- `discount_applied_not_tracked` - Discount mentioned but not documented
- `untracked_or_incorrect_customer_preference` - Color, material, timing preferences
- `labor_line_item_missing` - Labor discussed but not in estimate

### Level 3
- `scope_discrepancy` - Physical scope mismatch (e.g., shed roof not included)
- `incorrect_quantity` - Quantity doesn't match conversation/form

## Step 1: Prelabel (Generate Predictions)

Run the workflow with tracing enabled to generate prelabels:

```bash
# Run workflow with Braintrust tracing (level 1 classes only)
uv run python -m src.workflows.discrepancy_detection_v2 \\
  --dataset-path evals/estimate_deviation/dataset.json \\
  --uuid f3a7203d-29b6-441e-9e89-1198378410bb \\
  --level 1 \\
  --trace \\
  --prelabel \\
  --experiment-name "prelabel-2025-01-10"

# For level 2 evaluation (includes level 1 and 2 classes)
uv run python -m src.workflows.discrepancy_detection_v2 \\
  --dataset-path evals/estimate_deviation/dataset.json \\
  --uuid f3a7203d-29b6-441e-9e89-1198378410bb \\
  --level 2 \\
  --trace \\
  --prelabel \\
  --experiment-name "prelabel-level2-2025-01-10"

# For level 3 evaluation (all classes)
uv run python -m src.workflows.discrepancy_detection_v2 \\
  --dataset-path evals/estimate_deviation/dataset.json \\
  --uuid f3a7203d-29b6-441e-9e89-1198378410bb \\
  --level 3 \\
  --trace \\
  --prelabel \\
  --experiment-name "prelabel-level3-2025-01-10"
```

**Flag explanations:**
- `--level`: Controls which deviation class levels to include (default: 1)
  - Level 1: Only level 1 classes (most critical deviations)
  - Level 2: Level 1 and 2 classes
  - Level 3: All classes (comprehensive evaluation)
- `--prelabel`: Marks this run as prelabel data in Braintrust metadata (doesn't affect class filtering)
- `--trace`: Enables Braintrust tracing and logging
- `--experiment-name`: Name for the Braintrust experiment

This will:
- Execute the discrepancy detection workflow
- Log inputs/outputs to Braintrust as an experiment
- Auto-trace all OpenAI API calls (GPT-4o, embeddings)
- Calculate cost savings from pricebook matches
- Output format ready for dataset conversion

View results at https://braintrust.dev in the "discrepancy-detection" project.

## Step 2: Label (Review and Correct)

### In Braintrust UI

1. Go to https://braintrust.dev
2. Navigate to "discrepancy-detection" project
3. Find your prelabel experiment (e.g., "prelabel-2025-01-10")
4. Review each logged prediction:
   - Check deviations for accuracy
   - Validate cost_savings calculations
   - Review pricebook matches
5. For each entry:
   - Correct any errors in the deviations list
   - Adjust cost_savings if needed
   - Click "Add to dataset" → Select "ground-truth-labels"

### Label Format

Each dataset entry contains:

**Input (Data Files):**
```json
{
  "estimate": {
    "data": { ... },  // Parsed estimate JSON content
    "filename": "estimate.json"
  },
  "form": {
    "data": { ... },  // Parsed form JSON content
    "filename": "form.json"
  },
  "rilla_transcripts": [
    {
      "data": { ... },  // Parsed transcript JSON content
      "filename": "transcript_0.json"
    }
  ]
}
```

Note: JSON files are uploaded to Braintrust as `JSONAttachment` objects during prelabeling. Braintrust hosts the JSON content, making it viewable and downloadable in the UI. Audio recordings are not uploaded (not actively used in evaluation).

**Metadata (Identifying Information):**
```json
{
  "uuid": "f3a7203d-29b6-441e-9e89-1198378410bb",
  "project_id": "320698515",
  "job_id": "292862484",
  "estimate_id": "320707924",
  "prelabel": true,
  "rilla_links": [
    "https://app.rillavoice.com/conversations/single?id=f3a7203d-29b6-441e-9e89-1198378410bb"
  ],
  "project_created_date": "2025-07-03T16:54:51.977992+00:00",
  "estimate_sold_date": "2025-07-03T16:54:49.650000+00:00"
}
```

**Expected (Ground Truth):**
```json
{
  "deviations": [
    {
      "deviation_class": "product_or_component_not_in_estimate",
      "explanation": "The production notes specify that 351 units of gutters are included, but no line item exists in the estimate.",
      "occurrences": [
        {
          "conversation_idx": 0,
          "timestamp": "00:15:30"
        }
      ],
      "predicted_line_item": {
        "description": "Install Gutters",
        "quantity": 351.0,
        "unit": "LF",
        "notes": "From production notes",
        "matched_pricebook_item_id": "...",
        "matched_pricebook_item_code": "...",
        "unit_cost": 12.50,
        "total_cost": 4387.50
      }
    }
  ]
}
```

### Labeling Guidelines

- **Timestamps**: Use HH:MM:SS or MM:SS format (start of sentence where deviation mentioned)
- **Occurrences**: Include all mentions in the conversation
- **Predicted line items**: Include pricebook matches when available
- **Notes**: Use metadata field for edge cases or ambiguities

## Step 3: Run Evaluation

Once you have labeled data in Braintrust:

```bash
# Run eval against labeled dataset
uv run python -m evals.estimate_deviation.run_braintrust_eval
```

Optional arguments:
```bash
# Specify dataset name
uv run python -m evals.estimate_deviation.run_braintrust_eval \\
  --dataset-name "ground-truth-labels"

# Specify experiment name
uv run python -m evals.estimate_deviation.run_braintrust_eval \\
  --experiment-name "eval-2025-01-10"
```

The evaluation will:
- Load dataset from Braintrust
- Run workflow on each input
- Apply all scorers automatically
- Log results to Braintrust
- Display summary metrics

## Step 4: Analyze Results

### In Braintrust UI

1. Navigate to your eval experiment
2. View aggregate metrics:
   - Classification F1 score
   - False positive/negative rates
   - Occurrence accuracy
   - Binary detection accuracy
3. Drill down into failures:
   - Which deviations were missed?
   - Which deviations were hallucinated?
   - Which timestamps were incorrect?
4. Compare across experiments:
   - Track improvements over time
   - A/B test prompt changes
   - Compare model versions

### Metrics Explained

**Classification F1** - Macro-averaged F1 across all deviation classes
- Measures overall classification accuracy
- Balances precision and recall
- Ranges from 0.0 (worst) to 1.0 (perfect)

**False Positive Rate** - Hallucinated deviations / total predictions
- Lower is better
- Score = 1.0 - FP rate

**False Negative Rate** - Missed deviations / total ground truth
- Lower is better
- Score = 1.0 - FN rate

**Occurrence Accuracy** - Timestamps within 30s tolerance / total occurrences
- Measures timestamp accuracy
- Helps validate model is finding correct conversation segments

**Binary Detection** - Did we detect ANY deviations when we should have?
- Simple yes/no accuracy
- Useful for catching total failures

## Dataset Management

### Upload Local YAML Labels

If you have YAML files with labels:

```bash
# Upload all YAML files in labels/ directory
uv run python -m evals.estimate_deviation.manage_dataset --upload
```

### Export Dataset for Backup

```bash
# Export Braintrust dataset to local YAML files
uv run python -m evals.estimate_deviation.manage_dataset --export
```

### Sync Both Ways

```bash
# Upload local changes and export current state
uv run python -m evals.estimate_deviation.manage_dataset --upload --export
```

## Tips & Best Practices

### Labeling

- **Start small**: Label 3-5 entries first, run eval, iterate
- **Use prelabel**: Let the model do initial detection, then correct
- **Be consistent**: Use same deviation classes for similar issues
- **Document ambiguity**: Use metadata notes for edge cases
- **Validate pricebook**: Check that matched items make sense

### Evaluation

- **Run frequently**: Eval after every prompt change
- **Track experiments**: Use descriptive experiment names
- **Focus on failures**: Drill into false positives/negatives
- **Compare versions**: Use Braintrust's experiment comparison
- **Monitor costs**: Track token usage in Braintrust traces

### Iteration

1. **Identify weak classes** - Low F1 scores indicate classification issues
2. **Review false positives** - Check if model is hallucinating specific classes
3. **Review false negatives** - Check if model is missing specific patterns
4. **Refine prompts** - Update system prompts for problem areas
5. **Re-evaluate** - Measure improvement with same dataset

## Files Reference

- `run_braintrust_eval.py` - Main eval runner using Braintrust Eval()
- `manage_dataset.py` - Dataset upload/export utilities
- `schemas.py` - Pydantic models for workflow output and ground truth
- `scorers.py` - Evaluation metric functions (with Braintrust wrappers)
- `classes.json` - Deviation class taxonomy
- `labels/` - Local YAML backups of Braintrust dataset
- `discrepancy_detection_v2.py` - Workflow implementation with tracing

## Troubleshooting

### "Dataset not found" Error

The dataset must exist in Braintrust first. Either:
1. Upload YAML labels: `manage_dataset.py --upload`
2. Manually create dataset in Braintrust UI
3. Run prelabel and add some entries manually

### Scorer Errors

If a scorer returns an error:
- Check that expected output has required fields
- Validate deviation format matches schema
- Review error details in scorer metadata

### Missing Pricebook Data

If `unit_cost` or `total_cost` are None:
- Pricebook matching didn't find a match
- Check pricebook configuration
- Manual labeling may need estimated costs

## Advanced Usage

### Custom Scorers

Add your own scorers in `scorers.py`:

```python
def custom_scorer_bt(input, output, expected=None, **kwargs):
    \"\"\"Custom scorer for specific metric.\"\"\"
    if not expected:
        return None

    # Your scoring logic here
    score = calculate_custom_score(output, expected)

    return {
        "name": "custom_metric",
        "score": score,
        "metadata": {
            "details": "..."
        }
    }
```

Then add to `run_braintrust_eval.py` scorer list.

### Dataset Versions

Braintrust supports dataset versioning:
- Label quality improvements over time
- A/B test different label sets
- Roll back to previous versions

Access versions in Braintrust UI or via SDK:
```python
dataset = braintrust.init_dataset(
    project="discrepancy-detection",
    name="ground-truth-labels",
    version="v2"  # Specify version
)
```

### Parallel Evaluation

For large datasets, run eval on multiple entries in parallel:
- Braintrust Eval() handles concurrency automatically
- Adjust `max_concurrency` parameter if needed
- Monitor rate limits and costs

## Resources

- Braintrust Docs: https://braintrust.dev/docs
- Braintrust Dashboard: https://braintrust.dev
- Internal Docs: See CLAUDE.md for project architecture
