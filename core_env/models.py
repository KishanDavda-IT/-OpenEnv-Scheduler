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
    avoid_lunch: bool = False  # Lunch is slots 6-9 (12:00 to 14:00)

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
