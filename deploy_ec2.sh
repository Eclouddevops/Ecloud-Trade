#!/bin/bash
# ============================================
# Ecloud-Trade EC2 Deployment Script
# Run this ON the EC2 instance after SSH
# ============================================

echo "======================================"
echo "  Ecloud-Trade EC2 Deployment"
echo "======================================"

# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+ and pip
sudo apt install -y python3 python3-pip python3-venv nginx git

# Create app directory
sudo mkdir -p /opt/ecloud-trade
sudo chown ubuntu:ubuntu /opt/ecloud-trade
cd /opt/ecloud-trade

# Copy your code here (see instructions below)
# Or clone from git if you have a repo

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Create systemd service
sudo tee /etc/systemd/system/ecloud-trade.service > /dev/null <<EOF
[Unit]
Description=Ecloud-Trade Flask App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/ecloud-trade
ExecStart=/opt/ecloud-trade/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 app:app
Restart=always
RestartSec=5
Environment=FLASK_DEBUG=False

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
sudo tee /etc/nginx/sites-available/ecloud-trade > /dev/null <<EOF
server {
    listen 80;
    server_name ecloud-trade.timespro.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/ecloud-trade /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Start the app
sudo systemctl daemon-reload
sudo systemctl enable ecloud-trade
sudo systemctl start ecloud-trade

echo ""
echo "======================================"
echo "  DEPLOYMENT COMPLETE!"
echo "======================================"
echo "  App running at: http://$(curl -s ifconfig.me)"
echo "  Status: sudo systemctl status ecloud-trade"
echo "  Logs:   sudo journalctl -u ecloud-trade -f"
echo ""
echo "  Next: Point Cloudflare DNS A record"
echo "  ecloud-trade → $(curl -s ifconfig.me)"
echo "======================================"
