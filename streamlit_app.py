# -*- coding: utf-8 -*-
import os
import re
import html
import random
import hashlib
from datetime import datetime, date
from typing import Dict

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# Sentiment (VADER)
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Ensure VADER lexicon on Streamlit Cloud
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

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
# THEME (LIGHT/DARK) + STRONG CONTRASTS
# ────────────────────────────────────────────────────────────────────────────────
CSS = """
:root{
  --ink: #111827;              /* main text (light) */
  --muted: #4b5563;            /* secondary text (light) */
  --bg: #f6f8ff;               /* light background */
  --card: #ffffff;             /* cards */
  --border: #e6e8f2;           /* borders */
  --primaryGrad: linear-gradient(135deg,#7c3aed 0%, #ec4899 55%, #06b6d4 100%);
  --accentGrad: linear-gradient(135deg,#22c55e 0%, #06b6d4 50%, #818cf8 100%);
  --shadow: 0 14px 30px rgba(15,23,42,.08);
}

/* Dark mode */
@media (prefers-color-scheme: dark){
  :root{
    --ink: #f2f4ff;
    --muted: #c7c9d3;
    --bg: #0f1220;
    --card: #121529;
    --border: #2a2f45;
    --primaryGrad: linear-gradient(135deg,#a78bfa 0%, #f472b6 55%, #22d3ee 100%);
    --accentGrad: linear-gradient(135deg,#34d399 0%, #22d3ee 50%, #a5b4fc 100%);
    --shadow: 0 14px 30px rgba(0,0,0,.45);
  }
}

html, body, [data-testid="stAppViewContainer"]{
  background:
     radial-gradient(900px 600px at 90% 5%, rgba(236,72,153,.18), transparent 50%),
     radial-gradient(800px 600px at -10% 20%, rgba(99,102,241,.16), transparent 55%),
     radial-gradient(700px 500px at 50% 120%, rgba(34,197,94,.12), transparent 55%),
     var(--bg);
  color: var(--ink);
}

/* header/top */
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

h1,h2,h3 {letter-spacing:.2px;}
h1{font-weight: 900;}
h2{font-weight: 800;}
h3{font-weight: 700;}

.container{
  position:relative;
  padding: 8px 10px 2px 10px;
}

/* ───── Quote-of-the-Day banner (TOP) ───── */
.banner{
  position: relative;
  margin: 6px 0 20px 0;
  padding: 18px 20px;
  border-radius: 18px;
  background: var(--card);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
}
.banner:before{
  content: "";
  position: absolute; inset: -2px;
  border-radius: 20px;
  background: var(--primaryGrad);
  filter: blur(22px);
  opacity: .18;
  z-index: 0;
}
.banner .b-label{
  position: relative; z-index: 1;
  display:inline-block;
  font-weight: 900; letter-spacing:.5px;
  text-transform: uppercase;
  font-size: .9rem;
  background: var(--primaryGrad);
  -webkit-background-clip: text; background-clip: text;
  color: transparent;
  margin-bottom: 6px;
}
.banner .b-quote{
  position: relative;
  z-index: 1;
  font-size: 1.08rem;
  line-height: 1.6rem;
  font-style: italic;
}
.banner .b-author{
  position: relative;
  z-index: 1;
  margin-top: 6px;
  font-weight: 700;
  letter-spacing: .2px;
  color: var(--muted);
  font-size: 0.95rem;
}

/* hero */
.hero{
  position: relative;
  overflow: hidden;
  border-radius: 22px;
  padding: 26px 26px;
  background: var(--card);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}
.hero .title{
  background: var(--primaryGrad);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  font-weight: 900;
  font-size: 2.2rem;
  margin: 2px 0 8px 0;
}
.hero .pill{
  display:inline-flex; gap:8px; align-items:center;
  background: #eef2ff; color: #3730a3;
  padding: 8px 12px; border-radius: 999px;
  font-weight: 700; font-size: .9rem;
  border:1px solid #dfe3ff;
}
@media (prefers-color-scheme: dark){
  .hero .pill{ background:#1f2541; color:#c7d2fe; border-color:#2a3156; }
}
.hero .shapes{
  position:absolute; inset: -40px -40px auto auto;
  width: 280px; height: 280px; pointer-events:none;
  background:
      radial-gradient(120px 120px at 70% 35%, rgba(124,58,237,.25), transparent 60%),
      radial-gradient(120px 120px at 35% 55%, rgba(236,72,153,.22), transparent 60%),
      radial-gradient(150px 150px at 85% 75%, rgba(6,182,212,.25), transparent 60%);
  filter: blur(8px);
  transform: rotate(18deg);
}

/* divider */
.divider{ height:10px; border-radius: 999px; margin: 18px 0 10px 0; background: #eef1ff; border:1px solid #e3e7ff; }
@media (prefers-color-scheme: dark){
  .divider{ background:#1c2140; border-color:#2b335a; }
}

/* cards */
.card{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: var(--shadow);
  margin: 10px 0 16px 0;
}
.card h3{ margin-top:6px; }

/* inputs */
textarea, .stTextArea textarea{
  background: #fbfcff !important;
  border: 1px solid #e6e8f2 !important;
  color: var(--ink) !important;
  border-radius: 14px !important;
}
.stTextInput>div>div>input{
  background: #fbfcff !important; color: var(--ink) !important;
  border: 1px solid #e6e8f2 !important; border-radius: 14px !important;
}
@media (prefers-color-scheme: dark){
  textarea, .stTextArea textarea,
  .stTextInput>div>div>input{
    background:#101429 !important; border-color:#2a2f45 !important; color:#eaf0ff !important;
  }
}

/* radio -> pills */
div[role="radiogroup"] > label{
  display:inline-flex; align-items:center; gap:8px;
  margin:6px 10px 6px 0; cursor:pointer;
  background: #ffffff; color: var(--ink);
  border:1px solid #e7e9f5; border-radius:999px; padding:10px 14px;
  box-shadow: 0 5px 14px rgba(15,23,42,.06);
}
div[role="radiogroup"] > label:hover{
  border-color: #cfd5ff; background: #fbfcff;
}
@media (prefers-color-scheme: dark){
  div[role="radiogroup"] > label{ background:#101429; border-color:#2a2f45; box-shadow:none; }
  div[role="radiogroup"] > label:hover{ background:#0d1124; border-color:#3b4162; }
}

/* buttons */
.btn-primary button{
  width: 100%;
  background: var(--primaryGrad);
  color: #0b1020; font-weight: 900;
  border-radius: 14px; border: none;
  box-shadow: 0 14px 26px rgba(124,58,237,.24);
}
.btn-primary button:hover{ transform: translateY(-1px); box-shadow: 0 18px 34px rgba(124,58,237,.33); }

.btn-ghost button{
  width: 100%;
  background: transparent;
  border:1px solid #d8dcf2; color: var(--ink);
  border-radius: 14px;
}
.btn-ghost button:hover{ border-color:#c7cced; }
@media (prefers-color-scheme: dark){
  .btn-ghost button{ border-color:#2a2f45; color:#e9edff; }
  .btn-ghost button:hover{ border-color:#394066; }
}

/* callouts */
.callout {
  padding: 12px 14px; border-radius: 12px; margin: 8px 0;
  border: 1px solid var(--border); color: var(--ink); background:#f8faff;
}
.callout.warn{ background:#fff8e6; border-color:#ffe7ab; }
.callout.ok{ background:#ecfff3; border-color:#c6f7d4; }
.callout.info{ background:#eefaff; border-color:#cdefff; }
@media (prefers-color-scheme: dark){
  .callout{ background:#111634; border-color:#2a2f45; }
  .callout.warn{ background:#3b2b10; border-color:#7a5b14;}
  .callout.ok{ background:#0f2b1b; border-color:#1c5a32;}
  .callout.info{ background:#0f1c2c; border-color:#28435e;}
}

/* 3-step list */
ul.plan{ list-style:none; padding-left:3px; margin:10px 0 2px 0;}
ul.plan li{
  margin:8px 0; padding:9px 12px; border-radius:12px;
  border:1px solid #e8ebf6; background:#fbfdff;
}
@media (prefers-color-scheme: dark){
  ul.plan li{ background:#0f1429; border-color:#252b43; }
}

/* moment card */
.moment{
  border-radius: 16px; padding: 16px 18px; color:#0b1020;
  border:1px solid var(--border); box-shadow:var(--shadow);
}
.morning{ background: linear-gradient(135deg,#fff1f9 0%,#e6edff 100%); }
.midday{  background: linear-gradient(135deg,#e7fff8 0%,#ebf2ff 100%); }
.evening{ background: linear-gradient(135deg,#ffe8ec 0%,#ebe2ff 100%); }
@media (prefers-color-scheme: dark){
  .moment{ color:#eef2ff; border-color:#2a2f45; }
  .morning{ background: linear-gradient(135deg,#2a1930 0%,#1a1f40 100%); }
  .midday{  background: linear-gradient(135deg,#0d2a26 0%,#16243f 100%); }
  .evening{ background: linear-gradient(135deg,#2b1820 0%,#231c41 100%); }
}
.moment h4{ margin:6px 0 6px 0; font-weight:900;}
.moment p, .moment li{ margin:2px 0 0 0; color:#334155;}
@media (prefers-color-scheme: dark){
  .moment p, .moment li{ color:#cdd3ff;}
}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────────────
# UTILITIES
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
# QUOTE OF THE DAY (TOP banner)
# ────────────────────────────────────────────────────────────────────────────────
BIG_QUOTES = [
    ("Two-Minute Rule", "If it takes less than two minutes, do it now. Tiny wins spark momentum and make action easier next time.", "James Clear (Atomic Habits)"),
    ("Self-Determination Theory", "Sustainable motivation grows from autonomy, competence, and relatedness. Create a sense of mastery and connection.", "Deci & Ryan (2000)"),
    ("Pygmalion Effect", "High expectations change behavior and results. Believe you can improve—your brain follows your focus.", "Rosenthal & Jacobson (1968)"),
    ("Small Wins", "Celebrate micro-progress: each step links effort to satisfaction and builds a virtuous circle of motivation.", "Teresa Amabile (Harvard)"),
    ("Fresh Start Effect", "Temporal landmarks (Mondays, first of the month, birthdays) boost the urge to start clean and commit.", "Dai, Milkman & Riis (2014)"),
]

def big_quote_of_the_day() -> Dict[str, str]:
    seed = f"{date.today().isoformat()}::banner"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(BIG_QUOTES)
    title, text, author = BIG_QUOTES[idx]
    return {"title": title, "text": text, "author": author}

# (Small quotes list kept out — mini quote removed as requested)

# ────────────────────────────────────────────────────────────────────────────────
# FALLBACK COACH
# ────────────────────────────────────────────────────────────────────────────────
def fallback_coach(note: str, slot: str) -> Dict:
    t = note.lower()
    if any(w in t for w in ["exam", "examen", "test", "quiz"]):
        return {
            "analysis": "Exam context: clarity + quick activation + active recall.",
            "plan": [
                "Pick 1 sub-topic (write it).",
                "One 25′ Pomodoro: active read + recall.",
                "Create 5 flashcards and schedule a review."
            ],
            "mantra": "Small wins compound",
            "source": "fallback"
        }
    if any(w in t for w in ["stress", "stressed", "anxious", "anxiety"]):
        return {
            "analysis": "Stress detected: reduce mental load and start tiny.",
            "plan": [
                "2′ brain-dump: list all. Circle 1 doable item.",
                "Set a 10′ timer and do just the first micro-step.",
                "Remove one distraction (phone away)."
            ],
            "mantra": "Begin before you think",
            "source": "fallback"
        }
    if any(w in t for w in ["workout", "train", "gym", "sport"]):
        return {
            "analysis": "Motion > motivation: reduce activation energy.",
            "plan": [
                "Prep outfit + 5′ warmup.",
                "Do 2 easy sets to get moving.",
                "Log the session (date, sets, mood)."
            ],
            "mantra": "Motion creates momentum",
            "source": "fallback"
        }
    return {
        "analysis": f"{slot.title()} — keep one tiny clear goal.",
        "plan": [
            "Write the next 10-minute task.",
            "Prepare one thing that reduces friction.",
            "Commit to just 5 minutes and start."
        ],
        "mantra": "One small step beats zero",
        "source": "fallback"
    }

# ────────────────────────────────────────────────────────────────────────────────
# OPENAI COACH
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
        temperature=0.95,
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
# SENTIMENT → RADAR (6 factors)
# ────────────────────────────────────────────────────────────────────────────────
SIA = SentimentIntensityAnalyzer()

KEYS = {
    "sad": {"sad", "sadness,","depressed","down","cry","unhappy","low"},
    "anx": {"anxious","anxiety","nervous","worried","panic","stressed"},
    "mot": {"motivation","motivated","drive","excited","inspired","eager"},
    "focus": {"focus","concentrate","study","deep","locked","attention"},
    "tired": {"tired","exhausted","fatigued","sleepy","drained"},
}

def _density(note: str, vocab: set) -> float:
    t = re.findall(r"[a-zA-Z']+", note.lower())
    if not t:
        return 0.0
    count = sum(1 for w in t if w in vocab)
    return min(1.0, count / max(4, len(t)/6))

def sentiment_radar(note: str) -> Dict[str, float]:
    vs = SIA.polarity_scores(note or "")
    pos = vs["pos"]; neg = vs["neg"]; comp = vs["compound"]

    sad = _density(note, KEYS["sad"])
    anx = _density(note, KEYS["anx"])
    mot = _density(note, KEYS["mot"])
    foc = _density(note, KEYS["focus"])

    positive = min(1.0, pos + max(0.0, comp) * 0.5)
    negative = min(1.0, neg + max(0.0, -comp) * 0.5)
    sadness  = min(1.0, sad + neg * 0.3)
    anxiety  = min(1.0, anx + neg * 0.2)
    motivation = min(1.0, max(mot, pos * 0.6 + max(0, comp) * 0.3))
    focus = min(1.0, max(foc, pos * 0.3 + (1 - neg) * 0.2))

    return {
        "Positive": round(positive, 3),
        "Negative": round(negative, 3),
        "Sadness": round(sadness, 3),
        "Anxiety": round(anxiety, 3),
        "Motivation": round(motivation, 3),
        "Focus": round(focus, 3),
    }

def radar_chart(scores: Dict[str, float]) -> go.Figure:
    cats = list(scores.keys())
    vals = list(scores.values()) + [list(scores.values())[0]]
    cats_closed = cats + [cats[0]]

    fig = go.Figure(
        data=go.Scatterpolar(
            r=vals, theta=cats_closed, fill='toself', name='Sentiment',
            line=dict(color="#7c3aed"), fillcolor="rgba(124,58,237,.20)"
        )
    )
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0,1], showticklabels=True, tickfont=dict(color="#6b7280")),
            angularaxis=dict(tickfont=dict(color="#6b7280"))
        ),
        showlegend=False,
        margin=dict(l=20,r=20,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig

# ────────────────────────────────────────────────────────────────────────────────
# UI — CONTAINER
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="container">', unsafe_allow_html=True)

# TOP BANNER: Quote of the Day (big only)
bq = big_quote_of_the_day()
st.markdown(
    f"""
<div class="banner">
  <div class="b-label">QUOTE OF THE DAY</div>
  <div class="b-quote">“{html.escape(bq['text'])}”</div>
  <div class="b-author">— {html.escape(bq['author'])} · <span style="opacity:.8">{html.escape(bq['title'])}</span></div>
</div>
""",
    unsafe_allow_html=True,
)

# HERO (unchanged)
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
    <li><b>Step 2</b>: Describe what’s on your mind (one sentence is enough).</li>
    <li><b>Step 3</b>: Tap <i>Analyze & coach me</i> — get your plan + mantra.</li>
  </ul>
</div>
""",
    unsafe_allow_html=True,
)

# STEP 1 — MOMENT (mini quote removed)
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

st.caption({
    "morning": "Prompt used by the coach: Morning Boost — one small step beats zero.",
    "midday": "Prompt used by the coach: Midday Reset — turn one tiny win.",
    "evening": "Prompt used by the coach: Evening Wrap — reflect and set tomorrow’s seed."
}[slot])

# STEP 2 — USER NOTE + LIVE RADAR
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 2 — Tell me your note")

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
        st.experimental_rerun()
    st.markdown("</div>", unsafe_allow_html=True)

if (user_note or "").strip():
    st.markdown("#### Mood radar")
    scores = sentiment_radar(user_note)
    fig = radar_chart(scores)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander("Radar values"):
        st.json(scores)

# STEP 3 — ANALYZE & COACH
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 3 — Analyze & coach me")

st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
go = st.button("💬 Analyze & coach me", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if go:
    if not (user_note or "").strip():
        st.markdown('<div class="callout warn">⚠️ Please write a short note first.</div>', unsafe_allow_html=True)
    else:
        use_ai = ai_is_available()
        if not use_ai:
            st.markdown('<div class="callout info">ℹ️ OpenAI key not found — using smart fallback.</div>', unsafe_allow_html=True)
        with st.spinner("Crafting your plan…"):
            result = ai_coach(user_note, slot) if use_ai else fallback_coach(user_note, slot)
        if isinstance(result, dict) and result.get("error"):
            st.markdown('<div class="callout warn">⚠️ AI error — switched to smart fallback.</div>', unsafe_allow_html=True)
            result = fallback_coach(user_note, slot)

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
            st.json({"slot": slot, "note": user_note, "timestamp": datetime.utcnow().isoformat(), "engine": result.get("source", "n/a")})

st.markdown('</div>', unsafe_allow_html=True)  # container
