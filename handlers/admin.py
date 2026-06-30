"""
GET YOUR PLUS — Admin Handlers
Handles admin panel: product management, inventory, orders, users.
Uses ConversationHandler for multi-step flows.
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
)
from utils.keyboard import (
    admin_keyboard, cancel_keyboard, skip_keyboard,
    product_manage_buttons, product_edit_buttons,
    order_status_buttons, delete_confirm_buttons,
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


# ─── Admin Start ────────────────────────────────────────────────────

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin panel."""
    await update.message.reply_text(
        "🔐 *Admin Panel — GET YOUR PLUS*\n\n"
        "Use the buttons below to manage your store 👇",
        parse_mode="Markdown",
        reply_markup=admin_keyboard(),
    )


# ─── Add Product Conversation ───────────────────────────────────────

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
        # Download the highest resolution photo
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

    # Save to database
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
    await update.message.reply_text(
        "❌ Cancelled.", reply_markup=admin_keyboard()
    )
    return ConversationHandler.END


# ─── Manage Products ────────────────────────────────────────────────

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
        f"📄 Description: {product['description'] or 'N/A'}\n"
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
    # Parse: ename_1, edesc_1, eprice_1, estock_1, ewdays_1, ewinfo_1, eimg_1
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
                f"✅ Product image updated!",
                reply_markup=admin_keyboard(),
            )
        else:
            await update.message.reply_text(
                "❌ Please send a *photo*:", parse_mode="Markdown"
            )
            return True
    else:
        value = update.message.text.strip()

        # Validate numeric fields
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

    # Clear edit state
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


# ─── Inventory ──────────────────────────────────────────────────────

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


# ─── Orders ─────────────────────────────────────────────────────────

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

    for order in orders[:20]:  # Show latest 20
        status_emoji = {
            "pending": "⏳",
            "confirmed": "✅",
            "shipped": "🚚",
            "completed": "✔️",
        }.get(order["status"], "❓")

        text = (
            f"🆔 `{order['order_id']}`\n"
            f"👤 Chat ID: `{order['chat_id']}`\n"
            f"📦 {order['product_name']}\n"
            f"💰 {format_price(order['price'])}\n"
            f"📅 {format_date(order['created_at'])}\n"
            f"📊 {status_emoji} {order['status'].title()}"
        )
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=order_status_buttons(order["order_id"]),
        )


async def handle_order_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order status update from inline buttons."""
    query = update.callback_query
    await query.answer()

    data = query.data
    # oconfirm_GYP-XXXXX, oshipped_GYP-XXXXX, ocomplete_GYP-XXXXX
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
        f"🆔 `{order['order_id']}`\n"
        f"👤 Chat ID: `{order['chat_id']}`\n"
        f"📦 {order['product_name']}\n"
        f"💰 {format_price(order['price'])}\n"
        f"📅 {format_date(order['created_at'])}\n"
        f"📊 {status_emoji} {new_status.title()}\n\n"
        f"✅ Status updated!"
    )
    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=order_status_buttons(order_id),
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


# ─── Users ──────────────────────────────────────────────────────────

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

    for user in users[:20]:  # Show latest 20
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


# ─── Build Conversation Handlers ────────────────────────────────────

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
