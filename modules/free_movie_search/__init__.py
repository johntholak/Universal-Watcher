"""Import-compatible package facade for the hyphenated free-movie-search directory."""
from pathlib import Path

__path__ = [str(Path(__file__).resolve().parents[1] / "free-movie-search")]
