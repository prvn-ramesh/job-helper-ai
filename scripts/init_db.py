#!/usr/bin/env python3
import sys
from pathlib import Path

# Add src to pythonpath
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from infrastructure.database.sqlite import init_db

if __name__ == "__main__":
    init_db()
