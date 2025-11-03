# =========================================================
# DAILYUP – SMART AI COACH APP (Streamlit + OpenAI)
# =========================================================
# ✅ Verticale
# ✅ Design moderne
# ✅ Texte explicatif clair
# ✅ Analyse IA (GPT-4o-mini) avec créativité ajustable
# ✅ Fallback intelligent si IA hors-ligne
# =========================================================

import streamlit as st
import re
import json
import random
import os
from datetime import datetime
from typing import Dict, List
import pandas as pd
from openai import OpenAI

# ---------- CONFIG STREAMLIT ----------
st.set_page_config(
    page_title="🌈 DailyUp — AI Coach",
    page_icon="🌈",
    layout="centered"
)

# ---------- STYLE ----------
st.markdown("""
<style>
    body, .main {
        background: linear-gradient(180deg, #0d1117, #141c2f);
        color: #f8f9fa;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3 { color: white; font-weight: 800; }
    .intro {
        background-color: #ffffff;
        color: #111827;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 5px 20px rgba(0,0,0,0.3);
    }
    .section {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        color: #f1f5f9;
    }
    .stButton > button {
        background: linear-gradient(90deg, #7c3aed, #22d3ee);
        border: none;
        color: white;
        font-weight: 700;
        border-radius: 10px;
        padding: 0.6rem 1rem;
        transition: 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        filter: brightness(1.1);
    }
    .success {
        color: #10b981;
        font-weight: bold;
    }
    .error {
        color: #ef4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


# ---------- INITIALISATION ----------
if "logs" not in st.session_state:
    st.session_state.logs = []


# ---------- CLIENT OPENAI ----------
def openai_client():
    key = os.getenv("OPENAI_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
    if not key:
        return None
    return OpenAI(api_key=key)


# ---------- HISTORIQUE ----------
def append_log(entry: Dict):
    st.session_state.logs.append(entry)


def get_last_plan() -> List[str]:
    """Récupère le dernier plan pour éviter les répétitions."""
    if not st.session_state.logs:
        return []
    last = st.session_state.logs[-1]
    plan = str(last.get("plan", ""))
    return [s.strip("-• ").strip() for s in plan.splitlines() if s.strip()]


# ---------- IA PRINCIPALE ----------
def ask_llm(user_text: str, slot: str, temperature: float = 0.5) -> Dict[str, str]:
    client = openai_client()
    if not client:
        raise RuntimeError("Aucune clé OpenAI trouvée.")

    last_steps = get_last_plan()

    system = (
        "You are DailyUp, a concise micro-coach. "
        "Be practical, grounded, positive and short. "
        "Avoid repeating previous steps."
    )

    prompt = f"""
Return STRICT JSON with keys: analysis, plan_steps (array of 3), mantra.
User note: {user_text}
Time: {slot}
Rules:
- analysis: 1–2 short sentences based on the note.
- plan_steps: exactly 3 tiny actionable steps, start with a verb, <= 12 words.
- Avoid repeating these previous steps: {last_steps}.
- mantra: 3–5 words, no quotes.
Respond ONLY with JSON.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=temperature,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ]
    )

    txt = res.choices[0].message.content.strip()
    match = re.search(r"\{.*\}", txt, re.S)
    if not match:
        return {
            "analysis": txt[:200],
            "plan_steps": [
                "Clarify one tiny goal",
                "Work 10 focused minutes",
                "Remove one distraction"
            ],
            "mantra": "Small wins compound"
        }

    try:
        data = json.loads(match.group(0))
        return {
            "analysis": data.get("analysis", ""),
            "plan_steps": data.get("plan_steps", []),
            "mantra": data.get("mantra", "Begin before you think")
        }
    except Exception:
        return {
            "analysis": txt[:200],
            "plan_steps": [
                "Define one small goal",
                "Set a 10-min timer",
                "Focus and start"
            ],
            "mantra": "Begin before you think"
        }


# ---------- FALLBACK ----------
def smart_fallback(user_text: str, slot: str) -> Dict[str, str]:
    words = re.findall(r"[a-zA-Z]{4,}", user_text.lower())
    topic = ", ".join(words[:2]) if words else "your task"
    openings = {
        "morning": ["Morning Boost", "Start Fresh"],
        "midday": ["Midday Focus", "Tiny Reset"],
        "evening": ["Evening Wrap", "Gentle Close"],
    }
    intro = random.choice(openings.get(slot, ["Small Step"]))
    steps = random.sample([
        f"Define a 10-min goal about {topic}",
        "Write one sentence",
        "Turn off notifications",
        "Prepare tomorrow’s small win",
        "Commit to just 5 minutes",
        "Breathe, then start small"
    ], k=3)
    mantras = ["Action cures doubt", "Small wins compound", "Momentum over mood"]
    return {
        "analysis": f"{intro}: focus on something small and clear.",
        "plan_steps": steps,
        "mantra": random.choice(mantras)
    }


# =========================================================
# 🚀 INTERFACE UTILISATEUR
# =========================================================

st.markdown("<h1>🌈 DailyUp — AI Coach</h1>", unsafe_allow_html=True)

st.markdown("""
<div class="intro">
<h3>How to use DailyUp</h3>
<p>🕓 1️⃣ Select your moment (morning, midday, evening).<br>
💭 2️⃣ Write what’s on your mind (your goal, blocker or feeling).<br>
⚙️ 3️⃣ Click <b>Analyze & coach me</b> to get a personalized plan from AI.<br>
🚀 4️⃣ Optionally start a focus timer and track your progress below.</p>
</div>
""", unsafe_allow_html=True)


# ---------- Étape 1 ----------
st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("Step 1 — Pick your moment")
slot = st.segmented_control("Time window", ["morning", "midday", "evening"], default="morning")
st.session_state.slot = slot
st.markdown('</div>', unsafe_allow_html=True)


# ---------- Étape 2 ----------
st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("Step 2 — Write what’s on your mind")
examples = {
    "morning": "Example: I want to start my report calmly.",
    "midday": "Example: I feel stuck; need to refocus.",
    "evening": "Example: I’d like to wrap the day peacefully."
}
user_text = st.text_area(
    "Your note:",
    placeholder=examples[slot],
    height=120
)
st.session_state.user_text = user_text
st.markdown('</div>', unsafe_allow_html=True)


# ---------- Étape 3 ----------
st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("Step 3 — Analyze & coach me")
st.caption("AI will analyze your note, propose 3 micro-actions and a short mantra.")

temp = st.slider("AI creativity", 0.0, 1.0, 0.5, 0.1,
                 help="Lower = focused, Higher = more varied")

if st.button("💬 Analyze & coach me", use_container_width=True):
    if not user_text.strip():
        st.warning("✏️ Please write something first.")
    else:
        with st.spinner("🤔 Thinking..."):
            try:
                output = ask_llm(user_text, slot, temperature=temp)
            except Exception:
                output = smart_fallback(user_text, slot)

        analysis = output["analysis"]
        steps = output["plan_steps"]
        mantra = output["mantra"]

        st.success("✅ Your personalized plan is ready!")
        st.write(f"**Analysis:** {analysis}")
        st.write("**3-Step Plan:**")
        for i, s in enumerate(steps, 1):
            st.write(f"{i}. {s}")
        st.caption(f"**Mantra:** _{mantra}_")

        append_log({
            "timestamp": datetime.utcnow().isoformat(),
            "slot": slot,
            "note": user_text,
            "analysis": analysis,
            "plan": "\n".join(steps),
            "mantra": mantra
        })
st.markdown('</div>', unsafe_allow_html=True)


# ---------- Étape 4 ----------
st.markdown('<div class="section">', unsafe_allow_html=True)
st.subheader("Step 4 — Progress log")
if st.session_state.logs:
    df = pd.DataFrame(st.session_state.logs)
    st.dataframe(df.tail(5)[["timestamp", "slot", "mantra"]],
                 hide_index=True, use_container_width=True)
else:
    st.caption("No entries yet. Write something above to start!")
st.markdown('</div>', unsafe_allow_html=True)


st.markdown("<br><center>💫 Built with ❤️ by DailyUp</center>", unsafe_allow_html=True)
