from core_env.models import Observation, Action
from typing import Optional

class RuleBasedAgent:
    def __init__(self):
        pass
        
    def select_action(self, obs: Observation) -> Optional[Action]:
        if obs.current_meeting is None:
            return None
            
        meeting = obs.current_meeting
        # Only consider actual placement slots (0-17) for the greedy evaluation
        placement_slots = [s for s in obs.valid_slots if s < 18]
        
        # If no valid placement slots exist, skip the meeting.
        # We avoid using action 19 (RESCHEDULE) in the baseline to prevent infinite loops.
        if not placement_slots:
            return Action(slot_index=18)
            
        best_slot = placement_slots[0]
        best_score = -float('inf')
        
        for slot in placement_slots:
            score = 0
            
            # 1. Obey preferences
            if meeting.preferred_start_window and slot in meeting.preferred_start_window:
                score += 5
                
            # 2. Avoid lunch constraint
            if meeting.avoid_lunch:
                if any(s in [6, 7] for s in range(slot, slot + meeting.duration_slots)):
                    score -= 5
            
            # 3. Efficiency / Compactness heuristics
            # Use only agent-placed events for compactness check
            agent_events = [e for e in obs.calendar if not e.is_fixed]
            if agent_events:
                dist = min(abs(e.end_slot - slot) for e in agent_events)
                if dist == 0:
                    score += 2
                else:
                    score -= (0.5 * dist)
                    
            # 4. Schedule as early as possible
            score -= (slot * 0.1)
            
            if score > best_score:
                best_score = score
                best_slot = slot
                
        return Action(slot_index=best_slot)
