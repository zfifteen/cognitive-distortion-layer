#!/usr/bin/env python3
"""Compatibility shim for the curvature gist demo."""

if __name__ == "__main__":
    import runpy
    runpy.run_module("scripts.demos.curvature_gist", run_name="__main__")
else:
    from scripts.demos.curvature_gist import *  # noqa: F401,F403
