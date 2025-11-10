# Discrepancy Detection Evaluation Guide

This guide documents the evaluation workflow for the discrepancy detection system.

## Overview

The evaluation system uses:
- **Braintrust** for experiment tracking and tracing
- **Pydantic models** for type-safe data structures
- **Ground truth labels** stored in `dataset.json`
- **Automated scorers** for classification metrics

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

## Label Schema

Labels use the same Pydantic models as workflow output for consistency:

```json
{
  "uuid": "f3a7203d-29b6-441e-9e89-1198378410bb",
  "labels": {
    "deviations": [
      {
        "deviation_class": "product_or_component_undocumented",
        "explanation": "Ridge vents discussed but not in estimate",
        "occurrences": [
          {
            "rilla_conversation_index": 0,
            "timestamp": "00:15:30"
          }
        ],
        "predicted_line_item": {
          "description": "Ridge Vents",
          "quantity": 50.0,
          "unit": "LF",
          "notes": "Customer requested ridge vents for ventilation"
        }
      }
    ],
    "notes": "Verified against Rilla recording",
    "verified_by": "will",
    "verified_at": "2025-01-09T12:00:00Z"
  }
}
```

## Workflow

### 1. Run Workflow with Tracing (Pre-labeling)

```bash
# Run workflow with Braintrust tracing enabled
uv run python -m src.workflows.discrepancy_detection_v2 \
  --dataset-path evals/estimate_deviation/dataset.json \
  --uuid f3a7203d-29b6-441e-9e89-1198378410bb \
  --trace \
  --experiment-name "prelabel-2025-01-09"
```

This will:
- Execute the discrepancy detection workflow
- Log inputs/outputs to Braintrust
- Auto-trace all OpenAI API calls (GPT-5, embeddings)
- Generate initial deviation predictions

View results at https://braintrust.dev

### 2. Review and Label

#### Manual Labeling Process

1. **Review workflow output** - Check console logs and Braintrust UI
2. **Listen to Rilla recording** - Verify occurrences and timestamps
3. **Check form data** - Look for items in form but not in estimate
4. **Add/correct deviations** - Edit `dataset.json` directly

#### Labeling Guidelines

- **Timestamps**: Use HH:MM:SS or MM:SS format (start of sentence where deviation mentioned)
- **Occurrences**: Include all mentions in the conversation
- **Predicted line items**: Estimate what should be added to fix the deviation
- **Notes**: Document edge cases or ambiguities

Example label in `dataset.json`:

```json
{
  "uuid": "aa8f65aa-fe79-4c12-825b-9862dbe7e08c",
  "labels": {
    "deviations": [
      {
        "deviation_class": "discount_applied_not_tracked",
        "explanation": "5% monthly promotion + 5% same-day savings not documented",
        "occurrences": [
          {"rilla_conversation_index": 0, "timestamp": "01:49:03"},
          {"rilla_conversation_index": 0, "timestamp": "01:49:13"}
        ],
        "predicted_line_item": null
      }
    ],
    "verified_by": "will",
    "verified_at": "2025-01-09T15:30:00Z"
  }
}
```

### 3. Migrate Existing Labels (One-time)

If you have labels in `labels.md`, migrate them:

```bash
# Dry run to preview migration
uv run python -m evals.estimate_deviation.migrate_labels \
  --dry-run

# Actually migrate
uv run python -m evals.estimate_deviation.migrate_labels
```

### 4. Run Evaluation

```bash
# Evaluate all labeled entries
uv run python -m evals.estimate_deviation.run_eval

# Evaluate specific subset
uv run python -m evals.estimate_deviation.run_eval \
  --subset f3a7203d-29b6-441e-9e89-1198378410bb aa8f65aa-fe79-4c12-825b-9862dbe7e08c

# Log results to Braintrust
uv run python -m evals.estimate_deviation.run_eval \
  --experiment-name "eval-2025-01-09"
```

The evaluation will output:
- **Per-class F1 scores** - Classification accuracy for each deviation class
- **Confusion matrix** - Which classes are confused with each other
- **False positive/negative counts** - Hallucinations and missed detections
- **Occurrence accuracy** - Timestamp matching within 30s tolerance

### 5. Analyze Results

Review metrics in console output or Braintrust UI:

```
EVALUATION SUMMARY
============================================================
Total Entries Evaluated: 3
Errors: 0

Classification Metrics:
  Average F1 Score:   0.875
  Average Precision:  0.920
  Average Recall:     0.835

Error Analysis:
  Total False Positives:  2
  Total False Negatives:  3

Occurrence Accuracy:
  Average Timestamp Accuracy: 0.780
============================================================
```

### 6. Iterate

1. **Identify weak classes** - Low F1 scores indicate classification issues
2. **Review false positives** - Check if model is hallucinating specific classes
3. **Review false negatives** - Check if model is missing specific patterns
4. **Refine prompts** - Update `discrepancy_detection_prompt.md` for problem areas
5. **Re-run evaluation** - Measure improvement

## Evaluation Metrics

### Classification Scores
- **Overall F1**: Macro-averaged F1 across all classes
- **Per-class F1**: F1 for each deviation class individually
- **Precision/Recall**: Trade-off between false positives and false negatives

### Confusion Matrix
Shows which ground truth classes are predicted as which classes (or missed)

### False Positive Analysis
- **Count**: Number of predicted deviations not in ground truth
- **Rate**: FP count / total predictions
- **Classes**: Which classes are being hallucinated

### False Negative Analysis
- **Count**: Number of ground truth deviations missed
- **Rate**: FN count / total ground truth
- **Classes**: Which classes are being missed

### Occurrence Accuracy
- **Accuracy**: % of timestamps within 30s tolerance
- **Errors**: Specific timestamp mismatches with error details

## Files Reference

- `dataset.json` - Dataset with ground truth labels
- `classes.json` - Deviation class taxonomy
- `label_schema.py` - Pydantic models for labels
- `schemas.py` - Pydantic models for evaluation results
- `scorers.py` - Evaluation metric functions
- `run_eval.py` - Main evaluation script
- `migrate_labels.py` - Migration tool for old labels
- `discrepancy_detection_v2.py` - Workflow implementation

## Tips

- **Start small**: Label 3-5 entries first, run eval, iterate
- **Use tracing**: Always trace runs during development for debugging
- **Version experiments**: Use descriptive experiment names in Braintrust
- **Document edge cases**: Use the `notes` field in labels
- **Validate regularly**: Run `uv run python -m evals.estimate_deviation.label_schema` to validate label schema