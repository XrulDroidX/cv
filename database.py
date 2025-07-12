# database.py
import sqlite3
from config import DATABASE_FILE

def setup_database():
    """Membuat tabel database jika belum ada."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            default_base_name TEXT DEFAULT 'Kontak',
            group_reply_enabled INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()

def get_user_setting(user_id, setting_name):
    """Mengambil pengaturan spesifik dari database untuk seorang pengguna."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    cursor.execute(f"SELECT {setting_name} FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_user_setting(user_id, setting_name, value):
    """Menyimpan pengaturan spesifik ke database untuk seorang pengguna."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute(f"UPDATE users SET {setting_name} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()