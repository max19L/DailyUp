# -*- coding: utf-8 -*-
import os
import re
import html
import random
import hashlib
from datetime import datetime, date
from typing import Dict, List

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# ─────────────── téléchargement NLTK si nécessaire ───────────────
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")

# ─────────────── configuration page ───────────────
st.set_page_config(
    page_title="DailyUp — Micro-Coach",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────── CSS (le même que ta version précédente + ajout cadre top) ───────────────
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

/* Cadre citation du jour */
.banner{
  position: relative;
  margin: 10px 0 24px 0;
  padding: 22px 26px;
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
  font-size: 1.15rem;
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

/* autres styles (inchangés) */
.moment{border-radius:16px;padding:16px 18px;color:#0b1020;
border:1px solid var(--border);box-shadow:var(--shadow);}
.morning{background:linear-gradient(135deg,#fff1f9 0%,#e6edff 100%);}
.midday{background:linear-gradient(135deg,#e7fff8 0%,#ebf2ff 100%);}
.evening{background:linear-gradient(135deg,#ffe8ec 0%,#ebe2ff 100%);}
@media (prefers-color-scheme: dark){
  .moment{color:#eef2ff;border-color:#2a2f45;}
  .morning{background:linear-gradient(135deg,#2a1930 0%,#1a1f40 100%);}
  .midday{background:linear-gradient(135deg,#0d2a26 0%,#16243f 100%);}
  .evening{background:linear-gradient(135deg,#2b1820 0%,#231c41 100%);}
}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

# ─────────────── Grande citation scientifique du jour ───────────────
BIG_QUOTES = [
    (
        "La règle des 2 minutes",
        "Commence par une action minuscule : si une tâche prend moins de 2 minutes, fais-la immédiatement. "
        "Cette petite victoire déclenche la dopamine et la motivation. L’action précède souvent la motivation.",
        "James Clear (Atomic Habits)"
    ),
    (
        "L’effet Pygmalion",
        "Croire en ton potentiel augmente tes chances de réussir. Les attentes positives transforment ton comportement et tes résultats.",
        "Rosenthal & Jacobson (1968)"
    ),
    (
        "La théorie de l’autodétermination",
        "La motivation durable repose sur trois piliers : autonomie, compétence et lien social. "
        "Crée un sentiment de maîtrise et de connexion.",
        "Deci & Ryan (2000)"
    ),
    (
        "Le pouvoir des petites victoires",
        "Célèbre les micro-progrès : chaque étape franchie relie effort et satisfaction, créant un cercle vertueux de motivation.",
        "Teresa Amabile (Harvard)"
    ),
    (
        "L’effet Fresh Start",
        "Les débuts symboliques (lundi, mois, anniversaire) stimulent la motivation à repartir sur de bonnes bases.",
        "Dai, Milkman & Riis (2014)"
    ),
]
def big_quote_of_the_day() -> dict:
    seed = f"{date.today().isoformat()}::banner"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(BIG_QUOTES)
    title, text, author = BIG_QUOTES[idx]
    return {"title": title, "text": text, "author": author}

# ─────────────── affichage cadre quote ───────────────
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

# ─────────────── ton appli habituelle ensuite ───────────────
st.markdown('<div class="hero"><div class="pill">✨ Micro-Coach DailyUp</div><div class="title">Tiny nudges. Massive progress.</div><p style="max-width:820px; color:var(--muted); font-size:1.05rem;">Dis-moi comment tu te sens ou ton objectif du moment. Je te propose un plan en 3 micro-étapes et un mantra.</p></div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 1 — Choisis ton moment")

slot = st.radio("Quand veux-tu être coaché ?",
                options=["morning", "midday", "evening"],
                index=0,
                horizontal=True)

MOMENT_INFO = {
    "morning": {
        "title": "Matin — Démarre petit et fort",
        "bullets": [
            "⚡ Énergie : nouveau départ, réduis la friction.",
            "🎯 Focus : un petit objectif clair (10-15 min).",
            "🧭 Ton : action, momentum."
        ],
        "cls": "morning"
    },
    "midday": {
        "title": "Midi — Recentrage express",
        "bullets": [
            "🔄 Énergie : ré-alignement rapide.",
            "🎯 Focus : un bloc court (15-20 min).",
            "🧭 Ton : pragmatique, recentré."
        ],
        "cls": "midday"
    },
    "evening": {
        "title": "Soir — Clôture sereine",
        "bullets": [
            "🌙 Énergie : relâchement, calme.",
            "📝 Focus : réflexion et préparation de demain.",
            "🧭 Ton : apaisé, clair."
        ],
        "cls": "evening"
    },
}
info = MOMENT_INFO[slot]
bul = "".join([f"<li>{html.escape(x)}</li>" for x in info["bullets"]])
st.markdown(f"<div class='moment {info['cls']}'><h4>{info['title']}</h4><ul style='margin:.2rem 0 0 .9rem;'>{bul}</ul></div>", unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 2 — Rédige ta note")

note = st.text_area("Exprime ton ressenti ou ton objectif du moment",
                    placeholder="Ex : Je suis stressé avant mon examen...",
                    height=120)

# radar simplifié pour ne rien casser
if note.strip():
    sia = SentimentIntensityAnalyzer()
    scores = sia.polarity_scores(note)
    data = {
        "Positif": scores["pos"],
        "Négatif": scores["neg"],
        "Neutre": scores["neu"]
    }
    fig = go.Figure(data=go.Scatterpolar(r=list(data.values())+[list(data.values())[0]], theta=list(data.keys())+[list(data.keys())[0]], fill='toself', name='Sentiment'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,1])), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 3 — Analyse & coaching")
if st.button("💬 Analyze & coach me"):
    st.success("✅ Ton plan personnalisé est prêt !")
    st.markdown("""
**Analyse :** Démarre petit, clarifie ton intention, et réduis la friction.  
**Plan :**  
1. Note ton prochain micro-objectif.  
2. Lance-toi pendant 10 minutes sans te juger.  
3. Note ton ressenti et ta progression.  
**Mantra :** *Une petite action vaut mieux que zéro.*
""")
