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
# THEME LIGHT/DARK FIX
# ────────────────────────────────────────────────────────────────────────────────
base_theme = st.get_option("theme.base") or "light"
st.markdown(
    f'<script>document.documentElement.setAttribute("data-theme","{base_theme}");</script>',
    unsafe_allow_html=True,
)

CSS = """
:root {
  --ink: #0f172a;
  --muted: #4b5563;
  --bg: #f5f7ff;
  --card: #ffffff;
  --border: #e6e8f2;
  --primaryGrad: linear-gradient(135deg,#7c3aed 0%, #ec4899 55%, #06b6d4 100%);
  --shadow: 0 14px 30px rgba(15,23,42,.08);

  --morning-1: #fdf2ff; --morning-2: #e0e7ff;
  --midday-1:  #eafffb; --midday-2:  #ecf4ff;
  --evening-1: #fff1f2; --evening-2: #f1e6ff;
}

:root[data-theme="dark"] {
  --ink: #f8fafc;
  --muted: #cbd5e1;
  --bg: #0f172a;
  --card: #0b1220;
  --border: #273245;
  --shadow: 0 14px 30px rgba(0,0,0,.35);

  --morning-1: #312e81; --morning-2: #1e3a8a;
  --midday-1:  #064e3b; --midday-2:  #0c4a6e;
  --evening-1: #581c87; --evening-2: #3b0764;
}

html, body, [data-testid="stAppViewContainer"]{
  background:
     radial-gradient(900px 600px at 90% 5%, rgba(236,72,153,.25), transparent 50%),
     radial-gradient(800px 600px at -10% 20%, rgba(99,102,241,.22), transparent 55%),
     var(--bg) !important;
  color: var(--ink);
}
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

.hero{
  border-radius: 22px;
  padding: 26px;
  background: var(--card);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}
.hero .title{
  background: var(--primaryGrad);
  -webkit-background-clip: text;
  color: transparent;
  font-weight: 900;
  font-size: 2.2rem;
  margin-bottom: 8px;
}
.divider{ height:10px; border-radius: 999px; margin: 18px 0 10px 0;
  background: rgba(208,214,255,.25); border:1px solid var(--border); }

.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px;
  box-shadow: var(--shadow);
  margin: 10px 0 16px 0;
}

textarea, .stTextArea textarea{
  background: rgba(255,255,255,.9) !important;
  color: var(--ink) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}
:root[data-theme="dark"] textarea{
  background: #0f172a !important;
  color: #f8fafc !important;
  border-color: #334155 !important;
}

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

.callout { padding: 12px 14px; border-radius: 12px; margin: 8px 0;
  border: 1px solid var(--border); color: var(--ink); background: rgba(238,242,255,.35); }
:root[data-theme="dark"] .callout{
  background:#0b1426; border-color:#273245; color:#cbd5e1;
}

/* MOMENT CARDS */
.moment {
  border-radius: 16px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
.morning { background: linear-gradient(135deg,var(--morning-1) 0%,var(--morning-2) 100%); }
.midday  { background: linear-gradient(135deg,var(--midday-1) 0%, var(--midday-2) 100%); }
.evening { background: linear-gradient(135deg,var(--evening-1) 0%,var(--evening-2) 100%); }

.moment h4 { font-weight: 900; margin: 0 0 6px 0; color: #1e293b; }
[data-theme="dark"] .moment h4 { color: #f9fafb; }

.moment ul li {
  font-size: 0.95rem;
  font-weight: 600;
  margin: 4px 0;
  color: #334155;
}
[data-theme="dark"] .moment ul li { color: #e2e8f0; }

ul.plan{ list-style:none; padding-left:3px; margin:10px 0 2px 0;}
ul.plan li{
  margin:8px 0; padding:9px 12px; border-radius:12px;
  border:1px solid var(--border);
  background: rgba(255,255,255,.85);
}
[data-theme="dark"] ul.plan li{
  background:#0f172a;
  color:#f8fafc;
  border-color:#334155;
}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# OUTILS
# ────────────────────────────────────────────────────────────────────────────────
def ai_is_available() -> bool:
    if not os.getenv("OPENAI_API_KEY"):
        return False
    try:
        from openai import OpenAI  # noqa
        return True
    except Exception:
        return False

def _format_steps(items) -> str:
    if not items:
        items = []
    if isinstance(items, str):
        items = [items]
    items = [str(x) for x in items][:3] or ["Commit to just 5 minutes"]
    lis = "".join([f"<li>{html.escape(i)}</li>" for i in items])
    return f'<ul class="plan">{lis}</ul>'

# ────────────────────────────────────────────────────────────────────────────────
# COACH FALLBACK
# ────────────────────────────────────────────────────────────────────────────────
def fallback_coach(note: str, slot: str) -> Dict:
    t = note.lower()
    if any(w in t for w in ["exam", "test", "quiz"]):
        return {
            "analysis": "Exam vibes: clarity + short activation + active recall.",
            "plan": [
                "Pick one sub-topic and write it.",
                "One Pomodoro (25 min): active read + recall.",
                "Create 5 flashcards and review later."
            ],
            "mantra": "Small wins compound",
            "source": "fallback"
        }
    if any(w in t for w in ["stress", "stressed", "anxious"]):
        return {
            "analysis": "Stress detected: reduce mental load and start tiny.",
            "plan": [
                "2-min brain dump — circle 1 doable action.",
                "Set a 10-min timer — focus only on that.",
                "Remove 1 distraction (like your phone)."
            ],
            "mantra": "Begin before you think",
            "source": "fallback"
        }
    return {
        "analysis": f"{slot.title()} — pick one clear, small action.",
        "plan": [
            "Write the next 10-min task.",
            "Prepare something to reduce friction.",
            "Commit to just 5 minutes and start."
        ],
        "mantra": "One small step beats zero",
        "source": "fallback"
    }

# ────────────────────────────────────────────────────────────────────────────────
# COACH OPENAI
# ────────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are DailyUp, a micro-motivation coach.
Return JSON only:
{ "analysis": "...", "plan": ["...", "...", "..."], "mantra": "..." }
Be short, practical, motivational.
"""

def ai_coach(note: str, slot: str) -> Dict:
    from openai import OpenAI
    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Moment: {slot}\nNote: {note}"},
        ],
        temperature=0.95,
        max_tokens=220,
    )
    import json
    content = resp.choices[0].message.content
    content = re.sub(r"^```json|```$", "", content.strip(), flags=re.MULTILINE)
    data = json.loads(content)
    return {
        "analysis": data.get("analysis", "Keep it tiny and clear."),
        "plan": data.get("plan", []),
        "mantra": data.get("mantra", "Small wins compound"),
        "source": "openai"
    }

# ────────────────────────────────────────────────────────────────────────────────
# UI — HERO SECTION (améliorée)
# ────────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <div class="title">✨ Welcome to <b>DailyUp</b></div>
  <p style="max-width:820px; color:var(--muted); font-size:1.05rem; line-height:1.6;">
    Your personal <b>micro-coach</b> for building momentum — one tiny step at a time.
    <br><br>
    <b>Here’s how it works:</b>
  </p>
  <ul style="margin:.5rem 0 0 1rem; color:#334155; font-size:1rem;">
    <li>💡 <b>Step 1</b> — Choose your moment: <i>morning</i>, <i>midday</i>, or <i>evening</i>. This sets your mindset.</li>
    <li>🧠 <b>Step 2</b> — Tell me what’s on your mind: one honest sentence is enough.</li>
    <li>🚀 <b>Step 3</b> — Hit <b>“Analyze & coach me”</b>. I’ll create a short 3-step plan and a mantra to guide your day.</li>
  </ul>
  <p style="color:var(--muted); font-size:.95rem; margin-top:12px;">
    Every tap gives you a clear micro-plan to act on — designed to keep you moving.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 1 — PICK MOMENT
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 1 — Pick your moment")

slot = st.radio("When is this for?", ["morning", "midday", "evening"], horizontal=True)

MOMENT_INFO = {
    "morning": {
        "title": "Morning — Start bright & small",
        "bullets": ["⚡ Energy: fresh start, reduce friction",
                    "🎯 Focus: one clear tiny win (10–15 min)",
                    "🧭 Tone: action-first, momentum"],
        "cls": "morning"
    },
    "midday": {
        "title": "Midday — Reset & refocus",
        "bullets": ["🔄 Energy: re-align quickly",
                    "🎯 Focus: one compact block (15–20 min)",
                    "🧭 Tone: pragmatic, centered"],
        "cls": "midday"
    },
    "evening": {
        "title": "Evening — Wrap & seed tomorrow",
        "bullets": ["🌙 Energy: calm close",
                    "📝 Focus: reflect + plan ahead",
                    "🧭 Tone: clarity and closure"],
        "cls": "evening"
    },
}
info = MOMENT_INFO[slot]
bul = "".join([f"<li>{html.escape(x)}</li>" for x in info["bullets"]])
st.markdown(
    f"""<div class="moment {info['cls']}">
      <h4>{html.escape(info['title'])}</h4>
      <ul>{bul}</ul>
    </div>""",
    unsafe_allow_html=True,
)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 2 — USER NOTE
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 2 — Tell me your note")

user_note = st.text_area(
    "What’s on your mind right now?",
    placeholder="e.g., I’m stressed about my exam and can’t focus.",
    height=120,
)

# ────────────────────────────────────────────────────────────────────────────────
# STEP 3 — ANALYZE & COACH
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 3 — Analyze & coach me")

st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
go = st.button("💬 Analyze & coach me")
st.markdown("</div>", unsafe_allow_html=True)

if go:
    if not user_note.strip():
        st.warning("Please write a short note first.")
    else:
        with st.spinner("Analyzing your note..."):
            use_ai = ai_is_available()
            result = ai_coach(user_note, slot) if use_ai else fallback_coach(user_note, slot)

        st.success("✅ Your personalized plan is ready!")
        st.markdown("### Analysis")
        st.write(result["analysis"])
        st.markdown("### 3-Step Plan")
        st.markdown(_format_steps(result["plan"]), unsafe_allow_html=True)
        st.markdown("### Mantra")
        st.write(result["mantra"])
        st.caption(f"Source: {result.get('source','n/a')}")
