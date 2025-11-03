# -*- coding: utf-8 -*-
import os
import re
from datetime import datetime
from typing import Dict, List

import pandas as pd
import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG & THEME
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DailyUp — Micro-coach",
    page_icon="🌅",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Modern “Metabolik”-inspired theme: neon gradients + glass cards + vertical flow
CUSTOM_CSS = """
/* Global reset & base */
:root{
  --bg: #0b0f19;
  --card: #0f172a;             /* slate-900 */
  --ink: #e6f1ff;              /* near white */
  --muted: #9fb3c8;
  --success: #59ffa0;
  --warn: #ffd166;
  --danger: #ff7b7b;
  --grad1: linear-gradient(135deg, #ff4ecd 0%, #7c4dff 50%, #00e7ff 100%);
  --grad2: linear-gradient(135deg, #22d3ee 0%, #a78bfa 50%, #fb7185 100%);
}

html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(1200px 800px at 80% -10%, rgba(124,77,255,.15), transparent 60%),
              radial-gradient(800px 600px at -10% 30%, rgba(0,231,255,.12), transparent 50%),
              var(--bg);
  color: var(--ink);
}

/* hide default menu/footer */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

h1, h2, h3 {letter-spacing: .2px;}
h1{font-weight: 800;}
h2{font-weight: 700; margin-top: 1.2rem;}
h3{font-weight: 700; margin-top: .7rem;}

.hero{
  margin: 10px 0 22px 0;
  padding: 18px 22px;
  border-radius: 18px;
  background: rgba(15,23,42,.55);
  box-shadow: 0 10px 40px rgba(0,0,0,.35), inset 0 0 0 1px rgba(255,255,255,.06);
  backdrop-filter: blur(8px);
}
.hero .badge{
  display:inline-flex; align-items:center; gap:8px;
  padding:6px 12px; border-radius:999px; font-size:.86rem; color:#081019;
  background: var(--grad1);
  box-shadow: 0 6px 20px rgba(124,77,255,.35);
}

.card{
  margin: 10px 0 18px 0;
  padding: 18px 18px;
  border-radius: 16px;
  background: rgba(14,20,37,.65);
  box-shadow: 0 8px 32px rgba(0,0,0,.35), inset 0 0 0 1px rgba(255,255,255,.06);
  backdrop-filter: blur(8px);
}

/* Inputs (textarea/radio) higher contrast */
textarea, .stTextArea textarea{
  background: #0b1224 !important;
  color: var(--ink) !important;
  border-radius: 14px !important;
  border: 1px solid rgba(255,255,255,.06) !important;
}
.stTextInput>div>div>input{
  background: #0b1224 !important; color: var(--ink) !important; border-radius: 12px !important;
  border: 1px solid rgba(255,255,255,.06) !important;
}

/* Radio → pill style (morning/midday/evening) */
div[role="radiogroup"] > label{
  display:inline-flex; align-items:center; gap:8px; margin:4px 8px 4px 0; cursor:pointer;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.08);
  color: var(--ink); border-radius: 999px; padding: 9px 14px;
}
div[role="radiogroup"] > label:hover{ background: rgba(255,255,255,.09); }

/* Primary CTA button */
.btn-primary button{k}
.btn-primary button{
  width: 100%;
  background: var(--grad1);
  color: #0a1020; font-weight: 800;
  box-shadow: 0 10px 28px rgba(124,77,255,.35);
  border-radius: 14px; border: none;
}
.btn-primary button:hover{
  transform: translateY(-1px);
  box-shadow: 0 14px 34px rgba(124,77,255,.45);
}

/* Secondary button (ghost gradient) */
.btn-ghost button{
  width: 100%;
  background: transparent;
  border: 1px solid rgba(255,255,255,.12);
  color: var(--ink);
  border-radius: 14px;
}
.btn-ghost button:hover{
  border-color: rgba(255,255,255,.25);
}

/* Section titles divider */
.section-title{
  height: 10px; border-radius: 999px;
  background: #0b1224; box-shadow: inset 0 0 0 1px rgba(255,255,255,.06);
  margin: 10px 0 6px 0;
}

/* Alerts */
.callout {
  padding: 12px 14px; border-radius: 12px; margin: 8px 0;
  border: 1px solid rgba(255,255,255,.08); color: var(--ink);
}
.callout.warn{ background: rgba(255, 209, 102, .12); }
.callout.ok{ background: rgba(89, 255, 160, .12); }
.callout.info{ background: rgba(34,211,238,.12); }

/* List styling for 3-step plan */
ul.plan{
  list-style: none; padding-left: 10px; margin: 8px 0 4px 0;
}
ul.plan li{
  padding: 8px 12px; margin: 6px 0; border-radius: 10px;
  background: rgba(255,255,255,.04);
  border: 1px solid rgba(255,255,255,.06);
}
"""

st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# UTILITAIRES
# ────────────────────────────────────────────────────────────────────────────────
def ai_is_available() -> bool:
    """Check if OpenAI key is set and SDK can be imported."""
    if not os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from openai import OpenAI  # noqa
        return True
    except Exception:
        return False


def _format_steps_list(items: List[str]) -> str:
    """Format a bullet list in HTML with our custom style."""
    lis = "".join([f"<li>{st.escape_markdown(i)}</li>" for i in items])
    return f'<ul class="plan">{lis}</ul>'


# ────────────────────────────────────────────────────────────────────────────────
# HEURISTIC FALLBACK COACH (no external model)
# ────────────────────────────────────────────────────────────────────────────────
def fallback_coach(note: str, slot: str) -> Dict:
    text = note.lower()

    # Simple domain cues
    if any(w in text for w in ["exam", "examen", "test", "quiz"]):
        analysis = "Exam context: reduce anxiety via short focus bursts + active recall."
        plan = [
            "Pick one weak topic now and write the exact sub-skill to review.",
            "Do a 25-minute Pomodoro: read + active recall (no notes).",
            "Create 5 flashcards and schedule a quick review."
        ]
        mantra = "Small wins compound"
    elif any(w in text for w in ["stress", "stressed", "anxious", "anxiété"]):
        analysis = "Stress context: lower cognitive load and move first."
        plan = [
            "Brain-dump worries in 2 minutes; pick one actionable item.",
            "Set a 10-minute timer and do only the first tiny step.",
            "Remove one distraction (phone away / site blocker)."
        ]
        mantra = "Begin before you think"
    elif any(w in text for w in ["workout", "train", "gym", "sport"]):
        analysis = "Fitness context: reduce activation energy and start moving."
        plan = [
            "Lay out gear and start a 5-minute warm-up.",
            "Do 2 sets of your easiest exercise to switch on.",
            "Log the session (date, sets, mood)."
        ]
        mantra = "Motion creates momentum"
    else:
        analysis = f"{slot.title()} mode: focus on small, clear wins."
        plan = [
            "Define the next 10-minute task.",
            "Prep one thing that reduces friction for later.",
            "Commit to just 5 minutes and start."
        ]
        mantra = "One small step beats zero"

    return {"analysis": analysis, "plan": plan, "mantra": mantra, "source": "fallback"}


# ────────────────────────────────────────────────────────────────────────────────
# OPENAI COACH (if key is set)
# ────────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are DailyUp, a tiny motivational coach.
Return a concise JSON with:
- analysis: 1-2 sentences tailored to the user's note & context (morning/midday/evening).
- plan: an array of 3 compact, concrete micro-steps (actionable today, 10-20 minutes each).
- mantra: a short 3-6 word mantra (no quotes).
Keep tone clear, energetic, and practical. Avoid generic fluff. No preamble, only JSON.
"""

def ai_coach(note: str, slot: str) -> Dict:
    from openai import OpenAI
    client = OpenAI()

    user_prompt = f"""
Context: {slot}.
User note: {note}

Respond strictly with JSON keys: analysis, plan, mantra.
Example:
{{
 "analysis": "You're facing exam stress, reduce activation cost.",
 "plan": ["Pick weak topic", "Pomodoro 25", "Create 5 flashcards"],
 "mantra": "Small wins compound"
}}
    """.strip()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        max_tokens=220,
    )

    content = resp.choices[0].message.content
    # Try to extract a JSON-like dict robustly
    try:
        import json
        # If the model added formatting, strip code fences etc.
        content = re.sub(r"^```json|```$", "", content.strip(), flags=re.MULTILINE)
        data = json.loads(content)
        analysis = str(data.get("analysis", "")).strip()
        plan = [str(x).strip() for x in (data.get("plan") or [])][:3]
        mantra = str(data.get("mantra", "")).strip()
        # Basic sanity fills
        if len(plan) < 3:
            plan += ["Commit to just 5 minutes"] * (3 - len(plan))
        if not analysis:
            analysis = f"{slot.title()} focus — keep it tiny, clear, and doable."
        if not mantra:
            mantra = "Small wins compound"
        return {"analysis": analysis, "plan": plan, "mantra": mantra, "source": "openai"}
    except Exception as e:
        return {"error": str(e)}


# ────────────────────────────────────────────────────────────────────────────────
# UI — HERO
# ────────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <div class="badge">⚡ Live coach</div>
  <h1 style="margin:10px 0 4px 0;">DailyUp</h1>
  <p style="color:var(--muted);max-width:740px;">
  Micro-nudges, massive progress. Tell me how you feel or your main goal.
  I’ll craft a 3-step micro-plan and a mantra to keep you moving.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 1 — CHOOSE MOMENT & SEE THE NUDGE
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title"></div>', unsafe_allow_html=True)
st.subheader("Step 1 — Pick your moment")

slot = st.radio(
    "When is this for?",
    options=["morning", "midday", "evening"],
    index=0,
    horizontal=True,
    help="This tunes the tone of the nudge.",
)

NUDGES = {
    "morning": "Morning Boost — one small step beats zero.",
    "midday": "Midday Check-in — reset with one tiny win.",
    "evening": "Evening Wrap-up — reflect and set a seed for tomorrow.",
}
st.caption(f"Prompt: {NUDGES[slot]}")

# ────────────────────────────────────────────────────────────────────────────────
# STEP 2 — USER NOTE
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title"></div>', unsafe_allow_html=True)
st.subheader("Step 2 — Tell me your note")

user_note = st.text_area(
    "What’s on your mind right now?",
    placeholder="e.g. I’m stressed about my exam next week and keep procrastinating.",
    height=120,
    label_visibility="visible",
)

# Optional helper to auto-fill with a seed example
with st.container():
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        if st.button("Paste an example"):
            st.session_state["user_note"] = "I’m stressed for my exam and can't focus."
        st.markdown("</div>", unsafe_allow_html=True)

        # If the example button pressed, hydrate the textarea
        if "user_note" in st.session_state and not user_note:
            user_note = st.session_state["user_note"]

    with col2:
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        st.button("Clear", on_click=lambda: st.session_state.pop("user_note", None))
        st.markdown("</div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 3 — ANALYZE & COACH
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="section-title"></div>', unsafe_allow_html=True)
st.subheader("Step 3 — Analyze & coach me")

col = st.container()
with col:
    st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
    go = st.button("💬 Analyze & coach me", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if go:
    if not user_note.strip():
        st.markdown('<div class="callout warn">⚠️ Please write a short note first.</div>', unsafe_allow_html=True)
    else:
        use_ai = ai_is_available()
        if not use_ai:
            st.markdown(
                '<div class="callout info">ℹ️ OpenAI key not found — using smart fallback.</div>',
                unsafe_allow_html=True,
            )

        with st.spinner("Thinking…"):
            result = ai_coach(user_note, slot) if use_ai else fallback_coach(user_note, slot)

        if isinstance(result, dict) and result.get("error"):
            # Safety net → try fallback if AI errored
            st.markdown(
                '<div class="callout warn">⚠️ AI error — switched to smart fallback.</div>',
                unsafe_allow_html=True,
            )
            result = fallback_coach(user_note, slot)

        # Render result
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.success("✅ Your personalized plan is ready!", icon="✅")
        st.markdown("### Analysis")
        st.write(result["analysis"])

        st.markdown("### 3-Step Plan")
        st.markdown(_format_steps_list(result["plan"]), unsafe_allow_html=True)

        st.markdown("### Mantra")
        st.write(result["mantra"])
        st.markdown(
            f"<small style='color:var(--muted)'>Source: {result.get('source','n/a')}</small>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # Optional debug
        with st.expander("Debug (optional)"):
            st.json(
                {
                    "slot": slot,
                    "note": user_note,
                    "timestamp": datetime.utcnow().isoformat(),
                    "engine": result.get("source", "n/a"),
                }
            )

# Bottom spacer
st.markdown("<br><br>", unsafe_allow_html=True)
