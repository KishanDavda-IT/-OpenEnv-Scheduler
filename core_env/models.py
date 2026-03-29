"""
Domain models for OpenEnv Scheduler.

Time discretization (unambiguous):
  - Workday 09:00–18:00 is 18 half-hour slots indexed 0..17.
  - Slot i covers wall time [09:00 + i*30min, 09:00 + (i+1)*30min).
  - Events use half-open intervals [start_slot, end_slot): end_slot is exclusive.
  - Valid start indices for a meeting of duration_slots D are 0 .. 17-D (inclusive).
  - Lunch (for avoid_lunch): slots 6 and 7 only (12:00–13:00). Overlap if any
    scheduled slot s with start <= s < end satisfies s in {6, 7}.
"""
from pydantic import BaseModel
from typing import List, Optional

class Action(BaseModel):
    """
    Agent action for the scheduling environment.
    
    slot_index values:
      0-17  : Schedule meeting starting at the given 30-min slot (09:00 to 17:30)
      18    : SKIP — reject the current meeting entirely
      19    : RESCHEDULE — remove last placed meeting and re-queue it
    """
    slot_index: int  # 0-17 = place, 18 = SKIP, 19 = RESCHEDULE

class Meeting(BaseModel):
    id: str
    duration_slots: int  
    preferred_start_window: Optional[List[int]] = None  
    priority: int = 1  
    avoid_lunch: bool = False  # Lunch is slots 6-7 (12:00 to 13:00)

class ScheduledEvent(BaseModel):
    meeting_id: str
    start_slot: int
    end_slot: int  # Exclusive
    is_fixed: bool = False  # If True, this event cannot be moved or removed

class Observation(BaseModel):
    calendar: List[ScheduledEvent]
    current_meeting: Optional[Meeting]
    remaining_meetings: List[Meeting]
    valid_slots: List[int]
    
class Reward(BaseModel):
    value: float
    reason: str

class TaskConfig(BaseModel):
    task_id: str
    meetings_to_schedule: List[Meeting]
    fixed_events: List[ScheduledEvent] = []  # Pre-existing immovable events
