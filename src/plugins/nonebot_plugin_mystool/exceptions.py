from .utils import logger


class MystoolException(Exception):
    """Base genshinhelper exception."""

    def __init__(self, message):
        super().__init__(message)
        logger.error(message)
