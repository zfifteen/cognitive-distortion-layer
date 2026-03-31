#!/usr/bin/env python3
"""Compatibility shim for the canonical CDL API."""

from cdl_impl.core import *  # noqa: F401,F403
from cdl_impl.core import main


if __name__ == "__main__":
    main()
