# main.py
import logging
from telegram.ext import Application, PicklePersistence

# Impor dari file-file lokal
import config
import database
from handlers import register_handlers

# Konfigurasi logging ke file dan konsol
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Menjalankan XRX BOT dengan arsitektur profesional."""
    
    # Persiapan Awal
    logger.info("Memulai bot...")
    database.setup_database()
    persistence = PicklePersistence(filepath=config.PERSISTENCE_FILE)

    # Membangun Aplikasi
    application = Application.builder().token(config.TELEGRAM_TOKEN).persistence(persistence).build()

    # Mendaftarkan semua handler dari file handlers.py
    register_handlers(application)
    
    # Menjalankan bot
    logger.info("XRX BOT (Versi Profesional) siap beroperasi.")
    application.run_polling()

if __name__ == "__main__":
    main()