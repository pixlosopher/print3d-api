#!/usr/bin/env python3
"""
Start the Print3D web API server.

Usage:
    python run_web.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from web.api import main

if __name__ == "__main__":
    main()
