# streamlit_app.py — DailyUp (strict vertical flow + smarter AI)
# Requirements: streamlit>=1.39.0, pandas>=2.2, altair>=5, nltk>=3.9
# Optional: openai>=1.51.0 (if you set OPENAI_API_KEY)

import os
import re
import time
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from typing import Dict, Any, List

import streamlit as st
import pandas as pd
import altair as alt

import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# ------------- Optional OpenAI client
OPENAI_OK = False
try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False

# ------------- Page config
st.set_page_config(page_title="DailyUp — Live Coach", page_icon="🌈", layout="centered")

# ------------- Theme / CSS
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

      .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background:#0f1730 !important; border:1px solid #2a3655 !important;
        color:var(--text)!important; border-radius:12px!important;
      }

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
      .stButton>button:hover{filter:brightness(1.08); transform: translateY(-1px); transition: all .15s ease;}

      .chip{
        display:inline-flex; gap:8px; align-items:center; font-weight:700; font-size:.82rem;
        color:white; padding:6px 12px; border-radius:999px; margin-right:6px;
        background:linear-gradient(90deg,var(--accent2),var(--accent3));
        border:1px solid #3a4a75;
      }
      .good{color:var(--good)!important;} .bad{color:var(--bad)!important;}
      .stAlert{border-radius:12px;border:1px solid #2a3655;}
      section.main > div { padding-top: 0.35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ------------- DB (SQLite)
DB_PATH = "dailyup_data.db"

def ensure_db():
    with closing(sqlite3.connect(DB_PATH)) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS logs(
               id INTEGER PRIMARY KEY, ts TEXT, slot TEXT, user_text TEXT, tone TEXT,
               sentiment TEXT, score REAL, plan TEXT, mantra TEXT, analysis TEXT)"""
        )
ensure_db()

def save_log(row: Dict[str, Any]):
    with closing(sqlite3.connect(DB_PATH)) as conn, conn, closing(conn.cursor()) as cur:
        cur.execute("""INSERT INTO logs(ts,slot,user_text,tone,sentiment,score,plan,mantra,analysis)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (row["ts"],row["slot"],row["user_text"],row["tone"],row["sentiment"],
                     row["score"],row["plan"],row["mantra"],row["analysis"]))

def read_logs() -> pd.DataFrame:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        return pd.read_sql_query("SELECT * FROM logs ORDER BY ts DESC", conn)

# ------------- Sentiment
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

# ------------- OpenAI helper
def openai_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if OPENAI_OK and key:
        return OpenAI(api_key=key)
    return None

SYSTEM_PROMPT = (
    "You are DailyUp, a concise, encouraging micro-coach. Always be specific and actionable. "
    "Keep language simple and supportive. Use the provided slot (morning/midday/evening) to adapt tone."
)

def ask_llm(user_text:str, slot:str, tone:str)->Dict[str,str]:
    """
    Ask the model to return strict JSON so we can parse safely.
    """
    client=openai_client()
    if not client:
        raise RuntimeError("OpenAI not configured")

    user_prompt = f"""
Analyze the user's note and produce a tailored micro-coaching response in JSON.

User note: {user_text}
Time window: {slot}
Preferred tone: {tone}

Rules:
- Keep 'analysis' to 2 short sentences (what they mean / what's blocking).
- 'plan_steps' must be exactly 3 short, concrete steps (micro, 1 sentence each).
- 'mantra' must be 3-5 words. No quotes, no punctuation.
- Be highly specific to the user's content. Avoid generic advice.

Return ONLY valid JSON with keys:
{{
  "analysis": "...",
  "plan_steps": ["...", "...", "..."],
  "mantra": "..."
}}
    """.strip()

    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user","content":user_prompt}],
        temperature=0.4,
    )
    text=r.choices[0].message.content.strip()

    # Extract JSON block robustly
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        # fallback parse: put everything in analysis
        return {"analysis": text[:240], "plan_steps": ["Pick one tiny step","Work 10 minutes","Reduce one distraction"], "mantra":"Small wins compound"}

    import json
    try:
        data=json.loads(match.group(0))
        steps=data.get("plan_steps") or []
        if len(steps)<3:
            steps = (steps + ["Pick one tiny step","Work 10 minutes","Reduce one distraction"])[:3]
        return {
            "analysis": data.get("analysis",""),
            "plan_steps": steps,
            "mantra": data.get("mantra","Small wins compound")
        }
    except Exception:
        return {"analysis": text[:240], "plan_steps": ["Pick one tiny step","Work 10 minutes","Reduce one distraction"], "mantra":"Small wins compound"}

# ------------- Smarter local fallback (no API key)
NEGATIVE_HINTS = [
    ("procrastinate","Do a 2-minute start with a timer."),
    ("anxious","Breathe 4-4-6 for 60s before starting."),
    ("tired","Drink water and set a 5-min warm-up."),
    ("overwhelmed","Write the next micro-task on a sticky note."),
    ("stuck","Open the file and write one sentence."),
    ("sad","Move your body for 60 seconds before task."),
]

def smart_fallback(user_text:str, slot:str)->Dict[str,str]:
    text=user_text.lower()
    hits=[h for k,h in NEGATIVE_HINTS if k in text]
    # keyword extraction (very simple noun-ish tokens)
    words=re.findall(r"[a-zA-Z]{4,}", text)
    top = ", ".join(words[:3]) if words else "your task"

    openings={
        "morning":"Fresh start — build momentum.",
        "midday":"Midday nudge — keep it light.",
        "evening":"Wind down — finish small."
    }
    opening=openings.get(slot,"Small step now.")

    steps=["Open the exact place you'll work (file/URL/notebook).",
           f"Do a 10-minute focused burst on {top}.",
           "Reduce one distraction (mute, close 1 tab, put phone away)."]

    if hits:
        steps[0]=hits[0]

    return {
        "analysis": f"{opening} I hear a specific blocker. Let’s remove friction and begin tiny.",
        "plan_steps": steps,
        "mantra": "Begin before you think"
    }

# ------------- Session
if "slot" not in st.session_state: st.session_state.slot="morning"
if "user_text" not in st.session_state: st.session_state.user_text=""
if "result" not in st.session_state: st.session_state.result=None
if "timer_running" not in st.session_state: st.session_state.timer_running=False
if "timer_end" not in st.session_state: st.session_state.timer_end=None

# ------------- Header & intro
st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="title">DailyUp — Live Coach</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="intro-card">
      <div class="section-title">How to use this</div>
      <div class="hint">
        1) Pick your moment (<b>morning/midday/evening</b>) to get the right nudge.<br>
        2) Tell me what's happening.<br>
        3) Hit <b>Analyze & coach me</b>. You’ll get a <b>2-line analysis</b>, a <b>3-step micro-plan</b>, and a short <b>mantra</b> tailored to your note.
      </div>
      <span class="chip">1️⃣ Pick moment</span>
      <span class="chip">2️⃣ Write</span>
      <span class="chip">3️⃣ Analyze & Plan</span>
      <span class="chip">4️⃣ Focus</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# ------------- STEP 1 — PICK PROMPT FIRST
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 1 — Pick your moment</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Choose when you are checking in. The prompt below adapts.</div>', unsafe_allow_html=True)

    slot = st.segmented_control("Time window", ["morning","midday","evening"], default=st.session_state.slot)
    st.session_state.slot = slot

    nudges = {
        "morning": "Morning Boost — what’s your first tiny win?",
        "midday":  "Midday Nudge — quick check-in: any blocker?",
        "evening": "Evening Wrap — one small win + prep tomorrow."
    }
    st.caption(f"Prompt: _{nudges[slot]}_")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ------------- STEP 2 — USER WRITES
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 2 — Write what’s going on</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">One or two sentences are enough. Be concrete so the coach can be specific.</div>', unsafe_allow_html=True)

    st.session_state.user_text = st.text_area(
        "Your note",
        value=st.session_state.user_text,
        placeholder="Example: “I keep procrastinating my report and feel low energy.”",
        height=100,
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ------------- STEP 3 — ANALYZE & COACH
analysis, plan_steps, mantra = "", [], ""
sentiment_label, sentiment_score = "n/a", 0.0

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 3 — Analyze & coach me</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">I’ll analyze your note and produce a tailored 3-step plan. This uses AI if a key is set, otherwise a smarter fallback.</div>', unsafe_allow_html=True)

    disabled = not st.session_state.user_text.strip()
    if st.button("Analyze & coach me", disabled=disabled):
        with st.spinner("Thinking…"):
            # sentiment
            s = get_sentiment(st.session_state.user_text)
            sentiment_label, sentiment_score = s["label"], s["score"]

            # AI or fallback
            try:
                out = ask_llm(st.session_state.user_text, st.session_state.slot, "neutral")
            except Exception:
                out = smart_fallback(st.session_state.user_text, st.session_state.slot)

            analysis, plan_steps, mantra = out["analysis"], out["plan_steps"], out["mantra"]

            save_log({
                "ts": datetime.utcnow().isoformat(),
                "slot": st.session_state.slot,
                "user_text": st.session_state.user_text,
                "tone":"neutral",
                "sentiment": sentiment_label,
                "score": sentiment_score,
                "plan": "\n".join(plan_steps),
                "mantra": mantra,
                "analysis": analysis,
            })
        st.success("Your plan is ready. See below.")

    # Show current (last) result from DB to persist across reruns
    df_last = read_logs()
    if not df_last.empty:
        row = df_last.iloc[0]
        sentiment_label = row["sentiment"]; sentiment_score = row["score"]
        analysis = row["analysis"]; mantra = row["mantra"]
        plan_steps = (row["plan"].splitlines() if row["plan"] else [])

    color = "good" if sentiment_score>=.15 else ("bad" if sentiment_score<=-.15 else "muted")
    st.markdown(f"**Sentiment:** <span class='{color}'>{sentiment_label} ({sentiment_score:.2f})</span>", unsafe_allow_html=True)
    st.markdown("**Analysis:** " + (analysis or "_(will appear here)_"))
    st.markdown("**Plan:**")
    if plan_steps:
        st.write(f"1) {plan_steps[0]}\n2) {plan_steps[1]}\n3) {plan_steps[2]}")
    else:
        st.caption("No plan yet — press **Analyze & coach me**.")
    st.markdown(f"**Mantra:** _{mantra or '—'}_")

    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ------------- STEP 4 — OPTIONAL FOCUS TIMER
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 4 — Focus burst (optional)</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Do a short burst (5–45 min). Starting small builds momentum.</div>', unsafe_allow_html=True)

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
            st.success("⏰ Time’s up — great job! Log your win below.")
        else:
            m=int(remaining//60); s=int(remaining%60)
            st.metric("Remaining", f"{m:02d}:{s:02d}")
            time.sleep(0.6); st.experimental_rerun()
    else:
        st.caption("Timer is idle.")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ------------- STEP 5 — PROGRESS
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 5 — Progress</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Recent sentiment and mantras. Aim for tiny, steady improvements.</div>', unsafe_allow_html=True)

    df = read_logs()
    if df.empty:
        st.caption("No entries yet.")
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
st.markdown('</div>', unsafe_allow_html=True)
