"""LLM-based scorers for discrepancy detection using autoevals.

Comprehensive scorer that:
- Matches predicted deviations to expected using LLM semantic similarity
- Computes deterministic precision, recall, F1
- Evaluates explanation quality on matched pairs

Usage:
    from evals.estimate_deviation.scorers import comprehensive_deviation_scorer

    Eval(..., scores=[comprehensive_deviation_scorer])
"""

from autoevals import LLMClassifier
from braintrust import Score
from braintrust.framework import EvalScorer

from evals.estimate_deviation.schemas import Deviation, DeviationOccurrence


def parse_timestamp_to_seconds(timestamp: str) -> int:
    """Convert HH:MM:SS or MM:SS timestamp to total seconds.

    Args:
        timestamp: Timestamp string in format "HH:MM:SS" or "MM:SS"

    Returns:
        Total seconds as integer
    """
    parts = timestamp.split(":")
    if len(parts) == 3:  # HH:MM:SS
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
    elif len(parts) == 2:  # MM:SS
        minutes, seconds = parts
        return int(minutes) * 60 + int(seconds)
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def match_occurrences(
    predicted_occs: list[DeviationOccurrence] | None,
    expected_occs: list[DeviationOccurrence] | None,
    tolerance_seconds: int = 10,
) -> tuple[
    list[tuple[DeviationOccurrence, DeviationOccurrence]],
    list[DeviationOccurrence],
    list[DeviationOccurrence],
]:
    """Match predicted occurrences to expected occurrences optimally.

    Matching criteria:
    1. Same conversation_idx (exact match required)
    2. Timestamp within tolerance (±10 seconds)
    3. Optimal assignment: match to closest timestamp

    Args:
        predicted_occs: List of predicted occurrences (or None)
        expected_occs: List of expected occurrences (or None)
        tolerance_seconds: Maximum allowed time difference in seconds

    Returns:
        tuple: (
            matched_pairs: list[(predicted_occ, expected_occ)],
            unmatched_predicted: list[predicted_occ],
            unmatched_expected: list[expected_occ]
        )
    """
    if not predicted_occs and not expected_occs:
        # Both None or empty - perfect match
        return ([], [], [])

    if not predicted_occs:
        # No predictions but has expected - all unmatched
        return ([], [], expected_occs or [])

    if not expected_occs:
        # Has predictions but no expected - all unmatched
        return ([], predicted_occs or [], [])

    matched_pairs = []
    unmatched_predicted = list(predicted_occs)
    unmatched_expected = list(expected_occs)

    # For each expected occurrence, find best match
    for exp_occ in expected_occs:
        # Find candidates with same conversation_idx
        candidates = [
            (i, pred)
            for i, pred in enumerate(unmatched_predicted)
            if pred.conversation_idx == exp_occ.conversation_idx
        ]

        if not candidates:
            # No candidates for this conversation - stays unmatched
            continue

        # Find closest timestamp among candidates
        exp_seconds = parse_timestamp_to_seconds(exp_occ.timestamp)
        best_match = None
        best_distance = float("inf")

        for idx, pred in candidates:
            pred_seconds = parse_timestamp_to_seconds(pred.timestamp)
            distance = abs(exp_seconds - pred_seconds)

            if distance < best_distance:
                best_distance = distance
                best_match = (idx, pred)

        # Accept if within tolerance
        if best_match and best_distance <= tolerance_seconds:
            matched_pairs.append((best_match[1], exp_occ))
            unmatched_predicted.remove(best_match[1])
            unmatched_expected.remove(exp_occ)

    return (matched_pairs, unmatched_predicted, unmatched_expected)


# Semantic matching scorer: Are output and expected describing the same deviation?
deviation_semantic_match = LLMClassifier(
    name="DeviationSemanticMatch",
    prompt_template="""You are evaluating if two deviation descriptions refer to the same underlying issue.

Expected deviation:
Class: {{{expected.deviation_class}}}
Explanation: {{{expected.explanation}}}

Predicted deviation:
Class: {{{output.deviation_class}}}
Explanation: {{{output.explanation}}}

Question: Do these two deviations describe the SAME specific issue/discrepancy?

Consider:
- Same component/item (e.g., both about skylights, not one skylight one chimney)
- Same type of problem (e.g., both about missing from estimate)
- Same root cause

Return:
(A) Yes, same deviation
(B) No, different deviations""",
    choice_scores={"A": 1.0, "B": 0.0},
    model="gpt-4o",
)


# Explanation quality scorer: How well does the predicted explanation match expected?
explanation_quality = LLMClassifier(
    name="ExplanationQuality",
    prompt_template="""You are evaluating the quality of a predicted deviation explanation against ground truth.

Expected (ground truth):
{{{expected.explanation}}}

Predicted:
{{{output.explanation}}}

Evaluate the predicted explanation quality:
- Does it correctly identify the same issue as expected?
- Does it include key details?
- Is it clear and specific?

Return:
(A) Excellent - matches expected quality and accuracy
(B) Good - mostly accurate, minor details missing
(C) Fair - correct issue but explanation lacks detail
(D) Poor - misses key details or unclear
(F) Fail - wrong issue or seriously inaccurate""",
    choice_scores={"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "F": 0.0},
    model="gpt-4o",
)


# Line item semantic matcher: Are the pricebook items the same product type?
line_item_semantic_match = LLMClassifier(
    name="LineItemSemanticMatch",
    prompt_template="""You are evaluating if two pricebook line items refer to the same type of product/service.

Expected line item:
{{{expected.display_name}}}

Predicted line item:
{{{output.display_name}}}

Question: Do these refer to the SAME TYPE of product/service?

Consider:
- Focus on the CATEGORY (e.g., skylight, shingle, vent) not exact specifications
- Different brands/sizes of the same item type should MATCH
- "KQ Skylight Velux Fixed S/M-BOH" matches "Velux Skylight 2x4" (both skylights)
- Minor variations in naming are acceptable

Return:
(A) Yes, same product type
(B) No, different product types""",
    choice_scores={"A": 1.0, "B": 0.0},
    model="gpt-4o",
)


def _extract_score(result) -> float:
    """Helper to extract score from LLM classifier result."""
    if isinstance(result, dict):
        return result.get("score", 0.0)
    elif hasattr(result, "score"):
        return result.score
    else:
        return float(result) if result is not None else 0.0


def comprehensive_deviation_scorer(
    input, output, expected=None, **kwargs
) -> EvalScorer:
    """Comprehensive scorer with LLM-based semantic matching + occurrence validation + line item scoring.

    Workflow:
    1. Match predicted deviations to expected using LLM semantic similarity
    2. Validate occurrences: must match timestamps within ±10 seconds
    3. Compute deviation-level TP/FP/FN counts from matches
    4. Calculate deviation-level precision and recall
    5. Calculate occurrence-level precision and recall
    6. Score explanation quality on matched pairs
    7. Score line item predictions using semantic matching
    8. Calculate quantity and unit_cost accuracy for matched line items
    9. Calculate value (quantity * unit_cost) for TP line items
    10. Calculate value_created (sum of values, zero if any FP deviations)
    11. Return 8 scores: precision, explanation_quality, occurrence_precision, occurrence_recall,
        pricebook_item_precision, quantity_accuracy, unit_cost_accuracy, value_created

    Args:
        input: Input data (not used, deviations are in output/expected)
        output: Dict with "deviations" list
        expected: Dict with "deviations" list
        **kwargs: Additional metadata

    Returns:
        List of 8 Score objects with detailed metrics
    """
    # Constants
    MATCH_THRESHOLD = 0.7
    MAX_VALUE_PER_TASK = 10000.0

    if not expected or "deviations" not in expected:
        raise ValueError("No expected deviations")

    if not output or "deviations" not in output:
        raise ValueError("No output deviations")

    # Parse deviations into Pydantic objects
    output_devs = [Deviation(**d) for d in output["deviations"]]
    expected_devs = [Deviation(**d) for d in expected["deviations"]]

    # Step 1: Match deviations using LLM semantic similarity
    matches = []  # (expected_dev, predicted_dev, similarity_score)
    matched_predicted_indices = set()

    from src.utils.logger import logger

    logger.info(
        f"Starting comprehensive scorer: {len(output_devs)} predicted, {len(expected_devs)} expected"
    )

    for exp_dev in expected_devs:
        # Find candidates with same class
        candidates = [
            (i, pred)
            for i, pred in enumerate(output_devs)
            if pred.deviation_class == exp_dev.deviation_class
            and i not in matched_predicted_indices
        ]

        if not candidates:
            # No candidates for this class - will be counted as FN
            logger.info(f"No candidates for expected: {exp_dev.explanation[:50]}")
            continue

        logger.info(
            f"Found {len(candidates)} candidates for expected: {exp_dev.explanation[:50]}"
        )

        # Score each candidate using LLM
        best_match = None
        best_score = 0.0
        best_matched_occs = []

        for idx, candidate in candidates:
            # Use the deviation_semantic_match LLM classifier
            result = deviation_semantic_match(
                output={
                    "deviation_class": candidate.deviation_class,
                    "explanation": candidate.explanation,
                },
                expected={
                    "deviation_class": exp_dev.deviation_class,
                    "explanation": exp_dev.explanation,
                },
            )

            # Extract score from result (autoevals returns Score object with .score attribute)
            match_score = _extract_score(result)

            logger.info(f"  Candidate {idx}: score={match_score}")

            # Validate occurrences if semantic match is promising
            if match_score > 0:
                # Case 1: Expected has occurrences - validate predicted has matching ones
                if exp_dev.occurrences and len(exp_dev.occurrences) > 0:
                    if not candidate.occurrences or len(candidate.occurrences) == 0:
                        logger.info(
                            f"  Candidate {idx}: NO occurrences but expected has them - REJECT"
                        )
                        continue  # Skip this candidate

                    # Match occurrences
                    matched_occs, _, _ = match_occurrences(
                        candidate.occurrences,
                        exp_dev.occurrences,
                        tolerance_seconds=10,
                    )

                    if len(matched_occs) == 0:
                        logger.info(
                            f"  Candidate {idx}: NO matching occurrences - REJECT"
                        )
                        continue  # Skip - must have ≥1 matching occurrence

                    logger.info(
                        f"  Candidate {idx}: {len(matched_occs)} matching occurrences"
                    )

                # Case 2: Expected has no occurrences, but predicted does - spurious FP
                elif candidate.occurrences and len(candidate.occurrences) > 0:
                    logger.info(f"  Candidate {idx}: SPURIOUS occurrences - REJECT")
                    continue

                # Case 3: Neither has occurrences - OK
                else:
                    matched_occs = []
                    logger.info(f"  Candidate {idx}: no occurrences needed")
            else:
                matched_occs = []

            if match_score > best_score:
                best_score = match_score
                best_match = (idx, candidate)
                best_matched_occs = matched_occs

        # Accept match if above threshold
        if best_match and best_score >= MATCH_THRESHOLD:
            matched_predicted_indices.add(best_match[0])
            matches.append((exp_dev, best_match[1], best_score, best_matched_occs))
            logger.info(f"  ✓ Matched with score {best_score}")
        else:
            logger.info(f"  ✗ No match above threshold (best: {best_score})")

    # Step 2: Compute TP/FP/FN
    tp = len(matches)
    fn = len(expected_devs) - tp  # Expected deviations not matched
    fp = len(output_devs) - tp  # Predicted deviations not matched

    # Step 3: Calculate precision and recall
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # Aggregate occurrence statistics
    total_matched_occs = sum(len(occs) for (_, _, _, occs) in matches)
    total_predicted_occs = sum(len(d.occurrences or []) for d in output_devs)
    total_expected_occs = sum(len(d.occurrences or []) for d in expected_devs)

    occurrence_precision = (
        total_matched_occs / total_predicted_occs
        if total_predicted_occs > 0
        else 1.0  # No predicted occurrences = perfect (didn't hallucinate)
    )

    occurrence_recall = (
        total_matched_occs / total_expected_occs
        if total_expected_occs > 0
        else 1.0  # No expected occurrences = perfect (nothing to find)
    )

    logger.info(
        f"Occurrence metrics: Precision={occurrence_precision:.2f}, Recall={occurrence_recall:.2f}"
    )
    logger.info(
        f"Matched={total_matched_occs}, Predicted={total_predicted_occs}, Expected={total_expected_occs}"
    )

    # Step 4: Score explanation quality on matched pairs
    quality_scores = []
    for exp_dev, pred_dev, _, _ in matches:
        quality_result = explanation_quality(
            output={"explanation": pred_dev.explanation},
            expected={"explanation": exp_dev.explanation},
        )
        quality_score = _extract_score(quality_result)
        quality_scores.append(quality_score)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    # Step 5: Score line item predictions on matched pairs
    line_item_metrics = {
        "tp": 0,
        "fp": 0,
        "fn": 0,
        "quantity_accuracies": [],
        "unit_cost_accuracies": [],
        "values": [],
    }

    for exp_dev, pred_dev, _, _ in matches:
        # Check if both have line items
        if exp_dev.predicted_line_item and pred_dev.predicted_line_item:
            exp_item = exp_dev.predicted_line_item
            pred_item = pred_dev.predicted_line_item

            # Semantic match check
            if (
                exp_item.matched_pricebook_item_display_name
                and pred_item.matched_pricebook_item_display_name
            ):
                match_result = line_item_semantic_match(
                    output={
                        "display_name": pred_item.matched_pricebook_item_display_name
                    },
                    expected={
                        "display_name": exp_item.matched_pricebook_item_display_name
                    },
                )
                match_score = _extract_score(match_result)

                if match_score >= 0.7:  # TP
                    line_item_metrics["tp"] += 1

                    # Calculate quantity accuracy
                    if exp_item.quantity and pred_item.quantity:
                        pct_error = (
                            abs(pred_item.quantity - exp_item.quantity)
                            / exp_item.quantity
                        )
                        quantity_accuracy = max(0.0, 1.0 - pct_error)
                        line_item_metrics["quantity_accuracies"].append(
                            quantity_accuracy
                        )

                    # Calculate unit_cost accuracy
                    if exp_item.unit_cost and pred_item.unit_cost:
                        pct_error = (
                            abs(pred_item.unit_cost - exp_item.unit_cost)
                            / exp_item.unit_cost
                        )
                        unit_cost_accuracy = max(0.0, 1.0 - pct_error)
                        line_item_metrics["unit_cost_accuracies"].append(
                            unit_cost_accuracy
                        )

                    # Calculate value for this deviation (only for TP line items)
                    if pred_item.quantity and pred_item.unit_cost:
                        value = pred_item.quantity * pred_item.unit_cost
                        line_item_metrics["values"].append(value)
                else:  # FP - wrong line item
                    line_item_metrics["fp"] += 1
            else:  # FP - no display name
                line_item_metrics["fp"] += 1
        elif exp_dev.predicted_line_item and not pred_dev.predicted_line_item:
            # FN - expected had line item, predicted didn't
            line_item_metrics["fn"] += 1
        elif not exp_dev.predicted_line_item and pred_dev.predicted_line_item:
            # FP - predicted line item when not expected
            line_item_metrics["fp"] += 1

    # Calculate line item precision
    pricebook_item_precision = (
        line_item_metrics["tp"] / (line_item_metrics["tp"] + line_item_metrics["fp"])
        if (line_item_metrics["tp"] + line_item_metrics["fp"]) > 0
        else 0.0
    )

    # Calculate average quantity and unit cost accuracies
    avg_quantity_accuracy = (
        sum(line_item_metrics["quantity_accuracies"])
        / len(line_item_metrics["quantity_accuracies"])
        if line_item_metrics["quantity_accuracies"]
        else 0.0
    )

    avg_unit_cost_accuracy = (
        sum(line_item_metrics["unit_cost_accuracies"])
        / len(line_item_metrics["unit_cost_accuracies"])
        if line_item_metrics["unit_cost_accuracies"]
        else 0.0
    )

    # Calculate value_created (zero if ANY deviation FPs exist)
    total_value = sum(line_item_metrics["values"])
    value_created_dollars = 0.0 if fp > 0 else total_value

    # Log raw dollar amount as a metric (not constrained to 0-1)
    from braintrust import current_span

    current_span().log(metrics={"value_created_dollars": value_created_dollars})

    # Normalize to 0-1 for the score (using $10k as max reasonable value per task)
    value_created_normalized = min(1.0, value_created_dollars / MAX_VALUE_PER_TASK)

    logger.info(
        f"Line item metrics: TP={line_item_metrics['tp']}, FP={line_item_metrics['fp']}, FN={line_item_metrics['fn']}"
    )
    logger.info(
        f"Quantity accuracy: {avg_quantity_accuracy:.2f}, Unit cost accuracy: {avg_unit_cost_accuracy:.2f}"
    )
    logger.info(
        f"Total value: ${total_value:.2f}, Value created: ${value_created_dollars:.2f} (Deviation FPs: {fp})"
    )
    logger.info(
        f"Value created normalized: {value_created_normalized:.4f} (logged ${value_created_dollars:.2f} as metric)"
    )

    logger.info(
        f"Final metrics: Precision={precision:.2f}, Recall={recall:.2f}, Quality={avg_quality:.2f}"
    )
    logger.info(f"TP={tp}, FP={fp}, FN={fn}")

    # Return EIGHT separate scores as Score objects
    return [
        Score(
            name="precision",
            score=precision,
            metadata={
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "recall": recall,
                "num_matches": len(matches),
                "match_threshold": MATCH_THRESHOLD,
                "matches": [
                    {
                        "expected_explanation": exp.explanation[:100],
                        "predicted_explanation": pred.explanation[:100],
                        "similarity_score": score,
                        "matched_occurrences": len(occs),
                    }
                    for (exp, pred, score, occs) in matches
                ],
            },
        ),
        Score(
            name="explanation_quality",
            score=avg_quality,
            metadata={
                "num_evaluated": len(quality_scores),
                "individual_scores": quality_scores,
            },
        ),
        Score(
            name="occurrence_precision",
            score=occurrence_precision,
            metadata={
                "total_matched": total_matched_occs,
                "total_predicted": total_predicted_occs,
                "occurrence_recall": occurrence_recall,
            },
        ),
        Score(
            name="occurrence_recall",
            score=occurrence_recall,
            metadata={
                "total_matched": total_matched_occs,
                "total_expected": total_expected_occs,
            },
        ),
        Score(
            name="pricebook_item_precision",
            score=pricebook_item_precision,
            metadata={
                "tp": line_item_metrics["tp"],
                "fp": line_item_metrics["fp"],
                "fn": line_item_metrics["fn"],
                "recall": (
                    line_item_metrics["tp"]
                    / (line_item_metrics["tp"] + line_item_metrics["fn"])
                    if (line_item_metrics["tp"] + line_item_metrics["fn"]) > 0
                    else 0.0
                ),
            },
        ),
        Score(
            name="quantity_accuracy",
            score=avg_quantity_accuracy,
            metadata={
                "num_evaluated": len(line_item_metrics["quantity_accuracies"]),
                "individual_accuracies": line_item_metrics["quantity_accuracies"],
            },
        ),
        Score(
            name="unit_cost_accuracy",
            score=avg_unit_cost_accuracy,
            metadata={
                "num_evaluated": len(line_item_metrics["unit_cost_accuracies"]),
                "individual_accuracies": line_item_metrics["unit_cost_accuracies"],
            },
        ),
        Score(
            name="value_created",
            score=value_created_normalized,
            metadata={
                "value_created_dollars": value_created_dollars,
                "max_value_per_task": MAX_VALUE_PER_TASK,
                "total_value": total_value,
                "deviation_fps": fp,
                "num_line_items_with_value": len(line_item_metrics["values"]),
                "individual_values": line_item_metrics["values"],
                "penalized": fp > 0,
            },
        ),
    ]
