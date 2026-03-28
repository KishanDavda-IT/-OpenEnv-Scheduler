from core_env.models import TaskConfig, Meeting, ScheduledEvent

# Task 1 (Easy): 1 meeting, wide window, no fixed events
task1 = TaskConfig(
    task_id="task_1_easy",
    meetings_to_schedule=[
        Meeting(id="m1", duration_slots=3, preferred_start_window=list(range(15)), priority=1, avoid_lunch=False)
    ],
    fixed_events=[]
)

# Task 2 (Medium): 4 meetings, tight identical overlapping windows, fixed standup block
task2 = TaskConfig(
    task_id="task_2_medium",
    meetings_to_schedule=[
        Meeting(id="m1", duration_slots=4, preferred_start_window=[8], priority=2, avoid_lunch=True),
        Meeting(id="m2", duration_slots=4, preferred_start_window=[8], priority=2, avoid_lunch=True),
        Meeting(id="m3", duration_slots=4, preferred_start_window=[8], priority=1, avoid_lunch=True), 
        Meeting(id="m4", duration_slots=4, preferred_start_window=[8], priority=1, avoid_lunch=True)
    ],
    fixed_events=[
        ScheduledEvent(meeting_id="standup", start_slot=0, end_slot=1, is_fixed=True),  # 09:00-09:30
    ]
)

# Task 3 (Hard): 6 meetings requiring 29 slots (only 18 available), multiple fixed blocks
task3 = TaskConfig(
    task_id="task_3_hard",
    meetings_to_schedule=[
        Meeting(id="m1_urgent", duration_slots=6, preferred_start_window=[0], priority=3, avoid_lunch=True),
        Meeting(id="m2_urgent", duration_slots=5, preferred_start_window=[1, 2], priority=3, avoid_lunch=True),
        Meeting(id="m3_normal", duration_slots=4, preferred_start_window=[8], priority=2, avoid_lunch=True),
        Meeting(id="m4_normal", duration_slots=4, preferred_start_window=[9, 10], priority=2, avoid_lunch=True),
        Meeting(id="m5_low", duration_slots=5, preferred_start_window=[13], priority=1, avoid_lunch=False),
        Meeting(id="m6_low", duration_slots=5, preferred_start_window=[14, 15], priority=1, avoid_lunch=False)
    ],
    fixed_events=[
        ScheduledEvent(meeting_id="standup", start_slot=0, end_slot=1, is_fixed=True),        # 09:00-09:30
        ScheduledEvent(meeting_id="exec_sync", start_slot=16, end_slot=18, is_fixed=True),     # 17:00-18:00
    ]
)

TASKS = {
    "task_1_easy": task1,
    "task_2_medium": task2,
    "task_3_hard": task3
}
