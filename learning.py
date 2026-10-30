"""Publish the pre-reviewed introductory PPD learning path at most twice per UTC day."""
import datetime as dt
import os
from pathlib import Path
from pipeline import load, save, request_json, API, ROOT

PATH = ROOT / "data" / "learning_path.json"
STATE = ROOT / "data" / "learning_state.json"

def due(state, today):
    return state.get('last_date') != today.isoformat() or state.get('daily_count', 0) < 2

def next_lesson(lessons, state, today):
    index = state.get("next_index", 0)
    if index >= len(lessons) or not due(state, today):
        return None
    return lessons[index]

def run(batch=False):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    channel = os.getenv("TELEGRAM_CHANNEL_ID") or "@PPD_Research_FA"
    today = dt.datetime.now(dt.timezone.utc).date()
    lessons, state = load(PATH, []), load(STATE, {})
    remaining = len(lessons) - state.get("next_index", 0)
    if remaining <= 0 or (not batch and not due(state, today)):
        print("No learning lesson due")
        return
    count_to_send = remaining if batch else 1
    for _ in range(count_to_send):
        index = state.get("next_index", 0)
        lesson = lessons[index]
        message = ("مطالعه مقدماتی PPD | بخش " + str(index + 1) + " از " + str(len(lessons)) +
               "\nموضوع: " + lesson["topic"] + "\n\n" + lesson["title"] +
               "\n\n" + lesson["body"] + "\n\nمنبع برای مطالعه بیشتر: " +
               lesson["source"] + "\n\nاین متن یادداشت آموزشی مقدماتی است؛ نه ترجمه کامل یا مرور نظام‌مند منبع.")
        response = request_json(API + token + "/sendMessage", {"chat_id": channel, "text": message})
        if not response.get("ok"):
            raise RuntimeError("Telegram send not confirmed")
        count = (state.get("daily_count", 0) if state.get("last_date") == today.isoformat() else 0) + 1
        state = {"next_index": index + 1, "daily_count": count, "last_date": today.isoformat(),
                 "last_message_id": response["result"]["message_id"]}
        save(STATE, state)
        print("Published learning lesson:", index + 1)

if __name__ == "__main__":
    import sys
    run(batch=(len(sys.argv) > 1 and sys.argv[1] == "batch"))
