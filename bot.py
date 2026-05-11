import os
import sqlite3

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    ContextTypes,
    filters
)

from openai import OpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API = os.getenv("OPENAI_API")

client = OpenAI(api_key=OPENAI_API)

# =========================
# DATABASE
# =========================

conn = sqlite3.connect(
    "memory.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    user_id TEXT,
    role TEXT,
    message TEXT
)
""")

conn.commit()

# =========================
# SAVE
# =========================

def save_message(user_id, role, message):

    cursor.execute(
        "INSERT INTO chats VALUES (?, ?, ?)",
        (user_id, role, message)
    )

    conn.commit()

# =========================
# LOAD HISTORY
# =========================

def load_history(user_id):

    cursor.execute(
        """
        SELECT role, message
        FROM chats
        WHERE user_id=?
        ORDER BY rowid DESC
        LIMIT 10
        """,
        (user_id,)
    )

    rows = cursor.fetchall()

    rows.reverse()

    history = []

    for role, msg in rows:

        history.append({
            "role": role,
            "content": msg
        })

    return history

# =========================
# RESET
# =========================

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.message.from_user.id)

    cursor.execute(
        "DELETE FROM chats WHERE user_id=?",
        (user_id,)
    )

    conn.commit()

    await update.message.reply_text(
        "Đã reset memory."
    )

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "AI BOT ONLINE."
    )

# =========================
# AI CHAT
# =========================

async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = str(update.message.from_user.id)

    text = update.message.text

    bot_username = context.bot.username

    # GROUP MODE

    if update.message.chat.type in [
        "group",
        "supergroup"
    ]:

        if f"@{bot_username}" in text:

            text = text.replace(
                f"@{bot_username}",
                ""
            ).strip()

        elif text.startswith("/ai"):

            text = text.replace(
                "/ai",
                ""
            ).strip()

        else:
            return

    save_message(user_id, "user", text)

    history = load_history(user_id)

    messages = [
        {
            "role": "system",
            "content": "Bạn là AI Telegram nói tiếng Việt tự nhiên."
        }
    ]

    messages.extend(history)

    try:

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages
        )

        reply = response.choices[0].message.content

    except Exception as e:

        reply = f"Lỗi: {e}"

    save_message(
        user_id,
        "assistant",
        reply
    )

    await update.message.reply_text(reply)

# =========================
# RUN BOT
# =========================

app = ApplicationBuilder().token(
    BOT_TOKEN
).build()

app.add_handler(
    CommandHandler("start", start)
)

app.add_handler(
    CommandHandler("reset", reset)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        ai_chat
    )
)

print("BOT ONLINE...")

app.run_polling()