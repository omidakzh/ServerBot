#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات تلگرام برای مدیریت سرور اختصاصی با API ویرچوالایزور
Server Management Telegram Bot with Virtualizer API Integration
"""

import asyncio
import logging
import json
import sqlite3
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import psutil
import subprocess
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode
import os
from dataclasses import dataclass

# تنظیمات اصلی
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# وضعیت‌های مکالمه
(CREATE_VM, EDIT_VM, DELETE_VM, 
 CREATE_USER, EDIT_USER, DELETE_USER,
 BACKUP_CONFIG, RESTORE_CONFIG) = range(8)

@dataclass
class Config:
    """پیکربندی ربات"""
    BOT_TOKEN: str = "YOUR_BOT_TOKEN_HERE"
    VIRTUALIZER_API_URL: str = "http://your-virtualizer-server.com/api"
    VIRTUALIZER_API_KEY: str = "YOUR_API_KEY_HERE"
    DATABASE_PATH: str = "server_bot.db"
    ADMIN_USER_IDS: List[int] = None
    MAX_VMS_PER_USER: int = 5
    DEFAULT_VM_RESOURCES: Dict = None
    
    def __post_init__(self):
        if self.ADMIN_USER_IDS is None:
            self.ADMIN_USER_IDS = []
        if self.DEFAULT_VM_RESOURCES is None:
            self.DEFAULT_VM_RESOURCES = {
                'cpu': 1,
                'ram': 1024,
                'disk': 10240,
                'bandwidth': 1000
            }

config = Config()

class Database:
    """مدیریت دیتابیس"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """ایجاد جداول پایه"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # جدول کاربران
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    full_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    max_vms INTEGER DEFAULT 5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول ماشین‌های مجازی
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS virtual_machines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    vm_id TEXT UNIQUE,
                    name TEXT,
                    status TEXT DEFAULT 'stopped',
                    cpu INTEGER,
                    ram INTEGER,
                    disk INTEGER,
                    ip_address TEXT,
                    os_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (telegram_id)
                )
            ''')
            
            # جدول لاگ‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    details TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # جدول بکاپ‌ها
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vm_id TEXT,
                    backup_name TEXT,
                    backup_path TEXT,
                    size INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def add_user(self, telegram_id: int, username: str, full_name: str, is_admin: bool = False):
        """افزودن کاربر جدید"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (telegram_id, username, full_name, is_admin, last_activity)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, username, full_name, is_admin, datetime.now()))
            conn.commit()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """دریافت اطلاعات کاربر"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def log_activity(self, user_id: int, action: str, details: str = ""):
        """ثبت فعالیت کاربر"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO activity_logs (user_id, action, details)
                VALUES (?, ?, ?)
            ''', (user_id, action, details))
            conn.commit()

class VirtualizerAPI:
    """کلاس برای ارتباط با API ویرچوالایزور"""
    
    def __init__(self, api_url: str, api_key: str):
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = None
    
    async def init_session(self):
        """ایجاد session HTTP"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={'Authorization': f'Bearer {self.api_key}'}
            )
    
    async def close_session(self):
        """بستن session"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """ارسال درخواست به API"""
        await self.init_session()
        
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"API Error: {response.status} - {error_text}")
        
        except Exception as e:
            logger.error(f"API Request Error: {e}")
            raise
    
    async def get_server_stats(self) -> Dict:
        """دریافت آمار سرور"""
        return await self._make_request('GET', '/server/stats')
    
    async def list_vms(self, user_id: Optional[int] = None) -> List[Dict]:
        """لیست ماشین‌های مجازی"""
        endpoint = f'/vms?user_id={user_id}' if user_id else '/vms'
        return await self._make_request('GET', endpoint)
    
    async def create_vm(self, vm_config: Dict) -> Dict:
        """ایجاد ماشین مجازی جدید"""
        return await self._make_request('POST', '/vms', json=vm_config)
    
    async def get_vm_info(self, vm_id: str) -> Dict:
        """دریافت اطلاعات ماشین مجازی"""
        return await self._make_request('GET', f'/vms/{vm_id}')
    
    async def start_vm(self, vm_id: str) -> Dict:
        """روشن کردن ماشین مجازی"""
        return await self._make_request('POST', f'/vms/{vm_id}/start')
    
    async def stop_vm(self, vm_id: str) -> Dict:
        """خاموش کردن ماشین مجازی"""
        return await self._make_request('POST', f'/vms/{vm_id}/stop')
    
    async def restart_vm(self, vm_id: str) -> Dict:
        """راه‌اندازی مجدد ماشین مجازی"""
        return await self._make_request('POST', f'/vms/{vm_id}/restart')
    
    async def delete_vm(self, vm_id: str) -> Dict:
        """حذف ماشین مجازی"""
        return await self._make_request('DELETE', f'/vms/{vm_id}')
    
    async def create_backup(self, vm_id: str, backup_name: str) -> Dict:
        """ایجاد بکاپ"""
        data = {'backup_name': backup_name}
        return await self._make_request('POST', f'/vms/{vm_id}/backup', json=data)
    
    async def restore_backup(self, vm_id: str, backup_id: str) -> Dict:
        """بازیابی از بکاپ"""
        data = {'backup_id': backup_id}
        return await self._make_request('POST', f'/vms/{vm_id}/restore', json=data)

class ServerManagementBot:
    """کلاس اصلی ربات"""
    
    def __init__(self):
        self.db = Database(config.DATABASE_PATH)
        self.api = VirtualizerAPI(config.VIRTUALIZER_API_URL, config.VIRTUALIZER_API_KEY)
        self.app = None
    
    def is_admin(self, user_id: int) -> bool:
        """بررسی مجوز ادمین"""
        return user_id in config.ADMIN_USER_IDS
    
    def is_authorized(self, user_id: int) -> bool:
        """بررسی مجوز دسترسی"""
        user = self.db.get_user(user_id)
        return user and (user['is_active'] or self.is_admin(user_id))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """دستور شروع"""
        user = update.effective_user
        
        # ثبت کاربر در دیتابیس
        self.db.add_user(
            user.id, 
            user.username or "", 
            user.full_name or "",
            self.is_admin(user.id)
        )
        
        keyboard = [
            [KeyboardButton("📊 آمار سرور"), KeyboardButton("💻 ماشین‌های من")],
            [KeyboardButton("➕ ایجاد VM جدید"), KeyboardButton("⚙️ تنظیمات")],
            [KeyboardButton("📋 راهنما"), KeyboardButton("📞 پشتیبانی")]
        ]
        
        if self.is_admin(user.id):
            keyboard.append([KeyboardButton("👑 پنل ادمین")])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_text = f"""
🤖 **خوش آمدید به ربات مدیریت سرور**

سلام {user.first_name}! 

این ربات برای مدیریت سرور اختصاصی شما طراحی شده است.

**امکانات اصلی:**
• 📊 مشاهده آمار سرور
• 💻 مدیریت ماشین‌های مجازی
• 🔄 کنترل وضعیت VM ها
• 💾 مدیریت بکاپ
• 👥 مدیریت کاربران
• 📈 نظارت بر منابع

برای شروع از دکمه‌های زیر استفاده کنید.
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        
        self.db.log_activity(user.id, "start_bot")
    
    async def server_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش آمار سرور"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ شما مجوز دسترسی ندارید.")
            return
        
        try:
            # آمار سیستم محلی
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # آمار از API ویرچوالایزور
            api_stats = await self.api.get_server_stats()
            
            stats_text = f"""
📊 **آمار سرور**

**منابع سیستم:**
🖥️ CPU: {cpu_percent}%
🧠 RAM: {memory.percent}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
💾 دیسک: {disk.percent}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)

**ماشین‌های مجازی:**
▶️ فعال: {api_stats.get('active_vms', 0)}
⏸️ غیرفعال: {api_stats.get('inactive_vms', 0)}
📊 کل: {api_stats.get('total_vms', 0)}

**ترافیک شبکه:**
📤 ارسالی: {api_stats.get('network_tx', 0) / (1024**2):.1f} MB
📥 دریافتی: {api_stats.get('network_rx', 0) / (1024**2):.1f} MB

آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
            
            keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_stats")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در دریافت آمار: {str(e)}")
            logger.error(f"Stats error: {e}")
    
    async def my_vms(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """نمایش ماشین‌های مجازی کاربر"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ شما مجوز دسترسی ندارید.")
            return
        
        try:
            user_id = update.effective_user.id
            vms = await self.api.list_vms(user_id)
            
            if not vms:
                await update.message.reply_text(
                    "📭 شما هیچ ماشین مجازی ندارید.\n\n"
                    "برای ایجاد VM جدید از دکمه 'ایجاد VM جدید' استفاده کنید."
                )
                return
            
            vms_text = "💻 **ماشین‌های مجازی شما:**\n\n"
            
            keyboard = []
            for vm in vms:
                status_emoji = "▶️" if vm['status'] == 'running' else "⏸️"
                vms_text += f"{status_emoji} **{vm['name']}**\n"
                vms_text += f"   🏷️ ID: `{vm['vm_id']}`\n"
                vms_text += f"   🖥️ CPU: {vm['cpu']} Core\n"
                vms_text += f"   🧠 RAM: {vm['ram']} MB\n"
                vms_text += f"   🌐 IP: {vm.get('ip_address', 'تخصیص نیافته')}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"مدیریت {vm['name']}", 
                        callback_data=f"manage_vm_{vm['vm_id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("➕ ایجاد VM جدید", callback_data="create_vm")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                vms_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در دریافت لیست VM ها: {str(e)}")
            logger.error(f"VMs list error: {e}")
    
    async def vm_management_menu(self, vm_id: str, chat_id: int, message_id: int = None):
        """منوی مدیریت ماشین مجازی"""
        try:
            vm_info = await self.api.get_vm_info(vm_id)
            
            status_emoji = "▶️" if vm_info['status'] == 'running' else "⏸️"
            
            info_text = f"""
💻 **مدیریت {vm_info['name']}**

**وضعیت:** {status_emoji} {vm_info['status']}
**CPU:** {vm_info['cpu']} Core
**RAM:** {vm_info['ram']} MB  
**دیسک:** {vm_info['disk']} MB
**IP:** {vm_info.get('ip_address', 'تخصیص نیافته')}
**OS:** {vm_info.get('os_type', 'نامشخص')}
            """
            
            keyboard = []
            
            if vm_info['status'] == 'running':
                keyboard.append([
                    InlineKeyboardButton("⏸️ توقف", callback_data=f"stop_vm_{vm_id}"),
                    InlineKeyboardButton("🔄 ریستارت", callback_data=f"restart_vm_{vm_id}")
                ])
            else:
                keyboard.append([
                    InlineKeyboardButton("▶️ شروع", callback_data=f"start_vm_{vm_id}")
                ])
            
            keyboard.extend([
                [
                    InlineKeyboardButton("📊 آمار", callback_data=f"vm_stats_{vm_id}"),
                    InlineKeyboardButton("⚙️ تنظیمات", callback_data=f"vm_settings_{vm_id}")
                ],
                [
                    InlineKeyboardButton("💾 بکاپ", callback_data=f"vm_backup_{vm_id}"),
                    InlineKeyboardButton("🗑️ حذف", callback_data=f"delete_vm_{vm_id}")
                ],
                [InlineKeyboardButton("🔙 برگشت", callback_data="back_to_vms")]
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if message_id:
                await self.app.bot.edit_message_text(
                    info_text,
                    chat_id=chat_id,
                    message_id=message_id,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await self.app.bot.send_message(
                    chat_id,
                    info_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            error_msg = f"❌ خطا در دریافت اطلاعات VM: {str(e)}"
            if message_id:
                await self.app.bot.edit_message_text(error_msg, chat_id=chat_id, message_id=message_id)
            else:
                await self.app.bot.send_message(chat_id, error_msg)
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت دکمه‌های inline"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        
        if not self.is_authorized(user_id):
            await query.edit_message_text("⛔ شما مجوز دسترسی ندارید.")
            return
        
        try:
            if data == "refresh_stats":
                await self.server_stats_callback(query)
            
            elif data.startswith("manage_vm_"):
                vm_id = data.replace("manage_vm_", "")
                await self.vm_management_menu(vm_id, query.message.chat_id, query.message.message_id)
            
            elif data.startswith("start_vm_"):
                vm_id = data.replace("start_vm_", "")
                await self.start_vm_callback(query, vm_id)
            
            elif data.startswith("stop_vm_"):
                vm_id = data.replace("stop_vm_", "")
                await self.stop_vm_callback(query, vm_id)
            
            elif data.startswith("restart_vm_"):
                vm_id = data.replace("restart_vm_", "")
                await self.restart_vm_callback(query, vm_id)
            
            elif data.startswith("delete_vm_"):
                vm_id = data.replace("delete_vm_", "")
                await self.delete_vm_callback(query, vm_id)
            
            elif data == "create_vm":
                await self.create_vm_start(query)
            
            elif data == "back_to_vms":
                await self.my_vms_callback(query)
                
        except Exception as e:
            await query.edit_message_text(f"❌ خطا: {str(e)}")
            logger.error(f"Button handler error: {e}")
    
    async def start_vm_callback(self, query, vm_id: str):
        """روشن کردن VM"""
        try:
            await self.api.start_vm(vm_id)
            await query.edit_message_text("✅ ماشین مجازی در حال روشن شدن...")
            
            # بروزرسانی منو بعد از 3 ثانیه
            await asyncio.sleep(3)
            await self.vm_management_menu(vm_id, query.message.chat_id, query.message.message_id)
            
            self.db.log_activity(query.from_user.id, f"start_vm_{vm_id}")
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در روشن کردن VM: {str(e)}")
    
    async def stop_vm_callback(self, query, vm_id: str):
        """خاموش کردن VM"""
        try:
            await self.api.stop_vm(vm_id)
            await query.edit_message_text("✅ ماشین مجازی در حال خاموش شدن...")
            
            await asyncio.sleep(3)
            await self.vm_management_menu(vm_id, query.message.chat_id, query.message.message_id)
            
            self.db.log_activity(query.from_user.id, f"stop_vm_{vm_id}")
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در خاموش کردن VM: {str(e)}")
    
    async def restart_vm_callback(self, query, vm_id: str):
        """راه‌اندازی مجدد VM"""
        try:
            await self.api.restart_vm(vm_id)
            await query.edit_message_text("✅ ماشین مجازی در حال راه‌اندازی مجدد...")
            
            await asyncio.sleep(5)
            await self.vm_management_menu(vm_id, query.message.chat_id, query.message.message_id)
            
            self.db.log_activity(query.from_user.id, f"restart_vm_{vm_id}")
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در راه‌اندازی مجدد VM: {str(e)}")
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """مدیریت پیام‌های متنی"""
        text = update.message.text
        user_id = update.effective_user.id
        
        if not self.is_authorized(user_id):
            await update.message.reply_text("⛔ شما مجوز دسترسی ندارید.")
            return
        
        if text == "📊 آمار سرور":
            await self.server_stats(update, context)
        
        elif text == "💻 ماشین‌های من":
            await self.my_vms(update, context)
        
        elif text == "➕ ایجاد VM جدید":
            await self.create_vm_command(update, context)
        
        elif text == "⚙️ تنظیمات":
            await self.settings_command(update, context)
        
        elif text == "📋 راهنما":
            await self.help_command(update, context)
        
        elif text == "📞 پشتیبانی":
            await self.support_command(update, context)
        
        elif text == "👑 پنل ادمین" and self.is_admin(user_id):
            await self.admin_panel(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """راهنمای استفاده"""
        help_text = """
📋 **راهنمای استفاده از ربات**

**دستورات اصلی:**
• `/start` - شروع ربات
• `/stats` - آمار سرور
• `/myvms` - لیست ماشین‌های مجازی
• `/createvm` - ایجاد VM جدید
• `/help` - این راهنما

**مدیریت VM:**
• ایجاد، حذف، تنظیم منابع
• روشن/خاموش کردن
• راه‌اندازی مجدد
• مشاهده آمار

**امکانات بکاپ:**
• ایجاد بکاپ خودکار
• بازیابی از بکاپ
• مدیریت فایل‌های بکاپ

**نظارت:**
• آمار سرور لحظه‌ای
• مصرف منابع VM ها
• ترافیک شبکه

📞 برای کمک بیشتر با پشتیبانی تماس بگیرید.
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    def setup_handlers(self):
        """تنظیم handlers"""
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("stats", self.server_stats))
        self.app.add_handler(CommandHandler("myvms", self.my_vms))
        self.app.add_handler(CommandHandler("help", self.help_command))
        
        self.app.add_handler(CallbackQueryHandler(self.button_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
    
    async def run(self):
        """اجرای ربات"""
        self.app = Application.builder().token(config.BOT_TOKEN).build()
        self.setup_handlers()
        
        # تنظیم دستورات منو
        commands = [
            BotCommand("start", "شروع ربات"),
            BotCommand("stats", "آمار سرور"),
            BotCommand("myvms", "ماشین‌های مجازی من"),
            BotCommand("help", "راهنما"),
        ]
        await self.app.bot.set_my_commands(commands)
        
        print("🤖 ربات در حال اجرا...")
        await self.app.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """تابع اصلی"""
    bot = ServerManagementBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("🛑 ربات متوقف شد.")
    finally:
        asyncio.run(bot.api.close_session())

    async def create_vm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """شروع فرآیند ایجاد VM جدید"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ شما مجوز دسترسی ندارید.")
            return
        
        # بررسی حد مجاز VM
        user = self.db.get_user(update.effective_user.id)
        user_vms = await self.api.list_vms(update.effective_user.id)
        
        if len(user_vms) >= user.get('max_vms', config.MAX_VMS_PER_USER):
            await update.message.reply_text(
                f"⚠️ شما به حداکثر تعداد VM مجاز ({user['max_vms']}) رسیده‌اید.\n"
                "برای ایجاد VM جدید، ابتدا یکی از VM های موجود را حذف کنید."
            )
            return
        
        # منوی انتخاب نوع OS
        keyboard = [
            [
                InlineKeyboardButton("🐧 Ubuntu 22.04", callback_data="os_ubuntu22"),
                InlineKeyboardButton("🐧 Ubuntu 20.04", callback_data="os_ubuntu20")
            ],
            [
                InlineKeyboardButton("🎩 CentOS 8", callback_data="os_centos8"),
                InlineKeyboardButton("🎩 CentOS 7", callback_data="os_centos7")
            ],
            [
                InlineKeyboardButton("🪟 Windows Server 2019", callback_data="os_win2019"),
                InlineKeyboardButton("🪟 Windows Server 2022", callback_data="os_win2022")
            ],
            [
                InlineKeyboardButton("🔧 سفارشی", callback_data="os_custom"),
                InlineKeyboardButton("❌ لغو", callback_data="cancel_create")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "➕ **ایجاد ماشین مجازی جدید**\n\n"
            "لطفاً سیستم‌عامل مورد نظر را انتخاب کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def create_vm_start(self, query):
        """شروع ایجاد VM از طریق callback"""
        keyboard = [
            [
                InlineKeyboardButton("🐧 Ubuntu 22.04", callback_data="os_ubuntu22"),
                InlineKeyboardButton("🐧 Ubuntu 20.04", callback_data="os_ubuntu20")
            ],
            [
                InlineKeyboardButton("🎩 CentOS 8", callback_data="os_centos8"),
                InlineKeyboardButton("🎩 CentOS 7", callback_data="os_centos7")
            ],
            [
                InlineKeyboardButton("🪟 Windows Server 2019", callback_data="os_win2019"),
                InlineKeyboardButton("🪟 Windows Server 2022", callback_data="os_win2022")
            ],
            [
                InlineKeyboardButton("🔧 سفارشی", callback_data="os_custom"),
                InlineKeyboardButton("❌ لغو", callback_data="cancel_create")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➕ **ایجاد ماشین مجازی جدید**\n\n"
            "لطفاً سیستم‌عامل مورد نظر را انتخاب کنید:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تنظیمات کاربر"""
        if not self.is_authorized(update.effective_user.id):
            await update.message.reply_text("⛔ شما مجوز دسترسی ندارید.")
            return
        
        user = self.db.get_user(update.effective_user.id)
        
        settings_text = f"""
⚙️ **تنظیمات حساب کاربری**

**اطلاعات کاربر:**
👤 نام: {user['full_name']}
🆔 نام کاربری: @{user['username'] or 'تعریف نشده'}
📅 عضویت: {user['created_at'][:10]}

**محدودیت‌ها:**
💻 حداکثر VM: {user['max_vms']}
📊 وضعیت: {'فعال' if user['is_active'] else 'غیرفعال'}
👑 سطح دسترسی: {'ادمین' if user['is_admin'] else 'کاربر عادی'}

**تنظیمات اعلانات:**
🔔 اعلان وضعیت VM: فعال
📊 گزارش آمار روزانه: فعال
⚠️ هشدار منابع: فعال
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔔 تنظیمات اعلانات", callback_data="notification_settings"),
                InlineKeyboardButton("🔐 تغییر رمز", callback_data="change_password")
            ],
            [
                InlineKeyboardButton("📊 تاریخچه فعالیت", callback_data="activity_history"),
                InlineKeyboardButton("💾 دانلود داده‌ها", callback_data="export_data")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            settings_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پشتیبانی"""
        support_text = """
📞 **پشتیبانی و ارتباط با ما**

**راه‌های ارتباطی:**
📧 ایمیل: support@yourserver.com
💬 تلگرام: @YourSupportBot
🌐 وب‌سایت: https://yourserver.com
📱 تلفن: +98-21-12345678

**ساعات پشتیبانی:**
🕐 شنبه تا چهارشنبه: 8:00 - 20:00
🕐 پنج‌شنبه: 8:00 - 14:00
❌ جمعه‌ها تعطیل

**مسائل رایج:**
• مشکل اتصال به VM
• کندی سرور
• مشکلات بکاپ
• تغییر منابع

**گزارش مشکل:**
لطفاً موارد زیر را ذکر کنید:
- شرح کامل مشکل
- VM ID (در صورت وجود)
- زمان وقوع مشکل
- اسکرین‌شات (در صورت امکان)
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📧 ارسال تیکت", callback_data="create_ticket"),
                InlineKeyboardButton("❓ سوالات متداول", callback_data="faq")
            ],
            [
                InlineKeyboardButton("📊 وضعیت سرویس", callback_data="service_status"),
                InlineKeyboardButton("📋 مستندات", callback_data="documentation")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            support_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def admin_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """پنل مدیریت ادمین"""
        if not self.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ شما مجوز دسترسی به پنل ادمین ندارید.")
            return
        
        try:
            # آمار کلی سیستم
            all_vms = await self.api.list_vms()
            active_vms = len([vm for vm in all_vms if vm['status'] == 'running'])
            
            with sqlite3.connect(self.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
                active_users = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM users")
                total_users = cursor.fetchone()[0]
            
            admin_text = f"""
👑 **پنل مدیریت سیستم**

**آمار کلی:**
👥 کاربران فعال: {active_users}
👥 کل کاربران: {total_users}
💻 VM های فعال: {active_vms}
💻 کل VM ها: {len(all_vms)}

**عملیات سریع:**
• مدیریت کاربران
• نظارت بر سیستم
• تنظیمات سرور
• گزارش‌گیری

آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("👥 مدیریت کاربران", callback_data="admin_users"),
                    InlineKeyboardButton("💻 مدیریت VM ها", callback_data="admin_vms")
                ],
                [
                    InlineKeyboardButton("📊 گزارشات", callback_data="admin_reports"),
                    InlineKeyboardButton("⚙️ تنظیمات سیستم", callback_data="admin_settings")
                ],
                [
                    InlineKeyboardButton("🔧 ابزارهای سیستم", callback_data="admin_tools"),
                    InlineKeyboardButton("📝 لاگ سیستم", callback_data="admin_logs")
                ],
                [
                    InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_refresh")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                admin_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در بارگذاری پنل ادمین: {str(e)}")
    
    async def server_stats_callback(self, query):
        """بروزرسانی آمار سرور"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            api_stats = await self.api.get_server_stats()
            
            stats_text = f"""
📊 **آمار سرور**

**منابع سیستم:**
🖥️ CPU: {cpu_percent}%
🧠 RAM: {memory.percent}% ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)
💾 دیسک: {disk.percent}% ({disk.used // (1024**3):.1f}GB / {disk.total // (1024**3):.1f}GB)

**ماشین‌های مجازی:**
▶️ فعال: {api_stats.get('active_vms', 0)}
⏸️ غیرفعال: {api_stats.get('inactive_vms', 0)}
📊 کل: {api_stats.get('total_vms', 0)}

**ترافیک شبکه:**
📤 ارسالی: {api_stats.get('network_tx', 0) / (1024**2):.1f} MB
📥 دریافتی: {api_stats.get('network_rx', 0) / (1024**2):.1f} MB

آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            """
            
            keyboard = [[InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_stats")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در بروزرسانی آمار: {str(e)}")
    
    async def my_vms_callback(self, query):
        """نمایش لیست VM ها از طریق callback"""
        try:
            user_id = query.from_user.id
            vms = await self.api.list_vms(user_id)
            
            if not vms:
                await query.edit_message_text(
                    "📭 شما هیچ ماشین مجازی ندارید.\n\n"
                    "برای ایجاد VM جدید از دکمه زیر استفاده کنید.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("➕ ایجاد VM جدید", callback_data="create_vm")
                    ]])
                )
                return
            
            vms_text = "💻 **ماشین‌های مجازی شما:**\n\n"
            
            keyboard = []
            for vm in vms:
                status_emoji = "▶️" if vm['status'] == 'running' else "⏸️"
                vms_text += f"{status_emoji} **{vm['name']}**\n"
                vms_text += f"   🏷️ ID: `{vm['vm_id']}`\n"
                vms_text += f"   🖥️ CPU: {vm['cpu']} Core\n"
                vms_text += f"   🧠 RAM: {vm['ram']} MB\n"
                vms_text += f"   🌐 IP: {vm.get('ip_address', 'تخصیص نیافته')}\n\n"
                
                keyboard.append([
                    InlineKeyboardButton(
                        f"مدیریت {vm['name']}", 
                        callback_data=f"manage_vm_{vm['vm_id']}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("➕ ایجاد VM جدید", callback_data="create_vm")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                vms_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در دریافت لیست VM ها: {str(e)}")
    
    async def delete_vm_callback(self, query, vm_id: str):
        """تأیید و حذف VM"""
        try:
            vm_info = await self.api.get_vm_info(vm_id)
            
            confirmation_text = f"""
🗑️ **تأیید حذف ماشین مجازی**

⚠️ **هشدار:** این عمل غیرقابل بازگشت است!

**VM مورد نظر:**
📝 نام: {vm_info['name']}
🆔 شناسه: {vm_id}
💾 فضای دیسک: {vm_info['disk']} MB

**نکات مهم:**
• تمام داده‌های VM حذف خواهد شد
• بکاپ‌های موجود حفظ می‌شوند
• این عمل غیرقابل بازگشت است

آیا مطمئن هستید؟
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ بله، حذف کن", callback_data=f"confirm_delete_{vm_id}"),
                    InlineKeyboardButton("❌ لغو", callback_data=f"manage_vm_{vm_id}")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                confirmation_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            await query.edit_message_text(f"❌ خطا در دریافت اطلاعات VM: {str(e)}")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """مدیریت خطاها"""
        logger.error(f"Exception while handling an update: {context.error}")
        
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ خطای غیرمنتظره‌ای رخ داد. لطفاً دوباره تلاش کنید."
            )

if __name__ == "__main__":
    # تنظیمات اولیه - لطفاً قبل از اجرا این موارد را تنظیم کنید:
    
    # 1. توکن ربات تلگرام (از @BotFather دریافت کنید)
    config.BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # 2. آدرس و کلید API ویرچوالایزور
    config.VIRTUALIZER_API_URL = "http://your-virtualizer-server.com/api"
    config.VIRTUALIZER_API_KEY = "YOUR_API_KEY_HERE"
    
    # 3. لیست ID های ادمین
    config.ADMIN_USER_IDS = [123456789, 987654321]  # ID های تلگرام ادمین‌ها
    
    # 4. تنظیمات پیش‌فرض
    config.MAX_VMS_PER_USER = 5
    config.DEFAULT_VM_RESOURCES = {
        'cpu': 1,
        'ram': 1024,  # MB
        'disk': 10240,  # MB
        'bandwidth': 1000  # Mbps
    }
    
    print("🚀 در حال راه‌اندازی ربات مدیریت سرور...")
    print("📋 لطفاً مطمئن شوید که تمام تنظیمات به درستی انجام شده است.")
    
    # بررسی تنظیمات اولیه
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ خطا: لطفاً ابتدا BOT_TOKEN را تنظیم کنید")
        exit(1)
    
    if config.VIRTUALIZER_API_KEY == "YOUR_API_KEY_HERE":
        print("❌ خطا: لطفاً ابتدا VIRTUALIZER_API_KEY را تنظیم کنید")
        exit(1)
    
    # راه‌اندازی ربات
    bot = ServerManagementBot()
    main()