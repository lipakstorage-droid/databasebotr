import telebot
import os
import json
import random
import string
import time

TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

bot = telebot.TeleBot(TOKEN)

DB_FILE = "db.json"
TEMP_BATCH = {}

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

db = load_db()

# Collect multiple files within 10 seconds window
@bot.message_handler(content_types=['document', 'video', 'photo'])
def collect_files(message):
    user_id = message.from_user.id

    file_id = None
    if message.document:
        file_id = message.document.file_id
    elif message.video:
        file_id = message.video.file_id
    elif message.photo:
        file_id = message.photo[-1].file_id

    # Forward to storage channel
    bot.forward_message(CHANNEL_ID, message.chat.id, message.message_id)

    if user_id not in TEMP_BATCH:
        TEMP_BATCH[user_id] = {
            "files": [],
            "time": time.time()
        }

    TEMP_BATCH[user_id]["files"].append(file_id)
    TEMP_BATCH[user_id]["time"] = time.time()

    bot.reply_to(message, "File added to batch...")

# Background checker to finalize batch
def finalize_batches():
    while True:
        now = time.time()
        for user_id in list(TEMP_BATCH.keys()):
            if now - TEMP_BATCH[user_id]["time"] > 10:
                files = TEMP_BATCH[user_id]["files"]
                code = generate_code()
                db[code] = files
                save_db(db)

                bot.send_message(user_id, f"✅ Files stored!\nYour Code: `{code}`", parse_mode="Markdown")
                del TEMP_BATCH[user_id]
        time.sleep(5)

import threading
threading.Thread(target=finalize_batches, daemon=True).start()

# User sends code
@bot.message_handler(func=lambda m: True)
def send_files(message):
    code = message.text.strip().upper()
    if code in db:
        for f in db[code]:
            bot.send_document(message.chat.id, f)
    else:
        bot.reply_to(message, "❌ Invalid code")

print("Bot running...")
bot.infinity_polling()
