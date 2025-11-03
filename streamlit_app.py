# streamlit_app.py
# DailyUp – micro-coach vertical avec IA (créativité 100%) + fallback
# UI en anglais (clair, vertical, explicite). Commentaires en français.

import os
import json
from typing import Dict, List
import streamlit as st
from openai import OpenAI

# ======================
#   STYLES & THEME
# ======================
PRIMARY_BG = "#0B1220"      # fond cartes/focus
PRIMARY_TX = "#E6F0FF"
ACCENT_1   = "#7C3AED"      # violet
ACCENT_2   = "#22D3EE"      # cyan
OK_BG      = "#ECFDF5"
OK_TX      = "#065F46"
WARN_BG    = "#EEF2FF"
WARN_TX    = "#3730A3"

CUSTOM_CSS = f"""
<style>
    .app-title {{
        font-weight: 800; 
        font-size: 2.2rem; 
        letter-spacing: .3px;
        margin-bottom: .125rem;
    }}
    .badge-live {{
        padding: .25rem .6rem; 
        border-radius: 999px; 
        font-size: .8rem; 
        background: linear-gradient(90deg, {ACCENT_1}, {ACCENT_2});
        color: white; 
        display: inline-block;
        margin-left: .5rem;
    }}
    .lead {{
        color: #6B7280; 
        margin-bottom: 1.25rem;
    }}
    .soft-card {{
        background: white;
        border-radius: 16px;
        border: 1px solid rgba(12, 25, 55, .08);
        padding: 18px 16px;
        box-shadow: 0 12px 24px rgba(15, 23, 42, .06);
        margin-bottom: 14px;
    }}
    .soft-input textarea {{
        background: {PRIMARY_BG};
        color: {PRIMARY_TX};
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,.07) !important;
    }}
    .soft-input .stTextInput>div>div>input {{
        background: {PRIMARY_BG};
        color: {PRIMARY_TX};
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,.07) !important;
    }}
    .pill {{
        height: 10px;
        border-radius: 999px;
        background: {PRIMARY_BG};
        box-shadow: 0 16px 40px rgba(12,18,32,.25);
        margin: 12px 0 18px 0;
    }}
    .btn-grad button {{
        background: linear-gradient(90deg, {ACCENT_1}, {ACCENT_2}) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        height: 46px;
        font-weight: 700;
    }}
    .note-ok {{
        background: {OK_BG};
        color: {OK_TX};
        padding: 12px 14px; 
        border-radius: 12px; 
        border:1px solid rgba(16,185,129,.25);
        font-weight: 600;
    }}
    .note-warn {{
        background: {WARN_BG};
        color: {WARN_TX};
        padding: 12px 14px; 
        border-radius: 12px; 
        border:1px solid rgba(55,48,163,.18);
        font-weight: 600;
    }}
    .section-title {{
        font-size: 1.15rem; 
        font-weight: 800; 
        margin-bottom: .25rem;
    }}
    .helper {{
        color: #8A94A7; 
        margin-bottom: .5rem;
        font-size: 0.92rem;
    }}
</style>
"""
st.set_page_config(page_title="DailyUp — micro coach", page_icon="🌞", layout="centered")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ======================
#   PROMPTS / MODELS
# ======================
SLOT_PROMPTS = {
    "morning":  "Morning Boost — one small step beats zero.",
    "midday":   "Midday Check-in — keep momentum with a tiny action.",
    "evening":  "Evening Wind-down — reflect, lighten, and set tomorrow’s first step.",
}

def fallback_plan(note: str, slot: str) -> Dict:
    """Plan de secours si l'API est indisponible : contextualisé (exam/stress)."""
    text = (note or "").lower()
    steps: List[str] = []
    analysis = "Focus on one small, concrete action."

    if any(k in text for k in ["exam", "exams", "test", "final", "revision", "révision"]):
        analysis = "Exam context: reduce anxiety with time-boxed, active recall."
        steps = [
            "Pick 1 weak topic now",
            "Pomodoro 25 minutes",
            "Create 3 flashcards + review",
        ]
        mantra = "Small wins compound"
    elif any(k in text for k in ["stress", "stressed", "anxious", "anxiety"]):
        analysis = "Stress context: down-regulate, then a tiny step."
        steps = [
            "Breathe 4-7-8 for 60s",
            "Define one 5-min task",
            "Do it for 5 minutes",
        ]
        mantra = "Begin before you think"
    else:
        steps = [
            "Define a 10-min tiny step",
            "Remove one distraction",
            "Start a 5-minute timer",
        ]
        mantra = "Action cures fear"

    if slot == "evening":
        steps[-1] = "Set a 5-min starter for tomorrow"
        mantra = "Leave it lighter"

    return {"analysis": analysis, "steps": steps[:3], "mantra": mantra, "from_ai": False}


def compose_coach_response(note: str, slot: str, tone: str) -> Dict:
    """
    Utilise GPT-4o-mini avec créativité = 1.0 (fixe) pour une réponse JSON.
    Fallback contextuel si erreur / API absente.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_plan(note, slot)

    try:
        client = OpenAI(api_key=api_key)

        system_msg = (
            "You are a behavioral micro-coach. Be concise, practical and contextual. "
            "If exams/revisions are mentioned, prefer Pomodoro, active recall, flashcards. "
            "If stress/anxiety appears, add a brief down-regulation then a tiny action. "
            "Return JSON ONLY with: analysis (<=1 short sentence), "
            "steps (exactly 3 imperatives, <=12 words each), mantra (3-6 words)."
        )
        user_msg = (
            f"Time of day: {slot}\n"
            f"Coach tone: {tone}\n"
            f"User note: {note}\n"
            "Return JSON with keys: analysis, steps, mantra."
        )

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=1.0,                 # créativité fixée à 100%
            max_tokens=300,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )
        content = resp.choices[0].message.content
        data = json.loads(content)

        data["steps"] = (data.get("steps") or [])[:3]
        while len(data["steps"]) < 3:
            data["steps"].append("Take one tiny step")

        data["analysis"] = (data.get("analysis") or "").strip()
        data["mantra"] = (data.get("mantra") or "Small wins compound").strip()
        data["from_ai"] = True
        return data

    except Exception as e:
        st.session_state["ai_error"] = str(e)
        return fallback_plan(note, slot)

# ======================
#   UI — VERTICAL
# ======================

# En-tête
col1, col2 = st.columns([1, .001])
with col1:
    st.markdown('<div class="app-title">DailyUp</div>', unsafe_allow_html=True)
    st.caption("Tiny nudges, big progress.")
with col2:
    st.markdown(f'<div class="badge-live">Live Coach</div>', unsafe_allow_html=True)

st.markdown(
    """
<div class="soft-card">
  <div style="font-weight:700;margin-bottom:.35rem;">How to use the app</div>
  <div class="helper">
  1) Pick your moment and tone. 2) Write one sentence about your goal or how you feel.  
  3) Tap “Analyze & coach me” → you’ll get a tailored 3-step micro-plan + a short mantra.  
  If the AI is unavailable, a smart local fallback is used.
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.markdown('<div class="pill"></div>', unsafe_allow_html=True)

# Step 1 — moment & tone
st.markdown('<div class="section-title">Step 1 — Choose your moment & tone</div>', unsafe_allow_html=True)
st.markdown('<div class="helper">This sets the prompt and the coach vibe.</div>', unsafe_allow_html=True)

slot = st.radio(
    "Moment",
    options=["morning", "midday", "evening"],
    index=0,
    horizontal=True,
    label_visibility="collapsed",
)

tone = st.selectbox(
    "Tone",
    options=["neutral", "supportive", "direct", "playful"],
    index=1,
    help="Pick the vibe you want from the coach.",
)

st.markdown(f"""
<div class="soft-card">
<strong>Prompt:</strong> {SLOT_PROMPTS.get(slot, '')}
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="pill"></div>', unsafe_allow_html=True)

# Step 2 — note utilisateur
st.markdown('<div class="section-title">Step 2 — Tell me what’s on your mind</div>', unsafe_allow_html=True)
st.markdown('<div class="helper">One sentence is enough: “I’m stressed for my exam”, “I need to finish my report”, etc.</div>', unsafe_allow_html=True)

note = st.text_area(
    label="Your note",
    value="",
    placeholder="Type how you feel or your main goal for today…",
    height=120,
    label_visibility="collapsed",
)
st.markdown('<div class="pill"></div>', unsafe_allow_html=True)

# Step 3 — analyse & plan (IA 100%)
st.markdown('<div class="section-title">Step 3 — Analyze & coach me</div>', unsafe_allow_html=True)
st.markdown('<div class="helper">AI will analyze your note and propose 3 micro-actions and a short mantra.</div>', unsafe_allow_html=True)

clicked = st.container()
with clicked:
    col = st.container()
    with col:
        c1, = st.columns(1)
        with c1:
            analyze = st.button("💬 Analyze & coach me", use_container_width=True, type="primary", key="analyze", help="Uses GPT-4o-mini when available.",)
            st.markdown('<div class="btn-grad"></div>', unsafe_allow_html=True)

if analyze:
    if not note.strip():
        st.warning("Please write a quick note in Step 2 first.")
    else:
        with st.spinner("Thinking..."):
            out = compose_coach_response(note=note.strip(), slot=slot, tone=tone)

        if out.get("from_ai"):
            st.markdown(f'<div class="note-ok">✅ Your personalized plan is ready (AI).</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="note-warn">⚠️ Network/API issue — using smart fallback.</div>', unsafe_allow_html=True)

        st.markdown("### Analysis")
        st.write(out["analysis"])

        st.markdown("### 3-Step Plan")
        for i, step in enumerate(out["steps"], 1):
            st.markdown(f"{i}. {step}")

        st.markdown("### Mantra")
        st.write(out["mantra"])

        # Optionnel : afficher l’erreur IA si présente (debug discret)
        if "ai_error" in st.session_state:
            with st.expander("Debug (AI error)"):
                st.code(st.session_state["ai_error"])
