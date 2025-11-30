from __future__ import annotations

import asyncio
import base64
import html
import io
import json
import logging
import os
import random
import re
import string
import sys
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone

# --- THIRD-PARTY DEPENDENCIES (AUTO-INSTALL IF MISSING) ---

try:
    import requests  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests  # noqa: F401

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
    from telegram.error import BadRequest
except ImportError:
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "python-telegram-bot"]
    )
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )
    from telegram.error import BadRequest

try:
    import aiofiles  # For async file I/O
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiofiles"])
    import aiofiles

try:
    import httpx  # For async HTTP requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

try:
    import aiomysql  # For async MySQL database access
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiomysql"])
    import aiomysql

# Ensure cryptography is available for some MySQL auth methods
try:
    import cryptography  # noqa: F401
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "cryptography"])
    import cryptography  # noqa: F401

# --- LOGGING ---

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---

TELEGRAM_BOT_TOKEN = "8499529767:AAHDMLnMOoGI9tTe-Gf3Q3MjpaNxbJKtM1Y"

AUTO_CLEANUP_INTERVAL = 60 * 60  # 1 hour
DEFAULT_RATE_LIMIT_SECONDS = 300  # 5 minutes
USERS_PER_PAGE = 10  # (kept for compatibility, not heavily used)

# --- LOCAL FILE CONFIGURATION ---

DATA_DIR = "bot_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR, exist_ok=True)

USER_DATA_FILE = os.path.join(DATA_DIR, "approved_users.json")
REFERRAL_DATA_FILE = os.path.join(DATA_DIR, "referral_data.json")
ALL_USERS_FILE = os.path.join(DATA_DIR, "all_users.json")
PRICE_LIST_FILE = os.path.join(DATA_DIR, "price_list.json")
USER_SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# --- MYSQL DATABASE CONFIGURATION ---

MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "refihzbz_fbchek"
MYSQL_PASSWORD = "Asraf1025@#"
MYSQL_DB = "refihzbz_fbchek"

# --- PREMIUM ADMIN & APPROVAL SYSTEM ---

ADMIN_ID = 7646847122
ADMIN_USERNAME = "@Teamredadmin"
ADMIN_FIRST_NAME = "DOREMON"

approved_users: dict[int, datetime | None] = {ADMIN_ID: None}
referral_data: dict[str, dict] = {}
all_users: dict[str, dict] = {}
user_settings: dict[str, dict] = {}
user_last_request: dict[int, datetime] = {}
config_data: dict[str, int] = {"rate_limit_seconds": DEFAULT_RATE_LIMIT_SECONDS}

price_list = {
    "1_day": {"duration": "1 Day", "price_bdt": 50, "price_usd": 0.45},
    "3_days": {"duration": "3 Days", "price_bdt": 140, "price_usd": 1.25},
    "7_days": {"duration": "7 Days", "price_bdt": 300, "price_usd": 2.70},
    "15_days": {"duration": "15 Days", "price_bdt": 600, "price_usd": 5.40},
    "30_days": {"duration": "30 Days", "price_bdt": 1000, "price_usd": 9.00},
}

# --- LANGUAGE STRINGS (unchanged from previous version to preserve UX) ---

LANGUAGES = {
    "en": {
        "welcome": "👋 Hi {first_name}!\n\nWelcome to the Facebook Number Checker Bot.\n\nPlease select your preferred language:",
        "language_selected": "✅ Language has been set to English.\n\nThis is a premium service. Send me a list of phone numbers to check.\n\n🔐 Need access? Use /admin to contact support.",
        "example": "Example:\n+8801712345678\n+8801812345678",
        "access_denied": "🚫 Access Denied!\n\nThis is a premium service for paid users only. It runs on a VPS with premium proxies to avoid rate limitations.\n\nYour User ID: {uid}\n\nPlease contact the admin to get access.\nUse /admin to get support contact.",
        "buy_online": "Buy Online (Coming Soon)",
        "refer_earn": "Refer & Earn Free Access",
        "buy_online_msg": "🛒 Buy Online\n\nOnline payment option is coming soon!\n\nFor now, please contact the admin directly to purchase access.\nUse /admin to get contact details.",
        "refer_link": "🔗 Your Referral Link\n\nShare this link with your friends:\n{referral_link}\n\nReferrals: {referral_count}/3\n",
        "refer_earned": "✅ You've earned 2 hours of free access!\n",
        "refer_needed": "❌ You need {remaining} more referral(s) to get 2 hours of free access.\n",
        "referral_status": "🔗 Your Referral Status\n\nYour referral code: {referral_code}\nYour referral link:\n{referral_link}\n\nReferrals: {referral_count}/3\n",
        "access_until": "✅ You have access until: {expiry_date}\n",
        "permanent_access": "✅ You have permanent access.\n",
        "processing": "🚀 Processing your numbers... Please wait.",
        "no_numbers": "❌ You didn't send any valid numbers. Please send numbers, one per line.",
        "check_complete": "--- ✅ Check Complete! ---\n\n",
        "found_numbers": "✅ Found Numbers:\n",
        "not_found_numbers": "❌ Not Found Numbers:\n",
        "errors_unknown": "⚠️ Errors/Unknown:\n",
        "no_valid_numbers": "Could not process any numbers. Please check the format.",
        "rate_limit": "⏳ Rate Limit Exceeded!\n\nYou can only make one request every {time_limit}.\n\nPlease wait {remaining_time} before trying again.",
        "admin_contact": "👑 Admin Contact Information\n\n👤 Name: {admin_name}\n🆔 ID: {admin_id}\n🔗 Username: {admin_username}\n\nPlease contact the admin for approval or support.",
        "price_list": "💰 Price List\n\n",
        "payment_methods": "\n💳 Payment Methods:\n• Bkash\n• Nagad\n• Rocket\n• PayPal\n• Crypto\n\n📩 To purchase, please contact the admin.\nUse /admin to get contact details.",
        "admin_panel": "👑 Admin Panel\n\nSelect an option from the menu below:",
        "user_management": "👥 User Management",
        "price_management": "💰 Price Management",
        "communication": "📢 Communication",
        "system_management": "⚙️ System Management",
        "statistics": "📊 Statistics",
        "back": "🔙 Back",
        "approved_users": "✅ Approved Users",
        "all_users": "👤 All Users",
        "approve_user": "➕ Approve User",
        "disapprove_user": "➖ Disapprove User",
        "view_prices": "📋 View Price List",
        "broadcast_all": "📢 Broadcast to All",
        "broadcast_approved": "✅ Broadcast to Approved",
        "sync_files": "🔄 Sync Files",
        "export_data": "📦 Export Data",
        "change_rate_limit": "⚙️ Change Rate Limit",
        "bot_statistics": (
            "📊 Bot Statistics\n\n"
            "👥 Total Users: {total_users}\n"
            "✅ Approved Users: {approved_users}\n"
            "⏳ Pending Users: {pending_users}\n"
            "🔗 Total Referrals: {total_referrals}\n"
            "🔢 Total Numbers Checked: {total_numbers_checked}\n\n"
            "📅 Last Updated: {last_updated}"
        ),
        "current_price_list": "💰 Current Price List\n\n",
        "approve_user_msg": (
            "➕ Approve User\n\nPlease send the user ID and duration in the format:\n"
            "/approve &lt;user_id&gt; &lt;amount&gt; &lt;unit&gt;\n\n"
            "Example: /approve 123456789 7 days\n\nAvailable units: hours, days, months"
        ),
        "disapprove_user_msg": (
            "➖ Disapprove User\n\nPlease send the user ID in the format:\n"
            "/disapprove &lt;user_id&gt;\n\nExample: /disapprove 123456789"
        ),
        "broadcast_all_msg": (
            "📢 Broadcast to All Users\n\nPlease send your message in the format:\n"
            "/broadcast &lt;your message&gt;\n\n"
            "Example: /broadcast Hello everyone! The bot will be under maintenance for 2 hours."
        ),
        "broadcast_approved_msg": (
            "📢 Broadcast to Approved Users\n\nPlease send your message in the format:\n"
            "/broadcast_approved &lt;your message&gt;\n\n"
            "Example: /broadcast_approved New features have been added to the bot!"
        ),
        "unauthorized": "❌ You are not authorized to use this command.",
        "usage_approve": (
            "Usage: /approve &lt;user_id&gt; &lt;amount&gt; &lt;unit&gt;\n"
            "Example: /approve 123456789 7 days"
        ),
        "usage_disapprove": "Usage: /disapprove &lt;user_id&gt;\nExample: /disapprove 123456789",
        "usage_setratelimit": (
            "Usage: /setratelimit &lt;seconds&gt;\nExample: /setratelimit 600 (for 10 minutes)"
        ),
        "usage_broadcast": "Usage: /broadcast &lt;your message&gt;",
        "usage_broadcast_approved": "Usage: /broadcast_approved &lt;your message&gt;",
        "invalid_unit": "❌ Invalid unit. Use 'hours', 'days', or 'months'.",
        "invalid_input": "❌ Invalid input. Please use the correct format: {format}",
        "cannot_disapprove_admin": "❌ You cannot disapprove the main admin.",
        "user_not_approved": "⚠️ User {uid} was not in the approved list.",
        "user_approved": "✅ User {uid} has been approved until {expiry_date}.",
        "user_disapproved": "✅ User {uid} has been disapproved.",
        "rate_limit_updated": "✅ Rate limit updated to {seconds} seconds ({time_str}).",
        "broadcast_complete": (
            "✅ Broadcast complete.\n\n✅ Successful: {success_count}\n❌ Failed: {fail_count}"
        ),
        "broadcast_approved_complete": (
            "✅ Broadcast to approved users complete.\n\n"
            "✅ Successful: {success_count}\n❌ Failed: {fail_count}"
        ),
        "syncing": "🔄 Syncing data files...",
        "sync_success": "✅ All data files successfully synced.",
        "sync_failed": "❌ Failed to sync some data files. Please check the logs.",
        "no_approved_users": "There are no approved users.",
        "no_users": "No users have interacted with the bot yet.",
        "invalid_user_id": "❌ Invalid User ID. Please provide a valid numerical ID.",
        "list_too_long": "The list was too long and has been sent as a file.",
        "access_expired": (
            "⏳ Your access has expired.\n\nPlease contact the admin to renew your "
            "subscription.\nUse /admin for contact details."
        ),
        "access_approved": (
            "🎉 Congratulations! Your access has been approved.\n\n"
            "You can use the bot until {expiry_date}.\n\nEnjoy the premium service!"
        ),
        "access_revoked": (
            "🚫 Your access has been revoked by the admin.\n\n"
            "Please contact the admin for more details if you think this is a mistake.\n"
            "Use /admin for contact details."
        ),
        "referral_successful": "Referral successful! You now have {referral_count}/3 referrals.",
        "referral_earned": "Congratulations! You've earned 2 hours of access through referrals!",
        "already_used_bot": "You have already used the bot before.",
        "invalid_referral": "Invalid referral code.",
        "select_option": "Please select an option from the menu below:",
        "to_main_menu": "to Main Menu",
        "to_price_management": "to Price Management",
        "to_user_management": "to User Management",
        "to_communication": "to Communication",
        "to_system_management": "to System Management",
        "new_referral_notification": (
            "🎉 Good news! Someone joined using your referral link.\n\n"
            "You now have {referral_count}/3 referrals.\n\nKeep sharing to earn free access!"
        ),
        "cleanup_expired": "🧹 Cleaning up expired users...",
        "cleanup_complete": "✅ Cleanup complete. Removed {count} expired users.",
        "user_already_approved": (
            "⚠️ User {uid} is already approved until {expiry_date}."
        ),
        "select_user": "Select a user to view details:",
        "user_details": (
            "👤 User Details\n\nID: {user_id}\nName: {first_name} {last_name}\nUsername: "
            "@{username}\nLanguage: {language}\nLast Interaction: {last_interaction}\n"
            "Approved: {approved}\nNumbers Checked: {numbers_checked}\n{expiry_info}"
        ),
        "export_data_msg": (
            "📦 Export Data\n\nYour bot data is being prepared for download.\n\n"
            "This may take a moment if you have many users."
        ),
        "export_complete": "✅ Export complete. The data has been sent as a zip file.",
        "select_user_to_approve": "Select a user to approve:",
        "select_plan_for_user": "Select a plan for {user_name}:",
        "page_info": "Page {current_page}/{total_pages}",
        "no_pending_users": "There are no pending users to approve.",
        "change_rate_limit_msg": (
            "⚙️ Change Rate Limit\n\nCurrent rate limit: {current_limit} seconds "
            "({current_time_str})\n\nPlease send the new rate limit in seconds using "
            "the command:\n/setratelimit &lt;seconds&gt;\n\nExample: /setratelimit 600 "
            "(for 10 minutes)"
        ),
    },
    "bn": {
        "welcome": (
            "👋 হ্যালো {first_name}!\n\nফেসবুক নম্বর চেকার বটে স্বাগতম।\n\n"
            "অনুগ্রহ করে আপনার পছন্দের ভাষা নির্বাচন করুন:"
        ),
        "language_selected": (
            "✅ ভাষা বাংলায় সেট করা হয়েছে।\n\nএটি একটি প্রিমিয়াম সার্ভিস। "
            "আমাকে ফোন নম্বরের তালিকা পাঠান যাচাই করার জন্য।\n\n🔐 অ্যাক্সেস প্রয়োজন? "
            "/admin ব্যবহার করে সাপোর্টের সাথে যোগাযোগ করুন।"
        ),
        "example": "উদাহরণ:\n+8801712345678\n+8801812345678",
        "access_denied": (
            "🚫 অ্যাক্সেস প্রত্যাখ্যান করা হয়েছে!\n\nএটি শুধুমাত্র পেইড ইউজারদের জন্য "
            "একটি প্রিমিয়াম সার্ভিস। এটি হার সীমাবদ্ধতা এড়াতে একটি VPS এবং প্রিমিয়াম "
            "প্রক্সি ব্যবহার করে চলে।\n\nআপনার ইউজার ID: {uid}\n\nঅ্যাক্সেস পেতে অনুগ্রহ "
            "করে অ্যাডমিনের সাথে যোগাযোগ করুন।\nসাপোর্টের যোগাযোগের জন্য /admin ব্যবহার করুন।"
        ),
        "buy_online": "অনলাইনে কিনুন (শীঘ্রই আসছে)",
        "refer_earn": "রেফার করুন এবং ফ্রি অ্যাক্সেস অর্জন করুন",
        "buy_online_msg": (
            "🛒 অনলাইনে কিনুন\n\nঅনলাইন পেমেন্ট অপশন শীঘ্রই আসছে!\n\nএখন, অ্যাক্সেস "
            "কেনার জন্য সরাসরি অ্যাডমিনের সাথে যোগাযোগ করুন।\nযোগাযোগের বিবরণের জন্য "
            "/admin ব্যবহার করুন।"
        ),
        "refer_link": (
            "🔗 আপনার রেফারেল লিঙ্ক\n\nআপনার বন্ধুদের সাথে এই লিঙ্কটি শেয়ার করুন:\n"
            "{referral_link}\n\nরেফারেল: {referral_count}/3\n"
        ),
        "refer_earned": "✅ আপনি রেফারেলের মাধ্যমে 2 ঘন্টার ফ্রি অ্যাক্সেস অর্জন করেছেন!\n",
        "refer_needed": (
            "❌ 2 ঘন্টার ফ্রি অ্যাক্সেস পেতে আপনার {remaining} আরও রেফারেল(স) প্রয়োজন।\n"
        ),
        "referral_status": (
            "🔗 আপনার রেফারেল স্ট্যাটাস\n\nআপনার রেফারেল কোড: {referral_code}\n"
            "আপনার রেফারেল লিঙ্ক:\n{referral_link}\n\nরেফারেল: {referral_count}/3\n"
        ),
        "access_until": "✅ আপনার অ্যাক্সেস আছে পর্যন্ত: {expiry_date}\n",
        "permanent_access": "✅ আপনার স্থায়ী অ্যাক্সেস আছে।\n",
        "processing": "🚀 আপনার নম্বরগুলি প্রক্রিয়া করা হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।",
        "no_numbers": (
            "❌ আপনি কোনো বৈধ নম্বর পাঠাননি। অনুগ্রহ করে নম্বরগুলি পাঠান, এক লাইনে একটি করে।"
        ),
        "check_complete": "--- ✅ যাচাই সম্পন্ন! ---\n\n",
        "found_numbers": "✅ পাওয়া নম্বর:\n",
        "not_found_numbers": "❌ পাওয়া যায়নি এমন নম্বর:\n",
        "errors_unknown": "⚠️ ত্রুটি/অজানা:\n",
        "no_valid_numbers": "কোনো নম্বর প্রক্রিয়া করা যায়নি। অনুগ্রহ করে ফরম্যাট চেক করুন।",
        "rate_limit": (
            "⏳ রেট লিমিট অতিক্রান্ত!\n\nআপনি প্রতি {time_limit} শুধুমাত্র একবার "
            "রিকোয়েস্ট করতে পারেন।\n\nআবার চেষ্টা করার আগে অনুগ্রহ করে "
            "{remaining_time} অপেক্ষা করুন।"
        ),
        "admin_contact": (
            "👑 অ্যাডমিন যোগাযোগ তথ্য\n\n👤 নাম: {admin_name}\n🆔 ID: {admin_id}\n"
            "🔗 ইউজারনেম: {admin_username}\n\nঅনুমোদন বা সাপোর্টের জন্য অ্যাডমিনের সাথে "
            "যোগাযোগ করুন।"
        ),
        "price_list": "💰 মূল্য তালিকা\n\n",
        "payment_methods": (
            "\n💳 পেমেন্ট পদ্ধতি:\n• বিকাশ\n• নগদ\n• রকেট\n• পেপাল\n• ক্রিপ্টো\n\n"
            "📩 কেনার জন্য, অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।\nযোগাযোগের "
            "বিবরণের জন্য /admin ব্যবহার করুন।"
        ),
        "admin_panel": "👑 অ্যাডমিন প্যানেল\n\nনিচের মেনু থেকে একটি অপশন নির্বাচন করুন:",
        "user_management": "👥 ইউজার ম্যানেজমেন্ট",
        "price_management": "💰 মূল্য ম্যানেজমেন্ট",
        "communication": "📢 যোগাযোগ",
        "system_management": "⚙️ সিস্টেম ম্যানেজমেন্ট",
        "statistics": "📊 পরিসংখ্যান",
        "back": "🔙 ফিরে যান",
        "approved_users": "✅ অনুমোদিত ইউজার",
        "all_users": "👤 সমস্ত ইউজার",
        "approve_user": "➕ ইউজার অনুমোদন করুন",
        "disapprove_user": "➖ ইউজার অনুমোদন বাতিল করুন",
        "view_prices": "📋 মূল্য তালিকা দেখুন",
        "broadcast_all": "📢 সবার কাছে প্রচার করুন",
        "broadcast_approved": "✅ অনুমোদিত ইউজারদের কাছে প্রচার করুন",
        "sync_files": "🔄 ফাইল সিঙ্ক",
        "export_data": "📦 ডেটা এক্সপোর্ট করুন",
        "change_rate_limit": "⚙️ রেট লিমিট পরিবর্তন করুন",
        "bot_statistics": (
            "📊 বট পরিসংখ্যান\n\n👥 মোট ইউজার: {total_users}\n✅ অনুমোদিত ইউজার: "
            "{approved_users}\n⏳ অপেক্ষমাণ ইউজার: {pending_users}\n🔗 মোট রেফারেল: "
            "{total_referrals}\n🔢 মোট নম্বর চেক করা হয়েছে: {total_numbers_checked}\n\n"
            "📅 সর্বশেষ আপডেট: {last_updated}"
        ),
        "current_price_list": "💰 বর্তমান মূল্য তালিকা\n\n",
        "approve_user_msg": (
            "➕ ইউজার অনুমোদন করুন\n\nঅনুগ্রহ করে ইউজার ID এবং সময়কাল পাঠান ফরম্যাটে:\n"
            "/approve &lt;user_id&gt; &lt;amount&gt; &lt;unit&gt;\n\nউদাহরণ: "
            "/approve 123456789 7 days\n\nউপলব্ধ ইউনিট: hours, days, months"
        ),
        "disapprove_user_msg": (
            "➖ ইউজার অনুমোদন বাতিল করুন\n\nঅনুগ্রহ করে ইউজার ID পাঠান ফরম্যাটে:\n"
            "/disapprove &lt;user_id&gt;\n\nউদাহরণ: /disapprove 123456789"
        ),
        "broadcast_all_msg": (
            "📢 সমস্ত ইউজারদের কাছে প্রচার করুন\n\nঅনুগ্রহ করে আপনার বার্তা পাঠান "
            "ফরম্যাটে:\n/broadcast &lt;আপনার বার্তা&gt;\n\nউদাহরণ: /broadcast "
            "সবাইকে হ্যালো! বটটি 2 ঘন্টার জন্য রক্ষণাবেক্ষণে থাকবে।"
        ),
        "broadcast_approved_msg": (
            "📢 অনুমোদিত ইউজারদের কাছে প্রচার করুন\n\nঅনুগ্রহ করে আপনার বার্তা পাঠান "
            "ফরম্যাটে:\n/broadcast_approved &lt;আপনার বার্তা&gt;\n\nউদাহরণ: "
            "/broadcast_approved বটে নতুন বৈশিষ্ট্য যোগ করা হয়েছে!"
        ),
        "unauthorized": "❌ আপনি এই কমান্ড ব্যবহার করার অনুমতি পাননি।",
        "usage_approve": (
            "ব্যবহার: /approve &lt;user_id&gt; &lt;amount&gt; &lt;unit&gt;\nউদাহরণ: "
            "/approve 123456789 7 days"
        ),
        "usage_disapprove": (
            "ব্যবহার: /disapprove &lt;user_id&gt;\nউদাহরণ: /disapprove 123456789"
        ),
        "usage_setratelimit": (
            "ব্যবহার: /setratelimit &lt;seconds&gt;\nউদাহরণ: /setratelimit 600 "
            "(10 মিনিটের জন্য)"
        ),
        "usage_broadcast": "ব্যবহার: /broadcast &lt;আপনার বার্তা&gt;",
        "usage_broadcast_approved": "ব্যবহার: /broadcast_approved &lt;আপনার বার্তা&gt;",
        "invalid_unit": "❌ অবৈধ ইউনিট। 'hours', 'days', বা 'months' ব্যবহার করুন।",
        "invalid_input": (
            "❌ অবৈধ ইনপুট। অনুগ্রহ করে সঠিক ফরম্যাট ব্যবহার করুন: {format}"
        ),
        "cannot_disapprove_admin": (
            "❌ আপনি প্রধান অ্যাডমিনকে অনুমোদন বাতিল করতে পারবেন না।"
        ),
        "user_not_approved": "⚠️ ইউজার {uid} অনুমোদিত তালিকায় ছিল না।",
        "user_approved": "✅ ইউজার {uid} কে {expiry_date} পর্যন্ত অনুমোদন করা হয়েছে।",
        "user_disapproved": "✅ ইউজার {uid} এর অনুমোদন বাতিল করা হয়েছে।",
        "rate_limit_updated": (
            "✅ রেট লিমিট {seconds} সেকেন্ডে ({time_str}) আপডেট করা হয়েছে।"
        ),
        "broadcast_complete": (
            "✅ প্রচার সম্পন্ন।\n\n✅ সফল: {success_count}\n❌ ব্যর্থ: {fail_count}"
        ),
        "broadcast_approved_complete": (
            "✅ অনুমোদিত ইউজারদের কাছে প্রচার সম্পন্ন।\n\n✅ সফল: {success_count}\n❌ ব্যর্থ: {fail_count}"
        ),
        "syncing": "🔄 ডেটা ফাইল সিঙ্ক করা হচ্ছে...",
        "sync_success": "✅ সমস্ত ডেটা ফাইল সফলভাবে সিঙ্ক করা হয়েছে।",
        "sync_failed": (
            "❌ কিছু ডেটা ফাইল সিঙ্ক করতে ব্যর্থ হয়েছে। অনুগ্রহ করে লগ চেক করুন।"
        ),
        "no_approved_users": "কোনো অনুমোদিত ইউজার নেই।",
        "no_users": "এখনো কোনো ইউজার বটের সাথে ইন্টারঅ্যাক্ট করেনি।",
        "invalid_user_id": "❌ অবৈধ ইউজার ID। অনুগ্রহ করে একটি বৈধ সংখ্যাসূচক ID প্রদান করুন।",
        "list_too_long": "The list was too long and has been sent as a file.",
        "access_expired": (
            "⏳ Your access has expired.\n\nPlease contact the admin to renew your "
            "subscription.\nUse /admin for contact details."
        ),
        "access_approved": (
            "🎉 Congratulations! Your access has been approved.\n\nYou can use the bot "
            "until {expiry_date}.\n\nEnjoy the premium service!"
        ),
        "access_revoked": (
            "🚫 Your access has been revoked by the admin.\n\nPlease contact the admin "
            "for more details if you think this is a mistake.\nUse /admin for contact "
            "details."
        ),
        "referral_successful": "Referral successful! You now have {referral_count}/3 referrals.",
        "referral_earned": "Congratulations! You've earned 2 hours of access through referrals!",
        "already_used_bot": "You have already used the bot before.",
        "invalid_referral": "Invalid referral code.",
        "select_option": "Please select an option from the menu below:",
        "to_main_menu": "to Main Menu",
        "to_price_management": "to Price Management",
        "to_user_management": "to User Management",
        "to_communication": "to Communication",
        "to_system_management": "to System Management",
        "new_referral_notification": (
            "🎉 সুসংবাদ! কেউ আপনার রেফারেল লিঙ্ক ব্যবহার করে যোগ দিয়েছে।\n\nআপনার "
            "এখন {referral_count}/3 রেফারেল আছে।\n\nফ্রি অ্যাক্সেস পেতে শেয়ার করা "
            "চালিয়ে যান!"
        ),
        "cleanup_expired": "🧹 মেয়াদোত্তীর্ণ ইউজারদের পরিষ্কার করা হচ্ছে...",
        "cleanup_complete": (
            "✅ পরিষ্কার সম্পন্ন। {count} জন মেয়াদোত্তীর্ণ ইউজার মুছে ফেলা হয়েছে।"
        ),
        "user_already_approved": (
            "⚠️ ইউজার {uid} ইতিমধ্যে {expiry_date} পর্যন্ত অনুমোদিত।"
        ),
        "select_user": "একজন ইউজার নির্বাচন করুন বিস্তারিত দেখতে:",
        "user_details": (
            "👤 ইউজার বিস্তারিত\n\nID: {user_id}\nনাম: {first_name} {last_name}\n"
            "ইউজারনেম: @{username}\nভাষা: {language}\nশেষ ইন্টারঅ্যাকশন: "
            "{last_interaction}\nঅনুমোদিত: {approved}\nনম্বর চেক করা হয়েছে: "
            "{numbers_checked}\n{expiry_info}"
        ),
        "export_data_msg": (
            "📦 ডেটা এক্সপোর্ট করুন\n\nআপনার বট ডেটা ডাউনলোডের জন্য প্রস্তুত করা হচ্ছে।\n\n"
            "আপনার যদি অনেক ইউজার থাকে তবে এটি কিছুক্ষণ সময় নিতে পারে।"
        ),
        "export_complete": "✅ এক্সপোর্ট সম্পন্ন। ডেটা একটি জিপ ফাইল হিসেবে পাঠানো হয়েছে।",
        "select_user_to_approve": "অনুমোদনের জন্য একজন ইউজার নির্বাচন করুন:",
        "select_plan_for_user": "{user_name} এর জন্য একটি প্ল্যান নির্বাচন করুন:",
        "page_info": "পৃষ্ঠা {current_page}/{total_pages}",
        "no_pending_users": "অনুমোদনের জন্য কোনো অপেক্ষমাণ ইউজার নেই।",
        "change_rate_limit_msg": (
            "⚙️ রেট লিমিট পরিবর্তন করুন\n\nবর্তমান রেট লিমিট: {current_limit} "
            "সেকেন্ড ({current_time_str})\n\nঅনুগ্রহ করে কমান্ড ব্যবহার করে নতুন "
            "রেট লিমিট সেকেন্ডে পাঠান:\n/setratelimit &lt;seconds&gt;\n\nউদাহরণ: "
            "/setratelimit 600 (10 মিনিটের জন্য)"
        ),
    },
}

# --- DATA FOR FACEBOOK API ---

url = "https://www.facebook.com/ajax/login/help/identify.php?ctx=recover"
headers = {
    "accept": "*/*",
    "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.facebook.com",
    "priority": "u=1, i",
    "referer": "https://www.facebook.com/login/identify/?ctx=recover&from_login_screen=0",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "user-agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 "
        "Safari/604.1 Edg/141.0.0.0"
    ),
    "x-asbd-id": "359341",
    "x-fb-lsd": "AdE3czGo7uw",
}
cookies = {
    "datr": "5BfuaP5MJ81CQGWO4JTj_FQA",
    "wd": "980x2125",
}
base_data = {
    "jazoest": "2979",
    "lsd": "AdE3czGo7uw",
    "email": "number",
    "did_submit": "1",
    "__user": "0",
    "__a": "1",
    "__req": "7",
    "__hs": "20375.BP%3ADEFAULT.2.0...0",
    "dpr": "1",
    "__ccg": "EXCELLENT",
    "__rev": "1028355510",
    "__s": "uwimyp%3Awq8ee5%3Af3twai",
    "__hsi": "7561007094168113829",
    "__dyn": (
        "7xeUmwkHg7ebwKBAg5S1Dxu13wqovzEdEc8uxa0CEbo1nEhw2nVE4W0qa0FE2awt81s8hwGwQw4iw"
        "Bgao6C0Mo2swaO4U2zxe3C0D85a1qw8Xxm16wa-0raazo11E2ZwrU6C0hq1Iw6PG2O1TwmU3ywo81V8"
    ),
    "__hsdp": "gOMT1Cx0jK93aiyib89DxiZCmvzosxR1B04ywjofV4ciw5Ew",
    "__hblp": (
        "0Ww9W11wd20CU0xK0hS0aCw5Gw3fo0wO05Mo0Ei01pfw4Rw4ayrG3m0lK0B829wt83oUhw2sE0sdw"
    ),
    "__spin_r": "1028355510",
    "__spin_b": "trunk",
    "__spin_t": "1760434148",
}

# ---------------------------------------------------------------------------
# LOCAL FILE FUNCTIONS
# ---------------------------------------------------------------------------


async def load_config_from_file() -> None:
    global config_data
    try:
        if os.path.exists(CONFIG_FILE):
            async with aiofiles.open(CONFIG_FILE, "r") as f:
                content = await f.read()
                config_data = json.loads(content)
            logger.info("Successfully loaded config from file")
        else:
            await save_config_to_file()
    except Exception as e:
        logger.error(f"Error loading config from file: {e}")


async def save_config_to_file() -> bool:
    try:
        async with aiofiles.open(CONFIG_FILE, "w") as f:
            await f.write(json.dumps(config_data, indent=2))
        logger.info("Successfully saved config to file")
    except Exception as e:
        logger.error(f"Error saving config to file: {e}")
        return False

    try:
        await save_config_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving config to MySQL: {e}")
        return False


async def load_users_from_file() -> None:
    global approved_users
    try:
        if os.path.exists(USER_DATA_FILE):
            async with aiofiles.open(USER_DATA_FILE, "r") as f:
                content = await f.read()
                loaded_users = json.loads(content)

            temp_approved_users: dict[int, datetime | None] = {}
            for user_id_str, expiry_date in loaded_users.items():
                try:
                    user_id = int(user_id_str)
                    if expiry_date is not None:
                        temp_approved_users[user_id] = datetime.fromisoformat(
                            expiry_date
                        )
                    else:
                        temp_approved_users[user_id] = None
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting user ID {user_id_str}: {e}")

            temp_approved_users[ADMIN_ID] = None
            approved_users = temp_approved_users
            logger.info(
                "Successfully loaded %d users from file", len(approved_users)
            )
        else:
            approved_users = {ADMIN_ID: None}
            await save_users_to_file()
    except Exception as e:
        logger.error(f"Error loading users from file: {e}")
        approved_users = {ADMIN_ID: None}


async def load_all_users_from_file() -> None:
    global all_users
    try:
        if os.path.exists(ALL_USERS_FILE):
            async with aiofiles.open(ALL_USERS_FILE, "r") as f:
                content = await f.read()
                all_users = json.loads(content)
            logger.info("Successfully loaded %d all users from file", len(all_users))
        else:
            all_users = {}
            await save_all_users_to_file()
    except Exception as e:
        logger.error(f"Error loading all users from file: {e}")
        all_users = {}


async def load_referral_data_from_file() -> None:
    global referral_data
    try:
        if os.path.exists(REFERRAL_DATA_FILE):
            async with aiofiles.open(REFERRAL_DATA_FILE, "r") as f:
                content = await f.read()
                referral_data = json.loads(content)
            logger.info("Successfully loaded referral data from file")
        else:
            referral_data = {}
            await save_referral_data_to_file()
    except Exception as e:
        logger.error(f"Error loading referral data from file: {e}")
        referral_data = {}


async def load_price_list_from_file() -> None:
    global price_list
    try:
        if os.path.exists(PRICE_LIST_FILE):
            async with aiofiles.open(PRICE_LIST_FILE, "r") as f:
                content = await f.read()
                price_list = json.loads(content)
            logger.info("Successfully loaded price list from file")
        else:
            await save_price_list_to_file()
    except Exception as e:
        logger.error(f"Error loading price list from file: {e}")


async def load_user_settings_from_file() -> None:
    global user_settings
    try:
        if os.path.exists(USER_SETTINGS_FILE):
            async with aiofiles.open(USER_SETTINGS_FILE, "r") as f:
                content = await f.read()
                user_settings = json.loads(content)
            logger.info("Successfully loaded user settings from file")
        else:
            user_settings = {}
            await save_user_settings_to_file()
    except Exception as e:
        logger.error(f"Error loading user settings from file: {e}")
        user_settings = {}


async def save_users_to_file() -> bool:
    try:
        users_to_save: dict[str, str | None] = {}
        for user_id, expiry_date in approved_users.items():
            if expiry_date is None:
                users_to_save[str(user_id)] = None
            else:
                users_to_save[str(user_id)] = expiry_date.isoformat()

        async with aiofiles.open(USER_DATA_FILE, "w") as f:
            await f.write(json.dumps(users_to_save, indent=2))

        logger.info("Successfully saved %d users to file", len(approved_users))
    except Exception as e:
        logger.error(f"Error saving users to file: {e}")
        return False

    try:
        await save_users_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving users to MySQL: {e}")
        return False


async def save_all_users_to_file() -> bool:
    try:
        async with aiofiles.open(ALL_USERS_FILE, "w") as f:
            await f.write(json.dumps(all_users, indent=2))
        logger.info("Successfully saved all users to file")
    except Exception as e:
        logger.error(f"Error saving all users to file: {e}")
        return False

    try:
        await save_all_users_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving all users to MySQL: {e}")
        return False


async def save_referral_data_to_file() -> bool:
    try:
        async with aiofiles.open(REFERRAL_DATA_FILE, "w") as f:
            await f.write(json.dumps(referral_data, indent=2))
        logger.info("Successfully saved referral data to file")
    except Exception as e:
        logger.error(f"Error saving referral data to file: {e}")
        return False

    try:
        await save_referral_data_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving referral data to MySQL: {e}")
        return False


async def save_price_list_to_file() -> bool:
    try:
        async with aiofiles.open(PRICE_LIST_FILE, "w") as f:
            await f.write(json.dumps(price_list, indent=2))
        logger.info("Successfully saved price list to file")
        return True
    except Exception as e:
        logger.error(f"Error saving price list to file: {e}")
        return False


async def save_user_settings_to_file() -> bool:
    try:
        async with aiofiles.open(USER_SETTINGS_FILE, "w") as f:
            await f.write(json.dumps(user_settings, indent=2))
        logger.info("Successfully saved user settings to file")
    except Exception as e:
        logger.error(f"Error saving user settings to file: {e}")
        return False

    try:
        await save_user_settings_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving user settings to MySQL: {e}")
        return False


async def save_user_details_to_file(user_id: int, user_data: dict) -> bool:
    try:
        users_dir = os.path.join(DATA_DIR, "users")
        os.makedirs(users_dir, exist_ok=True)

        filename = os.path.join(users_dir, f"{user_id}.json")
        async with aiofiles.open(filename, "w") as f:
            await f.write(json.dumps(user_data, indent=2))

        logger.info("Successfully saved user %s details to file", user_id)
    except Exception as e:
        logger.error(f"Error saving user {user_id} details to file: {e}")
        return False

    try:
        await save_user_to_db(user_id, user_data)
        return True
    except Exception as e:
        logger.error(f"Error saving user {user_id} details to MySQL: {e}")
        return False


# ---------------------------------------------------------------------------
# MYSQL HELPERS (connection-per-operation, no global pool)
# ---------------------------------------------------------------------------


async def get_db_connection(db: str | None = None):
    """Create a new aiomysql connection (best-effort)."""
    try:
        conn = await aiomysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=db,
            autocommit=True,
        )
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to MySQL (db={db}): {e}")
        return None


async def ensure_database() -> bool:
    """Ensure that the target MySQL database exists (best-effort)."""
    conn = await get_db_connection(db=None)
    if conn is None:
        return False

    try:
        async with conn.cursor() as cur:
            await cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        logger.info("Ensured MySQL database '%s' exists", MYSQL_DB)
        return True
    except Exception as e:
        logger.error(f"Failed to create database '{MYSQL_DB}': {e}")
        return False
    finally:
        conn.close()


async def init_db() -> None:
    """Create required tables if they do not exist."""
    if not await ensure_database():
        return

    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    create_table_queries = [
        """
        CREATE TABLE IF NOT EXISTS approved_users (
            user_id BIGINT PRIMARY KEY,
            expiry_datetime DATETIME NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS all_users (
            user_id BIGINT PRIMARY KEY,
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            username VARCHAR(255),
            last_interaction DATETIME,
            numbers_checked INT DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS referral_data (
            user_id BIGINT PRIMARY KEY,
            referral_code VARCHAR(64),
            referred_by BIGINT NULL,
            referred_users_json TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id BIGINT PRIMARY KEY,
            language VARCHAR(8)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS config (
            config_key VARCHAR(64) PRIMARY KEY,
            config_value TEXT
        )
        """,
    ]

    try:
        async with conn.cursor() as cur:
            for q in create_table_queries:
                try:
                    await cur.execute(q)
                except Exception as e:
                    logger.error(f"Error creating table: {e}")
    finally:
        conn.close()


async def save_users_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    try:
        async with conn.cursor() as cur:
            try:
                await cur.execute("DELETE FROM approved_users")
                for user_id, expiry in approved_users.items():
                    expiry_str = (
                        expiry.strftime("%Y-%m-%d %H:%M:%S") if expiry is not None else None
                    )
                    await cur.execute(
                        "REPLACE INTO approved_users (user_id, expiry_datetime) "
                        "VALUES (%s, %s)",
                        (int(user_id), expiry_str),
                    )
            except Exception as e:
                logger.error(f"Error saving approved_users to MySQL: {e}")
    finally:
        conn.close()


async def save_all_users_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    try:
        async with conn.cursor() as cur:
            try:
                await cur.execute("DELETE FROM all_users")
                for user_id_str, data in all_users.items():
                    user_id = int(user_id_str)
                    first_name = data.get("first_name")
                    last_name = data.get("last_name")
                    username = data.get("username")
                    last_interaction = data.get("last_interaction")
                    numbers_checked = data.get("numbers_checked", 0)
                    await cur.execute(
                        """
                        REPLACE INTO all_users (
                            user_id, first_name, last_name, username,
                            last_interaction, numbers_checked
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            first_name,
                            last_name,
                            username,
                            last_interaction,
                            numbers_checked,
                        ),
                    )
            except Exception as e:
                logger.error(f"Error saving all_users to MySQL: {e}")
    finally:
        conn.close()


async def save_referral_data_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    try:
        async with conn.cursor() as cur:
            try:
                await cur.execute("DELETE FROM referral_data")
                for user_id_str, data in referral_data.items():
                    user_id = int(user_id_str)
                    referral_code = data.get("referral_code")
                    referred_by = data.get("referred_by")
                    referred_users = data.get("referred_users", [])
                    referred_users_json = json.dumps(referred_users)
                    await cur.execute(
                        """
                        REPLACE INTO referral_data (
                            user_id, referral_code, referred_by, referred_users_json
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            user_id,
                            referral_code,
                            int(referred_by) if referred_by else None,
                            referred_users_json,
                        ),
                    )
            except Exception as e:
                logger.error(f"Error saving referral_data to MySQL: {e}")
    finally:
        conn.close()


async def save_user_settings_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    try:
        async with conn.cursor() as cur:
            try:
                await cur.execute("DELETE FROM user_settings")
                for user_id_str, data in user_settings.items():
                    user_id = int(user_id_str)
                    language = data.get("language")
                    await cur.execute(
                        """
                        REPLACE INTO user_settings (user_id, language)
                        VALUES (%s, %s)
                        """,
                        (user_id, language),
                    )
            except Exception as e:
                logger.error(f"Error saving user_settings to MySQL: {e}")
    finally:
        conn.close()


async def save_config_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    try:
        async with conn.cursor() as cur:
            try:
                await cur.execute("DELETE FROM config")
                for key, value in config_data.items():
                    await cur.execute(
                        """
                        REPLACE INTO config (config_key, config_value)
                        VALUES (%s, %s)
                        """,
                        (key, json.dumps(value)),
                    )
            except Exception as e:
                logger.error(f"Error saving config to MySQL: {e}")
    finally:
        conn.close()


async def save_user_to_db(user_id: int, user_data: dict) -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return

    try:
        async with conn.cursor() as cur:
            try:
                first_name = user_data.get("first_name")
                last_name = user_data.get("last_name")
                username = user_data.get("username")
                last_interaction = user_data.get("last_interaction")
                numbers_checked = user_data.get("numbers_checked", 0)

                await cur.execute(
                    """
                    REPLACE INTO all_users (
                        user_id, first_name, last_name, username,
                        last_interaction, numbers_checked
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        int(user_id),
                        first_name,
                        last_name,
                        username,
                        last_interaction,
                        numbers_checked,
                    ),
                )

                language = user_data.get("language")
                if language:
                    await cur.execute(
                        """
                        REPLACE INTO user_settings (user_id, language)
                        VALUES (%s, %s)
                        """,
                        (int(user_id), language),
                    )
            except Exception as e:
                logger.error(f"Error saving single user {user_id} to MySQL: {e}")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# LANGUAGE HELPERS
# ---------------------------------------------------------------------------


def get_user_language(user_id: int) -> str:
    user_id_str = str(user_id)
    if user_id_str in user_settings:
        return user_settings[user_id_str].get("language", "en")
    return "en"


async def set_user_language(user_id: int, language: str) -> None:
    user_id_str = str(user_id)
    if user_id_str not in user_settings:
        user_settings[user_id_str] = {}
    user_settings[user_id_str]["language"] = language
    await save_user_settings_to_file()


async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Command: /lang – reopen language selection inline keyboard."""
    user = update.effective_user
    await track_user(user, update)

    keyboard = [
        [
            InlineKeyboardButton("🇺🇸 English", callback_data="set_language_en"),
            InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_language_bn"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        get_text(user.id, "welcome", first_name=user.first_name),
        reply_markup=reply_markup,
    )


def get_text(user_id: int, key: str, **kwargs) -> str:
    language = get_user_language(user_id)
    text = LANGUAGES.get(language, LANGUAGES["en"]).get(key, "")
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.error(f"Error formatting text for key '{key}': {e}")
    return text


# ---------------------------------------------------------------------------
# REFERRAL HELPERS
# ---------------------------------------------------------------------------


def generate_referral_code(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


async def get_or_create_referral_code(user_id: int) -> str:
    user_id_str = str(user_id)
    if user_id_str not in referral_data:
        referral_data[user_id_str] = {
            "referral_code": generate_referral_code(),
            "referred_by": None,
            "referred_users": [],
        }
        await save_referral_data_to_file()
    return referral_data[user_id_str]["referral_code"]


async def process_referral(
    referrer_id: int, referred_id: int, context: ContextTypes.DEFAULT_TYPE
) -> tuple[bool, str]:
    referrer_id_str = str(referrer_id)
    referred_id_str = str(referred_id)

    if referred_id_str in referral_data:
        return False, get_text(referred_id, "already_used_bot")

    if referrer_id_str not in referral_data:
        return False, get_text(referred_id, "invalid_referral")

    referral_data[referred_id_str] = {
        "referral_code": generate_referral_code(),
        "referred_by": referrer_id_str,
        "referred_users": [],
    }

    if referrer_id_str in referral_data:
        if "referred_users" not in referral_data[referrer_id_str]:
            referral_data[referrer_id_str]["referred_users"] = []
        if referred_id_str not in referral_data[referrer_id_str]["referred_users"]:
            referral_data[referrer_id_str]["referred_users"].append(referred_id_str)

    await save_referral_data_to_file()

    referral_count = len(referral_data[referrer_id_str]["referred_users"])

    await send_user_notification(
        context,
        int(referrer_id_str),
        get_text(referrer_id, "new_referral_notification", referral_count=referral_count),
    )

    if referral_count >= 3:
        expiry_date = datetime.now(timezone.utc) + timedelta(hours=2)
        approved_users[int(referrer_id_str)] = expiry_date
        await save_users_to_file()

        await send_user_notification(
            context,
            int(referrer_id_str),
            get_text(referrer_id, "referral_earned"),
        )

        return True, get_text(
            referred_id, "referral_successful", referral_count=referral_count
        )

    return True, get_text(
        referred_id, "referral_successful", referral_count=referral_count
    )


async def track_user(user, update: Update | None = None) -> None:
    user_id = str(user.id)
    if user_id not in all_users:
        all_users[user_id] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "last_interaction": datetime.now().isoformat(),
            "numbers_checked": 0,
        }
        await save_all_users_to_file()
    else:
        all_users[user_id]["last_interaction"] = datetime.now().isoformat()
        await save_all_users_to_file()


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------


async def check_facebook_number(client, phone_number: str) -> str:
    """Check a phone number against Facebook and return status string."""
    data = base_data.copy()
    data["email"] = phone_number

    try:
        response = await client.post(url, headers=headers, cookies=cookies, data=data)
        response.raise_for_status()

        text = response.text
        if text.startswith("for (;;);"):
            json_string = text[9:]
            data_json = json.loads(json_string)
        else:
            data_json = json.loads(text)

        if "jsmods" in data_json and "require" in data_json["jsmods"]:
            for requirement in data_json["jsmods"]["require"]:
                if (
                    isinstance(requirement, list)
                    and len(requirement) > 0
                    and requirement[0] == "ServerRedirect"
                ):
                    return "Found"

        if "domops" in data_json:
            for op in data_json["domops"]:
                if (
                    isinstance(op, list)
                    and len(op) > 3
                    and isinstance(op[3], dict)
                    and "__html" in op[3]
                ):
                    html_content = op[3]["__html"]
                    if "No search results" in html_content:
                        return "Not Found"

        return "Unknown Response (Possible CAPTCHA or Page Change)"

    except httpx.RequestError as e:
        logger.warning(f"httpx RequestError for {phone_number}: {e}")
        return f"Error: {e}"
    except json.JSONDecodeError:
        logger.warning(
            f"json.JSONDecodeError for {phone_number}: (Possibly Blocked)"
        )
        return "Error: Invalid JSON (Possibly Blocked)"
    except Exception as e:
        logger.error(f"Unexpected error in check_facebook_number for {phone_number}: {e}")
        return f"Error: {e}"


async def send_user_notification(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str
) -> None:
    """Send a notification to a user, ignoring common Telegram errors."""
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        msg = str(e)
        if "Chat not found" in msg or "chat not found" in msg:
            logger.debug(
                "Notification skipped for user %s: chat not found / not started",
                user_id,
            )
        elif "bot was blocked by the user" in msg:
            logger.debug("Notification skipped for user %s: bot blocked", user_id)
        else:
            logger.error("Could not send notification to user %s: %s", user_id, e)


def is_user_approved(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if user_id == ADMIN_ID:
        return True

    if user_id not in approved_users:
        return False

    expiry_date = approved_users.get(user_id)
    if expiry_date is None:
        return False

    if datetime.now(timezone.utc) > expiry_date:
        del approved_users[user_id]
        logger.info("User %s access expired", user_id)
        asyncio.create_task(
            send_user_notification(context, user_id, get_text(user_id, "access_expired"))
        )
        asyncio.create_task(save_users_to_file())
        return False

    return True


def check_rate_limit(user_id: int) -> tuple[bool, str | None]:
    current_time = datetime.now(timezone.utc)
    rate_limit_seconds = config_data.get("rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS)

    if user_id in user_last_request:
        last_request_time = user_last_request[user_id]
        diff = (current_time - last_request_time).total_seconds()
        if diff < rate_limit_seconds:
            remaining = int(rate_limit_seconds - diff)
            minutes = remaining // 60
            seconds = remaining % 60
            if minutes > 0:
                time_str = (
                    f"{minutes} minute{'s' if minutes > 1 else ''} and "
                    f"{seconds} second{'s' if seconds != 1 else ''}"
                )
            else:
                time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
            return False, time_str

    user_last_request[user_id] = current_time
    return True, None


async def cleanup_expired_users() -> int:
    """Remove expired users from the approved list."""
    global approved_users
    now = datetime.now(timezone.utc)
    expired = [
        uid
        for uid, expiry in list(approved_users.items())
        if uid != ADMIN_ID and expiry is not None and now > expiry
    ]

    if not expired:
        return 0

    for uid in expired:
        approved_users.pop(uid, None)
        logger.info("Removed expired user %s", uid)

    await save_users_to_file()
    return len(expi_coderenewd</)
)


async def auto_cleanup_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    while True:
        try:
            removed = await cleanup_expired_users()
            if removed > 0:
                logger.info("Auto cleanup removed %d users", removed)
        except Exception as e:
            logger.error(f"Error in auto cleanup task: {e}")
        await asyncio.sleep(AUTO_CLEANUP_INTERVAL)


async def export_bot_data() -> io.BytesIO | None:
    """Export all bot data as an in-memory zip file."""
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            users_to_save = {
                str(uid): (expiry.isoformat() if expiry else None)
                for uid, expiry in approved_users.items()
            }
            zf.writestr("approved_users.json", json.dumps(users_to_save, indent=2))
            zf.writestr("all_users.json", json.dumps(all_users, indent=2))
            zf.writestr("referral_data.json", json.dumps(referral_data, indent=2))
            zf.writestr("price_list.json", json.dumps(price_list, indent=2))
            zf.writestr("user_settings.json", json.dumps(user_settings, indent=2))
            zf.writestr("config.json", json.dumps(config_data, indent=2))

            users_dir = os.path.join(DATA_DIR, "users")
            if os.path.exists(users_dir):
                for filename in os.listdir(users_dir):
                    if filename.endswith(".json"):
                        path = os.path.join(users_dir, filename)
                        async with aiofiles.open(path, "r") as f:
                            zf.writestr(f"users/{filename}", await f.read())

            total_numbers_checked = sum(
                user.get("numbers_checked", 0) for user in all_users.values()
            )
            summary = {
                "export_date": datetime.now().isoformat(),
                "total_users": len(all_users),
                "approved_users": max(len(approved_users) - 1, 0),
                "total_referrals": sum(
                    len(data.get("referred_users", []))
                    for data in referral_data.values()
                ),
                "total_numbers_checked": total_numbers_checked,
                "price_list": price_list,
                "config": config_data,
            }
            zf.writestr("summary.json", json.dumps(summary, indent=2))

        zip_buffer.seek(0)
        return zip_buffer
    except Exception as e:
        logger.error(f"Error exporting bot data: {e}")
        return None


def remove_html_tags(text: str) -> str:
    clean_re = re.compile("<.*?>")
    return re.sub(clean_re, "", text)


# ---------------------------------------------------------------------------
# TELEGRAM HANDLERS
# ---------------------------------------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start and show language selection if not set."""
    user = update.effective_user
    await track_user(user, update)

    user_id_str = str(user.id)

    if user_id_str in user_settings and "language" in user_settings[user_id_str]:
        language = user_settings[user_id_str]["language"]

        # Process referral if present
        referral_code = context.args[0] if context.args else None
        if referral_code:
            referrer_id = None
            for uid, data in referral_data.items():
                if data.get("referral_code") == referral_code:
                    referrer_id = uid
                    break
            if referrer_id and referrer_id != user_id_str:
                success, _ = await process_referral(
                    int(referrer_id), user.id, context
                )
                if success:
                    await update.message.reply_text(
                        get_text(user.id, "referral_successful", referral_count=1)
                    )

        user_referral_code = await get_or_create_referral_code(user.id)

        user_data = {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "language_code": user.language_code,
            "is_bot": user.is_bot,
            "last_interaction": datetime.now().isoformat(),
            "approved": user.id in approved_users,
            "referral_code": user_referral_code,
            "language": language,
        }
        if user.id in approved_users and approved_users[user.id] is not None:
            user_data["expiry_date"] = approved_users[user.id].isoformat()

        await save_user_details_to_file(user.id, user_data)

        await update.message.reply_html(
            get_text(user.id, "language_selected", first_name=user.first_name)
        )
        await update.message.reply_text(get_text(user.id, "example"))
    else:
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data="set_language_en"),
                InlineKeyboardButton("🇧🇩 বাংলা", callback_data="set_language_bn"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if context.args:
            context.user_data["pending_referral"] = context.args[0]

        await update.message.reply_html(
            get_text(user.id, "welcome", first_name=user.first_name),
            reply_markup=reply_markup,
        )


async def admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await track_user(user, update)

    contact_text = get_text(
        user.id,
        "admin_contact",
        admin_name=ADMIN_FIRST_NAME,
        admin_id=ADMIN_ID,
        admin_username=ADMIN_USERNAME,
    )

    # Add an inline button to open the admin panel quickly (only visible to admin)
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("⚙️ Open Admin Panel", callback_data="admin_open_panel")]
        ]
        await update.message.reply_html(
            contact_text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_html(contact_text):
        text += (
            f"🔹 <b>{value['duration']}</b>: "
            f"{value['price_bdt']} BDT / {value['price_usd']} USD\n"
        )
    text += get_text(user.id, "payment_methods")
    await update.message.reply_html(text)


async def show_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin commands as an inline button menu."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text(get_text(user.id, "unauthorized"))
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Approved users", callback_data="admin_list_approved"),
            InlineKeyboardButton("📊 Stats", callback_data="admin_list_all"),
        ],
        [
            InlineKeyboardButton("➕ Approve user", callback_data="admin_help_approve"),
            InlineKeyboardButton("➖ Disapprove user", callback_data="admin_help_disapprove"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast all", callback_data="admin_help_broadcast"),
            InlineKeyboardButton(
                "📢 Approved only", callback_data="admin_help_broadcast_approved"
            ),
        ],
        [
            InlineKeyboardButton("⚙️ Rate limit", callback_data="admin_help_setratelimit"),
            InlineKeyboardButton("🔄 Sync files", callback_data="admin_do_sync"),
        ],
        [
            InlineKeyboardButton("🧹 Cleanup expired", callback_data="admin_do_cleanup"),
            InlineKeyboardButton("📦 Export data", callback_data="admin_do_export"),
        ],
        [
            InlineKeyboardButton("💰 Price list", callback_data="admin_show_pricelist"),
        ],
    ]
    msg = get_text(user.id, "admin_panel")
    await update.message.reply_html(msg, reply_markup=InlineKeyboardMarkup(keyboa_coderdnew)</)
async def referral_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current referral status and inline share button."""
    user = update.effective_user
    await track_user(user, update)

    user_id_str = str(user.id)
    referral_code = await get_or_create_referral_code(user.id)

    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"

    referral_count = 0
    if user_id_str in referral_data:
        referral_count = len(referral_data[user_id_str].get("referred_users", []))

    has_access = is_user_approved(user.id, context)

    message = get_text(
        user.id,
        "referral_status",
        referral_code=referral_code,
        referral_link=referral_link,
        referral_count=referral_count,
    )

    if has_access:
        expiry_date = approved_users.get(user.id)
        if expiry_date:
            expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S UTC")
            message += get_text(user.id, "access_until", expiry_date=expiry_str)
        else:
            message += get_text(user.id, "permanent_access")
    else:
        remaining = 3 - referral_count
        message += get_text(user.id, "refer_needed", remaining=remaining)

    keyboard = [
        [
            InlineKeyboardButton(
                "Share Referral Link",
                url=(
                    "https://t.me/share/url?"
                    f"url={referral_link}&text=Join this amazing Facebook Number "
                    "Checker Bot and get free access!"
                ),
            )
        ]
    ]
    await update.message.reply_html(message, reply_markup=InlineKeyboardMarkup(keyboard))


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not query.data:
        return

    # Open admin panel from inline button
    if query.data == "admin_open_panel":
        # Reuse the /cmd handler logic to show the inline admin menu
        fake_update = Update(update.update_id, message=update.effective_message)
        await show_admin_commands(fake_update, cont_codeexnewt</)

        await set_user_language(query.from_user.id, language)

        referral_code = context.user_data.pop("pending_referral", None)
        if referral_code:
            referrer_id = None
            for uid, data in referral_data.items():
                if data.get("referral_code") == referral_code:
                    referrer_id = uid
                    break
            if referrer_id and referrer_id != str(query.from_user.id):
                success, _ = await process_referral(
                    int(referrer_id), query.from_user.id, context
                )
                if success:
                    await query.edit_message_text(
                        get_text(
                            query.from_user.id,
                            "referral_successful",
                            referral_count=1,
                        )
                    )
                    return

        user_referral_code = await get_or_create_referral_code(query.from_user.id)
        user_data = {
            "id": query.from_user.id,
            "first_name": query.from_user.first_name,
            "last_name": query.from_user.last_name,
            "username": query.from_user.username,
            "language_code": query.from_user.language_code,
            "is_bot": query.from_user.is_bot,
            "last_interaction": datetime.now().isoformat(),
            "approved": query.from_user.id in approved_users,
            "referral_code": user_referral_code,
            "language": language,
        }
        if query.from_user.id in approved_users and approved_users[query.from_user.id]:
            user_data["expiry_date"] = approved_users[query.from_user.id].isoformat()

        await save_user_details_to_file(query.from_user.id, user_data)

        await query.edit_message_text(
            get_text(
                query.from_user.id,
                "language_selected",
                first_name=query.from_user.first_name,
            )
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text(query.from_user.id, "example"),
        )
        return

    # Normal user buttons
    if query.data == "buy_online":
        await query.edit_message_text(
            get_text(query.from_user.id, "buy_online_msg"), parse_mode="HTML"
        )
        return

    if query.data == "refer":
        user_id_str = str(query.from_user.id)
        referral_code = await get_or_create_referral_code(query.from_user.id)
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"

        referral_count = 0
        if user_id_str in referral_data:
            referral_count = len(referral_data[user_id_str].get("referred_users", []))

        message = get_text(
            query.from_user.id,
            "refer_link",
            referral_link=referral_link,
            referral_count=referral_count,
        )
        if referral_count >= 3:
            message += get_text(query.from_user.id, "refer_earned")
        else:
            remaining = 3 - referral_count
            message += get_text(query.from_user.id, "refer_needed", remaining=remaining)

        keyboard = [
            [
                InlineKeyboardButton(
                    "Share Referral Link",
                    url=(
                        "https://t.me/share/url?"
                        f"url={referral_link}&text=Join this amazing Facebook "
                        "Number Checker Bot and get free access!"
                    ),
                )
            ]
        ]
        await query.edit_message_text(
            text=message, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Admin inline menu actions
    if query.data.startswith("admin_"):
        if query.from_user.id != ADMIN_ID:
            await query.edit_message_text(
                get_text(query.from_user.id, "unauthorized")
            )
            return

        data = query.data

        if data == "admin_list_approved":
            # Show approved users list
            if not approved_users:
                await query.edit_message_text(
                    get_text(query.from_user.id, "no_approved_users")
                )
                return

            text = get_text(query.from_user.id, "approved_users") + "\n\n"
            for uid, expiry in approved_users.items():
                if uid == ADMIN_ID:
                    text += f"👑 <code>{uid}</code> (Admin - Permanent)\n"
                else:
                    if expiry is None:
                        text += f"👤 <code>{uid}</code> - Permanent Access\n"
                    else:
                        expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
                        text += (
                            f"👤 <code>{uid}</code> - Expires: <b>{expiry_str}</b>\n"
                        )
            await query.edit_message_text(text, parse_mode="HTML")
            return

        if data == "admin_list_all":
            total_users = len(all_users)
            approved_count = len(approved_users) - 1
            pending_users = total_users - approved_count
            total_referrals = sum(
                len(d.get("referred_users", [])) for d in referral_data.values()
            )
            total_numbers_checked = sum(
                u.get("numbers_checked", 0) for u in all_users.values()
            )
            stats_text = get_text(
                query.from_user.id,
                "bot_statistics",
                total_users=total_users,
                approved_users=approved_count,
                pending_users=pending_users,
                total_referrals=total_referrals,
                total_numbers_checked=total_numbers_checked,
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
            await query.edit_message_text(stats_text)
            return

        if data == "admin_help_approve":
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_approve"), parse_mode="HTML"
            )
            return

        if data == "admin_help_disapprove":
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_disapprove"), parse_mode="HTML"
            )
            return

        if data == "admin_help_broadcast":
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_broadcast"), parse_mode="HTML"
            )
            return

        if data == "admin_help_broadcast_approved":
            await query.edit_message_text(
                get_text(
                    query.from_user.id, "usage_broadcast_approved"
                ),
                parse_mode="HTML",
            )
            return

        if data == "admin_help_setratelimit":
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_setratelimit"),
                parse_mode="HTML",
            )
            return

        if data == "admin_do_sync":
            await query.edit_message_text(get_text(query.from_user.id, "syncing"))
            await load_users_from_file()
            await load_referral_data_from_file()
            await load_all_users_from_file()
            await load_price_list_from_file()
            await load_user_settings_from_file()
            await load_config_from_file()

            ok_users = await save_users_to_file()
            ok_ref = await save_referral_data_to_file()
            ok_all = await save_all_users_to_file()
            ok_price = await save_price_list_to_file()
            ok_settings = await save_user_settings_to_file()
            ok_config = await save_config_to_file()

            if all([ok_users, ok_ref, ok_all, ok_price, ok_settings, ok_config]):
                await query.edit_message_text(
                    get_text(query.from_user.id, "sync_success")
                )
            else:
                await query.edit_message_text(
                    get_text(query.from_user.id, "sync_failed")
                )
            return

        if data == "admin_do_cleanup":
            await query.edit_message_text(
                get_text(query.from_user.id, "cleanup_expired")
            )
            removed = await cleanup_expired_users()
            await query.edit_message_text(
                get_text(query.from_user.id, "cleanup_complete", count=removed)
            )
            return

        if data == "admin_do_export":
            await query.edit_message_text(
                get_text(query.from_user.id, "export_data_msg")
            )
            zip_buffer = await export_bot_data()
            if zip_buffer:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"bot_data_{ts}.zip"
                await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=zip_buffer,
                    filename=filename,
                    caption=get_text(query.from_user.id, "export_complete"),
                )
                await query.edit_message_text(
                    get_text(query.from_user.id, "export_complete")
                )
            else:
                await query.edit_message_text(
                    "❌ Failed to export data. Please check the logs."
                )
            return

        if data == "admin_show_pricelist":
            text = get_text(query.from_user.id, "current_price_list")
            for _, value in price_list.items():
                text += (
                    f"🔹 <b>{value['duration']}</b>: "
                    f"{value['price_bdt']} BDT / {value['price_usd']} USD\n"
                )
            await query.edit_message_text(text, parse_mode="HTML")
            return


# ---------------------------------------------------------------------------
# ADMIN COMMANDS
# ---------------------------------------------------------------------------


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not query.data:
        return

    # Open admin panel from inline button
    if query.data == "admin_open_panel":
        await show_admin_commands(update, context)
        return

    # Language selection buttons
    if query.data.startswith("set_language_"):
        language = query.data.replace("set_language_", "")
        await set_user_language(query.from_user.id, language)

        referral_code = context.user_data.pop("pending_referral", None)
        if referral_code:
            referrer_id = None
            for uid, data in referral_data.items():
                if data.get("referral_code") == referral_code:
                    referrer_id = uid
                    break
            if referrer_id and referrer_id != str(query.from_user.id):
                success, _ = await process_referral(
                    int(referrer_id), query.from_user.id, context
                )
                if success:
                    await query.edit_message_text(
                        get_text(
                            query.from_user.id,
                            "referral_successful",
                            referral_count=1,
                        )
                    )
                    return

        user_referral_code = await get_or_create_referral_code(query.from_user.id)
        user_data = {
            "id": query.from_user.id,
            "first_name": query.from_user.first_name,
            "last_name": query.from_user.last_name,
            "username": query.from_user.username,
            "language_code": query.from_user.language_code,
            "is_bot": query.from_user.is_bot,
            "last_interaction": datetime.now().isoformat(),
            "approved": query.from_user.id in approved_users,
            "referral_code": user_referral_code,
            "language": language,
        }
        if query.from_user.id in approved_users and approved_users[query.from_user.id]:
            user_data["expiry_date"] = approved_users[query.from_user.id].isoformat()

        await save_user_details_to_file(query.from_user.id, user_data)

        await query.edit_message_text(
            get_text(
                query.from_user.id,
                "language_selected",
                first_name=query.from_user.first_name,
            )
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text(query.from_user.id, "example"),
        )
        return

    # Normal user buttons
    if query.data == "buy_online":
        await query.edit_message_text(
            get_text(query.from_user.id, "buy_online_msg"), parse_mode="HTML"
        )
        return

    if query.data == "refer":
        user_id_str = str(query.from_user.id)
        referral_code = await get_or_create_referral_code(query.from_user.id)
        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"

        referral_count = 0
        if user_id_str in referral_data:
            referral_count = len(referral_data[user_id_str].get("referred_users", []))

        message = get_text(
            query.from_user.id,
            "refer_link",
            referral_link=referral_link,
            referral_count=referral_count,
        )
        if referral_count >= 3:
            message += get_text(query.from_user:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if len(context.args) != 3:
        await update.message.reply_html(get_text(update.effective_user.id, "usage_approve"))
        return

    try:
        user_id_to_approve = int(context.args[0])
        amount = int(context.args[1])
        unit = context.args[2].lower()

        if user_id_to_approve in approved_users:
            expiry_date = approved_users[user_id_to_approve]
            if expiry_date is None:
                await update.message.reply_html(
                    get_text(
                        update.effective_user.id,
                        "user_already_approved",
                        uid=user_id_to_approve,
                        expiry_date="Permanent",
                    )
                )
                return
            else:
                expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S UTC")
                await update.message.reply_html(
                    get_text(
                        update.effective_user.id,
                        "user_already_approved",
                        uid=user_id_to_approve,
                        expiry_date=expiry_str,
                    )
                )
                return

        if unit.startswith("hour"):
            expiry_date = datetime.now(timezone.utc) + timedelta(hours=amount)
        elif unit.startswith("day"):
            expiry_date = datetime.now(timezone.utc) + timedelta(days=amount)
        elif unit.startswith("month"):
            expiry_date = datetime.now(timezone.utc) + timedelta(days=amount * 30)
        else:
            await update.message.reply_text(get_text(update.effective_user.id, "invalid_unit"))
            return

        approved_users[user_id_to_approve] = expiry_date
        expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M:%S UTC")

        await save_users_to_file()

        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "user_approved",
                uid=user_id_to_approve,
                expiry_date=expiry_str,
            )
        )

        user_id_str = str(user_id_to_approve)
        if user_id_str in all_users:
            await send_user_notification(
                context,
                user_id_to_approve,
                get_text(
                    user_id_to_approve, "access_approved", expiry_date=expiry_str
                ),
            )
    except (ValueError, IndexError):
        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "invalid_input",
                format=get_text(update.effective_user.id, "usage_approve"),
            )
        )


async def disapprove(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not context.args:
        await update.message.reply_html(get_text(update.effective_user.id, "usage_disapprove"))
        return

    try:
        user_id_to_disapprove = int(context.args[0])
        if user_id_to_disapprove == ADMIN_ID:
            await update.message.reply_text(
                get_text(update.effective_user.id, "cannot_disapprove_admin")
            )
            return

        if user_id_to_disapprove in approved_users:
            del approved_users[user_id_to_disapprove]
            await save_users_to_file()

            await update.message.reply_html(
                get_text(
                    update.effective_user.id,
                    "user_disapproved",
                    uid=user_id_to_disapprove,
                )
            )

            user_id_str = str(user_id_to_disapprove)
            if user_id_str in all_users:
                await send_user_notification(
                    context,
                    user_id_to_disapprove,
                    get_text(user_id_to_disapprove, "access_revoked"),
                )
        else:
            await update.message.reply_html(
                get_text(
                    update.effective_user.id,
                    "user_not_approved",
                    uid=user_id_to_disapprove,
                )
            )
    except (ValueError, IndexError):
        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "invalid_input",
                format=get_text(update.effective_user.id, "usage_disapprove"),
            )
        )


async def set_rate_limit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not context.args:
        await update.message.reply_html(get_text(update.effective_user.id, "usage_setratelimit"))
        return

    try:
        seconds = int(context.args[0])
        if seconds < 10:
            await update.message.reply_text("❌ Rate limit must be at least 10 seconds.")
            return

        config_data["rate_limit_seconds"] = seconds
        await save_config_to_file()

        minutes = seconds // 60
        secs = seconds % 60
        if minutes > 0:
            time_str = (
                f"{minutes} minute{'s' if minutes > 1 else ''} and "
                f"{secs} second{'s' if secs != 1 else ''}"
            )
        else:
            time_str = f"{secs} second{'s' if secs != 1 else ''}"

        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "rate_limit_updated",
                seconds=seconds,
                time_str=time_str,
            )
        )
    except (ValueError, IndexError):
        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "invalid_input",
                format=get_text(update.effective_user.id, "usage_setratelimit"),
            )
        )


async def cleanup_expired(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    await update.message.reply_text(get_text(update.effective_user.id, "cleanup_expired"))
    removed = await cleanup_expired_users()
    await update.message.reply_html(
        get_text(update.effective_user.id, "cleanup_complete", count=removed)
    )


async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    await update.message.reply_text(get_text(update.effective_user.id, "export_data_msg"))
    zip_buffer = await export_bot_data()
    if zip_buffer:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bot_data_{timestamp}.zip"
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=zip_buffer,
            filename=filename,
            caption=get_text(update.effective_user.id, "export_complete"),
        )
    else:
        await update.message.reply_text("❌ Failed to export data. Please check the logs.")


async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not approved_users:
        await update.message.reply_text(get_text(update.effective_user.id, "no_approved_users"))
        return

    text = get_text(update.effective_user.id, "approved_users") + "\n\n"
    for uid, expiry in approved_users.items():
        if uid == ADMIN_ID:
            text += f"👑 <code>{uid}</code> (Admin - Permanent)\n"
        else:
            if expiry is None:
                text += f"👤 <code>{uid}</code> - Permanent Access\n"
            else:
                expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
                text += (
                    f"👤 <code>{uid}</code> - Expires: <b>{expiry_str}</b>\n"
                )
    await update.message.reply_html(text)


async def list_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not all_users:
        await update.message.reply_text(get_text(update.effective_user.id, "no_users"))
        return

    text = (
        get_text(update.effective_user.id, "all_users", total_users=len(all_users))
        + "\n\n"
    )

    for uid, user_data in all_users.items():
        name = html.escape(user_data.get("first_name", "Unknown"))
        username = html.escape(user_data.get("username", "No username"))
        numbers_checked = user_data.get("numbers_checked", 0)

        if uid == str(ADMIN_ID):
            text += (
                f"👑 <code>{uid}</code> - {name} (@{username}) - "
                f"Admin - Checked: {numbers_checked}\n"
            )
        elif int(uid) in approved_users:
            expiry = approved_users[int(uid)]
            if expiry is None:
                text += (
                    f"✅ <code>{uid}</code> - {name} (@{username}) - "
                    f"Permanent access - Checked: {numbers_checked}\n"
                )
            else:
                expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
                text += (
                    f"✅ <code>{uid}</code> - {name} (@{username}) - "
                    f"Approved until {expiry_str} - Checked: {numbers_checked}\n"
                )
        else:
            text += (
                f"👤 <code>{uid}</code> - {name} (@{username}) - "
                f"Not approved - Checked: {numbers_checked}\n"
            )

    if len(text) > 4000:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"all_users_{ts}.txt"
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(text)
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(filename, "rb"),
            caption="List of all users who have interacted with the bot.",
        )
        os.remove(filename)
    else:
        await update.message.reply_html(text)


async def show_price_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await track_user(user, update)

    text = get_text(userext(get_text(update.effective_user.id, "unauthorized"))
        return

    text = get_text(update.effective_user.id, "current_price_list")
    for _, value in price_list.items():
        text += (
            f" <<bb>{value['duration}<//bb>: "
            f"{alue['price_bdt']} BDT / {value['price_usd']} USD\n"
        )
    await update.message.reply_html(text)


async def sync_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    await update.message.reply_text(get_text(update.effective_user.id, "syncing"))

    await load_users_from_file()
    await load_referral_data_from_file()
    await load_all_users_from_file()
    await load_price_list_from_file()
    await load_user_settings_from_file()
    await load_config_from_file()

    ok_users = await save_users_to_file()
    ok_ref = await save_referral_data_to_file()
    ok_all = await save_all_users_to_file()
    ok_price = await save_price_list_to_file()
    ok_settings = await save_user_settings_to_file()
    ok_config = await save_config_to_file()

    if all([ok_users, ok_ref, ok_all, ok_price, ok_settings, ok_config]):
        await update.message.reply_text(get_text(update.effective_user.id, "sync_success"))
    else:
        await update.message.reply_text(get_text(update.effective_user.id, "sync_failed"))


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not context.args:
        await update.message.reply_html(get_text(update.effective_user.id, "usage_broadcast"))
        return

    message_to_broadcast = " ".join(context.args)
    success_count = 0
    fail_count = 0

    for user_id in all_users.keys():
        try:
            await context.bot.send_message(
                chat_id=int(user_id), text=message_to_broadcast, parse_mode="HTML"
            )
            success_count += 1
        except Exception as e:
            logger.error("Failed to broadcast to %s: %s", user_id, e)
            fail_count += 1

    await update.message.reply_html(
        get_text(
            update.effective_user.id,
            "broadcast_complete",
            success_count=success_count,
            fail_count=fail_count,
        )
    )


async def broadcast_approved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not context.args:
        await update.message.reply_html(
            get_text(update.effective_user.id, "usage_broadcast_approved")
        )
        return

    message_to_broadcast = " ".join(context.args)
    success_count = 0
    fail_count = 0

    for user_id in approved_users.keys():
        try:
            await context.bot.send_message(
                chat_id=user_id, text=message_to_broadcast, parse_mode="HTML"
            )
            success_count += 1
        except Exception as e:
            logger.error("Failed to broadcast to %s: %s", user_id, e)
            fail_count += 1

    await update.message.reply_html(
        get_text(
            update.effective_user.id,
            "broadcast_approved_complete",
            success_count=success_count,
            fail_count=fail_count,
        )
    )


# ---------------------------------------------------------------------------
# MESSAGE HANDLER
# ---------------------------------------------------------------------------


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id

    await track_user(user, update)

    user_data = {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "language_code": user.language_code,
        "is_bot": user.is_bot,
        "last_interaction": datetime.now().isoformat(),
        "approved": user_id in approved_users,
        "language": get_user_language(user_id),
    }
    if user_id in approved_users and approved_users[user_id] is not None:
        user_data["expiry_date"] = approved_users[user_id].isoformat()

    await save_user_details_to_file(user_id, user_data)

    if not is_user_approved(user_id, context):
        referral_code = await get_or_create_referral_code(user_id)

        if str(user_id) in referral_data:
            referral_count = len(referral_data[str(user_id)].get("referred_users", []))
        else:
            referral_count = 0

        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buy_online"), callback_data="buy_online")],
            [InlineKeyboardButton(get_text(user_id, "refer_earn"), callback_data="refer")],
        ]
        await update.message.reply_html(
            get_text(user_id, "access_denied", uid=user_id),
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    if user_id != ADMIN_ID:
        allowed, remaining = check_rate_limit(user_id)
        if not allowed:
            rate_limit_seconds = config_data.get(
                "rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS
            )
            await update.message.reply_html(
                get_text(
                    user_id, "rate_limit", remaining_time=remaining, time_limit=rate_limit_seconds
                )
            )
            return

    processing_message = await update.message.reply_text(
        get_text(user_id, "processing")
    )

    phone_numbers = [
        line.strip().lstrip("- ").strip()
        for line in update.message.text.splitlines()
        if line.strip().lstrip("- ").strip()
    ]
    if not phone_numbers:
        await processing_message.edit_text(get_text(user_id, "no_numbers"))
        return

    found_numbers: list[str] = []
    not_found_numbers: list[str] = []
    error_numbers: list[tuple[str, str]] = []

    async with httpx.AsyncClient() as client:
        tasks = [check_facebook_number(client, n) for n in phone_numbers]
        results = await asyncio.gather(*tasks)

    for number, status in zip(phone_numbers, results):
        if status == "Found":
            found_numbers.append(number)
        elif status == "Not Found":
            not_found_numbers.append(number)
        else:
            error_numbers.append((number, status))

    user_id_str = str(user_id)
    if user_id_str in all_users:
        all_users[user_id_str]["numbers_checked"] = (
            all_users[user_id_str].get("numbers_checked", 0) + len(phone_numbers)
        )
        await save_all_users_to_file()

    response_text = get_text(user_id, "check_complete")

    if found_numbers:
        response_text += get_text(user_id, "found_numbers")
        for n in found_numbers:
            response_text += f"  <code>{n}</code>\n"
        response_text += "\n"
    if not_found_numbers:
        response_text += get_text(user_id, "not_found_numbers")
        for n in not_found_numbers:
            response_text += f"  <code>{n}</code>\n"
        response_text += "\n"
    if error_numbers:
        response_text += get_text(user_id, "errors_unknown")
        for n, err in error_numbers:
            response_text += f"  <code>{n}</code>: {err}\n"
        response_text += "\n"

    if not (found_numbers or not_found_numbers or error_numbers):
        response_text = get_text(user_id, "no_valid_numbers")

    if len(response_text) > 3000 or len(phone_numbers) > 50:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{ts}.txt"
            clean_text = remove_html_tags(response_text)
            async with aiofiles.open(filename, "w", encoding="utf-8") as f:
                await f.write(clean_text)

            caption = (
                f"✅ Check Complete!\n\nFound: {len(found_numbers)}\n"
                f"Not Found: {len(not_found_numbers)}\nErrors: {len(error_numbers)}"
            )
            with open(filename, "rb") as f_sync:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=f_sync, caption=caption
                )
            os.remove(filename)
            await processing_message.delete()
            return
        except Exception as e:
            logger.error(f"Failed to create or send file: {e}")
            await processing_message.edit_text(
                "❌ An error occurred while creating the result file. Please try again."
            )
            return
    else:
        try:
            await processing_message.edit_text(response_text, parse_mode="HTML")
        except BadRequest as e:
            if "message is not modified" in str(e):
                pass
            else:
                logger.error(f"Failed to edit message: {e}")
                await processing_message.edit_text(
                    "❌ An error occurred while formatting the results. Please check the logs."
                )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await processing_message.edit_text(
                "❌ An error occurred while formatting the results. Please check the logs."
            )


# ---------------------------------------------------------------------------
# ERROR HANDLER, STARTUP, MAIN
# ---------------------------------------------------------------------------


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update: %s", context.error)
    try:
        if update and hasattr(update, "effective_user"):
            user_id = update.effective_user.id  # type: ignore[attr-defined]
            await context.bot.send_message(
                chat_id=user_id,
                text="An error occurred. Please try again later.",
                parse_mode="HTML",
            )
    except Exception:
        pass


async def load_all_data() -> None:
    await asyncio.gather(
        load_config_from_file(),
        load_users_from_file(),
        load_referral_data_from_file(),
        load_all_users_from_file(),
        load_price_list_from_file(),
        load_user_settings_from_file(),
    )
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Error initialising MySQL database: {e}")


def main() -> None:
    """Entry point: load data, then start the Telegram bot."""
    asyncio.run(load_all_data())
    asyncio.run(cleanup_expired_users())

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_error_handler(error_handler)

    # Public commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_contact))
    application.add_handler(CommandHandler("cmd", show_admin_commands))
    application.add_handler(CommandHandler("referral", referral_status))
    application.add_handler(CommandHandler("price", show_price_list))
    application.add_handler(CommandHandler("lang", change_language))

    # Admin commands
    application.add_handler(CommandHandler("approve", approve))
    application.add_handler(CommandHandler("disapprove", disapprove))
    application.add_handler(CommandHandler("approved", list_approved))
    application.add_handler(CommandHandler("allusers", list_all_users))
    application.add_handler(CommandHandler("pricelist", show_price_list_admin))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("broadcast_approved", broadcast_approved))
    application.add_handler(CommandHandler("sync", sync_files))
    application.add_handler(CommandHandler("cleanup", cleanup_expired))
    application.add_handler(CommandHandler("export", export_data))
    application.add_handler(CommandHandler("setratelimit", set_rate_limit))

    # Callback query handler (inline buttons)
    application.add_handler(CallbackQueryHandler(button_callback))

    # Text messages handler
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()