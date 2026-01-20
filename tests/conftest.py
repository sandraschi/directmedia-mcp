"""Pytest configuration for directmedia-mcp tests."""

import pytest
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Test fixtures can be added here
@pytest.fixture
def sample_dki_file():
    """Fixture for sample DKI file path."""
    # Return a path to a test DKI file if available
    return None

@pytest.fixture
def temp_output_dir(tmp_path):
    """Fixture for temporary output directory."""
    return tmp_path / "output"
    return tmp_path / "output"




