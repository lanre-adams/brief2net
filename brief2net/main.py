#!/usr/bin/env python3
"""brief2net — entry point.

Double-click / run with no arguments for a guided prompt, or see
`python main.py --help` for the command-line options.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brief2net.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
