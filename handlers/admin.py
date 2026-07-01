"""
GET YOUR PLUS — Admin Handlers
Handles admin panel: product management, payment methods, orders, users, chat system.
Uses ConversationHandler for multi-step flows.
Made by Rubel
"""

import os
from telegram import Update
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters,
)
from config import ADMIN_CHAT_ID, IMAGES_DIR
from database import (
    add_product, get_all_products, get_product, update_product_field,
    delete_product, toggle_product_active, get_all_orders,
    update_order_status, get_user_count, get_all_users,
    get_order_by_id, confirm_order_payment, reject_order_payment,
    add_payment_method, get_all_payment_methods, get_payment_method,
    delete_payment_method, toggle_payment_method, get_user,
)
from utils.keyboard import (
    admin_keyboard, cancel_keyboard, skip_keyboard,
    product_manage_buttons, product_edit_buttons,
    order_status_buttons, delete_confirm_buttons,
    payment_method_manage_buttons, close_chat_keyboard,
    admin_chat_only_button,
)
from utils.helpers import format_price, format_date


def is_admin(user_id: int) -> bool:
    """Check if a user is the admin."""
    return user_id == ADMIN_CHAT_ID


# ─── Conversation States ────────────────────────────────────────────
(
    ADD_NAME, ADD_DESC, ADD_PRICE, ADD_STOCK,
    ADD_WARRANTY_DAYS, ADD_WARRANTY_DETAILS, ADD_IMAGE,
) = range(7)

(EDIT_VALUE,) = range(7, 8)

# Payment method conversation states
(PM_NAME, PM_ADDRESS) = range(8, 10)


# ─── Admin Start ────────────────────────────────────────────────────

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    if not is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "🔐 *Admin Panel — GET YOUR PLUS*\n\n"
        "Use the buttons below to manage your store 👇",
        parse_mode="Markdown",
        reply_markup=admin_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════
#  ADD PRODUCT CONVERSATION
# ═══════════════════════════════════════════════════════════════════

async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the Add Product wizard."""
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_product"] = {}
    await update.message.reply_text(
        "➕ *Add New Product*\n\n"
        "Step 1/7: Enter the *product name*:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return ADD_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive product name."""
    context.user_data["new_product"]["name"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ Got it!\n\n"
        "Step 2/7: Enter the *product description*:\n"
        "(or tap ⏭ Skip to leave empty)",
        parse_mode="Markdown",
        reply_markup=skip_keyboard(),
    )
    return ADD_DESC


async def add_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive product description."""
    text = update.message.text.strip()
    context.user_data["new_product"]["description"] = "" if text == "⏭ Skip" else text
    await update.message.reply_text(
        "✅ Got it!\n\n"
        "Step 3/7: Enter the *price* (number only):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return ADD_PRICE


async def add_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive product price."""
    try:
        price = float(update.message.text.strip())
        if price <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid positive number for the price:"
        )
        return ADD_PRICE

    context.user_data["new_product"]["price"] = price
    await update.message.reply_text(
        f"✅ Price set to *{format_price(price)}*\n\n"
        "Step 4/7: Enter the *stock quantity* (number):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return ADD_STOCK


async def add_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive stock quantity."""
    try:
        stock = int(update.message.text.strip())
        if stock < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Please enter a valid non-negative number for stock:"
        )
        return ADD_STOCK

    context.user_data["new_product"]["stock"] = stock
    await update.message.reply_text(
        f"✅ Stock set to *{stock}* units\n\n"
        "Step 5/7: Enter *warranty period in days* (0 for no warranty):\n"
        "(or tap ⏭ Skip for no warranty)",
        parse_mode="Markdown",
        reply_markup=skip_keyboard(),
    )
    return ADD_WARRANTY_DAYS


async def add_warranty_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive warranty days."""
    text = update.message.text.strip()
    if text == "⏭ Skip":
        context.user_data["new_product"]["warranty_days"] = 0
    else:
        try:
            days = int(text)
            if days < 0:
                raise ValueError
            context.user_data["new_product"]["warranty_days"] = days
        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number of days:"
            )
            return ADD_WARRANTY_DAYS

    days = context.user_data["new_product"]["warranty_days"]
    if days > 0:
        await update.message.reply_text(
            f"✅ Warranty: *{days}* days\n\n"
            "Step 6/7: Enter *warranty details/terms*:\n"
            "(or tap ⏭ Skip to leave empty)",
            parse_mode="Markdown",
            reply_markup=skip_keyboard(),
        )
        return ADD_WARRANTY_DETAILS
    else:
        context.user_data["new_product"]["warranty_details"] = ""
        await update.message.reply_text(
            "✅ No warranty set.\n\n"
            "Step 7/7: Send the *product image*:\n"
            "(or tap ⏭ Skip to add without image)",
            parse_mode="Markdown",
            reply_markup=skip_keyboard(),
        )
        return ADD_IMAGE


async def add_warranty_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive warranty details."""
    text = update.message.text.strip()
    context.user_data["new_product"]["warranty_details"] = "" if text == "⏭ Skip" else text
    await update.message.reply_text(
        "✅ Got it!\n\n"
        "Step 7/7: Send the *product image*:\n"
        "(or tap ⏭ Skip to add without image)",
        parse_mode="Markdown",
        reply_markup=skip_keyboard(),
    )
    return ADD_IMAGE


async def add_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive product image or skip."""
    product_data = context.user_data["new_product"]
    image_path = ""

    if update.message.text and update.message.text.strip() == "⏭ Skip":
        pass  # No image
    elif update.message.photo:
        photo = update.message.photo[-1]
        os.makedirs(IMAGES_DIR, exist_ok=True)
        file = await photo.get_file()
        image_path = os.path.join(
            IMAGES_DIR, f"product_{photo.file_unique_id}.jpg"
        )
        await file.download_to_drive(image_path)
    else:
        await update.message.reply_text(
            "❌ Please send a *photo* or tap ⏭ Skip:",
            parse_mode="Markdown",
        )
        return ADD_IMAGE

    product_id = add_product(
        name=product_data["name"],
        description=product_data.get("description", ""),
        price=product_data["price"],
        stock=product_data["stock"],
        warranty_days=product_data.get("warranty_days", 0),
        warranty_details=product_data.get("warranty_details", ""),
        image_path=image_path,
    )

    summary = (
        f"✅ *Product Added Successfully!*\n\n"
        f"🆔 ID: {product_id}\n"
        f"📦 Name: {product_data['name']}\n"
        f"💰 Price: {format_price(product_data['price'])}\n"
        f"📊 Stock: {product_data['stock']}\n"
        f"🛡 Warranty: {product_data.get('warranty_days', 0)} days\n"
        f"🖼 Image: {'Yes' if image_path else 'No'}"
    )

    await update.message.reply_text(
        summary, parse_mode="Markdown", reply_markup=admin_keyboard()
    )

    context.user_data.pop("new_product", None)
    return ConversationHandler.END


async def add_image_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo message in ADD_IMAGE state."""
    return await add_image(update, context)


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel any ongoing conversation."""
    context.user_data.pop("new_product", None)
    context.user_data.pop("edit_product_id", None)
    context.user_data.pop("edit_field", None)
    context.user_data.pop("new_pm", None)
    await update.message.reply_text(
        "❌ Cancelled.", reply_markup=admin_keyboard()
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════
#  MANAGE PRODUCTS
# ═══════════════════════════════════════════════════════════════════

async def manage_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all products with manage buttons."""
    if not is_admin(update.effective_user.id):
        return

    products = get_all_products()
    if not products:
        await update.message.reply_text(
            "📦 No products yet. Use ➕ Add Product to create one!",
            reply_markup=admin_keyboard(),
        )
        return

    await update.message.reply_text(
        f"📦 *Manage Products* ({len(products)} total)\n" + "─" * 30,
        parse_mode="Markdown",
    )

    for product in products:
        status = "🟢 Active" if product["is_active"] else "🔴 Inactive"
        text = (
            f"🆔 *#{product['id']}* — {product['name']}\n"
            f"💰 {format_price(product['price'])} | 📦 Stock: {product['stock']}\n"
            f"🛡 Warranty: {product['warranty_days']} days\n"
            f"Status: {status}"
        )
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=product_manage_buttons(product["id"]),
        )


async def handle_toggle_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle product active/inactive."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    new_status = toggle_product_active(product_id)

    if new_status is None:
        await query.edit_message_text("❌ Product not found.")
        return

    status_text = "🟢 Active" if new_status else "🔴 Inactive"
    product = get_product(product_id)
    text = (
        f"🆔 *#{product['id']}* — {product['name']}\n"
        f"💰 {format_price(product['price'])} | 📦 Stock: {product['stock']}\n"
        f"🛡 Warranty: {product['warranty_days']} days\n"
        f"Status: {status_text}\n\n"
        f"✅ Status updated!"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=product_manage_buttons(product_id),
    )


async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show edit options for a product."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    text = (
        f"✏️ *Edit Product #{product_id}*\n\n"
        f"📦 Name: {product['name']}\n"
        f"📄 Desc: {product['description'] or 'N/A'}\n"
        f"💰 Price: {format_price(product['price'])}\n"
        f"📊 Stock: {product['stock']}\n"
        f"🛡 Warranty: {product['warranty_days']} days\n"
        f"📋 Warranty Info: {product['warranty_details'] or 'N/A'}\n"
        f"🖼 Image: {'Yes' if product['image_path'] else 'No'}\n\n"
        f"Select what to edit:"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=product_edit_buttons(product_id),
    )


async def handle_edit_field_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle edit field selection from inline buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data
    prefix = data.split("_")[0]
    product_id = int(data.split("_")[1])

    field_map = {
        "ename": ("name", "product name"),
        "edesc": ("description", "product description"),
        "eprice": ("price", "price (number)"),
        "estock": ("stock", "stock quantity (number)"),
        "ewdays": ("warranty_days", "warranty days (number)"),
        "ewinfo": ("warranty_details", "warranty details/terms"),
        "eimg": ("image_path", "product image (send a photo)"),
    }

    if prefix not in field_map:
        return

    field, label = field_map[prefix]
    context.user_data["edit_product_id"] = product_id
    context.user_data["edit_field"] = field
    context.user_data["edit_is_image"] = (field == "image_path")

    await query.message.reply_text(
        f"✏️ Enter the new *{label}* for product #{product_id}:",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )


async def handle_edit_back(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to manage buttons from edit view."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    status = "🟢 Active" if product["is_active"] else "🔴 Inactive"
    text = (
        f"🆔 *#{product['id']}* — {product['name']}\n"
        f"💰 {format_price(product['price'])} | 📦 Stock: {product['stock']}\n"
        f"🛡 Warranty: {product['warranty_days']} days\n"
        f"Status: {status}"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=product_manage_buttons(product_id),
    )


async def handle_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the new value for an edited field."""
    product_id = context.user_data.get("edit_product_id")
    field = context.user_data.get("edit_field")
    is_image = context.user_data.get("edit_is_image", False)

    if not product_id or not field:
        return False

    if is_image:
        if update.message.photo:
            photo = update.message.photo[-1]
            os.makedirs(IMAGES_DIR, exist_ok=True)
            file = await photo.get_file()
            image_path = os.path.join(
                IMAGES_DIR, f"product_{photo.file_unique_id}.jpg"
            )
            await file.download_to_drive(image_path)
            update_product_field(product_id, "image_path", image_path)
            await update.message.reply_text(
                "✅ Product image updated!",
                reply_markup=admin_keyboard(),
            )
        else:
            await update.message.reply_text(
                "❌ Please send a *photo*:", parse_mode="Markdown"
            )
            return True
    else:
        value = update.message.text.strip()
        menu_buttons = {
            "🛍 Products", "🛒 My Purchases", "🛡 Warranty", "💬 Help / Chat",
            "➕ Add Product", "📦 Manage Products", "📊 Inventory", "📋 Orders",
            "💳 Payment Methods", "📢 Broadcast", "👥 Users", "/start", "/admin"
        }
        if value in menu_buttons or value.startswith("/"):
            context.user_data.pop("edit_product_id", None)
            context.user_data.pop("edit_field", None)
            context.user_data.pop("edit_is_image", None)
            return False

        if field in ("price",):
            try:
                value = float(value)
                if value <= 0:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("❌ Enter a valid positive number:")
                return True

        if field in ("stock", "warranty_days"):
            try:
                value = int(value)
                if value < 0:
                    raise ValueError
            except ValueError:
                await update.message.reply_text("❌ Enter a valid non-negative number:")
                return True

        update_product_field(product_id, field, value)
        await update.message.reply_text(
            f"✅ Product #{product_id} *{field}* updated!",
            parse_mode="Markdown",
            reply_markup=admin_keyboard(),
        )

    context.user_data.pop("edit_product_id", None)
    context.user_data.pop("edit_field", None)
    context.user_data.pop("edit_is_image", None)
    return True


async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for delete confirmation."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    await query.edit_message_text(
        f"⚠️ *Delete Product?*\n\n"
        f"📦 {product['name']}\n"
        f"💰 {format_price(product['price'])}\n\n"
        f"This action cannot be undone!",
        parse_mode="Markdown",
        reply_markup=delete_confirm_buttons(product_id),
    )


async def handle_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and delete product."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if product and product["image_path"] and os.path.exists(product["image_path"]):
        try:
            os.remove(product["image_path"])
        except OSError:
            pass

    delete_product(product_id)
    await query.edit_message_text(
        f"✅ Product #{product_id} deleted successfully."
    )


async def handle_delete_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel product deletion."""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.edit_message_text("❌ Product not found.")
        return

    status = "🟢 Active" if product["is_active"] else "🔴 Inactive"
    text = (
        f"🆔 *#{product['id']}* — {product['name']}\n"
        f"💰 {format_price(product['price'])} | 📦 Stock: {product['stock']}\n"
        f"🛡 Warranty: {product['warranty_days']} days\n"
        f"Status: {status}"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=product_manage_buttons(product_id),
    )


# ═══════════════════════════════════════════════════════════════════
#  PAYMENT METHODS MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

async def show_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all payment methods with manage buttons."""
    if not is_admin(update.effective_user.id):
        return

    methods = get_all_payment_methods()
    if not methods:
        await update.message.reply_text(
            "💳 No payment methods yet.\n"
            "Use the button below to add one!\n\n"
            "Type /addpayment to add a payment method.",
            reply_markup=admin_keyboard(),
        )
        return

    await update.message.reply_text(
        f"💳 *Payment Methods* ({len(methods)} total)\n" + "─" * 30,
        parse_mode="Markdown",
    )

    for pm in methods:
        status = "🟢 Active" if pm["is_active"] else "🔴 Inactive"
        text = (
            f"*{pm['name']}*\n"
            f"`{pm['address']}`\n"
            f"Status: {status}"
        )
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=payment_method_manage_buttons(pm["id"]),
        )

    await update.message.reply_text(
        "💡 Type /addpayment to add a new payment method.",
        reply_markup=admin_keyboard(),
    )


async def add_payment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start add payment method wizard."""
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    context.user_data["new_pm"] = {}
    await update.message.reply_text(
        "💳 *Add Payment Method*\n\n"
        "Enter the *payment method name*\n"
        "(e.g. Binance BEP20, bKash, Nagad):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return PM_NAME


async def add_pm_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment method name."""
    context.user_data["new_pm"]["name"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ Got it!\n\n"
        "Now enter the *wallet/account address*\n"
        "(e.g. 0xABC123... or 01XXXXXXXXX):",
        parse_mode="Markdown",
        reply_markup=cancel_keyboard(),
    )
    return PM_ADDRESS


async def add_pm_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment method address and save."""
    pm_data = context.user_data["new_pm"]
    address = update.message.text.strip()

    pm_id = add_payment_method(pm_data["name"], address)

    await update.message.reply_text(
        f"✅ *Payment Method Added!*\n\n"
        f"💳 {pm_data['name']}\n"
        f"`{address}`\n"
        f"🆔 ID: {pm_id}",
        parse_mode="Markdown",
        reply_markup=admin_keyboard(),
    )

    context.user_data.pop("new_pm", None)
    return ConversationHandler.END


async def handle_pm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a payment method."""
    query = update.callback_query
    await query.answer()

    pm_id = int(query.data.split("_")[1])
    delete_payment_method(pm_id)
    await query.edit_message_text("✅ Payment method deleted.")


async def handle_pm_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle payment method active/inactive."""
    query = update.callback_query
    await query.answer()

    pm_id = int(query.data.split("_")[1])
    new_status = toggle_payment_method(pm_id)

    if new_status is None:
        await query.edit_message_text("❌ Payment method not found.")
        return

    pm = get_payment_method(pm_id)
    status = "🟢 Active" if new_status else "🔴 Inactive"
    text = (
        f"*{pm['name']}*\n"
        f"`{pm['address']}`\n"
        f"Status: {status}\n\n"
        f"✅ Status updated!"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=payment_method_manage_buttons(pm_id),
    )


# ═══════════════════════════════════════════════════════════════════
#  ORDER MANAGEMENT (Admin confirms/rejects payments)
# ═══════════════════════════════════════════════════════════════════

async def show_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show inventory overview."""
    if not is_admin(update.effective_user.id):
        return

    products = get_all_products()
    if not products:
        await update.message.reply_text(
            "📊 No products in inventory.",
            reply_markup=admin_keyboard(),
        )
        return

    text = "📊 *Inventory Overview*\n" + "─" * 30 + "\n\n"

    total_stock = 0
    total_value = 0.0

    for p in products:
        status = "🟢" if p["is_active"] else "🔴"
        stock_emoji = "✅" if p["stock"] > 0 else "❌"
        text += (
            f"{status} *{p['name']}*\n"
            f"   {stock_emoji} Stock: {p['stock']} | "
            f"💰 {format_price(p['price'])}\n\n"
        )
        total_stock += p["stock"]
        total_value += p["price"] * p["stock"]

    text += (
        "─" * 30 + "\n"
        f"📦 Total Products: {len(products)}\n"
        f"📊 Total Stock: {total_stock} units\n"
        f"💰 Total Value: {format_price(total_value)}"
    )

    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=admin_keyboard()
    )


async def show_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all orders for admin."""
    if not is_admin(update.effective_user.id):
        return

    orders = get_all_orders()
    if not orders:
        await update.message.reply_text(
            "📋 No orders yet.", reply_markup=admin_keyboard()
        )
        return

    await update.message.reply_text(
        f"📋 *All Orders* ({len(orders)} total)\n" + "─" * 30,
        parse_mode="Markdown",
    )

    for order in orders[:20]:
        status_emoji = {
            "awaiting_payment": "⏳",
            "payment_sent": "💸",
            "confirmed": "✅",
            "shipped": "🚚",
            "completed": "✔️",
            "rejected": "❌",
            "expired": "⏰",
        }.get(order["status"], "❓")

        text = (
            f"🆔 `{order['order_id']}` | {status_emoji} {order['status'].replace('_', ' ').title()}\n"
            f"👤 `{order['chat_id']}` | 📦 {order['product_name']}\n"
            f"💰 {format_price(order['price'])} | 📅 {format_date(order['created_at'])}"
        )

        if order["transaction_hash"]:
            text += f"\n🔗 TX: `{order['transaction_hash']}`"

        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=order_status_buttons(order["order_id"], order["chat_id"]),
        )


async def handle_admin_confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin confirms a customer's payment."""
    query = update.callback_query
    await query.answer("Payment confirmed! ✅")

    order_id = query.data.split("_")[1]
    confirm_order_payment(order_id)
    order = get_order_by_id(order_id)

    # Update admin message
    await query.edit_message_text(
        query.message.text + "\n\n✅ *PAYMENT CONFIRMED*",
        parse_mode="Markdown",
        reply_markup=admin_chat_only_button(order["chat_id"]) if order else None
    )

    # Notify customer
    if order:
        try:
            warranty_text = ""
            if order["warranty_expiry"]:
                from utils.helpers import format_date_short, warranty_status_text
                warranty_text = (
                    f"\n🛡 Warranty: {warranty_status_text(order['warranty_expiry'])}\n"
                    f"📅 Expires: {format_date_short(order['warranty_expiry'])}"
                )
                if order["warranty_details"]:
                    warranty_text += f"\n📋 Terms: {order['warranty_details']}"

            await context.bot.send_message(
                chat_id=order["chat_id"],
                text=(
                    f"✅ *Payment Confirmed!*\n\n"
                    f"🆔 Order: `{order_id}`\n"
                    f"📦 {order['product_name']}\n"
                    f"💰 {format_price(order['price'])}"
                    f"{warranty_text}\n\n"
                    f"Thank you for your purchase! 🎉"
                ),
                parse_mode="Markdown",
            )
        except Exception:
            pass


async def handle_admin_reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects a customer's payment."""
    query = update.callback_query
    await query.answer("Payment rejected.")

    order_id = query.data.split("_")[1]
    reject_order_payment(order_id)
    order = get_order_by_id(order_id)

    await query.edit_message_text(
        query.message.text + "\n\n❌ *PAYMENT REJECTED — Stock restored*",
        parse_mode="Markdown",
        reply_markup=admin_chat_only_button(order["chat_id"]) if order else None
    )

    # Notify customer
    if order:
        try:
            await context.bot.send_message(
                chat_id=order["chat_id"],
                text=(
                    f"❌ *Payment Rejected*\n\n"
                    f"🆔 Order: `{order_id}`\n"
                    f"📦 {order['product_name']}\n\n"
                    f"Your payment could not be verified.\n"
                    f"Please contact support if you believe this is an error."
                ),
                parse_mode="Markdown",
            )
        except Exception:
            pass


async def handle_order_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order status update from inline buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data
    parts = data.split("_", 1)
    action = parts[0]
    order_id = parts[1]

    status_map = {
        "oconfirm": "confirmed",
        "oshipped": "shipped",
        "ocomplete": "completed",
    }

    new_status = status_map.get(action)
    if not new_status:
        return

    update_order_status(order_id, new_status)
    order = get_order_by_id(order_id)

    status_emoji = {
        "confirmed": "✅",
        "shipped": "🚚",
        "completed": "✔️",
    }.get(new_status, "❓")

    text = (
        f"🆔 `{order['order_id']}` | {status_emoji} {new_status.title()}\n"
        f"👤 `{order['chat_id']}` | 📦 {order['product_name']}\n"
        f"💰 {format_price(order['price'])}\n\n"
        f"✅ Status updated!"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=order_status_buttons(order_id, order["chat_id"]),
    )

    # Notify customer
    try:
        customer_msg = (
            f"📦 *Order Update*\n\n"
            f"🆔 Order: `{order_id}`\n"
            f"📊 Status: {status_emoji} *{new_status.title()}*"
        )
        await context.bot.send_message(
            chat_id=order["chat_id"],
            text=customer_msg,
            parse_mode="Markdown",
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════
#  ADMIN ↔ CUSTOMER CHAT SYSTEM
# ═══════════════════════════════════════════════════════════════════

async def start_chat_with_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin clicks Chat button — enter chat mode with customer."""
    query = update.callback_query
    await query.answer()

    customer_chat_id = int(query.data.split("_")[1])
    customer = get_user(customer_chat_id)
    customer_name = customer["first_name"] if customer else "Customer"
    customer_username = customer["username"] if customer else None

    # Store active chat in bot_data (shared across all users)
    context.bot_data["admin_chat_with"] = customer_chat_id

    await query.message.reply_text(
        f"💬 *Chat Mode Active*\n\n"
        f"👤 Chatting with: {customer_name} (@{customer_username or 'N/A'})\n"
        f"🆔 Chat ID: `{customer_chat_id}`\n\n"
        f"All your messages will be forwarded to this customer.\n"
        f"Press 🔚 *Close Chat* when you're done.",
        parse_mode="Markdown",
        reply_markup=close_chat_keyboard(),
    )

    # Notify customer
    try:
        await context.bot.send_message(
            chat_id=customer_chat_id,
            text=(
                "💬 *Support Chat Started*\n\n"
                "An admin has connected with you.\n"
                "You can now send messages and they'll be forwarded to support."
            ),
            parse_mode="Markdown",
        )
    except Exception:
        pass


async def close_admin_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin closes the chat session."""
    customer_chat_id = context.bot_data.get("admin_chat_with")

    context.bot_data.pop("admin_chat_with", None)

    await update.message.reply_text(
        "🔚 Chat closed.",
        reply_markup=admin_keyboard(),
    )

    # Notify customer
    if customer_chat_id:
        try:
            await context.bot.send_message(
                chat_id=customer_chat_id,
                text="💬 *Chat Ended*\n\nThe support session has been closed. Thank you!",
                parse_mode="Markdown",
            )
        except Exception:
            pass


async def forward_admin_message_to_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward admin's message to the customer they're chatting with."""
    customer_chat_id = context.bot_data.get("admin_chat_with")
    if not customer_chat_id:
        return False

    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                chat_id=customer_chat_id,
                photo=photo.file_id,
                caption=f"💬 *Support:*\n{update.message.caption or ''}",
                parse_mode="Markdown",
            )
        elif update.message.text:
            await context.bot.send_message(
                chat_id=customer_chat_id,
                text=f"💬 *Support:*\n{update.message.text}",
                parse_mode="Markdown",
            )
        return True
    except Exception:
        await update.message.reply_text(
            "❌ Failed to send message to customer.",
            reply_markup=close_chat_keyboard(),
        )
        return True


async def forward_customer_message_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward customer's message to admin during active chat."""
    user_id = update.effective_user.id
    admin_chatting_with = context.bot_data.get("admin_chat_with")

    if admin_chatting_with != user_id:
        return False

    user = update.effective_user

    # Format customer full name and username for messages
    cust_name = user.first_name
    if user.last_name:
        cust_name += f" {user.last_name}"
    username_text = f" (@{user.username})" if user.username else ""

    try:
        if update.message.photo:
            photo = update.message.photo[-1]
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=photo.file_id,
                caption=f"👤 *{cust_name}{username_text}:*\n{update.message.caption or ''}",
                parse_mode="Markdown",
            )
        elif update.message.text:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"👤 *{cust_name}{username_text}:*\n{update.message.text}",
                parse_mode="Markdown",
            )
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════
#  USERS
# ═══════════════════════════════════════════════════════════════════

async def show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics."""
    if not is_admin(update.effective_user.id):
        return

    count = get_user_count()
    users = get_all_users()

    text = (
        f"👥 *User Statistics*\n\n"
        f"📊 Total Users: *{count}*\n"
        f"{'─' * 30}\n\n"
    )

    for user in users[:20]:
        text += (
            f"👤 {user['first_name'] or 'N/A'} "
            f"(@{user['username'] or 'N/A'})\n"
            f"   🆔 `{user['chat_id']}` | "
            f"📅 {format_date(user['joined_at'])}\n\n"
        )

    if count > 20:
        text += f"\n... and {count - 20} more users."

    await update.message.reply_text(
        text, parse_mode="Markdown", reply_markup=admin_keyboard()
    )


# ═══════════════════════════════════════════════════════════════════
#  BUILD CONVERSATION HANDLERS
# ═══════════════════════════════════════════════════════════════════

def get_add_product_handler():
    """Create the Add Product conversation handler."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^➕ Add Product$") & filters.User(ADMIN_CHAT_ID),
                add_product_start,
            ),
        ],
        states={
            ADD_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_name,
                ),
            ],
            ADD_DESC: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_desc,
                ),
            ],
            ADD_PRICE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_price,
                ),
            ],
            ADD_STOCK: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_stock,
                ),
            ],
            ADD_WARRANTY_DAYS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_warranty_days,
                ),
            ],
            ADD_WARRANTY_DETAILS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_warranty_details,
                ),
            ],
            ADD_IMAGE: [
                MessageHandler(filters.PHOTO, add_image_photo),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_image,
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Cancel$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation),
        ],
    )


def get_add_payment_handler():
    """Create the Add Payment Method conversation handler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("addpayment", add_payment_start),
        ],
        states={
            PM_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_pm_name,
                ),
            ],
            PM_ADDRESS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Cancel$"),
                    add_pm_address,
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Cancel$"), cancel_conversation),
            CommandHandler("cancel", cancel_conversation),
        ],
    )
