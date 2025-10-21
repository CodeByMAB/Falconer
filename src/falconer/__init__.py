"""Falconer - A Bitcoin-native AI agent built to hunt for insights and earn sats."""

__version__ = "0.1.0"
__author__ = "CodeByMAB"
__email__ = "mabcode@protonmail.com"

from .config import Config
from .logging import setup_logging

__all__ = ["Config", "setup_logging"]

if __name__ == "__main__":
    app(prog_name="falconer")
