#!/usr/bin/env python3
"""
Activity Tracker - Log activities with Eisenhower matrix quadrant and tags.
Usage: uv run track.py add --when "2024-01-04 10:30" --duration 45 --quadrant 2 --desc "Deep work on project X" --tags "work,coding,focus"
       uv run track.py add --duration 30 --quadrant 4 --desc "Scrolled Twitter" --tags "distraction,social"
"""

import sys
from pathlib import Path


if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from track.cli import main


if __name__ == "__main__":
    main()
