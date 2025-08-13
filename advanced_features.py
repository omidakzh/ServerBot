#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ویژگی‌های پیشرفته ربات مدیریت سرور
Advanced Features for Server Management Bot
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import schedule
from dataclasses import dataclass
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===== کلاس‌های کمکی =====

@dataclass
class VMTemplate:
    """قالب ماشین مجازی"""
    name: str
    os_type: str
    min_cpu: int
    min_ram: int
    min_disk: int
    default_software: List[str]
    
@dataclass
class Alert:
    """هشدار سیستم"""
    level: str  # info, warning, critical
    message: str
    vm_id: Optional[str]
    timestamp: datetime
    resolved: bool = False

class AdvancedMonitoring:
    """نظارت پیشرفته بر سیستم"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.alerts = []
        self.metrics_history = {}
    
    async def check_system_health(self):
        """بررسی سلامت کلی سیستم"""
        try:
            # بررسی CPU
            cpu_usage = psutil.cpu_percent(interval=1)
            if cpu_usage > 90:
                await self.create_alert(
                    "critical", 
                    f"مصرف CPU بالا: {cpu_usage}%"
                )
            
            # بررسی RAM
            memory = psutil.virtual_memory()
            if memory.percent > 85:
                await self.create_alert(
                    "warning", 
                    f"مصرف RAM بالا: {memory.percent}%"
                )
            
            # بررسی دیسک
            disk = psutil.disk_usage('/')
            if disk.percent > 90:
                await self.create_alert(
                    "critical", 
                    f"فضای دیسک کم: {disk.percent}%"
                )
            
            # بررسی VM های متوقف شده
            vms = await self.bot.api.list_vms()
            stopped_vms = [vm for vm in vms if vm['status'] == 'stopped']
            
            if len(stopped_vms) > 0:
                await self.create_alert(
                    "info",
                    f"{len(stopped_vms)} ماشین مجازی متوقف شده"
                )
                
        except Exception as e:
            logger.error(f"Error in health check: {e}")
    
    async def create_alert(self, level: str, message: str, vm_id: str = None):
        """ایجاد هشدار جدید"""
        alert = Alert(
            level=level,
            message=message,
            vm_id=vm_id,
            timestamp=datetime.now()
        )
        
        self.alerts.append(alert)
        
        # ارسال اعلان به ادمین‌ها
        await self.notify_admins(alert)
        
        # ذخیره در دیتابیس
        self.bot.db.log_activity(0, f"alert_{level}", message)
    
    async def notify_admins(self, alert: Alert):
        """اعلان به ادمین‌ها"""
        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️', 
            'critical': '🚨'
        }
        
        message = f"""
{emoji_map.get(alert.level, '📢')} **هشدار سیستم**

**سطح:** {alert.level.upper()}
**پیام:** {alert.message}
**زمان:** {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        if alert.vm_id:
            message += f"**VM ID:** {alert.vm_id}\n"
        
        for admin_id in config.ADMIN_USER_IDS:
            try:
                await self.bot.app.bot.send_message(
                    admin_id, 
                    message, 
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")

class BackupManager:
    """مدیریت پیشرفته بکاپ"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def auto_backup_all_vms(self):
        """بکاپ خودکار تمام VM ها"""
        try:
            vms = await self.bot.api.list_vms()
            
            for vm in vms:
                if vm['status'] == 'running':
                    backup_name = f"auto_backup_{vm['vm_id']}_{datetime.now().strftime('%Y%m%d_%H%M')}"
                    
                    try:
                        result = await self.bot.api.create_backup(vm['vm_id'], backup_name)
                        
                        # ثبت در دیتابیس
                        with sqlite3.connect(self.bot.db.db_path) as conn:
                            cursor = conn.cursor()
                cursor.execute('''
                    SELECT SUM(cpu) as total_cpu, SUM(ram) as total_ram, 
                           SUM(disk) as total_disk, COUNT(*) as total_vms
                    FROM virtual_machines 
                    WHERE user_id = ? AND status != 'deleted'
                ''', (user_id,))
                
                result = cursor.fetchone()
                
                return {
                    'cpu': result['total_cpu'] or 0,
                    'ram': result['total_ram'] or 0,
                    'disk': result['total_disk'] or 0,
                    'vms': result['total_vms'] or 0
                }
                
        except Exception as e:
            logger.error(f"Failed to get user resource usage: {e}")
            return {'cpu': 0, 'ram': 0, 'disk': 0, 'vms': 0}

class ScheduledTasks:
    """مدیریت وظایف زمان‌بندی شده"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.monitoring = AdvancedMonitoring(bot_instance)
        self.backup_manager = BackupManager(bot_instance)
    
    def setup_schedules(self):
        """تنظیم برنامه‌های زمان‌بندی"""
        # بررسی سلامت سیستم هر 5 دقیقه
        schedule.every(5).minutes.do(
            lambda: asyncio.create_task(self.monitoring.check_system_health())
        )
        
        # بکاپ خودکار روزانه در ساعت 2 شب
        schedule.every().day.at("02:00").do(
            lambda: asyncio.create_task(self.backup_manager.auto_backup_all_vms())
        )
        
        # پاکسازی بکاپ‌های قدیمی هفتگی
        schedule.every().sunday.at("03:00").do(
            lambda: asyncio.create_task(self.backup_manager.cleanup_old_backups())
        )
        
        # گزارش آمار روزانه
        schedule.every().day.at("09:00").do(
            lambda: asyncio.create_task(self.send_daily_report())
        )
    
    async def send_daily_report(self):
        """ارسال گزارش روزانه"""
        try:
            # جمع‌آوری آمار
            all_vms = await self.bot.api.list_vms()
            active_vms = len([vm for vm in all_vms if vm['status'] == 'running'])
            
            with sqlite3.connect(self.bot.db.db_path) as conn:
                cursor = conn.cursor()
                
                # کاربران فعال امروز
                cursor.execute('''
                    SELECT COUNT(DISTINCT user_id) 
                    FROM activity_logs 
                    WHERE DATE(timestamp) = DATE('now')
                ''')
                active_users_today = cursor.fetchone()[0]
                
                # تعداد VM های ایجاد شده امروز
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM virtual_machines 
                    WHERE DATE(created_at) = DATE('now')
                ''')
                new_vms_today = cursor.fetchone()[0]
            
            # آمار سیستم
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            report = f"""
📊 **گزارش روزانه سرور**
📅 {datetime.now().strftime('%Y-%m-%d')}

**آمار کلی:**
💻 VM های فعال: {active_vms}/{len(all_vms)}
👥 کاربران فعال امروز: {active_users_today}
➕ VM های جدید امروز: {new_vms_today}

**منابع سیستم:**
🖥️ CPU: {cpu_usage:.1f}%
🧠 RAM: {memory.percent:.1f}%
💾 دیسک: {disk.percent:.1f}%

**وضعیت کلی:** {'🟢 سالم' if cpu_usage < 80 and memory.percent < 85 else '🟡 نیاز به توجه'}
            """
            
            # ارسال به ادمین‌ها
            for admin_id in config.ADMIN_USER_IDS:
                try:
                    await self.bot.app.bot.send_message(
                        admin_id,
                        report,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.error(f"Failed to send daily report to {admin_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")

class EmailNotifications:
    """سیستم اعلان ایمیل"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    async def send_email(self, to_email: str, subject: str, body: str, html_body: str = None):
        """ارسال ایمیل"""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = to_email
            
            # متن ساده
            part1 = MIMEText(body, 'plain', 'utf-8')
            msg.attach(part1)
            
            # HTML (در صورت وجود)
            if html_body:
                part2 = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(part2)
            
            # ارسال
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
                
            logger.info(f"Email sent to {to_email}")
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

class APIRateLimiter:
    """محدودکننده نرخ درخواست API"""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {user_id: [timestamp, ...]}
    
    def is_allowed(self, user_id: int) -> bool:
        """بررسی مجاز بودن درخواست"""
        now = time.time()
        
        # حذف درخواست‌های قدیمی
        if user_id in self.requests:
            self.requests[user_id] = [
                req_time for req_time in self.requests[user_id]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[user_id] = []
        
        # بررسی محدودیت
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        
        # اضافه کردن درخواست جدید
        self.requests[user_id].append(now)
        return True

class SecurityManager:
    """مدیریت امنیت پیشرفته"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.failed_attempts = {}  # {user_id: count}
        self.blocked_users = set()
        self.rate_limiter = APIRateLimiter()
    
    def check_security(self, user_id: int) -> bool:
        """بررسی امنیت کاربر"""
        # بررسی مسدود بودن
        if user_id in self.blocked_users:
            return False
        
        # بررسی rate limiting
        if not self.rate_limiter.is_allowed(user_id):
            logger.warning(f"Rate limit exceeded for user {user_id}")
            return False
        
        return True
    
    def log_failed_attempt(self, user_id: int):
        """ثبت تلاش ناموفق"""
        self.failed_attempts[user_id] = self.failed_attempts.get(user_id, 0) + 1
        
        # مسدود کردن بعد از 5 تلاش ناموفق
        if self.failed_attempts[user_id] >= 5:
            self.blocked_users.add(user_id)
            logger.warning(f"User {user_id} blocked due to multiple failed attempts")

# ===== تست‌های خودکار =====

class BotTesting:
    """کلاس تست ربات"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    async def test_api_connection(self) -> bool:
        """تست اتصال به API"""
        try:
            result = await self.bot.api.get_server_stats()
            return 'active_vms' in result
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    async def test_database(self) -> bool:
        """تست دیتابیس"""
        try:
            with sqlite3.connect(self.bot.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                cursor.fetchone()
            return True
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return False
    
    async def test_vm_operations(self) -> bool:
        """تست عملیات VM"""
        try:
            # تست لیست VM ها
            vms = await self.bot.api.list_vms()
            
            if vms:
                # تست دریافت اطلاعات VM
                vm_info = await self.bot.api.get_vm_info(vms[0]['vm_id'])
                return 'status' in vm_info
            
            return True
        except Exception as e:
            logger.error(f"VM operations test failed: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """اجرای تمام تست‌ها"""
        tests = {
            'api_connection': await self.test_api_connection(),
            'database': await self.test_database(),
            'vm_operations': await self.test_vm_operations()
        }
        
        logger.info(f"Test results: {tests}")
        return tests

# ===== مدیریت تنظیمات پیشرفته =====

class ConfigManager:
    """مدیریت پیکربندی پیشرفته"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.settings = {}
        self.load_config()
    
    def load_config(self):
        """بارگذاری تنظیمات"""
        try:
            if os.path.exists(self.config_file):
                import yaml
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.settings = yaml.safe_load(f)
            else:
                self.create_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """ایجاد تنظیمات پیش‌فرض"""
        self.settings = {
            'bot': {
                'max_vms_per_user': 5,
                'default_resources': {
                    'cpu': 1,
                    'ram': 1024,
                    'disk': 10240
                }
            },
            'monitoring': {
                'check_interval': 300,
                'alert_thresholds': {
                    'cpu': 80,
                    'ram': 85,
                    'disk': 90
                }
            },
            'backup': {
                'auto_backup': True,
                'retention_days': 30,
                'backup_schedule': '02:00'
            }
        }
        self.save_config()
    
    def save_config(self):
        """ذخیره تنظیمات"""
        try:
            import yaml
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default=None):
        """دریافت تنظیم"""
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value):
        """تنظیم مقدار"""
        keys = key.split('.')
        settings = self.settings
        
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]
        
        settings[keys[-1]] = value
        self.save_config()

# ===== اسکریپت تست =====

async def run_diagnostics():
    """اجرای تشخیص مشکلات"""
    print("🔍 شروع تشخیص مشکلات...")
    
    # تست متغیرهای محیطی
    required_vars = ['BOT_TOKEN', 'VIRTUALIZER_API_URL', 'VIRTUALIZER_API_KEY']
    for var in required_vars:
        if not os.getenv(var):
            print(f"❌ متغیر محیطی {var} تنظیم نشده است")
        else:
            print(f"✅ {var} تنظیم شده")
    
    # تست فایل‌ها
    required_files = ['server_bot.py', 'requirements.txt']
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ فایل {file} موجود است")
        else:
            print(f"❌ فایل {file} یافت نشد")
    
    # تست دایرکتوری‌ها
    required_dirs = ['data', 'logs', 'backups']
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ دایرکتوری {dir_name} موجود است")
        else:
            print(f"⚠️ دایرکتوری {dir_name} وجود ندارد - در حال ایجاد...")
            os.makedirs(dir_name, exist_ok=True)
    
    print("✅ تشخیص مشکلات کامل شد")

if __name__ == "__main__":
    # اجرای تشخیص مشکلات
    asyncio.run(run_diagnostics())
            cursor.execute('''
                                INSERT INTO backups (vm_id, backup_name, backup_path, size)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                vm['vm_id'], 
                                backup_name, 
                                result.get('path', ''), 
                                result.get('size', 0)
                            ))
                            conn.commit()
                        
                        logger.info(f"Auto backup created for VM {vm['vm_id']}")
                        
                    except Exception as e:
                        logger.error(f"Failed to backup VM {vm['vm_id']}: {e}")
                        
        except Exception as e:
            logger.error(f"Auto backup failed: {e}")
    
    async def cleanup_old_backups(self, retention_days: int = 30):
        """حذف بکاپ‌های قدیمی"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            with sqlite3.connect(self.bot.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM backups 
                    WHERE created_at < ?
                ''', (cutoff_date,))
                
                old_backups = cursor.fetchall()
                
                for backup in old_backups:
                    # حذف فایل بکاپ
                    if os.path.exists(backup[3]):  # backup_path
                        os.remove(backup[3])
                    
                    # حذف از دیتابیس
                    cursor.execute('DELETE FROM backups WHERE id = ?', (backup[0],))
                
                conn.commit()
                logger.info(f"Cleaned up {len(old_backups)} old backups")
                
        except Exception as e:
            logger.error(f"Backup cleanup failed: {e}")

class UserQuotaManager:
    """مدیریت کوتا کاربران"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
    
    def check_user_quota(self, user_id: int, resource_type: str, amount: int) -> bool:
        """بررسی کوتا کاربر"""
        user = self.bot.db.get_user(user_id)
        if not user:
            return False
        
        # محاسبه مصرف فعلی
        current_usage = self.get_user_resource_usage(user_id)
        
        quotas = {
            'cpu': user.get('max_cpu', 4),
            'ram': user.get('max_ram', 8192),
            'disk': user.get('max_disk', 102400),
            'vms': user.get('max_vms', 5)
        }
        
        if resource_type in quotas:
            return current_usage.get(resource_type, 0) + amount <= quotas[resource_type]
        
        return True
    
    def get_user_resource_usage(self, user_id: int) -> Dict:
        """محاسبه مصرف منابع کاربر"""
        try:
            with sqlite3.connect(self.bot.db.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                