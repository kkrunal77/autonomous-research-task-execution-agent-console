import os
import httpx
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("GEMINI_API_KEY")

models = [
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
]

for model in models:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{"parts": [{"text": "Hello, write a 1-word reply."}]}]
    }
    try:
        r = httpx.post(url, json=body, timeout=10)
        print(f"MODEL {model} - STATUS: {r.status_code}")
        if r.status_code != 200:
            print("  ERROR:", r.json().get("error", {}).get("message", ""))
        else:
            print("  REPLY:", r.json()["candidates"][0]["content"]["parts"][0]["text"])
    except Exception as e:
        print(f"MODEL {model} - EXCEPTION: {e}")
