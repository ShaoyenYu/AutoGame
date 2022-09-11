import logging
import sys

from paddleocr.ppocr.utils.logging import get_logger


def init_logger(name=None, default_level=logging.INFO):
    logger = logging.Logger(name)

    formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(stream_handler)
    logger.setLevel(default_level)
    return logger


logger_paddle = get_logger()
logger_paddle.setLevel("INFO")
