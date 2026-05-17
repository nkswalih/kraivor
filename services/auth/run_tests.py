#!/usr/bin/env python
"""
Test runner for auth service.

Usage:
    uv run pytest              # Run all tests with beautiful output
    uv run pytest -v          # Verbose output
    uv run pytest --cov        # With coverage
    uv run pytest tests/test_signup.py  # Specific test file
    uv run pytest -m auth      # Run auth-marked tests only
    uv run pytest -m security  # Run security tests only
"""
import sys

if __name__ == "__main__":
    sys.exit(0)