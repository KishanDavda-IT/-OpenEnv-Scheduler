from fastapi import FastAPI, HTTPException
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
    version="1.2.2"
)

# ── Global singleton for OpenEnv Validator ───────────────────────────
_global_env: Optional[SchedulingEnv] = None
DEFAULT_TASK_ID = "task_2_medium"

# ── OpenEnv Compliant Endpoints ──────────────────────────────────────

class OpenEnvResetRequest(BaseModel):
    task_id: Optional[str] = "task_2_medium" # Use medium by default for validator
    seed: Optional[int] = None
    episode_id: Optional[str] = None

class OpenEnvStepRequest(BaseModel):
    action: Optional[Any] = None
    timeout_s: Optional[float] = None
    request_id: Optional[str] = None

@app.post("/reset")
def reset_env(request: Optional[OpenEnvResetRequest] = None):
    """
    OpenEnv reset endpoint. Accepts NO body or optional JSON body.
    Returns: session_id, task_id, and observation.
    """
    global _global_env
    # Handle CASE where body is completely NULL (None) or empty
    task_id = request.task_id if (request and hasattr(request, 'task_id') and request.task_id) else DEFAULT_TASK_ID
    
    _global_env = SchedulingEnv(task_id)
    obs = _global_env.reset()
    session_id = str(uuid.uuid4())
    
    return {
        "session_id": session_id,
        "task_id": task_id,
        "observation": obs.dict(),
        "reward": 0.0,
        "done": False
    }

@app.post("/step")
def step_env(request: Optional[OpenEnvStepRequest] = None):
    """
    OpenEnv step endpoint. Accepts NO body or optional JSON body.
    """
    global _global_env
    if _global_env is None:
        _global_env = SchedulingEnv(DEFAULT_TASK_ID)
        _global_env.reset()
    
    # Robust action extraction from optional body
    action_val = 18 # Default to SKIP if no action provided
    if request and request.action is not None:
        if isinstance(request.action, dict):
            action_val = request.action.get("slot_index", request.action.get("action", 18))
        else:
            action_val = request.action
        
    action = Action(slot_index=int(action_val))
    obs, reward_obj, done, info = _global_env.step(action)
    
    return {
        "observation": obs.dict(),
        "reward": float(reward_obj.value),
        "done": bool(done),
        "info": info
    }

@app.get("/state")
def get_state_env():
    global _global_env
    if _global_env is None:
        return {"error": "Env not initialized."}
    return {
        "calendar": [e.dict() for e in _global_env.calendar],
        "task_id": _global_env.task.task_id,
        "done": _global_env.is_done()
    }

@app.get("/tasks")
def get_tasks_list():
    return {k: v.dict() for k, v in TASKS.items()}

@app.get("/tasks/{task_id}")
def get_task_config(task_id: str):
    if task_id not in TASKS:
        raise HTTPException(status_code=404, detail="Task not found")
    return TASKS[task_id].dict()

@app.get("/baseline")
def run_baseline_agent(task_id: str):
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

def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 7860)))

if __name__ == "__main__":
    main()
