#!/usr/bin/env python3
"""Compatibility shim for the baseline validation report."""

from scripts.reports.baseline_report import *  # noqa: F401,F403
from scripts.reports.baseline_report import main


if __name__ == "__main__":
    main()
