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
    version="1.2.0"
)

# ── Mount Gradio at /dashboard ───────────────────────────────────────
app = gr.mount_gradio_app(app, demo, path="/dashboard")

# ── Global singleton for OpenEnv Validator ───────────────────────────
# The validator usually expects a single episode lifecycle per reset.
_global_env: Optional[SchedulingEnv] = None

# Default task for validator if no task_id provided
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
    """
    OpenEnv standard reset endpoint.
    Returns: observation, reward, done.
    """
    global _global_env
    # We default to Medium task unless otherwise specified (via headers or env vars)
    _global_env = SchedulingEnv(DEFAULT_TASK_ID)
    obs = _global_env.reset()
    
    # Return STRICT OpenEnv schema (no extra fields in root)
    return {
        "observation": obs.dict(),
        "reward": 0.0,
        "done": False,
        "info": {} # Most validators accept info, but keep it minimal
    }

@app.post("/step")
def step_compliant(req: OpenEnvStepRequest):
    """
    OpenEnv standard step endpoint.
    Expects action as a dict.
    Returns: observation, reward, done.
    """
    global _global_env
    if _global_env is None:
        # Auto-reset if step is called first (some validators do this)
        _global_env = SchedulingEnv(DEFAULT_TASK_ID)
        _global_env.reset()
    
    # Extract action slot_index from the action dict
    # OpenEnv actions are typically {"action": value} or flat.
    # Our internal Action model expects slot_index.
    action_val = req.action.get("slot_index")
    if action_val is None:
        # Fallback if the action is just the primitive value
        action_val = req.action if isinstance(req.action, int) else 0
        
    action = Action(slot_index=action_val)
    obs, reward_obj, done, info = _global_env.step(action)
    
    # Return STRICT OpenEnv schema
    return {
        "observation": obs.dict(),
        "reward": float(reward_obj.value),
        "done": bool(done),
        "info": info
    }

@app.get("/state")
def get_state_compliant():
    """Returns current environment state."""
    global _global_env
    if _global_env is None:
        return {"error": "Environment not initialized. Call /reset first."}
    return {
        "calendar": [e.dict() for e in _global_env.calendar],
        "task_id": _global_env.task.task_id,
        "done": _global_env.is_done()
    }

# ── Metadata & Task endpoints ────────────────────────────────────────

@app.get("/tasks")
def get_tasks():
    return {k: v.dict() for k, v in TASKS.items()}

# ── Gradio integration ───────────────────────────────────────────────
# Keep these for the UI if needed, but the primary 7860 will handle OpenEnv.
