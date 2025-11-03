# streamlit_app.py
# DailyUp — small nudges, big progress.
# Features: beautiful UI, AI coach (OpenAI w/ fallback), dashboard, chat, focus timer, local SQLite logging

import os
import time
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import List, Dict, Any

import streamlit as st
import pandas as pd
import altair as alt

# Sentiment (lightweight, Py3.13-friendly)
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Optional AI (OpenAI) — only if key provided
OPENAI_OK = False
try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False


# -----------------------------
# App Config & Styling
# -----------------------------
st.set_page_config(
    page_title="DailyUp — Live Coach",
    page_icon="🌞",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get help": None, "Report a bug": None, "About": "DailyUp • Small nudges, big progress."},
)

# Global CSS (glassmorphism + neon accents, minimal + futuristic)
st.markdown(
    """
    <style>
      :root {
        --bg1: #0e1117;
        --card-glass: rgba(255,255,255,0.06);
        --card-border: rgba(255,255,255,0.15);
        --accent: #7c3aed;            /* violet */
        --accent-2: #22d3ee;          /* cyan */
        --text: #e5e7eb;
        --muted: #9ca3af;
        --good: #34d399;              /* green */
        --bad:  #f43f5e;              /* rose */
      }

      .main {
        background: radial-gradient(1200px 1200px at 80% -10%, #1f2937 0%, #0e1117 55%);
        color: var(--text);
        font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, "Helvetica Neue", Arial;
      }

      .glass {
        background: var(--card-glass);
        border: 1px solid var(--card-border);
        box-shadow: 0 8px 28px rgba(0,0,0,0.35), 0 1px 0 rgba(255,255,255,0.08) inset;
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 18px 20px;
      }

      .headline {
        font-size: 2.1rem; font-weight: 800; letter-spacing: .2px;
        color: #fff; margin-bottom: .25rem;
      }

      .tagline {
        color: var(--muted); margin-top: .2rem;
      }

      .chip {
        display:inline-flex; align-items:center; gap:8px;
        background: linear-gradient(90deg, var(--accent), var(--accent-2));
        color:white; padding:6px 12px; border-radius:999px; font-size:.85rem; font-weight:600;
        box-shadow: 0 8px 24px rgba(34,211,238,0.22);
      }

      .neon-title {
        text-shadow: 0 0 14px rgba(124,58,237,.55), 0 0 28px rgba(34,211,238,.35);
      }

      .metric-good { color: var(--good); }
      .metric-bad  { color: var(--bad); }
      .muted { color: var(--muted); }

      /* Streamlit element tweaks */
      .stButton>button {
        border-radius: 999px !important;
        padding: .6rem 1.1rem !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        background: linear-gradient(90deg, #4c1d95, #0ea5e9) !important;
        color: #fff !important;
      }
      .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background: rgba(255,255,255,0.02) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        color: #e5e7eb !important;
      }
      .small { font-size:.88rem; }
    </style>
    """, unsafe_allow_html=True
)

# -----------------------------
# Light persistence (SQLite)
# -----------------------------
DB_PATH = "dailyup_data.db"

def _ensure_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs (
              id INTEGER PRIMARY KEY,
              ts TEXT,
              slot TEXT,
              user_text TEXT,
              tone TEXT,
              sentiment TEXT,
              score REAL,
              plan TEXT,
              mantra TEXT
            )
        """)
_ensure_db()

def save_log(row: Dict[str, Any]):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute("""
            INSERT INTO logs (ts, slot, user_text, tone, sentiment, score, plan, mantra)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (row["ts"], row["slot"], row["user_text"], row["tone"], row["sentiment"], row["score"], row["plan"], row["mantra"]))

def read_logs() -> pd.DataFrame:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        df = pd.read_sql_query("SELECT * FROM logs ORDER BY ts DESC", conn)
    return df

# -----------------------------
# Sentiment (VADER)
# -----------------------------
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

SIA = SentimentIntensityAnalyzer()

def get_sentiment(text: str) -> Dict[str, Any]:
    if not text.strip():
        return {"label": "NEUTRAL", "score": 0.0}
    s = SIA.polarity_scores(text)["compound"]
    label = "POSITIVE" if s >= 0.15 else ("NEGATIVE" if s <= -0.15 else "NEUTRAL")
    return {"label": label, "score": float(s)}

# -----------------------------
# AI Coach (OpenAI or Fallback)
# -----------------------------
def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if OPENAI_OK and api_key:
        return OpenAI(api_key=api_key)
    return None

def generate_ai_coach_reply(user_text: str, slot: str, tone: str) -> Dict[str, str]:
    """
    Return dict with keys: plan, mantra
    Uses OpenAI if key is present; otherwise returns a simple deterministic fallback.
    """
    client = get_openai_client()
    prompt = f"""
You are a concise, kind productivity coach.

Context:
- User wrote: "{user_text}"
- Time window: {slot}
- Desired tone: {tone}

Task:
1) Return a *3-step micro-plan* using a numbered list.
2) Return a short *mantra* (3-5 words, no quotes).
Be brief, friendly, and practical.
"""

    if client:
        try:
            # Small, fast model (adjust if needed)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are DailyUp, a minimalist productivity coach."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.4,
            )
            text = resp.choices[0].message.content.strip()
            # Heuristic split: assume plan first, mantra last line
            plan = text
            mantra = "Small wins compound"
            for line in text.splitlines()[::-1]:
                line = line.strip(" -•*").strip()
                if 2 <= len(line.split()) <= 6 and len(line) <= 40:
                    mantra = line
                    break
            return {"plan": plan, "mantra": mantra}
        except Exception as e:
            st.toast(f"Using fallback coach (API error).", icon="⚠️")

    # Fallback plan (no API)
    slot_hint = {
        "morning":  "Pick one priority • 10-min warm start • Remove distractions",
        "midday":   "Clarify next tiny step • 10-min deep dive • Close one distraction",
        "evening":  "Recap one win • Set next first step • Prep tomorrow",
    }.get(slot, "Pick one priority • 10-min start • Close distractions")

    return {
        "plan": f"""1) {slot_hint.split('•')[0].strip()}
2) {slot_hint.split('•')[1].strip()}
3) {slot_hint.split('•')[2].strip()}""",
        "mantra": "Begin before you think",
    }

# -----------------------------
# State init
# -----------------------------
if "timer_running" not in st.session_state:
    st.session_state.timer_running = False
if "timer_end" not in st.session_state:
    st.session_state.timer_end = None

# -----------------------------
# Header
# -----------------------------
left, right = st.columns([0.75, 0.25])
with left:
    st.markdown('<div class="headline neon-title">🌞 DailyUp</div>', unsafe_allow_html=True)
    st.caption("Small nudges, big progress.")
with right:
    st.markdown('<div style="text-align:right;margin-top:10px;"><span class="chip">Live Coach</span></div>', unsafe_allow_html=True)
st.write("")

# -----------------------------
# Sidebar — Settings
# -----------------------------
with st.sidebar:
    st.markdown("### Coach settings")
    slot = st.segmented_control("Select your time", options=["morning", "midday", "evening"], default="morning")
    tone = st.selectbox("Coach tone (override)", ["neutral", "encouraging", "challenging", "calm"], index=0)
    st.markdown("---")
    st.markdown("### Export / Data")
    if st.button("Download CSV"):
        df = read_logs()
        st.download_button("Download data.csv", df.to_csv(index=False), "dailyup_logs.csv", mime="text/csv")

# -----------------------------
# Layout: Coach + Right panel
# -----------------------------
col_left, col_right = st.columns([0.58, 0.42], gap="large")

# === Left: Prompt + Coach
with col_left:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("Coach desk", divider="blue")
    user_text = st.text_area("What's up?", placeholder="Tell me how you're doing or your main goal...", height=96)

    c1, c2 = st.columns([0.4, 0.6])
    with c1:
        get_btn = st.button("Get prompt")
    with c2:
        send_btn = st.button("Send reply")

    sentiment_label = "n/a"
    sentiment_score = 0.0
    plan, mantra = "", ""

    if get_btn:
        with st.spinner("Analyzing…"):
            # Generate a fresh prompt (mood poke)
            prompts = {
                "morning": "Morning Boost — One small step today beats zero.",
                "midday": "Midday Check-in — Tiny steps keep momentum.",
                "evening": "Evening Wrap — Log one win, prep tomorrow.",
            }
            st.session_state["prompt_block"] = prompts.get(slot, "What's one small step now?")
        st.success("Prompt generated ↓")

    st.markdown("###### Prompt")
    st.write(st.session_state.get("prompt_block", "Click **Get prompt** to receive a nudge."))

    if send_btn:
        with st.spinner("Coaching…"):
            s = get_sentiment(user_text)
            ai = generate_ai_coach_reply(user_text, slot, tone)
            sentiment_label, sentiment_score = s["label"], s["score"]
            plan, mantra = ai["plan"], ai["mantra"]

            log_row = {
                "ts": datetime.utcnow().isoformat(),
                "slot": slot,
                "user_text": user_text,
                "tone": tone,
                "sentiment": sentiment_label,
                "score": sentiment_score,
                "plan": plan,
                "mantra": mantra,
            }
            save_log(log_row)

    # Metrics area
    m1, m2 = st.columns(2)
    with m1:
        klass = "metric-good" if sentiment_score >= 0.15 else ("metric-bad" if sentiment_score <= -0.15 else "muted")
        st.markdown(f"**Sentiment:** <span class='{klass}'>{sentiment_label} ({sentiment_score:.2f})</span>", unsafe_allow_html=True)
    with m2:
        if mantra:
            st.markdown(f"**Mantra:** _{mantra}_")
        else:
            st.markdown("**Mantra:** —")

    st.markdown("###### Coach plan")
    st.write(plan if plan else "Your plan will appear here after **Send reply**")
    st.markdown('</div>', unsafe_allow_html=True)

# === Right: Timer + Dashboard
with col_right:
    st.markdown('<div class="glass">', unsafe_allow_html=True)
    st.subheader("Focus timer", divider="blue")

    dur = st.slider("Duration (minutes)", 5, 45, 10, 5)
    colA, colB = st.columns(2)
    with colA:
        if not st.session_state.timer_running and st.button("Start"):
            st.session_state.timer_running = True
            st.session_state.timer_end = datetime.utcnow() + timedelta(minutes=dur)
        if st.session_state.timer_running and st.button("Stop"):
            st.session_state.timer_running = False
            st.session_state.timer_end = None
    with colB:
        if st.session_state.timer_running:
            remaining = (st.session_state.timer_end - datetime.utcnow()).total_seconds()
            if remaining <= 0:
                st.session_state.timer_running = False
                st.session_state.timer_end = None
                st.success("⏰ Time’s up! Great job.")
            else:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                st.metric("Remaining", f"{mins:02d}:{secs:02d}")

                # Tiny live update
                time.sleep(0.6)
                st.experimental_rerun()
        else:
            st.caption("Timer is idle.")

    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="glass" style="margin-top:16px;">', unsafe_allow_html=True)
    st.subheader("Progress dashboard", divider="blue")
    df = read_logs()
    if df.empty:
        st.caption("No entries yet — send a reply to start logging.")
    else:
        df["ts"] = pd.to_datetime(df["ts"])
        df_plot = df.sort_values("ts")
        # Sentiment line
        chart = alt.Chart(df_plot).mark_line(point=True).encode(
            x=alt.X("ts:T", title="Time"),
            y=alt.Y("score:Q", title="Sentiment (VADER)"),
            color=alt.value("#22d3ee")
        ).properties(height=220)
        st.altair_chart(chart, use_container_width=True)

        # Recent logs
        st.markdown("##### Recent log")
        show = df_plot.tail(6)[["ts","slot","sentiment","score","mantra"]]
        show.columns = ["Time", "Slot", "Sentiment", "Score", "Mantra"]
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.markdown('</div>', unsafe_allow_html=True)

# Footer note
st.caption("Built with ❤️ • DailyUp")
