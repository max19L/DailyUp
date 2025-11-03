# streamlit_app.py — DailyUp (vertical, high-contrast, guided UX)

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

# OpenAI optionnel
OPENAI_OK = False
try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False

# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="DailyUp — Live Coach",
    page_icon="🌞",
    layout="centered",
)

# -----------------------------
# Styles (contraste + vertical)
# -----------------------------
st.markdown(
    """
    <style>
      :root{
        --bg:#0b0e14;
        --card:#151a23;  /* plus opaque que le verre, meilleur contraste */
        --card-border:#2b3342;
        --text:#eef2ff;  /* texte clair */
        --muted:#a3b2c7;
        --accent:#7c3aed; /* violet */
        --accent2:#22d3ee;/* cyan  */
        --green:#10b981;
        --red:#ef4444;
      }
      .main{background:linear-gradient(180deg,#0b0e14 0%, #0b0e14 60%, #0f1420 100%);
            color:var(--text); font-family:Inter, ui-sans-serif, system-ui;}
      .wrap{max-width:880px;margin:0 auto;}
      .card{background:var(--card); border:1px solid var(--card-border); border-radius:16px;
            padding:18px 18px 14px; box-shadow:0 8px 30px rgba(0,0,0,.38);}
      .title{font-weight:800;font-size:2.1rem;letter-spacing:.2px;margin:.2rem 0 .1rem;}
      .tag{display:inline-flex;gap:8px;align-items:center;font-weight:600;font-size:.85rem;
           color:white;padding:6px 12px;border-radius:999px;
           background:linear-gradient(90deg,var(--accent),var(--accent2));
           box-shadow:0 8px 26px rgba(34,211,238,.22);}
      .muted{color:var(--muted);}
      .section-title{font-size:1.1rem;font-weight:700;margin-bottom:.25rem;}
      .hint{color:var(--muted);font-size:.95rem;margin:.15rem 0 .6rem;}
      .good{color:var(--green)!important;} .bad{color:var(--red)!important;}
      /* Champs plus lisibles */
      .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background:#0f1420 !important; border:1px solid #2b3342 !important;
        color:var(--text)!important; border-radius:12px!important;
      }
      .stButton>button{
        border-radius:12px !important; font-weight:700 !important;
        border:1px solid #2b3342 !important; color:#fff !important;
        background:linear-gradient(90deg,#4c1d95,#0ea5e9) !important;
      }
      /* callouts streamlit plus lisibles */
      .stAlert{border-radius:12px;border:1px solid #2b3342;}
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
    prompt=f"""You are a concise, kind productivity coach.

Context
- User: "{user_text}"
- Time window: {slot}
- Tone: {tone}

Deliver:
1) A three-step micro plan (numbered list).
2) A short mantra (3–5 words, no quotes)."""

    if client:
        try:
            r=client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"You are DailyUp."},
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
        "evening": ["Log a win","Set the very first step","Prep for tomorrow"]
    }.get(slot,["Pick one priority","10-min start","Close distractions"])
    return {"plan":f"1) {fall[0]}\n2) {fall[1]}\n3) {fall[2]}", "mantra":"Begin before you think"}

# -----------------------------
# Session state
# -----------------------------
if "timer_running" not in st.session_state: st.session_state.timer_running=False
if "timer_end" not in st.session_state:     st.session_state.timer_end=None
if "prompt" not in st.session_state:        st.session_state.prompt=""

# -----------------------------
# Header (vertical)
# -----------------------------
st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="title">🌞 DailyUp</div>', unsafe_allow_html=True)
st.caption("Tiny nudges, massive progress.")

st.info("**How it works — 4 quick steps**\n\n"
        "1) _Check-in_ — tell me how you feel or your main goal.\n\n"
        "2) _Get a coach nudge_ — I’ll generate a tiny plan + mantra.\n\n"
        "3) _Focus_ — start a short timer to execute one step.\n\n"
        "4) _Track_ — watch your trend in the dashboard.\n\n"
        "Tip: choose the time window and tone that fit your moment.",
        icon="💡")

# -----------------------------
# Step 0 — Global settings (dans la page, pas de sidebar)
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Global settings</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Pick your time window and your preferred coach style.</div>', unsafe_allow_html=True)

    colA, colB = st.columns(2)
    with colA:
        slot = st.segmented_control("Time window", ["morning","midday","evening"], default="morning")
    with colB:
        tone = st.selectbox("Coach tone", ["neutral","encouraging","challenging","calm"], index=0)
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# -----------------------------
# Step 1 — Check-in (vertical)
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 1 — Check-in</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">One sentence is enough. Example: “I’m stuck starting my report.”</div>', unsafe_allow_html=True)

    user_text = st.text_area("What’s on your mind?",
                             placeholder="Say how you’re doing or your main target for this session…",
                             height=100)

    c1, c2 = st.columns([0.45, 0.55])
    with c1:
        if st.button("Suggest a nudge"):
            nudges = {
                "morning": "Morning Boost — one small step beats zero.",
                "midday":  "Midday Check-in — keep momentum with a tiny step.",
                "evening": "Evening Wrap — log a win, prep tomorrow."
            }
            st.session_state.prompt = nudges.get(slot, "What’s one tiny step now?")
    with c2:
        st.caption(f"Prompt: _{st.session_state.prompt or '— click “Suggest a nudge” to get one.'}_")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# -----------------------------
# Step 2 — Coach nudge (plan + mantra)
# -----------------------------
sentiment_label, sentiment_score, plan, mantra = "n/a", 0.0, "", ""

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 2 — Coach nudge</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">I’ll analyze your note, generate a 3-step micro-plan and give you a short mantra.</div>', unsafe_allow_html=True)

    if st.button("Get my micro-plan"):
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
        st.success("Plan generated. Scroll to Step 3 when you’re ready.", icon="✅")

    # Metrics (lisibles)
    col1, col2 = st.columns(2)
    with col1:
        colour = "good" if sentiment_score>=.15 else ("bad" if sentiment_score<=-.15 else "muted")
        st.markdown(f"**Sentiment:** <span class='{colour}'>{sentiment_label} ({sentiment_score:.2f})</span>",
                    unsafe_allow_html=True)
    with col2:
        st.markdown(f"**Mantra:** _{mantra or '— will appear here'}_")

    st.markdown("**Micro-plan**")
    st.write(plan or "Your plan will appear here once generated.")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# -----------------------------
# Step 3 — Focus timer
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 3 — Focus</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Pick a short burst (5–45 min). The goal is to start, not to be perfect.</div>', unsafe_allow_html=True)

    duration = st.slider("Duration (minutes)", 5, 45, 10, 5)
    cA, cB = st.columns(2)
    with cA:
        if not st.session_state.timer_running and st.button("Start focus"):
            st.session_state.timer_running=True
            st.session_state.timer_end=datetime.utcnow()+timedelta(minutes=duration)
        if st.session_state.timer_running and st.button("Stop"):
            st.session_state.timer_running=False
            st.session_state.timer_end=None
    with cB:
        if st.session_state.timer_running:
            remaining=(st.session_state.timer_end-datetime.utcnow()).total_seconds()
            if remaining<=0:
                st.session_state.timer_running=False
                st.session_state.timer_end=None
                st.success("⏰ Time’s up — nice work!")
            else:
                m=int(remaining//60); s=int(remaining%60)
                st.metric("Remaining", f"{m:02d}:{s:02d}")
                time.sleep(0.6); st.experimental_rerun()
        else:
            st.caption("Timer is idle.")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# -----------------------------
# Step 4 — Progress dashboard
# -----------------------------
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 4 — Progress dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">Your recent sentiment and mantras. Aim for steady, small improvements.</div>', unsafe_allow_html=True)

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
