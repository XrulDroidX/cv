# utils.py

import os
import shutil
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

def get_greeting():
    """Membuat sapaan dinamis berdasarkan waktu WIB (UTC+7)."""
    wib = timezone(timedelta(hours=7))
    current_hour = datetime.now(wib).hour
    if 5 <= current_hour < 12: return "Pagi"
    if 12 <= current_hour < 15: return "Siang"
    if 15 <= current_hour < 18: return "Sore"
    return "Malam"

def cleanup(context):
    """Membersihkan file dan direktori sementara setelah operasi selesai atau dibatalkan."""
    chat_id = context.user_data.get('chat_id')
    if chat_id and os.path.exists(str(chat_id)):
        shutil.rmtree(str(chat_id))
        logger.info(f"Direktori sementara untuk chat_id {chat_id} telah dihapus.")
    context.user_data.clear()