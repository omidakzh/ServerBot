# .env.example - نمونه فایل متغیرهای محیطی
# کپی کنید به .env و مقادیر را تنظیم کنید

# Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_FROM_BOTFATHER
BOT_USERNAME=YourBotUsername

# Virtualizer API Configuration
VIRTUALIZER_API_URL=http://your-virtualizer-server.com/api
VIRTUALIZER_API_KEY=your_api_key_here
VIRTUALIZER_USERNAME=admin
VIRTUALIZER_PASSWORD=your_password

# Database Configuration
DATABASE_PATH=./data/server_bot.db
DATABASE_BACKUP_PATH=./backups/

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321,555666777
SUPER_ADMIN_ID=123456789

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG_MODE=False
LOG_LEVEL=INFO

# VM Default Settings
MAX_VMS_PER_USER=5
DEFAULT_CPU_CORES=1
DEFAULT_RAM_MB=1024
DEFAULT_DISK_GB=10
DEFAULT_BANDWIDTH_MBPS=1000

# Security Settings
SECRET_KEY=your_secret_key_here
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=3
RATE_LIMIT_PER_MINUTE=30

# Backup Settings
AUTO_BACKUP_ENABLED=True
BACKUP_INTERVAL_HOURS=24
BACKUP_RETENTION_DAYS=30
BACKUP_COMPRESSION=True

# Notification Settings
NOTIFICATION_ENABLED=True
ALERT_CPU_THRESHOLD=80
ALERT_RAM_THRESHOLD=85
ALERT_DISK_THRESHOLD=90

# Monitoring
METRICS_ENABLED=True
HEALTH_CHECK_INTERVAL=60
PROMETHEUS_PORT=9090

# Redis Configuration (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

---

# config.yaml - پیکربندی پیشرفته
bot:
  token: "${BOT_TOKEN}"
  username: "${BOT_USERNAME}"
  webhook:
    enabled: false
    url: ""
    port: 8443
  
api:
  virtualizer:
    url: "${VIRTUALIZER_API_URL}"
    key: "${VIRTUALIZER_API_KEY}"
    timeout: 30
    retries: 3
    
database:
  type: "sqlite"
  path: "${DATABASE_PATH}"
  backup_path: "${DATABASE_BACKUP_PATH}"
  pool_size: 10
  
security:
  secret_key: "${SECRET_KEY}"
  session_timeout: 3600
  max_login_attempts: 3
  rate_limit:
    enabled: true
    requests_per_minute: 30
    
users:
  max_vms_per_user: 5
  default_resources:
    cpu: 1
    ram: 1024
    disk: 10240
    bandwidth: 1000
  
vm_templates:
  - name: "Ubuntu 22.04 LTS"
    os: "ubuntu"
    version: "22.04"
    min_ram: 512
    min_disk: 5120
    
  - name: "CentOS 8"
    os: "centos"
    version: "8"
    min_ram: 1024
    min_disk: 8192
    
  - name: "Windows Server 2019"
    os: "windows"
    version: "2019"
    min_ram: 2048
    min_disk: 20480

monitoring:
  enabled: true
  metrics:
    cpu_threshold: 80
    ram_threshold: 85
    disk_threshold: 90
  
  alerts:
    email:
      enabled: false
      smtp_server: ""
      smtp_port: 587
      username: ""
      password: ""
    
    telegram:
      enabled: true
      alert_chat_id: ""
      
backup:
  auto_backup: true
  interval_hours: 24
  retention_days: 30
  compression: true
  storage:
    local_path: "./backups/"
    remote_enabled: false
    remote_type: "s3"  # s3, ftp, sftp
    remote_config:
      bucket: ""
      access_key: ""
      secret_key: ""

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "./logs/bot.log"
  max_size: "10MB"
  backup_count: 5
  
features:
  vm_management: true
  backup_restore: true
  user_management: true
  monitoring: true
  auto_scaling: false
  load_balancing: false

---

# install.sh - اسکریپت نصب خودکار
#!/bin/bash

echo "🚀 نصب ربات مدیریت سرور تلگرام"
echo "=================================="

# بررسی Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 یافت نشد. لطفاً ابتدا Python 3 را نصب کنید."
    exit 1
fi

# بررسی pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 یافت نشد. در حال نصب..."
    sudo apt-get update
    sudo apt-get install python3-pip -y
fi

# ایجاد محیط مجازی
echo "📦 ایجاد محیط مجازی..."
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
echo "📋 نصب وابستگی‌ها..."
pip install -r requirements.txt

# ایجاد دایرکتوری‌های مورد نیاز
echo "📁 ایجاد دایرکتوری‌ها..."
mkdir -p data
mkdir -p logs
mkdir -p backups
mkdir -p monitoring

# کپی فایل پیکربندی
if [ ! -f .env ]; then
    echo "⚙️ ایجاد فایل پیکربندی..."
    cp .env.example .env
    echo "✏️ لطفاً فایل .env را ویرایش کنید و مقادیر مناسب را وارد کنید."
fi

# تنظیم مجوزها
echo "🔐 تنظیم مجوزها..."
chmod +x server_bot.py
chmod +x install.sh

# ایجاد سرویس systemd
echo "🔧 ایجاد سرویس سیستم..."
sudo tee /etc/systemd/system/telegram-bot.service > /dev/null <<EOF
[Unit]
Description=Telegram Server Management Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PWD
Environment=PATH=$PWD/venv/bin
ExecStart=$PWD/venv/bin/python $PWD/server_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable telegram-bot.service

echo "✅ نصب کامل شد!"
echo ""
echo "📋 مراحل بعدی:"
echo "1. فایل .env را ویرایش کنید"
echo "2. توکن ربات و API Key را وارد کنید"
echo "3. سرویس را اجرا کنید: sudo systemctl start telegram-bot"
echo "4. وضعیت سرویس را بررسی کنید: sudo systemctl status telegram-bot"

---

# systemctl_commands.sh - دستورات مدیریت سرویس
#!/bin/bash

# دستورات مدیریت سرویس ربات

case "$1" in
    start)
        echo "🚀 شروع سرویس ربات..."
        sudo systemctl start telegram-bot
        ;;
    stop)
        echo "⏹️ توقف سرویس ربات..."
        sudo systemctl stop telegram-bot
        ;;
    restart)
        echo "🔄 راه‌اندازی مجدد سرویس..."
        sudo systemctl restart telegram-bot
        ;;
    status)
        echo "📊 وضعیت سرویس:"
        sudo systemctl status telegram-bot
        ;;
    logs)
        echo "📝 لاگ‌های سرویس:"
        sudo journalctl -u telegram-bot -f
        ;;
    enable)
        echo "✅ فعال‌سازی خودکار سرویس..."
        sudo systemctl enable telegram-bot
        ;;
    disable)
        echo "❌ غیرفعال‌سازی خودکار سرویس..."
        sudo systemctl disable telegram-bot
        ;;
    *)
        echo "استفاده: $0 {start|stop|restart|status|logs|enable|disable}"
        echo ""
        echo "دستورات موجود:"
        echo "  start   - شروع سرویس"
        echo "  stop    - توقف سرویس"
        echo "  restart - راه‌اندازی مجدد"
        echo "  status  - نمایش وضعیت"
        echo "  logs    - نمایش لاگ‌ها"
        echo "  enable  - فعال‌سازی خودکار"
        echo "  disable - غیرفعال‌سازی خودکار"
        exit 1
        ;;
esac