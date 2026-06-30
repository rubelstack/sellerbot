# 🛍 GET YOUR PLUS — Telegram Seller Bot

> **Made by Rubel** 💚

A full-featured Telegram bot for selling products with inventory management, order tracking, warranty system, and admin panel.

## ✨ Features

- **🛍 Product Catalog** — Browse products with images, prices & stock info
- **🛒 Purchase System** — One-click buying with unique order IDs (`GYP-XXXXX`)
- **🛡 Warranty Tracking** — Auto-calculated warranty with status checks
- **📦 Inventory Management** — Admin panel to add, edit, delete products
- **📢 Broadcast System** — Send messages to all users (text + photo)
- **💬 Help Chat** — Customer messages forwarded to admin
- **📋 Order Management** — View & update order status (pending → confirmed → shipped → completed)
- **👥 User Statistics** — Track total users

---

## 🚀 Quick Setup

### One Command Setup

```bash
git clone https://github.com/yourusername/sellerbot.git
cd sellerbot
chmod +x setup.sh
sudo ./setup.sh
```

The setup wizard will ask you for:
1. **Bot Token** — Get it from [@BotFather](https://t.me/BotFather) on Telegram
2. **Admin Chat ID** — Your Telegram numeric user ID

That's it! The script handles everything else automatically.

### Start the Bot

```bash
python3 bot.py
```

---

## 🖥️ Deploy on Armbian / Linux Server

### Step 1: Clone & Setup

```bash
cd /opt
git clone https://github.com/yourusername/sellerbot.git
cd sellerbot
chmod +x setup.sh
sudo ./setup.sh
```

During setup, select **Yes** when asked to create a systemd service.

### Step 2: Start & Manage

```bash
# Start the bot
sudo systemctl start getyourplus.service

# Check status
sudo systemctl status getyourplus.service

# View live logs
sudo journalctl -u getyourplus.service -f

# Restart
sudo systemctl restart getyourplus.service

# Stop
sudo systemctl stop getyourplus.service
```

The bot will **auto-start on boot** — no manual intervention needed.

---

## 📱 Bot Commands

### Customer Commands
| Command/Button | Description |
|----------------|-------------|
| `/start` | Start the bot & show menu |
| 🛍 Products | Browse available products |
| 🛒 My Purchases | View purchase history |
| 🛡 Warranty | Check warranty by Order ID |
| 💬 Help / Chat | Send message to support |

### Admin Commands
| Command/Button | Description |
|----------------|-------------|
| `/admin` | Show admin panel |
| ➕ Add Product | Add a new product (guided wizard) |
| 📦 Manage Products | Edit, delete, toggle products |
| 📊 Inventory | View stock overview |
| 📋 Orders | View & manage all orders |
| 📢 Broadcast | Send message to all users |
| 👥 Users | View user statistics |

---

## 📁 Project Structure

```
sellerbot/
├── bot.py              # Main entry point
├── config.py           # Configuration (reads from .env)
├── database.py         # SQLite database layer
├── setup.sh            # Interactive setup wizard
├── handlers/
│   ├── admin.py        # Admin panel handlers
│   ├── broadcast.py    # Broadcast system
│   └── customer.py     # Customer-facing handlers
├── utils/
│   ├── helpers.py      # Formatting & date utilities
│   ├── keyboard.py     # Keyboard builders
│   └── orderid.py      # Order ID generator
├── data/               # (auto-created, gitignored)
│   ├── images/         # Product images
│   └── sellerbot.db    # SQLite database
├── .env                # (auto-created by setup.sh, gitignored)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Manual Configuration

If you prefer manual setup over the wizard, create a `.env` file:

```env
BOT_TOKEN=your-bot-token-from-botfather
ADMIN_CHAT_ID=your-telegram-chat-id
```

Then install dependencies:

```bash
pip3 install -r requirements.txt
```

---

## 📝 License

This project is for private use by GET YOUR PLUS.

---

<p align="center">
  Made with 💚 by <b>Rubel</b>
</p>
