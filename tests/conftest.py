"""Create the ignored parent required by the repository pytest basetemp."""
from pathlib import Path


def pytest_configure() -> None:
    (Path(__file__).resolve().parent / "test-vault").mkdir(exist_ok=True)
