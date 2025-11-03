# -*- coding: utf-8 -*-
import os
import re
import html
from datetime import datetime
from typing import Dict

import streamlit as st

# ========== PAGE CONFIG ==========
st.set_page_config(
    page_title="DailyUp — Micro-Coach",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ========== STYLE FIX (dark & light) ==========
st.markdown("""
<style>
:root {
  --primary-grad: linear-gradient(135deg,#7c3aed 0%, #ec4899 50%, #06b6d4 100%);
  --bg-light: #f8fafc;
  --bg-dark: #0f172a;
  --text-light: #0f172a;
  --text-dark: #f9fafb;
  --card-light: #ffffff;
  --card-dark: #1e293b;
  --shadow: 0 6px 16px rgba(0,0,0,.1);
}

/* background adapts */
[data-base-theme="light"] .stApp {
  background: radial-gradient(900px 600px at 90% 5%, rgba(236,72,153,.15), transparent 60%),
              radial-gradient(800px 600px at -10% 20%, rgba(99,102,241,.15), transparent 60%),
              var(--bg-light);
  color: var(--text-light);
}
[data-base-theme="dark"] .stApp {
  background: radial-gradient(900px 600px at 90% 5%, rgba(236,72,153,.2), transparent 60%),
              radial-gradient(800px 600px at -10% 20%, rgba(99,102,241,.25), transparent 60%),
              var(--bg-dark);
  color: var(--text-dark);
}

/* hero */
.hero {
  border-radius: 20px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
[data-base-theme="light"] .hero { background: var(--card-light); color: var(--text-light); }
[data-base-theme="dark"] .hero { background: var(--card-dark); color: var(--text-dark); }

/* moment cards */
.moment {
  border-radius: 16px;
  padding: 14px 18px;
  margin-bottom: 20px;
  box-shadow: var(--shadow);
}
.morning { background: linear-gradient(135deg,#faf5ff 0%,#dbeafe 100%); }
.midday  { background: linear-gradient(135deg,#ecfdf5 0%,#e0f2fe 100%); }
.evening { background: linear-gradient(135deg,#fdf2f8 0%,#ede9fe 100%); }
[data-base-theme="dark"] .morning { background: linear-gradient(135deg,#312e81 0%,#1e3a8a 100%); }
[data-base-theme="dark"] .midday  { background: linear-gradient(135deg,#064e3b 0%,#0c4a6e 100%); }
[data-base-theme="dark"] .evening { background: linear-gradient(135deg,#581c87 0%,#3b0764 100%); }

/* buttons */
.btn-primary button {
  width: 100%;
  font-weight: 700;
  background: var(--primary-grad);
  border-radius: 12px;
  border: none;
  color: white;
  box-shadow: 0 6px 16px rgba(124,58,237,.25);
}
.btn-primary button:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(124,58,237,.35);
}

/* textareas */
textarea, .stTextArea textarea {
  border-radius: 10px !important;
  border: 1px solid #cbd5e1 !important;
  padding: 10px !important;
  font-size: 1rem;
}
[data-base-theme="dark"] textarea, [data-base-theme="dark"] .stTextArea textarea {
  background-color: #1e293b !important;
  color: #f9fafb !important;
  border-color: #475569 !important;
}

/* lists + markdown */
ul li, ol li { margin-bottom: 0.4rem; }

</style>
""", unsafe_allow_html=True)

# === DETECT DARK/LIGHT ===
st.markdown(
    f'<script>document.body.setAttribute("data-base-theme", "{st.get_option("theme.base") or "light"}");</script>',
    unsafe_allow_html=True
)

# ========== MOCK COACH (SAME LOGIC) ==========
def fallback_coach(note: str, slot: str) -> Dict:
    low = note.lower()
    if "exam" in low or "stress" in low:
        return {
            "analysis": "Exam context — focus on reducing anxiety and keeping focus small.",
            "plan": ["Pick 1 small topic", "Study for 20 minutes", "Review key points"],
            "mantra": "Small wins compound",
        }
    return {
        "analysis": f"{slot.title()} — focus on one tiny action you can take now.",
        "plan": ["Define 1 small goal", "Prepare one item", "Start for 5 minutes"],
        "mantra": "One small step beats zero",
    }

# ========== LAYOUT ==========
st.markdown("""
<div class="hero">
  <h1>🌞 DailyUp</h1>
  <p><b>Tiny nudges, big progress.</b>  
  Write how you feel or your main goal — I’ll craft a short 3-step plan with a motivational mantra.  
  Follow vertically: Step 1 → Step 2 → Step 3.</p>
</div>
""", unsafe_allow_html=True)

# Step 1
st.subheader("Step 1 — Pick your moment")
slot = st.radio(
    "When is this for?",
    ["morning", "midday", "evening"],
    horizontal=True,
    label_visibility="collapsed"
)
MOMENT_INFO = {
    "morning": ("Morning — Start bright & small", "⚡ Energy: fresh start", "🎯 Focus: one clear tiny win", "🧭 Tone: action-first"),
    "midday": ("Midday — Reset & refocus", "🔄 Energy: realign", "🎯 Focus: 15–20 min block", "🧭 Tone: pragmatic"),
    "evening": ("Evening — Wrap & seed tomorrow", "🌙 Energy: calm close", "📝 Focus: reflection", "🧭 Tone: clarity"),
}
info = MOMENT_INFO[slot]
st.markdown(f"""
<div class="moment {slot}">
  <h4>{info[0]}</h4>
  <ul>
    <li>{info[1]}</li>
    <li>{info[2]}</li>
    <li>{info[3]}</li>
  </ul>
</div>
""", unsafe_allow_html=True)

# Step 2
st.subheader("Step 2 — Tell me your note")
user_note = st.text_area("What's on your mind?", placeholder="e.g., I’m stressed because I have an exam.")

# Step 3
st.subheader("Step 3 — Analyze & coach me")
st.markdown('<div class="btn-primary">', unsafe_allow_html=True)
go = st.button("💬 Analyze & coach me")
st.markdown('</div>', unsafe_allow_html=True)

if go:
    if not user_note.strip():
        st.warning("Please enter a note first!")
    else:
        with st.spinner("Analyzing..."):
            result = fallback_coach(user_note, slot)
        st.success("✅ Your personalized plan is ready!")
        st.markdown(f"**Analysis:** {result['analysis']}")
        st.markdown("### 3-Step Plan")
        for i, step in enumerate(result["plan"], start=1):
            st.markdown(f"{i}. {step}")
        st.markdown(f"**Mantra:** *{result['mantra']}*")
