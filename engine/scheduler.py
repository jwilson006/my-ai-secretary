import time
import threading
from engine import world_clock, agent

# 1 real hour = 1 in-world day (24 ticks)
# So 1 tick = 2.5 real minutes = 150 seconds
TICK_INTERVAL_SECONDS = 150

_scheduler_thread = None
_stop_event = threading.Event()


def run_tick():
    clock_state = world_clock.tick()
    print(f"\n[TICK] {world_clock.get_time_label()}")

    for agent_id in agent.AGENT_IDS:
        print(f"  → Running {agent_id}...")
        result = agent.run_agent_tick(agent_id, clock_state)
        if result:
            print(f"     {result.get('activity', '?')} | {result.get('mood', '?')}")
        # Small gap between agents to avoid hammering claude CLI
        time.sleep(3)


def _loop():
    while not _stop_event.is_set():
        if world_clock.is_running():
            run_tick()
        _stop_event.wait(timeout=TICK_INTERVAL_SECONDS)


def start():
    global _scheduler_thread, _stop_event

    world_clock.set_running(True)

    if _scheduler_thread and _scheduler_thread.is_alive():
        print("[Scheduler] Already running.")
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_loop, daemon=True)
    _scheduler_thread.start()
    print(f"[Scheduler] Started. Tick every {TICK_INTERVAL_SECONDS}s = 1 in-world hour.")


def stop():
    world_clock.set_running(False)
    _stop_event.set()
    print("[Scheduler] Stopped.")


def is_running():
    return world_clock.is_running()
