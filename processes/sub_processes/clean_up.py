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


def release_keys() -> None:
    """Release Ctrl, Alt, and Shift keys if they are stuck."""

    logger.info("Releasing Ctrl, Alt, and Shift keys.")
    # pylint: disable-next = import-outside-toplevel
    import ctypes

    try:
        # Use Windows API to release keys
        user32 = ctypes.windll.user32

        # Key codes
        keys_to_release = [
            0x11,  # VK_CONTROL
            0x10,  # VK_SHIFT
            0x12,  # VK_MENU (Alt)
            0x5B,  # VK_LWIN
            0x5C,  # VK_RWIN
            0xA2,  # VK_LCONTROL
            0xA3,  # VK_RCONTROL
            0xA0,  # VK_LSHIFT
            0xA1,  # VK_RSHIFT
            0xA4,  # VK_LMENU
            0xA5,  # VK_RMENU
        ]

        # Send key up events (0x0002 is KEYEVENTF_KEYUP)
        for key in keys_to_release:
            user32.keybd_event(key, 0, 0x0002, 0)

    # pylint: disable-next = broad-exception-caught
    except Exception as e:
        logger.error(f"Error releasing keys: {e}")
