from core_env.models import Action, Observation, Reward, ScheduledEvent, Meeting
from core_env.tasks import TASKS
from core_env.grader import grader
from typing import Tuple, Dict, Any, List

class SchedulingEnv:
    """
    OpenEnv-compliant Scheduling Environment.
    
    Methods:
        reset()  -> Observation : Reset the environment and return the initial observation.
        step(action) -> (Observation, Reward, bool, dict) : Take an action and return results.
        state()  -> Observation : Return the current observation without advancing.
    
    Action space:
        0-17  : Place meeting at slot (09:00 to 17:30 in 30-min increments)
        18    : SKIP the current meeting
        19    : RESCHEDULE — remove the last agent-placed meeting and re-queue it
    """

    def __init__(self, task_id: str):
        if task_id not in TASKS:
            raise ValueError(f"Unknown task {task_id}")
        self.task = TASKS[task_id]
        self.reset()
        
    def reset(self) -> Observation:
        # Load fixed events (immovable) into the calendar
        self.calendar: List[ScheduledEvent] = [
            ScheduledEvent(
                meeting_id=e.meeting_id,
                start_slot=e.start_slot,
                end_slot=e.end_slot,
                is_fixed=True
            )
            for e in self.task.fixed_events
        ]
        # Sort remaining meetings by priority (highest first)
        self.remaining_meetings = sorted(
            self.task.meetings_to_schedule.copy(),
            key=lambda x: x.priority, reverse=True
        )
        self.current_meeting = self.remaining_meetings.pop(0) if self.remaining_meetings else None
        self._last_placed_meeting = None  # Track last placement for reschedule
        
        return self.state()

    def is_done(self) -> bool:
        """True when all meetings have been processed (episode terminal)."""
        return self.current_meeting is None

    def state(self) -> Observation:
        if self.current_meeting is None:
            valid_slots = []
        else:
            valid_slots = self._get_valid_slots(self.current_meeting)
            
        return Observation(
            calendar=self.calendar,
            current_meeting=self.current_meeting,
            remaining_meetings=self.remaining_meetings,
            valid_slots=valid_slots
        )
        
    def _has_conflict(self, start: int, end: int, exclude_meeting_id: str = None) -> bool:
        for e in self.calendar:
            if exclude_meeting_id and e.meeting_id == exclude_meeting_id:
                continue
            if start < e.end_slot and end > e.start_slot:
                return True
        return False
        
    def _get_valid_slots(self, meeting: Meeting) -> list:
        valid = []
        for i in range(18 - meeting.duration_slots + 1):
            if not self._has_conflict(i, i + meeting.duration_slots):
                valid.append(i)
        valid.append(18)  # 18 is the SKIP action
        if self._last_placed_meeting is not None:
            valid.append(19)  # 19 is RESCHEDULE (only if there's something to undo)
        return valid

    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict[str, Any]]:
        if self.current_meeting is None:
            return self.state(), Reward(value=0.0, reason="Done"), True, {}

        slot = action.slot_index
        reward_value = 0.0
        reason = []
        
        # --- RESCHEDULE ACTION (19) ---
        if slot == 19:
            if self._last_placed_meeting is None:
                reward_value -= 5.0
                reason.append("Reschedule failed (nothing to undo)")
            else:
                # Remove the last placed event from the calendar
                removed_id = self._last_placed_meeting.id
                self.calendar = [
                    e for e in self.calendar
                    if not (e.meeting_id == removed_id and not e.is_fixed)
                ]
                # Re-queue the removed meeting at the front
                self.remaining_meetings.insert(0, self.current_meeting)
                self.current_meeting = self._last_placed_meeting
                self._last_placed_meeting = None
                reward_value -= 2.0  # Small penalty for indecision
                reason.append(f"Rescheduled: re-queued '{removed_id}'")
            
            return self.state(), Reward(value=reward_value, reason=", ".join(reason)), False, {}

        # --- SKIP ACTION (18) ---
        if slot == 18:
            reward_value -= (10.0 * self.current_meeting.priority)
            reason.append("Skipped meeting (heavy penalty)")
            self._last_placed_meeting = None
        else:
            # --- PLACE ACTION (0-17) ---
            end_slot = slot + self.current_meeting.duration_slots
            is_conflict = self._has_conflict(slot, end_slot)
            is_out_of_bounds = end_slot > 18

            if is_conflict or is_out_of_bounds:
                reward_value -= (30.0 * self.current_meeting.priority)
                reason.append("Invalid conflict/out of bounds")
                self._last_placed_meeting = None
            else:
                # Valid placement
                reward_value += (10.0 * self.current_meeting.priority)
                reason.append("Valid placement")
                
                # Preferences
                if self.current_meeting.preferred_start_window is not None:
                    if slot in self.current_meeting.preferred_start_window:
                        reward_value += 5.0
                        reason.append("Pref matched")
                    else:
                        reward_value -= 5.0
                        reason.append("Pref missed")
                        
                # Avoid Lunch (slots 6-7 = 12:00-13:00)
                if self.current_meeting.avoid_lunch:
                    if any(s in [6, 7] for s in range(slot, end_slot)):
                        reward_value -= 10.0
                        reason.append("Lunch overlap")
                
                # Efficiency / Compactness factor
                agent_events = [e for e in self.calendar if not e.is_fixed]
                if agent_events:
                    dist = min(abs(e.end_slot - slot) for e in agent_events)
                    if dist == 0:
                        reward_value += 2.0  # Bonus for contiguous booking
                    else:
                        reward_value -= (0.5 * dist)  # Penalty for scattered gaps

                # Save to calendar
                self.calendar.append(
                    ScheduledEvent(
                        meeting_id=self.current_meeting.id,
                        start_slot=slot,
                        end_slot=end_slot,
                        is_fixed=False
                    )
                )
                self._last_placed_meeting = self.current_meeting

        # Advance to next meeting
        if self.remaining_meetings:
            self.current_meeting = self.remaining_meetings.pop(0)
            done = False
        else:
            self.current_meeting = None
            done = True
            
        info = {}
        if done:
            info["final_score"] = grader(self.task, self.calendar)
            
        return self.state(), Reward(value=reward_value, reason=", ".join(reason)), done, info
