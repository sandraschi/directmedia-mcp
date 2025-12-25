# DirectMedia MCP Tests

This directory contains the test suite for the DirectMedia MCP server.

## Test Structure

- `test_directmedia.py` - Tests for the main DirectMedia decompressor functionality
- `test_epub.py` - Tests for EPUB conversion features
- `conftest.py` - Pytest configuration and fixtures
- `run_tests.py` - Test runner script

## Running Tests

### Using pytest directly:
```bash
pytest tests/
```

### Using the test runner:
```bash
python tests/run_tests.py
```

### With coverage:
```bash
pytest --cov=directmedia_mcp tests/
```

## Test Categories

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test the full decompression pipeline
- **Slow tests**: Marked with `@pytest.mark.slow` - can be skipped with `-m "not slow"`

## Adding New Tests

1. Create test files with the pattern `test_*.py`
2. Use descriptive test function names starting with `test_`
3. Use fixtures from `conftest.py` for common test setup
4. Mark slow tests with `@pytest.mark.slow`

## Test Fixtures

- `sample_dki_file`: Path to a sample DKI file for testing
- `temp_output_dir`: Temporary directory for test outputs
