"""Pytest configuration for backend tests."""
import sys
import os

# Ensure 'app' package is importable from tests
sys.path.insert(0, os.path.dirname(__file__))
