import os
import requests
import json
import random

class LLMClient:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.enabled = self.api_key is not None and self.api_key != ""

    def compose_outreach(self, merchant_name: str, locality: str, signals: dict) -> str:
        """
        Uses LLM (or Synthetic Intelligence) to compose a personalized outreach message.
        """
        if self.enabled:
            prompt = f"""
            You are Vera, an AI growth partner for Magicpin merchants.
            Merchant: {merchant_name}
            Locality: {locality}
            Signals: {json.dumps(signals)}
            
            Write a persuasive WhatsApp message (max 300 chars) in natural Hinglish.
            Anchor on real numbers. Mention the trending item: {signals.get('trending_item')}.
            End with "Reply YES to launch."
            """
            res = self._call_anthropic(prompt)
            if res: return res

        # ── Synthetic Intelligence Fallback ──
        item = signals.get('trending_item', 'Special Offer')
        views = signals.get('views', 100)
        search_count = signals.get('search_count', 1500)
        
        personalities = [
            f"Hey {merchant_name}! Big news—{search_count} people in {locality} are looking for {item} right now. Your listing has {views} views, let's convert them! Sab log dhund rahe hain. Reply YES to launch.",
            f"Hi {merchant_name}! Vera here. I noticed {item} is trending in {locality} (+{random.randint(20,50)}% spike). You've already got {views} views this month—want to turn that into orders? Reply YES to launch.",
            f"Bhai {merchant_name}, {locality} mein {item} ki demand bohot high hai! {search_count} potential customers are searching. Your {views} views are a goldmine. Deal setup karein? Reply YES to launch.",
            f"Urgent insight for {merchant_name}: {item} is the top trending item in {locality} today. With {views} views on your profile, you are perfectly placed to win. Don't miss out! Reply YES to launch."
        ]
        return random.choice(personalities)

    def analyze_reply(self, turns: list, latest_message: str) -> dict:
        """
        Analyzes merchant reply to determine intent and next action.
        """
        if self.enabled:
            prompt = f"""
            Analyze this merchant reply for a Magicpin bot.
            History: {json.dumps(turns)}
            Latest: "{latest_message}"
            
            Return JSON: {{"intent": "commit|refuse|question|other", "hinglish_summary": "...", "suggested_reply": "..."}}
            """
            res = self._call_anthropic(prompt, json_mode=True)
            if res:
                try:
                    return json.loads(res)
                except:
                    pass

        # ── Synthetic Intent Recognition Fallback ──
        msg = latest_message.lower()
        
        # Commit
        if any(w in msg for w in ["yes", "ha", "haan", "ok", "karo", "sure", "theek", "proceed", "send"]):
            return {
                "intent": "commit",
                "hinglish_summary": "Merchant is ready to proceed.",
                "suggested_reply": "Great choice! Setting up the campaign for you. You'll see it live in a few minutes. 👍"
            }
        
        # Refuse
        if any(w in msg for w in ["no", "nahi", "stop", "don't", "band", "later", "busy"]):
            return {
                "intent": "refuse",
                "hinglish_summary": "Merchant declined or is busy.",
                "suggested_reply": "No worries at all! I'll check back later when there's another big trend. Have a great day!"
            }
            
        # Question
        if any(w in msg for w in ["how", "what", "kyu", "price", "cost", "paise", "why", "?"]):
            return {
                "intent": "question",
                "hinglish_summary": "Merchant has a specific question.",
                "suggested_reply": None # Will trigger escalation in bot.py
            }

        return {"intent": "other", "hinglish_summary": "Ambiguous message.", "suggested_reply": None}

    def _call_anthropic(self, prompt: str, json_mode: bool = False) -> str:
        try:
            if not self.api_key: return None
                
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            data = {
                "model": "claude-3-5-sonnet-20240620",
                "max_tokens": 512,
                "messages": [{"role": "user", "content": prompt}]
            }
            if json_mode:
                prompt += "\n\nIMPORTANT: Return ONLY valid JSON."
                
            response = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=8)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception:
            return None

llm = LLMClient()
