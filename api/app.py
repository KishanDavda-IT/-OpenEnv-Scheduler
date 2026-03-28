from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import sys
import os

# Ensure the project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_env.tasks import TASKS
from core_env.scheduler import SchedulingEnv
from core_env.grader import grader
from core_env.models import ScheduledEvent, Action
from agent.baseline import RuleBasedAgent

app = FastAPI(
    title="OpenEnv Scheduling API",
    description="A deterministic scheduling environment API for training and evaluating AI agents.",
    version="1.0.0"
)

# In-memory session store for interactive play
_sessions: Dict[str, SchedulingEnv] = {}

class StepRequest(BaseModel):
    session_id: str
    slot_index: int

class ResetRequest(BaseModel):
    task_id: str

class GraderRequest(BaseModel):
    task_id: str
    calendar: List[Dict[str, Any]]

# ── Read-only endpoints ──────────────────────────────────────────────

@app.get("/tasks")
def get_tasks():
    """List all available task configurations."""
    return {k: v.dict() for k, v in TASKS.items()}

@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get a single task configuration by ID."""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id].dict()

# ── Interactive environment endpoints ────────────────────────────────

@app.post("/reset")
def reset_env(req: ResetRequest):
    """
    Create a new environment session for a task.
    Returns a session_id and the initial observation.
    """
    if req.task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    
    session_id = str(uuid.uuid4())
    env = SchedulingEnv(req.task_id)
    obs = env.reset()
    _sessions[session_id] = env
    
    return {
        "session_id": session_id,
        "observation": obs.dict()
    }

@app.post("/step")
def step_env(req: StepRequest):
    """
    Take a step in an existing session.
    Accepts a session_id and a slot_index (0-17=place, 18=skip, 19=reschedule).
    """
    env = _sessions.get(req.session_id)
    if env is None:
        raise HTTPException(status_code=404, detail="Session not found. Call /reset first.")
    
    action = Action(slot_index=req.slot_index)
    obs, reward, done, info = env.step(action)
    
    if done:
        # Clean up session after episode ends
        del _sessions[req.session_id]
    
    return {
        "observation": obs.dict(),
        "reward": reward.dict(),
        "done": done,
        "info": info
    }

# ── Grader endpoint ──────────────────────────────────────────────────

@app.post("/grader")
def run_grader(req: GraderRequest):
    """Evaluate a final calendar for a given task. Returns score 0.0-1.0."""
    if req.task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
        
    events = [ScheduledEvent(**e) for e in req.calendar]
    score = grader(TASKS[req.task_id], events)
    return {"score": score}

# ── Baseline endpoint ────────────────────────────────────────────────

@app.get("/baseline")
def run_baseline(task_id: str):
    """Run the rule-based baseline agent on a task and return the full trace."""
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
        
    env = SchedulingEnv(task_id)
    agent = RuleBasedAgent()
    
    obs = env.reset()
    done = False
    total_reward = 0.0
    history = []
    
    while not done:
        action = agent.select_action(obs)
        if action is None:
            break
            
        next_obs, reward, done, info = env.step(action)
        history.append({
            "action": action.dict(),
            "reward": reward.dict(),
            "meeting": obs.current_meeting.dict() if obs.current_meeting else None
        })
        total_reward += reward.value
        obs = next_obs
        
    return {
        "calendar": [e.dict() for e in env.calendar],
        "history": history,
        "total_reward": total_reward,
        "final_info": info if done else {"final_score": grader(env.task, env.calendar)}
    }
