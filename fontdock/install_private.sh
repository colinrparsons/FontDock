#!/bin/bash

# FontDock Server Installation Script (Private Repository Version)
# For Ubuntu/Debian-based Linux servers

set -e

echo "======================================"
echo "FontDock Server Installation"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Prompt for GitHub credentials
echo "This repository is private. Please provide authentication:"
echo ""
read -p "GitHub Username: " GITHUB_USER
read -sp "GitHub Personal Access Token: " GITHUB_TOKEN
echo ""
echo ""

# Get the actual user (not root)
ACTUAL_USER=${SUDO_USER:-$USER}
INSTALL_DIR="/opt/fontdock"
SERVICE_USER="fontdock"

echo "📦 Installing system dependencies..."
apt-get update
apt-get install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx

echo ""
echo "👤 Creating fontdock user..."
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -m -d /opt/fontdock -s /bin/bash $SERVICE_USER
    echo "✓ User created"
else
    echo "✓ User already exists"
fi

echo ""
echo "📁 Cloning repository..."
mkdir -p $INSTALL_DIR
cd /tmp
rm -rf FontDock
git clone https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/colinrparsons/FontDock.git
cd FontDock/fontdock
cp -r . $INSTALL_DIR/
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

echo ""
echo "🐍 Creating Python virtual environment..."
sudo -u $SERVICE_USER python3 -m venv $INSTALL_DIR/venv

echo ""
echo "📚 Installing Python dependencies..."
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install --upgrade pip
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/pip install -r $INSTALL_DIR/requirements.txt

echo ""
echo "📂 Creating required directories..."
mkdir -p $INSTALL_DIR/storage/fonts
mkdir -p $INSTALL_DIR/logs
mkdir -p $INSTALL_DIR/uploads
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/storage
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/logs
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/uploads

echo ""
echo "⚙️  Creating configuration file..."
cat > $INSTALL_DIR/.env << 'EOF'
# FontDock Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DATABASE_URL=sqlite:///./fontdock.db
SECRET_KEY=CHANGE_THIS_TO_A_RANDOM_SECRET_KEY
STORAGE_PATH=/opt/fontdock/storage/fonts
LOG_LEVEL=INFO
EOF

# Generate a random secret key
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
sed -i "s/CHANGE_THIS_TO_A_RANDOM_SECRET_KEY/$SECRET_KEY/" $INSTALL_DIR/.env

chown $SERVICE_USER:$SERVICE_USER $INSTALL_DIR/.env
chmod 600 $INSTALL_DIR/.env

echo ""
echo "🔧 Creating systemd service..."
cat > /etc/systemd/system/fontdock.service << EOF
[Unit]
Description=FontDock Font Management Server
After=network.target

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo ""
echo "🌐 Configuring Nginx reverse proxy..."
cat > /etc/nginx/sites-available/fontdock << 'EOF'
server {
    listen 80;
    server_name _;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed in future)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Enable the site
ln -sf /etc/nginx/sites-available/fontdock /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
nginx -t

echo ""
echo "🔄 Reloading services..."
systemctl daemon-reload
systemctl enable fontdock
systemctl restart nginx

echo ""
echo "👤 Creating admin user..."
cd $INSTALL_DIR
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python $INSTALL_DIR/scripts/create_admin.py

echo ""
echo "🚀 Starting FontDock server..."
systemctl start fontdock

# Clean up credentials from memory
unset GITHUB_USER
unset GITHUB_TOKEN

echo ""
echo "======================================"
echo "✅ Installation Complete!"
echo "======================================"
echo ""
echo "Server Status:"
systemctl status fontdock --no-pager -l
echo ""
echo "📍 Server is running at:"
echo "   http://$(hostname -I | awk '{print $1}')"
echo "   http://localhost"
echo ""
echo "📝 Useful commands:"
echo "   sudo systemctl status fontdock    # Check status"
echo "   sudo systemctl restart fontdock   # Restart server"
echo "   sudo systemctl stop fontdock      # Stop server"
echo "   sudo journalctl -u fontdock -f    # View logs"
echo ""
echo "📂 Installation directory: $INSTALL_DIR"
echo "📄 Configuration file: $INSTALL_DIR/.env"
echo "📊 Logs: $INSTALL_DIR/logs/"
echo ""
echo "🔐 To enable HTTPS with Let's Encrypt:"
echo "   1. Point your domain to this server's IP"
echo "   2. Update server_name in /etc/nginx/sites-available/fontdock"
echo "   3. Run: sudo certbot --nginx -d your-domain.com"
echo ""
