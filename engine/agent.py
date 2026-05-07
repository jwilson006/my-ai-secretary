import json
import subprocess
import os
from pathlib import Path
from datetime import datetime

AGENTS_DIR = Path(__file__).parent.parent / "world" / "agents"
LOGS_DIR = Path(__file__).parent.parent / "world" / "logs"
WORLD_CONFIG_PATH = Path(__file__).parent.parent / "world" / "config" / "world.json"

AGENT_IDS = ["erin_maroni", "lily_maroni", "david_callahan", "isabel_callahan"]


def load_profile(agent_id):
    path = AGENTS_DIR / agent_id / "profile.json"
    with open(path) as f:
        return json.load(f)


def load_state(agent_id):
    path = AGENTS_DIR / agent_id / "state.json"
    with open(path) as f:
        return json.load(f)


def save_state(agent_id, state):
    path = AGENTS_DIR / agent_id / "state.json"
    with open(path, "w") as f:
        json.dump(state, f, indent=2)


def load_world_config():
    with open(WORLD_CONFIG_PATH) as f:
        return json.load(f)


def log_activity(agent_id, entry):
    log_path = LOGS_DIR / "activity_feed.json"
    try:
        with open(log_path) as f:
            feed = json.load(f)
    except Exception:
        feed = []

    feed.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_id,
        **entry
    })
    # Keep last 200 entries
    feed = feed[:200]
    with open(log_path, "w") as f:
        json.dump(feed, f, indent=2)


def build_prompt(agent_id, clock_state):
    profile = load_profile(agent_id)
    state = load_state(agent_id)
    world = load_world_config()

    hour = clock_state["hour"]
    day = clock_state["day"]
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    hour_labels = [
        "12:00 AM","1:00 AM","2:00 AM","3:00 AM","4:00 AM","5:00 AM",
        "6:00 AM","7:00 AM","8:00 AM","9:00 AM","10:00 AM","11:00 AM",
        "12:00 PM","1:00 PM","2:00 PM","3:00 PM","4:00 PM","5:00 PM",
        "6:00 PM","7:00 PM","8:00 PM","9:00 PM","10:00 PM","11:00 PM"
    ]
    time_label = f"{day_names[clock_state['day_of_week']]}, Day {day} — {hour_labels[hour]}"

    assigned_tasks = state.get("assigned_tasks", [])
    task_section = ""
    if assigned_tasks:
        task_list = "\n".join(f"- {t}" for t in assigned_tasks)
        task_section = f"\nYou have been assigned the following tasks:\n{task_list}\n"

    prompt = f"""{profile['system_prompt']}

---
WORLD: {world['name']}, {world['state']}
CURRENT TIME: {time_label}
YOUR LOCATION: {state['current_location']} / {state['current_room']}
YOUR MOOD: {state['mood']}
YOUR ENERGY: {state['energy']}/100
YOUR CURRENT ACTIVITY: {state['current_activity']}
{task_section}
---

Based on the current time and your personality, respond with ONLY a valid JSON object in this exact format:
{{
  "activity": "what you are doing right now (short phrase)",
  "location": "location_id from: maroni_house, callahan_house, cornerstone_church, maroni_fashion_hq",
  "room": "which room within the location",
  "mood": "one word mood",
  "energy": <number 0-100>,
  "thought": "what is on your mind right now (1-2 sentences, first person)",
  "dialogue": "something you might say out loud right now, or null if you are alone and quiet",
  "task_completed": "name of task if you completed one this hour, or null",
  "action": "any notable action you took this hour (created a file, wrote blog post, held meeting, etc.), or null"
}}

Only return the JSON. No other text."""

    return prompt


def run_agent_tick(agent_id, clock_state):
    prompt = build_prompt(agent_id, clock_state)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        raw = result.stdout.strip()

        # Extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in response")

        response = json.loads(raw[start:end])

        state = load_state(agent_id)
        state["current_activity"] = response.get("activity", state["current_activity"])
        state["current_location"] = response.get("location", state["current_location"])
        state["current_room"] = response.get("room", state["current_room"])
        state["mood"] = response.get("mood", state["mood"])
        state["energy"] = response.get("energy", state["energy"])
        state["recent_thought"] = response.get("thought", "")
        state["last_dialogue"] = response.get("dialogue") or ""

        # Handle completed tasks
        completed = response.get("task_completed")
        if completed and completed in state.get("assigned_tasks", []):
            state["assigned_tasks"].remove(completed)
            if "completed_tasks" not in state:
                state["completed_tasks"] = []
            state["completed_tasks"].append(completed)

        save_state(agent_id, state)

        log_activity(agent_id, {
            "time_label": f"Day {clock_state['day']} Hour {clock_state['hour']}",
            "activity": response.get("activity", ""),
            "location": response.get("location", ""),
            "room": response.get("room", ""),
            "thought": response.get("thought", ""),
            "dialogue": response.get("dialogue"),
            "action": response.get("action")
        })

        return response

    except subprocess.TimeoutExpired:
        log_activity(agent_id, {"error": "claude call timed out"})
        return None
    except Exception as e:
        log_activity(agent_id, {"error": str(e)})
        return None


def assign_task(agent_id, task):
    state = load_state(agent_id)
    if "assigned_tasks" not in state:
        state["assigned_tasks"] = []
    state["assigned_tasks"].append(task)
    save_state(agent_id, state)
