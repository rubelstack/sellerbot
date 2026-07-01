"""
GET YOUR PLUS — Keyboard Builders
Reply keyboards for customer/admin and inline keyboards for products/orders/payments/chat.
Made by Rubel
"""

from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
)
from utils.helpers import format_price


# ─── Reply Keyboards ────────────────────────────────────────────────

def customer_keyboard():
    """Main reply keyboard for customers."""
    keyboard = [
        [KeyboardButton("🛍 Products"), KeyboardButton("🛒 My Purchases")],
        [KeyboardButton("🛡 Warranty"), KeyboardButton("💬 Help / Chat")],
    ]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )


def admin_keyboard():
    """Main reply keyboard for admin."""
    keyboard = [
        [KeyboardButton("➕ Add Product"), KeyboardButton("📦 Manage Products")],
        [KeyboardButton("📊 Inventory"), KeyboardButton("📋 Orders")],
        [KeyboardButton("💳 Payment Methods"), KeyboardButton("📢 Broadcast")],
        [KeyboardButton("👥 Users")],
    ]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )


def cancel_keyboard():
    """Cancel keyboard for conversation flows."""
    keyboard = [[KeyboardButton("❌ Cancel")]]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )


def skip_keyboard():
    """Skip keyboard for optional steps."""
    keyboard = [[KeyboardButton("⏭ Skip"), KeyboardButton("❌ Cancel")]]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )


def confirm_keyboard():
    """Confirm/Cancel keyboard."""
    keyboard = [[KeyboardButton("✅ Confirm"), KeyboardButton("❌ Cancel")]]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )


def close_chat_keyboard():
    """Reply keyboard for admin during active chat session."""
    keyboard = [[KeyboardButton("🔚 Close Chat")]]
    return ReplyKeyboardMarkup(
        keyboard, resize_keyboard=True, one_time_keyboard=False
    )


# ─── Inline Keyboards ───────────────────────────────────────────────

def product_buy_button(product_id: int):
    """Inline buy and details buttons for a product."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📄 Details", callback_data=f"details_{product_id}"),
            InlineKeyboardButton("🛒 Buy Now", callback_data=f"buy_{product_id}"),
        ]
    ])


def product_details_back_button(product_id: int):
    """Back button for details view."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back", callback_data=f"view_card_{product_id}")]
    ])


def product_manage_buttons(product_id: int):
    """Inline edit/delete buttons for admin product management."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_{product_id}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"del_{product_id}"),
        ],
        [
            InlineKeyboardButton(
                "🔄 Toggle Active", callback_data=f"toggle_{product_id}"
            ),
        ],
    ])


def product_edit_buttons(product_id: int):
    """Inline buttons for editing specific product fields."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Name", callback_data=f"ename_{product_id}"),
            InlineKeyboardButton("📄 Description", callback_data=f"edesc_{product_id}"),
        ],
        [
            InlineKeyboardButton("💰 Price", callback_data=f"eprice_{product_id}"),
            InlineKeyboardButton("📦 Stock", callback_data=f"estock_{product_id}"),
        ],
        [
            InlineKeyboardButton("🛡 Warranty Days", callback_data=f"ewdays_{product_id}"),
            InlineKeyboardButton("📋 Warranty Info", callback_data=f"ewinfo_{product_id}"),
        ],
        [
            InlineKeyboardButton("🖼 Image", callback_data=f"eimg_{product_id}"),
        ],
        [
            InlineKeyboardButton("« Back", callback_data=f"eback_{product_id}"),
        ],
    ])


def order_status_buttons(order_id: str, customer_chat_id: int):
    """Inline buttons for admin to update order status and chat with customer."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"oconfirm_{order_id}"),
            InlineKeyboardButton("🚚 Shipped", callback_data=f"oshipped_{order_id}"),
        ],
        [
            InlineKeyboardButton("✔️ Complete", callback_data=f"ocomplete_{order_id}"),
        ],
        [
            InlineKeyboardButton(
                "💬 Chat with Customer",
                callback_data=f"achat_{customer_chat_id}",
            ),
        ],
    ])


def admin_chat_only_button(customer_chat_id: int):
    """Inline button to chat with customer only."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💬 Chat with Customer",
                callback_data=f"achat_{customer_chat_id}",
            )
        ]
    ])


def payment_screen_buttons(order_id: str):
    """Inline buttons for payment screen (cancel order)."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "❌ Cancel Order",
                callback_data=f"paycancel_{order_id}",
            )
        ]
    ])



def buy_confirm_button(product_id: int):
    """Confirm purchase inline button."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Confirm Purchase", callback_data=f"confirm_buy_{product_id}"
            ),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_buy"),
        ]
    ])


def payment_done_button(order_id: str):
    """Payment Done inline button after customer submits tx hash."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Payment Done", callback_data=f"paydone_{order_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "❌ Cancel Order", callback_data=f"paycancel_{order_id}"
            ),
        ],
    ])


def admin_order_notification_buttons(order_id: str, customer_chat_id: int):
    """Admin order notification — confirm/reject/chat buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Confirm Payment", callback_data=f"aconfirm_{order_id}"
            ),
            InlineKeyboardButton(
                "❌ Reject", callback_data=f"areject_{order_id}"
            ),
        ],
        [
            InlineKeyboardButton(
                "💬 Chat with Customer",
                callback_data=f"achat_{customer_chat_id}",
            ),
        ],
    ])


def payment_method_manage_buttons(pm_id: int):
    """Inline buttons for managing a payment method."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗑 Delete", callback_data=f"pmdel_{pm_id}"),
            InlineKeyboardButton("🔄 Toggle", callback_data=f"pmtoggle_{pm_id}"),
        ],
    ])


def broadcast_confirm_button():
    """Confirm broadcast inline button."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "✅ Send to All", callback_data="broadcast_confirm"
            ),
            InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel"),
        ]
    ])


def delete_confirm_buttons(product_id: int):
    """Confirm product deletion."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚠️ Yes, Delete", callback_data=f"delconfirm_{product_id}"
            ),
            InlineKeyboardButton("❌ No", callback_data=f"delcancel_{product_id}"),
        ]
    ])


def claim_warranty_button(order_id: str):
    """Inline button to claim warranty."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🛡️ Claim Warranty",
                callback_data=f"claimw_{order_id}",
            )
        ]
    ])

