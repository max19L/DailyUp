# streamlit_app.py  (ou app.py si tu as mis ça dans Main file path)
import streamlit as st
from datetime import datetime
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

# Télécharge le lexique VADER si besoin
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon")
sia = SentimentIntensityAnalyzer()

st.set_page_config(page_title="DailyUp", page_icon="☀️", layout="wide")
st.title("☀️ DailyUp")
st.caption("De minuscules coups de pouce, des progrès massifs.")

slot = st.radio("Moment", ["morning", "midday", "evening"], horizontal=True)
user = st.text_area("Ta réponse (1–2 phrases)")

if st.button("Analyser"):
    scores = sia.polarity_scores(user)
    label = "POSITIVE" if scores["compound"] >= 0.25 else "NEGATIVE" if scores["compound"] <= -0.25 else "NEUTRAL"
    st.write(f"**Sentiment**: {label} ({abs(scores['compound']):.2f})")

    # mini plan
    plan = {
        "morning": ["Choisis un micro-pas (≤10 min)", "Coupe distractions 20 min", "Démarre avant de réfléchir"],
        "midday":  ["Note 1 réussite", "Relance une tâche 10 min", "Ferme une distraction"],
        "evening": ["Log un apprentissage", "Prépare le 1er pas de demain", "Range 2 min"]
    }[slot]
    st.subheader("Plan coach (3 étapes)")
    for i, step in enumerate(plan, 1):
        st.write(f"{i}. {step}")
