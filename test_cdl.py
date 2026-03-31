#!/usr/bin/env python3
"""Compatibility runner for the reorganized test suite."""

from tests.test_suite import run_all_tests


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
