import json
import os
from pathlib import Path

WORLD_CONFIG_PATH = Path(__file__).parent.parent / "world" / "config" / "world.json"
CLOCK_STATE_PATH = Path(__file__).parent.parent / "world" / "config" / "clock_state.json"

HOUR_LABELS = [
    "12:00 AM", "1:00 AM", "2:00 AM", "3:00 AM", "4:00 AM", "5:00 AM",
    "6:00 AM", "7:00 AM", "8:00 AM", "9:00 AM", "10:00 AM", "11:00 AM",
    "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM", "4:00 PM", "5:00 PM",
    "6:00 PM", "7:00 PM", "8:00 PM", "9:00 PM", "10:00 PM", "11:00 PM"
]

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def load_clock():
    if CLOCK_STATE_PATH.exists():
        with open(CLOCK_STATE_PATH) as f:
            return json.load(f)
    return {"day": 1, "hour": 0, "running": False, "day_of_week": 0}


def save_clock(state):
    with open(CLOCK_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def tick():
    state = load_clock()
    state["hour"] += 1
    if state["hour"] >= 24:
        state["hour"] = 0
        state["day"] += 1
        state["day_of_week"] = (state["day_of_week"] + 1) % 7
    save_clock(state)
    return state


def get_time_label():
    state = load_clock()
    hour_label = HOUR_LABELS[state["hour"]]
    day_name = DAY_NAMES[state["day_of_week"]]
    return f"{day_name}, Day {state['day']} — {hour_label}"


def is_running():
    return load_clock().get("running", False)


def set_running(value: bool):
    state = load_clock()
    state["running"] = value
    save_clock(state)


def reset():
    save_clock({"day": 1, "hour": 0, "running": False, "day_of_week": 0})
