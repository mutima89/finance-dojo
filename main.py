"""Entry point: python main.py (also the PyInstaller entry script)."""
import sys

from fts.ui.app import run

if __name__ == "__main__":
    sys.exit(run())
