from __future__ import annotations

import asyncio
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

# --- LOCAL FILE CONFIGURATION ---

DATA_DIR = "bot_data"
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

# --- LANGUAGE STRINGS (EN & BN) ---

LANGUAGES = {
    "en": {
        "welcome": (
            "👋 Hi {first_name}!\n\n"
            "Welcome to the Facebook Number Checker Bot.\n\n"
            "Please select your preferred language:"
        ),
        "language_selected": (
            "✅ Language has been set to English.\n\n"
            "This is a premium service. Send me a list of phone numbers to check.\n\n"
            "🔐 Need access? Use /admin to contact support."
        ),
        "example": "Example:\n+8801712345678\n+8801812345678",
        "access_denied": (
            "🚫 Access Denied!\n\n"
            "This is a premium service for paid users only. It runs on a VPS with "
            "premium proxies to avoid rate limitations.\n\n"
            "Your User ID: {uid}\n\n"
            "Please contact the admin to get access.\n"
            "Use /admin to get support contact."
        ),
        "buy_online": "Buy Online (Coming Soon)",
        "refer_earn": "Refer & Earn Free Access",
        "buy_online_msg": (
            "🛒 Buy Online\n\n"
            "Online payment option is coming soon!\n\n"
            "For now, please contact the admin directly to purchase access.\n"
            "Use /admin to get contact details."
        ),
        "refer_link": (
            "🔗 Your Referral Link\n\n"
            "Share this link with your friends:\n{referral_link}\n\n"
            "Referrals: {referral_count}/3\n"
        ),
        "refer_earned": "✅ You've earned 2 hours of free access!\n",
        "refer_needed": (
            "❌ You need {remaining} more referral(s) to get 2 hours of free access.\n"
        ),
        "referral_status": (
            "🔗 Your Referral Status\n\n"
            "Your referral code: {referral_code}\n"
            "Your referral link:\n{referral_link}\n\n"
            "Referrals: {referral_count}/3\n"
        ),
        "access_until": "✅ You have access until: {expiry_date}\n",
        "permanent_access": "✅ You have permanent access.\n",
        "processing": "🚀 Processing your numbers... Please wait.",
        "no_numbers": (
            "❌ You didn't send any valid numbers. "
            "Please send numbers, one per line."
        ),
        "check_complete": "--- ✅ Check Complete! ---\n\n",
        "found_numbers": "✅ Found Numbers:\n",
        "not_found_numbers": "❌ Not Found Numbers:\n",
        "errors_unknown": "⚠️ Errors/Unknown:\n",
        "no_valid_numbers": "Could not process any numbers. Please check the format.",
        "rate_limit": (
            "⏳ Rate Limit Exceeded!\n\n"
            "You can only make one request every {time_limit}.\n\n"
            "Please wait {remaining_time} before trying again."
        ),
        "admin_contact": (
            "👑 Admin Contact Information\n\n"
            "👤 Name: {admin_name}\n"
            "🆔 ID: {admin_id}\n"
            "🔗 Username: {admin_username}\n\n"
            "Please contact the admin for approval or support."
        ),
        "price_list": "💰 Price List\n\n",
        "payment_methods": (
            "\n💳 Payment Methods:\n"
            "• Bkash\n• Nagad\n• Rocket\n• PayPal\n• Crypto\n\n"
            "📩 To purchase, please contact the admin.\n"
            "Use /admin to get contact details."
        ),
        "admin_panel": "👑 Admin Panel\n\nSelect an option from the menu below:",
        "approved_users": "✅ Approved Users",
        "all_users": "👤 All Users (Total: {total_users})",
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
        "unauthorized": "❌ You are not authorized to use this command.",
        "usage_approve": (
            "Usage: /approve &lt;user_id&gt; &lt;amount&gt; &lt;unit&gt;\n"
            "Example: /approve 123456789 7 days"
        ),
        "usage_disapprove": (
            "Usage: /disapprove &lt;user_id&gt;\nExample: /disapprove 123456789"
        ),
        "usage_setratelimit": (
            "Usage: /setratelimit &lt;seconds&gt;\n"
            "Example: /setratelimit 600 (for 10 minutes)"
        ),
        "usage_broadcast": "Usage: /broadcast &lt;your message&gt;",
        "usage_broadcast_approved": "Usage: /broadcast_approved &lt;your message&gt;",
        "invalid_unit": "❌ Invalid unit. Use 'hours', 'days', or 'months'.",
        "invalid_input": "❌ Invalid input. Please use the correct format: {format}",
        "cannot_disapprove_admin": "❌ You cannot disapprove the main admin.",
        "user_not_approved": "⚠️ User {uid} was not in the approved list.",
        "user_approved": "✅ User {uid} has been approved until {expiry_date}.",
        "user_disapproved": "✅ User {uid} has been disapproved.",
        "rate_limit_updated": (
            "✅ Rate limit updated to {seconds} seconds ({time_str})."
        ),
        "broadcast_complete": (
            "✅ Broadcast complete.\n\n"
            "✅ Successful: {success_count}\n"
            "❌ Failed: {fail_count}"
        ),
        "broadcast_approved_complete": (
            "✅ Broadcast to approved users complete.\n\n"
            "✅ Successful: {success_count}\n"
            "❌ Failed: {fail_count}"
        ),
        "syncing": "🔄 Syncing data files...",
        "sync_success": "✅ All data files successfully synced.",
        "sync_failed": "❌ Failed to sync some data files. Please check the logs.",
        "no_approved_users": "There are no approved users.",
        "no_users": "No users have interacted with the bot yet.",
        "invalid_user_id": "❌ Invalid User ID. Please provide a valid numerical ID.",
        "list_too_long": "The list was too long and has been sent as a file.",
        "access_expired": (
            "⏳ Your access has expired.\n\n"
            "Please contact the admin to renew your subscription.\n"
            "Use /admin for contact details."
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
        "referral_successful": (
            "Referral successful! You now have {referral_count}/3 referrals."
        ),
        "referral_earned": (
            "Congratulations! You've earned 2 hours of access through referrals!"
        ),
        "already_used_bot": "You have already used the bot before.",
        "invalid_referral": "Invalid referral code.",
        "new_referral_notification": (
            "🎉 Good news! Someone joined using your referral link.\n\n"
            "You now have {referral_count}/3 referrals.\n\n"
            "Keep sharing to earn free access!"
        ),
        "cleanup_expired": "🧹 Cleaning up expired users...",
        "cleanup_complete": "✅ Cleanup complete. Removed {count} expired users.",
        "user_already_approved": (
            "⚠️ User {uid} is already approved until {expiry_date}."
        ),
        "export_data_msg": (
            "📦 Export Data\n\n"
            "Your bot data is being prepared for download.\n\n"
            "This may take a moment if you have many users."
        ),
        "export_complete": "✅ Export complete. The data has been sent as a zip file.",
    },
    "bn": {
        "welcome": (
            "👋 হ্যালো {first_name}!\n\n"
            "ফেসবুক নম্বর চেকার বটে স্বাগতম।\n\n"
            "অনুগ্রহ করে আপনার পছন্দের ভাষা নির্বাচন করুন:"
        ),
        "language_selected": (
            "✅ ভাষা বাংলায় সেট করা হয়েছে।\n\n"
            "এটি একটি প্রিমিয়াম সার্ভিস। আমাকে ফোন নম্বরের তালিকা পাঠান যাচাই করার জন্য।\n\n"
            "🔐 অ্যাক্সেস প্রয়োজন? /admin ব্যবহার করে সাপোর্টের সাথে যোগাযোগ করুন।"
        ),
        "example": "উদাহরণ:\n+8801712345678\n+8801812345678",
        "access_denied": (
            "🚫 অ্যাক্সেস প্রত্যাখ্যান করা হয়েছে!\n\n"
            "এটি শুধুমাত্র পেইড ইউজারদের জন্য একটি প্রিমিয়াম সার্ভিস। "
            "এটি হার সীমাবদ্ধতা এড়াতে একটি VPS এবং প্রিমিয়াম প্রক্সি ব্যবহার করে চলে।\n\n"
            "আপনার ইউজার ID: {uid}\n\n"
            "অ্যাক্সেস পেতে অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।\n"
            "সাপোর্টের যোগাযোগের জন্য /admin ব্যবহার করুন।"
        ),
        "buy_online": "অনলাইনে কিনুন (শীঘ্রই আসছে)",
        "refer_earn": "রেফার করুন এবং ফ্রি অ্যাক্সেস অর্জন করুন",
        "buy_online_msg": (
            "🛒 অনলাইনে কিনুন\n\n"
            "অনলাইন পেমেন্ট অপশন শীঘ্রই আসছে!\n\n"
            "এখন, অ্যাক্সেস কেনার জন্য সরাসরি অ্যাডমিনের সাথে যোগাযোগ করুন।\n"
            "যোগাযোগের বিবরণের জন্য /admin ব্যবহার করুন।"
        ),
        "refer_link": (
            "🔗 আপনার রেফারেল লিঙ্ক\n\n"
            "আপনার বন্ধুদের সাথে এই লিঙ্কটি শেয়ার করুন:\n{referral_link}\n\n"
            "রেফারেল: {referral_count}/3\n"
        ),
        "refer_earned": "✅ আপনি রেফারেলের মাধ্যমে 2 ঘন্টার ফ্রি অ্যাক্সেস অর্জন করেছেন!\n",
        "refer_needed": (
            "❌ 2 ঘন্টার ফ্রি অ্যাক্সেস পেতে আপনার {remaining} আরও রেফারেল(স) প্রয়োজন।\n"
        ),
        "referral_status": (
            "🔗 আপনার রেফারেল স্ট্যাটাস\n\n"
            "আপনার রেফারেল কোড: {referral_code}\n"
            "আপনার রেফারেল লিঙ্ক:\n{referral_link}\n\n"
            "রেফারেল: {referral_count}/3\n"
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
            "⏳ রেট লিমিট অতিক্রান্ত!\n\n"
            "আপনি প্রতি {time_limit} শুধুমাত্র একবার রিকোয়েস্ট করতে পারেন।\n\n"
            "আবার চেষ্টা করার আগে অনুগ্রহ করে {remaining_time} অপেক্ষা করুন।"
        ),
        "admin_contact": (
            "👑 অ্যাডমিন যোগাযোগ তথ্য\n\n"
            "👤 নাম: {admin_name}\n"
            "🆔 ID: {admin_id}\n"
            "🔗 ইউজারনেম: {admin_username}\n\n"
            "অনুমোদন বা সাপোর্টের জন্য অ্যাডমিনের সাথে যোগাযোগ করুন।"
        ),
        "price_list": "💰 মূল্য তালিকা\n\n",
        "payment_methods": (
            "\n💳 পেমেন্ট পদ্ধতি:\n"
            "• বিকাশ\n• নগদ\n• রকেট\n• পেপাল\n• ক্রিপ্টো\n\n"
            "📩 কেনার জন্য, অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।\n"
            "যোগাযোগের বিবরণের জন্য /admin ব্যবহার করুন।"
        ),
        "admin_panel": "👑 অ্যাডমিন প্যানেল\n\nনিচের মেনু থেকে একটি অপশন নির্বাচন করুন:",
        "approved_users": "✅ অনুমোদিত ইউজার",
        "all_users": "👤 সমস্ত ইউজার (মোট: {total_users})",
        "bot_statistics": (
            "📊 বট পরিসংখ্যান\n\n"
            "👥 মোট ইউজার: {total_users}\n"
            "✅ অনুমোদিত ইউজার: {approved_users}\n"
            "⏳ অপেক্ষমাণ ইউজার: {pending_users}\n"
            "🔗 মোট রেফারেল: {total_referrals}\n"
            "🔢 মোট নম্বর চেক করা হয়েছে: {total_numbers_checked}\n\n"
            "📅 সর্বশেষ আপডেট: {last_updated}"
        ),
        "current_price_list": "💰 বর্তমান মূল্য তালিকা\n\n",
        "unauthorized": "❌ আপনি এই কমান্ড ব্যবহার করার অনুমতি পাননি।",
        "usage_approve": (
            "ব্যবহার: /approve &lt;user_id&gt; &lt;amount&gt; &lt;unit&gt;\n"
            "উদাহরণ: /approve 123456789 7 days"
        ),
        "usage_disapprove": (
            "ব্যবহার: /disapprove &lt;user_id&gt;\nউদাহরণ: /disapprove 123456789"
        ),
        "usage_setratelimit": (
            "ব্যবহার: /setratelimit &lt;seconds&gt;\nউদাহরণ: /setratelimit 600 (10 মিনিটের জন্য)"
        ),
        "usage_broadcast": "ব্যবহার: /broadcast &lt;আপনার বার্তা&gt;",
        "usage_broadcast_approved": (
            "ব্যবহার: /broadcast_approved &lt;আপনার বার্তা&gt;"
        ),
        "invalid_unit": "❌ অবৈধ ইউনিট। 'hours', 'days', বা 'months' ব্যবহার করুন।",
        "invalid_input": (
            "❌ অবৈধ ইনপুট। অনুগ্রহ করে সঠিক ফরম্যাট ব্যবহার করুন: {format}"
        ),
        "cannot_disapprove_admin": "❌ আপনি প্রধান অ্যাডমিনকে অনুমোদন বাতিল করতে পারবেন না।",
        "user_not_approved": "⚠️ ইউজার {uid} অনুমোদিত তালিকায় ছিল না।",
        "user_approved": "✅ ইউজার {uid} কে {expiry_date} পর্যন্ত অনুমোদন করা হয়েছে।",
        "user_disapproved": "✅ ইউজার {uid} এর অনুমোদন বাতিল করা হয়েছে।",
        "rate_limit_updated": (
            "✅ রেট লিমিট {seconds} সেকেন্ডে ({time_str}) আপডেট করা হয়েছে।"
        ),
        "broadcast_complete": (
            "✅ প্রচার সম্পন্ন।\n\n"
            "✅ সফল: {success_count}\n❌ ব্যর্থ: {fail_count}"
        ),
        "broadcast_approved_complete": (
            "✅ অনুমোদিত ইউজারদের কাছে প্রচার সম্পন্ন।\n\n"
            "✅ সফল: {success_count}\n❌ ব্যর্থ: {fail_count}"
        ),
        "syncing": "🔄 ডেটা ফাইল সিঙ্ক করা হচ্ছে...",
        "sync_success": "✅ সমস্ত ডেটা ফাইল সফলভাবে সিঙ্ক করা হয়েছে।",
        "sync_failed": (
            "❌ কিছু ডেটা ফাইল সিঙ্ক করতে ব্যর্থ হয়েছে। অনুগ্রহ করে লগ চেক করুন।"
        ),
        "no_approved_users": "কোনো অনুমোদিত ইউজার নেই।",
        "no_users": "এখনো কোনো ইউজার বটের সাথে ইন্টারঅ্যাক্ট করেনি।",
        "invalid_user_id": "❌ অবৈধ ইউজার ID। অনুগ্রহ করে একটি বৈধ সংখ্যাসূচক ID প্রদান করুন।",
        "list_too_long": "তালিকাটি অনেক বড় ছিল এবং এটি ফাইল হিসেবে পাঠানো হয়েছে।",
        "access_expired": (
            "⏳ আপনার অ্যাক্সেসের মেয়াদ শেষ হয়ে গেছে।\n\n"
            "সাবস্ক্রিপশন নবায়নের জন্য অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।\n"
            "যোগাযোগের জন্য /admin ব্যবহার করুন।"
        ),
        "access_approved": (
            "🎉 অভিনন্দন! আপনার অ্যাক্সেস অনুমোদিত হয়েছে।\n\n"
            "আপনি {expiry_date} পর্যন্ত বট ব্যবহার করতে পারবেন।\n\n"
            "প্রিমিয়াম সার্ভিস উপভোগ করুন!"
        ),
        "access_revoked": (
            "🚫 আপনার অ্যাক্সেস অ্যাডমিন দ্বারা বাতিল করা হয়েছে।\n\n"
            "আপনি যদি মনে করেন এটি ভুলবশত হয়েছে, তাহলে বিস্তারিত জানতে অ্যাডমিনের সাথে যোগাযোগ করুন।\n"
            "যোগাযোগের জন্য /admin ব্যবহার করুন।"
        ),
        "referral_successful": (
            "রেফারেল সফল! এখন আপনার {referral_count}/3 টি রেফারেল হয়েছে।"
        ),
        "referral_earned": (
            "অভিনন্দন! আপনি রেফারেলের মাধ্যমে 2 ঘন্টার অ্যাক্সেস অর্জন করেছেন!"
        ),
        "already_used_bot": "আপনি ইতোমধ্যে এই বট ব্যবহার করেছেন।",
        "invalid_referral": "অবৈধ রেফারেল কোড।",
        "new_referral_notification": (
            "🎉 সুসংবাদ! কেউ আপনার রেফারেল লিঙ্ক ব্যবহার করে যোগ দিয়েছে।\n\n"
            "এখন আপনার {referral_count}/3 টি রেফারেল আছে।\n\n"
            "ফ্রি অ্যাক্সেস পেতে শেয়ার করা চালিয়ে যান!"
        ),
        "cleanup_expired": "🧹 মেয়াদোত্তীর্ণ ইউজারদের পরিষ্কার করা হচ্ছে...",
        "cleanup_complete": (
            "✅ পরিষ্কার সম্পন্ন। {count} জন মেয়াদোত্তীর্ণ ইউজার মুছে ফেলা হয়েছে।"
        ),
        "user_already_approved": (
            "⚠️ ইউজার {uid} ইতিমধ্যে {expiry_date} পর্যন্ত অনুমোদিত।"
        ),
        "export_data_msg": (
            "📦 ডেটা এক্সপোর্ট\n\n"
            "আপনার বট ডেটা ডাউনলোডের জন্য প্রস্তুত করা হচ্ছে।\n\n"
            "অনেক ইউজার থাকলে এতে কিছুটা সময় লাগতে পারে।"
        ),
        "export_complete": "✅ এক্সপোর্ট সম্পন্ন। ডেটা একটি জিপ ফাইল হিসেবে পাঠানো হয়েছে।",
    },
}

# --- FACEBOOK CHECKER HTTP DATA ---

FB_URL = "https://www.facebook.com/ajax/login/help/identify.php?ctx=recover"
FB_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en;q=0.9,en-US;q=0.8",
    "content-type": "application/x-www-form-urlencoded",
    "origin": "https://www.facebook.com",
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
FB_COOKIES = {
    "datr": "5BfuaP5MJ81CQGWO4JTj_FQA",
    "wd": "980x2125",
}
FB_BASE_DATA = {
    "jazoest": "2979",
    "lsd": "AdE3czGo7uw",
    "email": "number",
    "did_submit": "1",
    "__user": "0",
    "__a": "1",
    "__req": "7",
    "__hs": "20375.BP%3ADEFAULT.2.0...0",
    "dpr": "1",
    "__rev": "1028355510",
}

# ---------------------------------------------------------------------------
# LOCAL FILE FUNCTIONS
# ---------------------------------------------------------------------------


async def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        async with aiofiles.open(path, "r", encoding="utf-8") as f:
            content = await f.read()
            return json.loads(content)
    except Exception as e:
        logger.error("Error loading JSON from %s: %s", path, e)
        return default


async def save_json(path: str, data) -> bool:
    try:
        async with aiofiles.open(path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        logger.error("Error saving JSON to %s: %s", path, e)
        return False


async def load_config_from_file() -> None:
    global config_data
    cfg = await load_json(CONFIG_FILE, {})
    if cfg:
        config_data.update(cfg)


async def save_config_to_file() -> bool:
    ok = await save_json(CONFIG_FILE, config_data)
    if not ok:
        return False
    try:
        await save_config_to_db()
    except Exception as e:
        logger.error("Error saving config to MySQL: %s", e)
    return True


async def load_users_from_file() -> None:
    global approved_users
    data = await load_json(USER_DATA_FILE, {})
    temp: dict[int, datetime | None] = {}
    for user_id_str, expiry in data.items():
        try:
            uid = int(user_id_str)
        except ValueError:
            continue
        if expiry is None:
            temp[uid] = None
        else:
            try:
                temp[uid] = datetime.fromisoformat(expiry)
            except ValueError:
                temp[uid] = None
    temp[ADMIN_ID] = None
    approved_users = temp


async def save_users_to_file() -> bool:
    data: dict[str, str | None] = {}
    for uid, expiry in approved_users.items():
        data[str(uid)] = expiry.isoformat() if expiry else None
    ok = await save_json(USER_DATA_FILE, data)
    if not ok:
        return False
    try:
        await save_users_to_db()
    except Exception as e:
        logger.error("Error saving users to MySQL: %s", e)
    return True


async def load_all_users_from_file() -> None:
    global all_users
    all_users = await load_json(ALL_USERS_FILE, {})


async def save_all_users_to_file() -> bool:
    ok = await save_json(ALL_USERS_FILE, all_users)
    if not ok:
        return False
    try:
        await save_all_users_to_db()
    except Exception as e:
        logger.error("Error saving all_users to MySQL: %s", e)
    return True


async def load_referral_data_from_file() -> None:
    global referral_data
    referral_data = await load_json(REFERRAL_DATA_FILE, {})


async def save_referral_data_to_file() -> bool:
    ok = await save_json(REFERRAL_DATA_FILE, referral_data)
    if not ok:
        return False
    try:
        await save_referral_data_to_db()
    except Exception as e:
        logger.error("Error saving referral_data to MySQL: %s", e)
    return True


async def load_price_list_from_file() -> None:
    global price_list
    data = await load_json(PRICE_LIST_FILE, {})
    if data:
        price_list.update(data)


async def save_price_list_to_file() -> bool:
    return await save_json(PRICE_LIST_FILE, price_list)


async def load_user_settings_from_file() -> None:
    global user_settings
    user_settings = await load_json(USER_SETTINGS_FILE, {})


async def save_user_settings_to_file() -> bool:
    ok = await save_json(USER_SETTINGS_FILE, user_settings)
    if not ok:
        return False
    try:
        await save_user_settings_to_db()
    except Exception as e:
        logger.error("Error saving user_settings to MySQL: %s", e)
    return True


async def save_user_details_to_file(user_id: int, user_data: dict) -> bool:
    try:
        users_dir = os.path.join(DATA_DIR, "users")
        os.makedirs(users_dir, exist_ok=True)
        filename = os.path.join(users_dir, f"{user_id}.json")
        async with aiofiles.open(filename, "w", encoding="utf-8") as f:
            await f.write(json.dumps(user_data, indent=2, ensure_ascii=False))
        return True
    except Exception as e:
        logger.error("Error saving user %s details to file: %s", user_id, e)
        return False

# ---------------------------------------------------------------------------
# MYSQL HELPERS
# ---------------------------------------------------------------------------


async def get_db_connection(db: str | None = None):
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
        logger.error("Failed to connect to MySQL (db=%s): %s", db, e)
        return None


async def ensure_database() -> bool:
    conn = await get_db_connection(db=None)
    if conn is None:
        return False
    try:
        async with conn.cursor() as cur:
            await cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DB}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        return True
    except Exception as e:
        logger.error("Failed to create database '%s': %s", MYSQL_DB, e)
        return False
    finally:
        conn.close()


async def init_db() -> None:
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
                    logger.error("Error creating table: %s", e)
    finally:
        conn.close()


async def save_users_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM approved_users")
            for uid, expiry in approved_users.items():
                expiry_str = (
                    expiry.strftime("%Y-%m-%d %H:%M:%S") if expiry is not None else None
                )
                await cur.execute(
                    "REPLACE INTO approved_users (user_id, expiry_datetime) "
                    "VALUES (%s, %s)",
                    (int(uid), expiry_str),
                )
    except Exception as e:
        logger.error("Error saving approved_users to MySQL: %s", e)
    finally:
        conn.close()


async def save_all_users_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM all_users")
            for user_id_str, data in all_users.items():
                uid = int(user_id_str)
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
                        uid,
                        first_name,
                        last_name,
                        username,
                        last_interaction,
                        numbers_checked,
                    ),
                )
    except Exception as e:
        logger.error("Error saving all_users to MySQL: %s", e)
    finally:
        conn.close()


async def save_referral_data_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM referral_data")
            for user_id_str, data in referral_data.items():
                uid = int(user_id_str)
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
                        uid,
                        referral_code,
                        int(referred_by) if referred_by else None,
                        referred_users_json,
                    ),
                )
    except Exception as e:
        logger.error("Error saving referral_data to MySQL: %s", e)
    finally:
        conn.close()


async def save_user_settings_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return
    try:
        async with conn.cursor() as cur:
            await cur.execute("DELETE FROM user_settings")
            for user_id_str, data in user_settings.items():
                uid = int(user_id_str)
                language = data.get("language")
                await cur.execute(
                    """
                    REPLACE INTO user_settings (user_id, language)
                    VALUES (%s, %s)
                    """,
                    (uid, language),
                )
    except Exception as e:
        logger.error("Error saving user_settings to MySQL: %s", e)
    finally:
        conn.close()


async def save_config_to_db() -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return
    try:
        async with conn.cursor() as cur:
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
        logger.error("Error saving config to MySQL: %s", e)
    finally:
        conn.close()


async def save_user_to_db(user_id: int, user_data: dict) -> None:
    conn = await get_db_connection(db=MYSQL_DB)
    if conn is None:
        return
    try:
        async with conn.cursor() as cur:
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
        logger.error("Error saving single user %s to MySQL: %s", user_id, e)
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
    user_settings.setdefault(user_id_str, {})
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
            logger.error("Error formatting text for key '%s': %s", key, e)
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

    if "referred_users" not in referral_data[referrer_id_str]:
        referral_data[referrer_id_str]["referred_users"] = []
    if referred_id_str not in referral_data[referrer_id_str]["referred_users"]:
        referral_data[referrer_id_str]["referred_users"].append(referred_id_str)

    await save_referral_data_to_file()

    referral_count = len(referral_data[referrer_id_str]["referred_users"])

    await send_user_notification(
        context,
        referrer_id,
        get_text(referrer_id, "new_referral_notification", referral_count=referral_count),
    )

    if referral_count >= 3:
        expiry_date = datetime.now(timezone.utc) + timedelta(hours=2)
        approved_users[referrer_id] = expiry_date

        # Store referral bonus plan info (2 hours free) for this user
        ref_user_id_str = str(referrer_id)
        user_rec = all_users.setdefault(ref_user_id_str, {})
        user_rec["plan_duration"] = "2 hours (referral bonus)"
        user_rec["plan_price_bdt"] = 0
        user_rec["plan_price_usd"] = 0.0
        await save_all_users_to_file()

        await save_users_to_file()
        await send_user_notification(
            context,
            referrer_id,
            get_text(referrer_id, "referral_earned"),
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
    else:
        all_users[user_id]["last_interaction"] = datetime.now().isoformat()
    await save_all_users_to_file()

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------


async def check_facebook_number(client: httpx.AsyncClient, phone_number: str) -> str:
    """Check a phone number against Facebook and return status string."""
    data = FB_BASE_DATA.copy()
    data["email"] = phone_number

    try:
        response = await client.post(
            FB_URL, headers=FB_HEADERS, cookies=FB_COOKIES, data=data, timeout=20
        )
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
        logger.warning("httpx RequestError for %s: %s", phone_number, e)
        return f"Error: {e}"
    except json.JSONDecodeError:
        logger.warning("json.JSONDecodeError for %s: Possibly blocked", phone_number)
        return "Error: Invalid JSON (Possibly Blocked)"
    except Exception as e:
        logger.error(
            "Unexpected error in check_facebook_number for %s: %s", phone_number, e
        )
        return f"Error: {e}"


async def send_user_notification(
    context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str
) -> None:
    """Send a notification to a user, ignoring common Telegram errors."""
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        msg = str(e)
        if "chat not found" in msg.lower():
            logger.debug(
                "Notification skipped for user %s: chat not found / not started", user_id
            )
        elif "bot was blocked by the user" in msg.lower():
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
            send_user_notification(
                context, user_id, get_text(user_id, "access_expired")
            )
        )
        asyncio.create_task(save_users_to_file())
        return False

    return True


def check_rate_limit(user_id: int) -> tuple[bool, str | None]:
    current_time = datetime.now(timezone.utc)
    rate_limit_seconds = config_data.get(
        "rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS
    )

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
    return len(expired)


async def ensure_daily_reset() -> None:
    """Reset numbers_checked for all users once per day."""
    today = datetime.now(timezone.utc).date().isoformat()
    last_reset = config_data.get("last_reset_date")
    if last_reset == today:
        return

    for data in all_users.values():
        if isinstance(data, dict):
            data["numbers_checked"] = 0

    config_data["last_reset_date"] = today
    await save_all_users_to_file()
    await save_config_to_file()
    logger.info("Daily reset of numbers_checked completed")


async def auto_cleanup_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    while True:
        try:
            removed = await cleanup_expired_users()
            if removed > 0:
                logger.info("Auto cleanup removed %d users", removed)
        except Exception as e:
            logger.error("Error in auto cleanup task: %s", e)
        await asyncio.sleep(AUTO_CLEANUP_INTERVAL)


async def export_bot_data() -> io.BytesIO | None:
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
                        async with aiofiles.open(path, "r", encoding="utf-8") as f:
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
        logger.error("Error exporting bot data: %s", e)
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
        await save_user_to_db(user.id, user_data)

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

    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("⚙️ Open Admin Panel", callback_data="admin_open_panel")]
        ]
        await update.message.reply_html(
            contact_text, reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_html(contact_text)


async def show_price_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the price list with inline buttons for buy/refer."""
    user = update.effective_user
    await track_user(user, update)

    text = get_text(user.id, "price_list")
    for _, value in price_list.items():
        text += (
            f"🔹 <b>{value['duration']}</b>: "
            f"{value['price_bdt']} BDT / {value['price_usd']} USD\n"
        )
    text += get_text(user.id, "payment_methods")

    keyboard = [
        [InlineKeyboardButton(get_text(user.id, "buy_online"), callback_data="buy_online")],
        [InlineKeyboardButton(get_text(user.id, "refer_earn"), callback_data="refer")],
    ]

    await update.message.reply_html(text, reply_markup=InlineKeyboardMarkup(keyboard))


async def show_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin commands as an inline button menu."""
    user = update.effective_user
    unauthorized_text = get_text(user.id, "unauthorized")

    # Handle unauthorized access both for commands and callbacks
    if user.id != ADMIN_ID:
        if getattr(update, "message", None) is not None:
            await update.message.reply_text(unauthorized_text)
        else:
            query = getattr(update, "callback_query", None)
            if query is not None:
                await query.edit_message_text(unauthorized_text)
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
    markup = InlineKeyboardMarkup(keyboard)

    # If called from a normal message (/cmd), reply; if from a callback, edit the message
    if getattr(update, "message", None) is not None:
        await update.message.reply_html(msg, reply_markup=markup)
    else:
        query = getattr(update, "callback_query", None)
        if query is not None:
            await query.edit_message_text(msg, reply_markup=markup, parse_mode="HTML")


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
        await save_user_to_db(query.from_user.id, user_data)

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
            if not approved_users:
                await query.edit_message_text(
                    get_text(query.from_user.id, "no_approved_users")
                )
                return

            keyboard: list[list[InlineKeyboardButton]] = []
            for uid, _ in approved_users.items():
                user_info = all_users.get(str(uid), {})
                name = user_info.get("first_name", "Unknown")
                if uid == ADMIN_ID:
                    label = f"👑 {name} (Admin)"
                else:
                    label = f"👤 {name} ({uid})"
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            label,
                            callback_data=f"admin_user_details_approved_{uid}",
                        )
                    ]
                )

            keyboard.append(
                [InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]
            )

            text = (
                get_text(query.from_user.id, "approved_users")
                + "\n\nTap a user to view details."
            )
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if data == "admin_list_all":
            if not all_users:
                await query.edit_message_text(
                    get_text(query.from_user.id, "no_users")
                )
                return

            keyboard: list[list[InlineKeyboardButton]] = []
            for uid, user_data in all_users.items():
                name = user_data.get("first_name", "Unknown")
                if uid == str(ADMIN_ID):
                    label = f"👑 {name} (Admin)"
                elif int(uid) in approved_users:
                    label = f"✅ {name} ({uid})"
                else:
                    label = f"👤 {name} ({uid})"
                keyboard.append(
                    [
                        InlineKeyboardButton(
                            label,
                            callback_data=f"admin_user_details_all_{uid}",
                        )
                    ]
                )

            keyboard.append(
                [InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]
            )

            text = (
                get_text(
                    query.from_user.id, "all_users", total_users=len(all_users)
                )
                + "\n\nTap a user to view details."
            )
            await query.edit_message_text(
                text, reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if data.startswith("admin_user_details_"):
            # Show per-user details (plan, expiry, total checked)
            if data.startswith("admin_user_details_approved_"):
                user_source = "approved"
                prefix = "admin_user_details_approved_"
            else:
                user_source = "all"
                prefix = "admin_user_details_all_"

            user_id_str = data.replace(prefix, "")
            try:
                uid = int(user_id_str)
            except ValueError:
                await query.edit_message_text("Invalid user id.")
                return

            user_data = all_users.get(user_id_str, {})
            name = html.escape(user_data.get("first_name", "Unknown"))
            raw_username = user_data.get("username")
            if raw_username:
                username = "@" + html.escape(raw_username)
            else:
                username = "None"
            numbers_checked = user_data.get("numbers_checked", 0)
            language = user_data.get("language", get_user_language(uid))

            is_approved = uid in approved_users
            if is_approved:
                expiry = approved_users.get(uid)
                if expiry is None:
                    expiry_info = "Permanent access"
                else:
                    expiry_info = expiry.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                expiry_info = "Not approved"

            plan_duration = user_data.get("plan_duration")
            plan_bdt = user_data.get("plan_price_bdt")
            plan_usd = user_data.get("plan_price_usd")
            if plan_duration:
                if plan_bdt is not None and plan_usd is not None:
                    plan_info = f"{plan_duration} - {plan_bdt} BDT / {plan_usd} USD"
                else:
                    plan_info = plan_duration
            else:
                plan_info = "Not set"

            details = (
                "👤 User Details\n\n"
                f"ID: {uid}\n"
                f"Name: {name}\n"
                f"Username: {username}\n"
                f"Language: {language}\n"
                f"Numbers checked (last 24h): {numbers_checked}\n"
                f"Approved: {'Yes' if is_approved else 'No'}\n"
                f"Expiry: {expiry_info}\n"
                f"Plan: {plan_info}\n"
            )

            back_cb = "admin_list_approved" if user_source == "approved" else "admin_list_all"
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=back_cb)]]

            await query.edit_message_text(
                details,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        if data == "admin_help_approve":
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_approve"),
                parse_mode="HTML",
                reply_markup=back_kb,
            )
            return

        if data == "admin_help_disapprove":
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_disapprove"),
                parse_mode="HTML",
                reply_markup=back_kb,
            )
            return

        if data == "admin_help_broadcast":
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_broadcast"),
                parse_mode="HTML",
                reply_markup=back_kb,
            )
            return

        if data == "admin_help_broadcast_approved":
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_broadcast_approved"),
                parse_mode="HTML",
                reply_markup=back_kb,
            )
            return

        if data == "admin_help_setratelimit":
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(
                get_text(query.from_user.id, "usage_setratelimit"),
                parse_mode="HTML",
                reply_markup=back_kb,
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

            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )

            if all([ok_users, ok_ref, ok_all, ok_price, ok_settings, ok_config]):
                await query.edit_message_text(
                    get_text(query.from_user.id, "sync_success"),
                    reply_markup=back_kb,
                )
            else:
                await query.edit_message_text(
                    get_text(query.from_user.id, "sync_failed"),
                    reply_markup=back_kb,
                )
            return

        if data == "admin_do_cleanup":
            await query.edit_message_text(
                get_text(query.from_user.id, "cleanup_expired")
            )
            removed = await cleanup_expired_users()
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(
                get_text(query.from_user.id, "cleanup_complete", count=removed),
                reply_markup=back_kb,
            )
            return

        if data == "admin_do_export":
            await query.edit_message_text(
                get_text(query.from_user.id, "export_data_msg")
            )
            zip_buffer = await export_bot_data()
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
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
                    get_text(query.from_user.id, "export_complete"),
                    reply_markup=back_kb,
                )
            else:
                await query.edit_message_text(
                    "❌ Failed to export data. Please check the logs.",
                    reply_markup=back_kb,
                )
            return

        if data == "admin_show_pricelist":
            text = get_text(query.from_user.id, "current_price_list")
            for _, value in price_list.items():
                text += (
                    f"🔹 <b>{value['duration']}</b>: "
                    f"{value['price_bdt']} BDT / {value['price_usd']} USD\n"
                )
            back_kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("🔙 Back", callback_data="admin_open_panel")]]
            )
            await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_kb)
            return

    return


async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    if len(context.args) != 3:
        await update.message.reply_html(
            get_text(update.effective_user.id, "usage_approve")
        )
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
            await update.message.reply_text(
                get_text(update.effective_user.id, "invalid_unit")
            )
            return

        # Derive and store plan info (duration and price, if from price_list)
        plan_duration = f"{amount} {unit}"
        plan_price_bdt = None
        plan_price_usd = None

        if unit.startswith("day"):
            for value in price_list.values():
                try:
                    num_str, unit_str = value["duration"].split()[:2]
                    num_days = int(num_str)
                except Exception:
                    continue
                if num_days == amount and unit_str.lower().startswith("day"):
                    plan_duration = value["duration"]
                    plan_price_bdt = value.get("price_bdt")
                    plan_price_usd = value.get("price_usd")
                    break

        user_id_str = str(user_id_to_approve)
        user_rec = all_users.setdefault(user_id_str, {})
        user_rec["plan_duration"] = plan_duration
        if plan_price_bdt is not None:
            user_rec["plan_price_bdt"] = plan_price_bdt
        if plan_price_usd is not None:
            user_rec["plan_price_usd"] = plan_price_usd
        await save_all_users_to_file()

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

        if user_id_str in all_users:
            await send_user_notification(
                context,
                user_id_to_approve,
                get_text(
                    user_id_to_approve,
                    "access_approved",
                    expiry_date=expiry_str,
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
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    if not context.args:
        await update.message.reply_html(
            get_text(update.effective_user.id, "usage_disapprove")
        )
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
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    if not context.args:
        await update.message.reply_html(
            get_text(update.effective_user.id, "usage_setratelimit")
        )
        return

    try:
        seconds = int(context.args[0])
        if seconds < 10:
            await update.message.reply_text(
                "❌ Rate limit must be at least 10 seconds."
            )
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
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    await update.message.reply_text(
        get_text(update.effective_user.id, "cleanup_expired")
    )
    removed = await cleanup_expired_users()
    await update.message.reply_html(
        get_text(update.effective_user.id, "cleanup_complete", count=removed)
    )


async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    await update.message.reply_text(
        get_text(update.effective_user.id, "export_data_msg")
    )
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
        await update.message.reply_text(
            "❌ Failed to export data. Please check the logs."
        )


async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    if not approved_users:
        await update.message.reply_text(
            get_text(update.effective_user.id, "no_approved_users")
        )
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
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    if not all_users:
        await update.message.reply_text(
            get_text(update.effective_user.id, "no_users")
        )
        return

    text = (
        get_text(
            update.effective_user.id,
            "all_users",
            total_users=len(all_users),
        )
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


async def show_price_list_admin(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    text = get_text(update.effective_user.id, "current_price_list")
    for _, value in price_list.items():
        text += (
            f"🔹 <b>{value['duration']}</b>: "
            f"{value['price_bdt']} BDT / {value['price_usd']} USD\n"
        )
    await update.message.reply_html(text)


async def sync_files(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    await update.message.reply_text(
        get_text(update.effective_user.id, "syncing")
    )

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
        await update.message.reply_text(
            get_text(update.effective_user.id, "sync_success")
        )
    else:
        await update.message.reply_text(
            get_text(update.effective_user.id, "sync_failed")
        )


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
        return

    if not context.args:
        await update.message.reply_html(
            get_text(update.effective_user.id, "usage_broadcast")
        )
        return

    message_to_broadcast = " ".join(context.args)
    success_count = 0
    fail_count = 0

    for user_id in all_users.keys():
        try:
            await context.bot.send_message(
                chat_id=int(user_id),
                text=message_to_broadcast,
                parse_mode="HTML",
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
        await update.message.reply_text(
            get_text(update.effective_user.id, "unauthorized")
        )
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
    await ensure_daily_reset()

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
    await save_user_to_db(user_id, user_data)

    if not is_user_approved(user_id, context):
        await handle_unauthorized_user(update, context)
        return

    if user_id != ADMIN_ID:
        allowed, remaining = check_rate_limit(user_id)
        if not allowed:
            rate_limit_seconds = config_data.get(
                "rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS
            )
            await update.message.reply_html(
                get_text(
                    user_id,
                    "rate_limit",
                    remaining_time=remaining,
                    time_limit=rate_limit_seconds,
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
                    chat_id=update.effective_chat.id,
                    document=f_sync,
                    caption=caption,
                )
            os.remove(filename)
            await processing_message.delete()
            return
        except Exception as e:
            logger.error("Failed to create or send file: %s", e)
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
                logger.error("Failed to edit message: %s", e)
                await processing_message.edit_text(
                    "❌ An error occurred while formatting the results. "
                    "Please check the logs."
                )
        except Exception as e:
            logger.error("Failed to send message: %s", e)
            await processing_message.edit_text(
                "❌ An error occurred while formatting the results. "
                "Please check the logs."
            )


async def handle_unauthorized_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    user = update.effective_user
    user_id = user.id

    _ = await get_or_create_referral_code(user_id)

    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "buy_online"), callback_data="buy_online")],
        [InlineKeyboardButton(get_text(user_id, "refer_earn"), callback_data="refer")],
    ]
    await update.message.reply_html(
        get_text(user_id, "access_denied", uid=user_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
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
        logger.error("Error initialising MySQL database: %s", e)


def main() -> None:
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