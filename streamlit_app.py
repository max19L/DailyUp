# -*- coding: utf-8 -*-
import os
import re
import html
import hashlib
from datetime import datetime, date
from typing import Dict, List

import pandas as pd
import streamlit as st
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import plotly.graph_objects as go

# Télécharger le lexique de sentiment si besoin
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

# ─────────────────────────────────────────────
# CONFIGURATION DE LA PAGE
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="DailyUp — Micro-Coach",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────
# STYLE GLOBAL (CLAIROSCURO + CADRE QUOTE)
# ─────────────────────────────────────────────
CSS = """
:root{
  --ink: #111827;
  --muted: #4b5563;
  --bg: #f6f8ff;
  --card: #ffffff;
  --border: #e6e8f2;
  --primaryGrad: linear-gradient(135deg,#7c3aed 0%, #ec4899 55%, #06b6d4 100%);
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
    --shadow: 0 14px 30px rgba(0,0,0,.45);
  }
}
html, body, [data-testid="stAppViewContainer"]{
  background: radial-gradient(900px 600px at 90% 5%, rgba(236,72,153,.18), transparent 50%),
              radial-gradient(800px 600px at -10% 20%, rgba(99,102,241,.16), transparent 55%),
              radial-gradient(700px 500px at 50% 120%, rgba(34,197,94,.12), transparent 55%),
              var(--bg);
  color: var(--ink);
}
#MainMenu, footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}
.banner{
  position: relative;
  margin: 8px 0 20px 0;
  padding: 22px 24px;
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
.banner .b-quote{
  position: relative;
  z-index: 1;
  font-size: 1.12rem;
  line-height: 1.65rem;
  font-style: italic;
}
.banner .b-author{
  position: relative;
  z-index: 1;
  margin-top: 8px;
  font-weight: 700;
  letter-spacing: .2px;
  color: var(--muted);
  font-size: 0.95rem;
}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# BANQUE DE GRANDES CITATIONS SCIENTIFIQUES
# ─────────────────────────────────────────────
BIG_QUOTES = [
    (
        "La règle des 2 minutes",
        "Commence par une action minuscule : si une tâche prend moins de 2 minutes, fais-la immédiatement. "
        "Cette petite victoire déclenche la dopamine et la motivation. L’action précède souvent la motivation.",
        "James Clear (Atomic Habits)"
    ),
    (
        "La théorie de l’autodétermination",
        "La motivation durable repose sur trois piliers : l’autonomie (choisis), la compétence (progresse) et le lien social (partage). "
        "Crée un sentiment de maîtrise et de connexion.",
        "Deci & Ryan (2000)"
    ),
    (
        "L’effet Pygmalion",
        "Croire en ton potentiel augmente tes chances de réussir. Les attentes positives transforment ton comportement et tes résultats.",
        "Rosenthal & Jacobson (1968)"
    ),
    (
        "Le pouvoir des petites victoires",
        "Célèbre les micro-progrès : chaque étape franchie relie effort et satisfaction, créant un cercle vertueux de motivation.",
        "Teresa Amabile (Harvard)"
    ),
    (
        "L’effet Fresh Start",
        "Les dates symboliques (lundi, début du mois, anniversaire) stimulent la motivation à repartir sur de bonnes bases.",
        "Dai, Milkman & Riis (2014)"
    ),
    (
        "L’environnement crée l’action",
        "Rends la prochaine étape visible et facile : la motivation vient souvent quand l’obstacle devient minime.",
        "BJ Fogg (Tiny Habits)"
    ),
]

def big_quote_of_the_day() -> dict:
    seed = f"{date.today().isoformat()}::banner"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(BIG_QUOTES)
    title, text, author = BIG_QUOTES[idx]
    return {"title": title, "text": text, "author": author}

# ─────────────────────────────────────────────
# AFFICHAGE DE LA GRANDE CITATION
# ─────────────────────────────────────────────
bq = big_quote_of_the_day()
st.markdown(
    f"""
<div class="banner">
  <div class="b-quote">“{html.escape(bq['text'])}”</div>
  <div class="b-author">— {html.escape(bq['author'])} · <span style="opacity:.8">{html.escape(bq['title'])}</span></div>
</div>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# TITRE DE L’APPLICATION
# ─────────────────────────────────────────────
st.title("✨ DailyUp — Micro-Coach")
st.markdown(
    "Des micro-actions. Des résultats massifs. "
    "Écris ton état d’esprit, et je génère un plan de 3 étapes et un mantra pour te relancer."
)

# ─────────────────────────────────────────────
# SAISIE UTILISATEUR + ANALYSE DE SENTIMENT
# ─────────────────────────────────────────────
note = st.text_area("🧠 Que ressens-tu ou que veux-tu accomplir aujourd’hui ?",
    placeholder="Ex : Je suis stressé pour mon examen demain...",
    height=120
)

def analyze_sentiment(txt: str) -> Dict[str, float]:
    sia = SentimentIntensityAnalyzer()
    scores = sia.polarity_scores(txt)
    return {
        "Positif": round(scores["pos"], 3),
        "Négatif": round(scores["neg"], 3),
        "Neutre": round(scores["neu"], 3),
        "Score global": round(scores["compound"], 3)
    }

def radar_chart(scores: Dict[str, float]) -> go.Figure:
    cats = list(scores.keys())
    vals = list(scores.values()) + [list(scores.values())[0]]
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=cats + [cats[0]], fill='toself', line_color="#7c3aed"))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0,1])),
        showlegend=False,
        margin=dict(l=0,r=0,t=10,b=10),
        paper_bgcolor="rgba(0,0,0,0)"
    )
    return fig

if note.strip():
    st.markdown("### 🌈 Analyse émotionnelle instantanée")
    scores = analyze_sentiment(note)
    st.plotly_chart(radar_chart(scores), use_container_width=True)
    st.json(scores)

# ─────────────────────────────────────────────
# SECTION PLAN COACH (SIMPLIFIÉE)
# ─────────────────────────────────────────────
if st.button("💬 Générer mon micro-plan"):
    st.success("✅ Voici ton plan en 3 étapes :")
    st.markdown("""
1. Respire et identifie une micro-action (≤ 10 minutes).  
2. Lance-toi tout de suite, sans réfléchir.  
3. Note ton ressenti après 5 minutes.
""")
    st.caption("Mantra : *Commence avant d’y penser.*")
