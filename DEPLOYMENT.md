# Deployment Guide — ecloud-trade.timespro.com

## Option 1: Cloudflare Tunnel (No public IP needed)

### One-Time Setup
```
setup_tunnel.bat
```

### Daily Usage
```
python app.py
```
App auto-connects to `https://ecloud-trade.timespro.com`

---

## Option 2: Nginx Reverse Proxy (Recommended for Production)

Your app runs on `192.168.0.122:5000`. You need a server with a **public IP** running Nginx.

### Architecture
```
Users (Internet)
      ↓
Cloudflare DNS (ecloud-trade.timespro.com → Public IP)
      ↓
Nginx Server (Public IP)
      ↓
Flask App (192.168.0.122:5000)
```

### Step 1: Install Nginx on the public server
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx -y

# CentOS/RHEL
sudo yum install nginx -y
```

### Step 2: Configure Nginx
Create file `/etc/nginx/sites-available/ecloud-trade`:

```nginx
server {
    listen 80;
    server_name ecloud-trade.timespro.com;

    location / {
        proxy_pass http://192.168.0.122:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 90;
    }

    # WebSocket support (for future live streaming)
    location /ws {
        proxy_pass http://192.168.0.122:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### Step 3: Enable the site
```bash
sudo ln -s /etc/nginx/sites-available/ecloud-trade /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 4: Cloudflare DNS Record
Go to Cloudflare Dashboard → timespro.com → DNS:

| Type | Name | Value | Proxy |
|------|------|-------|-------|
| A | ecloud-trade | Public-IP-of-Nginx-Server | Proxied (orange) |

### Step 5: Cloudflare SSL
Go to SSL/TLS → Set mode to **Full (Strict)**

### Step 6: Start your Flask app
On your local machine (192.168.0.122):
```bash
python app.py
```

### Verify
Open `https://ecloud-trade.timespro.com` in any browser.

---

## Important Notes

### If Nginx and Flask are on the SAME machine:
Change `proxy_pass` to:
```nginx
proxy_pass http://127.0.0.1:5000;
```

### If Flask is on a DIFFERENT machine (your case):
Make sure:
1. Port 5000 is accessible from the Nginx server
2. Both machines are on the same network OR connected via VPN
3. No firewall blocking port 5000

### Allow Flask to accept external connections:
Already configured — app.py runs with `host="0.0.0.0"`

### For production (not dev mode):
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Run as background service:
```bash
# Create systemd service
sudo nano /etc/systemd/system/ecloud-trade.service
```

```ini
[Unit]
Description=Ecloud-Trade Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/Ecloud-Trade
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable ecloud-trade
sudo systemctl start ecloud-trade
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| 502 Bad Gateway | Flask app not running on 192.168.0.122:5000 |
| 522 Connection Timed Out | Nginx can't reach Flask — check firewall |
| ERR_SSL_VERSION | Set Cloudflare SSL to "Full" not "Full Strict" |
| DNS not resolving | Wait 5 min for Cloudflare DNS propagation |
| Nginx permission denied | `sudo setsebool -P httpd_can_network_connect 1` |
