# config.py
import os
from dotenv import load_dotenv

# Memuat variabel dari file .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN tidak ditemukan! Pastikan file .env sudah benar.")

DATABASE_FILE = "xrx_bot.db"
PERSISTENCE_FILE = "xrx_bot_persistence"