# streamlit_app.py
import streamlit as st
from datetime import datetime
import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# --- VADER ------------------------------------------------------------------------
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")
SIA = SentimentIntensityAnalyzer()

# --- Page config ------------------------------------------------------------------
st.set_page_config(
    page_title="DailyUp",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CSS (thème sombre + néon, cartes glassmorphism) ------------------------------
CSS = """
<style>
:root {
  --bg: #0b0f15;
  --card: rgba(19, 24, 34, 0.65);
  --border: rgba(255, 255, 255, 0.08);
  --muted: #98a2b3;
  --text: #e6eaf0;
  --brand: #00e5ff;
  --brand-2: #7cffb2;
  --shadow: 0 8px 30px rgba(0,0,0,.45);
}

html, body, [class^="css"] {
  background: radial-gradient(1200px 800px at 10% -10%, #13203b66, transparent 60%),
              radial-gradient(900px 600px at 110% -20%, #0e1a2c66, transparent 60%),
              var(--bg)!important;
  color: var(--text);
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 18px 14px;
  box-shadow: var(--shadow);
  backdrop-filter: blur(8px);
}

.stButton>button {
  background: linear-gradient(90deg, var(--brand), #6df7f7);
  color: #001018;
  border: none; padding: .75rem 1.1rem;
  border-radius: 12px; font-weight: 700;
  transition: transform .04s ease;
}
.stButton>button:hover { transform: translateY(-1px); }

textarea, .stTextInput input {
  background: rgba(15,20,28,.65)!important;
  color: var(--text)!important;
  border: 1px solid var(--border)!important;
  border-radius: 12px!important;
}

.pill{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;border-radius:999px;font-size:12.5px;letter-spacing:.3px;border:1px solid var(--border);color:var(--muted);background:rgba(18,24,34,.6)}
.pill .dot{width:8px;height:8px;border-radius:50%;background:var(--brand)}

.metric{display:flex;flex-direction:column;gap:6px;background:var(--card);border:1px solid var(--border);border-radius:14px;padding:14px}
.metric .value{font-weight:800;font-size:22px;color:var(--brand-2)}
.metric .label{font-size:12.5px;color:var(--muted)}

.steps li{margin:.2rem 0 .6rem 0}
hr{border-color:var(--border)}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# --- Helpers ----------------------------------------------------------------------
def analyze_sentiment(text: str):
    if not text.strip():
        return {"label": "NEUTRAL", "score": 0.0, "badge": "〰️"}
    s = SIA.polarity_scores(text)
    comp = s["compound"]
    if comp >= 0.25: lbl, badge = "POSITIVE", "✅"
    elif comp <= -0.25: lbl, badge = "NEGATIVE", "⚠️"
    else: lbl, badge = "NEUTRAL", "〰️"
    return {"label": lbl, "score": abs(comp), "badge": badge}

def get_prompt(slot: str) -> dict:
    bank = {
        "morning": {
            "title": "🌅 Morning Boost",
            "quote": "Consistency beats intensity.",
            "question": "Quel est TON micro-objectif de ce matin (≤10 min) ?"
        },
        "midday": {
            "title": "🌤 Midday Check-in",
            "quote": "One small step today beats zero.",
            "question": "Où en es-tu ? Quelle petite friction à dégager ?"
        },
        "evening": {
            "title": "🌙 Evening Wrap",
            "quote": "Tiny wins compound.",
            "question": "Qu’as-tu appris aujourd’hui ? Quel 1er geste prépare demain ?"
        }
    }
    return bank.get(slot, bank["morning"])

def coach_plan(slot: str, tone: str) -> list[str]:
    base = {
        "morning": [
            "Choisis **1 micro-pas (≤10 min)**",
            "Coupe distractions **20 min**",
            "Démarre **avant** de trop réfléchir",
        ],
        "midday": [
            "Note **1 réussite**",
            "Relance **une** tâche 10 min",
            "Ferme **une** distraction",
        ],
        "evening": [
            "Log **1 apprentissage**",
            "Prépare **le 1er pas** de demain",
            "Range **2 minutes**",
        ],
    }[slot]

    if tone == "supportive":
        base[0] = "Respire 20s, puis **1 micro-pas (≤10 min)**"
    elif tone == "challenging":
        base[-1] = "Publie **une preuve** (photo/note) de ton avance"

    return base

def add_to_journal(slot, user_text, sentiment, plan):
    row = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds"),
        "slot": slot,
        "message": user_text,
        "sentiment": sentiment["label"],
        "score": round(sentiment["score"], 2),
        "plan": " | ".join(plan),
    }
    st.session_state.journal = pd.concat(
        [st.session_state.journal, pd.DataFrame([row])],
        ignore_index=True,
    )

def render_metric(label, value):
    st.markdown(
        f"""<div class="metric">
                <div class="label">{label}</div>
                <div class="value">{value}</div>
            </div>""",
        unsafe_allow_html=True,
    )

# --- State ------------------------------------------------------------------------
if "journal" not in st.session_state:
    st.session_state.journal = pd.DataFrame(
        columns=["timestamp", "slot", "message", "sentiment", "score", "plan"]
    )

# --- Header -----------------------------------------------------------------------
left, _, right = st.columns([1.6, .2, 1.2])
with left:
    st.markdown("### ☀️ **DailyUp**")
    st.caption("De minuscules coups de pouce, des progrès massifs.")
with right:
    st.markdown('<span class="pill"><span class="dot"></span>Live Coach</span>', unsafe_allow_html=True)

st.markdown("<br/>", unsafe_allow_html=True)

# --- Layout principal --------------------------------------------------------------
col_left, col_right = st.columns([1.05, 1])

# ---- Panneau gauche ---------------------------------------------------------------
with col_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Réglages coach")

    # Remplace segmented_control -> radio (horizontal)
    slot = st.radio(
        "Moment",
        options=["morning", "midday", "evening"],
        index=0,
        horizontal=True,
    )

    tone = st.selectbox(
        "Tonalité du coach",
        ["neutral", "supportive", "challenging"],
        index=0,
        help="Neutral: factuel • Supportive: empathique • Challenging: énergique",
    )

    pr = get_prompt(slot)
    st.markdown("---")
    st.markdown(f"#### {pr['title']}")
    st.caption(f"“{pr['quote']}”")
    st.info(pr["question"])
    st.markdown("</div>", unsafe_allow_html=True)

# ---- Panneau droit ---------------------------------------------------------------
with col_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Ton input")

    user_text = st.text_area(
        "Écris 1–2 phrases (sentiment détecté automatiquement)",
        height=120,
        label_visibility="collapsed",
        placeholder="Par ex. : 'je procrastine sur le rapport' ou 'bonne énergie, je veux finaliser...'",
    )

    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        get_btn = st.button("✨ Générer un prompt")
    with c2:
        send_btn = st.button("🚀 Proposer un plan")
    with c3:
        clear_btn = st.button("🧹 Effacer")

    st.markdown("</div>", unsafe_allow_html=True)

# ---- Sorties ----------------------------------------------------------------------
st.markdown("<br/>", unsafe_allow_html=True)
out_left, out_right = st.columns([1, 1])

with out_left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🎯 Prompt")
    if get_btn:
        st.success(f"**{pr['title']}** — {pr['quote']}\n\n**Question** — {pr['question']}")
    else:
        st.caption("Clique sur *Générer un prompt* pour afficher la question du moment.")
    st.markdown("</div>", unsafe_allow_html=True)

with out_right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🧠 Analyse & plan")

    if send_btn:
        senti = analyze_sentiment(user_text)
        steps = coach_plan(slot, tone)

        m1, m2, m3 = st.columns(3)
        with m1: render_metric("Sentiment", f"{senti['badge']} {senti['label']}")
        with m2: render_metric("Score", f"{senti['score']:.2f}")
        with m3: render_metric("Tonalité", tone.capitalize())

        st.markdown("##### Plan (3 étapes)")
        st.markdown(
            "<ol class='steps'>" + "".join([f"<li>{s}</li>" for s in steps]) + "</ol>",
            unsafe_allow_html=True,
        )

        add_to_journal(slot, user_text, senti, steps)

    elif clear_btn:
        st.session_state.journal = st.session_state.journal.iloc[0:0]
        st.info("Journal vidé.")
    else:
        st.caption("Écris ton message puis clique sur *Proposer un plan*.")

    st.markdown("</div>", unsafe_allow_html=True)

# --- Journal -----------------------------------------------------------------------
st.markdown("<br/>", unsafe_allow_html=True)
st.markdown('<div class="card">', unsafe_allow_html=True)
st.subheader("📜 Journal")
if len(st.session_state.journal):
    st.dataframe(
        st.session_state.journal.sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    csv = st.session_state.journal.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Export CSV", csv, "dailyup_journal.csv", "text/csv")
else:
    st.caption("Ton journal est vide pour l’instant.")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    "<div style='text-align:center;color:var(--muted);padding:10px 0;opacity:.9'>"
    "Built with 💙 Streamlit • DailyUp"
    "</div>",
    unsafe_allow_html=True,
)
