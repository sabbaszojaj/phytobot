import logging
import datetime
import os
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from collections import deque

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "-1001234567890"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "328462927"))
MAX_QUESTIONS = 100
question_queue = deque(maxlen=MAX_QUESTIONS)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام! ربات دارویی فعال است.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if message.chat.type in ["group", "supergroup"] and message.reply_to_message is None:
        username = message.from_user.username or message.from_user.full_name
        text = message.text.strip()
        question_queue.append({
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "username": username,
            "text": text,
            "date": datetime.datetime.now()
        })

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message.reply_to_message:
        return
    for q in question_queue:
        if q["message_id"] == message.reply_to_message.message_id:
            await send_combined_message(context, q, message.voice.file_id)
            break

async def send_combined_message(context: ContextTypes.DEFAULT_TYPE, question, voice_file_id):
    date_str = question["date"].strftime("%Y/%m/%d")
    username = question["username"]
    hashtags = extract_hashtags(question["text"])
    caption = (
        f"🗣 سؤال توسط @{username if username else 'کاربر'}:\n"
        f"❓ {question['text']}\n\n"
        f"🎧 پاسخ دکتر زجاجی:\n"
        f"📅 تاریخ: {date_str}\n"
        f"#مشاوره_دارویی #داروخانه_آنلاین {' '.join(hashtags)}"
    )
    await context.bot.send_voice(
        chat_id=question["chat_id"],
        voice=voice_file_id,
        caption=caption
    )

def extract_hashtags(text):
    words = text.lower().split()
    return [f"#{w}" for w in words if len(w) > 3][:5]

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    await app.bot.delete_webhook(drop_pending_updates=True)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    scheduler = AsyncIOScheduler()
    scheduler.start()

    logging.info("🤖 ربات فعال است...")
    await app.run_polling()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "event loop is already running" in str(e):
            loop = asyncio.get_event_loop()
            loop.create_task(main())
            loop.run_forever()
        else:
            raise
