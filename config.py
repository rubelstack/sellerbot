"""
GET YOUR PLUS — Configuration
Reads credentials from .env file. Run setup.sh to configure.
Made by Rubel
"""

import os
import sys

def _load_env():
    """Load .env file into os.environ."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        print("\033[91m")
        print("╔══════════════════════════════════════════════════╗")
        print("║  ❌  .env file not found!                        ║")
        print("║  Run ./setup.sh to configure the bot first.      ║")
        print("╚══════════════════════════════════════════════════╝")
        print("\033[0m")
        sys.exit(1)
    
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

_load_env()

# Bot Token (from @BotFather)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# Admin Telegram Chat ID
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))

if not BOT_TOKEN or ADMIN_CHAT_ID == 0:
    print("\033[91m")
    print("╔══════════════════════════════════════════════════╗")
    print("║  ❌  BOT_TOKEN or ADMIN_CHAT_ID is missing!      ║")
    print("║  Run ./setup.sh to configure the bot.            ║")
    print("╚══════════════════════════════════════════════════╝")
    print("\033[0m")
    sys.exit(1)

# Order ID prefix
ORDER_PREFIX = "GYP"

# Order ID length (characters after prefix)
ORDER_ID_LENGTH = 5

# Currency symbol
CURRENCY = "$"

# Database file path
DB_PATH = "data/sellerbot.db"

# Product images directory
IMAGES_DIR = "data/images"
