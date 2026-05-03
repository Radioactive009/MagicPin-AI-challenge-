from database import db
import re

AUTO_REPLY_RE = re.compile(
    r"thank you for contacting|our team will respond|automated (assistant|reply)|"
    r"i am an? automated|aapki madad ke liye shukriya",
    re.IGNORECASE
)

OPT_OUT_RE = re.compile(
    r"\b(stop|unsubscribe|not interested|don'?t message|nahi chahiye|band karo)\b",
    re.IGNORECASE
)

COMMIT_RE = re.compile(
    r"\b(yes|yeah|haan|ok|okay|sure|go ahead|let'?s do it|chalte hain|theek hai|"
    r"karo|kar do|send it|proceed|confirm|start|great)\b",
    re.IGNORECASE
)

def respond(conv_id: str, merchant_id: str, merchant_message: str) -> dict:
    """
    Given conversation id + merchant's latest message, return next action dict.
    """
    if db.is_conv_ended(conv_id):
        return {"action": "end", "rationale": "Conversation already ended."}

    # Record the turn
    db.add_turn(conv_id, "merchant", merchant_message)
    turns = db.get_turns(conv_id)
    
    # Count auto-replies
    auto_reply_count = 0
    for t in turns:
        if t["from"] == "merchant" and AUTO_REPLY_RE.search(t["msg"]):
            auto_reply_count += 1
        else:
            break # consecutive only

    # Opt-out
    if OPT_OUT_RE.search(merchant_message):
        db.end_conversation(conv_id)
        return {"action": "end", "rationale": "Merchant opted out. Closing."}

    # Auto-reply escalation
    if AUTO_REPLY_RE.search(merchant_message):
        if auto_reply_count >= 3:
            db.end_conversation(conv_id)
            return {"action": "end", "rationale": "Auto-reply 3× in a row; closing."}
        elif auto_reply_count == 2:
            return {"action": "wait", "wait_seconds": 86400,
                    "rationale": "Second consecutive auto-reply; backing off 24h."}
        else:
            body = "Looks like an auto-reply 🙂 When the owner sees this, reply YES to continue."
            db.add_turn(conv_id, "vera", body)
            return {"action": "send", "body": body, "cta": "binary_yes_no",
                    "rationale": "First auto-reply; leaving note for owner."}

    # Intent transition
    if COMMIT_RE.search(merchant_message):
        body = "Bढ़िया! Proceeding now — drafting the campaign. I'll send the preview in 60 seconds. Reply CONFIRM to go live."
        db.add_turn(conv_id, "vera", body)
        return {
            "action": "send",
            "body": body,
            "cta": "binary_confirm_cancel",
            "rationale": "Merchant committed; switched to action mode immediately.",
        }

    # Default: continue conversation (handled by bot.py)
    return {"action": "continue", "rationale": "Continue to engine logic."}
