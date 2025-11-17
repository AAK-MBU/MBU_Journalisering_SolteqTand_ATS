"""Module for cleaning up temporary folder after processing"""

import logging
import os
import shutil

from helpers.config import DOCUMENT_PATH

logger = logging.getLogger(__name__)


def clean_up():
    """Function to clean up temporary folder"""
    try:
        logger.info("Starting cleanup of temporary folder...")
        path = DOCUMENT_PATH
        if os.path.exists(path):
            shutil.rmtree(path)
            logger.info("Temporary folder cleaned up successfully.")
        else:
            logger.info("Temporary folder does not exist. No cleanup needed.")
    except OSError as e:
        logger.error("Error during cleanup: %s", e)
        raise RuntimeError("Cleanup failed: " + str(e)) from e
