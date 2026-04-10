# FontDock on Proxmox LXC

FontDock works perfectly in Proxmox LXC containers! This is actually the **recommended** deployment method for self-hosted setups.

## Why LXC is Perfect for FontDock

✅ **Lightweight** - Much less overhead than VMs
✅ **Fast** - Near-native performance
✅ **Easy backups** - Proxmox built-in backup/restore
✅ **Resource efficient** - Minimal RAM/CPU usage
✅ **Easy snapshots** - Test updates safely

## Quick Setup

### 1. Create LXC Container

In Proxmox web UI:

**Container Settings:**
- **Template:** Ubuntu 22.04 or Debian 12
- **Disk:** 10GB minimum (more if storing many fonts)
- **CPU:** 1-2 cores
- **RAM:** 1GB minimum, 2GB recommended
- **Network:** Bridge to your network
- **Start on boot:** Yes (recommended)

**Important Options:**
- ✅ **Unprivileged container** (recommended for security)
- ✅ **Nesting:** Enable if you plan to use Docker later
- ✅ **DHCP or Static IP** (static recommended for stable access)

### 2. Start Container and Login

```bash
# From Proxmox host
pct start 100  # Replace 100 with your container ID
pct enter 100
```

Or use the web console.

### 3. Update System

```bash
apt update && apt upgrade -y
```

### 4. Install FontDock

```bash
# Install git first
apt install -y git

# Clone and install
cd /tmp
git clone https://github.com/colinrparsons/FontDock.git
cd FontDock/fontdock
chmod +x install.sh
./install.sh
```

That's it! FontDock is now running.

### 5. Access Your Server

Find your container's IP:
```bash
hostname -I
```

Access FontDock at: `http://CONTAINER_IP`

## Recommended LXC Configuration

### Container Config File

Edit on Proxmox host: `/etc/pve/lxc/100.conf` (replace 100 with your CT ID)

```conf
# Basic settings
arch: amd64
cores: 2
memory: 2048
swap: 512
hostname: fontdock
net0: name=eth0,bridge=vmbr0,firewall=1,hwaddr=XX:XX:XX:XX:XX:XX,ip=dhcp,type=veth
ostype: ubuntu
rootfs: local-lxc:vm-100-disk-0,size=20G

# Features
features: nesting=1

# Start on boot
onboot: 1
```

### Resource Allocation

**Minimum:**
- CPU: 1 core
- RAM: 1GB
- Disk: 10GB

**Recommended:**
- CPU: 2 cores
- RAM: 2GB
- Disk: 20GB+ (depends on font library size)

**For Large Teams (100+ users):**
- CPU: 4 cores
- RAM: 4GB
- Disk: 50GB+

## Networking Options

### Option 1: Bridge Mode (Recommended)

Container gets its own IP on your network.

**Pros:**
- Easy to access from any device
- Simple firewall rules
- Works with Let's Encrypt

**Setup:**
- Use `vmbr0` bridge
- Assign static IP or DHCP reservation

### Option 2: NAT with Port Forwarding

Container uses private IP, Proxmox host forwards ports.

**Proxmox host:**
```bash
# Forward port 80 to container
iptables -t nat -A PREROUTING -i vmbr0 -p tcp --dport 80 -j DNAT --to CONTAINER_IP:80
iptables -t nat -A POSTROUTING -s CONTAINER_IP -o vmbr0 -j MASQUERADE
```

Make persistent with `iptables-persistent`.

## Storage Considerations

### Font Storage Location

FontDock stores fonts in: `/opt/fontdock/storage/fonts`

### Bind Mount (Optional)

To store fonts on Proxmox host storage:

**On Proxmox host:**
```bash
# Create directory on host
mkdir -p /mnt/fontdock-storage

# Add to container config
pct set 100 -mp0 /mnt/fontdock-storage,mp=/opt/fontdock/storage
```

**Benefits:**
- Easier backups
- Shared storage across containers
- Better performance on some setups

## Backups

### Proxmox Built-in Backup

**Web UI:** Datacenter → Backup

**CLI:**
```bash
# Backup container
vzdump 100 --mode snapshot --compress zstd

# Restore
pct restore 100 /var/lib/vz/dump/vzdump-lxc-100-*.tar.zst
```

### Manual Font Backup

Inside container:
```bash
# Backup fonts and database
cd /opt/fontdock
tar -czf fontdock-backup-$(date +%Y%m%d).tar.gz storage/ fontdock.db

# Copy to Proxmox host
scp fontdock-backup-*.tar.gz root@proxmox-host:/var/backups/
```

## Firewall Configuration

### Proxmox Firewall (Recommended)

**Datacenter → Firewall → Add:**
- Direction: IN
- Action: ACCEPT
- Protocol: TCP
- Dest. port: 80,443
- Comment: FontDock HTTP/HTTPS

### Container Firewall (UFW)

Inside container:
```bash
apt install -y ufw
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp  # SSH
ufw enable
```

## SSL/HTTPS Setup

### Let's Encrypt in LXC

Works perfectly! Just ensure:
1. Container has public IP or port forwarding
2. Domain points to container IP
3. Port 80 is accessible from internet

```bash
# Inside container
certbot --nginx -d fontdock.yourdomain.com
```

### Reverse Proxy on Proxmox Host

Alternative: Use Nginx on Proxmox host as reverse proxy.

## Performance Tips

### 1. Use ZFS Storage (if available)

ZFS provides:
- Snapshots
- Compression
- Deduplication

### 2. Allocate Enough RAM

FontDock + Nginx + Python needs ~500MB minimum.
Add buffer for font processing: 2GB recommended.

### 3. CPU Cores

2 cores handles ~50 concurrent users comfortably.

### 4. Disk I/O

SSD storage recommended for database and font cache.

## Monitoring

### Inside Container

```bash
# Check resource usage
htop

# Check disk usage
df -h

# Check FontDock status
systemctl status fontdock
journalctl -u fontdock -f
```

### From Proxmox Host

```bash
# Container resource usage
pct status 100
pct exec 100 -- systemctl status fontdock
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
pct start 100
journalctl -xe
```

### Can't Access from Network

1. Check container IP: `pct exec 100 -- hostname -I`
2. Check firewall: `pct exec 100 -- ufw status`
3. Ping container from another machine
4. Check Proxmox firewall rules

### FontDock Service Issues

```bash
# Enter container
pct enter 100

# Check service
systemctl status fontdock
journalctl -u fontdock -n 50
```

### Database Locked Errors

SQLite can have issues with NFS/CIFS storage.

**Solution:** Use local storage for database, or switch to PostgreSQL.

## Migration from VM

If you're currently running in a VM:

1. Backup fonts and database from VM
2. Create new LXC container
3. Install FontDock
4. Restore backup
5. Update client settings to new IP

## Updating FontDock

```bash
# Enter container
pct enter 100

# Update
cd /opt/fontdock
sudo -u fontdock git pull
sudo -u fontdock venv/bin/pip install -r requirements.txt
systemctl restart fontdock
```

## Example Production Setup

**Container Specs:**
- Ubuntu 22.04 LXC
- 2 CPU cores
- 2GB RAM
- 30GB disk (ZFS)
- Static IP: 192.168.1.100
- Proxmox firewall enabled
- Daily automated backups

**Access:**
- Internal: `http://192.168.1.100`
- External: `https://fonts.company.com` (via reverse proxy)

**Backup Strategy:**
- Proxmox snapshot: Daily
- Font/DB backup: Weekly
- Offsite backup: Monthly

## Best Practices

1. ✅ **Use unprivileged containers** for security
2. ✅ **Enable start on boot** for reliability
3. ✅ **Set static IP** for consistent access
4. ✅ **Regular backups** via Proxmox
5. ✅ **Monitor disk space** - fonts add up!
6. ✅ **Use SSL/HTTPS** for production
7. ✅ **Keep system updated** - security patches

## Advantages Over VM

| Feature | LXC | VM |
|---------|-----|-----|
| Boot time | 2-5 seconds | 30-60 seconds |
| RAM overhead | ~50MB | ~500MB+ |
| Disk overhead | Minimal | 2-5GB+ |
| Performance | Near-native | 5-10% slower |
| Snapshots | Instant | Slower |
| Backups | Fast | Slower |

## Summary

**FontDock + Proxmox LXC = Perfect Match! 🎯**

- Fast deployment (< 5 minutes)
- Minimal resources
- Easy management
- Built-in backups
- Production-ready

Questions? Check the main [DEPLOYMENT.md](DEPLOYMENT.md) or open an issue on GitHub.
