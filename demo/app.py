import gradio as gr
import os
import sys

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core_env.tasks import TASKS
from core_env.scheduler import SchedulingEnv
from core_env.grader import grader
from core_env.models import Action
from agent.baseline import RuleBasedAgent

SLOT_TO_TIME = {i: f"{9 + (i * 30) // 60:02d}:{(i * 30) % 60:02d}" for i in range(19)}

def get_task_info(task_id):
    """Get task config directly from TASKS dict."""
    if task_id in TASKS:
        return TASKS[task_id].dict()
    return {}

def run_agent(task_id):
    try:
        task_info = get_task_info(task_id)
        meetings = task_info.get("meetings_to_schedule", [])
        fixed_events = task_info.get("fixed_events", [])
        total_meetings = len(meetings)

        # Difficulty Context
        if "easy" in task_id:
            diff_label = "🟢 **EASY:** Straightforward scheduling with wide optimization availability."
            expected = "90–100%"
        elif "medium" in task_id:
            diff_label = "🟡 **MEDIUM:** Unavoidable trade-offs, preference conflicts, constraints."
            expected = "70–85%"
        else:
            diff_label = "🔴 **HARD:** Mathematically impossible scenario forcing critical prioritization skips."
            expected = "40–60%"

        # Run baseline agent directly (no HTTP call)
        env = SchedulingEnv(task_id)
        agent = RuleBasedAgent()
        obs = env.reset()
        done = False
        history = []
        while not done:
            action = agent.select_action(obs)
            if not action:
                break
            next_obs, reward, done, info = env.step(action)
            history.append({
                "action": action.dict(),
                "reward": reward.dict(),
                "meeting": obs.current_meeting.dict() if obs.current_meeting else None
            })
            obs = next_obs

        calendar = [e.dict() for e in env.calendar]
        score = info.get("final_score", grader(env.task, env.calendar))

        # Format calendar as List of Lists for gr.Dataframe
        cal_data = []
        sch_ids = set()
        for ev in calendar:
            start_m = ev["start_slot"] * 30
            end_m = ev["end_slot"] * 30
            s_time = f"{9 + start_m // 60:02d}:{start_m % 60:02d}"
            e_time = f"{9 + end_m // 60:02d}:{end_m % 60:02d}"
            is_fixed = ev.get("is_fixed", False)

            if not is_fixed:
                sch_ids.add(ev["meeting_id"])

            icon = "📌" if is_fixed else "🤝"
            tag = " (Fixed)" if is_fixed else ""
            cal_data.append([
                f"{icon} {ev['meeting_id']}{tag}",
                s_time,
                e_time,
                f"{(ev['end_slot'] - ev['start_slot']) * 30} mins"
            ])

        # Format explanation
        exp_str = ""
        total_high = 0
        scheduled_high = 0
        missed_prefs = 0
        missed_lunch = 0

        for m in meetings:
            is_high = m.get("priority", 1) >= 3
            if is_high:
                total_high += 1
            if m["id"] in sch_ids and is_high:
                scheduled_high += 1

        for i, h in enumerate(history):
            if h.get('meeting'):
                m_id = h['meeting']['id']
                slot = h['action']['slot_index']
                val = h['reward']['value']
                reason = h['reward']['reason']

                bullet_pts = ""
                if "Valid placement" in reason: bullet_pts += "✔ Valid schedule mapping<br>"
                if "Pref matched" in reason: bullet_pts += "✔ Scheduled inside preferred window<br>"
                if "Pref missed" in reason:
                    bullet_pts += "✖ Preference window violated<br>"
                    missed_prefs += 1
                if "Lunch overlap" in reason:
                    bullet_pts += "✖ Lunch hour constraint violated<br>"
                    missed_lunch += 1
                if "Invalid conflict" in reason: bullet_pts += "🚫 CRITICAL: Conflicting overlap penalty<br>"
                if "Skipped" in reason: bullet_pts += "⚠️ Explicitly skipped task<br>"
                if "Rescheduled" in reason: bullet_pts += "🔄 Rescheduled previous placement<br>"

                if val >= 10:
                    color = "#10b981"
                    emoji = "✅"
                elif val >= 0:
                    color = "#f59e0b"
                    emoji = "⚠️"
                else:
                    color = "#ef4444"
                    emoji = "❌"

                if slot == 19:
                    target = "RESCHEDULE"
                elif slot == 18:
                    target = "SKIPPED"
                else:
                    target = f"Slot {slot} ({SLOT_TO_TIME.get(slot, '?')})"

                exp_str += f"""
<div style='border-left: 4px solid {color}; padding-left: 10px; margin-bottom: 15px; background: rgba(0,0,0,0.02); padding: 10px; border-radius: 4px;'>
    <b style='color: {color};'>{emoji} Step {i+1}: Action on `{m_id}` -> {target}</b><br>
    <div style='margin-top: 5px; font-size: 0.9em; line-height: 1.5;'>
        {bullet_pts}
        <b>Net Reward: {val}</b>
    </div>
</div>
"""

        if not exp_str:
            exp_str = "No actions taken."

        # Score Context
        score_color = "#10b981" if score >= 0.8 else "#f59e0b" if score > 0.4 else "#ef4444"
        score_md = f"""
<div style='border: 1px solid #ddd; padding: 15px; border-radius: 8px; text-align: center;'>
    <h2 style='color: {score_color}; font-size: 3rem; margin: 0;'>{score * 100:.1f}%</h2>
    <p style='font-weight: bold; margin: 0;'>Task Success Score</p>
    <p style='margin: 5px 0 0 0; font-size: 0.9em; color: gray;'>Expected Score Range: {expected}</p>
</div>
"""

        # Why score is not higher
        missed_m = total_meetings - len(sch_ids)
        issues_md = f"### 📉 Grading Audit (Why score isn't 100%)\n"
        if score == 1.0:
            issues_md += "Perfect scheduling! No penalties detected."
        else:
            if missed_m > 0: issues_md += f"- **Missed Meetings**: Agent skipped {missed_m} meetings.\n"
            if total_high > scheduled_high: issues_md += f"- **Critical High-Priority Miss**: Failed to schedule {total_high - scheduled_high} priority-3 tasks! (Heavy Penalty)\n"
            if missed_prefs > 0: issues_md += f"- **Preference Violations**: Forced {missed_prefs} meetings outside their requested time window.\n"
            if missed_lunch > 0: issues_md += f"- **Constraint Violations**: Disregarded 'avoid lunch' constraint {missed_lunch} times.\n"
            if fixed_events: issues_md += f"- **Fixed Events**: {len(fixed_events)} immovable event(s) reduced available capacity.\n"

        # Summary Panel
        if not calendar:
            efficiency = "N/A"
        else:
            agent_cal = [ev for ev in calendar if not ev.get("is_fixed", False)]
            if agent_cal:
                slots_used = sum(ev["end_slot"] - ev["start_slot"] for ev in agent_cal)
                span = max(ev["end_slot"] for ev in agent_cal) - min(ev["start_slot"] for ev in agent_cal)
                compact = slots_used / span if span > 0 else 1.0
                efficiency = "High 🟢" if compact >= 0.8 else "Medium 🟡" if compact >= 0.5 else "Low 🔴"
            else:
                efficiency = "N/A"

        conflicts_avoided = "Yes ✅" if "Invalid conflict" not in "".join(h['reward']['reason'] for h in history) else "No ❌"

        # Highlight constraints
        rules_md = "### 📜 Active Constraints Overview\n"
        lunch_avoiders = sum(1 for m in meetings if m.get("avoid_lunch"))
        if lunch_avoiders > 0:
            rules_md += f"- 🛑 **Lunch Avoidance**: {lunch_avoiders} meetings strictly avoid 12:00-14:00.\n"
        if fixed_events:
            rules_md += f"- 📌 **Fixed Events**: {len(fixed_events)} immovable event(s) block calendar slots.\n"
        if sum(m.get('duration_slots', 0) for m in meetings) > 18:
            rules_md += f"- ⚠️ **Capacity Overflow**: Required timeline exceeds 9-hour workday!\n"

        summary_md = f"""
{rules_md}
### 📊 Final Summary Analytics
- **Total Meetings Scheduled**: {len(sch_ids)} / {total_meetings}
- **High-Priority Completed**: {scheduled_high} / {total_high}
- **Conflicts Avoided**: {conflicts_avoided}
- **Schedule Efficiency**: {efficiency}
- **Fixed Events on Calendar**: {len(fixed_events)}
"""

        info_out = f"{diff_label}"

        return cal_data if cal_data else [], exp_str, score_md, info_out, summary_md, issues_md

    except Exception as e:
        import traceback
        traceback.print_exc()
        err_box = f"<div style='border: 1px solid red; padding: 20px; border-radius: 8px;'><h2 style='color:red;text-align:center;'>Error</h2><p>{str(e)}</p></div>"
        return [], "", err_box, "", "", ""

with gr.Blocks(theme=gr.themes.Soft(primary_hue="blue", neutral_hue="slate")) as demo:
    gr.HTML("<h1 style='text-align: center; margin-bottom: 0;'>🤖 OpenEnv Scheduling AI</h1>")
    gr.HTML("<p style='text-align: center; color: gray; margin-top: 0;'>Reinforcement Learning Environment for Calendar Optimization</p>")
    gr.Markdown("✔ **System Status: API Server Online**")

    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 🎛️ Control Panel")
            task_dropdown = gr.Dropdown(choices=["task_1_easy", "task_2_medium", "task_3_hard"], label="Select Mission", value="task_1_easy", interactive=True)
            task_info_md = gr.Markdown("🟢 **EASY:** Straightforward scheduling with wide optimization availability.")
            btn = gr.Button("🚀 Run RL Baseline Agent", variant="primary")

            gr.HTML("<hr style='margin-top: 20px; margin-bottom: 20px;'>")
            score_out = gr.HTML("<div style='border: 1px solid #ddd; padding: 15px; border-radius: 8px; text-align: center;'><h2 style='color: gray; font-size: 2.5rem; margin: 0;'>-</h2><p style='margin: 0;'>Task Success Score</p></div>")

            with gr.Accordion("📋 Analytics Dashboard", open=True):
                summary_out = gr.Markdown("Run an agent to populate summary metrics.")
                issues_out = gr.Markdown("")

        with gr.Column(scale=2):
            gr.Markdown("### 📅 Final Calendar Schedule")
            calendar_out = gr.Dataframe(headers=["Meeting ID", "Start Time", "End Time", "Duration"], interactive=False)

            with gr.Accordion("🔍 View Agent Decision Process", open=True):
                explain_out = gr.HTML("<div style='color: gray; padding: 10px;'>Click 'Run' to see the agent's step-by-step reasoning.</div>")

    btn.click(fn=run_agent, inputs=[task_dropdown], outputs=[calendar_out, explain_out, score_out, task_info_md, summary_out, issues_out])
    task_dropdown.change(fn=lambda tid: "🟢 **EASY:** Straightforward scheduling with wide optimization availability." if "easy" in tid else "🟡 **MEDIUM:** Unavoidable trade-offs, preference conflicts, constraints." if "medium" in tid else "🔴 **HARD:** Mathematically impossible scenario forcing critical prioritization skips.", inputs=[task_dropdown], outputs=[task_info_md])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
