"""
GET YOUR PLUS — Customer Handlers
Handles all customer-facing interactions: browsing, purchasing, payments, warranties, help.
Made by Rubel
"""

import os
import html
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_CHAT_ID
from database import (
    upsert_user, get_active_products, get_product, get_user_orders,
    get_order_by_id, create_order, get_active_payment_methods,
    set_transaction_hash, cancel_expired_order, get_user, get_coupon,
)
from utils.keyboard import (
    customer_keyboard, product_buy_button, buy_confirm_button,
    payment_done_button, admin_order_notification_buttons,
    product_details_back_button, admin_chat_only_button,
    payment_screen_buttons, claim_warranty_button,
)
from utils.helpers import (
    format_price, format_date, warranty_status_text, format_date_short,
    normalize_order_id,
)


# ─── Logger ──────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


def get_reply_keyboard(user_id: int):
    """Get reply keyboard based on user role (prevent admin seeing customer portal)."""
    from utils.keyboard import admin_keyboard
    return admin_keyboard() if user_id == ADMIN_CHAT_ID else customer_keyboard()


# ─── Payment timeout (seconds) ──────────────────────────────────────
PAYMENT_TIMEOUT = 600  # 10 minutes


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command for customers."""
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    if user.id == ADMIN_CHAT_ID:
        from handlers.admin import admin_start
        await admin_start(update, context)
        return

    welcome = (
        f"👋 Welcome to *GET YOUR PLUS*, {user.first_name}!\n\n"
        "🛍 Browse our products and purchase instantly.\n"
        "🛒 Track your orders and warranties.\n"
        "💬 Need help? We're here for you!\n\n"
        "Use the buttons below to navigate 👇"
    )
    await update.message.reply_text(
        welcome, parse_mode="Markdown", reply_markup=get_reply_keyboard(user.id)
    )


# ─── Product Card Format Helpers ─────────────────────────────────────

def format_product_compact(product):
    """Format compact product card (Name, Price, Stock only)."""
    stock_status = f"🟢 {product['stock']} units available" if product["stock"] > 0 else "🔴 Out of Stock"
    return (
        f"🛍️ <b>Product:</b> {html.escape(product['name'])}\n"
        f"💵 <b>Price:</b> {format_price(product['price'])}\n"
        f"📦 <b>Stock:</b> {stock_status}"
    )


def format_product_details(product):
    """Format full details view (Description & Warranty)."""
    desc = product['description'] if product['description'] else "No description available."
    warranty = f"🛡️ {product['warranty_days']} Days Warranty" if product['warranty_days'] > 0 else "🛡️ No Warranty"
    warranty_info = f"\n📋 <b>Warranty Terms:</b>\n{html.escape(product['warranty_details'])}" if product['warranty_details'] else ""
    return (
        f"🌟 <b>{html.escape(product['name'])} — Details</b>\n"
        f"──────────────────────────\n"
        f"📄 <b>Description:</b>\n<i>{html.escape(desc)}</i>\n\n"
        f"🛡️ <b>Warranty:</b> {warranty}{warranty_info}"
    )


# ─── Product Browsing ───────────────────────────────────────────────

async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available products to the customer (compact cards with Details + Buy buttons)."""
    products = get_active_products()

    if not products:
        await update.message.reply_text(
            "😔 No products available right now. Check back later!",
            reply_markup=get_reply_keyboard(update.effective_user.id),
        )
        return

    for product in products:
        caption = format_product_compact(product)
        markup = product_buy_button(product["id"])

        # Send with product image if available
        if product["image_path"] and os.path.exists(product["image_path"]):
            with open(product["image_path"], "rb") as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=markup,
                )
        else:
            await update.message.reply_text(
                caption,
                parse_mode="HTML",
                reply_markup=markup,
            )


async def handle_details_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle details button press — edit card to show full description."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.message.reply_text("❌ Product not found.")
        return

    text = format_product_details(product)
    
    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=text,
                parse_mode="HTML",
                reply_markup=product_details_back_button(product_id)
            )
        else:
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=product_details_back_button(product_id)
            )
    except Exception:
        pass


async def handle_view_card_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back button press — edit card back to compact view."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[2])
    product = get_product(product_id)

    if not product:
        await query.message.reply_text("❌ Product not found.")
        return

    text = format_product_compact(product)
    
    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=text,
                parse_mode="HTML",
                reply_markup=product_buy_button(product_id)
            )
        else:
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=product_buy_button(product_id)
            )
    except Exception:
        pass


# ─── Purchase Flow ──────────────────────────────────────────────────

async def handle_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buy button press — show option to apply coupon code or skip."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)

    product = get_product(product_id)
    if not product:
        await query.message.reply_text("❌ Product not found.")
        return

    if product["stock"] <= 0:
        await query.message.reply_text("❌ Sorry, this product is now out of stock!")
        return

    # Check payment methods exist
    payment_methods = get_active_payment_methods()
    if not payment_methods:
        await query.message.reply_text(
            "❌ No payment methods configured yet. Please contact support."
        )
        return

    from utils.keyboard import coupon_options_keyboard

    # Show purchase options (Apply Coupon / Skip Coupon)
    text = (
        f"🛒 *Confirm Purchase: {html.escape(product['name'])}*\n\n"
        f"💵 Price: *{format_price(product['price'])}*\n\n"
        f"Do you want to apply a coupon code for a discount?"
    )

    try:
        if query.message.photo:
            await query.edit_message_caption(
                caption=text,
                parse_mode="HTML",
                reply_markup=coupon_options_keyboard(product_id)
            )
        else:
            await query.edit_message_text(
                text=text,
                parse_mode="HTML",
                reply_markup=coupon_options_keyboard(product_id)
            )
    except Exception:
        await query.message.reply_text(
            text, parse_mode="HTML", reply_markup=coupon_options_keyboard(product_id)
        )


async def handle_apply_coupon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt the customer to input the coupon code."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[2])
    product = get_product(product_id)
    if not product:
        await query.message.reply_text("❌ Product not found.")
        return

    context.user_data["awaiting_coupon_code"] = product_id

    # Prompt user
    await query.message.reply_text(
        f"🎟️ Please enter/send the coupon code for *{html.escape(product['name'])}* below:",
        parse_mode="HTML",
    )


async def handle_buy_no_coupon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Directly buy a product without a coupon code."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[3])
    await process_purchase(update, context, product_id)


async def handle_confirm_buy_coupon_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm purchasing a product with a coupon code."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    product_id = int(parts[3])
    coupon_code = parts[4]

    await process_purchase(update, context, product_id, coupon_code)


async def handle_coupon_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process coupon code inputted by customer."""
    product_id = context.user_data.get("awaiting_coupon_code")
    if not product_id:
        return False

    coupon_code_raw = update.message.text.strip().upper()

    # Cancel if menu button pressed or command entered
    menu_buttons = {
        "🛍 Products", "🛒 My Purchases", "🛡 Warranty", "💬 Help / Chat",
        "➕ Add Product", "📦 Manage Products", "📊 Inventory", "📋 Orders",
        "💳 Payment Methods", "🎟️ Coupons", "📢 Broadcast", "👥 Users", "/start", "/admin"
    }
    if coupon_code_raw in menu_buttons or coupon_code_raw.startswith("/"):
        context.user_data.pop("awaiting_coupon_code", None)
        return False

    # Get product
    product = get_product(product_id)
    if not product:
        context.user_data.pop("awaiting_coupon_code", None)
        await update.message.reply_text("❌ Product not found.")
        return True

    # Validate coupon code
    coupon = get_coupon(coupon_code_raw)

    if not coupon or not coupon["is_active"]:
        await update.message.reply_text(
            "❌ Invalid coupon code. Please try again or type a menu option to cancel:"
        )
        return True

    if coupon["used_count"] >= coupon["usage_limit"]:
        await update.message.reply_text(
            "❌ This coupon code has reached its usage limit. Please try another code:"
        )
        return True

    # Coupon is valid! Clear state and show discounted confirmation screen.
    context.user_data.pop("awaiting_coupon_code", None)

    discount = coupon["discount"]
    new_price = max(0.0, product["price"] - discount)

    from utils.keyboard import coupon_confirm_keyboard
    confirm_text = (
        f"🎟️ *Coupon Applied successfully!*\n\n"
        f"📦 Product: *{html.escape(product['name'])}*\n"
        f"💵 Original Price: *{format_price(product['price'])}*\n"
        f"🎟️ Discount: -*{format_price(discount)}*\n"
        f"💰 Final Price: *{format_price(new_price)}*\n\n"
        f"Confirm purchase?"
    )

    await update.message.reply_text(
        confirm_text, parse_mode="Markdown",
        reply_markup=coupon_confirm_keyboard(product_id, coupon_code_raw)
    )
    return True


async def process_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int, coupon_code: str = None):
    """Create the order and show payment screen."""
    query = update.callback_query
    user = query.from_user
    upsert_user(user.id, user.username, user.first_name)

    product = get_product(product_id)
    if not product:
        await query.message.reply_text("❌ Product not found.")
        return

    if product["stock"] <= 0:
        await query.message.reply_text("❌ Sorry, this product is now out of stock!")
        return

    payment_methods = get_active_payment_methods()
    if not payment_methods:
        await query.message.reply_text(
            "❌ No payment methods configured yet. Please contact support."
        )
        return

    # Check coupon details if coupon_code is provided
    discount_amount = 0.0
    if coupon_code:
        coupon = get_coupon(coupon_code)
        if coupon and coupon["is_active"] and coupon["used_count"] < coupon["usage_limit"]:
            discount_amount = coupon["discount"]
        else:
            await query.message.reply_text("❌ Coupon code is invalid or has expired.")
            return

    # Create order in database
    order_id, result = create_order(user.id, product_id, coupon_code, discount_amount)
    if order_id is None:
        await query.message.reply_text(f"❌ {result}")
        return

    order = result

    # Build payment methods text
    pm_text = ""
    for pm in payment_methods:
        pm_text += f"  • *{pm['name']}*\n    `{pm['address']}`\n\n"

    # Generate initial text with countdown
    text = get_payment_screen_text(
        order_id=order_id,
        product_name=order["product_name"],
        price=order["price"],
        pm_text=pm_text,
        coupon_code=coupon_code,
        discount_amount=discount_amount,
        seconds_left=PAYMENT_TIMEOUT
    )

    # Reply with payment info and a cancel order button
    sent_message = await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=payment_screen_buttons(order_id)
    )

    # Set awaiting tx hash state
    context.user_data["awaiting_tx_hash"] = order_id

    # Schedule payment timeout (10 minutes)
    context.job_queue.run_once(
        payment_timeout_job,
        PAYMENT_TIMEOUT,
        data={"order_id": order_id, "chat_id": user.id},
        name=f"payment_timeout_{order_id}",
    )

    # Schedule payment countdown (repeating every 60 seconds)
    context.job_queue.run_repeating(
        payment_countdown_job,
        interval=60,
        first=60,
        data={
            "order_id": order_id,
            "chat_id": user.id,
            "message_id": sent_message.message_id,
            "product_name": order['product_name'],
            "price": order['price'],
            "pm_text": pm_text,
            "coupon_code": coupon_code,
            "discount_amount": discount_amount,
            "seconds_left": PAYMENT_TIMEOUT
        },
        name=f"payment_countdown_{order_id}",
    )

    # Notify admin about new order (awaiting payment)
    admin_msg = (
        f"🔔 *New Order Created!*\n\n"
        f"🆔 Order: `{order_id}`\n"
        f"📦 Product: {order['product_name']}\n"
        f"{coupon_info}"
        f"💰 Amount: {format_price(order['price'])}\n"
        f"⏳ Status: Awaiting Payment\n\n"
        f"{'─' * 25}\n"
        f"👤 *Customer Details:*\n"
        f"  Name: {user.first_name}\n"
        f"  Username: @{user.username or 'N/A'}\n"
        f"  Chat ID: `{user.id}`\n"
        f"{'─' * 25}"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_msg,
            parse_mode="Markdown",
            reply_markup=admin_chat_only_button(user.id),
        )
    except Exception as e:
        logger.error(f"Failed to notify admin of new order creation: {e}")


async def payment_timeout_job(context: ContextTypes.DEFAULT_TYPE):
    """Auto-cancel order after payment timeout."""
    job_data = context.job.data
    order_id = job_data["order_id"]
    chat_id = job_data["chat_id"]

    # Cancel countdown job
    countdown_jobs = context.job_queue.get_jobs_by_name(f"payment_countdown_{order_id}")
    for job in countdown_jobs:
        job.schedule_removal()

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
    menu_buttons = {
        "🛍 Products", "🛒 My Purchases", "🛡 Warranty", "💬 Help / Chat",
        "➕ Add Product", "📦 Manage Products", "📊 Inventory", "📋 Orders",
        "💳 Payment Methods", "📢 Broadcast", "👥 Users", "/start", "/admin"
    }
    if tx_hash in menu_buttons or tx_hash.startswith("/"):
        context.user_data["awaiting_tx_hash"] = None
        return False
    if len(tx_hash) < 3:
        await update.message.reply_text(
            "❌ That doesn't look like a valid transaction hash. Please try again:"
        )
        return True

    # Save tx hash and update payment_status
    set_transaction_hash(order_id, tx_hash)
    
    # Clear payment states
    context.user_data["awaiting_tx_hash"] = None
    context.user_data.pop("awaiting_payment_done", None)
    context.user_data.pop("tx_hash", None)

    # Cancel the timeout and countdown jobs
    for suffix in ["timeout", "countdown"]:
        jobs = context.job_queue.get_jobs_by_name(f"payment_{suffix}_{order_id}")
        for job in jobs:
            job.schedule_removal()

    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.")
        return True

    # Confirm to customer professionally
    thank_you_text = (
        f"🙏 *Thank you for your order!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"📦 Product: *{order['product_name']}*\n"
        f"💰 Amount: *{format_price(order['price'])}*\n"
        f"🔗 TX Hash: `{tx_hash}`\n\n"
        f"⏳ We are currently verifying your transaction. "
        f"You will be notified here as soon as the admin confirms it!"
    )
    await update.message.reply_text(thank_you_text, parse_mode="Markdown")

    # Get customer info
    user = update.effective_user
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
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")

    return True


async def handle_payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Legacy handler for payment done button."""
    query = update.callback_query
    await query.answer("Payment already submitted! ✅")


async def handle_payment_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Customer cancels order during payment."""
    query = update.callback_query
    await query.answer()

    order_id = query.data.split("_")[1]

    # Cancel timeout and countdown jobs
    for suffix in ["timeout", "countdown"]:
        jobs = context.job_queue.get_jobs_by_name(f"payment_{suffix}_{order_id}")
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
            reply_markup=get_reply_keyboard(user.id),
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
                chunk, parse_mode="Markdown", reply_markup=get_reply_keyboard(user.id)
            )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=get_reply_keyboard(user.id)
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

    order_id_raw = update.message.text.strip()

    # If user clicked a menu button or ran a command, abort state and let it route
    menu_buttons = {
        "🛍 Products", "🛒 My Purchases", "🛡 Warranty", "💬 Help / Chat",
        "➕ Add Product", "📦 Manage Products", "📊 Inventory", "📋 Orders",
        "💳 Payment Methods", "📢 Broadcast", "👥 Users", "/start", "/admin"
    }
    if order_id_raw in menu_buttons or order_id_raw.startswith("/"):
        context.user_data["awaiting_warranty_check"] = False
        return False

    # Normalize entered Order ID
    order_id = normalize_order_id(order_id_raw)

    order = get_order_by_id(order_id)
    if not order:
        await update.message.reply_text(
            f"❌ No order found with ID <code>{html.escape(order_id_raw)}</code>.\n\n"
            "Please check the ID and try again, or click a button below to cancel: 👇",
            parse_mode="HTML",
            reply_markup=get_reply_keyboard(update.effective_user.id),
        )
        # Keep awaiting_warranty_check = True so they can retry
        return True

    # Correct ID provided, clear state
    context.user_data["awaiting_warranty_check"] = False

    warranty = warranty_status_text(order["warranty_expiry"])
    warranty_expiry = format_date_short(order["warranty_expiry"]) if order["warranty_expiry"] else "N/A"

    text = (
        f"🛡 <b>Warranty Details</b>\n\n"
        f"🆔 Order: <code>{order['order_id']}</code>\n"
        f"📦 Product: {html.escape(order['product_name'])}\n"
        f"📅 Purchase Date: {format_date(order['created_at'])}\n"
        f"📅 Warranty Expires: {warranty_expiry}\n"
        f"📊 Status: {warranty}\n"
    )

    if order["warranty_details"]:
        text += f"\n📋 <b>Terms:</b>\n{html.escape(order['warranty_details'])}"

    # If warranty is active, show the Claim Warranty button
    from utils.helpers import is_warranty_active
    reply_markup = get_reply_keyboard(update.effective_user.id)
    if is_warranty_active(order["warranty_expiry"]):
        reply_markup = claim_warranty_button(order["order_id"])

    await update.message.reply_text(
        text, parse_mode="HTML", reply_markup=reply_markup
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

    help_msg_raw = update.message.text.strip()

    # If user clicked a menu button or ran a command, abort state and let it route
    menu_buttons = {
        "🛍 Products", "🛒 My Purchases", "🛡 Warranty", "💬 Help / Chat",
        "➕ Add Product", "📦 Manage Products", "📊 Inventory", "📋 Orders",
        "💳 Payment Methods", "📢 Broadcast", "👥 Users", "/start", "/admin"
    }
    if help_msg_raw in menu_buttons or help_msg_raw.startswith("/"):
        context.user_data["awaiting_help_message"] = False
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
            reply_markup=get_reply_keyboard(user.id),
        )
    except Exception:
        await update.message.reply_text(
            "❌ Failed to send message. Please try again later.",
            reply_markup=get_reply_keyboard(user.id),
        )

    return True


async def handle_claim_warranty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Claim Warranty button press — notify admin and prompt user for message."""
    query = update.callback_query
    await query.answer()

    order_id = query.data.split("_")[1]
    order = get_order_by_id(order_id)
    user = query.from_user

    if not order:
        await query.message.reply_text("❌ Order not found.")
        return

    # Notify admin
    cust_name = user.first_name
    if user.last_name:
        cust_name += f" {user.last_name}"
    username_text = f" (@{user.username})" if user.username else ""

    admin_msg = (
        f"🚨 *Warranty Claim Request!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"📦 Product: {order['product_name']}\n"
        f"📅 Purchase Date: {format_date(order['created_at'])}\n"
        f"📅 Expiry: {format_date_short(order['warranty_expiry'])}\n\n"
        f"{'─' * 25}\n"
        f"👤 *Customer Details:*\n"
        f"  Name: {cust_name}\n"
        f"  Username: {username_text or '@N/A'}\n"
        f"  Chat ID: `{user.id}`\n"
        f"{'─' * 25}"
    )

    try:
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
    except Exception as e:
        logger.error(f"Failed to notify admin of warranty claim: {e}")

    # Reply to customer
    context.user_data["awaiting_help_message"] = True

    text = (
        f"🛡️ *Warranty Claim Initiated!*\n\n"
        f"We have notified the support team regarding your warranty claim for order `{order_id}`.\n\n"
        f"💬 Please type your message below describing the issue, and an agent will join the chat to help you shortly:"
    )
    await query.edit_message_text(text, parse_mode="Markdown")


def get_payment_screen_text(order_id, product_name, price, pm_text, coupon_code=None, discount_amount=0.0, seconds_left=600):
    coupon_info = ""
    if coupon_code:
        coupon_info = f"🎟️ Coupon Applied: `{coupon_code}` (-{format_price(discount_amount)})\n"

    minutes = seconds_left // 60
    seconds = seconds_left % 60
    time_str = f"*{minutes}m {seconds:02d}s*"

    return (
        f"✅ *Order Created!*\n\n"
        f"🆔 Order ID: `{order_id}`\n"
        f"📦 {product_name}\n"
        f"{coupon_info}"
        f"💰 Amount: *{format_price(price)}*\n\n"
        f"{'─' * 25}\n"
        f"💳 *Payment Methods:*\n\n"
        f"{pm_text}"
        f"{'─' * 25}\n\n"
        f"⏳ Time Remaining: {time_str}\n"
        f"After payment, send your *Transaction Hash/ID* here."
    )


async def payment_countdown_job(context: ContextTypes.DEFAULT_TYPE):
    """Update payment screen timer countdown."""
    job = context.job
    data = job.data
    order_id = data["order_id"]
    chat_id = data["chat_id"]
    message_id = data["message_id"]
    seconds_left = data["seconds_left"] - 60

    # Check if order is still awaiting payment
    from database import get_order_by_id
    order = get_order_by_id(order_id)
    if not order or order["status"] != "awaiting_payment":
        job.schedule_removal()
        return

    if seconds_left <= 0:
        job.schedule_removal()
        return

    data["seconds_left"] = seconds_left

    text = get_payment_screen_text(
        order_id=order_id,
        product_name=data["product_name"],
        price=data["price"],
        pm_text=data["pm_text"],
        coupon_code=data["coupon_code"],
        discount_amount=data["discount_amount"],
        seconds_left=seconds_left
    )

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=payment_screen_buttons(order_id)
        )
    except Exception as e:
        logger.error(f"Failed to update payment countdown: {e}")
        # If the message is deleted or cannot be edited, remove job to save resources
        job.schedule_removal()

