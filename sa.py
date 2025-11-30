import logging
import requests
import json
import concurrent.futures
import os
import asyncio
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
from telegram.error import BadRequest
import base64
import random
import string
import html  # Added for HTML escaping
import re  # Added for removing HTML tags
import zipfile  # Added for creating zip files
import io  # Added for in-memory file operations

# --- NEW IMPORTS FOR ASYNC OPERATIONS ---
import aiofiles  # For async file I/O
import httpx     # For async HTTP requests
import aiomysql  # For async MySQL database access

# Enable logging to see errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = '8499529767:AAHd3L5QTaJpcgqqadYCKv6FXTMADuniCVM'
MAX_WORKERS = 100  # This is no longer used for HTTP, but kept for reference
FILE_SEND_THRESHOLD = 120  # This is no longer used in the logic, but kept for reference
AUTO_CLEANUP_INTERVAL = 100  # Auto cleanup every hour (in seconds)
USERS_PER_PAGE = 10  # Number of users to show per page in pagination
DEFAULT_RATE_LIMIT_SECONDS = 300  # Default 5 minutes rate limit (300 seconds)

# --- LOCAL FILE CONFIGURATION ---
# Create a directory to store data files if it doesn't exist
DATA_DIR = "bot_data"
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# --- MYSQL DATABASE CONFIGURATION ---
# Production MySQL configuration (shared hosting)
MYSQL_HOST = "localhost"  # Change if your hosting provider gives a different host
MYSQL_PORT = 3306
MYSQL_USER = "refihzbz_fbchek"
MYSQL_PASSWORD = "Asraf1025@#"
MYSQL_DB = "refihzbz_fbchek"

# Global connection pool
db_pool = None

USER_DATA_FILE = os.path.join(DATA_DIR, "approved_users.json")
REFERRAL_DATA_FILE = os.path.join(DATA_DIR, "referral_data.json")
ALL_USERS_FILE = os.path.join(DATA_DIR, "all_users.json")
PRICE_LIST_FILE = os.path.join(DATA_DIR, "price_list.json")
USER_SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")

# --- PREMIUM ADMIN & APPROVAL SYSTEM ---
ADMIN_ID = 7646847122
ADMIN_USERNAME = '@Teamredadmin'
ADMIN_FIRST_NAME = "DOREMON"
approved_users = {ADMIN_ID: None}
referral_data = {}
all_users = {}
user_settings = {}
user_last_request = {}  # Track last request time for rate limiting
config_data = {"rate_limit_seconds": DEFAULT_RATE_LIMIT_SECONDS} # Config for rate limit and other settings
# Fixed price list - removed price change functionality
price_list = {
    "1_day": {"duration": "1 Day", "price_bdt": 50, "price_usd": 0.45},
    "3_days": {"duration": "3 Days", "price_bdt": 140, "price_usd": 1.25},
    "7_days": {"duration": "7 Days", "price_bdt": 300, "price_usd": 2.70},
    "15_days": {"duration": "15 Days", "price_bdt": 600, "price_usd": 5.40},
    "30_days": {"duration": "30 Days", "price_bdt": 1000, "price_usd": 9.00}
}

# --- LANGUAGE STRINGS ---
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
        "bot_statistics": "📊 Bot Statistics\n\n👥 Total Users: {total_users}\n✅ Approved Users: {approved_users}\n⏳ Pending Users: {pending_users}\n🔗 Total Referrals: {total_referrals}\n🔢 Total Numbers Checked: {total_numbers_checked}\n\n📅 Last Updated: {last_updated}",
        "current_price_list": "💰 Current Price List\n\n",
        "approve_user_msg": "➕ Approve User\n\nPlease send the user ID and duration in the format:\n/approve <user_id> <amount> <unit>\n\nExample: /approve 123456789 7 days\n\nAvailable units: hours, days, months",
        "disapprove_user_msg": "➖ Disapprove User\n\nPlease send the user ID in the format:\n/disapprove <user_id>\n\nExample: /disapprove 123456789",
        "broadcast_all_msg": "📢 Broadcast to All Users\n\nPlease send your message in the format:\n/broadcast <your message>\n\nExample: /broadcast Hello everyone! The bot will be under maintenance for 2 hours.",
        "broadcast_approved_msg": "📢 Broadcast to Approved Users\n\nPlease send your message in the format:\n/broadcast_approved <your message>\n\nExample: /broadcast_approved New features have been added to the bot!",
        "unauthorized": "❌ You are not authorized to use this command.",
        "usage_approve": "Usage: /approve <user_id> <amount> <unit>\nExample: /approve 123456789 7 days",
        "usage_disapprove": "Usage: /disapprove <user_id>\nExample: /disapprove 123456789",
        "usage_setratelimit": "Usage: /setratelimit <seconds>\nExample: /setratelimit 600 (for 10 minutes)",
        "usage_broadcast": "Usage: /broadcast <your message>",
        "usage_broadcast_approved": "Usage: /broadcast_approved <your message>",
        "invalid_unit": "❌ Invalid unit. Use 'hours', 'days', or 'months'.",
        "invalid_input": "❌ Invalid input. Please use the correct format: {format}",
        "cannot_disapprove_admin": "❌ You cannot disapprove the main admin.",
        "user_not_approved": "⚠️ User {uid} was not in the approved list.",
        "user_approved": "✅ User {uid} has been approved until {expiry_date}.",
        "user_disapproved": "✅ User {uid} has been disapproved.",
        "rate_limit_updated": "✅ Rate limit updated to {seconds} seconds ({time_str}).",
        "broadcast_complete": "✅ Broadcast complete.\n\n✅ Successful: {success_count}\n❌ Failed: {fail_count}",
        "broadcast_approved_complete": "✅ Broadcast to approved users complete.\n\n✅ Successful: {success_count}\n❌ Failed: {fail_count}",
        "syncing": "🔄 Syncing data files...",
        "sync_success": "✅ All data files successfully synced.",
        "sync_failed": "❌ Failed to sync some data files. Please check the logs.",
        "no_approved_users": "There are no approved users.",
        "no_users": "No users have interacted with the bot yet.",
        "invalid_user_id": "❌ Invalid User ID. Please provide a valid numerical ID.",
        "list_too_long": "The list was too long and has been sent as a file.",
        "access_expired": "⏳ Your access has expired.\n\nPlease contact the admin to renew your subscription.\nUse /admin for contact details.",
        "access_approved": "🎉 Congratulations! Your access has been approved.\n\nYou can use the bot until {expiry_date}.\n\nEnjoy the premium service!",
        "access_revoked": "🚫 Your access has been revoked by the admin.\n\nPlease contact the admin for more details if you think this is a mistake.\nUse /admin for contact details.",
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
        "new_referral_notification": "🎉 Good news! Someone joined using your referral link.\n\nYou now have {referral_count}/3 referrals.\n\nKeep sharing to earn free access!",
        "cleanup_expired": "🧹 Cleaning up expired users...",
        "cleanup_complete": "✅ Cleanup complete. Removed {count} expired users.",
        "user_already_approved": "⚠️ User {uid} is already approved until {expiry_date}.",
        "select_user": "Select a user to view details:",
        "user_details": "👤 User Details\n\nID: {user_id}\nName: {first_name} {last_name}\nUsername: @{username}\nLanguage: {language}\nLast Interaction: {last_interaction}\nApproved: {approved}\nNumbers Checked: {numbers_checked}\n{expiry_info}",
        "export_data_msg": "📦 Export Data\n\nYour bot data is being prepared for download.\n\nThis may take a moment if you have many users.",
        "export_complete": "✅ Export complete. The data has been sent as a zip file.",
        "select_user_to_approve": "Select a user to approve:",
        "select_plan_for_user": "Select a plan for {user_name}:",
        "page_info": "Page {current_page}/{total_pages}",
        "no_pending_users": "There are no pending users to approve.",
        "change_rate_limit_msg": "⚙️ Change Rate Limit\n\nCurrent rate limit: {current_limit} seconds ({current_time_str})\n\nPlease send the new rate limit in seconds using the command:\n/setratelimit <seconds>\n\nExample: /setratelimit 600 (for 10 minutes)"
    },
    "bn": {
        "welcome": "👋 হ্যালো {first_name}!\n\nফেসবুক নম্বর চেকার বটে স্বাগতম।\n\nঅনুগ্রহ করে আপনার পছন্দের ভাষা নির্বাচন করুন:",
        "language_selected": "✅ ভাষা বাংলায় সেট করা হয়েছে।\n\nএটি একটি প্রিমিয়াম সার্ভিস। আমাকে ফোন নম্বরের তালিকা পাঠান যাচাই করার জন্য।\n\n🔐 অ্যাক্সেস প্রয়োজন? /admin ব্যবহার করে সাপোর্টের সাথে যোগাযোগ করুন।",
        "example": "উদাহরণ:\n+8801712345678\n+8801812345678",
        "access_denied": "🚫 অ্যাক্সেস প্রত্যাখ্যান করা হয়েছে!\n\nএটি শুধুমাত্র পেইড ইউজারদের জন্য একটি প্রিমিয়াম সার্ভিস। এটি হার সীমাবদ্ধতা এড়াতে একটি VPS এবং প্রিমিয়াম প্রক্সি ব্যবহার করে চলে।\n\nআপনার ইউজার ID: {uid}\n\nঅ্যাক্সেস পেতে অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।\nসাপোর্টের যোগাযোগের জন্য /admin ব্যবহার করুন।",
        "buy_online": "অনলাইনে কিনুন (শীঘ্রই আসছে)",
        "refer_earn": "রেফার করুন এবং ফ্রি অ্যাক্সেস অর্জন করুন",
        "buy_online_msg": "🛒 অনলাইনে কিনুন\n\nঅনলাইন পেমেন্ট অপশন শীঘ্রই আসছে!\n\nএখন, অ্যাক্সেস কেনার জন্য সরাসরি অ্যাডমিনের সাথে যোগাযোগ করুন।\nযোগাযোগের বিবরণের জন্য /admin ব্যবহার করুন।",
        "refer_link": "🔗 আপনার রেফারেল লিঙ্ক\n\nআপনার বন্ধুদের সাথে এই লিঙ্কটি শেয়ার করুন:\n{referral_link}\n\nরেফারেল: {referral_count}/3\n",
        "refer_earned": "✅ আপনি রেফারেলের মাধ্যমে 2 ঘন্টার ফ্রি অ্যাক্সেস অর্জন করেছেন!\n",
        "refer_needed": "❌ 2 ঘন্টার ফ্রি অ্যাক্সেস পেতে আপনার {remaining} আরও রেফারেল(স) প্রয়োজন।\n",
        "referral_status": "🔗 আপনার রেফারেল স্ট্যাটাস\n\nআপনার রেফারেল কোড: {referral_code}\nআপনার রেফারেল লিঙ্ক:\n{referral_link}\n\nরেফারেল: {referral_count}/3\n",
        "access_until": "✅ আপনার অ্যাক্সেস আছে পর্যন্ত: {expiry_date}\n",
        "permanent_access": "✅ আপনার স্থায়ী অ্যাক্সেস আছে।\n",
        "processing": "🚀 আপনার নম্বরগুলি প্রক্রিয়া করা হচ্ছে... অনুগ্রহ করে অপেক্ষা করুন।",
        "no_numbers": "❌ আপনি কোনো বৈধ নম্বর পাঠাননি। অনুগ্রহ করে নম্বরগুলি পাঠান, এক লাইনে একটি করে।",
        "check_complete": "--- ✅ যাচাই সম্পন্ন! ---\n\n",
        "found_numbers": "✅ পাওয়া নম্বর:\n",
        "not_found_numbers": "❌ পাওয়া যায়নি এমন নম্বর:\n",
        "errors_unknown": "⚠️ ত্রুটি/অজানা:\n",
        "no_valid_numbers": "কোনো নম্বর প্রক্রিয়া করা যায়নি। অনুগ্রহ করে ফরম্যাট চেক করুন।",
        "rate_limit": "⏳ রেট লিমিট অতিক্রান্ত!\n\nআপনি প্রতি {time_limit} শুধুমাত্র একবার রিকোয়েস্ট করতে পারেন।\n\nআবার চেষ্টা করার আগে অনুগ্রহ করে {remaining_time} অপেক্ষা করুন।",
        "admin_contact": "👑 অ্যাডমিন যোগাযোগ তথ্য\n\n👤 নাম: {admin_name}\n🆔 ID: {admin_id}\n🔗 ইউজারনেম: {admin_username}\n\nঅনুমোদন বা সাপোর্টের জন্য অ্যাডমিনের সাথে যোগাযোগ করুন।",
        "price_list": "💰 মূল্য তালিকা\n\n",
        "payment_methods": "\n💳 পেমেন্ট পদ্ধতি:\n• বিকাশ\n• নগদ\n• রকেট\n• পেপাল\n• ক্রিপ্টো\n\n📩 কেনার জন্য, অনুগ্রহ করে অ্যাডমিনের সাথে যোগাযোগ করুন।\nযোগাযোগের বিবরণের জন্য /admin ব্যবহার করুন।",
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
        "bot_statistics": "📊 বট পরিসংখ্যান\n\n👥 মোট ইউজার: {total_users}\n✅ অনুমোদিত ইউজার: {approved_users}\n⏳ অপেক্ষমাণ ইউজার: {pending_users}\n🔗 মোট রেফারেল: {total_referrals}\n🔢 মোট নম্বর চেক করা হয়েছে: {total_numbers_checked}\n\n📅 সর্বশেষ আপডেট: {last_updated}",
        "current_price_list": "💰 বর্তমান মূল্য তালিকা\n\n",
        "approve_user_msg": "➕ ইউজার অনুমোদন করুন\n\nঅনুগ্রহ করে ইউজার ID এবং সময়কাল পাঠান ফরম্যাটে:\n/approve <user_id> <amount> <unit>\n\nউদাহরণ: /approve 123456789 7 days\n\nউপলব্ধ ইউনিট: hours, days, months",
        "disapprove_user_msg": "➖ ইউজার অনুমোদন বাতিল করুন\n\nঅনুগ্রহ করে ইউজার ID পাঠান ফরম্যাটে:\n/disapprove <user_id>\n\nউদাহরণ: /disapprove 123456789",
        "broadcast_all_msg": "📢 সমস্ত ইউজারদের কাছে প্রচার করুন\n\nঅনুগ্রহ করে আপনার বার্তা পাঠান ফরম্যাটে:\n/broadcast <আপনার বার্তা>\n\nউদাহরণ: /broadcast সবাইকে হ্যালো! বটটি 2 ঘন্টার জন্য রক্ষণাবেক্ষণে থাকবে।",
        "broadcast_approved_msg": "📢 অনুমোদিত ইউজারদের কাছে প্রচার করুন\n\nঅনুগ্রহ করে আপনার বার্তা পাঠান ফরম্যাটে:\n/broadcast_approved <আপনার বার্তা>\n\nউদাহরণ: /broadcast_approved বটে নতুন বৈশিষ্ট্য যোগ করা হয়েছে!",
        "unauthorized": "❌ আপনি এই কমান্ড ব্যবহার করার অনুমতি পাননি।",
        "usage_approve": "ব্যবহার: /approve <user_id> <amount> <unit>\nউদাহরণ: /approve 123456789 7 days",
        "usage_disapprove": "ব্যবহার: /disapprove <user_id>\nউদাহরণ: /disapprove 123456789",
        "usage_setratelimit": "ব্যবহার: /setratelimit <seconds>\nউদাহরণ: /setratelimit 600 (10 মিনিটের জন্য)",
        "usage_broadcast": "ব্যবহার: /broadcast <আপনার বার্তা>",
        "usage_broadcast_approved": "ব্যবহার: /broadcast_approved <আপনার বার্তা>",
        "invalid_unit": "❌ অবৈধ ইউনিট। 'hours', 'days', বা 'months' ব্যবহার করুন।",
        "invalid_input": "❌ অবৈধ ইনপুট। অনুগ্রহ করে সঠিক ফরম্যাট ব্যবহার করুন: {format}",
        "cannot_disapprove_admin": "❌ আপনি প্রধান অ্যাডমিনকে অনুমোদন বাতিল করতে পারবেন না।",
        "user_not_approved": "⚠️ ইউজার {uid} অনুমোদিত তালিকায় ছিল না।",
        "user_approved": "✅ ইউজার {uid} কে {expiry_date} পর্যন্ত অনুমোদন করা হয়েছে।",
        "user_disapproved": "✅ ইউজার {uid} এর অনুমোদন বাতিল করা হয়েছে।",
        "rate_limit_updated": "✅ রেট লিমিট {seconds} সেকেন্ডে ({time_str}) আপডেট করা হয়েছে।",
        "broadcast_complete": "✅ প্রচার সম্পন্ন।\n\n✅ সফল: {success_count}\n❌ ব্যর্থ: {fail_count}",
        "broadcast_approved_complete": "✅ অনুমোদিত ইউজারদের কাছে প্রচার সম্পন্ন।\n\n✅ সফল: {success_count}\n❌ ব্যর্থ: {fail_count}",
        "syncing": "🔄 ডেটা ফাইল সিঙ্ক করা হচ্ছে...",
        "sync_success": "✅ সমস্ত ডেটা ফাইল সফলভাবে সিঙ্ক করা হয়েছে।",
        "sync_failed": "❌ কিছু ডেটা ফাইল সিঙ্ক করতে ব্যর্থ হয়েছে। অনুগ্রহ করে লগ চেক করুন।",
        "no_approved_users": "কোনো অনুমোদিত ইউজার নেই।",
        "no_users": "এখনো কোনো ইউজার বটের সাথে ইন্টারঅ্যাক্ট করেনি।",
        "invalid_user_id": "❌ অবৈধ ইউজার ID। অনুগ্রহ করে একটি বৈধ সংখ্যাসূচক ID প্রদান করুন।",
        "list_too_long": "The list was too long and has been sent as a file.",
        "access_expired": "⏳ Your access has expired.\n\nPlease contact the admin to renew your subscription.\nUse /admin for contact details.",
        "access_approved": "🎉 Congratulations! Your access has been approved.\n\nYou can use the bot until {expiry_date}.\n\nEnjoy the premium service!",
        "access_revoked": "🚫 Your access has been revoked by the admin.\n\nPlease contact the admin for more details if you think this is a mistake.\nUse /admin for contact details.",
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
        "new_referral_notification": "🎉 সুসংবাদ! কেউ আপনার রেফারেল লিঙ্ক ব্যবহার করে যোগ দিয়েছে।\n\nআপনার এখন {referral_count}/3 রেফারেল আছে।\n\nফ্রি অ্যাক্সেস পেতে শেয়ার করা চালিয়ে যান!",
        "cleanup_expired": "🧹 মেয়াদোত্তীর্ণ ইউজারদের পরিষ্কার করা হচ্ছে...",
        "cleanup_complete": "✅ পরিষ্কার সম্পন্ন। {count} জন মেয়াদোত্তীর্ণ ইউজার মুছে ফেলা হয়েছে।",
        "user_already_approved": "⚠️ ইউজার {uid} ইতিমধ্যে {expiry_date} পর্যন্ত অনুমোদিত।",
        "select_user": "একজন ইউজার নির্বাচন করুন বিস্তারিত দেখতে:",
        "user_details": "👤 ইউজার বিস্তারিত\n\nID: {user_id}\nনাম: {first_name} {last_name}\nইউজারনেম: @{username}\nভাষা: {language}\nশেষ ইন্টারঅ্যাকশন: {last_interaction}\nঅনুমোদিত: {approved}\nনম্বর চেক করা হয়েছে: {numbers_checked}\n{expiry_info}",
        "export_data_msg": "📦 ডেটা এক্সপোর্ট করুন\n\nআপনার বট ডেটা ডাউনলোডের জন্য প্রস্তুত করা হচ্ছে।\n\nআপনার যদি অনেক ইউজার থাকে তবে এটি কিছুক্ষণ সময় নিতে পারে।",
        "export_complete": "✅ এক্সপোর্ট সম্পন্ন। ডেটা একটি জিপ ফাইল হিসেবে পাঠানো হয়েছে।",
        "select_user_to_approve": "অনুমোদনের জন্য একজন ইউজার নির্বাচন করুন:",
        "select_plan_for_user": "{user_name} এর জন্য একটি প্ল্যান নির্বাচন করুন:",
        "page_info": "পৃষ্ঠা {current_page}/{total_pages}",
        "no_pending_users": "অনুমোদনের জন্য কোনো অপেক্ষমাণ ইউজার নেই।",
        "change_rate_limit_msg": "⚙️ রেট লিমিট পরিবর্তন করুন\n\nবর্তমান রেট লিমিট: {current_limit} সেকেন্ড ({current_time_str})\n\nঅনুগ্রহ করে কমান্ড ব্যবহার করে নতুন রেট লিমিট সেকেন্ডে পাঠান:\n/setratelimit <seconds>\n\nউদাহরণ: /setratelimit 600 (10 মিনিটের জন্য)"
    }
}

# --- DATA FOR FACEBOOK API ---
url = 'https://www.facebook.com/ajax/login/help/identify.php?ctx=recover'
headers = {
    'accept': '*/*',
    'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8',
    'content-type': 'application/x-www-form-urlencoded',
    'origin': 'https://www.facebook.com',
    'priority': 'u=1, i',
    'referer': 'https://www.facebook.com/login/identify/?ctx=recover&from_login_screen=0',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1 Edg/141.0.0.0',
    'x-asbd-id': '359341',
    'x-fb-lsd': 'AdE3czGo7uw'
}
cookies = {
    'datr': '5BfuaP5MJ81CQGWO4JTj_FQA',
    'wd': '980x2125'
}
base_data = {
    'jazoest': '2979',
    'lsd': 'AdE3czGo7uw',
    'email': 'number',
    'did_submit': '1',
    '__user': '0',
    '__a': '1',
    '__req': '7',
    '__hs': '20375.BP%3ADEFAULT.2.0...0',
    'dpr': '1',
    '__ccg': 'EXCELLENT',
    '__rev': '1028355510',
    '__s': 'uwimyp%3Awq8ee5%3Af3twai',
    '__hsi': '7561007094168113829',
    '__dyn': '7xeUmwkHg7ebwKBAg5S1Dxu13wqovzEdEc8uxa0CEbo1nEhw2nVE4W0qa0FE2awt81s8hwGwQw4iwBgao6C0Mo2swaO4U2zxe3C0D85a1qw8Xxm16wa-0raazo11E2ZwrU6C0hq1Iw6PG2O1TwmU3ywo81V8',
    '__hsdp': 'gOMT1Cx0jK93aiyib89DxiZCmvzosxR1B04ywjofV4ciw5Ew',
    '__hblp': '0Ww9W11wd20CU0xK0hS0aCw5Gw3fo0wO05Mo0Ei01pfw4Rw4ayrG3m0lK0B829wt83oUhw2sE0sdw',
    '__spin_r': '1028355510',
    '__spin_b': 'trunk',
    '__spin_t': '1760434148'
}

# --- LOCAL FILE FUNCTIONS (REFACTORED WITH AIOFILES) ---

async def load_config_from_file():
    """Load config from local file asynchronously."""
    global config_data
    try:
        if os.path.exists(CONFIG_FILE):
            async with aiofiles.open(CONFIG_FILE, 'r') as f:
                content = await f.read()
                config_data = json.loads(content)
            logger.info("Successfully loaded config from file")
        else:
            # Create the file if it doesn't exist
            await save_config_to_file()
    except Exception as e:
        logger.error(f"Error loading config from file: {e}")

async def save_config_to_file():
    """Save config to local file asynchronously and mirror to MySQL."""
    try:
        async with aiofiles.open(CONFIG_FILE, 'w') as f:
            await f.write(json.dumps(config_data, indent=2))
        logger.info("Successfully saved config to file")
    except Exception as e:
        logger.error(f"Error saving config to file: {e}")

    try:
        await save_config_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving config to MySQL: {e}")
        return False

async def load_users_from_file():
    """Load approved users from local file asynchronously."""
    global approved_users
    try:
        if os.path.exists(USER_DATA_FILE):
            async with aiofiles.open(USER_DATA_FILE, 'r') as f:
                content = await f.read()
                loaded_users = json.loads(content)

            temp_approved_users = {}
            for user_id_str, expiry_date in loaded_users.items():
                try:
                    user_id = int(user_id_str)
                    if expiry_date is not None:
                        temp_approved_users[user_id] = datetime.fromisoformat(expiry_date)
                    else:
                        temp_approved_users[user_id] = None
                except (ValueError, TypeError) as e:
                    logger.error(f"Error converting user ID {user_id_str}: {e}")

            temp_approved_users[ADMIN_ID] = None
            approved_users = temp_approved_users
            logger.info(f"Successfully loaded {len(approved_users)} users from file")
        else:
            approved_users = {ADMIN_ID: None}
            await save_users_to_file()

    except Exception as e:
        logger.error(f"Error loading users from file: {e}")
        approved_users = {ADMIN_ID: None}

async def load_all_users_from_file():
    """Load all users from local file asynchronously."""
    global all_users
    try:
        if os.path.exists(ALL_USERS_FILE):
            async with aiofiles.open(ALL_USERS_FILE, 'r') as f:
                content = await f.read()
                all_users = json.loads(content)
            logger.info(f"Successfully loaded {len(all_users)} all users from file")
        else:
            all_users = {}
            await save_all_users_to_file()
    except Exception as e:
        logger.error(f"Error loading all users from file: {e}")
        all_users = {}

async def load_referral_data_from_file():
    """Load referral data from local file asynchronously."""
    global referral_data
    try:
        if os.path.exists(REFERRAL_DATA_FILE):
            async with aiofiles.open(REFERRAL_DATA_FILE, 'r') as f:
                content = await f.read()
                referral_data = json.loads(content)
            logger.info("Successfully loaded referral data from file")
        else:
            referral_data = {}
            await save_referral_data_to_file()
    except Exception as e:
        logger.error(f"Error loading referral data from file: {e}")
        referral_data = {}

async def load_price_list_from_file():
    """Load price list from local file asynchronously."""
    global price_list
    try:
        if os.path.exists(PRICE_LIST_FILE):
            async with aiofiles.open(PRICE_LIST_FILE, 'r') as f:
                content = await f.read()
                price_list = json.loads(content)
            logger.info("Successfully loaded price list from file")
        else:
            await save_price_list_to_file()
    except Exception as e:
        logger.error(f"Error loading price list from file: {e}")

async def load_user_settings_from_file():
    """Load user settings from local file asynchronously."""
    global user_settings
    try:
        if os.path.exists(USER_SETTINGS_FILE):
            async with aiofiles.open(USER_SETTINGS_FILE, 'r') as f:
                content = await f.read()
                user_settings = json.loads(content)
            logger.info("Successfully loaded user settings from file")
        else:
            user_settings = {}
            await save_user_settings_to_file()
    except Exception as e:
        logger.error(f"Error loading user settings from file: {e}")
        user_settings = {}

async def save_users_to_file():
    """Save approved users to local file asynchronously and mirror to MySQL."""
    try:
        users_to_save = {}
        for user_id, expiry_date in approved_users.items():
            if expiry_date is None:
                users_to_save[str(user_id)] = None
            else:
                users_to_save[str(user_id)] = expiry_date.isoformat()

        async with aiofiles.open(USER_DATA_FILE, 'w') as f:
            await f.write(json.dumps(users_to_save, indent=2))

        logger.info(f"Successfully saved {len(approved_users)} users to file")
    except Exception as e:
        logger.error(f"Error saving users to file: {e}")

    # Mirror to MySQL (best effort)
    try:
        await save_users_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving users to MySQL: {e}")
        return False

async def save_all_users_to_file():
    """Save all users to local file asynchronously and mirror to MySQL."""
    try:
        async with aiofiles.open(ALL_USERS_FILE, 'w') as f:
            await f.write(json.dumps(all_users, indent=2))
        logger.info("Successfully saved all users to file")
    except Exception as e:
        logger.error(f"Error saving all users to file: {e}")

    try:
        await save_all_users_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving all users to MySQL: {e}")
        return False

async def save_referral_data_to_file():
    """Save referral data to local file asynchronously and mirror to MySQL."""
    try:
        async with aiofiles.open(REFERRAL_DATA_FILE, 'w') as f:
            await f.write(json.dumps(referral_data, indent=2))
        logger.info("Successfully saved referral data to file")
    except Exception as e:
        logger.error(f"Error saving referral data to file: {e}")

    try:
        await save_referral_data_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving referral data to MySQL: {e}")
        return False

async def save_price_list_to_file():
    """Save price list to local file asynchronously."""
    try:
        async with aiofiles.open(PRICE_LIST_FILE, 'w') as f:
            await f.write(json.dumps(price_list, indent=2))
        logger.info("Successfully saved price list to file")
        return True
    except Exception as e:
        logger.error(f"Error saving price list to file: {e}")
        return False

async def save_user_settings_to_file():
    """Save user settings to local file asynchronously and mirror to MySQL."""
    try:
        async with aiofiles.open(USER_SETTINGS_FILE, 'w') as f:
            await f.write(json.dumps(user_settings, indent=2))
        logger.info("Successfully saved user settings to file")
    except Exception as e:
        logger.error(f"Error saving user settings to file: {e}")

    try:
        await save_user_settings_to_db()
        return True
    except Exception as e:
        logger.error(f"Error saving user settings to MySQL: {e}")
        return False

async def save_user_details_to_file(user_id, user_data):
    """Save specific user details to local file asynchronously and mirror to MySQL if configured."""
    try:
        users_dir = os.path.join(DATA_DIR, "users")
        if not os.path.exists(users_dir):
            os.makedirs(users_dir)

        filename = os.path.join(users_dir, f"{user_id}.json")
        async with aiofiles.open(filename, 'w') as f:
            await f.write(json.dumps(user_data, indent=2))

        logger.info(f"Successfully saved user {user_id} details to file")
    except Exception as e:
        logger.error(f"Error saving user {user_id} details to file: {e}")

    # Mirror to MySQL (best effort, does not affect local file flow)
    try:
        await save_user_to_db(user_id, user_data)
        return True
    except Exception as e:
        logger.error(f"Error saving user {user_id} details to MySQL: {e}")
        return False


# --- MYSQL DATABASE HELPERS ---

async def get_db_pool():
    """Get (or create) a global aiomysql connection pool."""
    global db_pool
    if db_pool is not None:
        return db_pool

    try:
        db_pool = await aiomysql.create_pool(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DB,
            autocommit=True,
            minsize=1,
            maxsize=10
        )
        logger.info("MySQL connection pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create MySQL pool: {e}")
        db_pool = None

    return db_pool


async def init_db():
    """Create required tables if they do not exist."""
    pool = await get_db_pool()
    if pool is None:
        # If MySQL is not configured / not reachable, silently skip
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
        """
    ]

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            for q in create_table_queries:
                try:
                    await cur.execute(q)
                except Exception as e:
                    logger.error(f"Error creating table: {e}")


async def save_users_to_db():
    """Mirror in-memory approved_users dict to MySQL approved_users table."""
    pool = await get_db_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                await cur.execute("DELETE FROM approved_users")
                for user_id, expiry in approved_users.items():
                    # store None as NULL
                    expiry_str = expiry.strftime("%Y-%m-%d %H:%M:%S") if expiry is not None else None
                    await cur.execute(
                        "REPLACE INTO approved_users (user_id, expiry_datetime) VALUES (%s, %s)",
                        (int(user_id), expiry_str),
                    )
            except Exception as e:
                logger.error(f"Error saving approved_users to MySQL: {e}")


async def save_all_users_to_db():
    """Mirror in-memory all_users dict to MySQL all_users table."""
    pool = await get_db_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
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
                        REPLACE INTO all_users (user_id, first_name, last_name, username, last_interaction, numbers_checked)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (user_id, first_name, last_name, username, last_interaction, numbers_checked),
                    )
            except Exception as e:
                logger.error(f"Error saving all_users to MySQL: {e}")


async def save_referral_data_to_db():
    """Mirror in-memory referral_data dict to MySQL referral_data table."""
    pool = await get_db_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
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
                        REPLACE INTO referral_data (user_id, referral_code, referred_by, referred_users_json)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, referral_code, int(referred_by) if referred_by else None, referred_users_json),
                    )
            except Exception as e:
                logger.error(f"Error saving referral_data to MySQL: {e}")


async def save_user_settings_to_db():
    """Mirror in-memory user_settings dict to MySQL user_settings table."""
    pool = await get_db_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
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


async def save_config_to_db():
    """Mirror in-memory config_data dict to MySQL config table."""
    pool = await get_db_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
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


async def save_user_to_db(user_id, user_data):
    """Insert/update a single user row in all_users + user_settings tables."""
    pool = await get_db_pool()
    if pool is None:
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            try:
                first_name = user_data.get("first_name")
                last_name = user_data.get("last_name")
                username = user_data.get("username")
                last_interaction = user_data.get("last_interaction")
                numbers_checked = user_data.get("numbers_checked", 0)

                await cur.execute(
                    """
                    REPLACE INTO all_users (user_id, first_name, last_name, username, last_interaction, numbers_checked)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (int(user_id), first_name, last_name, username, last_interaction, numbers_checked),
                )

                # also update user_settings language if present
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

# --- LANGUAGE FUNCTIONS ---

def get_user_language(user_id):
    """Get the user's preferred language."""
    user_id_str = str(user_id)
    if user_id_str in user_settings:
        return user_settings[user_id_str].get("language", "en")
    return "en"

async def set_user_language(user_id, language):
    """Set the user's preferred language."""
    user_id_str = str(user_id)
    if user_id_str not in user_settings:
        user_settings[user_id_str] = {}

    user_settings[user_id_str]["language"] = language
    await save_user_settings_to_file()

def get_text(user_id, key, **kwargs):
    """Get localized text based on user's language preference."""
    language = get_user_language(user_id)
    text = LANGUAGES.get(language, LANGUAGES["en"]).get(key, "")

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.error(f"Error formatting text: {e}")

    return text

# --- REFERRAL FUNCTIONS ---

def generate_referral_code(length=8):
    """Generate a random referral code."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def get_or_create_referral_code(user_id):
    """Get existing referral code or create a new one for the user."""
    user_id_str = str(user_id)
    if user_id_str not in referral_data:
        referral_data[user_id_str] = {
            "referral_code": generate_referral_code(),
            "referred_by": None,
            "referred_users": []
        }
        await save_referral_data_to_file()

    return referral_data[user_id_str]["referral_code"]

async def process_referral(referrer_id, referred_id, context: ContextTypes.DEFAULT_TYPE):
    """Process a referral and update referral data."""
    referrer_id_str = str(referrer_id)
    referred_id_str = str(referred_id)

    # Check if the referred user already exists
    if referred_id_str in referral_data:
        return False, get_text(referred_id, "already_used_bot")

    # Check if the referrer exists
    if referrer_id_str not in referral_data:
        return False, get_text(referred_id, "invalid_referral")

    # Create referral data for the new user
    referral_data[referred_id_str] = {
        "referral_code": generate_referral_code(),
        "referred_by": referrer_id_str,
        "referred_users": []
    }

    # Add the new user to the referrer's referred users list
    if referrer_id_str in referral_data:
        if "referred_users" not in referral_data[referrer_id_str]:
            referral_data[referrer_id_str]["referred_users"] = []

        # Check if this user is already in the referred list
        if referred_id_str not in referral_data[referrer_id_str]["referred_users"]:
            referral_data[referrer_id_str]["referred_users"].append(referred_id_str)

    # Save the updated referral data
    await save_referral_data_to_file()

    # Get the updated referral count
    referral_count = len(referral_data[referrer_id_str]["referred_users"])

    # Send notification to the referrer about the new referral
    await send_user_notification(
        context,
        int(referrer_id_str),
        get_text(referrer_id, "new_referral_notification", referral_count=referral_count)
    )

    # Check if the referrer has reached the required number of referrals
    if referral_count >= 3:
        # Grant access to the referrer
        expiry_date = datetime.now(timezone.utc) + timedelta(hours=2)
        approved_users[int(referrer_id_str)] = expiry_date
        await save_users_to_file()

        # Send notification to the referrer about earning access
        await send_user_notification(
            context,
            int(referrer_id_str),
            get_text(referrer_id, "referral_earned")
        )

        return True, get_text(referred_id, "referral_successful", referral_count=referral_count)

    # Return success with the updated referral count for the referred user
    return True, get_text(referred_id, "referral_successful", referral_count=referral_count)

async def track_user(user, update: Update = None):
    """Track all users who interact with the bot."""
    user_id = str(user.id)

    if user_id not in all_users:
        all_users[user_id] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "last_interaction": datetime.now().isoformat(),
            "numbers_checked": 0  # Initialize number counter
        }
        await save_all_users_to_file()
    else:
        all_users[user_id]["last_interaction"] = datetime.now().isoformat()
        await save_all_users_to_file()

# --- HELPER FUNCTIONS ---

# --- REFACTORED with httpx ---
async def check_facebook_number(client: httpx.AsyncClient, phone_number: str):
    """Checks a specific phone number asynchronously and returns its status."""
    data = base_data.copy()
    data['email'] = phone_number

    try:
        response = await client.post(url, headers=headers, cookies=cookies, data=data)
        response.raise_for_status()

        response_text = response.text
        if response_text.startswith('for (;;);'):
            json_string = response_text[9:]
            data_json = json.loads(json_string)
        else:
            data_json = json.loads(response_text)

        if 'jsmods' in data_json and 'require' in data_json['jsmods']:
            for requirement in data_json['jsmods']['require']:
                if isinstance(requirement, list) and len(requirement) > 0 and requirement[0] == 'ServerRedirect':
                    return "Found"

        if 'domops' in data_json:
            for op in data_json['domops']:
                if isinstance(op, list) and len(op) > 3 and isinstance(op[3], dict) and '__html' in op[3]:
                    html_content = op[3]['__html']
                    if 'No search results' in html_content:
                        return "Not Found"

        return "Unknown Response (Possible CAPTCHA or Page Change)"

    except httpx.RequestError as e:
        logger.warning(f"httpx RequestError for {phone_number}: {e}")
        return f"Error: {e}"
    except json.JSONDecodeError:
        logger.warning(f"json.JSONDecodeError for {phone_number}: (Possibly Blocked)")
        return "Error: Invalid JSON (Possibly Blocked)"
    except Exception as e:
        logger.error(f"Unexpected error in check_facebook_number for {phone_number}: {e}")
        return f"Error: {e}"

async def send_user_notification(context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Sends a notification to a user and handles potential errors."""
    try:
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode='HTML')
    except Exception as e:
        # আরও ভালো এরর হ্যান্ডলিং
        if "Chat not found" in str(e):
            logger.warning(f"Could not send notification to user {user_id}: User has not interacted with the bot or has blocked it")
        elif "Forbidden: bot was blocked by the user" in str(e):
            logger.warning(f"Could not send notification to user {user_id}: User has blocked the bot")
        else:
            logger.error(f"Could not send notification to user {user_id}: {e}")

def is_user_approved(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Checks if a user is approved and if their access has expired."""
    if user_id == ADMIN_ID:
        return True

    if user_id not in approved_users:
        return False

    expiry_date = approved_users.get(user_id)
    if expiry_date is None:
        return False

    if datetime.now(timezone.utc) > expiry_date:
        del approved_users[user_id]
        logger.info(f"User {user_id}'s access has expired.")
        asyncio.create_task(send_user_notification(
            context,
            user_id,
            get_text(user_id, "access_expired")
        ))
        asyncio.create_task(save_users_to_file())
        return False

    return True

# --- RATE LIMIT FUNCTION ---

def check_rate_limit(user_id: int):
    """Check if user is rate limited."""
    current_time = datetime.now(timezone.utc)
    rate_limit_seconds = config_data.get("rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS)
    
    # Check if user has made a request before
    if user_id in user_last_request:
        last_request_time = user_last_request[user_id]
        time_diff = (current_time - last_request_time).total_seconds()
        
        # If less than RATE_LIMIT_SECONDS have passed, user is rate limited
        if time_diff < rate_limit_seconds:
            remaining_time = rate_limit_seconds - int(time_diff)
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            
            if minutes > 0:
                time_str = f"{minutes} minute{'s' if minutes > 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
            else:
                time_str = f"{seconds} second{'s' if seconds != 1 else ''}"
            
            return False, time_str
    
    # Update the last request time
    user_last_request[user_id] = current_time
    return True, None

# --- CLEANUP FUNCTION ---

async def cleanup_expired_users():
    """Remove expired users from the approved_users list."""
    global approved_users
    current_time = datetime.now(timezone.utc)
    expired_users = []
    
    # Create a list of expired users to avoid modifying the dictionary while iterating
    for user_id, expiry_date in list(approved_users.items()):
        if user_id != ADMIN_ID and expiry_date is not None and current_time > expiry_date:
            expired_users.append(user_id)
    
    # Remove expired users
    for user_id in expired_users:
        del approved_users[user_id]
        logger.info(f"Removed expired user {user_id}")
    
    # Save the updated list
    if expired_users:
        await save_users_to_file()
    
    return len(expired_users)

async def auto_cleanup_task(context: ContextTypes.DEFAULT_TYPE):
    """Periodically clean up expired users."""
    while True:
        try:
            removed_count = await cleanup_expired_users()
            if removed_count > 0:
                logger.info(f"Auto cleanup removed {removed_count} expired users")
            await asyncio.sleep(AUTO_CLEANUP_INTERVAL)
        except Exception as e:
            logger.error(f"Error in auto cleanup task: {e}")
            await asyncio.sleep(AUTO_CLEANUP_INTERVAL)

# --- EXPORT DATA FUNCTION ---

async def export_bot_data():
    """Export all bot data as a zip file."""
    try:
        # Create a BytesIO object to store the zip file in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add approved users data
            users_to_save = {}
            for user_id, expiry_date in approved_users.items():
                if expiry_date is None:
                    users_to_save[str(user_id)] = None
                else:
                    users_to_save[str(user_id)] = expiry_date.isoformat()
            
            zip_file.writestr("approved_users.json", json.dumps(users_to_save, indent=2))
            
            # Add all users data
            zip_file.writestr("all_users.json", json.dumps(all_users, indent=2))
            
            # Add referral data
            zip_file.writestr("referral_data.json", json.dumps(referral_data, indent=2))
            
            # Add price list
            zip_file.writestr("price_list.json", json.dumps(price_list, indent=2))
            
            # Add user settings
            zip_file.writestr("user_settings.json", json.dumps(user_settings, indent=2))
            
            # Add config
            zip_file.writestr("config.json", json.dumps(config_data, indent=2))
            
            # Add individual user files if they exist
            users_dir = os.path.join(DATA_DIR, "users")
            if os.path.exists(users_dir):
                for filename in os.listdir(users_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(users_dir, filename)
                        # REFACTORED: Use async read for consistency (though sync is fine here)
                        async with aiofiles.open(file_path, 'r') as f:
                            zip_file.writestr(f"users/{filename}", await f.read())
            
            # Add a summary file
            total_numbers_checked = sum(user.get("numbers_checked", 0) for user in all_users.values())
            summary = {
                "export_date": datetime.now().isoformat(),
                "total_users": len(all_users),
                "approved_users": len(approved_users) - 1,  # Exclude admin
                "total_referrals": sum(len(data.get("referred_users", [])) for data in referral_data.values()),
                "total_numbers_checked": total_numbers_checked,
                "price_list": price_list,
                "config": config_data
            }
            zip_file.writestr("summary.json", json.dumps(summary, indent=2))
        
        # Reset buffer position to the beginning
        zip_buffer.seek(0)
        
        return zip_buffer
        
    except Exception as e:
        logger.error(f"Error exporting bot data: {e}")
        return None

# --- SAFE MESSAGE EDITING ---

async def safe_edit_message(query, text, reply_markup=None, parse_mode=None):
    """Safely edit a message, handling potential errors."""
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except BadRequest as e:
        if "message is not modified" in str(e):
            return True
        elif "message to edit not found" in str(e):
            try:
                await query.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
                return True
            except Exception as e2:
                logger.error(f"Failed to send new message: {e2}")
                return False
        else:
            logger.error(f"Error editing message: {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error editing message: {e}")
        return False

# --- ADMIN PANEL FUNCTIONS ---

async def admin_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the main admin menu with inline buttons."""
    query = update.callback_query if update.callback_query else None

    if query:
        user_id = query.from_user.id
        await query.answer()
    else:
        user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        if query:
            await safe_edit_message(query, get_text(user_id, "unauthorized"))
        else:
            await update.message.reply_text(get_text(user_id, "unauthorized"))
        return

    keyboard = [
        [
            InlineKeyboardButton(get_text(user_id, "user_management"), callback_data="admin_user_management"),
            InlineKeyboardButton(get_text(user_id, "price_management"), callback_data="admin_price_management")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "communication"), callback_data="admin_communication"),
            InlineKeyboardButton(get_text(user_id, "system_management"), callback_data="admin_system")
        ],
        [
            InlineKeyboardButton(get_text(user_id, "statistics"), callback_data="admin_statistics"),
            InlineKeyboardButton(get_text(user_id, "back"), callback_data="admin_back")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if query:
        await safe_edit_message(
            query,
            get_text(user_id, "admin_panel"),
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_html(
            get_text(user_id, "admin_panel"),
            reply_markup=reply_markup
        )

async def admin_user_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the user management menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [
            InlineKeyboardButton(get_text(query.from_user.id, "approved_users"), callback_data="admin_approved_users"),
            InlineKeyboardButton(get_text(query.from_user.id, "all_users"), callback_data="admin_all_users")
        ],
        [
            InlineKeyboardButton(get_text(query.from_user.id, "approve_user"), callback_data="admin_approve_user_paginated"),
            InlineKeyboardButton(get_text(query.from_user.id, "disapprove_user"), callback_data="admin_disapprove_user")
        ],
        [
            InlineKeyboardButton("🧹 Cleanup Expired Users", callback_data="admin_cleanup_expired"),
            InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_main_menu"), callback_data="admin_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "user_management") + "\n\n" + get_text(query.from_user.id, "select_option"),
        reply_markup=reply_markup
    )

async def admin_price_management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the price management menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    # Simplified price management menu - removed edit price option
    keyboard = [
        [
            InlineKeyboardButton(get_text(query.from_user.id, "view_prices"), callback_data="admin_view_prices")
        ],
        [
            InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_main_menu"), callback_data="admin_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "price_management") + "\n\n" + get_text(query.from_user.id, "select_option"),
        reply_markup=reply_markup
    )

async def admin_communication_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the communication menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [
            InlineKeyboardButton(get_text(query.from_user.id, "broadcast_all"), callback_data="admin_broadcast_all"),
            InlineKeyboardButton(get_text(query.from_user.id, "broadcast_approved"), callback_data="admin_broadcast_approved")
        ],
        [
            InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_main_menu"), callback_data="admin_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "communication") + "\n\n" + get_text(query.from_user.id, "select_option"),
        reply_markup=reply_markup
    )

async def admin_system_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the system management menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [
            InlineKeyboardButton(get_text(query.from_user.id, "change_rate_limit"), callback_data="admin_change_rate_limit"),
            InlineKeyboardButton(get_text(query.from_user.id, "sync_files"), callback_data="admin_sync_files")
        ],
        [
            InlineKeyboardButton(get_text(query.from_user.id, "statistics"), callback_data="admin_statistics"),
            InlineKeyboardButton(get_text(query.from_user.id, "export_data"), callback_data="admin_export_data")
        ],
        [
            InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_main_menu"), callback_data="admin_main")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "system_management") + "\n\n" + get_text(query.from_user.id, "select_option"),
        reply_markup=reply_markup
    )

async def admin_statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display statistics about the bot."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    total_users = len(all_users)
    approved_users_count = len(approved_users) - 1
    pending_users = total_users - approved_users_count

    total_referrals = sum(len(data.get("referred_users", [])) for data in referral_data.values())
    total_numbers_checked = sum(user.get("numbers_checked", 0) for user in all_users.values())

    stats_text = get_text(
        query.from_user.id,
        "bot_statistics",
        total_users=total_users,
        approved_users=approved_users_count,
        pending_users=pending_users,
        total_referrals=total_referrals,
        total_numbers_checked=total_numbers_checked,
        last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_main_menu"), callback_data="admin_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        stats_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def admin_view_prices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the current price list."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    price_text = get_text(query.from_user.id, "current_price_list")

    for key, value in price_list.items():
        price_text += f"🔹 <b>{value['duration']}</b>: {value['price_bdt']} BDT / {value['price_usd']} USD\n"

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_price_management"), callback_data="admin_price_management")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        price_text,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def admin_approved_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the list of approved users with their names."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    if not approved_users:
        await safe_edit_message(query, get_text(query.from_user.id, "no_approved_users"))
        return

    # Create inline buttons for each approved user with their names
    keyboard = []
    
    for uid, expiry in approved_users.items():
        # Get user name from all_users if available
        user_name = "Unknown"
        if str(uid) in all_users:
            user_name = all_users[str(uid)].get("first_name", "Unknown")
        
        if uid == ADMIN_ID:
            button_text = f"👑 Admin: {user_name}"
        else:
            if expiry is None:
                button_text = f"✅ {user_name} (ID: {uid}) - Permanent"
            else:
                expiry_str = expiry.strftime('%Y-%m-%d')
                button_text = f"✅ {user_name} (ID: {uid}) - Expires: {expiry_str}"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_user_details_{uid}")])
    
    # Add back button
    keyboard.append([InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "approved_users") + "\n\n" + get_text(query.from_user.id, "select_user"),
        reply_markup=reply_markup
    )

async def admin_all_users_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the list of all users as inline buttons."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    if not all_users:
        await safe_edit_message(query, get_text(query.from_user.id, "no_users"))
        return

    # Create inline buttons for each user
    keyboard = []
    
    for uid, user_data in all_users.items():
        name = user_data.get("first_name", "Unknown")
        
        if uid == str(ADMIN_ID):
            button_text = f"👑 Admin: {name}"
        elif int(uid) in approved_users:
            button_text = f"✅ {name} (ID: {uid})"
        else:
            button_text = f"👤 {name} (ID: {uid})"
        
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_user_details_{uid}")])
    
    # Add back button
    keyboard.append([InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "all_users") + "\n\n" + get_text(query.from_user.id, "select_user"),
        reply_markup=reply_markup
    )

async def admin_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display details for a specific user with disapprove button for approved users."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    # আরও ভালো কলব্যাক ডেটা পার্সিং
    if not query.data or not query.data.startswith("admin_user_details_"):
        await safe_edit_message(query, "Invalid callback data format")
        return

    user_id_str = query.data.replace("admin_user_details_", "")
    
    # নিশ্চিত করুন যে user_id_str খালি নয়
    if not user_id_str:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    # নিশ্চিত করুন যে ইউজার ID সব ইউজার লিস্টে আছে
    if user_id_str not in all_users:
        await safe_edit_message(query, "User not found in all users list.")
        return
    
    user_data = all_users[user_id_str]
    
    # Get user details
    first_name = user_data.get("first_name", "Unknown")
    last_name = user_data.get("last_name", "")
    username = user_data.get("username", "None")
    last_interaction = user_data.get("last_interaction", "Unknown")
    numbers_checked = user_data.get("numbers_checked", 0)
    
    # Get user language
    language = get_user_language(user_id)
    
    # Check if user is approved
    is_approved = user_id in approved_users
    expiry_info = ""
    
    if is_approved:
        expiry_date = approved_users.get(user_id)
        if expiry_date is None:
            expiry_info = "Access: Permanent"
        else:
            expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')
            expiry_info = f"Access until: {expiry_str}"
    else:
        expiry_info = "Access: Not approved"
    
    # Get referral info
    referral_info = ""
    if user_id_str in referral_data:
        referral_code = referral_data[user_id_str].get("referral_code", "None")
        referred_by = referral_data[user_id_str].get("referred_by", "None")
        referred_users = referral_data[user_id_str].get("referred_users", [])
        
        referral_info = f"\nReferral Code: {referral_code}"
        if referred_by:
            referral_info += f"\nReferred By: {referred_by}"
        if referred_users:
            referral_info += f"\nReferred Users: {len(referred_users)}"
    
    # Create user details text - Fixed HTML parsing issue
    details_text = "👤 User Details\n\n"
    details_text += f"ID: {user_id}\n"
    details_text += f"Name: {first_name} {last_name}\n"
    details_text += f"Username: @{username}\n"
    details_text += f"Language: {language}\n"
    details_text += f"Last Interaction: {last_interaction}\n"
    details_text += f"Approved: {'Yes' if is_approved else 'No'}\n"
    details_text += f"Numbers Checked: {numbers_checked}\n"
    details_text += expiry_info
    details_text += referral_info
    
    # Create action buttons
    keyboard = []
    
    # Add disapprove button if user is approved and not admin
    if user_id != ADMIN_ID and is_approved:
        keyboard.append([InlineKeyboardButton("➖ Disapprove User", callback_data=f"admin_disapprove_user_{user_id}")])
    
    # Add approve button if user is not approved
    if not is_approved:
        keyboard.append([InlineKeyboardButton("➕ Approve User", callback_data=f"admin_approve_user_{user_id}")])
    
    keyboard.append([InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(
        query,
        details_text,
        reply_markup=reply_markup
    )

async def admin_approve_user_from_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user from the details view."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    # আরও ভালো কলব্যাক ডেটা পার্সিং
    if not query.data or not query.data.startswith("admin_approve_user_"):
        await safe_edit_message(query, "Invalid callback data format")
        return

    user_id_str = query.data.replace("admin_approve_user_", "")
    
    # নিশ্চিত করুন যে user_id_str খালি নয়
    if not user_id_str:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    # Default approval: 7 days
    expiry_date = datetime.now(timezone.utc) + timedelta(days=7)
    approved_users[user_id] = expiry_date
    expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')

    await save_users_to_file()

    # নোটিফিকেশন পাঠানোর আগে চেক করুন যে ইউজারটি বটের সাথে ইন্টারঅ্যাক্ট করেছে কিনা
    if user_id_str in all_users:
        await send_user_notification(
            context,
            user_id,
            get_text(
                user_id,
                "access_approved",
                expiry_date=expiry_str
            )
        )
    
    # Show updated user details
    await admin_user_details(update, context)

async def admin_disapprove_user_from_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Disapprove a user from the details view."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    # আরও ভালো কলব্যাক ডেটা পার্সিং
    if not query.data or not query.data.startswith("admin_disapprove_user_"):
        await safe_edit_message(query, "Invalid callback data format")
        return

    user_id_str = query.data.replace("admin_disapprove_user_", "")
    
    # নিশ্চিত করুন যে user_id_str খালি নয়
    if not user_id_str:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    if user_id == ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "cannot_disapprove_admin"))
        return

    if user_id in approved_users:
        del approved_users[user_id]
        await save_users_to_file()

        # নোটিফিকেশন পাঠানোর আগে চেক করুন যে ইউজারটি বটের সাথে ইন্টারঅ্যাক্ট করেছে কিনা
        if user_id_str in all_users:
            await send_user_notification(
                context,
                user_id,
                get_text(user_id, "access_revoked")
            )
    
    # Show updated user details
    await admin_user_details(update, context)

async def admin_approve_user_paginated(update: Update, context: ContextTypes.DEFAULT_TYPE, page=1):
    """Display paginated list of users to approve with plan selection."""
    query = update.callback_query if update.callback_query else None
    
    if query:
        user_id = query.from_user.id
        await query.answer()
    else:
        user_id = update.effective_user.id

    if user_id != ADMIN_ID:
        if query:
            await safe_edit_message(query, get_text(user_id, "unauthorized"))
        else:
            await update.message.reply_text(get_text(user_id, "unauthorized"))
        return

    # Get users who are not approved yet
    pending_users = []
    for uid_str, user_data in all_users.items():
        uid = int(uid_str)
        if uid != ADMIN_ID and uid not in approved_users:
            pending_users.append((uid, user_data))
    
    if not pending_users:
        message_text = get_text(user_id, "no_pending_users")
        keyboard = [[InlineKeyboardButton(get_text(user_id, "back") + " " + get_text(user_id, "to_user_management"), callback_data="admin_user_management")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if query:
            await safe_edit_message(query, message_text, reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup)
        return

    # Calculate pagination
    total_users = len(pending_users)
    total_pages = (total_users + USERS_PER_PAGE - 1) // USERS_PER_PAGE
    start_index = (page - 1) * USERS_PER_PAGE
    end_index = start_index + USERS_PER_PAGE
    current_page_users = pending_users[start_index:end_index]

    # Create message text
    message_text = get_text(user_id, "select_user_to_approve")
    if total_pages > 1:
        message_text += f"\n\n{get_text(user_id, 'page_info', current_page=page, total_pages=total_pages)}"

    # Create keyboard with user buttons
    keyboard = []
    
    for uid, user_data in current_page_users:
        name = user_data.get("first_name", "Unknown")
        button_text = f"👤 {name} (ID: {uid})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_select_plan_{uid}")])
    
    # Add pagination buttons if needed
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"admin_approve_paginated_{page-1}"))
    
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_approve_paginated_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Add back button
    keyboard.append([InlineKeyboardButton(get_text(user_id, "back") + " " + get_text(user_id, "to_user_management"), callback_data="admin_user_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await safe_edit_message(query, message_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message_text, reply_markup=reply_markup)

async def admin_select_plan_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display plan selection for a specific user."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    user_id_str = query.data.replace("admin_select_plan_", "")
    
    try:
        user_id = int(user_id_str)
    except ValueError:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_user_id"))
        return
    
    if user_id_str not in all_users:
        await safe_edit_message(query, "User not found in all users list.")
        return
    
    user_data = all_users[user_id_str]
    user_name = user_data.get("first_name", "Unknown")
    
    # Store the selected user ID for later use
    context.user_data["selected_user_id"] = user_id
    
    # Create plan selection keyboard
    keyboard = []
    
    for key, value in price_list.items():
        button_text = f"{value['duration']} - {value['price_bdt']} BDT / {value['price_usd']} USD"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"admin_approve_with_plan_{key}")])
    
    # Add back button
    keyboard.append([InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = get_text(query.from_user.id, "select_plan_for_user", user_name=user_name)
    
    await safe_edit_message(
        query,
        message_text,
        reply_markup=reply_markup
    )

async def admin_approve_with_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user with a specific plan."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    plan_key = query.data.replace("admin_approve_with_plan_", "")
    
    if plan_key not in price_list:
        await safe_edit_message(query, get_text(query.from_user.id, "invalid_duration_selected"))
        return
    
    # Get the selected user ID
    user_id = context.user_data.get("selected_user_id")
    if not user_id:
        await safe_edit_message(query, "No user selected. Please try again.")
        return
    
    # Calculate expiry date based on plan
    plan_duration = price_list[plan_key]["duration"]
    
    if "day" in plan_duration.lower():
        days = int(plan_duration.split()[0])
        expiry_date = datetime.now(timezone.utc) + timedelta(days=days)
    else:
        # Default to 7 days if we can't parse the duration
        expiry_date = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Approve the user
    approved_users[user_id] = expiry_date
    expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    await save_users_to_file()
    
    # Send notification to the user
    user_id_str = str(user_id)
    if user_id_str in all_users:
        await send_user_notification(
            context,
            user_id,
            get_text(
                user_id,
                "access_approved",
                expiry_date=expiry_str
            )
        )
    
    # Show success message
    user_name = all_users.get(str(user_id), {}).get("first_name", "Unknown")
    success_text = f"✅ User {user_name} (ID: {user_id}) has been approved with the {plan_duration} plan until {expiry_str}."
    
    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(
        query,
        success_text,
        reply_markup=reply_markup
    )

async def admin_approve_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the approve user menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "approve_user_msg"),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def admin_disapprove_user_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the disapprove user menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "disapprove_user_msg"),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def admin_broadcast_all_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the broadcast to all users menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_communication"), callback_data="admin_communication")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "broadcast_all_msg"),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def admin_broadcast_approved_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the broadcast to approved users menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_communication"), callback_data="admin_communication")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "broadcast_approved_msg"),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def admin_sync_files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle syncing files."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    await safe_edit_message(query, get_text(query.from_user.id, "syncing"))

    await load_users_from_file()
    await load_referral_data_from_file()
    await load_all_users_from_file()
    await load_price_list_from_file()
    await load_user_settings_from_file()
    await load_config_from_file()

    success_users = await save_users_to_file()
    success_referral = await save_referral_data_to_file()
    success_all_users = await save_all_users_to_file()
    success_price = await save_price_list_to_file()
    success_settings = await save_user_settings_to_file()
    success_config = await save_config_to_file()

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_system_management"), callback_data="admin_system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if success_users and success_referral and success_all_users and success_price and success_settings and success_config:
        await safe_edit_message(
            query,
            get_text(query.from_user.id, "sync_success"),
            reply_markup=reply_markup
        )
    else:
        await safe_edit_message(
            query,
            get_text(query.from_user.id, "sync_failed"),
            reply_markup=reply_markup
        )

async def admin_cleanup_expired_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cleanup of expired users."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    await safe_edit_message(query, get_text(query.from_user.id, "cleanup_expired"))
    
    # Run the cleanup function
    removed_count = await cleanup_expired_users()
    
    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_user_management"), callback_data="admin_user_management")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(
        query,
        get_text(query.from_user.id, "cleanup_complete", count=removed_count),
        reply_markup=reply_markup
    )

async def admin_export_data_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle exporting bot data."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    await safe_edit_message(query, get_text(query.from_user.id, "export_data_msg"))
    
    # Export the data
    zip_buffer = await export_bot_data()
    
    if zip_buffer:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bot_data_{timestamp}.zip"
        
        # Send the zip file
        await context.bot.send_document(
            chat_id=query.message.chat_id,
            document=zip_buffer,
            filename=filename,
            caption=get_text(query.from_user.id, "export_complete")
        )
        
        # Reset the message
        keyboard = [
            [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_system_management"), callback_data="admin_system")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(
            query,
            get_text(query.from_user.id, "export_complete"),
            reply_markup=reply_markup
        )
    else:
        await safe_edit_message(
            query,
            "❌ Failed to export data. Please check the logs.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_system_management"), callback_data="admin_system")]
            ])
        )

async def admin_change_rate_limit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the change rate limit menu."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await safe_edit_message(query, get_text(query.from_user.id, "unauthorized"))
        return

    current_limit = config_data.get("rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS)
    minutes = current_limit // 60
    seconds = current_limit % 60
    if minutes > 0:
        time_str = f"{minutes} minute{'s' if minutes > 1 else ''} and {seconds} second{'s' if seconds != 1 else ''}"
    else:
        time_str = f"{seconds} second{'s' if seconds != 1 else ''}"

    keyboard = [
        [InlineKeyboardButton(get_text(query.from_user.id, "back") + " " + get_text(query.from_user.id, "to_system_management"), callback_data="admin_system")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await safe_edit_message(
        query,
        get_text(query.from_user.id, "change_rate_limit_msg", current_limit=current_limit, current_time_str=time_str),
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

# --- Telegram Bot Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a message when the command /start is issued."""
    user = update.effective_user

    await track_user(user, update)

    user_id_str = str(user.id)

    # Check if user has language preference
    if user_id_str in user_settings and "language" in user_settings[user_id_str]:
        language = user_settings[user_id_str]["language"]

        # Process referral if present
        referral_code = None
        if context.args and len(context.args) > 0:
            referral_code = context.args[0]

            referrer_id = None
            for uid, data in referral_data.items():
                if data["referral_code"] == referral_code:
                    referrer_id = uid
                    break

            if referrer_id and referrer_id != str(user.id):
                success, message = await process_referral(referrer_id, user.id, context)
                # Only send message to the new user, not the referrer message
                if success:
                    await update.message.reply_text(get_text(user.id, "referral_successful", referral_count=1))

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
            "language": language
        }

        if user.id in approved_users and approved_users[user.id] is not None:
            user_data["expiry_date"] = approved_users[user.id].isoformat()

        await save_user_details_to_file(user.id, user_data)

        await update.message.reply_html(
            get_text(user.id, "language_selected", first_name=user.first_name)
        )
        await update.message.reply_text(get_text(user.id, "example"))
    else:
        # First time user - show language selection
        keyboard = [
            [
                InlineKeyboardButton("🇺🇸 English", callback_data=f"set_language_en"),
                InlineKeyboardButton("🇧🇩 বাংলা", callback_data=f"set_language_bn")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Store referral code if present for later processing
        if context.args and len(context.args) > 0:
            referral_code = context.args[0]
            context.user_data["pending_referral"] = referral_code

        await update.message.reply_html(
            get_text(user.id, "welcome", first_name=user.first_name),
            reply_markup=reply_markup
        )

async def admin_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides the admin's contact information."""
    user = update.effective_user
    await track_user(user, update)

    contact_text = get_text(
        user.id,
        "admin_contact",
        admin_name=ADMIN_FIRST_NAME,
        admin_id=ADMIN_ID,
        admin_username=ADMIN_USERNAME
    )
    await update.message.reply_html(contact_text)

async def show_price_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the price list for bot access."""
    user = update.effective_user
    await track_user(user, update)

    price_text = get_text(user.id, "price_list")

    for key, value in price_list.items():
        price_text += f"🔹 <b>{value['duration']}</b>: {value['price_bdt']} BDT / {value['price_usd']} USD\n"

    price_text += get_text(user.id, "payment_methods")

    await update.message.reply_html(price_text)

async def show_admin_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the admin panel with inline buttons."""
    await admin_main_menu(update, context)

async def referral_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the user's referral status and referral link."""
    user = update.effective_user
    await track_user(user, update)

    user_id = str(user.id)

    referral_code = await get_or_create_referral_code(user.id)

    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"

    referral_count = 0
    if user_id in referral_data:
        referral_count = len(referral_data[user_id]["referred_users"])

    has_access = is_user_approved(user.id, context)

    message = get_text(
        user.id,
        "referral_status",
        referral_code=referral_code,
        referral_link=referral_link,
        referral_count=referral_count
    )

    if has_access:
        expiry_date = approved_users.get(user.id)
        if expiry_date:
            expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')
            message += get_text(user.id, "access_until", expiry_date=expiry_str)
        else:
            message += get_text(user.id, "permanent_access")
    else:
        remaining = 3 - referral_count
        message += get_text(user.id, "refer_needed", remaining=remaining)

    keyboard = [
        [InlineKeyboardButton("Share Referral Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing Facebook Number Checker Bot and get free access!")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(message, reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles button callbacks."""
    query = update.callback_query
    await query.answer()

    # Fix for NoneType error: Check if query.data is None before using .replace()
    if query.data is None:
        logger.error("Received None for query.data in button_callback")
        return

    if query.data.startswith("set_language_"):
        language = query.data.replace("set_language_", "")
        await set_user_language(query.from_user.id, language)

        # Process pending referral if exists
        referral_code = None
        if "pending_referral" in context.user_data:
            referral_code = context.user_data["pending_referral"]
            del context.user_data["pending_referral"]
        elif query.message and query.message.text and "/start" in query.message.text:
            parts = query.message.text.split()
            if len(parts) > 1:
                referral_code = parts[1]

        if referral_code:
            referrer_id = None
            for uid, data in referral_data.items():
                if data["referral_code"] == referral_code:
                    referrer_id = uid
                    break

            if referrer_id and referrer_id != str(query.from_user.id):
                success, message = await process_referral(referrer_id, query.from_user.id, context)
                # Only send message to the new user, not the referrer message
                if success:
                    await safe_edit_message(query, get_text(query.from_user.id, "referral_successful", referral_count=1))
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
            "language": language
        }

        if query.from_user.id in approved_users and approved_users[query.from_user.id] is not None:
            user_data["expiry_date"] = approved_users[query.from_user.id].isoformat()

        await save_user_details_to_file(query.from_user.id, user_data)

        await safe_edit_message(
            query,
            get_text(query.from_user.id, "language_selected", first_name=query.from_user.first_name)
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=get_text(query.from_user.id, "example")
        )
        return

    if query.data == "buy_online":
        await safe_edit_message(
            query,
            get_text(query.from_user.id, "buy_online_msg"),
            parse_mode="HTML"
        )
    elif query.data == "refer":
        user_id = str(query.from_user.id)

        referral_code = await get_or_create_referral_code(query.from_user.id)

        bot_username = (await context.bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"

        referral_count = 0
        if user_id in referral_data:
            referral_count = len(referral_data[user_id]["referred_users"])

        message = get_text(
            query.from_user.id,
            "refer_link",
            referral_link=referral_link,
            referral_count=referral_count
        )

        if referral_count >= 3:
            message += get_text(query.from_user.id, "refer_earned")
        else:
            remaining = 3 - referral_count
            message += get_text(query.from_user.id, "refer_needed", remaining=remaining)

        keyboard = [
            [InlineKeyboardButton("Share Referral Link", url=f"https://t.me/share/url?url={referral_link}&text=Join this amazing Facebook Number Checker Bot and get free access!")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await safe_edit_message(
            query,
            text=message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )

    elif query.data == "admin_main":
        await admin_main_menu(update, context)
    elif query.data == "admin_user_management":
        await admin_user_management_menu(update, context)
    elif query.data == "admin_price_management":
        await admin_price_management_menu(update, context)
    elif query.data == "admin_communication":
        await admin_communication_menu(update, context)
    elif query.data == "admin_system":
        await admin_system_menu(update, context)
    elif query.data == "admin_statistics":
        await admin_statistics_menu(update, context)
    elif query.data == "admin_view_prices":
        await admin_view_prices(update, context)
    elif query.data == "admin_approved_users":
        await admin_approved_users_list(update, context)
    elif query.data == "admin_all_users":
        await admin_all_users_list(update, context)
    elif query.data.startswith("admin_user_details_"):
        await admin_user_details(update, context)
    elif query.data.startswith("admin_approve_user_"):
        await admin_approve_user_from_details(update, context)
    elif query.data.startswith("admin_disapprove_user_"):
        await admin_disapprove_user_from_details(update, context)
    elif query.data == "admin_approve_user":
        await admin_approve_user_menu(update, context)
    elif query.data == "admin_approve_user_paginated":
        await admin_approve_user_paginated(update, context)
    elif query.data.startswith("admin_approve_paginated_"):
        page = int(query.data.split("_")[-1])
        await admin_approve_user_paginated(update, context, page=page)
    elif query.data.startswith("admin_select_plan_"):
        await admin_select_plan_for_user(update, context)
    elif query.data.startswith("admin_approve_with_plan_"):
        await admin_approve_with_plan(update, context)
    elif query.data == "admin_disapprove_user":
        await admin_disapprove_user_menu(update, context)
    elif query.data == "admin_broadcast_all":
        await admin_broadcast_all_menu(update, context)
    elif query.data == "admin_broadcast_approved":
        await admin_broadcast_approved_menu(update, context)
    elif query.data == "admin_sync_files":
        await admin_sync_files_menu(update, context)
    elif query.data == "admin_cleanup_expired":
        await admin_cleanup_expired_menu(update, context)
    elif query.data == "admin_export_data":
        await admin_export_data_menu(update, context)
    elif query.data == "admin_change_rate_limit":
        await admin_change_rate_limit_menu(update, context)
    elif query.data == "admin_back":
        await admin_main_menu(update, context)

# --- Admin Command Handlers ---

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to approve a user for a specific duration."""
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

        # Check if user is already approved
        if user_id_to_approve in approved_users:
            expiry_date = approved_users[user_id_to_approve]
            if expiry_date is None:
                await update.message.reply_html(
                    get_text(
                        update.effective_user.id,
                        "user_already_approved",
                        uid=user_id_to_approve,
                        expiry_date="Permanent"
                    )
                )
                return
            else:
                expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')
                await update.message.reply_html(
                    get_text(
                        update.effective_user.id,
                        "user_already_approved",
                        uid=user_id_to_approve,
                        expiry_date=expiry_str
                    )
                )
                return

        if unit.startswith('hour'):
            expiry_date = datetime.now(timezone.utc) + timedelta(hours=amount)
        elif unit.startswith('day'):
            expiry_date = datetime.now(timezone.utc) + timedelta(days=amount)
        elif unit.startswith('month'):
            expiry_date = datetime.now(timezone.utc) + timedelta(days=amount * 30)
        else:
            await update.message.reply_text(get_text(update.effective_user.id, "invalid_unit"))
            return

        approved_users[user_id_to_approve] = expiry_date
        expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')

        await save_users_to_file()

        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "user_approved",
                uid=user_id_to_approve,
                expiry_date=expiry_str
            )
        )

        # নোটিফিকেশন পাঠানোর আগে চেক করুন যে ইউজারটি বটের সাথে ইন্টারঅ্যাক্ট করেছে কিনা
        user_id_str = str(user_id_to_approve)
        if user_id_str in all_users:
            await send_user_notification(
                context,
                user_id_to_approve,
                get_text(
                    user_id_to_approve,
                    "access_approved",
                    expiry_date=expiry_str
                )
            )

    except (ValueError, IndexError):
        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "invalid_input",
                format=get_text(update.effective_user.id, "usage_approve")
            )
        )

async def disapprove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to disapprove a user."""
    if update.effective_user.id != ADMIN_ID:
        if update.message:
            await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=get_text(update.effective_user.id, "unauthorized")
            )
        return

    # If no arguments are provided, show proper usage instead of failing
    if not context.args:
        usage_text = get_text(update.effective_user.id, "usage_disapprove")
        if update.message:
            await update.message.reply_html(usage_text)
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=usage_text,
                parse_mode="HTML"
            )
        return

    try:
        user_id_to_disapprove = int(context.args[0])
        if user_id_to_disapprove == ADMIN_ID:
            await update.message.reply_text(get_text(update.effective_user.id, "cannot_disapprove_admin"))
            return

        if user_id_to_disapprove in approved_users:
            del approved_users[user_id_to_disapprove]

            await save_users_to_file()

            await update.message.reply_html(
                get_text(
                    update.effective_user.id,
                    "user_disapproved",
                    uid=user_id_to_disapprove
                )
            )

            # নোটিফিকেশন পাঠানোর আগে চেক করুন যে ইউজারটি বটের সাথে ইন্টারঅ্যাক্ট করেছে কিনা
            user_id_str = str(user_id_to_disapprove)
            if user_id_str in all_users:
                await send_user_notification(
                    context,
                    user_id_to_disapprove,
                    get_text(user_id_to_disapprove, "access_revoked")
                )
        else:
            await update.message.reply_html(
                get_text(
                    update.effective_user.id,
                    "user_not_approved",
                    uid=user_id_to_disapprove
                )
            )

    except (ValueError, IndexError):
        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "invalid_input",
                format=get_text(update.effective_user.id, "usage_disapprove")
            )
        )

async def set_rate_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to change the rate limit."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not context.args:
        await update.message.reply_html(get_text(update.effective_user.id, "usage_setratelimit"))
        return

    try:
        seconds = int(context.args[0])
        if seconds < 10: # Minimum 10 seconds
            await update.message.reply_text("❌ Rate limit must be at least 10 seconds.")
            return

        config_data["rate_limit_seconds"] = seconds
        await save_config_to_file()

        minutes = seconds // 60
        secs = seconds % 60
        if minutes > 0:
            time_str = f"{minutes} minute{'s' if minutes > 1 else ''} and {secs} second{'s' if secs != 1 else ''}"
        else:
            time_str = f"{secs} second{'s' if secs != 1 else ''}"

        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "rate_limit_updated",
                seconds=seconds,
                time_str=time_str
            )
        )

    except (ValueError, IndexError):
        await update.message.reply_html(
            get_text(
                update.effective_user.id,
                "invalid_input",
                format=get_text(update.effective_user.id, "usage_setratelimit")
            )
        )

async def cleanup_expired(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to cleanup expired users."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    await update.message.reply_text(get_text(update.effective_user.id, "cleanup_expired"))
    
    # Run the cleanup function
    removed_count = await cleanup_expired_users()
    
    await update.message.reply_html(
        get_text(update.effective_user.id, "cleanup_complete", count=removed_count)
    )

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to export bot data."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    await update.message.reply_text(get_text(update.effective_user.id, "export_data_msg"))
    
    # Export the data
    zip_buffer = await export_bot_data()
    
    if zip_buffer:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"bot_data_{timestamp}.zip"
        
        # Send the zip file
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=zip_buffer,
            filename=filename,
            caption=get_text(update.effective_user.id, "export_complete")
        )
    else:
        await update.message.reply_text("❌ Failed to export data. Please check the logs.")

async def list_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all approved users and their expiry dates."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not approved_users:
        await update.message.reply_text(get_text(update.effective_user.id, "no_approved_users"))
        return

    response_text = get_text(update.effective_user.id, "approved_users") + "\n\n"
    for uid, expiry in approved_users.items():
        if uid == ADMIN_ID:
            response_text += f"👑 <code>{uid}</code> (Admin - Permanent)\n"
        else:
            if expiry is None:
                response_text += f"👤 <code>{uid}</code> - Permanent Access\n"
            else:
                expiry_str = expiry.strftime('%Y-%m-%d %H:%M:%S UTC')
                response_text += f"👤 <code>{uid}</code> - Expires: <b>{expiry_str}</b>\n"

    await update.message.reply_html(response_text)

async def list_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to list all users who have interacted with the bot."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not all_users:
        await update.message.reply_text(get_text(update.effective_user.id, "no_users"))
        return

    response_text = get_text(update.effective_user.id, "all_users", total_users=len(all_users)) + "\n\n"

    for uid, user_data in all_users.items():
        # Escape HTML special characters in user data
        name = html.escape(user_data.get("first_name", "Unknown"))
        username = html.escape(user_data.get("username", "No username"))
        last_interaction = user_data.get("last_interaction", "Unknown")
        numbers_checked = user_data.get("numbers_checked", 0)

        if uid == str(ADMIN_ID):
            response_text += f"👑 <code>{uid}</code> - {name} (@{username}) - Admin - Checked: {numbers_checked}\n"
        elif int(uid) in approved_users:
            expiry_date = approved_users[int(uid)]
            if expiry_date is None:
                response_text += f"✅ <code>{uid}</code> - {name} (@{username}) - Permanent access - Checked: {numbers_checked}\n"
            else:
                expiry_str = expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')
                response_text += f"✅ <code>{uid}</code> - {name} (@{username}) - Approved until {expiry_str} - Checked: {numbers_checked}\n"
        else:
            response_text += f"👤 <code>{uid}</code> - {name} (@{username}) - Not approved - Checked: {numbers_checked}\n"

    if len(response_text) > 4000:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"all_users_{timestamp}.txt"

        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            await f.write(response_text)

        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=open(filename, 'rb'),
            caption=f"List of all users who have interacted with the bot."
        )

        os.remove(filename)
    else:
        await update.message.reply_html(response_text)

async def show_price_list_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows the current price list to the admin."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    price_text = get_text(update.effective_user.id, "current_price_list")

    for key, value in price_list.items():
        price_text += f"🔹 <b>{value['duration']}</b>: {value['price_bdt']} BDT / {value['price_usd']} USD\n"

    await update.message.reply_html(price_text)

async def sync_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to sync data files."""
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

    success_users = await save_users_to_file()
    success_referral = await save_referral_data_to_file()
    success_all_users = await save_all_users_to_file()
    success_price = await save_price_list_to_file()
    success_settings = await save_user_settings_to_file()
    success_config = await save_config_to_file()

    if success_users and success_referral and success_all_users and success_price and success_settings and success_config:
        await update.message.reply_text(get_text(update.effective_user.id, "sync_success"))
    else:
        await update.message.reply_text(get_text(update.effective_user.id, "sync_failed"))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast a message to all users."""
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
            await context.bot.send_message(chat_id=int(user_id), text=message_to_broadcast, parse_mode='HTML')
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {user_id}: {e}")
            fail_count += 1

    await update.message.reply_html(
        get_text(
            update.effective_user.id,
            "broadcast_complete",
            success_count=success_count,
            fail_count=fail_count
        )
    )


async def broadcast_approved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to broadcast a message to approved users only."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text(get_text(update.effective_user.id, "unauthorized"))
        return

    if not context.args:
        await update.message.reply_html(get_text(update.effective_user.id, "usage_broadcast_approved"))
        return

    message_to_broadcast = " ".join(context.args)
    success_count = 0
    fail_count = 0

    for user_id in approved_users.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=message_to_broadcast, parse_mode='HTML')
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to {user_id}: {e}")
            fail_count += 1

    await update.message.reply_html(
        get_text(
            update.effective_user.id,
            "broadcast_approved_complete",
            success_count=success_count,
            fail_count=fail_count
        )
    )


# Function to remove HTML tags from text
def remove_html_tags(text):
    """Remove HTML tags from a string."""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the message containing phone numbers."""
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
        "language": get_user_language(user_id)
    }

    if user_id in approved_users and approved_users[user_id] is not None:
        user_data["expiry_date"] = approved_users[user_id].isoformat()

    await save_user_details_to_file(user_id, user_data)

    if not is_user_approved(user_id, context):
        referral_code = await get_or_create_referral_code(user_id)

        referral_count = 0
        if str(user_id) in referral_data:
            referral_count = len(referral_data[str(user_id)]["referred_users"])

        keyboard = [
            [InlineKeyboardButton(get_text(user_id, "buy_online"), callback_data="buy_online")],
            [InlineKeyboardButton(get_text(user_id, "refer_earn"), callback_data="refer")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_html(
            get_text(user_id, "access_denied", uid=user_id),
            reply_markup=reply_markup
        )
        return

    # Check rate limit (skip for admin)
    if user_id != ADMIN_ID:
        is_allowed, remaining_time = check_rate_limit(user_id)
        if not is_allowed:
            rate_limit_seconds = config_data.get("rate_limit_seconds", DEFAULT_RATE_LIMIT_SECONDS)
            await update.message.reply_html(
                get_text(user_id, "rate_limit", remaining_time=remaining_time, time_limit=rate_limit_seconds)
            )
            return

    processing_message = await update.message.reply_text(get_text(user_id, "processing"))

    phone_numbers = [line.strip().lstrip('- ').strip() for line in update.message.text.splitlines() if line.strip().lstrip('- ').strip()]

    if not phone_numbers:
        await processing_message.edit_text(get_text(user_id, "no_numbers"))
        return

    found_numbers = []
    not_found_numbers = []
    error_numbers = []

    # --- REFACTORED with httpx and asyncio.gather ---
    # Create an httpx.AsyncClient to reuse connections
    async with httpx.AsyncClient() as client:
        # Create a list of tasks
        tasks = [check_facebook_number(client, number) for number in phone_numbers]
        # Run all tasks concurrently
        results = await asyncio.gather(*tasks)

    # Process the results
    for number, status in zip(phone_numbers, results):
        if status == "Found":
            found_numbers.append(number)
        elif status == "Not Found":
            not_found_numbers.append(number)
        else:
            error_numbers.append((number, status))

    # Update numbers checked count
    user_id_str = str(user_id)
    if user_id_str in all_users:
        all_users[user_id_str]["numbers_checked"] = all_users[user_id_str].get("numbers_checked", 0) + len(phone_numbers)
        await save_all_users_to_file()

    response_text = get_text(user_id, "check_complete")

    if found_numbers:
        response_text += get_text(user_id, "found_numbers")
        for number in found_numbers:
            response_text += f"  <code>{number}</code>\n"
        response_text += "\n"

    if not_found_numbers:
        response_text += get_text(user_id, "not_found_numbers")
        for number in not_found_numbers:
            response_text += f"  <code>{number}</code>\n"
        response_text += "\n"

    if error_numbers:
        response_text += get_text(user_id, "errors_unknown")
        for number, error in error_numbers:
            response_text += f"  <code>{number}</code>: {error}\n"
        response_text += "\n"

    if not found_numbers and not not_found_numbers and not error_numbers:
        response_text = get_text(user_id, "no_valid_numbers")

    # FIX: Corrected logic for sending long results as a file
    if len(response_text) > 3000 or len(phone_numbers) > 50:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{timestamp}.txt"

            # Remove HTML tags from the content when writing to file
            clean_text = remove_html_tags(response_text)

            # REFACTORED: Use aiofiles to write the file
            async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
                await f.write(clean_text)

            caption = f"✅ Check Complete!\n\nFound: {len(found_numbers)}\nNot Found: {len(not_found_numbers)}\nErrors: {len(error_numbers)}"
            
            # Send the file
            with open(filename, 'rb') as f_sync:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f_sync,
                    caption=caption
                )

            os.remove(filename)

            # Delete the processing message
            await processing_message.delete()
            return # Important: exit the function here

        except Exception as e:
            logger.error(f"Failed to create or send file: {e}")
            # Don't delete the message if file sending fails, so we can edit it
            await processing_message.edit_text("❌ An error occurred while creating the result file. Please try again.")
            return
    else:
        # If we reach here, the list is short enough for a message
        try:
            await processing_message.edit_text(response_text, parse_mode='HTML')
        except BadRequest as e:
            if "message is not modified" in str(e):
                pass # No need to do anything
            else:
                logger.error(f"Failed to edit message: {e}")
                await processing_message.edit_text("❌ An error occurred while formatting the results. Please check the logs.")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await processing_message.edit_text("❌ An error occurred while formatting the results. Please check the logs.")

# --- ERROR HANDLER ---

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the admin."""
    logger.error(f"Exception while handling an update: {context.error}")

    try:
        if update and hasattr(update, 'effective_user'):
            user_id = update.effective_user.id
            await context.bot.send_message(
                chat_id=user_id,
                text="An error occurred. Please try again later.",
                parse_mode='HTML'
            )
    except Exception:
        pass


async def load_all_data():
    """Load all data files concurrently on startup and initialise MySQL (if configured)."""
    await asyncio.gather(
        load_config_from_file(),
        load_users_from_file(),
        load_referral_data_from_file(),
        load_all_users_from_file(),
        load_price_list_from_file(),
        load_user_settings_from_file()
    )

    # Initialise MySQL schema (if connection works)
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Error initialising MySQL database: {e}")


def main():
    """Start the bot."""
    # Create a new event loop for the main thread
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # For direct connection without proxy
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add error handler
    application.add_error_handler(error_handler)

    # Load data from local files on startup (concurrently)
    logger.info("Loading all data from files...")
    loop.run_until_complete(load_all_data())
    logger.info("Data loading complete.")
    
    # Clean up expired users on startup
    logger.info("Cleaning up expired users...")
    loop.run_until_complete(cleanup_expired_users())
    logger.info("Cleanup complete.")

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_contact))
    application.add_handler(CommandHandler("cmd", show_admin_commands))
    application.add_handler(CommandHandler("referral", referral_status))
    application.add_handler(CommandHandler("price", show_price_list))

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

    # Button callback handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # on non command i.e message - handle the message
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the auto cleanup task
    loop.create_task(auto_cleanup_task(application))

    # Run the bot until the user presses Ctrl-C
    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == '__main__':
    main()
