# 🤖 ربات تلگرام مدیریت سرور اختصاصی

ربات جامع برای مدیریت سرور اختصاصی با قابلیت اتصال به API ویرچوالایزور و امکانات پیشرفته مدیریت ماشین‌های مجازی.

## ✨ امکانات

### 🖥️ مدیریت ماشین‌های مجازی
- ✅ ایجاد، حذف و تنظیم VM ها
- ✅ کنترل وضعیت (روشن/خاموش/ریستارت)
- ✅ مشاهده آمار و مصرف منابع
- ✅ تنظیم منابع (CPU, RAM, Disk)
- ✅ مدیریت IP و تنظیمات شبکه

### 💾 مدیریت بکاپ
- ✅ ایجاد بکاپ خودکار و دستی
- ✅ بازیابی از بکاپ
- ✅ مدیریت فایل‌های بکاپ
- ✅ برنامه‌ریزی بکاپ

### 👥 مدیریت کاربران
- ✅ سیستم مجوز چندسطحه
- ✅ محدودیت منابع برای هر کاربر
- ✅ ثبت فعالیت و لاگ
- ✅ پنل ادمین پیشرفته

### 📊 نظارت و گزارش‌گیری
- ✅ آمار لحظه‌ای سرور
- ✅ نظارت بر مصرف منابع
- ✅ هشدارهای هوشمند
- ✅ گزارش‌های دوره‌ای

### 🔧 ویژگی‌های پیشرفته
- ✅ رابط کاربری زیبا و کاربردی
- ✅ پشتیبانی از Docker
- ✅ سیستم امنیتی قوی
- ✅ قابلیت سفارشی‌سازی بالا

## 📋 پیش‌نیازها

### نرم‌افزارهای مورد نیاز
- Python 3.8+ 
- SQLite3
- ویرچوالایزور (با API فعال)
- Git

### سخت‌افزار توصیه شده
- RAM: حداقل 2GB
- CPU: 2 هسته
- Storage: 20GB فضای خالی

## 🚀 نصب و راه‌اندازی

### روش 1: نصب مستقیم

```bash
# کلون کردن پروژه
git clone https://github.com/yourusername/telegram-server-bot.git
cd telegram-server-bot

# اجرای اسکریپت نصب خودکار
chmod +x install.sh
./install.sh
```

### روش 2: نصب دستی

```bash
# ایجاد محیط مجازی
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
pip install -r requirements.txt

# ایجاد دایرکتوری‌ها
mkdir -p data logs backups

# کپی فایل پیکربندی
cp .env.example .env
```

### روش 3: استفاده از Docker

```bash
# کپی فایل‌های پیکربندی
cp .env.example .env

# ویرایش تنظیمات
nano .env

# اجرا با Docker Compose
docker-compose up -d
```

## ⚙️ پیکربندی

### 1. دریافت توکن ربات

1. به [@BotFather](https://t.me/BotFather) در تلگرام مراجعه کنید
2. دستور `/newbot` را ارسال کنید
3. نام و username برای ربات انتخاب کنید
4. توکن دریافتی را در فایل `.env` قرار دهید

### 2. تنظیم API ویرچوالایزور

```bash
# در فایل .env
VIRTUALIZER_API_URL=http://your-server.com/api
VIRTUALIZER_API_KEY=your_api_key_here
```

### 3. تعیین ادمین‌ها

```bash
# در فایل .env
ADMIN_USER_IDS=123456789,987654321
```

برای دریافت User ID تلگرام خود:
1. به [@userinfobot](https://t.me/userinfobot) مراجعه کنید
2. دستور `/start` ارسال کنید

### 4. تنظیمات امنیتی

```bash
# تولید کلید امنیتی
SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env
```

## 🔧 اجرا

### اجرای مستقیم

```bash
# فعال‌سازی محیط مجازی
source venv/bin/activate

# اجرای ربات
python server_bot.py
```

### اجرا به عنوان سرویس

```bash
# شروع سرویس
sudo systemctl start telegram-bot

# فعال‌سازی خودکار
sudo systemctl enable telegram-bot

# بررسی وضعیت
sudo systemctl status telegram-bot
```

### مدیریت سرویس

```bash
# استفاده از اسکریپت مدیریت
./systemctl_commands.sh start    # شروع
./systemctl_commands.sh stop     # توقف
./systemctl_commands.sh restart  # راه‌اندازی مجدد
./systemctl_commands.sh status   # وضعیت
./systemctl_commands.sh logs     # مشاهده لاگ‌ها
```

## 📱 راهنمای استفاده

### برای کاربران عادی

1. **شروع کار**
   - دستور `/start` را ارسال کنید
   - از منوی اصلی گزینه‌های مورد نظر را انتخاب کنید

2. **مشاهده VM ها**
   - روی "💻 ماشین‌های من" کلیک کنید
   - لیست VM های شما نمایش داده می‌شود

3. **ایجاد VM جدید**
   - "➕ ایجاد VM جدید" را انتخاب کنید
   - سیستم‌عامل مورد نظر را انتخاب کنید
   - منابع مورد نیاز را تعیین کنید

4. **مدیریت VM**
   - روی نام VM کلیک کنید
   - از منوی مدیریت عملیات مورد نظر را انتخاب کنید

### برای ادمین‌ها

1. **پنل ادمین**
   - روی "👑 پنل ادمین" کلیک کنید
   - دسترسی به تمام امکانات مدیریتی

2. **مدیریت کاربران**
   - مشاهده لیست کاربران
   - تنظیم محدودیت‌ها
   - فعال/غیرفعال کردن کاربران

3. **نظارت بر سیستم**
   - آمار کلی سرور
   - مشاهده تمام VM ها
   - گزارش‌های عملکرد

## 🔒 امنیت

### تنظیمات امنیتی

- 🔐 احراز هویت چندسطحه
- 🚫 محدودیت نرخ درخواست
- 📝 ثبت کامل فعالیت‌ها
- 🔑 رمزنگاری داده‌های حساس

### بهترین شیوه‌ها

```bash
# تغییر مالکیت فایل‌ها
chown -R bot:bot /path/to/bot

# تنظیم مجوزهای فایل
chmod 600 .env
chmod 644 *.py
chmod 755 *.sh

# فایروال
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw enable
```

## 📊 نظارت

### لاگ‌ها

```bash
# مشاهده لاگ‌های ربات
tail -f logs/bot.log

# لاگ‌های سیستم
journalctl -u telegram-bot -f

# لاگ‌های Docker
docker-compose logs -f telegram-bot
```

### متریک‌ها

- CPU Usage
- Memory Usage  
- Disk Usage
- Network Traffic
- Active VMs
- User Activity

## 🛠️ عیب‌یابی

### مشکلات رایج

1. **ربات پاسخ نمی‌دهد**
   ```bash
   # بررسی وضعیت سرویس
   systemctl status telegram-bot
   
   # بررسی لاگ‌ها
   journalctl -u telegram-bot --lines=50
   ```

2. **خطای اتصال به API**
   ```bash
   # تست اتصال
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        http://your-server.com/api/status
   ```

3. **مشکل دیتابیس**
   ```bash
   # بررسی فایل دیتابیس
   sqlite3 data/server_bot.db ".tables"
   
   # بازیابی از بکاپ
   cp backups/latest_backup.db data/server_bot.db
   ```

### فایل‌های لاگ

- `logs/bot.log` - لاگ اصلی ربات
- `logs/api.log` - لاگ درخواست‌های API
- `logs/error.log` - لاگ خطاها

## 🔄 بروزرسانی

```bash
# دریافت آخرین تغییرات
git pull origin main

# بروزرسانی وابستگی‌ها
pip install -r requirements.txt --upgrade

# راه‌اندازی مجدد سرویس
systemctl restart telegram-bot
```

## 📚 API Reference

### API ویرچوالایزور

| Endpoint | Method | توضیح |
|----------|--------|--------|
| `/api/vms` | GET | لیست VM ها |
| `/api/vms` | POST | ایجاد VM |
| `/api/vms/{id}` | GET | اطلاعات VM |
| `/api/vms/{id}/start` | POST | روشن کردن |
| `/api/vms/{id}/stop` | POST | خاموش کردن |
| `/api/vms/{id}/backup` | POST | ایجاد بکاپ |

### ساختار پاسخ

```json
{
    "success": true,
    "data": {
        "vm_id": "vm-123",
        "name": "Ubuntu Server",
        "status": "running",
        "resources": {
            "cpu": 2,
            "ram": 2048,
            "disk": 20480
        }
    },
    "message": "عملیات با موفقیت انجام شد"
}
```

## 🤝 مشارکت

برای مشارکت در پروژه:

1. Fork کنید
2. Branch جدید ایجاد کنید
3. تغییرات را commit کنید
4. Pull Request ارسال کنید

### قوانین Commit

```bash
feat: اضافه کردن ویژگی جدید
fix: رفع باگ
docs: بروزرسانی مستندات
style: تغییرات فرمت کد
refactor: بازسازی کد
test: اضافه کردن تست
```

## 📄 مجوز

این پروژه تحت مجوز MIT منتشر شده است. برای جزئیات بیشتر فایل [LICENSE](LICENSE) را مطالعه کنید.

## 📞 پشتیبانی

- 📧 Email: support@yourserver.com
- 💬 Telegram: [@YourSupportBot](https://t.me/YourSupportBot)
- 🌐 Website: [https://yourserver.com](https://yourserver.com)
- 📋 Issues: [GitHub Issues](https://github.com/yourusername/telegram-server-bot/issues)

## 🎯 نقشه راه

### v2.0 (در دست توسعه)

- [ ] پشتیبانی از Kubernetes
- [ ] رابط وب ادمین
- [ ] API REST کامل
- [ ] پلاگین سیستم
- [ ] Multi-server support

### v2.1 (آینده)

- [ ] Mobile App
- [ ] AI-powered monitoring
- [ ] Auto-scaling
- [ ] Advanced networking

---

**💡 نکته:** برای دریافت آخرین بروزرسانی‌ها، ستاره (⭐) پروژه را فراموش نکنید!

## 📸 تصاویر

### منوی اصلی
![Main Menu](screenshots/main_menu.png)

### مدیریت VM
![VM Management](screenshots/vm_management.png)

### پنل ادمین
![Admin Panel](screenshots/admin_panel.png)

### آمار سرور
![Server Stats](screenshots/server_stats.png)