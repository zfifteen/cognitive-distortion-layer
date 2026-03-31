#!/usr/bin/env python3
"""Compatibility shim for the CDL dashboard generator."""

from scripts.dashboards.generate_cdl_dashboards import *  # noqa: F401,F403
from scripts.dashboards.generate_cdl_dashboards import main


if __name__ == "__main__":
    main()
