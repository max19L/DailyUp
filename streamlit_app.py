# streamlit_app.py — DailyUp (fixed KeyError + white intro + guided placeholders)

import os
import re
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

# Optional OpenAI
OPENAI_OK = False
try:
    from openai import OpenAI
    OPENAI_OK = True
except Exception:
    OPENAI_OK = False


# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="DailyUp — Live Coach", page_icon="🌈", layout="centered")

# ====================== CSS ======================
st.markdown(
    """
    <style>
      :root{
        --bg1:#0b1020; --bg2:#10172a; --card:#12192e; --card-border:#2a3655;
        --text:#f7faff; --muted:#b5c3dd; --accent1:#ff5ea7; --accent2:#7c3aed; --accent3:#22d3ee;
        --good:#10b981; --bad:#ef4444;
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
        font-weight:900;font-size:2.3rem;letter-spacing:.2px;margin:.2rem 0 .5rem;
        background:linear-gradient(90deg,var(--accent1),var(--accent2),var(--accent3));
        -webkit-background-clip:text;-webkit-text-fill-color:transparent;
      }

      /* === Intro en blanc === */
      .intro-card{
        background:#ffffff; color:#0b1020;
        border:1px solid #e7ebf3; border-radius:18px; padding:18px 18px 14px;
        box-shadow:0 10px 40px rgba(0,0,0,.10);
      }
      .intro-card .section-title{color:#0b1020;}
      .intro-card .hint{color:#334155;}

      .card{
        background:var(--card);
        border:1px solid var(--card-border);
        border-radius:18px;
        padding:18px 18px 14px;
        box-shadow:0 10px 40px rgba(0,0,0,.45);
      }

      .section-title{font-size:1.15rem;font-weight:800;margin-bottom:.35rem;}
      .hint{color:var(--muted);font-size:.95rem;margin:.15rem 0 .7rem;}

      .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div {
        background:#0f1730 !important; border:1px solid #2a3655 !important;
        color:var(--text)!important; border-radius:12px!important;
      }

      @keyframes glow{0%{box-shadow:0 0 0 rgba(255,94,167,.0)}50%{box-shadow:0 10px 35px rgba(124,58,237,.35)}100%{box-shadow:0 0 0 rgba(34,211,238,.0)}}
      .stButton>button{
        border-radius:12px!important;font-weight:800!important;letter-spacing:.3px;
        border:1px solid #2a3655!important;color:#fff!important;padding:0.65rem 1rem!important;
        background:linear-gradient(90deg,var(--accent1),var(--accent2),var(--accent3))!important;
        background-size:200% 200%!important;animation:glow 2.6s ease-in-out infinite;
      }
      .stButton>button:hover{filter:brightness(1.08);transform:translateY(-1px);transition:all .15s ease;}

      .chip{display:inline-flex;gap:8px;align-items:center;font-weight:700;font-size:.82rem;color:white;
            padding:6px 12px;border-radius:999px;margin-right:6px;
            background:linear-gradient(90deg,var(--accent2),var(--accent3));border:1px solid #3a4a75;}
      .good{color:var(--good)!important;} .bad{color:var(--bad)!important;}
      .stAlert{border-radius:12px;border:1px solid #2a3655;}
      section.main > div { padding-top: .35rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ====================== DATABASE ======================
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

# ====================== SENTIMENT ======================
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

# ====================== OPENAI HELPER ======================
def openai_client():
    key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if OPENAI_OK and key:
        return OpenAI(api_key=key)
    return None

SYSTEM_PROMPT = (
    "You are DailyUp, a concise, encouraging micro-coach. "
    "Always be specific and actionable. Use plain English and stay short."
)

def ask_llm(user_text:str, slot:str, tone:str)->Dict[str,str]:
    client=openai_client()
    if not client:
        raise RuntimeError("OpenAI not configured")

    prompt = f"""
Analyze the user note and produce JSON:

User note: {user_text}
Time window: {slot}
Tone: {tone}

Rules:
- analysis: 2 short sentences explaining mood or blockers
- plan_steps: exactly 3 micro actions
- mantra: 3–5 words
Return JSON only.
"""
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":SYSTEM_PROMPT},
                  {"role":"user","content":prompt}],
        temperature=0.4,
    )
    text=r.choices[0].message.content.strip()
    match=re.search(r"\{.*\}",text,re.S)
    if not match:
        return {"analysis":text[:200],"plan_steps":["Start small","Work 10 min","Cut distractions"],"mantra":"Small wins compound"}
    import json
    try:
        data=json.loads(match.group(0))
        return {
            "analysis":data.get("analysis",""),
            "plan_steps":data.get("plan_steps",["Start small","Work 10 min","Cut distractions"]),
            "mantra":data.get("mantra","Small wins compound")
        }
    except Exception:
        return {"analysis":text[:200],"plan_steps":["Start small","Work 10 min","Cut distractions"],"mantra":"Small wins compound"}

# ====================== FALLBACK ======================
def smart_fallback(user_text:str, slot:str)->Dict[str,str]:
    words=re.findall(r"[a-zA-Z]{4,}",user_text.lower())
    top=", ".join(words[:3]) if words else "your task"
    openers={"morning":"Morning Boost.","midday":"Midday focus.","evening":"Evening wrap."}
    opening=openers.get(slot,"Small step.")
    return {
        "analysis":f"{opening} You might feel resistance but let’s make it tiny.",
        "plan_steps":[
            f"Clarify one micro goal about {top}.",
            "Work for 10 focused minutes.",
            "Remove one distraction before starting."
        ],
        "mantra":"Begin before you think"
    }

# ====================== SESSION ======================
if "slot" not in st.session_state: st.session_state.slot="morning"
if "user_text" not in st.session_state: st.session_state.user_text=""
if "timer_running" not in st.session_state: st.session_state.timer_running=False
if "timer_end" not in st.session_state: st.session_state.timer_end=None

# ====================== HEADER ======================
st.markdown('<div class="wrap">', unsafe_allow_html=True)
st.markdown('<div class="title">DailyUp — Live Coach</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="intro-card">
      <div class="section-title">How to use this</div>
      <div class="hint">
        1️⃣ Pick your moment (morning/midday/evening)<br>
        2️⃣ Tell me what’s happening<br>
        3️⃣ Click <b>Analyze & coach me</b><br>
        I’ll give you a short <b>analysis</b>, a <b>3-step plan</b> and a <b>mantra</b> to stay focused.
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# ====================== STEP 1 — PICK MOMENT ======================
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 1 — Pick your moment</div>', unsafe_allow_html=True)
    slot=st.segmented_control("Time window",["morning","midday","evening"],default=st.session_state.slot)
    st.session_state.slot=slot
    prompts={
        "morning":"Morning Boost — what’s your first tiny win?",
        "midday":"Midday Nudge — what’s blocking progress?",
        "evening":"Evening Wrap — one small win today?"
    }
    st.caption(f"Prompt: _{prompts[slot]}_")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ====================== STEP 2 — USER NOTE ======================
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 2 — Write what’s going on</div>', unsafe_allow_html=True)
    examples={
        "morning":"Example: “This morning I’d like to draft the intro of my report.”",
        "midday":"Example: “I feel stuck on section 2; next tiny step?”",
        "evening":"Example: “I want one small win and prep tomorrow.”"
    }
    st.session_state.user_text = st.text_area(
        "Your note",
        value=st.session_state.user_text,
        placeholder=examples[st.session_state.slot],
        height=100,
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ====================== STEP 3 — ANALYZE ======================
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 3 — Analyze & coach me</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">AI will analyze and give you a 3-step plan. Fallback works locally if no key.</div>', unsafe_allow_html=True)

    disabled=not st.session_state.user_text.strip()
    if st.button("Analyze & coach me", disabled=disabled):
        with st.spinner("Thinking..."):
            s=get_sentiment(st.session_state.user_text)
            try:
                out=ask_llm(st.session_state.user_text, st.session_state.slot, "neutral")
            except Exception:
                out=smart_fallback(st.session_state.user_text, st.session_state.slot)

            save_log({
                "ts":datetime.utcnow().isoformat(),
                "slot":st.session_state.slot,
                "user_text":st.session_state.user_text,
                "tone":"neutral",
                "sentiment":s["label"],
                "score":s["score"],
                "plan":"\n".join(out["plan_steps"]),
                "mantra":out["mantra"],
                "analysis":out["analysis"],
            })
        st.success("Your personalized plan is ready 👇")

    # --- reload last result safely
    df_last=read_logs()
    if not df_last.empty:
        rowd=df_last.iloc[0].to_dict()
        sentiment=rowd.get("sentiment","NEUTRAL")
        try: score=float(rowd.get("score",0.0) or 0.0)
        except Exception: score=0.0
        analysis=rowd.get("analysis","")
        mantra=rowd.get("mantra","")
        plan_raw=rowd.get("plan","")
        steps=plan_raw.splitlines() if plan_raw else []

        color="good" if score>=.15 else ("bad" if score<=-.15 else "muted")
        st.markdown(f"**Sentiment:** <span class='{color}'>{sentiment} ({score:.2f})</span>", unsafe_allow_html=True)
        st.markdown("**Analysis:** "+(analysis or "_(none yet)_"))
        st.markdown("**Plan:**")
        if steps: st.write(f"1) {steps[0]}\n2) {steps[1]}\n3) {steps[2]}")
        else: st.caption("No plan yet.")
        st.markdown(f"**Mantra:** _{mantra}_")
    else:
        st.caption("No analysis yet.")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ====================== STEP 4 — TIMER ======================
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 4 — Focus burst (optional)</div>', unsafe_allow_html=True)
    duration=st.slider("Duration (minutes)",5,45,10,5)
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
            st.success("⏰ Time’s up — nice work!")
        else:
            m=int(remaining//60); s=int(remaining%60)
            st.metric("Remaining",f"{m:02d}:{s:02d}")
            time.sleep(0.6); st.experimental_rerun()
    else:
        st.caption("Timer is idle.")
    st.markdown('</div>', unsafe_allow_html=True)

st.write("")

# ====================== STEP 5 — DASHBOARD ======================
with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Step 5 — Progress</div>', unsafe_allow_html=True)
    df=read_logs()
    if df.empty:
        st.caption("No entries yet.")
    else:
        df["ts"]=pd.to_datetime(df["ts"])
        chart=alt.Chart(df).mark_line(point=True).encode(
            x=alt.X("ts:T",title="Time"),
            y=alt.Y("score:Q",title="Sentiment"),
            color=alt.value("#22d3ee")
        ).properties(height=240)
        st.altair_chart(chart,use_container_width=True)
        show=df.tail(6)[["ts","slot","sentiment","score","mantra"]]
        show.columns=["Time","Slot","Sentiment","Score","Mantra"]
        st.dataframe(show,hide_index=True,use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.caption("Built with ❤️ — DailyUp")
st.markdown('</div>', unsafe_allow_html=True)
