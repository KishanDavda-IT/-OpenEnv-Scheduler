# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

OpenEnv Scheduler is a deterministic scheduling environment for the Meta PyTorch OpenEnv Hackathon. AI agents must schedule meetings on a 9-hour calendar (09:00–18:00, 18 slots of 30 minutes each) while respecting constraints like lunch blocks, preferred windows, and fixed events.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run standalone demo (no servers)
python demo_script.py

# Run tests
python tests/qa.py

# Start API server (port 8000)
uvicorn api.app:app --host 0.0.0.0 --port 8000

# Start Gradio UI (port 7860)
python demo/app.py

# Docker build and run
docker build -t scheduling-env .
docker run -p 8000:8000 -p 7860:7860 scheduling-env
```

## Architecture

```
core_env/               # Core environment (OpenEnv-compliant)
  models.py             # Pydantic models: Action, Observation, Reward, Meeting, ScheduledEvent, TaskConfig
  scheduler.py          # SchedulingEnv class with reset(), step(), state() methods
  grader.py             # Deterministic scorer returning 0.0–1.0
  tasks.py              # Task definitions: task_1_easy, task_2_medium, task_3_hard

agent/
  baseline.py           # RuleBasedAgent — greedy heuristic baseline

api/app.py              # FastAPI endpoints: /tasks, /reset, /step, /grader, /baseline
demo/app.py             # Gradio web UI on port 7860
demo_script.py          # Standalone demo without server dependencies
tests/qa.py             # 13 validation tests
```

## Action Space

- **0–17**: Place meeting at slot (09:00 to 17:30 in 30-min increments)
- **18**: SKIP — reject current meeting (heavy penalty)
- **19**: RESCHEDULE — undo last placement and re-queue it (small penalty)

## Environment API

```python
env = SchedulingEnv("task_1_easy")
obs = env.reset()                          # Returns Observation
obs, reward, done, info = env.step(Action(slot_index=2))  # Take action
obs = env.state()                          # Get current observation
```

## Grader Scoring (0.0–1.0)

- 30% Scheduled meetings ratio
- 20% No-conflict ratio
- 20% Priority-weighted success
- 20% Constraint satisfaction (preferences + lunch avoidance)
- 10% Efficiency (compactness + earliness)

## Key Constraints

- Lunch blocks: slots 6–9 (12:00–14:00) — avoid if `avoid_lunch=True`
- Fixed events are immovable and cannot overlap
- Meetings with `preferred_start_window` get ±5 reward based on match
- High-priority meetings (priority ≥ 3) have heavy penalties when missed
