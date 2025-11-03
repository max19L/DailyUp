# streamlit_app.py — DailyUp (vertical, colorful & guided)
# Requirements: streamlit>=1.39.0, pandas>=2.2, altair>=5, nltk>=3.9
# Optional: openai>=1.51.0 (only if you set OPENAI_API_KEY)

import os
import time
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Dict, Any

import streamlit as st
import pandas as pd
import altair as alt

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# --- OpenAI optional
OPENAI_OK = False
try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="DailyUp — Live Coach", page_icon="🌈", layout="centered")

# -----------------------------
# THEME / STYLES (high-contrast + colorful + animated buttons)
# -----------------------------
st.markdown(
    """
    <style>
      :root{
        --bg1:#0b1020;
        --bg2:#10172a;
        --card:#12192e;
        --card-border:#2a3655;
        --text:#f7faff;
        --muted:#b5c3dd;
        --accent1:#ff5ea7; /* pink */
        --accent2:#7c3aed; /* violet */
        --accent3:#22d3ee; /* cyan */
        --good:#10b981;
        --bad:#ef4444;
      }
      /* Gradient background */
      .main{
        background: radial-gradient(1000px 600px at 10% 5%, #10203f 0%, transparent 70%),
                    radial-gradient(800px 500px at 90% 10%, #1b2a52 0%, transparent 70%),
                    linear-gradient(180deg, var(--bg1), var(--bg2));
        color:var(--text);
        font-family: Inter, ui-sans-serif, system-ui;
      }
      .wrap{max-width:840px;margin:0 auto;}

      .title{
        font-weight:900; font-size:2.3rem; letter-spacing:.2px; margin:.2rem 0 .5rem;
        background:linear-gradient(90deg,var(--accent1),var(--accent2),var(--accent3));
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      }

      .intro-card, .card{
        background:var(--card); border:1px solid var(--card-border); border-radius:18px;
        padding:18px 18px 14px; box-shadow:0 10px 40px rgba(0,0,0,.45);
      }
      .section-title{font-size:1.15rem;font-weight:800;margin-bottom:.35rem;}
      .hint{color:var(--muted);font-size:.95rem;margin:.15rem 0 .7rem;}

      /* Inputs */
      .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div,
      .stSlider>div>div>div>input{
        background:#0f1730 !important; border:1px solid #2a3655 !important;
        color:var(--text)!important; border-radius:12px!important;
      }
      /* Buttons – animated gradient */
      @keyframes glow {
        0% {box-shadow:0 0 0 rgba(255,94,167,.0)}
        50%{box-shadow:0 10px 35px rgba(124,58,237,.35)}
        100%{box-shadow:0 0 0 rgba(34,211,238,.0)}
      }
      .stButton>button{
        border-radius:12px !important; font-weight:800 !important; letter-spacing:.3px;
        border:1px solid #2a3655 !important; color:#fff !important;
        padding:0.65rem 1rem !important;
        background:linear-gradient(90deg,var(--accent1),var(--accent2),var(--accent3)) !important;
        background-size:200% 200% !important; animation:glow 2.6s ease-in-out infinite;
      }
      .stButton>button:hover{
        filter:brightness(1.08);
        transform: translateY(-1px);
        transition: all .15s ease;
      }

      .chip{
        display:inline-flex; gap:8px; align-items:center; font-weight:700; font-size:.82rem;
        color:white; padding:6px 12px; border-radius:999px; margin-right:6px;
        background:linear-gradient(90deg,var(--accent2),var(--accent3));
        border:1px solid #3a4a75;
      }

      .good{color:var(--good)!important;} .bad{color:var(--bad)!important;}

      .stAlert{border-radius:12px;border:1px solid #2a3655;}

      /* Make everything vertical: remove default column margin tweaks */
      section.main > div { padding-top: 0.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# -----------------------------
# DB SQLite
# -----------------------------
DB_PATH = "dailyup_data.db"

def ensure_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS logs(
               id INTEGER PRIMARY KEY, ts TEXT, slot TEXT, user_text TEXT, tone TEXT,
               sentiment TEXT, score REAL, plan TEXT, mantra TEXT)"""
        )
ensure_db()

def save_log(row: Dict[str, Any]):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute("""INSERT INTO logs(ts,slot,user_text,tone,sentiment,score,plan,mantra)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (row["ts"],row["slot"],row["user_text"],row["tone"],
                     row["sentiment"],row["score"],row["plan"],row["mantra"]))

def read_logs() -> pd.DataFrame:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return pd.read_sql_query("SELECT * FROM logs ORDER BY ts DESC", conn)

# -----------------------------
# Sentiment
# -----------------------------
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")
SIA = SentimentIntensityAnalyzer()

def get_sentiment(text:str)->Dict[str,Any]:
    if not text.strip():
        return {"label":"NEUTRAL","score":0.0}
    s=SIA.polarity_scores(text)["compound"]
    label="POSITIVE" if s>=.15 else ("NEGATIVE" if s<=-.15 else "NEUTRAL")
    return {"label":label,"score":float(s)}

# -----------------------------
# OpenAI (optionnel)
# -----------------------------
def openai_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if OPENAI_OK and key:
        return OpenAI(api_key=key)
    return None

def coach_reply(user_text:str, slot:str, tone:str)->Dict[str,str]:
    client=openai_client()
    prompt=f"""You are a concise, uplifting micro-coach for productivity.

User note: "{user_text}"
Time window: {slot}
Preferred tone: {tone}

Produce:
1) A numbered 3-step MICRO plan.
2) A 3–5 word mantra (no quotes)."""

    if client:
        try:
            r=client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"You are DailyUp, kind and practical."},
                          {"role":"user","content":prompt}],
                temperature=0.4,
            )
            text=r.choices[0].message.content.strip()
            mantra="Small wins compound"
            for line in text.splitlines()[::-1]:
                line=line.strip("-•* ").strip()
                if 2<=len(line.split())<=6 and len(line)<=40:
                    mantra=line; break
            return {"plan":text,"mantra":mantra}
        except Exception:
            st.info("OpenAI unreachable — using fallback.", icon="⚠️")

    fall={
        "morning": ["Pick one priority","10-min warm start","Remove one distraction"],
        "midday":  ["Clarify next tiny step","10-min deep dive","Close one distraction"],
        "evening": ["Log a win","Set the first step","Prep tomorrow"]
    }.get(slot,["Pick one priority","10-min start","Close distractions"])
    return {"plan":f"1) {fall[0]}\n2) {fall[1]}\n3) {fall[2]}", "mantra":"Begin before you think"}

# -----------------------------
# Session state
# -----------------------------
if "timer_running" not in st.session_state: st.session_state.timer_running=False
if "timer_end" not in st.session_state:     st.session_state.timer_end=None
if "prompt" not in st.session_state:        st.session_state.prompt=""

# -----------------------------
# HEADER + INTRO (clear purpose)
# -----------------------------
st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="title">DailyUp — Live Coach</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="intro-card">
      <div class="section-title">What is this app?</div>
      <div class="hint">
        DailyUp is a <b>mini productivity coach</b>. In a few lines, it turns your check-in into
        a <b>3-step micro-plan</b> + a short <b>mantra</b>. Start a brief focus timer and watch your mood trend
        in the dashboard.<br><br>
        <b>Why it works:</b> tiny steps are easier to start, and starting is how momentum begins.
      </div>
      <span class="chip">1️⃣ Check-in</span>
      <span class="chip">2️⃣ Get micro-plan</span>
      <span class="chip">3️⃣ Focus timer</span>
      <span class="chip">4️⃣ See progress</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")  # small spacer

# -----------------------------
# Step 0 — Global Settings (vertical)
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">General settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Pick your moment and the coach style you prefer.</div>', unsafe_allow_html=True)

    # 100% vertical flow (no columns)
    slot = st.segmented_control("Time window", ["morning","midday","evening"], default="morning")
    tone = st.selectbox("Coach tone", ["neutral","encouraging","challenging","calm"], index=0)
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# -----------------------------
# Step 1 — Check-in
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 1 — Check-in</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Tell me your main goal or how you feel. One sentence is enough.</div>', unsafe_allow_html=True)

    user_text = st.text_area(
        "What’s on your mind right now?",
        placeholder="Example: “I’m procrastinating on my report” or “I feel low energy, need a jump-start.”",
        height=110
    )
    if st.button("Suggest a nudge"):
        st.session_state.prompt = {
            "morning": "Morning Boost — one small step beats zero.",
            "midday":  "Midday Check-in — keep momentum with a tiny step.",
            "evening": "Evening Wrap — log a win, prep tomorrow."
        }.get(slot, "What’s one tiny step now?")
    st.caption(f"Prompt: _{st.session_state.prompt or '— click “Suggest a nudge” to get one.'}_")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# -----------------------------
# Step 2 — Coach nudge (plan + mantra)
# -----------------------------
sentiment_label, sentiment_score, plan, mantra = "n/a", 0.0, "", ""

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 2 — Get your micro-plan</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">I’ll analyze your note, suggest 3 tiny steps and give a short mantra to keep you focused.</div>', unsafe_allow_html=True)

    if st.button("Generate micro-plan"):
        with st.spinner("Coaching…"):
            s = get_sentiment(user_text)
            out = coach_reply(user_text=user_text, slot=slot, tone=tone)
            sentiment_label, sentiment_score = s["label"], s["score"]
            plan, mantra = out["plan"], out["mantra"]

            save_log({
                "ts": datetime.utcnow().isoformat(),
                "slot": slot, "user_text": user_text, "tone": tone,
                "sentiment": sentiment_label, "score": sentiment_score,
                "plan": plan, "mantra": mantra,
            })
        st.success("Micro-plan ready. Move to Step 3 when you’re set.", icon="✅")

    colour = "good" if sentiment_score>=.15 else ("bad" if sentiment_score<=-.15 else "muted")
    st.markdown(f"**Sentiment:** <span class='{colour}'>{sentiment_label} ({sentiment_score:.2f})</span>", unsafe_allow_html=True)
    st.markdown(f"**Mantra:** _{mantra or '— will appear here'}_")
    st.markdown("**Plan:**")
    st.write(plan or "Your plan will appear here once generated.")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# -----------------------------
# Step 3 — Focus timer
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 3 — Focus burst</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Set a short timer (5–45 min). The goal is to start. When time is up, log a tiny win.</div>', unsafe_allow_html=True)

    duration = st.slider("Duration (minutes)", 5, 45, 10, 5)
    if not st.session_state.timer_running and st.button("Start focus"):
        st.session_state.timer_running=True
        st.session_state.timer_end=datetime.utcnow()+timedelta(minutes=duration)
    if st.session_state.timer_running and st.button("Stop"):
        st.session_state.timer_running=False
        st.session_state.timer_end=None

    if st.session_state.timer_running:
        remaining=(st.session_state.timer_end-datetime.utcnow()).total_seconds()
        if remaining<=0:
            st.session_state.timer_running=False
            st.session_state.timer_end=None
            st.success("⏰ Time’s up — nice work! Log your win in Step 4.")
        else:
            m=int(remaining//60); s=int(remaining%60)
            st.metric("Remaining", f"{m:02d}:{s:02d}")
            time.sleep(0.6); st.experimental_rerun()
    else:
        st.caption("Timer is idle.")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# -----------------------------
# Step 4 — Progress dashboard
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 4 — Progress</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Your recent sentiment and mantras. Aim for small, steady improvements.</div>', unsafe_allow_html=True)

    df = read_logs()
    if df.empty:
        st.caption("No entries yet — generate your first micro-plan above.")
    else:
        df["ts"]=pd.to_datetime(df["ts"])
        df=df.sort_values("ts")
        chart=alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("ts:T", title="Time"),
            y=alt.Y("score:Q", title="Sentiment (VADER)"),
            color=alt.value("#22d3ee")
        ).properties(height=240)
        st.altair_chart(chart, use_container_width=True)

        st.markdown("**Recent log**")
        show=df.tail(6)[["ts","slot","sentiment","score","mantra"]]
        show.columns=["Time","Slot","Sentiment","Score","Mantra"]
        st.dataframe(show, hide_index=True, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Built with ❤️ — DailyUp")
st.markdown('</div>', unsafe_allow_html=True)  # wrap
