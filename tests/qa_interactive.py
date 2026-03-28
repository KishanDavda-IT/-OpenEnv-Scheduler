import sys
sys.path.append('.')

from core_env.scheduler import SchedulingEnv
from core_env.models import Action
from agent.baseline import RuleBasedAgent
from core_env.tasks import TASKS

print("=== 1. CALL RESET & PRINT STATE ===")
env = SchedulingEnv('task_2_medium')
obs = env.reset()
print(obs.model_dump_json(indent=2))
print()

print("=== 2 to 4. ACTION TESTS (Valid, Conflict, Out-of-Range) ===")
# 1. Valid Action. First meeting requires duration=2, preferred=[0,1,2,3]
valid_act = Action(slot_index=2)
env = SchedulingEnv('task_2_medium')
env.reset()
obs, r1, d1, i1 = env.step(valid_act)
print(f"Action: Valid Slot (2) -> Reward: {r1.value} ({r1.reason}) | Done: {d1} | Info: {i1}")

# 2. Conflicting Action. Meeting 2 needs 3 slots. If we place it at slot 2, it conflicts with meeting 1.
conflicting_act = Action(slot_index=2)
obs, r2, d2, i2 = env.step(conflicting_act)
print(f"Action: Conflicting Slot (2) -> Reward: {r2.value} ({r2.reason}) | Done: {d2} | Info: {i2}")

# 3. Out of Range Action. Meeting needs 3 slots, placed at 17 -> end = 20 > 18.
env = SchedulingEnv('task_2_medium')
env.reset()
out_act = Action(slot_index=17)
obs, r3, d3, i3 = env.step(out_act) # meeting 1
print(f"Action: Out-of-Range Slot (17) -> Reward: {r3.value} ({r3.reason}) | Done: {d3} | Info: {i3}")
print()

print("=== 5. DETERMINISM (SAME ACTION TWICE) ===")
env1 = SchedulingEnv('task_1_easy')
env1.reset()
_, rew_a, _, _ = env1.step(Action(slot_index=0))

env2 = SchedulingEnv('task_1_easy')
env2.reset()
_, rew_b, _, _ = env2.step(Action(slot_index=0))
print(f"Run A Reward: {rew_a.value}")
print(f"Run B Reward: {rew_b.value}")
print("Identical?", rew_a.value == rew_b.value)
print()

print("=== 6. BASELINE TEST SCORES ===")
agent = RuleBasedAgent()
for tid in TASKS:
    e = SchedulingEnv(tid)
    o = e.reset()
    while True:
        a = agent.select_action(o)
        if not a: break
        o, r, d, i = e.step(a)
        if d:
            print(f"Task '{tid}' Final Score: {i.get('final_score')}")
            break
print()

status = "PASS" if (r1.value > 0 and r2.value < 0 and r3.value < 0 and rew_a.value == rew_b.value) else "FAIL"
print(f"OVERALL QA STATUS: {status}")
