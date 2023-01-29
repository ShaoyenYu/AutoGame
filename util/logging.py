import logging
import sys


def init_logger(name=None, default_level=logging.INFO):
    logger = logging.Logger(name)

    formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(stream_handler)
    logger.setLevel(default_level)
    return logger
