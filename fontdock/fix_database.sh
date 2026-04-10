#!/bin/bash

# Quick fix for database creation issue
# Run this on your server if installation failed at admin user creation

echo "🔧 Fixing FontDock database..."

INSTALL_DIR="/opt/fontdock"
SERVICE_USER="fontdock"

# Ensure we're in the right directory
cd $INSTALL_DIR

# Make sure fontdock user owns everything
echo "Setting permissions..."
chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# Create admin user
echo "Creating admin user..."
sudo -u $SERVICE_USER $INSTALL_DIR/venv/bin/python $INSTALL_DIR/scripts/create_admin.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database and admin user created successfully!"
    echo ""
    echo "Starting FontDock service..."
    systemctl start fontdock
    systemctl status fontdock --no-pager
    echo ""
    echo "Server should now be running at:"
    echo "  http://$(hostname -I | awk '{print $1}')"
else
    echo ""
    echo "❌ Failed to create admin user"
    echo "Check the error above for details"
fi
