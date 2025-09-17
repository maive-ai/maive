import inspect
import logging
import os
from typing import Any


class Logger(logging.LoggerAdapter):
    _instance = None
    _initialized = False

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not Logger._initialized:
            # Get log level from environment variable, default to INFO
            log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()

            # Map string log levels to logging constants
            log_level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }

            # Set default level to INFO if invalid level specified
            log_level = log_level_map.get(log_level_str, logging.INFO)

            formatter = logging.Formatter(
                fmt=(
                    '{"@timestamp": "%(asctime)s", '
                    '"log_level": "%(levelname)s", '
                    '"message": "%(message)s", '
                    '"data": "%(log_dict)s"}'
                ),
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)

            logger = logging.getLogger("maive")
            logger.setLevel(log_level)
            logger.addHandler(handler)

            super().__init__(logger)
            Logger._initialized = True

    def error(self, msg: str, *args: tuple, **kwargs: dict) -> None:
        """Delegate an error call to the underlying logger with file and line info."""
        frame = inspect.currentframe()
        if frame and frame.f_back:
            file_info = f"{frame.f_back.f_code.co_filename}:{frame.f_back.f_lineno}"
        else:
            file_info = "unknown:0"
        # Filter out logging-specific kwargs to avoid conflicts
        log_kwargs: dict[str, Any] = {
            k: v
            for k, v in kwargs.items()
            if k not in ["exc_info", "stack_info", "stacklevel"]
        }
        self.log(logging.ERROR, f"{msg} (at {file_info})", *args, **log_kwargs)

    def exception(
        self, msg: str, *args: tuple, exc_info: bool = True, **kwargs: dict
    ) -> None:
        """Delegate an exception call to the underlying logger with file and line info."""
        frame = inspect.currentframe()
        if frame and frame.f_back:
            file_info = f"{frame.f_back.f_code.co_filename}:{frame.f_back.f_lineno}"
        else:
            file_info = "unknown:0"
        # Filter out logging-specific kwargs to avoid conflicts
        log_kwargs: dict[str, Any] = {
            k: v
            for k, v in kwargs.items()
            if k not in ["exc_info", "stack_info", "stacklevel"]
        }
        self.log(
            logging.ERROR,
            f"{msg} (at {file_info})",
            *args,
            exc_info=exc_info,
            **log_kwargs,
        )

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        kwargs = {"extra": {"log_dict": kwargs if kwargs is not None else {}}}
        return msg, kwargs


# Create a singleton instance
logger = Logger()
logger.info(
    f"Logging level set to {logging.getLevelName(logger.logger.getEffectiveLevel())}"
)


def test_logger() -> None:
    logger.info("No extra")
    logger.info("hello world", foo="bar", two=2, test=[1, 2, 3], nan=None)
