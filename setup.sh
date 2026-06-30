#!/bin/bash

# ═══════════════════════════════════════════════════════════════
#  GET YOUR PLUS — Telegram Seller Bot Setup
#  Made by Rubel
# ═══════════════════════════════════════════════════════════════

# ─── Colors ──────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# ─── Fancy Banner ────────────────────────────────────────────
clear
echo ""
echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║${CYAN}   ██████╗ ███████╗████████╗   ██╗   ██╗ ██████╗ ██╗   ██╗██████╗  ${NC}"
echo -e "${PURPLE}║${CYAN}  ██╔════╝ ██╔════╝╚══██╔══╝   ╚██╗ ██╔╝██╔═══██╗██║   ██║██╔══██╗ ${NC}"
echo -e "${PURPLE}║${CYAN}  ██║  ███╗█████╗     ██║       ╚████╔╝ ██║   ██║██║   ██║██████╔╝ ${NC}"
echo -e "${PURPLE}║${CYAN}  ██║   ██║██╔══╝     ██║        ╚██╔╝  ██║   ██║██║   ██║██╔══██╗ ${NC}"
echo -e "${PURPLE}║${CYAN}  ╚██████╔╝███████╗   ██║         ██║   ╚██████╔╝╚██████╔╝██║  ██║ ${NC}"
echo -e "${PURPLE}║${CYAN}   ╚═════╝ ╚══════╝   ╚═╝         ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║${YELLOW}              ██████╗ ██╗     ██╗   ██╗███████╗              ${NC}"
echo -e "${PURPLE}║${YELLOW}              ██╔══██╗██║     ██║   ██║██╔════╝              ${NC}"
echo -e "${PURPLE}║${YELLOW}              ██████╔╝██║     ██║   ██║███████╗              ${NC}"
echo -e "${PURPLE}║${YELLOW}              ██╔═══╝ ██║     ██║   ██║╚════██║              ${NC}"
echo -e "${PURPLE}║${YELLOW}              ██║     ███████╗╚██████╔╝███████║              ${NC}"
echo -e "${PURPLE}║${YELLOW}              ╚═╝     ╚══════╝ ╚═════╝ ╚══════╝              ${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}║${DIM}${WHITE}          Telegram Seller Bot • Setup Wizard v1.1.2         ${NC}"
echo -e "${PURPLE}║${DIM}${GREEN}                   Made by Rubel 💚                         ${NC}"
echo -e "${PURPLE}║                                                              ║${NC}"
echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ─── Functions ───────────────────────────────────────────────
print_step() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${WHITE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

print_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "  ${CYAN}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "  ${RED}❌ $1${NC}"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ─── Check if running as root ────────────────────────────────
IS_ROOT=false
if [ "$(id -u)" -eq 0 ]; then
    IS_ROOT=true
fi

if [ "$IS_ROOT" = false ]; then
    echo -e "  ${YELLOW}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "  ${YELLOW}║  ⚠️  This script needs root access for installing  ║${NC}"
    echo -e "  ${YELLOW}║  packages and creating the systemd service.        ║${NC}"
    echo -e "  ${YELLOW}║                                                    ║${NC}"
    echo -e "  ${YELLOW}║  ${WHITE}Please run:  ${CYAN}sudo ./setup.sh${YELLOW}                    ║${NC}"
    echo -e "  ${YELLOW}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    exit 1
fi

# ─── Step 1: Check & Install Python ─────────────────────────
print_step "Step 1/5 — Checking Python Installation"

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1)
    print_success "Python found: ${PYTHON_VERSION}"
else
    print_warning "Python 3 not found. Installing..."
    apt update -qq && apt install -y python3 python3-pip -qq
    if [ $? -eq 0 ]; then
        print_success "Python 3 installed successfully"
    else
        print_error "Failed to install Python 3. Please install manually."
        exit 1
    fi
fi

# Ensure pip is available
if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
    print_warning "pip not found. Installing..."
    apt install -y python3-pip -qq
fi
print_success "pip is available"

# ─── Step 2: Bot Configuration ──────────────────────────────
print_step "Step 2/5 — Bot Configuration"

echo -e "  ${CYAN}You'll need your Bot Token from @BotFather${NC}"
echo -e "  ${CYAN}and your Telegram Chat ID (numeric).${NC}"
echo ""

# Ask for Bot Token
while true; do
    echo -ne "  ${YELLOW}🔑 Enter your Bot Token: ${NC}"
    read -r BOT_TOKEN
    if [ -z "$BOT_TOKEN" ]; then
        print_error "Bot token cannot be empty!"
    elif [[ ! "$BOT_TOKEN" =~ ^[0-9]+: ]]; then
        print_error "Invalid token format! Should be like: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    else
        print_success "Bot token set!"
        break
    fi
done

echo ""

# Ask for Admin Chat ID
while true; do
    echo -ne "  ${YELLOW}👤 Enter Admin Chat ID: ${NC}"
    read -r ADMIN_CHAT_ID
    if [ -z "$ADMIN_CHAT_ID" ]; then
        print_error "Admin Chat ID cannot be empty!"
    elif [[ ! "$ADMIN_CHAT_ID" =~ ^[0-9]+$ ]]; then
        print_error "Chat ID must be a number!"
    else
        print_success "Admin Chat ID set!"
        break
    fi
done

# ─── Step 3: Create .env File ───────────────────────────────
print_step "Step 3/5 — Creating Configuration File"

cat > "${SCRIPT_DIR}/.env" << EOF
# ═══════════════════════════════════════════════════
#  GET YOUR PLUS — Bot Configuration
#  Made by Rubel
#  Generated on: $(date '+%Y-%m-%d %H:%M:%S')
# ═══════════════════════════════════════════════════

# Bot Token from @BotFather
BOT_TOKEN=${BOT_TOKEN}

# Admin Telegram Chat ID
ADMIN_CHAT_ID=${ADMIN_CHAT_ID}
EOF

print_success "Configuration saved to .env"
print_info "You can edit .env later to update credentials"

# ─── Step 4: Install Dependencies ───────────────────────────
print_step "Step 4/5 — Installing Dependencies"

echo -e "  ${CYAN}Installing Python packages...${NC}"
pip3 install -r "${SCRIPT_DIR}/requirements.txt" --break-system-packages -q 2>/dev/null || \
pip3 install -r "${SCRIPT_DIR}/requirements.txt" -q 2>/dev/null

if [ $? -eq 0 ]; then
    print_success "All dependencies installed"
else
    print_error "Failed to install dependencies!"
    print_info "Try manually: pip3 install -r requirements.txt"
    exit 1
fi

# ─── Step 5: Setup Data & Systemd ───────────────────────────
print_step "Step 5/5 — Final Setup"

# Create data directories
mkdir -p "${SCRIPT_DIR}/data/images"
print_success "Created data/images directory"

# Create systemd service
echo ""
echo -ne "  ${YELLOW}🖥️  Create systemd service for auto-start on boot? (y/n): ${NC}"
read -r CREATE_SERVICE

if [[ "$CREATE_SERVICE" =~ ^[Yy]$ ]]; then
    cat > /etc/systemd/system/getyourplus.service << SERVICEEOF
[Unit]
Description=GET YOUR PLUS Telegram Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=$(which python3) ${SCRIPT_DIR}/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SERVICEEOF

    systemctl daemon-reload
    systemctl enable getyourplus.service
    print_success "Systemd service created & enabled for auto-start"
    print_info "Start with: sudo systemctl start getyourplus.service"
    print_info "Logs with:  sudo journalctl -u getyourplus.service -f"
else
    print_info "Skipped systemd service creation"
    print_info "You can start manually with: python3 bot.py"
fi

# ─── Done! ───────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${WHITE}${BOLD}           🎉  SETUP COMPLETE!  🎉                            ${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${CYAN}   Your GET YOUR PLUS bot is ready to launch!                 ${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${YELLOW}   To start the bot:                                          ${NC}"
echo -e "${GREEN}║${WHITE}     python3 bot.py                                            ${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${YELLOW}   Or with systemd (if enabled):                              ${NC}"
echo -e "${GREEN}║${WHITE}     sudo systemctl start getyourplus.service                  ${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${YELLOW}   Useful commands:                                           ${NC}"
echo -e "${GREEN}║${WHITE}     sudo systemctl status getyourplus.service                 ${NC}"
echo -e "${GREEN}║${WHITE}     sudo systemctl restart getyourplus.service                ${NC}"
echo -e "${GREEN}║${WHITE}     sudo journalctl -u getyourplus.service -f                 ${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}║${DIM}${PURPLE}              Made with 💚 by Rubel                            ${NC}"
echo -e "${GREEN}║                                                              ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
