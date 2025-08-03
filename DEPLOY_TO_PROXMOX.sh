#!/bin/bash

# Crypto Arbitrage Bot - Proxmox Deployment Helper
# This script helps copy files from local machine to Proxmox and run setup

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
LOCAL_DIR="$(pwd)"
REMOTE_USER="root"
REMOTE_DIR="/opt/arbitrage-bot"
SCRIPT_NAME="$(basename "$0")"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Display banner
cat << "EOF"
🚀 Crypto Arbitrage Bot - Proxmox Deployment Helper
==================================================

This script will help you deploy the arbitrage bot to your Proxmox server.

Prerequisites:
- Proxmox server with SSH access
- Root or sudo access on Proxmox
- Local machine with SSH client

EOF

# Get Proxmox server details
read -p "Enter Proxmox server IP/hostname: " PROXMOX_HOST
read -p "Enter SSH username [root]: " SSH_USER
SSH_USER=${SSH_USER:-root}
read -p "Enter SSH port [22]: " SSH_PORT
SSH_PORT=${SSH_PORT:-22}

if [[ -z "$PROXMOX_HOST" ]]; then
    error "Proxmox host is required"
fi

# Test SSH connection
log "Testing SSH connection to $PROXMOX_HOST..."
ssh -p $SSH_PORT $SSH_USER@$PROXMOX_HOST "echo 'Connection successful'" || error "SSH connection failed"

# Create deployment commands
cat << EOF > deploy_commands.sh
#!/bin/bash
# Commands to run on Proxmox server

echo "🚀 Starting Proxmox deployment..."

# Create application directory
mkdir -p /opt/arbitrage-bot/{app,config,logs,data,backups}
cd /opt/arbitrage-bot

# Set permissions
chown -R root:root /opt/arbitrage-bot
chmod 755 /opt/arbitrage-bot

# Copy deployment script
chmod +x proxmox_deployment.sh

# Run automated setup
./proxmox_deployment.sh

echo "✅ Proxmox setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure environment: nano /opt/arbitrage-bot/.env"
echo "2. Start services: systemctl start arbitrage-bot slack-bot"
echo "3. Check status: systemctl status arbitrage-bot"
echo "4. View logs: journalctl -u arbitrage-bot -f"
EOF

chmod +x deploy_commands.sh

# Display deployment steps
cat << EOF

📋 Deployment Steps:
1. Copy files to Proxmox
2. Run automated setup
3. Configure environment variables
4. Start services
5. Test functionality

EOF

# Step 1: Copy files to Proxmox
log "Step 1: Copying files to Proxmox..."
rsync -avz --exclude='.git' --exclude='__pycache__' \
    --exclude='*.log' --exclude='*.pyc' \
    -e "ssh -p $SSH_PORT" \
    ./ $SSH_USER@$PROXMOX_HOST:/opt/arbitrage-bot/

# Step 2: Run setup on Proxmox
log "Step 2: Running automated setup..."
ssh -p $SSH_PORT $SSH_USER@$PROXMOX_HOST "cd /opt/arbitrage-bot && chmod +x proxmox_deployment.sh && ./proxmox_deployment.sh"

# Step 3: Configuration prompt
cat << EOF

🎯 Step 3: Configuration Required

The bot is now installed on your Proxmox server!

Next, you need to configure it:

1. SSH into your Proxmox server:
   ssh -p $SSH_PORT $SSH_USER@$PROXMOX_HOST

2. Configure environment variables:
   cd /opt/arbitrage-bot
   cp .env.example .env
   nano .env

3. Add your configuration:
   - Wallet private keys
   - Slack webhook URL
   - API keys

4. Start services:
   systemctl start arbitrage-bot slack-bot
   systemctl enable arbitrage-bot slack-bot

5. Test the setup:
   python proxmox_test_suite.py

6. Monitor logs:
   journalctl -u arbitrage-bot -f

EOF

# Create quick reference
cat << EOF > quick_reference.md
# 🚀 Quick Deployment Reference

## SSH Commands
ssh -p $SSH_PORT $SSH_USER@$PROXMOX_HOST

## File Locations
- App Directory: /opt/arbitrage-bot
- Logs: /opt/arbitrage-bot/logs/
- Config: /opt/arbitrage-bot/.env
- Scripts: /opt/arbitrage-bot/

## Service Management
systemctl status arbitrage-bot
systemctl start arbitrage-bot
systemctl stop arbitrage-bot
systemctl restart arbitrage-bot

## Logs
journalctl -u arbitrage-bot -f
journalctl -u slack-bot -f

## Testing
python proxmox_test_suite.py
./health-check.sh

## Monitoring URLs
- Bot Health: http://$PROXMOX_HOST:8080/health
- Grafana: http://$PROXMOX_HOST:3000 (admin/admin123)
- Prometheus: http://$PROXMOX_HOST:9090

## Slack Commands
/arbitrage help
/arbitrage status
/arbitrage pairs
/arbitrage profit
EOF

log "✅ Deployment helper script created!"
log "📋 Quick reference saved to: quick_reference.md"
log "🎯 Ready to deploy to Proxmox server: $PROXMOX_HOST"

# Display final instructions
cat << EOF

🎉 Deployment Complete!

Your arbitrage bot is ready for deployment. Run this script to:
1. Copy all files to your Proxmox server
2. Run the automated setup
3. Configure the bot

Usage:
./deploy_to_proxmox.sh

EOF