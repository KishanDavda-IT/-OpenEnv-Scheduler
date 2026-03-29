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

## Hackathon alignment

| Requirement | How this repo satisfies it |
|-------------|----------------------------|
| **Clear scheduling tasks** | Three tasks in `core_env/tasks.py` + `openenv.yaml`: easy (wide window), medium (standup + lunch + overlapping preferences), hard (overbooked calendar → prioritize / skip). |
| **Grader / evaluation** | `core_env/grader.py` — deterministic `grader(task, calendar) → float` in **[0, 1]** (coverage, conflicts, priority, constraints, efficiency). **`POST /grader`** evaluates any full calendar for a task. |
| **Reward logic** | `SchedulingEnv.step()` — dense rewards for valid placement, preference match/miss, lunch violation, fragmentation; penalties for skip, invalid placement, reschedule. |
| **OpenEnv-style interface** | Typed **Pydantic** `Action` / `Observation` / `Reward`; **`reset()`**, **`step(action)`**, **`state()`** on `SchedulingEnv`; HTTP **`POST /reset`**, **`POST /step`**, **`GET /state`**; spec in **`openenv.yaml`**. Optional **`openenv-core`**: `pip install ".[openenv]"`. |
| **Working demo (Spaces)** | Gradio UI is mounted on the FastAPI app at **`/`**; Spaces runs **`start.py`** on port **7860**. **Live Space:** [OpenEnv-Scheduler on Hugging Face](https://huggingface.co/spaces/kishandavda/OpenEnv-Scheduler). |
| **Offline demo** | **`python demo_script.py`** — baseline agent on all three tasks; uses only `core_env` + `agent` (no network). |
| **Submission package** | Public **GitHub** repo, **`requirements.txt`**, **`demo_script.py`**, this **README**, deployed **Spaces URL** (link above). |

**Round 1 deadline:** 7 April 2026, 11:59 PM IST (latest push before deadline is evaluated).

---

## 📋 Project plan

The workday is **09:00–18:00** in **18** half-hour slots (indices **0 … 17**). Each slot covers **[09:00 + 30×i min, 09:00 + 30×(i+1) min)**. Events use **[`start_slot`, `end_slot`)** with **exclusive** `end_slot` (standard conflict test: `start < e.end_slot and end > e.start_slot`). **Place** action uses a **start slot** index; the meeting occupies **`duration_slots` contiguous slots**. **Special actions:** `18` = skip, `19` = reschedule last placement.

---

## Slot index → start time

| Slot | Start time | Slot | Start time |
|:---:|:---:|:---:|:---:|
| 0 | 09:00 | 9 | 13:30 |
| 1 | 09:30 | 10 | 14:00 |
| 2 | 10:00 | 11 | 14:30 |
| 3 | 10:30 | 12 | 15:00 |
| 4 | 11:00 | 13 | 15:30 |
| 5 | 11:30 | 14 | 16:00 |
| **6** | **12:00** (lunch) | 15 | 16:30 |
| **7** | **12:30** (lunch) | 16 | 17:00 |
| 8 | 13:00 | 17 | 17:30 |

---

## 📁 Folder structure

```
openenv_scheduler/
├── core_env/               # Environment (models, SchedulingEnv, grader, tasks)
├── agent/                  # Baseline agent
├── server/                 # FastAPI + Gradio mounted at /
│   └── app.py
├── demo/                   # Gradio Blocks definition imported by server
├── tests/                  # qa.py
├── demo_script.py          # Offline demo (no Docker / no API)
├── inference.py            # Validator-oriented episode loop
├── openenv.yaml            # Task and interface summary
├── requirements.txt
├── Dockerfile
├── start.py                # uvicorn server.app:app (port 7860)
└── README.md
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
| **FastAPI backend** | Programmatic API (`server/app.py`) + Gradio on the same port |
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
pip install -r requirements.txt
# Optional: pip install ".[openenv]"  # OpenEnv meta-package for extra tooling

python demo_script.py

# API + Gradio (same process; UI at /, OpenAPI at /docs)
uvicorn server.app:app --host 0.0.0.0 --port 7860
```

### Option 2: Docker
```bash
docker build -t scheduling-env .
docker run -p 7860:7860 scheduling-env
```

### Access points (local)
- **Gradio + API**: http://localhost:7860 — **API docs**: http://localhost:7860/docs

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/tasks` | List all task configurations |
| `GET` | `/tasks/{task_id}` | Get a single task |
| `POST` | `/reset` | Start a new interactive session |
| `POST` | `/step` | Take an action in an active session |
| `POST` | `/grader` | Body: `{"task_id": "...", "calendar": [ ScheduledEvent, ... ]}` → `final_score` in [0,1] |
| `GET` | `/baseline` | Run the baseline agent on a task |

### Interactive API usage
```bash
curl -s -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d "{\"task_id\": \"task_1_easy\"}"

# Place current meeting at slot 2 (10:00): action must be nested
curl -s -X POST http://localhost:7860/step -H "Content-Type: application/json" -d "{\"action\": {\"slot_index\": 2}}"
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
