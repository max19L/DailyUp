import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import gradio as gr
from transformers import pipeline

# ================================
# Storage (simple mémoire persistante)
# ================================
STORE_DIR = Path("/tmp/dailyup_store")
STORE_DIR.mkdir(exist_ok=True, parents=True)
PROFILE_PATH = STORE_DIR / "profile.json"
LOG_PATH = STORE_DIR / "journal.json"

DEFAULT_PROFILE = {
    "name": "You",
    "tone": "neutral"  # neutral | supportive | direct | playful
}

def load_json(p: Path, fallback):
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return fallback
    return fallback

def save_json(p: Path, data):
    try:
        p.write_text(json.dumps(data, indent=2))
    except Exception:
        pass

profile = load_json(PROFILE_PATH, DEFAULT_PROFILE)
journal: List[Dict[str, Any]] = load_json(LOG_PATH, [])

# ================================
# Prompts & tiny coach logic
# ================================
MORNING_PROMPTS = [
    ("🌅 Morning Boost", "Tiny start today beats zero. What’s your main goal for this morning?"),
    ("🌄 Focus Sprint", "Pick one task you can move in 15 minutes. Which one?")
]
MIDDAY_PROMPTS = [
    ("🌤️ Midday Check-in", "How’s it going so far? Any blocker you want to clear now?"),
    ("🔁 Momentum", "What’s one small win you can get before the next break?")
]
EVENING_PROMPTS = [
    ("🌙 Evening Reflection", "What are you proud of today? Anything to improve tomorrow?"),
    ("📦 Close the Day", "One tiny step to make tomorrow start easier?")
]

def pick_prompt(slot: str) -> str:
    bag = {
        "morning": MORNING_PROMPTS,
        "midday": MIDDAY_PROMPTS,
        "evening": EVENING_PROMPTS
    }[slot]
    title, q = random.choice(bag)
    return f"**{title}**\n\n{q}"

# ================================
# Lightweight AI
# ================================
SENTIMENT = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

GEN = pipeline(
    "text2text-generation",
    model="google/flan-t5-small",
    max_new_tokens=120
)

def analyze_sentiment(text: str) -> Dict[str, Any]:
    if not text.strip():
        return {"label": "NEUTRAL", "score": 0.0}
    res = SENTIMENT(text[:512])[0]
    return {"label": res["label"], "score": float(res["score"])}

def make_plan(slot: str, user_text: str, tone: str) -> str:
    tone_map = {
        "neutral": "calm and concise",
        "supportive": "warm and encouraging",
        "direct": "clear and no-nonsense",
        "playful": "light, upbeat and friendly"
    }
    style = tone_map.get(tone, "calm and concise")

    prompt = (
        "You are a personal micro-coach. "
        f"Write a short 3-step plan in a {style} tone. "
        "Be ultra actionable, 1 line per step, then end with a 3-5 word mantra. "
        f"Context: time_of_day={slot}. User said: {user_text!r}"
    )

    out = GEN(prompt)[0]["generated_text"].strip()
    # nettoyer un peu les puces éventuelles
    lines = [ln.strip(" -•") for ln in out.splitlines() if ln.strip()]
    return "\n".join(lines[:6])

def build_entry(slot: str, user_text: str, tone: str) -> Dict[str, Any]:
    sent = analyze_sentiment(user_text)
    plan = make_plan(slot, user_text, tone)
    stamp = datetime.utcnow().isoformat()

    entry = {
        "timestamp": stamp,
        "slot": slot,
        "message": user_text,
        "sentiment": sent["label"],
        "score": round(sent["score"], 2),
        "plan": plan
    }
    return entry

def append_log(entry: Dict[str, Any]):
    journal.append(entry)
    save_json(LOG_PATH, journal)

# ================================
# UI (Gradio Blocks + custom CSS)
# ================================

CUSTOM_CSS = """
:root {
  --bg: #0b1020;
  --panel: rgba(18, 24, 42, 0.6);
  --card: rgba(24, 31, 56, 0.55);
  --stroke: rgba(148, 163, 184, 0.12);
  --text: #e6e7eb;
  --muted: #9aa4b2;
  --accent: #6EE7F9;       /* cyan */
  --accent-2: #A78BFA;     /* purple */
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --radius: 16px;
}

.gradio-container, body, html { background: radial-gradient(1200px 700px at 20% -10%, #101735 0%, var(--bg) 40%) fixed; color: var(--text); }

#root .container { max-width: 1200px !important; }
* { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, "SF Pro Display", sans-serif; }

.neoglass {
  background: var(--panel);
  backdrop-filter: blur(10px);
  border: 1px solid var(--stroke);
  box-shadow: 0 20px 40px rgba(0,0,0,0.35), inset 0 1px rgba(255,255,255,0.05);
  border-radius: var(--radius);
}

.neoglass-card {
  background: var(--card);
  backdrop-filter: blur(10px);
  border: 1px solid var(--stroke);
  border-radius: var(--radius);
  padding: 14px 16px;
}

.h1 {
  font-weight: 700;
  letter-spacing: 0.4px;
  font-size: 28px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.btn-primary button {
  background: linear-gradient(90deg, var(--accent), var(--accent-2)) !important;
  color: #09101f !important;
  border: none !important;
  box-shadow: 0 10px 30px rgba(103, 232, 249, 0.25), 0 2px 0 rgba(0,0,0,0.15) inset;
}
.btn-secondary button {
  background: transparent !important;
  color: var(--text) !important;
  border: 1px solid var(--stroke) !important;
}
.badge {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 6px 10px; border-radius: 999px; font-size: 12px;
  border: 1px solid var(--stroke); color: var(--muted);
}
.badge .dot { width: 8px; height: 8px; border-radius: 50%; }
.dot-pos { background: var(--success); }
.dot-neg { background: var(--danger); }
.dot-neu { background: var(--warning); }
"""

with gr.Blocks(css=CUSTOM_CSS, fill_height=True, theme=gr.themes.Soft(primary_hue="cyan", neutral_hue="slate")) as demo:
    # hidden state
    st_profile = gr.State(profile)
    st_log = gr.State(journal)

    # Header
    with gr.Row(elem_classes="neoglass", elem_id="top"):
        gr.Markdown("## <span class='h1'>Daily Up</span><br><span style='color:var(--muted)'>Small nudges, big progress.</span>")

    with gr.Row(equal_height=True):
        # Left column - settings & prompt
        with gr.Column(scale=5, elem_classes="neoglass"):
            with gr.Accordion("Coach settings (memory)", open=False, elem_classes="neoglass-card"):
                tone_override = gr.Dropdown(
                    ["neutral", "supportive", "direct", "playful"], value=profile.get("tone", "neutral"),
                    label="Default coach tone"
                )
                def save_tone(t):
                    profile["tone"] = t
                    save_json(PROFILE_PATH, profile)
                    return gr.update()
                tone_override.change(save_tone, tone_override, None)

            slot = gr.Radio(["morning", "midday", "evening"], value="morning", label="Select your time")
            get_btn = gr.Button("Get prompt", elem_classes="btn-primary")
            prompt_box = gr.Markdown(elem_classes="neoglass-card", label="Prompt")

        # Right column - reply / analysis
        with gr.Column(scale=6, elem_classes="neoglass"):
            user_reply = gr.Textbox(lines=6, label="Your reply", placeholder="Type how you're doing…", elem_classes="neoglass-card")
            send_btn = gr.Button("Send reply", elem_classes="btn-secondary")
            # small badges area
            badges = gr.Markdown(value="", elem_classes="neoglass-card")
            plan_md = gr.Markdown(value="", elem_classes="neoglass-card")

    # Journal (simple table)
    with gr.Row(elem_classes="neoglass"):
        gr.Markdown("### Journal", elem_classes="neoglass-card")
    with gr.Row(elem_classes="neoglass"):
        log_table = gr.Dataframe(
            headers=["timestamp", "slot", "message", "sentiment", "score", "plan"],
            row_count=(0, "dynamic"),
            wrap=True,
            interactive=False,
            elem_classes="neoglass-card"
        )

    # ===== Callbacks =====
    def on_get(slot_value: str):
        return pick_prompt(slot_value)

    get_btn.click(on_get, inputs=slot, outputs=prompt_box)

    def on_send(slot_value: str, reply_text: str, prof: Dict[str, Any], cur_log: List[Dict[str, Any]]):
        if not reply_text.strip():
            return (
                gr.update(),
                "⚪ <span class='badge'><span class='dot dot-neu'></span>Sentiment: n/a</span>",
                "Please write a short message.",
                cur_log
            )
        # tone final
        tone = prof.get("tone", "neutral")
        entry = build_entry(slot_value, reply_text, tone)
        append_log(entry)
        cur_log.append(entry)

        # sentiment badge
        dot = {
            "POSITIVE": "dot-pos",
            "NEGATIVE": "dot-neg"
        }.get(entry["sentiment"], "dot-neu")
        badge_html = f"<span class='badge'><span class='dot {dot}'></span>Sentiment: {entry['sentiment']} ({entry['score']})</span>"

        # Plan
        plan = f"**Coach plan**\n\n" + "\n".join([f"- {ln}" for ln in entry["plan"].splitlines()])

        # table rows
        rows = [[e["timestamp"], e["slot"], e["message"], e["sentiment"], e["score"], e["plan"]] for e in cur_log]
        return gr.update(value=""), badge_html, plan, rows

    send_btn.click(
        on_send,
        inputs=[slot, user_reply, st_profile, st_log],
        outputs=[user_reply, badges, plan_md, log_table]
    )

# -------------------------
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")   # laisse Codespaces choisir le port libre
