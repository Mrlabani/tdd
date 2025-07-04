import os
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import ImportContacts
from telethon.tl.types import InputPhoneContact
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

API_ID = int(os.environ.get("API_ID", 26555614))
API_HASH = os.environ.get("API_HASH", "93bf5cde23435bb236066dcd7358ae6a")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7732753230:AAFiR83Tpy59PBsy1gNIwRjiJ5sQpCXuEr4")
SESSION_FILE = "session.txt"

client = None

# ========== Flask Health Check ==========
flask_app = Flask(__name__)

@flask_app.route("/health")
def health():
    return "✅ Bot is alive", 200

def run_flask():
    flask_app.run(host="0.0.0.0", port=8080)

# ========== Telegram Bot ==========
user_check_count = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📲 Send /login to connect your Telegram client.\nThen send phone numbers (max 100 per session).")

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            session_str = f.read().strip()
        client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
    else:
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        await client.start(
            phone=lambda: input("📞 Phone: "),
            code_callback=lambda: input("📩 Code: "),
            password=lambda: input("🔒 2FA Password: ") if client.is_user_authorized() else None,
        )
        session_str = client.session.save()
        with open(SESSION_FILE, "w") as f:
            f.write(session_str)

    await update.message.reply_text("✅ Telegram client logged in successfully.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    user_id = update.effective_user.id

    if client is None:
        await update.message.reply_text("❌ Please /login first.")
        return

    if user_id not in user_check_count:
        user_check_count[user_id] = 0

    numbers = update.message.text.strip().split()
    if len(numbers) + user_check_count[user_id] > 100:
        await update.message.reply_text("🚫 Limit exceeded! Only 100 checks per user allowed.")
        return

    for number in numbers:
        if not number.isdigit() or len(number) < 7:
            await update.message.reply_text(f"❌ Invalid number: {number}")
            continue

        try:
            result = await client(ImportContacts([
                InputPhoneContact(client_id=0, phone=number, first_name="Check", last_name="User")
            ]))
            if result.users:
                await update.message.reply_text(f"✅ Found: {number}")
            else:
                await update.message.reply_text(f"❌ Not Found: {number}")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error checking {number}: {e}")

        user_check_count[user_id] += 1

# ========== Run Bot ==========
def main():
    Thread(target=run_flask).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
