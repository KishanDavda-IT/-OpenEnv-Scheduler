#!/usr/bin/env python3
"""
OpenEnv Scheduler — Sample Demo Script

Run this standalone to see the baseline agent tackle all three tasks.
No Docker or API required.

Usage:
    python demo_script.py
"""
import sys
sys.path.insert(0, '.')

from core_env.scheduler import SchedulingEnv
from core_env.tasks import TASKS
from core_env.grader import grader
from core_env.models import Action
from agent.baseline import RuleBasedAgent

SLOT_TO_TIME = {i: f"{9 + (i * 30) // 60:02d}:{(i * 30) % 60:02d}" for i in range(19)}

def run_demo(task_id: str):
    print(f"\n{'='*60}")
    print(f"  TASK: {task_id}")
    print(f"{'='*60}")
    
    env = SchedulingEnv(task_id)
    agent = RuleBasedAgent()
    obs = env.reset()
    
    task = TASKS[task_id]
    print(f"  Meetings to schedule : {len(task.meetings_to_schedule)}")
    print(f"  Fixed events         : {len(task.fixed_events)}")
    total_slots = sum(m.duration_slots for m in task.meetings_to_schedule)
    print(f"  Total slots needed   : {total_slots} / 18 available")
    
    if task.fixed_events:
        print(f"\n  📌 Fixed Events:")
        for fe in task.fixed_events:
            print(f"     {fe.meeting_id}: {SLOT_TO_TIME[fe.start_slot]} – {SLOT_TO_TIME.get(fe.end_slot, '18:00')}")
    
    print(f"\n  --- Agent Actions ---")
    step = 0
    done = False
    total_reward = 0.0
    
    while not done:
        action = agent.select_action(obs)
        if action is None:
            break
        
        meeting_id = obs.current_meeting.id if obs.current_meeting else "?"
        step += 1
        
        obs, reward, done, info = env.step(action)
        total_reward += reward.value
        
        if action.slot_index == 18:
            action_str = "SKIP"
        elif action.slot_index == 19:
            action_str = "RESCHEDULE"
        else:
            action_str = f"Place @ {SLOT_TO_TIME[action.slot_index]}"
        
        status = "✅" if reward.value >= 10 else "⚠️" if reward.value >= 0 else "❌"
        print(f"  {status} Step {step}: {meeting_id:15s} -> {action_str:20s}  reward={reward.value:+.1f}  ({reward.reason})")
    
    print(f"\n  --- Final Calendar ---")
    for ev in env.calendar:
        tag = " (FIXED)" if ev.is_fixed else ""
        end_time = SLOT_TO_TIME.get(ev.end_slot, "18:00")
        print(f"     {ev.meeting_id:15s}  {SLOT_TO_TIME[ev.start_slot]} – {end_time}{tag}")
    
    final_score = info.get("final_score", grader(env.task, env.calendar))
    print(f"\n  Total Reward : {total_reward:+.1f}")
    print(f"  Final Score  : {final_score:.3f} ({final_score*100:.1f}%)")
    print(f"{'='*60}")
    
    return final_score


if __name__ == "__main__":
    print("\n🤖 OpenEnv Scheduler — Baseline Agent Demo")
    print("=" * 60)
    
    scores = {}
    for task_id in ["task_1_easy", "task_2_medium", "task_3_hard"]:
        scores[task_id] = run_demo(task_id)
    
    print(f"\n\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for tid, sc in scores.items():
        bar = "█" * int(sc * 30) + "░" * (30 - int(sc * 30))
        print(f"  {tid:20s}  [{bar}]  {sc*100:.1f}%")
    print(f"{'='*60}\n")
