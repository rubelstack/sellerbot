"""
GET YOUR PLUS — Main Bot Entry Point
Initializes the bot, registers all handlers, and starts polling.
Made by Rubel
"""

import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters,
)
from config import BOT_TOKEN, ADMIN_CHAT_ID, VERSION
from database import init_db, upsert_user

from handlers.customer import (
    start_command, show_products, show_my_purchases,
    show_warranty, check_warranty_input,
    help_chat, forward_help_message,
    handle_buy_callback,
    handle_tx_hash_input, handle_payment_done, handle_payment_cancel,
    handle_details_callback, handle_view_card_callback,
    handle_claim_warranty,
    handle_apply_coupon_callback, handle_buy_no_coupon_callback,
    handle_confirm_buy_coupon_callback, handle_coupon_code_input,
)
from handlers.admin import (
    admin_start, manage_products, show_inventory,
    show_orders, show_users, show_payment_methods,
    handle_toggle_product, handle_edit_product,
    handle_edit_field_callback, handle_edit_value,
    handle_edit_back,
    handle_delete_product, handle_delete_confirm, handle_delete_cancel,
    handle_order_status_callback,
    handle_admin_confirm_payment, handle_admin_reject_payment,
    start_chat_with_customer, close_admin_chat,
    forward_admin_message_to_customer, forward_customer_message_to_admin,
    handle_pm_delete, handle_pm_toggle,
    get_add_product_handler, get_add_payment_handler, is_admin,
    show_coupons, handle_coupon_delete, get_add_coupon_handler,
)
from handlers.broadcast import (
    get_broadcast_handler,
    broadcast_confirm, broadcast_cancel,
)
from utils.keyboard import customer_keyboard, admin_keyboard


# ─── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Message Router ──────────────────────────────────────────────────

async def handle_message(update: Update, context):
    """Route text messages based on user type and context."""
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    text = update.message.text.strip()
    btn_text = text.replace("\ufe0f", "")
    user_id = user.id

    # Register user
    upsert_user(user_id, user.username, user.first_name)

    # ─── Check if active chat session exists ───
    # Admin active chat session
    if is_admin(user_id):
        # Admin wants to close chat
        if btn_text == "🔚 Close Chat":
            await close_admin_chat(update, context)
            return
        
        # Admin is typing message to customer
        in_chat = await forward_admin_message_to_customer(update, context)
        if in_chat:
            return
    else:
        # Customer sending message to admin during active chat
        in_chat = await forward_customer_message_to_admin(update, context)
        if in_chat:
            return

    # ─── Check if awaiting edit input (admin) ───
    if is_admin(user_id) and context.user_data.get("edit_product_id"):
        handled = await handle_edit_value(update, context)
        if handled:
            return

    # ─── Check if awaiting tx hash input (customer) ───
    if context.user_data.get("awaiting_tx_hash"):
        handled = await handle_tx_hash_input(update, context)
        if handled:
            return

    # ─── Check if awaiting coupon code input (customer) ───
    if context.user_data.get("awaiting_coupon_code"):
        handled = await handle_coupon_code_input(update, context)
        if handled:
            return

    # ─── Check if awaiting warranty check (customer) ───
    if context.user_data.get("awaiting_warranty_check"):
        handled = await check_warranty_input(update, context)
        if handled:
            return

    # ─── Check if awaiting help message (customer) ───
    if context.user_data.get("awaiting_help_message"):
        handled = await forward_help_message(update, context)
        if handled:
            return

    # ─── Admin button routing ───
    if is_admin(user_id):
        if btn_text == "📦 Manage Products":
            await manage_products(update, context)
            return
        elif btn_text == "📊 Inventory":
            await show_inventory(update, context)
            return
        elif btn_text == "📋 Orders":
            await show_orders(update, context)
            return
        elif btn_text == "💳 Payment Methods":
            await show_payment_methods(update, context)
            return
        elif btn_text == "🎟️ Coupons":
            await show_coupons(update, context)
            return
        elif btn_text == "👥 Users":
            await show_users(update, context)
            return

    # ─── Customer button routing ───
    if btn_text == "🛍 Products":
        await show_products(update, context)
    elif btn_text == "🛒 My Purchases":
        await show_my_purchases(update, context)
    elif btn_text == "🛡 Warranty":
        await show_warranty(update, context)
    elif btn_text == "💬 Help / Chat":
        await help_chat(update, context)
    else:
        # Unknown text — show appropriate keyboard
        if is_admin(user_id):
            await update.message.reply_text(
                "Use the buttons below to navigate 👇",
                reply_markup=admin_keyboard(),
            )
        else:
            await update.message.reply_text(
                "Use the buttons below to navigate 👇",
                reply_markup=customer_keyboard(),
            )


async def handle_photo_message(update: Update, context):
    """Handle photo messages (for admin edit image and active chats)."""
    user_id = update.effective_user.id

    # Active chat forwarding
    if is_admin(user_id):
        in_chat = await forward_admin_message_to_customer(update, context)
        if in_chat:
            return
    else:
        in_chat = await forward_customer_message_to_admin(update, context)
        if in_chat:
            return

    if is_admin(user_id) and context.user_data.get("edit_is_image"):
        await handle_edit_value(update, context)
        return


# ─── Callback Router ────────────────────────────────────────────────

async def handle_callback(update: Update, context):
    """Route inline button callback queries."""
    query = update.callback_query
    data = query.data

    if data.startswith("details_"):
        await handle_details_callback(update, context)
    elif data.startswith("view_card_"):
        await handle_view_card_callback(update, context)
    elif data.startswith("buy_"):
        await handle_buy_callback(update, context)
    elif data.startswith("apply_coupon_"):
        await handle_apply_coupon_callback(update, context)
    elif data.startswith("buy_no_coupon_"):
        await handle_buy_no_coupon_callback(update, context)
    elif data.startswith("conf_buy_cp_"):
        await handle_confirm_buy_coupon_callback(update, context)
    elif data.startswith("cpdel_"):
        await handle_coupon_delete(update, context)
    elif data.startswith("claimw_"):
        await handle_claim_warranty(update, context)
    elif data.startswith("paydone_"):
        await handle_payment_done(update, context)
    elif data.startswith("paycancel_"):
        await handle_payment_cancel(update, context)
    elif data.startswith("toggle_"):
        await handle_toggle_product(update, context)
    elif data.startswith("edit_"):
        await handle_edit_product(update, context)
    elif data.startswith(("ename_", "edesc_", "eprice_", "estock_", "ewdays_", "ewinfo_", "eimg_")):
        await handle_edit_field_callback(update, context)
    elif data.startswith("eback_"):
        await handle_edit_back(update, context)
    elif data.startswith("del_"):
        await handle_delete_product(update, context)
    elif data.startswith("delconfirm_"):
        await handle_delete_confirm(update, context)
    elif data.startswith("delcancel_"):
        await handle_delete_cancel(update, context)
    elif data.startswith("aconfirm_"):
        await handle_admin_confirm_payment(update, context)
    elif data.startswith("areject_"):
        await handle_admin_reject_payment(update, context)
    elif data.startswith("achat_"):
        await start_chat_with_customer(update, context)
    elif data.startswith("pmdel_"):
        await handle_pm_delete(update, context)
    elif data.startswith("pmtoggle_"):
        await handle_pm_toggle(update, context)
    elif data.startswith(("oconfirm_", "oshipped_", "ocomplete_")):
        await handle_order_status_callback(update, context)
    elif data == "broadcast_confirm":
        await broadcast_confirm(update, context)
    elif data == "broadcast_cancel":
        await broadcast_cancel(update, context)


# ─── Main ────────────────────────────────────────────────────────────

def main():
    """Initialize and run the bot."""
    # Initialize database
    init_db()
    logger.info("Database initialized.")

    # Build application (job-queue is enabled automatically if requirements.txt contains python-telegram-bot[job-queue])
    app = Application.builder().token(BOT_TOKEN).build()

    # ─── Conversation handlers (must be added FIRST) ───
    app.add_handler(get_add_product_handler())
    app.add_handler(get_add_payment_handler())
    app.add_handler(get_add_coupon_handler())
    app.add_handler(get_broadcast_handler())

    # ─── Command handlers ───
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_start))

    # ─── Callback query handler ───
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ─── Photo/Media message handler ───
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_photo_message))

    # ─── General text message handler (catch-all, must be LAST) ───
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ─── Start polling ───
    logger.info(f"🚀 GET YOUR PLUS Bot v{VERSION} is starting...")
    logger.info(f"Admin Chat ID: {ADMIN_CHAT_ID}")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
