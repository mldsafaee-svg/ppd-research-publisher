"""Publish the pre-reviewed introductory PPD learning path at most once every 7 days."""
import datetime as dt
import os
from pathlib import Path
from pipeline import load, save, request_json, API, ROOT

PATH = ROOT / "data" / "learning_path.json"
STATE = ROOT / "data" / "learning_state.json"

def due(state, today):
    if not state.get("last_date"):
        return True
    return (today - dt.date.fromisoformat(state["last_date"])).days >= 7

def next_lesson(lessons, state, today):
    index = state.get("next_index", 0)
    if index >= len(lessons) or not due(state, today):
        return None
    return lessons[index]

def run():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    channel = os.getenv("TELEGRAM_CHANNEL_ID") or "@PPD_Research_FA"
    today = dt.datetime.now(dt.timezone.utc).date()
    lessons, state = load(PATH, []), load(STATE, {})
    lesson = next_lesson(lessons, state, today)
    if not lesson:
        print("No learning lesson due")
        return
    index = state.get("next_index", 0)
    message = ("مطالعه مقدماتی PPD | بخش " + str(index + 1) + " از " + str(len(lessons)) +
               "\nموضوع: " + lesson["topic"] + "\n\n" + lesson["title"] +
               "\n\n" + lesson["body"] + "\n\nمنبع برای مطالعه بیشتر: " +
               lesson["source"] + "\n\nاین متن یادداشت آموزشی مقدماتی است؛ نه ترجمه کامل یا مرور نظام‌مند منبع.")
    response = request_json(API + token + "/sendMessage", {"chat_id": channel, "text": message})
    if not response.get("ok"):
        raise RuntimeError("Telegram send not confirmed")
    save(STATE, {"next_index": index + 1, "last_date": today.isoformat(),
                 "last_message_id": response["result"]["message_id"]})
    print("Published learning lesson:", index + 1)

if __name__ == "__main__":
    run()
