import os
import sys
import json
from core_env.scheduler import SchedulingEnv
from agent.baseline import RuleBasedAgent

def run_inference(task_id: str = "task_2_medium"):
    """
    Standard entrypoint for the OpenEnv validator.
    Runs a single transition or a full episode.
    """
    print(f"🚀 Initializing OpenEnv Inference for Task: {task_id}")
    env = SchedulingEnv(task_id)
    agent = RuleBasedAgent()
    
    obs = env.reset()
    done = False
    step_count = 0
    total_reward = 0.0
    
    while not done and step_count < 20: # Safety break
        # Select action
        action = agent.select_action(obs)
        if action is None:
            break
            
        # Execute action
        next_obs, reward, done, info = env.step(action)
        total_reward += reward.value
        obs = next_obs
        step_count += 1
        
        print(f"Step {step_count}: Action {action.slot_index} | Reward {reward.value}")
        
    print(f"✅ Inference Complete. Total Steps: {step_count} | Total Reward: {total_reward}")
    return {
        "steps": step_count,
        "reward": total_reward,
        "done": done
    }

if __name__ == "__main__":
    # If run as a script, execute a sample task
    run_inference()
