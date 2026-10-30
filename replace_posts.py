"""Replace the ten original channel posts with expanded Persian versions.
The message IDs were supplied explicitly by the channel owner.
"""
import os
from pipeline import API, ROOT, load, save, request_json

LESSONS = ROOT / "data" / "learning_path.json"
STATE = ROOT / "data" / "replacement_state.json"
IDS = list(range(3, 13))

def message_for(item, index, total):
    return ("مطالعه مقدماتی افسردگی پس از زایمان | بخش " + str(index + 1) +
            " از " + str(total) + "\n\n" + item["topic"] + " — " +
            item["title"] + "\n\n" + item["body"] +
            "\n\nمنبع و اطلاعات تکمیلی: " + item["source"] +
            "\n\nیادداشت تحلیلی فارسی؛ نه ترجمه کامل مقاله یا توصیه پزشکی.")

def replace():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is missing")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID") or "@PPD_Research_FA"
    lessons = load(LESSONS, [])
    if len(lessons) != len(IDS):
        raise RuntimeError("Expected exactly 10 lessons")
    state = load(STATE, {"completed": []})
    completed = set(state["completed"])
    for i, (message_id, item) in enumerate(zip(IDS, lessons)):
        if message_id in completed:
            continue
        response = request_json(API + token + "/editMessageText", {
            "chat_id": channel, "message_id": message_id,
            "text": message_for(item, i, len(lessons)),
            "disable_web_page_preview": True})
        if not response.get("ok"):
            raise RuntimeError("Telegram did not confirm edit for message " + str(message_id))
        completed.add(message_id)
        save(STATE, {"completed": sorted(completed)})
        print("Edited Telegram message:", message_id)
    print("Confirmed replacements:", len(completed))

if __name__ == "__main__":
    replace()
