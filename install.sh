#!/bin/bash

# نصب خودکار ربات تلگرام مدیریت سرور اختصاصی
# Telegram Server Management Bot Auto Installer

set -e

# رنگ‌ها برای نمایش بهتر
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# تابع نمایش پیام‌ها
print_header() {
    echo -e "${BLUE}=================================="
    echo -e "🤖 نصب ربات مدیریت سرور تلگرام"
    echo -e "==================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ️ $1${NC}"
}

print_step() {
    echo -e "${PURPLE}🔧 $1${NC}"
}

# بررسی دسترسی root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        print_warning "این اسکریپت نباید با دسترسی root اجرا شود!"
        print_info "لطفاً با یک کاربر عادی اجرا کنید."
        exit 1
    fi
}

# بررسی سیستم‌عامل
check_os() {
    print_step "بررسی سیستم‌عامل..."
    
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt &> /dev/null; then
            OS="ubuntu"
            print_success "Ubuntu/Debian تشخیص داده شد"
        elif command -v yum &> /dev/null; then
            OS="centos"
            print_success "CentOS/RHEL تشخیص داده شد"
        else
            print_error "سیستم‌عامل پشتیبانی نشده"
            exit 1
        fi
    else
        print_error "این اسکریپت فقط روی Linux کار می‌کند"
        exit 1
    fi
}

# نصب Python
install_python() {
    print_step "بررسی و نصب Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        print_success "Python $PYTHON_VERSION یافت شد"
        
        # بررسی نسخه Python (حداقل 3.8)
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)"; then
            print_success "نسخه Python مناسب است"
        else
            print_error "Python 3.8 یا بالاتر مورد نیاز است"
            exit 1
        fi
    else
        print_info "Python یافت نشد. در حال نصب..."
        
        if [[ "$OS" == "ubuntu" ]]; then
            sudo apt update
            sudo apt install -y python3 python3-pip python3-venv
        elif [[ "$OS" == "centos" ]]; then
            sudo yum install -y python3 python3-pip
        fi
        
        if command -v python3 &> /dev/null; then
            print_success "Python با موفقیت نصب شد"
        else
            print_error "خطا در نصب Python"
            exit 1
        fi
    fi
}

# نصب pip
install_pip() {
    print_step "بررسی pip..."
    
    if command -v pip3 &> /dev/null; then
        print_success "pip یافت شد"
    else
        print_info "pip یافت نشد. در حال نصب..."
        
        if [[ "$OS" == "ubuntu" ]]; then
            sudo apt install -y python3-pip
        elif [[ "$OS" == "centos" ]]; then
            sudo yum install -y python3-pip
        fi
        
        if command -v pip3 &> /dev/null; then
            print_success "pip با موفقیت نصب شد"
        else
            print_error "خطا در نصب pip"
            exit 1
        fi
    fi
}

# نصب ابزارهای سیستمی
install_system_tools() {
    print_step "نصب ابزارهای مورد نیاز سیستم..."
    
    if [[ "$OS" == "ubuntu" ]]; then
        sudo apt update
        sudo apt install -y \
            git \
            wget \
            curl \
            sqlite3 \
            build-essential \
            libssl-dev \
            libffi-dev \
            python3-dev
    elif [[ "$OS" == "centos" ]]; then
        sudo yum install -y \
            git \
            wget \
            curl \
            sqlite \
            gcc \
            openssl-devel \
            libffi-devel \
            python3-devel
    fi
    
    print_success "ابزارهای سیستمی نصب شدند"
}

# ایجاد محیط مجازی
create_virtual_env() {
    print_step "ایجاد محیط مجازی Python..."
    
    if [[ -d "venv" ]]; then
        print_warning "محیط مجازی از قبل موجود است"
        read -p "آیا می‌خواهید آن را حذف و دوباره ایجاد کنید؟ (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf venv
        else
            print_info "از محیط مجازی موجود استفاده می‌شود"
            return
        fi
    fi
    
    python3 -m venv venv
    
    if [[ -d "venv" ]]; then
        print_success "محیط مجازی ایجاد شد"
    else
        print_error "خطا در ایجاد محیط مجازی"
        exit 1
    fi
}

# فعال‌سازی محیط مجازی
activate_virtual_env() {
    print_step "فعال‌سازی محیط مجازی..."
    
    source venv/bin/activate
    
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_success "محیط مجازی فعال شد"
    else
        print_error "خطا در فعال‌سازی محیط مجازی"
        exit 1
    fi
}

# بروزرسانی pip
upgrade_pip() {
    print_step "بروزرسانی pip..."
    
    pip install --upgrade pip
    print_success "pip بروزرسانی شد"
}

# نصب وابستگی‌ها
install_dependencies() {
    print_step "نصب وابستگی‌های Python..."
    
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        print_success "وابستگی‌ها نصب شدند"
    else
        print_error "فایل requirements.txt یافت نشد"
        exit 1
    fi
}

# ایجاد دایرکتوری‌ها
create_directories() {
    print_step "ایجاد دایرکتوری‌های مورد نیاز..."
    
    directories=("data" "logs" "backups" "monitoring")
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            print_success "دایرکتوری $dir ایجاد شد"
        else
            print_info "دایرکتوری $dir از قبل موجود است"
        fi
    done
}

# ایجاد فایل پیکربندی
create_config() {
    print_step "ایجاد فایل پیکربندی..."
    
    if [[ ! -f ".env" ]]; then
        if [[ -f ".env.example" ]]; then
            cp .env.example .env
            print_success "فایل .env ایجاد شد"
            print_warning "لطفاً فایل .env را ویرایش کنید"
        else
            print_error "فایل .env.example یافت نشد"
            
            # ایجاد فایل .env ساده
            cat > .env << EOF
# Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
BOT_USERNAME=YourBotUsername

# Virtualizer API Configuration  
VIRTUALIZER_API_URL=http://your-virtualizer-server.com/api
VIRTUALIZER_API_KEY=YOUR_API_KEY_HERE

# Admin Configuration
ADMIN_USER_IDS=123456789,987654321

# Database
DATABASE_PATH=./data/server_bot.db

# Security
SECRET_KEY=$(openssl rand -hex 32)
DEBUG_MODE=False
EOF
            print_success "فایل .env پایه ایجاد شد"
        fi
    else
        print_info "فایل .env از قبل موجود است"
    fi
}

# تنظیم مجوزها
set_permissions() {
    print_step "تنظیم مجوزهای فایل..."
    
    # مجوز اجرا برای اسکریپت‌ها
    chmod +x server_bot.py 2>/dev/null || true
    chmod +x *.sh 2>/dev/null || true
    
    # محافظت از فایل تنظیمات
    chmod 600 .env 2>/dev/null || true
    
    # مجوز خواندن برای فایل‌های Python
    chmod 644 *.py 2>/dev/null || true
    
    print_success "مجوزهای فایل تنظیم شدند"
}

# ایجاد سرویس systemd
create_systemd_service() {
    print_step "ایجاد سرویس systemd..."
    
    SERVICE_FILE="/etc/systemd/system/telegram-bot.service"
    CURRENT_USER=$(whoami)
    CURRENT_DIR=$(pwd)
    
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=Telegram Server Management Bot
After=network.target
Wants=network.target

[Service]
Type=simple
User=$CURRENT_USER
Group=$CURRENT_USER
WorkingDirectory=$CURRENT_DIR
Environment=PATH=$CURRENT_DIR/venv/bin
ExecStart=$CURRENT_DIR/venv/bin/python $CURRENT_DIR/server_bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$CURRENT_DIR

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable telegram-bot.service
    
    print_success "سرویس systemd ایجاد و فعال شد"
}

# ایجاد اسکریپت مدیریت
create_management_script() {
    print_step "ایجاد اسکریپت مدیریت..."
    
    cat > bot_manager.sh << 'EOF'
#!/bin/bash

# اسکریپت مدیریت ربات تلگرام

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
    update)
        echo "📦 بروزرسانی ربات..."
        source venv/bin/activate
        pip install -r requirements.txt --upgrade
        sudo systemctl restart telegram-bot
        ;;
    backup)
        echo "💾 ایجاد بکاپ..."
        BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$BACKUP_DIR"
        cp -r data logs .env "$BACKUP_DIR/"
        tar -czf "${BACKUP_DIR}.tar.gz" "$BACKUP_DIR"
        rm -rf "$BACKUP_DIR"
        echo "بکاپ ایجاد شد: ${BACKUP_DIR}.tar.gz"
        ;;
    *)
        echo "استفاده: $0 {start|stop|restart|status|logs|enable|disable|update|backup}"
        echo ""
        echo "دستورات موجود:"
        echo "  start   - شروع سرویس"
        echo "  stop    - توقف سرویس"
        echo "  restart - راه‌اندازی مجدد"
        echo "  status  - نمایش وضعیت"
        echo "  logs    - نمایش لاگ‌ها"
        echo "  enable  - فعال‌سازی خودکار"
        echo "  disable - غیرفعال‌سازی خودکار"
        echo "  update  - بروزرسانی"
        echo "  backup  - ایجاد بکاپ"
        exit 1
        ;;
esac
EOF

    chmod +x bot_manager.sh
    print_success "اسکریپت مدیریت ایجاد شد"
}

# تست نصب
test_installation() {
    print_step "تست نصب..."
    
    # تست Python
    if python3 -c "import telegram, aiohttp, psutil" 2>/dev/null; then
        print_success "وابستگی‌های Python صحیح هستند"
    else
        print_error "مشکل در وابستگی‌های Python"
        return 1
    fi
    
    # تست فایل‌ها
    required_files=("server_bot.py" ".env" "requirements.txt")
    for file in "${required_files[@]}"; do
        if [[ -f "$file" ]]; then
            print_success "فایل $file موجود است"
        else
            print_error "فایل $file یافت نشد"
            return 1
        fi
    done
    
    # تست دایرکتوری‌ها
    required_dirs=("data" "logs" "backups" "venv")
    for dir in "${required_dirs[@]}"; do
        if [[ -d "$dir" ]]; then
            print_success "دایرکتوری $dir موجود است"
        else
            print_error "دایرکتوری $dir یافت نشد"
            return 1
        fi
    done
    
    print_success "تمام تست‌ها موفق بودند"
    return 0
}

# نمایش مراحل نهایی
show_final_steps() {
    echo
    echo -e "${GREEN}🎉 نصب با موفقیت کامل شد!${NC}"
    echo
    echo -e "${YELLOW}📋 مراحل بعدی:${NC}"
    echo -e "${CYAN}1. فایل .env را ویرایش کنید:${NC}"
    echo "   nano .env"
    echo
    echo -e "${CYAN}2. توکن ربات تلگرام را از @BotFather دریافت کرده و در .env قرار دهید${NC}"
    echo
    echo -e "${CYAN}3. تنظیمات API ویرچوالایزور را وارد کنید${NC}"
    echo
    echo -e "${CYAN}4. ID تلگرام خود را از @userinfobot دریافت کرده و به عنوان ادمین اضافه کنید${NC}"
    echo
    echo -e "${CYAN}5. سرویس را شروع کنید:${NC}"
    echo "   ./bot_manager.sh start"
    echo
    echo -e "${CYAN}6. وضعیت سرویس را بررسی کنید:${NC}"
    echo "   ./bot_manager.sh status"
    echo
    echo -e "${CYAN}7. لاگ‌ها را مشاهده کنید:${NC}"
    echo "   ./bot_manager.sh logs"
    echo
    echo -e "${PURPLE}💡 نکات مهم:${NC}"
    echo -e "${YELLOW}- فایل .env حاوی اطلاعات حساس است، آن را محفوظ نگه دارید${NC}"
    echo -e "${YELLOW}- برای مدیریت ربات از اسکریپت bot_manager.sh استفاده کنید${NC}"
    echo -e "${YELLOW}- برای بکاپ منظم از دستور ./bot_manager.sh backup استفاده کنید${NC}"
    echo
    echo -e "${GREEN}✨ موفق باشید!${NC}"
}

# تابع اصلی
main() {
    print_header
    
    # بررسی‌های اولیه
    check_root
    check_os
    
    # نصب نیازمندی‌ها
    install_system_tools
    install_python
    install_pip
    
    # آماده‌سازی محیط
    create_virtual_env
    activate_virtual_env
    upgrade_pip
    install_dependencies
    
    # پیکربندی
    create_directories
    create_config
    set_permissions
    
    # سرویس سیستم
    create_systemd_service
    create_management_script
    
    # تست و تایید
    if test_installation; then
        show_final_steps
    else
        print_error "نصب با مشکل مواجه شد"
        exit 1
    fi
}

# اجرای برنامه اصلی
main "$@"