from core_env.models import TaskConfig, ScheduledEvent
from typing import List

def grader(task: TaskConfig, final_calendar: List[ScheduledEvent]) -> float:
    """
    Deterministic grader returning a score between 0.0 and 1.0.
    
    Scoring breakdown:
        0.30 — Scheduled meetings ratio (how many meetings placed)
        0.20 — No-conflict ratio (penalizes overlapping events)
        0.20 — Priority-weighted success (higher-priority meetings matter more)
        0.20 — Constraint satisfaction (preferred windows + lunch avoidance)
        0.10 — Efficiency score (compactness + early placement)
    
    Additional penalties:
        -0.25 per missed high-priority meeting (priority >= 3)
        Score capped at 0.52 if total required duration exceeds 18 slots
    """
    if not task.meetings_to_schedule:
        return 1.0
    
    # Filter out fixed events — only grade agent-placed events
    agent_events = [e for e in final_calendar if not e.is_fixed]
    
    total_meetings = len(task.meetings_to_schedule)
    meetings_dict = {m.id: m for m in task.meetings_to_schedule}
    scheduled_ids = {e.meeting_id for e in agent_events}
    
    # Identify valid agent events (in-bounds and non-conflicting)
    valid_agent_events = []
    conflicts = 0
    
    # 1. Conflict and Bounds check
    all_events = final_calendar
    total_events = len(all_events)
    for i in range(total_events):
        e1 = all_events[i]
        is_invalid = False
        
        # Check bounds
        if e1.start_slot < 0 or e1.end_slot > 18 or e1.start_slot >= e1.end_slot:
            is_invalid = True
        else:
            # Check overlap with all other events
            for j in range(total_events):
                if i == j: continue
                e2 = all_events[j]
                if e1.start_slot < e2.end_slot and e1.end_slot > e2.start_slot:
                    is_invalid = True
                    break
        
        if is_invalid:
            conflicts += 1
        elif not e1.is_fixed:
            valid_agent_events.append(e1)
            
    # 2. Scheduled meetings ratio [0.3]
    scheduled_ids = {e.meeting_id for e in valid_agent_events}
    total_meetings = len(task.meetings_to_schedule)
    scheduled_ratio = len(scheduled_ids) / total_meetings if total_meetings > 0 else 1.0
    sched_score = scheduled_ratio * 0.3
    
    # 3. No conflict ratio [0.2]
    no_conflict_ratio = max(0.0, 1.0 - (conflicts / total_events)) if total_events > 0 else 1.0
    conflict_free_score = no_conflict_ratio * 0.2
    
    # 4. Priority weighted success [0.2]
    meetings_dict = {m.id: m for m in task.meetings_to_schedule}
    total_priority = sum(m.priority for m in task.meetings_to_schedule)
    scheduled_priority = sum(meetings_dict[m_id].priority for m_id in scheduled_ids if m_id in meetings_dict)
    priority_score = (scheduled_priority / total_priority) * 0.2 if total_priority > 0 else 0.2
    
    # 5. Constraint satisfaction [0.2]
    constraint_hits = 0
    pref_penalty = 0.0
    agent_count = len(valid_agent_events)
    total_constraints = agent_count * 2 if agent_count > 0 else 1
    for e in valid_agent_events:
        m = meetings_dict.get(e.meeting_id)
        if not m: continue
        
        # Preferred window check
        if m.preferred_start_window is None or e.start_slot in m.preferred_start_window:
            constraint_hits += 1
        else:
            pref_penalty += 0.015
            
        # Lunch avoidance check (slots 6-7 = 12:00-13:00)
        lunch_conflict = False
        if m.avoid_lunch:
            if any(s in [6, 7] for s in range(e.start_slot, e.end_slot)):
                lunch_conflict = True
        if not lunch_conflict:
            constraint_hits += 1
            
    preference_score = (constraint_hits / total_constraints) * 0.2 if agent_count > 0 else 0.0
    
    # 6. Efficiency Score [0.1]
    efficiency_score = 0.0
    if agent_count > 0:
        slots_used = sum((e.end_slot - e.start_slot) for e in valid_agent_events)
        min_start = min(e.start_slot for e in valid_agent_events)
        max_end = max(e.end_slot for e in valid_agent_events)
        span = max_end - min_start
        
        compactness = slots_used / span if span > 0 else 1.0
        avg_earliness = 1.0 - (sum(e.start_slot for e in valid_agent_events) / agent_count / 18.0)
        
        efficiency_score = (compactness * 0.05) + (avg_earliness * 0.05)

    score = sched_score + conflict_free_score + priority_score + preference_score + efficiency_score - pref_penalty
    
    # --- STRONG HIGH-PRIORITY PENALTY ---
    missed_criticals = sum(1 for m in task.meetings_to_schedule if m.priority >= 3 and m.id not in scheduled_ids)
    score -= (0.25 * missed_criticals)
    
    # --- HANDLE IMPOSSIBLE TASKS ---
    total_required_duration = sum(m.duration_slots for m in task.meetings_to_schedule)
    if total_required_duration > 18:
        score = min(score, 0.52)
        
    return round(max(0.0, score), 3)
        
    return round(max(0.0, score), 3)
