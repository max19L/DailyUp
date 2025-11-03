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
# THEME (LIGHT/DARK) + STYLING
# ────────────────────────────────────────────────────────────────────────────────
CSS = """
:root{
  --ink: #111827;
  --muted: #4b5563;
  --bg: #f6f8ff;
  --card: #ffffff;
  --border: #e6e8f2;
  --primaryGrad: linear-gradient(135deg,#7c3aed 0%, #ec4899 55%, #06b6d4 100%);
  --accentGrad: linear-gradient(135deg,#22c55e 0%, #06b6d4 50%, #818cf8 100%);
  --shadow: 0 14px 30px rgba(15,23,42,.08);
}
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
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
h1,h2,h3{letter-spacing:.2px;}
h1{font-weight:900;}
h2{font-weight:800;}
h3{font-weight:700;}
.container{position:relative;padding:8px 10px 2px 10px;}
/* big title */
.bigtitle{
  text-align:center;
  font-weight:900;
  font-size:3rem;
  background: var(--primaryGrad);
  -webkit-background-clip: text;
  background-clip: text;
  color:transparent;
  margin-top:10px;
  margin-bottom:25px;
  letter-spacing:1px;
}
/* quote banner */
.banner{
  position:relative;margin:6px 0 20px 0;padding:18px 20px;
  border-radius:18px;background:var(--card);border:1px solid var(--border);box-shadow:var(--shadow);
}
.banner:before{
  content:"";position:absolute;inset:-2px;border-radius:20px;
  background:var(--primaryGrad);filter:blur(22px);opacity:.18;z-index:0;
}
.banner .b-label{
  position:relative;z-index:1;display:inline-block;
  font-weight:900;letter-spacing:.5px;text-transform:uppercase;
  font-size:.9rem;background:var(--primaryGrad);
  -webkit-background-clip:text;background-clip:text;color:transparent;
  margin-bottom:6px;
}
.banner .b-quote{position:relative;z-index:1;font-size:1.08rem;line-height:1.6rem;font-style:italic;}
.banner .b-author{position:relative;z-index:1;margin-top:6px;font-weight:700;letter-spacing:.2px;color:var(--muted);font-size:0.95rem;}
/* hero */
.hero{position:relative;overflow:hidden;border-radius:22px;padding:26px 26px;background:var(--card);box-shadow:var(--shadow);border:1px solid var(--border);}
.hero .title{background:var(--primaryGrad);-webkit-background-clip:text;background-clip:text;color:transparent;font-weight:900;font-size:2.2rem;margin:2px 0 8px 0;}
.hero .pill{display:inline-flex;gap:8px;align-items:center;background:#eef2ff;color:#3730a3;padding:8px 12px;border-radius:999px;font-weight:700;font-size:.9rem;border:1px solid #dfe3ff;}
@media (prefers-color-scheme: dark){.hero .pill{background:#1f2541;color:#c7d2fe;border-color:#2a3156;}}
.divider{height:10px;border-radius:999px;margin:18px 0 10px 0;background:#eef1ff;border:1px solid #e3e7ff;}
@media (prefers-color-scheme: dark){.divider{background:#1c2140;border-color:#2b335a;}}
.card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:18px 18px;box-shadow:var(--shadow);margin:10px 0 16px 0;}
.card h3{margin-top:6px;}
/* moment card */
.moment{border-radius:16px;padding:16px 18px;color:#0b1020;border:1px solid var(--border);box-shadow:var(--shadow);}
.morning{background:linear-gradient(135deg,#fff1f9 0%,#e6edff 100%);}
.midday{background:linear-gradient(135deg,#e7fff8 0%,#ebf2ff 100%);}
.evening{background:linear-gradient(135deg,#ffe8ec 0%,#ebe2ff 100%);}
@media (prefers-color-scheme: dark){
  .moment{color:#eef2ff;border-color:#2a2f45;}
  .morning{background:linear-gradient(135deg,#2a1930 0%,#1a1f40 100%);}
  .midday{background:linear-gradient(135deg,#0d2a26 0%,#16243f 100%);}
  .evening{background:linear-gradient(135deg,#2b1820 0%,#231c41 100%);}
}
/* mantra highlight */
.mantra-box{
  text-align:center;
  margin-top:20px;
  padding:22px 26px;
  border-radius:18px;
  border:2px solid transparent;
  background:var(--card);
  background-image:var(--accentGrad);
  background-origin:border-box;
  background-clip:padding-box,border-box;
  box-shadow:var(--shadow);
}
.mantra-text{
  font-size:1.4rem;
  font-weight:800;
  background:var(--primaryGrad);
  -webkit-background-clip:text;
  background-clip:text;
  color:transparent;
}
.mantra-sub{
  color:var(--muted);
  font-size:0.9rem;
  margin-top:6px;
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
        from openai import OpenAI
        return True
    except Exception:
        return False

def _format_steps(items):
    if not items:
        items = []
    if isinstance(items, str):
        items = [items]
    items = [str(x) for x in items][:3]
    lis = "".join([f"<li>{html.escape(i)}</li>" for i in items])
    return f'<ul class="plan">{lis}</ul>'

# ────────────────────────────────────────────────────────────────────────────────
# QUOTE OF THE DAY (TOP)
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

# ────────────────────────────────────────────────────────────────────────────────
# FALLBACK COACH
# ────────────────────────────────────────────────────────────────────────────────
def fallback_coach(note, slot):
    t = note.lower()
    if "exam" in t or "test" in t:
        return {"analysis": "Exam stress: focus, recall, calm.", "plan": ["Review one topic", "Pomodoro 25", "Flashcards"], "mantra": "Small wins compound"}
    elif "stress" in t or "anxious" in t:
        return {"analysis": "Stress detected: simplify and act small.", "plan": ["List your worries", "Do one micro-step", "Remove a distraction"], "mantra": "Begin before you think"}
    else:
        return {"analysis": f"{slot.title()} — keep it clear and doable.", "plan": ["Pick one 10-min task", "Reduce friction", "Start for 5 minutes"], "mantra": "One small step beats zero"}

# ────────────────────────────────────────────────────────────────────────────────
# SENTIMENT RADAR
# ────────────────────────────────────────────────────────────────────────────────
SIA = SentimentIntensityAnalyzer()
def sentiment_radar(note):
    vs = SIA.polarity_scores(note or "")
    return {"Positive": vs["pos"], "Negative": vs["neg"], "Neutral": vs["neu"], "Compound": (vs["compound"]+1)/2}
def radar_chart(scores):
    cats=list(scores.keys()); vals=list(scores.values())+[list(scores.values())[0]]
    fig=go.Figure(go.Scatterpolar(r=vals,theta=cats+[cats[0]],fill='toself',name='Sentiment',
        line=dict(color="#7c3aed"),fillcolor="rgba(124,58,237,.20)"))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True,range=[0,1])),showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",margin=dict(l=20,r=20,t=10,b=10))
    return fig

# ────────────────────────────────────────────────────────────────────────────────
# UI
# ────────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="container">', unsafe_allow_html=True)
# Big title
st.markdown('<div class="bigtitle">DailyUp</div>', unsafe_allow_html=True)
# Quote banner
bq=big_quote_of_the_day()
st.markdown(f"""
<div class="banner">
  <div class="b-label">QUOTE OF THE DAY</div>
  <div class="b-quote">“{html.escape(bq['text'])}”</div>
  <div class="b-author">— {html.escape(bq['author'])} · <span style="opacity:.8">{html.escape(bq['title'])}</span></div>
</div>
""",unsafe_allow_html=True)
# Hero
st.markdown("""
<div class="hero">
  <div class="pill">✨ Micro-Coach</div>
  <div class="title">Tiny nudges. Massive progress.</div>
  <p style="max-width:820px; color:var(--muted); font-size:1.05rem;">
    Tell me your goal or mood. I’ll generate a <b>3-step micro-plan</b> and an inspiring <b>mantra</b> to keep you moving.
  </p>
</div>
""",unsafe_allow_html=True)

# Step 1
st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
st.subheader("Step 1 — Pick your moment")
slot=st.radio("When is this for?",["morning","midday","evening"],horizontal=True)
MOMENT={"morning":["⚡ Energy: fresh start","🎯 Focus: tiny win","🧭 Tone: momentum"],
"midday":["🔄 Reset: re-align","🎯 Focus: single block","🧭 Tone: pragmatic"],
"evening":["🌙 Calm: closure","📝 Reflect: next step","🧭 Tone: serene"]}
info=MOMENT[slot]
st.markdown(f"<div class='moment {slot}'><h4>{slot.title()}</h4><ul>"+ "".join([f'<li>{i}</li>' for i in info])+"</ul></div>",unsafe_allow_html=True)

# Step 2
st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
st.subheader("Step 2 — Tell me your note")
note=st.text_area("What’s on your mind?",placeholder="e.g., I'm stressed about my exam.",height=120)
if note.strip():
    st.markdown("#### Mood radar")
    fig=radar_chart(sentiment_radar(note))
    st.plotly_chart(fig,use_container_width=True)

# Step 3
st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
st.subheader("Step 3 — Analyze & coach me")
if st.button("💬 Analyze & coach me",use_container_width=True):
    result=fallback_coach(note,slot)
    st.success("✅ Your personalized plan is ready!")
    st.markdown("### Analysis"); st.write(result["analysis"])
    st.markdown("### 3-Step Plan"); st.markdown(_format_steps(result["plan"]),unsafe_allow_html=True)
    st.markdown(f"""
    <div class="mantra-box">
      <div class="mantra-text">“{html.escape(result["mantra"])}”</div>
      <div class="mantra-sub">— Your daily focus</div>
    </div>
    """,unsafe_allow_html=True)
st.markdown('</div>',unsafe_allow_html=True)
