"""
GET YOUR PLUS — Customer Handlers
Handles all customer-facing interactions: browsing, purchasing, warranties, help.
"""

import os
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_CHAT_ID
from database import (
    upsert_user, get_active_products, get_product, get_user_orders,
    get_order_by_id, create_order,
)
from utils.keyboard import (
    customer_keyboard, product_buy_button, buy_confirm_button,
)
from utils.helpers import (
    format_price, format_date, warranty_status_text, format_date_short,
)


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


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available products to the customer."""
    products = get_active_products()

    if not products:
        await update.message.reply_text(
            "😔 No products available right now. Check back later!",
            reply_markup=customer_keyboard(),
        )
        return

    await update.message.reply_text(
        f"🛍 *Available Products* ({len(products)} items)\n"
        "─────────────────────────",
        parse_mode="Markdown",
    )

    for product in products:
        stock_text = f"📦 In Stock: {product['stock']}" if product["stock"] > 0 else "❌ Out of Stock"
        warranty_text = (
            f"🛡 {product['warranty_days']} days warranty"
            if product["warranty_days"] > 0
            else "🛡 No warranty"
        )

        caption = (
            f"*{product['name']}*\n\n"
            f"{product['description']}\n\n"
            f"💰 Price: *{format_price(product['price'])}*\n"
            f"{stock_text}\n"
            f"{warranty_text}"
        )

        # Send with product image if available
        if product["image_path"] and os.path.exists(product["image_path"]):
            with open(product["image_path"], "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=product_buy_button(product["id"]) if product["stock"] > 0 else None,
                )
        else:
            await update.message.reply_text(
                caption,
                parse_mode="Markdown",
                reply_markup=product_buy_button(product["id"]) if product["stock"] > 0 else None,
            )


async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy button press — show confirmation."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    if product["stock"] <= 0:
        await query.edit_message_text("❌ Sorry, this product is now out of stock!")
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
    """Handle purchase confirmation."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[2])
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)

    order_id, result = create_order(user.id, product_id)

    if order_id is None:
        await query.edit_message_text(f"❌ {result}")
        return

    order = result
    warranty_text = ""
    if order["warranty_days"] and order["warranty_days"] > 0:
        warranty_text = (
            f"\n🛡 *Warranty:* {order['warranty_days']} days\n"
            f"📅 *Expires:* {format_date_short(order['warranty_expiry'])}\n"
            f"📋 *Details:* {order['warranty_details']}"
        )

    receipt = (
        f"✅ *Order Placed Successfully!*\n\n"
        f"🆔 *Order ID:* `{order_id}`\n"
        f"📦 *Product:* {order['product_name']}\n"
        f"💰 *Price:* {format_price(order['price'])}\n"
        f"📅 *Date:* {format_date(order['created_at'])}\n"
        f"📊 *Status:* Pending"
        f"{warranty_text}\n\n"
        f"💡 Save your Order ID to check warranty status later!"
    )

    await query.edit_message_text(receipt, parse_mode="Markdown")

    # Notify admin
    admin_msg = (
        f"🔔 *New Order!*\n\n"
        f"🆔 Order: `{order_id}`\n"
        f"👤 Customer: {user.first_name} (@{user.username or 'N/A'})\n"
        f"📦 Product: {order['product_name']}\n"
        f"💰 Price: {format_price(order['price'])}"
    )
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown",
        )
    except Exception:
        pass  # Admin notification is best-effort


async def handle_cancel_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle purchase cancellation."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ Purchase cancelled.")


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
            "pending": "⏳",
            "confirmed": "✅",
            "shipped": "🚚",
            "completed": "✔️",
        }.get(order["status"], "❓")

        warranty = warranty_status_text(order["warranty_expiry"])

        text += (
            f"🆔 `{order['order_id']}`\n"
            f"📦 {order['product_name']}\n"
            f"💰 {format_price(order['price'])}\n"
            f"📅 {format_date(order['created_at'])}\n"
            f"📊 Status: {status_emoji} {order['status'].title()}\n"
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
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown",
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
