"""
@Project   : genshinhelper
@Author    : y1ndan
@Blog      : https://www.yindan.me
@GitHub    : https://github.com/y1ndan
"""

from .utils import logger


class MystoolException(Exception):
    """Base genshinhelper exception."""

    def __init__(self, message):
        super().__init__(message)
        logger.error(message)
