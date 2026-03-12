"""Pytest configuration for GTA VII test suite."""
import sys
import os

# Ensure the src directory is on the Python path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
