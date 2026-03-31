#!/usr/bin/env python3
"""Compatibility shim for white-paper plot generation."""

from scripts.demos.generate_plots import *  # noqa: F401,F403
from scripts.demos.generate_plots import main


if __name__ == "__main__":
    main()
