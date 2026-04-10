# FontDock Server - Quick Start Guide

## Deploy to Linux Server

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/colinrparsons/FontDock/main/fontdock/install.sh | sudo bash
```

Or manual:

```bash
git clone https://github.com/colinrparsons/FontDock.git
cd FontDock/fontdock
sudo chmod +x install.sh
sudo ./install.sh
```

### What Gets Installed

- Python 3 + dependencies
- Nginx reverse proxy
- Systemd service (auto-start on boot)
- FontDock server at `/opt/fontdock`
- Admin user created during install

### Access Your Server

After installation:
- **Web UI:** `http://YOUR_SERVER_IP`
- **API:** `http://YOUR_SERVER_IP/api`

### Default Port

- Server runs on port **8000** internally
- Nginx proxies port **80** → **8000**
- For HTTPS, use Let's Encrypt (see DEPLOYMENT.md)

## Test Locally First

Before deploying to a server, test on your Mac:

```bash
cd fontdock
export SERVER_HOST=0.0.0.0
export SERVER_PORT=8000
python3 run.py
```

Access at: `http://YOUR_LOCAL_IP:8000`

Find your local IP:
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

## Connect macOS Client to Remote Server

1. Open FontDock client
2. Settings → Server URL
3. Enter: `http://YOUR_SERVER_IP` or `https://your-domain.com`
4. Save and login

## Useful Commands

```bash
# Check server status
sudo systemctl status fontdock

# View logs
sudo journalctl -u fontdock -f

# Restart server
sudo systemctl restart fontdock

# Stop server
sudo systemctl stop fontdock
```

## Firewall

Make sure ports are open:
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

## Troubleshooting

**Can't connect from client:**
1. Check server IP: `hostname -I`
2. Test locally: `curl http://localhost:8000`
3. Check firewall: `sudo ufw status`
4. Check service: `sudo systemctl status fontdock`

**Server won't start:**
```bash
sudo journalctl -u fontdock -n 50
```

## Full Documentation

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete installation and configuration guide.
