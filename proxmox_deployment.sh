#!/bin/bash

# Crypto Arbitrage Bot - Proxmox Deployment Script
# Automated setup for Ubuntu-based Proxmox server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/arbitrage-bot"
USER_NAME="arbitrage-bot"
SERVICE_NAME="arbitrage-bot"
SLACK_SERVICE_NAME="slack-bot"

# Logging
LOG_FILE="/var/log/arbitrage-bot-setup.log"

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}" | tee -a "$LOG_FILE"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   error "This script must be run as root (use sudo)"
fi

log "Starting Crypto Arbitrage Bot Proxmox deployment..."

# Update system
log "Updating system packages..."
apt update && apt upgrade -y

# Install dependencies
log "Installing system dependencies..."
apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget \
    nginx \
    fail2ban \
    ufw \
    docker.io \
    docker-compose \
    htop \
    vim \
    unzip \
    build-essential \
    software-properties-common

# Install Node.js for web interface (optional)
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt install -y nodejs

# Create application user
log "Creating application user..."
if ! id "$USER_NAME" &>/dev/null; then
    useradd -r -s /bin/false "$USER_NAME"
    log "User $USER_NAME created"
else
    log "User $USER_NAME already exists"
fi

# Create application directory
log "Creating application directory..."
mkdir -p "$APP_DIR"/{app,config,logs,data,backups}
chown -R "$USER_NAME:$USER_NAME" "$APP_DIR"

# Set up Python virtual environment
log "Setting up Python virtual environment..."
sudo -u "$USER_NAME" python3 -m venv "$APP_DIR/venv"
sudo -u "$USER_NAME" "$APP_DIR/venv/bin/pip" install --upgrade pip

# Install Python dependencies
log "Installing Python dependencies..."
sudo -u "$USER_NAME" "$APP_DIR/venv/bin/pip" install -r requirements.txt

# Configure firewall
log "Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8080/tcp  # Bot API
ufw allow 3000/tcp  # Grafana
ufw --force enable

# Configure fail2ban
log "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600
EOF

systemctl enable fail2ban
systemctl restart fail2ban

# Configure Nginx
log "Configuring Nginx..."
cat > /etc/nginx/sites-available/arbitrage-bot << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /grafana {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /prometheus {
        proxy_pass http://127.0.0.1:9090;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

ln -sf /etc/nginx/sites-available/arbitrage-bot /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t || error "Nginx configuration test failed"

# Create systemd services
log "Creating systemd services..."

# Arbitrage bot service
cat > /etc/systemd/system/$SERVICE_NAME.service << EOF
[Unit]
Description=Crypto Arbitrage Bot
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/monitorbot.py --with-slack-commands
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Slack bot service
cat > /etc/systemd/system/$SLACK_SERVICE_NAME.service << EOF
[Unit]
Description=Slack Bot Command Server
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/venv/bin
ExecStart=$APP_DIR/venv/bin/python $APP_DIR/slack_bot_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create log rotation
log "Setting up log rotation..."
cat > /etc/logrotate.d/arbitrage-bot << EOF
$APP_DIR/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 $USER_NAME $USER_NAME
    postrotate
        systemctl reload $SERVICE_NAME || true
        systemctl reload $SLACK_SERVICE_NAME || true
    endscript
}
EOF

# Create backup script
log "Creating backup script..."
cat > "$APP_DIR/backup.sh" << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/arbitrage-bot/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/arbitrage_bot_backup_$DATE.tar.gz"

# Create backup
tar -czf "$BACKUP_FILE" \
    /opt/arbitrage-bot/config \
    /opt/arbitrage-bot/logs \
    /opt/arbitrage-bot/data \
    2>/dev/null || true

# Keep only last 30 backups
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete

# Log backup
logger "Arbitrage bot backup created: $BACKUP_FILE"
EOF

chmod +x "$APP_DIR/backup.sh"

# Create health check script
log "Creating health check script..."
cat > "$APP_DIR/health-check.sh" << 'EOF'
#!/bin/bash
# Health check for arbitrage bot

# Check if services are running
if ! systemctl is-active --quiet arbitrage-bot; then
    echo "ERROR: Arbitrage bot service is not running"
    exit 1
fi

if ! systemctl is-active --quiet slack-bot; then
    echo "ERROR: Slack bot service is not running"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "ERROR: Disk usage is ${DISK_USAGE}%"
    exit 1
fi

# Check memory usage
MEMORY_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ "$MEMORY_USAGE" -gt 90 ]; then
    echo "WARNING: Memory usage is ${MEMORY_USAGE}%"
fi

echo "All health checks passed"
exit 0
EOF

chmod +x "$APP_DIR/health-check.sh"

# Create cron job for backups
log "Setting up cron jobs..."
(crontab -l 2>/dev/null; echo "0 2 * * * $APP_DIR/backup.sh") | crontab -

# Reload systemd and enable services
log "Enabling services..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl enable $SLACK_SERVICE_NAME
systemctl enable nginx

# Start services
log "Starting services..."
systemctl start nginx
systemctl start $SERVICE_NAME
systemctl start $SLACK_SERVICE_NAME

# Create .env template
log "Creating .env template..."
cat > "$APP_DIR/.env.template" << 'EOF'
# === WALLET CONFIGURATION ===
# NEVER commit this file to version control
POLYGON_PRIVATE_KEY=0x[YOUR_POLYGON_PRIVATE_KEY]
BSC_PRIVATE_KEY=0x[YOUR_BSC_PRIVATE_KEY]
AVALANCHE_PRIVATE_KEY=0x[YOUR_AVALANCHE_PRIVATE_KEY]

# === SLACK INTEGRATION ===
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/HERE
SLACK_BOT_TOKEN=xoxb-YOUR-BOT-TOKEN-HERE

# === BOT SETTINGS ===
MAX_LOAN_AMOUNT=50
PROFIT_THRESHOLD=3.0
SERVER_HOST=0.0.0.0
SERVER_PORT=8080

# === API KEYS ===
INFURA_PROJECT_ID=YOUR_INFURA_PROJECT_ID
EOF

# Create quick start guide
log "Creating quick start guide..."
cat > "$APP_DIR/QUICK_START.md" << 'EOF'
# 🚀 Quick Start Guide

## 1. Configure Environment
```bash
cd /opt/arbitrage-bot
cp .env.template .env
nano .env  # Add your wallet keys and Slack tokens
```

## 2. Test Configuration
```bash
python proxmox_test_suite.py
```

## 3. Monitor Services
```bash
systemctl status arbitrage-bot slack-bot
journalctl -u arbitrage-bot -f
```

## 4. Access Dashboards
- Bot Health: http://your-server-ip:8080/health
- Grafana: http://your-server-ip:3000 (admin/admin123)
- Prometheus: http://your-server-ip:9090

## 5. Slack Commands
```
/arbitrage help      # Show all commands
/arbitrage status    # Bot status
/arbitrage pairs     # List trading pairs
/arbitrage profit    # Show daily profit
```

## 6. Troubleshooting
```bash
# Check logs
journalctl -u arbitrage-bot -f

# Restart services
systemctl restart arbitrage-bot slack-bot

# Run health check
./health-check.sh
```

## 7. Backup
```bash
./backup.sh
```
EOF

# Set permissions
chown -R "$USER_NAME:$USER_NAME" "$APP_DIR"
chmod 600 "$APP_DIR/.env.template"

# Final status
log "Deployment completed successfully!"
log "Repository: https://github.com/Joelalbon/crypto-arbitrage-bot"
log "Next steps:"
log "1. Copy your bot files to $APP_DIR"
log "2. Configure .env file with your keys"
log "3. Run: systemctl restart arbitrage-bot slack-bot"
log "4. Check status: systemctl status arbitrage-bot"

# Display system info
echo ""
echo "===================================="
echo "🎉 Proxmox Deployment Complete!"
echo "===================================="
echo ""
echo "📁 Application Directory: $APP_DIR"
echo "🔧 Configuration File: $APP_DIR/.env"
echo "📊 Logs: journalctl -u arbitrage-bot -f"
echo "🩺 Health Check: $APP_DIR/health-check.sh"
echo "💾 Backup: $APP_DIR/backup.sh"
echo ""
echo "🌐 Access URLs:"
echo "   Bot API: http://$(hostname -I | awk '{print $1}'):8080"
echo "   Grafana: http://$(hostname -I | awk '{print $1}'):3000"
echo ""
echo "📖 Quick Start: cat $APP_DIR/QUICK_START.md"