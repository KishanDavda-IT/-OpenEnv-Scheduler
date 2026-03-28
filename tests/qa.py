import sys
import traceback
sys.path.append('.')

from core_env.scheduler import SchedulingEnv
from core_env.models import Action, Meeting, TaskConfig, ScheduledEvent
from core_env.tasks import TASKS
from core_env.grader import grader
from agent.baseline import RuleBasedAgent

report = []

def run_test(name, func):
    try:
        res, issues = func()
        status = "PASS" if res else "FAIL"
        report.append(f"### {name}: **{status}**")
        for i in issues:
            report.append(f"- {i}")
    except Exception as e:
        report.append(f"### {name}: **FAIL**")
        report.append(f"- Exception: {str(e)}")
        traceback.print_exc()

# 1. API Validation
def test_api():
    i = []
    env = SchedulingEnv('task_1_easy')
    obs = env.reset()
    if not hasattr(obs, 'calendar') or not hasattr(obs, 'valid_slots'):
        i.append("state() did not return valid Observation")
        return False, i
    obs, r, d, info = env.step(Action(slot_index=0))
    if not hasattr(r, 'value'):
        i.append("Reward missing value")
        return False, i
    return True, i

# 2. DETERMINISM TEST
def test_determinism():
    i = []
    scores = []
    rewards = []
    for _ in range(3):
        env = SchedulingEnv('task_1_easy')
        env.reset()
        _, r, _, _ = env.step(Action(slot_index=2))
        rewards.append(r.value)
    if len(set(rewards)) == 1:
        return True, i
    i.append(f"Varying rewards {rewards}")
    return False, i

# 3. CONFLICT DETECTION TEST
def test_conflict():
    i = []
    e1 = ScheduledEvent(meeting_id='m1', start_slot=2, end_slot=4)
    e2_valid = ScheduledEvent(meeting_id='m2', start_slot=4, end_slot=6)
    e3_invalid = ScheduledEvent(meeting_id='m3', start_slot=3, end_slot=5)
    e3_edge = ScheduledEvent(meeting_id='m4', start_slot=1, end_slot=3)
    
    t = TaskConfig(task_id='t', meetings_to_schedule=[
        Meeting(id='m1', duration_slots=2),
        Meeting(id='m2', duration_slots=2),
    ])
    s1 = grader(t, [e1, e2_valid])
    s2 = grader(t, [e1, e3_invalid])
    
    passed = True
    if s1 < 0.7:
        passed = False; i.append(f"Valid placement scored too low: {s1}")
    if s2 >= s1:
        passed = False; i.append(f"Conflicting scored >= valid: s1={s1}, s2={s2}")
    return passed, i

# 4. CONSTRAINT TEST
def test_constraint():
    i = []
    e_out = ScheduledEvent(meeting_id='m1', start_slot=17, end_slot=19)
    e_lunch = ScheduledEvent(meeting_id='m1', start_slot=6, end_slot=8)
    
    t = TaskConfig(task_id='t', meetings_to_schedule=[Meeting(id='m1', duration_slots=2, avoid_lunch=True, preferred_start_window=[0,1])])
    
    s_out = grader(t, [e_out])
    s_lunch = grader(t, [e_lunch])
    
    passed = True
    if s_out > 0.5:
        passed = False; i.append(f"Out of bound scored too high: {s_out}")
    if s_lunch >= 1.0:
        passed = False; i.append("Lunch override not penalized")
        
    return passed, i

# 5. TASK VALIDATION
def test_tasks():
    i = []
    if len(TASKS) != 3:
        return False, ["Missing 3 tasks"]
    t1, t2, t3 = TASKS['task_1_easy'], TASKS['task_2_medium'], TASKS['task_3_hard']
    if len(t1.meetings_to_schedule) >= len(t3.meetings_to_schedule):
        return False, ["Difficulty does not increase logically"]
    return True, i

# 6. GRADER TEST
def test_grader():
    i = []
    t = TASKS['task_1_easy']
    e_opt = ScheduledEvent(meeting_id='m1', start_slot=0, end_slot=3)
    s_opt = grader(t, [e_opt])
    
    if s_opt < 0.8:
        i.append(f"Optimal placement scored too low: opt={s_opt}")
        return False, i
    return True, i

# 7. REWARD FUNCTION
def test_reward():
    i = []
    env = SchedulingEnv('task_1_easy')
    env.reset()
    # Place at valid slot
    _, r1, _, _ = env.step(Action(slot_index=2))
    
    env2 = SchedulingEnv('task_1_easy')
    env2.reset()
    # Place at conflicting slot (inject a conflict first)
    env2.calendar.append(ScheduledEvent(meeting_id='x', start_slot=0, end_slot=4, is_fixed=False))
    _, r2, _, _ = env2.step(Action(slot_index=1))
    
    if r1.value <= 0 or r2.value >= 0:
        i.append(f"Rewards fail: valid={r1.value}, conflict={r2.value}")
        return False, i
    return True, i

# 8. ACTION SPACE TEST
def test_action_space():
    i = []
    env = SchedulingEnv('task_1_easy')
    env.reset()
    obs, r, d, info = env.step(Action(slot_index=99))
    if r.value >= 0:
        i.append("Out of range was not penalized")
        return False, i
    return True, i

# 9. BASELINE TEST
def test_baseline():
    i = []
    agent = RuleBasedAgent()
    for t_id in TASKS:
        env = SchedulingEnv(t_id)
        obs = env.reset()
        while True:
            act = agent.select_action(obs)
            if not act: break
            obs, r, d, info = env.step(act)
            if d:
                score = info.get('final_score', 0)
                if "hard" not in t_id and score < 0.4:
                    i.append(f"Baseline failed {t_id} with score {score}")
                    return False, i
                break
    return True, i

# 10. EDGE CASES
def test_edge():
    i = []
    passed = True
    t_zero = TaskConfig(task_id='e', meetings_to_schedule=[Meeting(id='m', duration_slots=0)])
    env = SchedulingEnv('task_1_easy')
    env.task = t_zero
    env.reset()
    obs, r, d, info = env.step(Action(slot_index=0)) 
    if not d: 
        passed = False; i.append("Zero duration failed to finish")
    if r.value < 0:
        passed = False; i.append("Zero duration penalized incorrectly")
        
    return passed, i

# 11. FIXED EVENTS TEST
def test_fixed_events():
    i = []
    # Medium task should have fixed events
    t2 = TASKS['task_2_medium']
    if len(t2.fixed_events) == 0:
        i.append("Medium task has no fixed events")
        return False, i
    
    # Hard task should have fixed events
    t3 = TASKS['task_3_hard']
    if len(t3.fixed_events) == 0:
        i.append("Hard task has no fixed events")
        return False, i
    
    # Fixed events should be loaded on reset
    env = SchedulingEnv('task_2_medium')
    obs = env.reset()
    fixed_in_cal = [e for e in obs.calendar if e.is_fixed]
    if len(fixed_in_cal) != len(t2.fixed_events):
        i.append(f"Expected {len(t2.fixed_events)} fixed events, got {len(fixed_in_cal)}")
        return False, i
    
    return True, i

# 12. RESCHEDULE ACTION TEST
def test_reschedule():
    i = []
    env = SchedulingEnv('task_1_easy')
    obs = env.reset()
    
    # Reschedule before placing anything should be invalid (19 not in valid_slots)
    if 19 in obs.valid_slots:
        i.append("Reschedule available before any placement")
        return False, i
    
    # Place a meeting, then check reschedule is available on next step
    # For task_1_easy there's only 1 meeting, so after placing it we're done
    # Use a multi-meeting task instead
    env2 = SchedulingEnv('task_2_medium')
    obs2 = env2.reset()
    
    # Place first meeting
    valid_non_skip = [s for s in obs2.valid_slots if s < 18]
    if not valid_non_skip:
        i.append("No valid slots for first meeting")
        return False, i
    
    obs2, r, d, info = env2.step(Action(slot_index=valid_non_skip[0]))
    
    # After successful placement, 19 should be available
    if not d and 19 not in obs2.valid_slots:
        i.append("Reschedule not available after valid placement")
        return False, i
    
    return True, i

# 13. SKIP ACTION TEST
def test_skip():
    i = []
    env = SchedulingEnv('task_1_easy')
    obs = env.reset()
    
    # 18 should always be in valid_slots
    if 18 not in obs.valid_slots:
        i.append("SKIP (18) not in valid_slots")
        return False, i
    
    obs, r, d, info = env.step(Action(slot_index=18))
    if r.value >= 0:
        i.append(f"Skip should be penalized, got reward {r.value}")
        return False, i
    
    return True, i

run_test("1. API VALIDATION", test_api)
run_test("2. DETERMINISM TEST", test_determinism)
run_test("3. CONFLICT DETECTION TEST", test_conflict)
run_test("4. CONSTRAINT TEST", test_constraint)
run_test("5. TASK VALIDATION", test_tasks)
run_test("6. GRADER TEST", test_grader)
run_test("7. REWARD FUNCTION TEST", test_reward)
run_test("8. ACTION SPACE TEST", test_action_space)
run_test("9. BASELINE TEST", test_baseline)
run_test("10. EDGE CASES", test_edge)
run_test("11. FIXED EVENTS TEST", test_fixed_events)
run_test("12. RESCHEDULE ACTION TEST", test_reschedule)
run_test("13. SKIP ACTION TEST", test_skip)

print("\n".join(report))
with open('tests/qa_output.txt', 'w', encoding='utf-8') as f:
    f.write("\n".join(report))
print(f"\n--- {sum(1 for r in report if 'PASS' in r)}/{sum(1 for r in report if '###' in r)} tests passed ---")
