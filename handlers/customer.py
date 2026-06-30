"""
GET YOUR PLUS — Customer Handlers
Handles all customer-facing interactions: browsing, purchasing, payments, warranties, help.
Made by Rubel
"""

import os
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_CHAT_ID
from database import (
    upsert_user, get_active_products, get_product, get_user_orders,
    get_order_by_id, create_order, get_active_payment_methods,
    set_transaction_hash, cancel_expired_order, get_user,
)
from utils.keyboard import (
    customer_keyboard, product_buy_button, buy_confirm_button,
    payment_done_button, admin_order_notification_buttons,
)
from utils.helpers import (
    format_price, format_date, warranty_status_text, format_date_short,
)


# ─── Payment timeout (seconds) ──────────────────────────────────────
PAYMENT_TIMEOUT = 600  # 10 minutes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command for customers."""
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    welcome = (
        f"👋 Welcome to *GET YOUR PLUS*, {user.first_name}!\n\n"
        "🛍 Browse our products and purchase instantly.\n"
        "🛒 Track your orders and warranties.\n"
        "💬 Need help? We're here for you!\n\n"
        "Use the buttons below to navigate 👇"
    )
    await update.message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=customer_keyboard()
    )


# ─── Product Browsing (Compact) ─────────────────────────────────────

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available products to the customer (compact cards)."""
    products = get_active_products()

    if not products:
        await update.message.reply_text(
            "😔 No products available right now. Check back later!",
            reply_markup=customer_keyboard(),
        )
        return

    for product in products:
        # Stock status
        stock_status = f"🟢 {product['stock']} units" if product["stock"] > 0 else "🔴 Out of Stock"

        # Product details compilation
        desc = product['description'] if product['description'] else "No description available."
        warranty = f"🛡️ {product['warranty_days']} Days Warranty" if product['warranty_days'] > 0 else "🛡️ No Warranty"
        
        # Elegant decorated card layout
        caption = (
            f"🛍️ *{product['name']}*\n"
            f"💵 Price: *{format_price(product['price'])}*\n"
            f"📦 Stock: {stock_status}\n\n"
            f"📄 *Product Details:*\n"
            f"• {desc}\n"
            f"• {warranty}"
        )

        markup = product_buy_button(product["id"])

        # Send with product image if available
        if product["image_path"] and os.path.exists(product["image_path"]):
            with open(product["image_path"], "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=markup,
                )
        else:
            await update.message.reply_text(
                caption,
                parse_mode="Markdown",
                reply_markup=markup,
            )


# ─── Purchase Flow ──────────────────────────────────────────────────

async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy button press — show confirmation."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.message.reply_text("❌ Product not found.")
        return

    if product["stock"] <= 0:
        await query.message.reply_text("❌ Sorry, this product is now out of stock!")
        return

    text = (
        f"🛒 *Confirm Purchase*\n\n"
        f"📦 *{product['name']}*\n"
        f"💰 Price: *{format_price(product['price'])}*\n\n"
        f"Are you sure you want to buy this product?"
    )

    await query.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=buy_confirm_button(product_id),
    )


async def handle_confirm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase confirmation — create order and show payment methods."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[2])
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)

    # Check payment methods exist
    payment_methods = get_active_payment_methods()
    if not payment_methods:
        await query.edit_message_text(
            "❌ No payment methods configured yet. Please contact support."
        )
        return

    # Create order
    order_id, result = create_order(user.id, product_id)

    if order_id is None:
        await query.edit_message_text(f"❌ {result}")
        return

    order = result

    # Build payment methods text
    pm_text = ""
    for pm in payment_methods:
        pm_text += f"  • *{pm['name']}*\n    `{pm['address']}`\n\n"

    text = (
        f"✅ *Order Created!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"📦 {order['product_name']}\n"
        f"💰 Amount: *{format_price(order['price'])}*\n\n"
        f"{'─' * 25}\n"
        f"💳 *Payment Methods:*\n\n"
        f"{pm_text}"
        f"{'─' * 25}\n\n"
        f"⏳ You have *10 minutes* to complete payment.\n"
        f"After payment, send your *Transaction Hash/ID* here."
    )

    await query.edit_message_text(text, parse_mode="Markdown")

    # Set awaiting tx hash state
    context.user_data["awaiting_tx_hash"] = order_id

    # Schedule payment timeout (10 minutes)
    context.job_queue.run_once(
        payment_timeout_job,
        PAYMENT_TIMEOUT,
        data={"order_id": order_id, "chat_id": user.id},
        name=f"payment_timeout_{order_id}",
    )


async def payment_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    """Auto-cancel order after payment timeout."""
    job_data = context.job.data
    order_id = job_data["order_id"]
    chat_id = job_data["chat_id"]

    cancelled = cancel_expired_order(order_id)
    if cancelled:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"⏰ *Payment Timeout!*\n\n"
                    f"🆔 Order `{order_id}` has been cancelled because\n"
                    f"payment was not completed within 10 minutes.\n\n"
                    f"You can place a new order anytime."
                ),
                parse_mode="Markdown",
            )
        except Exception:
            pass


async def handle_tx_hash_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process transaction hash from customer."""
    order_id = context.user_data.get("awaiting_tx_hash")
    if not order_id:
        return False

    tx_hash = update.message.text.strip()
    if len(tx_hash) < 3:
        await update.message.reply_text(
            "❌ That doesn't look like a valid transaction hash. Please try again:"
        )
        return True

    # Save tx hash
    set_transaction_hash(order_id, tx_hash)
    context.user_data["awaiting_tx_hash"] = None
    context.user_data["awaiting_payment_done"] = order_id
    context.user_data["tx_hash"] = tx_hash

    text = (
        f"✅ *Transaction Hash Received!*\n\n"
        f"🆔 Order: `{order_id}`\n"
        f"🔗 TX Hash: `{tx_hash}`\n\n"
        f"Click *Payment Done* when you've confirmed the transfer."
    )

    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=payment_done_button(order_id),
    )
    return True


async def handle_payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Payment Done button — notify admin with order details."""
    query = update.callback_query
    await query.answer("Payment submitted! ✅")

    order_id = query.data.split("_")[1]
    order = get_order_by_id(order_id)
    user = query.from_user

    if not order:
        await query.edit_message_text("❌ Order not found.")
        return

    # Cancel the timeout job
    jobs = context.job_queue.get_jobs_by_name(f"payment_timeout_{order_id}")
    for job in jobs:
        job.schedule_removal()

    # Clear payment states
    context.user_data.pop("awaiting_payment_done", None)
    tx_hash = context.user_data.pop("tx_hash", order.get("transaction_hash", "N/A"))

    # Confirm to customer
    await query.edit_message_text(
        f"✅ *Payment Submitted!*\n\n"
        f"🆔 Order: `{order_id}`\n"
        f"📦 {order['product_name']}\n"
        f"💰 {format_price(order['price'])}\n"
        f"🔗 TX: `{tx_hash}`\n\n"
        f"⏳ Waiting for admin to verify your payment.\n"
        f"You'll be notified once confirmed!",
        parse_mode="Markdown",
    )

    # Get customer info
    customer = get_user(user.id)
    customer_name = customer["first_name"] if customer else user.first_name
    customer_username = customer["username"] if customer else user.username

    # Notify admin with order details + chat button
    admin_msg = (
        f"🔔 *New Payment Received!*\n\n"
        f"🆔 Order: `{order_id}`\n"
        f"📦 Product: {order['product_name']}\n"
        f"💰 Amount: {format_price(order['price'])}\n"
        f"🔗 TX Hash: `{tx_hash}`\n\n"
        f"{'─' * 25}\n"
        f"👤 *Customer Details:*\n"
        f"  Name: {customer_name}\n"
        f"  Username: @{customer_username or 'N/A'}\n"
        f"  Chat ID: `{user.id}`\n"
        f"{'─' * 25}"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown",
            reply_markup=admin_order_notification_buttons(order_id, user.id),
        )
    except Exception:
        pass


async def handle_payment_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Customer cancels order during payment."""
    query = update.callback_query
    await query.answer()

    order_id = query.data.split("_")[1]

    # Cancel timeout job
    jobs = context.job_queue.get_jobs_by_name(f"payment_timeout_{order_id}")
    for job in jobs:
        job.schedule_removal()

    # Cancel order and restore stock
    cancel_expired_order(order_id)

    # Clear states
    context.user_data.pop("awaiting_tx_hash", None)
    context.user_data.pop("awaiting_payment_done", None)
    context.user_data.pop("tx_hash", None)

    await query.edit_message_text(
        f"❌ Order `{order_id}` has been cancelled.",
        parse_mode="Markdown",
    )


async def handle_cancel_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase cancellation (before order creation)."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Purchase cancelled.")


# ─── My Purchases ───────────────────────────────────────────────────

async def show_my_purchases(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show customer's purchase history."""
    user = update.effective_user
    orders = get_user_orders(user.id)

    if not orders:
        await update.message.reply_text(
            "🛒 You haven't made any purchases yet.\n"
            "Browse our products to get started! 🛍",
            reply_markup=customer_keyboard(),
        )
        return

    text = f"🛒 *Your Purchases* ({len(orders)} orders)\n" + "─" * 30 + "\n\n"

    for order in orders:
        status_emoji = {
            "awaiting_payment": "⏳",
            "payment_sent": "💸",
            "confirmed": "✅",
            "shipped": "🚚",
            "completed": "✔️",
            "rejected": "❌",
            "expired": "⏰",
        }.get(order["status"], "❓")

        warranty = warranty_status_text(order["warranty_expiry"])

        text += (
            f"🆔 `{order['order_id']}` | {status_emoji} {order['status'].replace('_', ' ').title()}\n"
            f"📦 {order['product_name']} — {format_price(order['price'])}\n"
            f"🛡 {warranty}\n"
            f"{'─' * 30}\n\n"
        )

    # Split message if too long
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await update.message.reply_text(
                chunk, parse_mode="Markdown", reply_markup=customer_keyboard()
            )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=customer_keyboard()
        )


# ─── Warranty ────────────────────────────────────────────────────────

async def show_warranty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt customer to enter order ID for warranty check."""
    context.user_data["awaiting_warranty_check"] = True
    await update.message.reply_text(
        "🛡 *Warranty Check*\n\n"
        "Please enter your *Order ID* (e.g. `GYP-XT56K`) to check warranty status:",
        parse_mode="Markdown",
    )


async def check_warranty_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process warranty check by order ID."""
    if not context.user_data.get("awaiting_warranty_check"):
        return False

    context.user_data["awaiting_warranty_check"] = False
    order_id = update.message.text.strip().upper()

    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text(
            f"❌ No order found with ID `{order_id}`.\n"
            "Please check the ID and try again.",
            parse_mode="Markdown",
            reply_markup=customer_keyboard(),
        )
        return True

    warranty = warranty_status_text(order["warranty_expiry"])
    warranty_expiry = format_date_short(order["warranty_expiry"]) if order["warranty_expiry"] else "N/A"

    text = (
        f"🛡 *Warranty Details*\n\n"
        f"🆔 Order: `{order['order_id']}`\n"
        f"📦 Product: {order['product_name']}\n"
        f"📅 Purchase Date: {format_date(order['created_at'])}\n"
        f"📅 Warranty Expires: {warranty_expiry}\n"
        f"📊 Status: {warranty}\n"
    )

    if order["warranty_details"]:
        text += f"\n📋 *Terms:*\n{order['warranty_details']}"

    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=customer_keyboard()
    )
    return True


# ─── Help / Chat ────────────────────────────────────────────────────

async def help_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt customer to send a help message."""
    context.user_data["awaiting_help_message"] = True
    await update.message.reply_text(
        "💬 *Help / Chat*\n\n"
        "Type your message below and it will be sent to our support team.\n"
        "We'll get back to you as soon as possible!",
        parse_mode="Markdown",
    )


async def forward_help_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward customer's help message to admin."""
    if not context.user_data.get("awaiting_help_message"):
        return False

    context.user_data["awaiting_help_message"] = False
    user = update.effective_user

    admin_msg = (
        f"💬 *Help Message from Customer*\n\n"
        f"👤 {user.first_name} (@{user.username or 'N/A'})\n"
        f"🆔 Chat ID: `{user.id}`\n\n"
        f"📝 *Message:*\n{update.message.text}"
    )

    try:
        from utils.keyboard import admin_order_notification_buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        chat_btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "💬 Chat with Customer",
                callback_data=f"achat_{user.id}",
            )]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown",
            reply_markup=chat_btn,
        )
        await update.message.reply_text(
            "✅ Your message has been sent to our support team!\n"
            "We'll reply as soon as possible. 🙏",
            reply_markup=customer_keyboard(),
        )
    except Exception:
        await update.message.reply_text(
            "❌ Failed to send message. Please try again later.",
            reply_markup=customer_keyboard(),
        )

    return True
