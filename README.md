---
title: OpenEnv Scheduler
emoji: 🤖
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🤖 OpenEnv Scheduler

> An OpenEnv-compliant Scheduling Assistant environment for the **Meta PyTorch OpenEnv Hackathon**.  
> A deterministic simulation where AI agents schedule meetings on a calendar while respecting real-world constraints.

---

## 📋 Project Plan

This environment simulates a 9-hour workday calendar (09:00–18:00) divided into 30-minute slots. An AI agent receives meeting requests and must place them optimally while navigating constraints like lunch breaks, preferred time windows, priority conflicts, and fixed immovable events. The environment provides dense rewards for each action and a deterministic final score (0.0–1.0) via a built-in grader.

---

## 📁 Folder Structure

```
openenv_scheduler/
├── core_env/               # Core environment package
│   ├── __init__.py         # Re-exports key classes
│   ├── models.py           # Pydantic models (Action, Observation, Reward, etc.)
│   ├── scheduler.py        # SchedulingEnv — the main OpenEnv environment
│   ├── grader.py           # Deterministic grader (0.0 to 1.0)
│   └── tasks.py            # Easy, Medium, Hard task definitions
├── agent/                  # Agent implementations
│   ├── __init__.py         # Re-exports RuleBasedAgent
│   └── baseline.py         # Greedy rule-based baseline agent
├── api/                    # FastAPI backend
│   ├── __init__.py
│   └── app.py              # REST API endpoints
├── demo/                   # Gradio web UI
│   ├── __init__.py
│   └── app.py              # Gradio Blocks app (port 7860)
├── tests/                  # QA test suite
│   └── qa.py               # 10+ automated validation tests
├── demo_script.py          # Standalone demo script (no Docker needed)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build file
├── run.sh                  # Entrypoint script (API + Gradio)
└── README.md               # This file
```

---

## ✨ Features

| Feature | Description |
|---|---|
| **OpenEnv Compliant** | Typed Pydantic models (`Action`, `Observation`, `Reward`) and standard methods (`reset()`, `step()`, `state()`) |
| **Fixed Events** | Pre-existing immovable calendar blocks (e.g., standups, exec syncs) |
| **Dense Rewards** | Intermediate rewards for valid placements, constraint satisfaction, and penalties for conflicts |
| **Deterministic Grader** | Final score from 0.0 to 1.0 based on efficiency, constraints, priority, and conflicts |
| **3 Task Difficulties** | Easy, Medium, and Hard scenarios with increasing complexity |
| **3 Agent Actions** | Place a meeting, Skip/reject a meeting, Reschedule the last placement |
| **Baseline Agent** | Rule-based greedy agent demonstrating environment usage |
| **Gradio Demo** | Interactive web UI visualizing calendar, agent decisions, and scores |
| **FastAPI Backend** | Programmatic API for running scenarios and interactive play |
| **HF Spaces Ready** | Deployable to Hugging Face Spaces via Docker |

---

## 🎯 Action & Observation Space

### Action Space
| Value | Action | Description |
|---|---|---|
| `0–17` | **Place** | Schedule meeting at the given 30-min slot (09:00 to 17:30) |
| `18` | **Skip** | Reject the current meeting entirely (heavy penalty) |
| `19` | **Reschedule** | Remove last placed meeting and re-queue it (small penalty) |

### Observation Space
```python
Observation(
    calendar       = [ScheduledEvent(...)],    # Current calendar state (fixed + placed)
    current_meeting = Meeting(...),             # Meeting request to handle
    remaining_meetings = [Meeting(...)],        # Queue of future meetings
    valid_slots    = [0, 1, 5, 18, 19, ...]    # Legal actions for current meeting
)
```

---

## 📝 Tasks

| Task | Difficulty | Meetings | Fixed Events | Total Slots Needed | Key Challenge |
|---|---|---|---|---|---|
| `task_1_easy` | 🟢 Easy | 1 | 0 | 3 / 18 | Simple placement, wide window |
| `task_2_medium` | 🟡 Medium | 4 | 1 | 16 / 18 | Lunch avoidance, overlapping preferences, standup block |
| `task_3_hard` | 🔴 Hard | 6 | 2 | 29 / 18 | Impossible fit — forces priority-based skipping |

---

## 🏗️ Constraints

- Meeting durations must be **contiguous** 30-minute blocks
- Cannot schedule during **lunch blocks** (12:00–14:00, slots 6–9) if `avoid_lunch=True`
- Complete meetings within their `preferred_start_window` for bonus reward
- **Fixed events** cannot be moved or overlapped
- Placements overlapping with existing meetings are penalized heavily
- **Fragmented** scheduling (large gaps between meetings) receives efficiency penalties

---

## 🏆 Reward & Grading

### Step Rewards
| Event | Reward |
|---|---|
| Valid placement | `+10 × priority` |
| Preferred window matched | `+5` |
| Preferred window missed | `-5` |
| Lunch overlap (when avoid_lunch) | `-10` |
| Contiguous with existing meeting | `+2` |
| Gap penalty | `-0.5 × distance` |
| Skip meeting | `-10 × priority` |
| Conflict / out of bounds | `-30 × priority` |
| Reschedule | `-2` |

### Grader Score (0.0 → 1.0)
| Component | Weight |
|---|---|
| Scheduled meetings ratio | 0.30 |
| No-conflict ratio | 0.20 |
| Priority-weighted success | 0.20 |
| Constraint satisfaction | 0.20 |
| Efficiency (compactness + earliness) | 0.10 |

---

## 🚀 Running Locally

### Option 1: Direct Python (fastest)
```bash
# Install dependencies
pip install -r requirements.txt

# Run the standalone demo (no servers needed)
python demo_script.py

# Or start the API + Gradio servers
uvicorn api.app:app --host 0.0.0.0 --port 8000 &
python demo/app.py
```

### Option 2: Docker
```bash
docker build -t scheduling-env .
docker run -p 8000:8000 -p 7860:7860 scheduling-env
```

### Access Points
- **API Docs**: http://localhost:8000/docs
- **Gradio Demo**: http://localhost:7860

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tasks` | List all task configurations |
| `GET` | `/tasks/{task_id}` | Get a single task |
| `POST` | `/reset` | Start a new interactive session |
| `POST` | `/step` | Take an action in an active session |
| `POST` | `/grader` | Evaluate a final calendar for a task |
| `GET` | `/baseline` | Run the baseline agent on a task |

### Interactive API Usage Example
```bash
# Start a session
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_1_easy"}'

# Take a step (place meeting at slot 2 = 10:00)
curl -X POST http://localhost:8000/step \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<SESSION_ID>", "slot_index": 2}'
```

---

## ☁️ Deploying to Hugging Face Spaces

1. Create a new Space on [huggingface.co/spaces](https://huggingface.co/spaces) with **Docker** SDK
2. Push this repository to the Space
3. The `Dockerfile` and `run.sh` handle everything automatically
4. The Gradio UI will be available on port 7860

---

## 🧪 Running Tests

```bash
cd openenv_scheduler
python tests/qa.py
cat tests/qa_output.txt
```

---

## 📜 License

Built for the Meta PyTorch OpenEnv Hackathon.
