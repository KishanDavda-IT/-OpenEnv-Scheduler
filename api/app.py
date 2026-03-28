from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import sys
import os
import gradio as gr

# Ensure the project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_env.tasks import TASKS
from core_env.scheduler import SchedulingEnv
from core_env.grader import grader
from core_env.models import ScheduledEvent, Action
from demo.app import demo

app = FastAPI(
    title="OpenEnv Scheduling API",
    description="Compliant OpenEnv environment for the Meta PyTorch Hackathon.",
    version="1.2.1"
)

# ── Global singleton for OpenEnv Validator ───────────────────────────
_global_env: Optional[SchedulingEnv] = None
DEFAULT_TASK_ID = "task_2_medium"

# ── OpenEnv Compliant Endpoints ──────────────────────────────────────

class OpenEnvResetRequest(BaseModel):
    seed: Optional[int] = None
    episode_id: Optional[str] = None

class OpenEnvStepRequest(BaseModel):
    action: Dict[str, Any]
    timeout_s: Optional[float] = None
    request_id: Optional[str] = None

@app.post("/reset")
def reset_compliant(req: Optional[OpenEnvResetRequest] = Body(None)):
    global _global_env
    _global_env = SchedulingEnv(DEFAULT_TASK_ID)
    obs = _global_env.reset()
    return {
        "observation": obs.dict(),
        "reward": 0.0,
        "done": False,
        "info": {}
    }

@app.post("/step")
def step_compliant(req: OpenEnvStepRequest):
    global _global_env
    if _global_env is None:
        _global_env = SchedulingEnv(DEFAULT_TASK_ID)
        _global_env.reset()
    
    action_val = req.action.get("slot_index")
    if action_val is None:
        action_val = req.action if isinstance(req.action, int) else 0
        
    action = Action(slot_index=action_val)
    obs, reward_obj, done, info = _global_env.step(action)
    
    return {
        "observation": obs.dict(),
        "reward": float(reward_obj.value),
        "done": bool(done),
        "info": info
    }

@app.get("/state")
def get_state_compliant():
    global _global_env
    if _global_env is None:
        return {"error": "Environment not initialized."}
    return {
        "calendar": [e.dict() for e in _global_env.calendar],
        "task_id": _global_env.task.task_id,
        "done": _global_env.is_done()
    }

@app.get("/tasks")
def get_tasks():
    return {k: v.dict() for k, v in TASKS.items()}

@app.get("/tasks/{task_id}")
def get_single_task(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id].dict()

@app.get("/baseline")
def run_baseline(task_id: str):
    from agent.baseline import RuleBasedAgent
    env = SchedulingEnv(task_id)
    agent = RuleBasedAgent()
    obs = env.reset()
    done = False
    history = []
    while not done:
        action = agent.select_action(obs)
        if not action: break
        next_obs, reward, done, info = env.step(action)
        history.append({
            "action": action.dict(),
            "reward": reward.dict(),
            "meeting": obs.current_meeting.dict() if obs.current_meeting else None
        })
        obs = next_obs
    return {
        "calendar": [e.dict() for e in env.calendar],
        "history": history,
        "final_info": info if done else {"final_score": grader(env.task, env.calendar)}
    }

# ── Mount Gradio at root (/) ──────────────────────────────────────────
# IMPORTANT: All FastAPI routes must be defined BEFORE this mount.
app = gr.mount_gradio_app(app, demo, path="/")
