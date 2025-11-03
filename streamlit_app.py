import os
import time
from typing import Dict, List

import streamlit as st
import pandas as pd

# --- IA (OpenAI) optionnelle : on l'active seulement si la clé est dispo ---
USE_OPENAI = bool(os.getenv("OPENAI_API_KEY"))
if USE_OPENAI:
    try:
        from openai import OpenAI
        client = OpenAI()
    except Exception:
        USE_OPENAI = False


# =========================
#      THEME & STYLES
# =========================
def inject_theme_css() -> None:
    """
    CSS responsive au thème Streamlit.
    Utilise les variables natives : --text-color, --background-color, --primary-color.
    Donne du contraste en dark & light, accentue les cartes et les boutons.
    """
    st.markdown(
        """
        <style>
        :root {
            --du-card-radius: 18px;
            --du-shadow: 0 10px 30px rgba(0,0,0,0.08);
            --du-ring: 0 0 0 3px rgba(0,0,0,0.08);
        }
        .stApp {
            background: radial-gradient(1200px 600px at 20% -10%, #96E6FF22, transparent 60%),
                        radial-gradient(900px 500px at 110% 10%, #B794F422, transparent 55%),
                        var(--background-color);
        }
        /* Titres + intro */
        .du-hero h1 {
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: .25rem;
            color: var(--text-color);
        }
        .du-hero .subtitle {
            color: var(--text-color);
            opacity: .85;
            font-size: 1.05rem;
        }

        /* Cartes */
        .du-card {
            border-radius: var(--du-card-radius);
            padding: 18px 18px 16px 18px;
            box-shadow: var(--du-shadow);
            border: 1px solid rgba(128,128,160,.18);
            background: color-mix(in oklab, var(--background-color) 84%, white 16%);
        }
        [data-base-theme="dark"] .du-card {
            background: color-mix(in oklab, var(--background-color) 88%, black 12%);
            border-color: rgba(255,255,255,.12);
        }

        /* Radio pill */
        .du-pills > div div[role="radiogroup"] {
            gap: 12px !important;
        }
        .du-pill {
            border-radius: 999px;
            padding: 10px 16px;
            border: 1.5px solid rgba(128,128,160,.25);
            background: color-mix(in oklab, var(--background-color) 88%, white 12%);
            cursor: pointer;
            transition: .15s ease-in-out;
        }
        [data-base-theme="dark"] .du-pill {
            background: color-mix(in oklab, var(--background-color) 90%, black 10%);
        }
        .du-pill:hover { transform: translateY(-1px); box-shadow: var(--du-shadow); }
        .du-pill .label { font-weight: 700; color: var(--text-color); }
        .du-pill .dot { width:10px; height:10px; border-radius:50%; display:inline-block; margin-right:8px; }

        /* Colors for pills */
        .du-am   .dot { background:#FF6B6B; }
        .du-noon .dot { background:#FFC857; }
        .du-pm   .dot { background:#4BE0AB; }

        /* Bouton principal */
        .du-btn > button[kind="primary"] {
            border-radius: 14px;
            padding: 14px 18px;
            font-weight: 700;
            letter-spacing: .2px;
            background: linear-gradient(90deg, #FF6B6B, #8A5CF6 55%, #47E1A0);
            color: white;
            border: 0;
            box-shadow: 0 10px 18px rgba(138,92,246,.25);
        }
        .du-btn > button[kind="primary"]:hover { filter: brightness(1.03); transform: translateY(-1px); }
        .du-btn > div:has(> button[kind="primary"]) { width:100%; }
        .du-btn > button { width: 100%; }

        /* Textarea lisible */
        textarea {
            background: color-mix(in oklab, var(--background-color) 85%, white 15%) !important;
            color: var(--text-color) !important;
            border-radius: 14px !important;
            border: 1px solid rgba(128,128,160,.25) !important;
        }
        [data-base-theme="dark"] textarea {
            background: color-mix(in oklab, var(--background-color) 92%, black 8%) !important;
        }

        /* Chips */
        .du-chip {
            display:inline-flex; align-items:center; gap:8px;
            padding:6px 10px; border-radius:999px; font-weight:700;
            background: color-mix(in oklab, var(--primary-color) 18%, var(--background-color) 82%);
            color: var(--text-color);
            border: 1px solid rgba(128,128,160,.25);
        }

        /* Sections */
        .du-h2 { font-weight:800; margin: 6px 0 8px 0; }
        .du-h3 { font-weight:800; margin: 16px 0 4px 0; }

        /* Make section titles consistent */
        .block-container { padding-top: 1.5rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
#   PROMPTS & FALLBACKS
# =========================
SLOT_META: Dict[str, Dict[str, str]] = {
    "morning": {
        "title": "Morning — Start bright & small",
        "energy": "fresh start, reduce friction",
        "focus": "one clear tiny win (10–15 min)",
        "tone": "action-first, momentum",
        "prompt": "Morning Boost: one small step beats zero.",
        "emoji": "🌅",
    },
    "midday": {
        "title": "Midday — Reset & refocus",
        "energy": "shake off sluggishness, refuel",
        "focus": "resume one paused task",
        "tone": "calm, pragmatic",
        "prompt": "Midday Check-in: one small step today beats zero.",
        "emoji": "🌤️",
    },
    "evening": {
        "title": "Evening — Slow down & close",
        "energy": "light wrap-up, lower friction",
        "focus": "finish or prep tomorrow",
        "tone": "reflective, kind",
        "prompt": "Evening Wind-down: close small loops, prepare calmly.",
        "emoji": "🌙",
    },
}


def smart_fallback(note: str, slot: str) -> Dict[str, List[str] | str]:
    """
    Coach basique quand l'API n’est pas dispo. Personnalise selon le slot et le contenu.
    """
    low = note.lower()
    plan = []
    analysis = ""

    if "exam" in low or "examen" in low or "test" in low:
        analysis = "Exam context: reduce anxiety with time-boxed study and active recall."
        plan = [
            "Pick 1 weak topic now",
            "Pomodoro 25 minutes (focused)",
            "Create 3 flashcards + review",
        ]
        mantra = "Small wins compound"
    elif "stress" in low or "stressed" in low:
        analysis = "High stress: downshift; cut the task in half and start with a 5-minute micro-action."
        plan = ["Breathe 2 min (box breathing)", "Write next tiny step", "Do 5 minutes now"]
        mantra = "Begin before you think"
    else:
        msg = SLOT_META.get(slot, SLOT_META["morning"])
        analysis = f"{msg['title']}: prioritise one tiny, concrete next step."
        plan = ["Define your single, tiny goal", "Remove one blocker", "Start 5–10 minutes"]
        mantra = "One clear step"

    return {"analysis": analysis, "plan": plan, "mantra": mantra}


def ai_coach(note: str, slot: str) -> Dict[str, List[str] | str]:
    """
    Utilise OpenAI si possible, sinon fallback.
    """
    if not USE_OPENAI:
        return smart_fallback(note, slot)

    system = (
        "You are a concise, empathetic micro-coach. "
        "You must return JSON with keys: analysis (string), plan (array of 3 short steps), mantra (short slogan). "
        "No preamble."
    )
    msg = SLOT_META.get(slot, SLOT_META["morning"])
    user = (
        f"User note: {note}\n"
        f"Context: {msg['title']}. Tone: {msg['tone']}. Focus: {msg['focus']}. "
        "Return JSON only."
    )

    try:
        # GPT-4o mini : compact, créatif
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.9,  # pas de curseur : on pousse la créativité par défaut
        )
        content = resp.choices[0].message.content.strip()
        # sécurise un peu le parsing
        import json
        data = json.loads(content)
        # garde un format propre
        analysis = str(data.get("analysis", "")).strip()
        steps = [str(s).strip() for s in (data.get("plan") or [])][:3]
        mantra = str(data.get("mantra", "")).strip()
        if not steps or len(steps) < 3:
            raise ValueError("Bad plan size → fallback")
        return {"analysis": analysis, "plan": steps, "mantra": mantra}
    except Exception:
        return smart_fallback(note, slot)


# =========================
#           UI
# =========================
def pill(label: str, cls: str) -> str:
    return f'<span class="du-pill {cls}"><span class="dot"></span><span class="label">{label}</span></span>'


def section_title(txt: str):
    st.markdown(f'<h2 class="du-h2">{txt}</h2>', unsafe_allow_html=True)


def small_title(txt: str):
    st.markdown(f'<h3 class="du-h3">{txt}</h3>', unsafe_allow_html=True)


def show_slot_card(slot: str):
    meta = SLOT_META[slot]
    with st.container(border=False):
        st.markdown('<div class="du-card">', unsafe_allow_html=True)
        st.markdown(f"**{meta['emoji']}  {meta['title']}**")
        st.markdown(
            f"""
- ⚡ **Energy**: {meta['energy']}
- 🎯 **Focus**: {meta['focus']}
- 🕒 **Tone**: {meta['tone']}

<small>Prompt used by the coach: *{meta['prompt']}*</small>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="DailyUp", page_icon="🌞", layout="centered")
    inject_theme_css()

    # Détecte thème (pour acces CSS data attr)
    st.markdown(
        f'<script>document.body.setAttribute("data-base-theme", "{st.get_option("theme.base") or "light"}");</script>',
        unsafe_allow_html=True,
    )

    # -------- HERO --------
    st.markdown(
        """
        <div class="du-hero">
            <h1>DailyUp</h1>
            <div class="subtitle">
                De minuscules coups de pouce, des progrès massifs.  
                Choisis ton moment, écris en une phrase ce que tu vis, puis laisse le coach te proposer un **plan en 3 étapes** + un **mantra**.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    # -------- STEP 1 --------
    section_title("Step 1 — Pick your moment")

    col_r, _ = st.columns([1, 5])
    with col_r:
        # radio visuelle
        st.markdown('<div class="du-pills">', unsafe_allow_html=True)
        slot = st.radio(
            "moment",
            ["morning", "midday", "evening"],
            format_func=lambda s: {"morning": "Morning", "midday": "Midday", "evening": "Evening"}[s],
            label_visibility="collapsed",
            horizontal=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # badges jolis sous la radio
    cols = st.columns(3)
    with cols[0]:
        st.markdown(pill("Morning", "du-am"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(pill("Midday", "du-noon"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(pill("Evening", "du-pm"), unsafe_allow_html=True)

    # carte descriptive claire
    show_slot_card(slot)
    st.divider()

    # -------- STEP 2 --------
    section_title("Step 2 — Tell me your note")
    st.caption("One sentence is enough. Example: *“I’m stressed because I have an exam.”*")

    note = st.text_area("note", label_visibility="collapsed", height=120, placeholder="Type here…")

    st.markdown('<div class="du-btn">', unsafe_allow_html=True)
    run = st.button("💬 Analyze & coach me", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # -------- STEP 3 --------
    section_title("Step 3 — Your micro-plan")

    if run:
        if not note.strip():
            st.warning("Please write a short note first.")
            return

        with st.spinner("Thinking…"):
            result = ai_coach(note.strip(), slot)
            time.sleep(0.1)

        # Résultats
        small_title("Analysis")
        st.markdown(result["analysis"])

        small_title("3-Step Plan")
        # On affiche proprement en markdown (évite les erreurs d’HTML + meilleur contraste)
        steps = result["plan"] or []
        st.markdown("\n".join([f"1. {steps[0]}", f"2. {steps[1]}", f"3. {steps[2]}"]))

        small_title("Mantra")
        st.markdown(f'<span class="du-chip">✨ {result["mantra"]}</span>', unsafe_allow_html=True)

        if not USE_OPENAI:
            st.info("⚠️ OpenAI indisponible ou clé absente — réponse générée par le coach local (fallback).")
    else:
        st.caption("Tap the button to get your 3-step plan + mantra.")

    st.write("")  # bottom space


if __name__ == "__main__":
    main()
