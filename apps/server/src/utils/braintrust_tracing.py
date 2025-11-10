"""Braintrust tracing utilities for evaluation and monitoring.

Provides utilities for:
- Creating Braintrust experiments
- Auto-instrumenting OpenAI API calls
- Logging workflow inputs/outputs as spans
- Gracefully handling when tracing is disabled
"""

from contextlib import asynccontextmanager, contextmanager
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Generator

from src.utils.logger import logger

# Import Braintrust, but handle gracefully if not installed
try:
    import braintrust
    from braintrust import init_logger, wrap_openai
    from openai import AsyncOpenAI

    BRAINTRUST_AVAILABLE = True
except ImportError:
    BRAINTRUST_AVAILABLE = False
    logger.warning("Braintrust not installed. Tracing will be disabled.")


@contextmanager
def braintrust_experiment(
    experiment_name: str | None = None,
    project_name: str = "discrepancy-detection",
) -> Generator[Any, None, None]:
    """Context manager for Braintrust experiment.

    Creates a Braintrust experiment for tracking runs. If Braintrust is not
    available or experiment creation fails, returns a no-op context.

    Args:
        experiment_name: Name of the experiment (defaults to timestamp)
        project_name: Braintrust project name

    Yields:
        Braintrust experiment object or None if tracing disabled
    """
    if not BRAINTRUST_AVAILABLE:
        logger.debug("Braintrust not available, skipping experiment creation")
        yield None
        return

    try:
        # Default experiment name to timestamp
        if experiment_name is None:
            experiment_name = f"run-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}"

        logger.info(f"Creating Braintrust experiment: {experiment_name}")
        experiment = braintrust.init(
            project=project_name,
            experiment=experiment_name,
        )

        yield experiment

        # Flush at end
        logger.info("Flushing Braintrust experiment data")
        experiment.flush()

    except Exception as e:
        logger.error(f"Failed to create Braintrust experiment: {e}")
        yield None


@asynccontextmanager
async def traced_openai_client(
    client: AsyncOpenAI,
) -> AsyncGenerator[AsyncOpenAI, None]:
    """Wrap OpenAI client with Braintrust tracing.

    Automatically instruments all OpenAI API calls to log prompts, responses,
    tokens, latency, and costs to Braintrust.

    Args:
        client: OpenAI AsyncOpenAI client instance

    Yields:
        Wrapped OpenAI client (or original if tracing unavailable)
    """
    if not BRAINTRUST_AVAILABLE:
        logger.debug("Braintrust not available, returning unwrapped client")
        yield client
        return

    try:
        logger.info("Wrapping OpenAI client with Braintrust tracing")
        wrapped_client = wrap_openai(client)
        yield wrapped_client
    except Exception as e:
        logger.error(f"Failed to wrap OpenAI client: {e}")
        yield client


@contextmanager
def braintrust_span(
    experiment: Any,
    name: str,
    input: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """Context manager for creating a Braintrust span.

    Logs a span with inputs and outputs. Use for tracking workflow steps.

    Args:
        experiment: Braintrust experiment object
        name: Name of the span
        input: Input data to log
        metadata: Optional metadata

    Yields:
        Span object for logging additional data

    Example:
        with braintrust_span(exp, "analyze_call", input={"uuid": "123"}) as span:
            result = do_analysis()
            span.log(output=result, scores={"accuracy": 0.95})
    """
    if experiment is None or not BRAINTRUST_AVAILABLE:
        # No-op span
        class NoOpSpan:
            def log(self, **kwargs):
                pass

        yield NoOpSpan()
        return

    try:
        logger.debug(f"Starting Braintrust span: {name}")
        span = experiment.start_span(
            name=name,
            input=input,
            metadata=metadata,
        )

        yield span

        # Span auto-closes on exit
        logger.debug(f"Completed Braintrust span: {name}")

    except Exception as e:
        logger.error(f"Error in Braintrust span {name}: {e}")
        # Yield no-op span to prevent crashes
        class NoOpSpan:
            def log(self, **kwargs):
                pass

        yield NoOpSpan()


def log_workflow_run(
    experiment: Any,
    uuid: str,
    inputs: dict[str, Any],
    output: dict[str, Any],
    metadata: dict[str, Any] | None = None,
) -> None:
    """Log a complete workflow run to Braintrust.

    Convenience function for logging a full workflow execution with inputs/outputs.

    Args:
        experiment: Braintrust experiment object
        uuid: Unique identifier for this run
        inputs: Workflow inputs
        output: Workflow outputs
        metadata: Optional metadata
    """
    if experiment is None or not BRAINTRUST_AVAILABLE:
        return

    try:
        logger.debug(f"Logging workflow run to Braintrust: {uuid}")
        experiment.log(
            id=uuid,
            input=inputs,
            output=output,
            metadata=metadata,
        )
    except Exception as e:
        logger.error(f"Failed to log workflow run {uuid}: {e}")


def init_braintrust_logger():
    """Initialize Braintrust logger for automatic OpenAI tracing.

    Call this at module/app startup to enable automatic tracing of OpenAI calls.
    Safe to call even if Braintrust is not installed.
    """
    if not BRAINTRUST_AVAILABLE:
        logger.debug("Braintrust not available, skipping logger initialization")
        return

    try:
        init_logger()
        logger.info("Braintrust logger initialized for automatic OpenAI tracing")
    except Exception as e:
        logger.error(f"Failed to initialize Braintrust logger: {e}")
