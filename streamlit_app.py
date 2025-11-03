# -*- coding: utf-8 -*-
import os
import re
import html
from datetime import datetime
from typing import Dict, List

import streamlit as st

# ────────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ────────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DailyUp — Micro-Coach",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ────────────────────────────────────────────────────────────────────────────────
# THEME LIGHT/DARK — on garde la même interface, on fixe juste les contrastes
# ────────────────────────────────────────────────────────────────────────────────
base_theme = st.get_option("theme.base") or "light"
st.markdown(
    f'<script>document.documentElement.setAttribute("data-theme","{base_theme}");</script>',
    unsafe_allow_html=True,
)

CSS = """
/* Variables pour les deux modes */
:root {
  --ink: #0f172a;
  --muted: #4b5563;
  --bg: #f5f7ff;
  --card: #ffffff;
  --border: #e6e8f2;
  --ink-contrast: #0b1020;

  --primaryGrad: linear-gradient(135deg,#7c3aed 0%, #ec4899 55%, #06b6d4 100%);
  --shadow: 0 14px 30px rgba(15,23,42,.08);

  --morning-1: #fdf2ff; --morning-2: #e0e7ff;
  --midday-1:  #eafffb; --midday-2:  #ecf4ff;
  --evening-1: #fff1f2; --evening-2: #f1e6ff;

  --chip-bg: #eef2ff; --chip-fg: #3730a3; --chip-br: #dfe3ff;
}

:root[data-theme="dark"] {
  --ink: #f8fafc;
  --muted: #cbd5e1;
  --bg: #0f172a;
  --card: #0b1220;
  --border: #273245;
  --ink-contrast: #0b1020;

  --shadow: 0 14px 30px rgba(0,0,0,.35);

  /* dégradés adaptés au sombre */
  --morning-1: #312e81; --morning-2: #1e3a8a;
  --midday-1:  #064e3b; --midday-2:  #0c4a6e;
  --evening-1: #581c87; --evening-2: #3b0764;

  --chip-bg: #1e293b; --chip-fg: #c7d2fe; --chip-br: #334155;
}

/* fond global avec shapes douces, Light/Dark */
html, body, [data-testid="stAppViewContainer"]{
  background:
     radial-gradient(900px 600px at 90% 5%, rgba(236,72,153,.25), transparent 50%),
     radial-gradient(800px 600px at -10% 20%, rgba(99,102,241,.22), transparent 55%),
     radial-gradient(700px 500px at 50% 120%, rgba(34,197,94,.16), transparent 55%),
     var(--bg) !important;
  color: var(--ink) !important;
}
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

h1,h2,h3 {letter-spacing:.2px;}
h1{font-weight: 900;}
h2{font-weight: 800;}
h3{font-weight: 700;}

.container{ padding: 8px 10px 2px 10px; }

.hero{
  position: relative; overflow: hidden;
  border-radius: 22px; padding: 26px;
  background: var(--card); color: var(--ink);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}
.hero .title{
  background: var(--primaryGrad);
  -webkit-background-clip: text; background-clip: text;
  color: transparent; font-weight: 900; font-size: 2.2rem; margin: 2px 0 8px 0;
}
.hero .pill{
  display:inline-flex; gap:8px; align-items:center;
  background: var(--chip-bg); color: var(--chip-fg);
  padding: 8px 12px; border-radius: 999px;
  font-weight: 700; font-size: .9rem; border:1px solid var(--chip-br);
}
.hero .shapes{
  position:absolute; inset: -40px -40px auto auto;
  width: 280px; height: 280px; pointer-events:none;
  background:
      radial-gradient(120px 120px at 70% 35%, rgba(124,58,237,.25), transparent 60%),
      radial-gradient(120px 120px at 35% 55%, rgba(236,72,153,.22), transparent 60%),
      radial-gradient(150px 150px at 85% 75%, rgba(6,182,212,.25), transparent 60%);
  filter: blur(8px); transform: rotate(18deg);
}

.divider{ height:10px; border-radius: 999px; margin: 18px 0 10px 0;
  background: rgba(208,214,255,.25); border:1px solid var(--border); }

.card{
  background: var(--card); color: var(--ink);
  border: 1px solid var(--border);
  border-radius: 18px; padding: 18px; box-shadow: var(--shadow);
  margin: 10px 0 16px 0;
}
.card h3{ margin-top:6px; }

/* Inputs lisibles en sombre comme en clair */
textarea, .stTextArea textarea{
  background: rgba(255,255,255,.8) !important;
  color: var(--ink) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}
:root[data-theme="dark"] textarea,
:root[data-theme="dark"] .stTextArea textarea{
  background: #0f172a !important;
  color: #f8fafc !important;
  border-color: #334155 !important;
}
.stTextInput>div>div>input{
  background: rgba(255,255,255,.85) !important; color: var(--ink) !important;
  border: 1px solid var(--border) !important; border-radius: 14px !important;
}
:root[data-theme="dark"] .stTextInput>div>div>input{
  background: #0f172a !important; color: #f8fafc !important;
  border-color: #334155 !important;
}

/* Radio pills (matin/midi/soir) */
div[role="radiogroup"] > label{
  display:inline-flex; align-items:center; gap:8px;
  margin:6px 10px 6px 0; cursor:pointer;
  background: var(--card); color: var(--ink);
  border:1px solid var(--border); border-radius:999px; padding:10px 14px;
  box-shadow: 0 5px 14px rgba(15,23,42,.06);
}
div[role="radiogroup"] > label:hover{
  border-color: #cfd5ff; background: rgba(255,255,255,.9);
}
:root[data-theme="dark"] div[role="radiogroup"] > label:hover{
  background:#111827; border-color:#3b455a;
}

/* Boutons */
.btn-primary button{
  width: 100%;
  background: var(--primaryGrad);
  color: #ffffff; font-weight: 900;
  border-radius: 14px; border: none;
  box-shadow: 0 14px 26px rgba(124,58,237,.24);
}
.btn-primary button:hover{
  transform: translateY(-1px); box-shadow: 0 18px 34px rgba(124,58,237,.33);
}
.btn-ghost button{
  width: 100%; background: transparent;
  border:1px solid var(--border); color: var(--ink); border-radius: 14px;
}
.btn-ghost button:hover{
  border-color:#c7cced;
}
:root[data-theme="dark"] .btn-ghost button:hover{
  border-color:#3b455a;
}

/* Callouts */
.callout { padding: 12px 14px; border-radius: 12px; margin: 8px 0;
  border: 1px solid var(--border); color: var(--ink); background: rgba(238,242,255,.35); }
.callout.warn{ background:#fff8e6; border-color:#ffe7ab; color:#92400e; }
.callout.ok{ background:#ecfff3; border-color:#c6f7d4; color:#065f46; }
.callout.info{ background:#eefaff; border-color:#cdefff; color:#0c4a6e; }
:root[data-theme="dark"] .callout{
  background:#0b1426; border-color:#273245; color:#cbd5e1;
}

/* Liste du plan */
ul.plan{ list-style:none; padding-left:3px; margin:10px 0 2px 0;}
ul.plan li{
  margin:8px 0; padding:9px 12px; border-radius:12px;
  border:1px solid var(--border); background: rgba(255,255,255,.75);
  color: var(--ink);
}
:root[data-theme="dark"] ul.plan li{
  background:#0f172a; color:#f8fafc; border-color:#334155;
}

/* Cartes moment (dégradés) */
.moment{
  border-radius: 16px; padding: 14px 16px;
  border:1px solid var(--border); box-shadow: var(--shadow);
}
.morning{ background: linear-gradient(135deg,var(--morning-1) 0%,var(--morning-2) 100%); }
.midday { background: linear-gradient(135deg,var(--midday-1) 0%, var(--midday-2) 100%); }
.evening{ background: linear-gradient(135deg,var(--evening-1) 0%,var(--evening-2) 100%); }
.moment h4{ margin:6px 0 4px 0; font-weight:900; color:#ffffffaa; }
:root[data-theme="light"] .moment h4{ color: var(--ink); }
.moment p, .moment li{ color:#f8fafc; }
:root[data-theme="light"] .moment p, :root[data-theme="light"] .moment li{ color:#334155; }
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# OUTILS
# ────────────────────────────────────────────────────────────────────────────────
def ai_is_available() -> bool:
    """True si la clé OPENAI_API_KEY est présente et que le SDK se charge."""
    if not os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from openai import OpenAI  # noqa
        return True
    except Exception:
        return False

def _format_steps(items) -> str:
    """Retourne une <ul> sûre. Accepte str ou list[str]."""
    if not items:
        items = []
    if isinstance(items, str):
        items = [items]
    items = [str(x) for x in items][:3] or ["Commit to just 5 minutes"]
    lis = "".join([f"<li>{html.escape(i)}</li>" for i in items])
    return f'<ul class="plan">{lis}</ul>'

# ────────────────────────────────────────────────────────────────────────────────
# COACH FALLBACK (sans IA)
# ────────────────────────────────────────────────────────────────────────────────
def fallback_coach(note: str, slot: str) -> Dict:
    t = note.lower()
    if any(w in t for w in ["exam", "examen", "test", "quiz"]):
        return {
            "analysis": "Exam vibes: clarity + short activation + active recall.",
            "plan": [
                "Pick one sub-topic and write it.",
                "One Pomodoro (25 min): active read + recall without notes.",
                "Create 5 flashcards and schedule a review."
            ],
            "mantra": "Small wins compound",
            "source": "fallback"
        }
    if any(w in t for w in ["stress", "stressed", "anxious", "anxiété"]):
        return {
            "analysis": "Stress detected: reduce mental load and start tiny.",
            "plan": [
                "2-min brain dump. Circle 1 doable action.",
                "Set a 10-min timer and do only step 1.",
                "Remove one distraction (phone in another room)."
            ],
            "mantra": "Begin before you think",
            "source": "fallback"
        }
    if any(w in t for w in ["workout", "train", "gym", "sport"]):
        return {
            "analysis": "Movement > motivation: lower activation energy.",
            "plan": [
                "Lay out clothes + start 5-min warmup.",
                "Do 2 easy sets to switch on.",
                "Log the session (date, sets, mood)."
            ],
            "mantra": "Motion creates momentum",
            "source": "fallback"
        }
    return {
        "analysis": f"{slot.title()} — pick one clear, tiny objective.",
        "plan": [
            "Write the next 10-min task.",
            "Prepare one thing that reduces friction.",
            "Commit to just 5 minutes and start."
        ],
        "mantra": "One small step beats zero",
        "source": "fallback"
    }

# ────────────────────────────────────────────────────────────────────────────────
# COACH OPENAI (si clé dispo)
# ────────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are DailyUp, a tiny motivational coach.
Return only compact JSON with:
- analysis: 1–2 sentences tailored to user's note + moment (morning/midday/evening).
- plan: exactly 3 concrete micro-steps (10–20 minutes each).
- mantra: 3–6 words, no quotes.
Energetic, practical, zero fluff. No preamble: JSON only.
"""

def ai_coach(note: str, slot: str) -> Dict:
    from openai import OpenAI
    client = OpenAI()

    user_prompt = f"""
Moment: {slot}
Note: {note}

Reply strictly as JSON with keys: analysis, plan, mantra.
Example:
{{
 "analysis": "Exam stress — use short focus and active recall.",
 "plan": ["Pick 1 weak topic", "Pomodoro 25", "Create 5 flashcards"],
 "mantra": "Small wins compound"
}}
""".strip()

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.95,   # créativité max (pas de curseur)
        max_tokens=220,
    )

    content = resp.choices[0].message.content or ""
    try:
        import json
        content = re.sub(r"^```json|```$", "", content.strip(), flags=re.MULTILINE)
        data = json.loads(content)
        analysis = str(data.get("analysis", "")).strip()
        plan = [str(x).strip() for x in (data.get("plan") or [])][:3]
        mantra = str(data.get("mantra", "")).strip()
        if len(plan) < 3:
            plan += ["Commit to just 5 minutes"] * (3 - len(plan))
        if not analysis:
            analysis = f"{slot.title()} — keep it tiny, clear, doable."
        if not mantra:
            mantra = "Small wins compound"
        return {"analysis": analysis, "plan": plan, "mantra": mantra, "source": "openai"}
    except Exception as e:
        return {"error": str(e)}

# ────────────────────────────────────────────────────────────────────────────────
# UI — INTRO (identique à avant)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="container">', unsafe_allow_html=True)
st.markdown(
    """
<div class="hero">
  <div class="shapes"></div>
  <div class="pill">✨ Micro-Coach DailyUp</div>
  <div class="title">Tiny nudges. Massive progress.</div>
  <p style="max-width:820px; color:var(--muted); font-size:1.05rem;">
    Tell me your main goal or how you feel. I’ll craft a <b>3-step micro-plan</b> and a short <b>mantra</b> you can use today.
    Stay vertical: Step 1 → Step 2 → Step 3. Simple, bright, focused.
  </p>
  <ul style="margin:.5rem 0 0 1rem; color:#334155;">
    <li><b>Step 1</b>: Pick your moment (morning / midday / evening).</li>
    <li><b>Step 2</b>: Describe what’s on your mind (1 sentence is enough).</li>
    <li><b>Step 3</b>: Tap <i>Analyze & coach me</i> — get your plan + mantra.</li>
  </ul>
</div>
""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 1 — MOMENT
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 1 — Pick your moment")

slot = st.radio(
    "When is this for?",
    options=["morning", "midday", "evening"],
    index=0,
    horizontal=True,
    help="This tunes the tone and examples for your coach.",
)

MOMENT_INFO = {
    "morning": {
        "title": "Morning — Start bright & small",
        "bullets": [
            "⚡ Energy: fresh start, reduce friction",
            "🎯 Focus: one clear tiny win (10–15 min)",
            "🧭 Tone: action-first, momentum"
        ],
        "cls": "morning"
    },
    "midday": {
        "title": "Midday — Reset & refocus",
        "bullets": [
            "🔄 Energy: re-align quickly",
            "🎯 Focus: one compact block (15–20 min)",
            "🧭 Tone: pragmatic, re-centering"
        ],
        "cls": "midday"
    },
    "evening": {
        "title": "Evening — Wrap & seed tomorrow",
        "bullets": [
            "🌙 Energy: soft close, reduce anxiety",
            "📝 Focus: reflect + seed next step",
            "🧭 Tone: calming, clear next action"
        ],
        "cls": "evening"
    },
}

info = MOMENT_INFO[slot]
bul = "".join([f"<li>{html.escape(x)}</li>" for x in info["bullets"]])
st.markdown(
    f"""
<div class="moment {info['cls']}">
  <h4>{html.escape(info['title'])}</h4>
  <ul style="margin:.2rem 0 0 .9rem;">{bul}</ul>
</div>
""",
    unsafe_allow_html=True,
)

NUDGES = {
    "morning": "Morning Boost — one small step beats zero.",
    "midday": "Midday Reset — turn one tiny win.",
    "evening": "Evening Wrap — reflect and set tomorrow’s seed."
}
st.caption(f"Prompt used by the coach: {NUDGES[slot]}")

# ────────────────────────────────────────────────────────────────────────────────
# STEP 2 — NOTE UTILISATEUR
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 2 — Tell me your note")

with st.container():
    user_note = st.text_area(
        "What’s on your mind right now?",
        placeholder="e.g., I’m stressed about my exam and I keep procrastinating.",
        height=120,
        label_visibility="visible",
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        if st.button("Paste an example"):
            st.session_state["seed"] = "I'm stressed for my exam and can't focus."
        st.markdown("</div>", unsafe_allow_html=True)
        if "seed" in st.session_state and not user_note:
            user_note = st.session_state["seed"]
    with c2:
        st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
        if st.button("Clear"):
            st.session_state.pop("seed", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 3 — ANALYZE & COACH
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 3 — Analyze & coach me")

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
        with st.spinner("Crafting your plan…"):
            result = ai_coach(user_note, slot) if use_ai else fallback_coach(user_note, slot)
        if isinstance(result, dict) and result.get("error"):
            st.markdown(
                '<div class="callout warn">⚠️ AI error — switched to smart fallback.</div>',
                unsafe_allow_html=True,
            )
            result = fallback_coach(user_note, slot)

        # Rendu — identique, mais contrastes sûrs
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.success("✅ Your personalized plan is ready!", icon="✅")
        st.markdown("### Analysis")
        st.write(result["analysis"])

        st.markdown("### 3-Step Plan")
        st.markdown(_format_steps(result["plan"]), unsafe_allow_html=True)

        st.markdown("### Mantra")
        st.write(result["mantra"])
        st.caption(f"Source: {result.get('source','n/a')}")
        st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("Debug (optional)"):
            st.json(
                {
                    "slot": slot,
                    "note": user_note,
                    "timestamp": datetime.utcnow().isoformat(),
                    "engine": result.get("source", "n/a"),
                }
            )

st.markdown('</div>', unsafe_allow_html=True)
