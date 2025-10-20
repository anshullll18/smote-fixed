import logging
import logging.config
import sys


def configure_logging(level: str = "INFO") -> None:
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                },
                "uvicorn": {
                    "()": "uvicorn.logging.DefaultFormatter",
                    "fmt": "%(levelprefix)s %(asctime)s %(name)s %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                    "use_colors": True,
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "stream": sys.stdout,
                },
                "uvicorn": {
                    "class": "logging.StreamHandler",
                    "formatter": "uvicorn",
                    "stream": sys.stdout,
                },
            },
            "loggers": {
                "": {"handlers": ["default"], "level": level},
                "uvicorn": {
                    "handlers": ["uvicorn"],
                    "level": level,
                    "propagate": False,
                },
                "uvicorn.error": {"level": level, "propagate": True},
                "uvicorn.access": {
                    "handlers": ["uvicorn"],
                    "level": level,
                    "propagate": False,
                },
            },
        }
    )
