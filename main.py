#!/usr/bin/env python3
"""Compatibility shim for the cognitive frame-shift demo."""

from scripts.demos.main import *  # noqa: F401,F403
from scripts.demos.main import main


if __name__ == "__main__":
    main()
