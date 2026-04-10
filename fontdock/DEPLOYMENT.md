# FontDock Server Deployment Guide

This guide covers deploying FontDock server on a Linux server (Ubuntu/Debian).

## Quick Install

### 1. Prepare Your Server

Requirements:
- Ubuntu 20.04+ or Debian 11+
- 2GB+ RAM
- 10GB+ disk space
- Root/sudo access

### 2. Clone the Repository

```bash
cd /tmp
git clone https://github.com/colinrparsons/FontDock.git
cd FontDock/fontdock
```

### 3. Run the Installation Script

```bash
sudo chmod +x install.sh
sudo ./install.sh
```

The script will:
- Install Python 3, Nginx, and dependencies
- Create a `fontdock` system user
- Set up a Python virtual environment
- Install FontDock in `/opt/fontdock`
- Create systemd service
- Configure Nginx reverse proxy
- Generate a secure secret key
- Create an admin user

### 4. Access Your Server

After installation, access FontDock at:
- `http://YOUR_SERVER_IP`
- `http://YOUR_DOMAIN` (if configured)

Default admin credentials will be shown during installation.

## Manual Installation

If you prefer to install manually:

### 1. Install Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx
```

### 2. Create User and Directory

```bash
sudo useradd -r -m -d /opt/fontdock -s /bin/bash fontdock
sudo mkdir -p /opt/fontdock
cd /opt/fontdock
```

### 3. Clone and Setup

```bash
sudo git clone https://github.com/colinrparsons/FontDock.git .
sudo chown -R fontdock:fontdock /opt/fontdock
```

### 4. Create Virtual Environment

```bash
sudo -u fontdock python3 -m venv venv
sudo -u fontdock venv/bin/pip install -r requirements.txt
```

### 5. Configure Environment

```bash
sudo cp .env.example .env
sudo nano .env  # Edit configuration
```

Generate a secret key:
```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
```

### 6. Create Directories

```bash
sudo mkdir -p /opt/fontdock/storage/fonts
sudo mkdir -p /opt/fontdock/logs
sudo chown -R fontdock:fontdock /opt/fontdock
```

### 7. Create Admin User

```bash
sudo -u fontdock venv/bin/python scripts/create_admin.py
```

### 8. Setup Systemd Service

Create `/etc/systemd/system/fontdock.service`:

```ini
[Unit]
Description=FontDock Font Management Server
After=network.target

[Service]
Type=simple
User=fontdock
WorkingDirectory=/opt/fontdock
Environment="PATH=/opt/fontdock/venv/bin"
ExecStart=/opt/fontdock/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fontdock
sudo systemctl start fontdock
```

### 9. Configure Nginx

Create `/etc/nginx/sites-available/fontdock`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/fontdock /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Recommended)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot will automatically:
- Obtain SSL certificate
- Configure Nginx for HTTPS
- Set up auto-renewal

## Configuration

### Environment Variables

Edit `/opt/fontdock/.env`:

```bash
# Server binding
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database (SQLite or PostgreSQL)
DATABASE_URL=sqlite:///./fontdock.db

# Security
SECRET_KEY=your-random-secret-key

# Storage
STORAGE_PATH=/opt/fontdock/storage/fonts

# Logging
LOG_LEVEL=INFO
```

### PostgreSQL Setup (Optional)

For production, PostgreSQL is recommended:

```bash
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb fontdock
sudo -u postgres createuser fontdock -P
```

Update `.env`:
```
DATABASE_URL=postgresql://fontdock:password@localhost/fontdock
```

Install PostgreSQL driver:
```bash
sudo -u fontdock /opt/fontdock/venv/bin/pip install psycopg2-binary
```

## Management Commands

### Service Control

```bash
# Check status
sudo systemctl status fontdock

# Start/Stop/Restart
sudo systemctl start fontdock
sudo systemctl stop fontdock
sudo systemctl restart fontdock

# View logs
sudo journalctl -u fontdock -f
```

### Application Logs

```bash
# Real-time logs
tail -f /opt/fontdock/logs/fontdock.log

# View all logs
less /opt/fontdock/logs/fontdock.log
```

### Database Backup

```bash
# SQLite
sudo -u fontdock cp /opt/fontdock/fontdock.db /opt/fontdock/backups/fontdock-$(date +%Y%m%d).db

# PostgreSQL
sudo -u postgres pg_dump fontdock > fontdock-backup-$(date +%Y%m%d).sql
```

## Firewall Configuration

### UFW (Ubuntu Firewall)

```bash
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
```

## Client Configuration

Update macOS client settings to point to your server:

1. Open FontDock client
2. Go to Settings
3. Set Server URL to: `http://YOUR_SERVER_IP` or `https://your-domain.com`
4. Save and restart

## Troubleshooting

### Server won't start

```bash
# Check service status
sudo systemctl status fontdock

# Check logs
sudo journalctl -u fontdock -n 50

# Check Python errors
sudo -u fontdock /opt/fontdock/venv/bin/python /opt/fontdock/run.py
```

### Can't connect from client

1. Check firewall allows port 80/443
2. Verify Nginx is running: `sudo systemctl status nginx`
3. Test server directly: `curl http://localhost:8000/api/health`
4. Check server IP: `hostname -I`

### Database errors

```bash
# Check database file permissions
ls -la /opt/fontdock/fontdock.db

# Reset database (WARNING: deletes all data)
sudo -u fontdock rm /opt/fontdock/fontdock.db
sudo -u fontdock /opt/fontdock/venv/bin/python /opt/fontdock/run.py
```

### Upload errors

```bash
# Check storage directory permissions
ls -la /opt/fontdock/storage/fonts

# Fix permissions
sudo chown -R fontdock:fontdock /opt/fontdock/storage
```

## Updating FontDock

```bash
cd /opt/fontdock
sudo -u fontdock git pull
sudo -u fontdock venv/bin/pip install -r requirements.txt
sudo systemctl restart fontdock
```

## Security Best Practices

1. **Use HTTPS** - Always use SSL/TLS in production
2. **Strong passwords** - Use complex admin passwords
3. **Firewall** - Only open necessary ports
4. **Regular updates** - Keep system and FontDock updated
5. **Backups** - Regular database and font file backups
6. **Private network** - Consider using VPN (Tailscale) for remote access

## Performance Tuning

### For High Traffic

Edit `/etc/systemd/system/fontdock.service`:

```ini
[Service]
Environment="WORKERS=4"
ExecStart=/opt/fontdock/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Nginx Caching

Add to Nginx config:

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=fontdock_cache:10m max_size=1g;

location / {
    proxy_cache fontdock_cache;
    proxy_cache_valid 200 1h;
    # ... rest of proxy config
}
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/colinrparsons/FontDock/issues
- Documentation: https://github.com/colinrparsons/FontDock

## License

FontDock is licensed under the MIT License.
