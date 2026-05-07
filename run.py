#!/usr/bin/env python3
"""
Cedarbrook — AI Agent Simulation
Run this to start the local server and dashboard.
Open http://localhost:3000 in your browser.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from engine.server import run
from engine.world_clock import load_clock

if __name__ == "__main__":
    clock = load_clock()
    print("=" * 48)
    print("  CEDARBROOK — AI Agent Simulation")
    print("=" * 48)
    print(f"  Day {clock['day']} | Hour {clock['hour']} | {'RUNNING' if clock.get('running') else 'PAUSED'}")
    print(f"  Dashboard → http://localhost:3000")
    print("  Press Ctrl+C to shut down.")
    print("=" * 48)
    run()
