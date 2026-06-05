#!/bin/bash
# EC2 User Data - Auto-setup on launch
set -e

export DEBIAN_FRONTEND=noninteractive

# Update system
apt-get update -y
apt-get upgrade -y

# Install dependencies
apt-get install -y python3 python3-pip python3-venv nginx git

# Create app user and directory
mkdir -p /opt/ecloud-trade
chown ubuntu:ubuntu /opt/ecloud-trade

# Install Python packages globally for initial setup
pip3 install gunicorn

# Configure Nginx
cat > /etc/nginx/sites-available/ecloud-trade <<'NGINX'
server {
    listen 80;
    server_name ecloud-trade.timespro.com _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120;
        proxy_connect_timeout 120;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/ecloud-trade /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx
systemctl enable nginx

# Create systemd service for the app
cat > /etc/systemd/system/ecloud-trade.service <<'SERVICE'
[Unit]
Description=Ecloud-Trade Flask Application
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/ecloud-trade
Environment=FLASK_DEBUG=False
Environment=FLASK_PORT=5000
ExecStart=/opt/ecloud-trade/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 --timeout 120 --access-logfile /opt/ecloud-trade/access.log --error-logfile /opt/ecloud-trade/error.log app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable ecloud-trade

echo "EC2 setup complete. Waiting for code deployment via GitHub Actions."
