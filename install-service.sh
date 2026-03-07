#!/bin/bash
# APEX Fleet Systemd Service Installer

set -e

echo "⚡ Installing APEX Fleet Systemd Service..."

# Create log directory
sudo mkdir -p /var/log/apex
sudo chown teacherchris37:teacherchris37 /var/log/apex

# Copy service file
sudo cp apex-service.service /etc/systemd/system/apex-fleet.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable apex-fleet.service

echo "✅ APEX Fleet service installed!"
echo ""
echo "Commands:"
echo "  sudo systemctl start apex-fleet    # Start the fleet"
echo "  sudo systemctl stop apex-fleet     # Stop the fleet"
echo "  sudo systemctl status apex-fleet   # Check status"
echo "  sudo systemctl restart apex-fleet  # Restart"
echo "  sudo journalctl -u apex-fleet -f   # View logs"
echo ""
echo "Dashboard: http://localhost:7777"
echo "Logs: /var/log/apex/"
