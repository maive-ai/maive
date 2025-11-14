import inspect
import logging
import os

from pythonjsonlogger import jsonlogger


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

            formatter = jsonlogger.JsonFormatter(
                "%(asctime)s %(levelname)s %(message)s",
                rename_fields={"asctime": "@timestamp", "levelname": "log_level"},
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
        
        kwargs["file"] = file_info
        self.log(logging.ERROR, msg, *args, **kwargs)

    def exception(
        self, msg: str, *args: tuple, exc_info: bool = True, **kwargs: dict
    ) -> None:
        """Delegate an exception call to the underlying logger with file and line info."""
        frame = inspect.currentframe()
        if frame and frame.f_back:
            file_info = f"{frame.f_back.f_code.co_filename}:{frame.f_back.f_lineno}"
        else:
            file_info = "unknown:0"
        
        kwargs["file"] = file_info
        self.log(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)

    def process(self, msg: str, kwargs: dict) -> tuple[str, dict]:
        # pythonjsonlogger automatically picks up 'extra' fields
        # Extract logging-specific kwargs that shouldn't go into 'extra'
        exc_info = kwargs.pop("exc_info", None)
        stack_info = kwargs.pop("stack_info", None)
        stacklevel = kwargs.pop("stacklevel", None)
        
        result_kwargs = {}
        if kwargs:
            result_kwargs["extra"] = kwargs
        if exc_info is not None:
            result_kwargs["exc_info"] = exc_info
        if stack_info is not None:
            result_kwargs["stack_info"] = stack_info
        if stacklevel is not None:
            result_kwargs["stacklevel"] = stacklevel
            
        return msg, result_kwargs


# Create a singleton instance
logger = Logger()
logger.info(
    f"Logging level set to {logging.getLevelName(logger.logger.getEffectiveLevel())}"
)


def test_logger() -> None:
    logger.info("No extra")
    logger.info("hello world", foo="bar", two=2, test=[1, 2, 3], nan=None)
