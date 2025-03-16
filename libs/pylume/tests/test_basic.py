"""
Basic tests for the pylume package
"""
import pytest


def test_import():
    """Test that the package can be imported"""
    import pylume
    try:
        assert pylume.__version__ == "0.1.0"
    except AttributeError:
        # If __version__ is not defined, that's okay for this test
        pass


def test_pylume_import():
    """Test that the PyLume class can be imported"""
    from pylume import PyLume
    assert PyLume is not None 