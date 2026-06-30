"""
GET YOUR PLUS — Broadcast Handler
Send messages to all registered users.
"""

from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CallbackQueryHandler, filters,
)
from config import ADMIN_CHAT_ID
from database import get_all_users
from utils.keyboard import admin_keyboard, cancel_keyboard, broadcast_confirm_button

# Conversation states
BROADCAST_CONTENT = 0


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast flow."""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return ConversationHandler.END

    await update.message.reply_text(
        "📢 *Broadcast Message*\n\n"
        "Send the message you want to broadcast to all users.\n"
        "You can send *text* or a *photo with caption*.\n\n"
        "Tap ❌ Cancel to abort.",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return BROADCAST_CONTENT


async def broadcast_receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive text broadcast content."""
    context.user_data["broadcast_text"] = update.message.text
    context.user_data["broadcast_photo"] = None

    users = get_all_users()
    await update.message.reply_text(
        f"📢 *Preview:*\n\n{update.message.text}\n\n"
        f"This will be sent to *{len(users)}* users.",
        parse_mode="Markdown",
        reply_markup=broadcast_confirm_button(),
    )
    return ConversationHandler.END


async def broadcast_receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive photo broadcast content."""
    photo = update.message.photo[-1]
    caption = update.message.caption or ""

    context.user_data["broadcast_text"] = caption
    context.user_data["broadcast_photo"] = photo.file_id

    users = get_all_users()
    await update.message.reply_photo(
        photo=photo.file_id,
        caption=f"📢 *Preview:*\n\n{caption}\n\n"
                f"This will be sent to *{len(users)}* users.",
        parse_mode="Markdown",
        reply_markup=broadcast_confirm_button(),
    )
    return ConversationHandler.END


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all users."""
    query = update.callback_query
    await query.answer("Sending broadcast...")

    text = context.user_data.get("broadcast_text", "")
    photo_id = context.user_data.get("broadcast_photo")
    users = get_all_users()

    success = 0
    failed = 0

    await query.edit_message_text("📢 Sending broadcast... ⏳")

    for user in users:
        try:
            chat_id = user["chat_id"]
            if chat_id == ADMIN_CHAT_ID:
                continue  # Skip admin

            if photo_id:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_id,
                    caption=text,
                    parse_mode="Markdown",
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode="Markdown",
                )
            success += 1
        except Exception:
            failed += 1

    report = (
        f"📢 *Broadcast Complete!*\n\n"
        f"✅ Sent: {success}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total: {success + failed}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=report,
        parse_mode="Markdown",
        reply_markup=admin_keyboard(),
    )

    # Clean up
    context.user_data.pop("broadcast_text", None)
    context.user_data.pop("broadcast_photo", None)


async def broadcast_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Broadcast cancelled.")

    context.user_data.pop("broadcast_text", None)
    context.user_data.pop("broadcast_photo", None)


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel broadcast from text."""
    context.user_data.pop("broadcast_text", None)
    context.user_data.pop("broadcast_photo", None)
    await update.message.reply_text(
        "❌ Broadcast cancelled.", reply_markup=admin_keyboard()
    )
    return ConversationHandler.END


def get_broadcast_handler():
    """Create the broadcast conversation handler."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^📢 Broadcast$") & filters.User(ADMIN_CHAT_ID),
                broadcast_start,
            ),
        ],
        states={
            BROADCAST_CONTENT: [
                MessageHandler(filters.PHOTO, broadcast_receive_photo),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    broadcast_receive_text,
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Cancel$"), cancel_broadcast),
        ],
    )
