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

from evals.estimate_deviation.schemas import Deviation

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
    model="gpt-4o-mini",
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


def comprehensive_deviation_scorer(input, output, expected=None, **kwargs) -> EvalScorer:
    """Comprehensive scorer with LLM-based semantic matching + deterministic metrics.

    Workflow:
    1. Match predicted deviations to expected using LLM semantic similarity
    2. Compute TP/FP/FN counts from matches
    3. Calculate precision, recall, F1
    4. Score explanation quality on matched pairs
    5. Return combined score + detailed breakdown

    Args:
        input: Input data (not used, deviations are in output/expected)
        output: Dict with "deviations" list
        expected: Dict with "deviations" list
        **kwargs: Additional metadata

    Returns:
        Dict with score and detailed metrics
    """
    if not expected or "deviations" not in expected:
        return None

    if not output or "deviations" not in output:
        return {
            "name": "comprehensive_score",
            "score": 0.0,
            "metadata": {"error": "No output deviations"},
        }

    try:
        # Parse deviations into Pydantic objects
        output_devs = [Deviation(**d) for d in output["deviations"]]
        expected_devs = [Deviation(**d) for d in expected["deviations"]]

        # Step 1: Match deviations using LLM semantic similarity
        matches = []  # (expected_dev, predicted_dev, similarity_score)
        matched_predicted_indices = set()

        from src.utils.logger import logger as debug_logger

        debug_logger.info(
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
                debug_logger.info(
                    f"No candidates for expected: {exp_dev.explanation[:50]}"
                )
                continue

            debug_logger.info(
                f"Found {len(candidates)} candidates for expected: {exp_dev.explanation[:50]}"
            )

            # Score each candidate using LLM
            best_match = None
            best_score = 0.0

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
                if isinstance(result, dict):
                    match_score = result.get("score", 0.0)
                elif hasattr(result, "score"):
                    match_score = result.score
                else:
                    match_score = float(result) if result is not None else 0.0

                debug_logger.info(f"  Candidate {idx}: score={match_score}")

                if match_score > best_score:
                    best_score = match_score
                    best_match = (idx, candidate)

            # Accept match if above threshold
            MATCH_THRESHOLD = 0.7
            if best_match and best_score >= MATCH_THRESHOLD:
                matched_predicted_indices.add(best_match[0])
                matches.append((exp_dev, best_match[1], best_score))
                debug_logger.info(f"  ✓ Matched with score {best_score}")
            else:
                debug_logger.info(f"  ✗ No match above threshold (best: {best_score})")

        # Step 2: Compute TP/FP/FN
        tp = len(matches)
        fn = len(expected_devs) - tp  # Expected deviations not matched
        fp = len(output_devs) - tp  # Predicted deviations not matched

        # Step 3: Calculate precision and recall
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        # Step 4: Score explanation quality on matched pairs
        quality_scores = []
        for exp_dev, pred_dev, _ in matches:
            quality_result = explanation_quality(
                output={"explanation": pred_dev.explanation},
                expected={"explanation": exp_dev.explanation},
            )
            # Extract score from Score object or dict
            if isinstance(quality_result, dict):
                quality_score = quality_result.get("score", 0.0)
            elif hasattr(quality_result, "score"):
                quality_score = quality_result.score
            else:
                quality_score = (
                    float(quality_result) if quality_result is not None else 0.0
                )
            quality_scores.append(quality_score)

        avg_quality = (
            sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
        )

        debug_logger.info(
            f"Final metrics: Precision={precision:.2f}, Recall={recall:.2f}, Quality={avg_quality:.2f}"
        )
        debug_logger.info(f"TP={tp}, FP={fp}, FN={fn}")

        # Return TWO separate scores as Score objects: precision and explanation quality
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
                        }
                        for (exp, pred, score) in matches
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
        ]

    except Exception as e:
        import traceback

        return {
            "name": "comprehensive_score",
            "score": 0.0,
            "metadata": {"error": str(e), "traceback": traceback.format_exc()},
        }
