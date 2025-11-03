import re
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import gradio as gr
from transformers import (
    pipeline,
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
)

# =============================
# Storage (persistent memory)
# =============================
STORE_DIR = Path("/tmp/dailyup_store")
STORE_DIR.mkdir(exist_ok=True, parents=True)
PROFILE_PATH = STORE_DIR / "profile.json"
LOG_PATH = STORE_DIR / "journal.json"

DEFAULT_PROFILE = {
    "name": "You",
    "long_term_goal": "Improve consistency and finish key projects.",
    "work_context": "Knowledge work (reports, study, emails).",
    "preferred_tone": "neutral",
}

def load_profile() -> Dict[str, Any]:
    if PROFILE_PATH.exists():
        try:
            return json.loads(PROFILE_PATH.read_text())
        except Exception:
            pass
    PROFILE_PATH.write_text(json.dumps(DEFAULT_PROFILE, indent=2))
    return DEFAULT_PROFILE.copy()

def save_profile(p: Dict[str, Any]):
    PROFILE_PATH.write_text(json.dumps(p, indent=2))

def read_log() -> List[Dict[str, Any]]:
    if LOG_PATH.exists():
        try:
            return json.loads(LOG_PATH.read_text())
        except Exception:
            pass
    LOG_PATH.write_text("[]")
    return []

def append_log(entry: Dict[str, Any]):
    data = read_log()
    data.append(entry)
    LOG_PATH.write_text(json.dumps(data[-300:], indent=2))

def recent_blockers(n: int = 5) -> List[str]:
    """Return last N user messages that had NEGATIVE sentiment."""
    rows = read_log()
    out = []
    for r in reversed(rows):
        if r.get("sentiment") == "NEGATIVE":
            msg = r.get("message", "")
            if msg.startswith("User: "):
                msg = msg[6:]
            out.append(msg)
        if len(out) >= n:
            break
    return list(reversed(out))


# =============================
# Quotes
# =============================
QUOTES = [
    "Start where you are. Use what you have. Do what you can.",
    "Small steps every day become big changes.",
    "You don’t need more time; you need more focus.",
    "Be kind to your mind. You’re doing the best you can.",
    "Your future self is already proud of you.",
    "Action cures fear. Move first.",
    "Consistency beats intensity.",
    "Win the morning, win the day.",
    "Progress, not perfection.",
    "One small step today beats zero.",
]
def random_quote() -> str:
    return f"“{random.choice(QUOTES)}”"


# =============================
# Sentiment (Hugging Face)
# =============================
def _safe_sentiment():
    try:
        return pipeline(
            "sentiment-analysis",
            model="distilbert/distilbert-base-uncased-finetuned-sst-2-english",
        )
    except Exception:
        return lambda x: [{"label": "NEUTRAL", "score": 0.5}]

_sentiment = _safe_sentiment()

def classify(text: str) -> Dict[str, Any]:
    r = _sentiment(text)[0]
    label = str(r.get("label", "NEUTRAL")).upper()
    if label not in ("POSITIVE", "NEGATIVE", "NEUTRAL"):
        label = "NEUTRAL"
    return {"label": label, "score": float(r.get("score", 0.0))}


# =============================
# Coach generator (FLAN-T5)
# =============================
GEN_MODEL_ID = "google/flan-t5-small"
try:
    _gen_tok = AutoTokenizer.from_pretrained(GEN_MODEL_ID)
    _gen_model = AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL_ID)
except Exception:
    _gen_tok = _gen_model = None  # safe fallback

_STOPWORDS = {
    "i","to","the","a","an","and","or","of","in","on","for","with","it","is","am","are",
    "be","been","being","this","that","those","these","my","me","you","your","our","we",
    "have","has","had","do","did","does","will","would","should","can","could","at","as",
    "from","by","about"
}

def _keywords(s: str, k: int = 7) -> str:
    words = [w.strip(".,!?;:()[]{}\"'").lower() for w in s.split()]
    words = [w for w in words if w and w not in _STOPWORDS and len(w) > 2]
    seen, out = set(), []
    for w in words:
        if w not in seen:
            out.append(w); seen.add(w)
        if len(out) >= k:
            break
    return ", ".join(out) if out else "general productivity"

def _smart_plan(user_text: str, slot: str) -> List[str]:
    """Heuristic fallback plan if model fails."""
    topics = _keywords(user_text, k=5)
    if slot == "morning":
        steps = [
            f"Outline {topics} in 3 bullets",
            "Block 25 min (timer on)",
            "Draft first paragraph/solution",
        ]
    elif slot == "midday":
        steps = [
            "Pick the next 10-min step",
            "Mute notifications and start",
            "Write a 2-line progress note",
        ]
    else:
        steps = [
            "List 2 wins + 1 blocker",
            "Extract first step for tomorrow",
            "Prepare materials (file, link, note)",
        ]
    return steps

def _fallback_plan(slot: str, user_text: str, sentiment_label: str, profile: Dict[str, Any]) -> str:
    empathy = {
        "NEGATIVE": "I hear you—let’s make this feel lighter.",
        "POSITIVE": "Great momentum—let’s harness it.",
        "NEUTRAL":  "Got it—let’s keep it simple.",
    }.get(sentiment_label, "I’m with you—let’s keep it simple.")
    steps = _smart_plan(user_text, slot)
    return (
        f"Empathy: {empathy}\n"
        f"Plan (3 steps):\n"
        f"1) {steps[0]}\n2) {steps[1]}\n3) {steps[2]}\n"
        f"Nudge: Begin before you think.\n"
        f"Mantra: small wins compound"
    )

def generate_coach_reply(slot: str, user_text: str, sentiment_label: str, tone: str, profile: Dict[str, Any], last_blockers: List[str]) -> str:
    tone_style = {
        "neutral": "calm, practical",
        "focus":   "laser-focused, directive",
        "calm":    "gentle, de-stressing",
        "energy":  "high-energy, upbeat",
    }.get(tone, "calm, practical")

    topics = _keywords(user_text, k=7)
    blockers_text = "; ".join(last_blockers) if last_blockers else "none noted"
    profile_text = (
        f"Name: {profile.get('name','You')}. "
        f"Long-term goal: {profile.get('long_term_goal')}. "
        f"Work context: {profile.get('work_context')}."
    )

    prompt = f"""
You are "Daily Up", a concise, warm productivity coach. Style: {tone_style}.
Use the profile and blockers to personalize the plan. Avoid clichés and generic filler.
ALWAYS reply with ONLY the following schema (no extra text):

Empathy: <one sentence tailored with the user's topics and/or blockers>
Plan (3 steps):
1) <short, concrete step>
2) <short, concrete step>
3) <short, concrete step>
Nudge: <one punchy sentence to start now>
Mantra: <3-5 words, no quotes>

User context:
- Time of day: {slot}
- Detected sentiment: {sentiment_label}
- User topics: {topics}
- Last blockers: {blockers_text}
- Profile: {profile_text}
- User message: "{user_text}"
""".strip()

    if _gen_tok is None or _gen_model is None:
        return _fallback_plan(slot, user_text, sentiment_label, profile)

    inputs = _gen_tok(prompt, return_tensors="pt")
    outputs = _gen_model.generate(
        **inputs,
        max_new_tokens=240,
        do_sample=True,
        temperature=0.85,
        top_p=0.92,
        num_beams=1,
        no_repeat_ngram_size=3,
    )
    text = _gen_tok.decode(outputs[0], skip_special_tokens=True).strip()

    if "Empathy:" not in text:
        return _fallback_plan(slot, user_text, sentiment_label, profile)
    m = re.search(r"Empathy:.*", text, flags=re.DOTALL)
    cleaned = m.group(0).strip() if m else text
    if not all(k in cleaned for k in ["Empathy:", "Plan", "Nudge:", "Mantra:"]):
        return _fallback_plan(slot, user_text, sentiment_label, profile)

    cleaned = re.sub(r"\n\s*-\s*", "\n", cleaned)
    return cleaned


# =============================
# Prompts
# =============================
MORNING_PROMPT = "What's your main goal for today?"
MIDDAY_PROMPT  = "Quick check-in: how’s it going? Any blocker?"
EVENING_PROMPT = "What’s one thing you’re proud of today?"

def build_message(slot: str, last_user_text: str | None = None) -> Dict[str, Any]:
    base = {
        "morning": ("🌅 Morning Boost", MORNING_PROMPT),
        "midday":  ("🌤️ Midday Check-in", MIDDAY_PROMPT),
        "evening": ("🌙 Evening Reflection", EVENING_PROMPT),
    }
    title, prompt = base.get(slot, base["morning"])
    text = f"{random_quote()}\n\n{prompt}"
    payload = {"title": title, "text": text, "slot": slot, "ts": datetime.utcnow().isoformat()}
    if last_user_text:
        payload["analysis"] = classify(last_user_text)
    return payload


# =============================
# Gradio UI
# =============================
with gr.Blocks(title="Daily Up — Your AI Success Partner") as demo:
    gr.Markdown("# 🌞 Daily Up\nSmall nudges, big progress.")

    with gr.Accordion("⚙️ Coach settings (memory)", open=False):
        prof = load_profile()
        name_inp = gr.Textbox(label="Your name", value=prof.get("name","You"))
        goal_inp = gr.Textbox(label="Long-term goal", value=prof.get("long_term_goal",""))
        ctx_inp = gr.Textbox(label="Work / study context", value=prof.get("work_context",""))
        tone_pref = gr.Dropdown(["neutral","focus","calm","energy"], value=prof.get("preferred_tone","neutral"), label="Preferred tone")
        save_btn = gr.Button("Save profile")
        save_status = gr.Markdown("")

    def on_save(name, goal, ctx, tone_p):
        p = load_profile()
        p.update({"name": name or "You", "long_term_goal": goal, "work_context": ctx, "preferred_tone": tone_p})
        save_profile(p)
        return f"✅ Saved profile for **{p['name']}**."

    save_btn.click(fn=on_save, inputs=[name_inp, goal_inp, ctx_inp, tone_pref], outputs=[save_status])

    with gr.Row():
        with gr.Column():
            slot = gr.Radio(["morning","midday","evening"], value="morning", label="Select your time")
            tone = gr.Dropdown(["neutral","focus","calm","energy"], value="neutral", label="Coach tone (override)")
            get_btn = gr.Button("Get prompt")
            prompt_box = gr.Textbox(label="Prompt", lines=6)

        with gr.Column():
            user_reply = gr.Textbox(label="Your reply", placeholder="Type how you're doing…", lines=3)
            send_btn = gr.Button("Send reply")
            analysis = gr.Markdown("Sentiment: _n/a_")
            suggestion = gr.Markdown("Generated with coach mode")
            coach_plan = gr.Markdown("Coach plan will appear here.")

    journal = gr.Dataframe(headers=["timestamp","slot","message","reply","sentiment","score"], wrap=True, interactive=False)

    def on_get(slot_value: str):
        p = build_message(slot_value)
        append_log({"timestamp": p["ts"], "slot": slot_value, "message": p["text"], "reply": "", "sentiment": "", "score": ""})
        return f"{p['title']}\n\n{p['text']}", read_log()[-30:]

    def on_send(slot_value: str, reply_text: str, tone_value: str):
        prof = load_profile()
        effective_tone = tone_value or prof.get("preferred_tone","neutral")
        p = build_message(slot_value, last_user_text=reply_text)
        s = p.get("analysis", {"label": "NEUTRAL", "score": 0.0})
        plan = generate_coach_reply(slot_value, reply_text, s["label"], effective_tone, prof, recent_blockers(4))
        append_log({"timestamp": datetime.utcnow().isoformat(), "slot": slot_value, "message": f"User: {reply_text}", "reply": plan, "sentiment": s["label"], "score": s["score"]})
        return (f"**Sentiment:** {s['label']} ({s['score']:.2f})", f"_Coach tone: {effective_tone}_", plan, read_log()[-30:])

    get_btn.click(fn=on_get, inputs=[slot], outputs=[prompt_box, journal])
    send_btn.click(fn=on_send, inputs=[slot, user_reply, tone], outputs=[analysis, suggestion, coach_plan, journal])

if __name__ == "__main__":
    demo.launch()
