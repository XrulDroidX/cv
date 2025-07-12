import os
import zipfile
import logging
import shutil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definisikan tahapan percakapan
(
    AWAIT_FILE,
    AWAIT_CHOICE_STRUCTURED,
    AWAIT_BASE_NAME_NUMBERS,
    AWAIT_SPLIT_NUMBER,
    AWAIT_FILENAME,
) = range(5)

def is_numbers_only_file(file_path):
    """Mendeteksi apakah file hanya berisi nomor telepon."""
    with open(file_path, 'r', encoding='utf-8') as f:
        first_line = f.readline().strip()
    # Asumsi: jika baris pertama tidak mengandung koma dan bisa jadi nomor,
    # maka ini adalah file khusus nomor.
    return ',' not in first_line and any(char.isdigit() for char in first_line)

def generate_vcf(txt_file_path, output_dir, is_numbers_only, **kwargs):
    """
    Fungsi utama untuk membuat file VCF dari TXT.
    Menggunakan **kwargs untuk menerima argumen opsional.
    """
    # Ambil argumen dari kwargs
    base_contact_name = kwargs.get('base_contact_name')
    contacts_per_file = kwargs.get('contacts_per_file')
    custom_filename = kwargs.get('custom_filename', 'kontak')

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_files = []
    contact_index = 0
    file_index = 1
    vcf_file = None
    
    with open(txt_file_path, 'r', encoding='utf-8') as file_in:
        lines = [line.strip() for line in file_in if line.strip()]

        # Lewati header untuk file terstruktur
        if not is_numbers_only and ',' in lines[0]:
            lines.pop(0)
        
        total_contacts = len(lines)
        if total_contacts == 0:
            return [], 0
            
        for line in lines:
            # Tentukan nama, telepon, email berdasarkan tipe file
            if is_numbers_only:
                nama = f"{base_contact_name} {contact_index + 1}"
                telepon = line
                email = None
            else: # File terstruktur
                parts = line.split(',')
                nama = parts[0].strip()
                telepon = parts[1].strip() if len(parts) > 1 else ""
                email = parts[2].strip() if len(parts) > 2 else ""

            if not nama or not telepon:
                continue

            # Logika pembagian file
            if contacts_per_file and contact_index % contacts_per_file == 0:
                if vcf_file: vcf_file.close()
                start_num = (file_index - 1) * contacts_per_file + 1
                end_num = min(file_index * contacts_per_file, total_contacts)
                fname = f"{custom_filename}_{start_num}-{end_num}.vcf"
                output_path = os.path.join(output_dir, fname)
                output_files.append(output_path)
                vcf_file = open(output_path, 'w', encoding='utf-8')
                file_index += 1
            
            elif not vcf_file: # Buat file pertama jika belum ada
                output_path = os.path.join(output_dir, f"{custom_filename}.vcf")
                output_files.append(output_path)
                vcf_file = open(output_path, 'w', encoding='utf-8')

            # Tulis data VCF
            vcf_file.write('BEGIN:VCARD\nVERSION:3.0\n')
            vcf_file.write(f'FN:{nama}\n')
            vcf_file.write(f'TEL;TYPE=CELL:{telepon}\n')
            if email: vcf_file.write(f'EMAIL:{email}\n')
            vcf_file.write('END:VCARD\n\n')
            
            contact_index += 1
    
    if vcf_file: vcf_file.close()
    return output_files, contact_index

def create_zip_file(files, zip_name):
    """Membuat file ZIP dari beberapa file."""
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file in files:
            zipf.write(file, os.path.basename(file))
    return zip_name

def cleanup(context: ContextTypes.DEFAULT_TYPE):
    """Membersihkan file dan direktori sementara."""
    chat_id = context.user_data.get('chat_id')
    if chat_id:
        dir_path = str(chat_id)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            logger.info(f"Direktori sementara {dir_path} dihapus.")
    context.user_data.clear()

# --- HANDLER BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai percakapan."""
    await update.message.reply_text(
        "👋 Halo! Saya adalah Bot Konverter Kontak Cerdas.\n\n"
        "Kirimkan file `.txt` Anda. Saya bisa memproses 2 format:\n\n"
        "1️⃣ **Format Lengkap**:\n`Nama,Telepon,Email`\n\n"
        "2️⃣ **Format Nomor Saja**:\n`+6281234567890`\n\n"
        "Kirim file Anda untuk memulai!",
        parse_mode='Markdown'
    )
    return AWAIT_FILE

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima file, mendeteksi format, dan melanjutkan alur."""
    document = update.message.document
    chat_id = update.effective_chat.id
    context.user_data['chat_id'] = chat_id
    
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("❌ File tidak valid. Harap kirim file `.txt`.")
        return AWAIT_FILE

    # Buat direktori unik untuk user ini
    user_dir = str(chat_id)
    os.makedirs(user_dir, exist_ok=True)
    
    file_path = os.path.join(user_dir, document.file_name)
    file = await document.get_file()
    await file.download_to_drive(file_path)
    context.user_data['txt_file_path'] = file_path

    # Deteksi tipe file
    is_numbers_only = is_numbers_only_file(file_path)
    context.user_data['is_numbers_only'] = is_numbers_only

    with open(file_path, 'r', encoding='utf-8') as f:
        num_contacts = sum(1 for line in f if line.strip())

    if not is_numbers_only:
        num_contacts -= 1 # Kurangi header

    context.user_data['num_contacts'] = num_contacts

    if is_numbers_only:
        await update.message.reply_text(
            f"✅ File terdeteksi hanya berisi nomor ({num_contacts} kontak).\n\n"
            "Silakan ketik **nama dasar** untuk kontak ini (contoh: `Teman Baru`).\n\n"
            "Saya akan menamainya menjadi 'Teman Baru 1', 'Teman Baru 2', dan seterusnya.",
            parse_mode='Markdown'
        )
        return AWAIT_BASE_NAME_NUMBERS
    else:
        keyboard = [
            [InlineKeyboardButton("✅ Konversi Semua", callback_data='convert_all')],
            [InlineKeyboardButton("✂️ Bagi Kontak", callback_data='split')],
        ]
        await update.message.reply_text(
            f"✅ File terdeteksi format lengkap ({num_contacts} kontak).\n\n"
            "Pilih opsi:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return AWAIT_CHOICE_STRUCTURED

async def get_base_name_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima nama dasar untuk kontak dari file nomor saja."""
    base_name = update.message.text.strip()
    if not base_name:
        await update.message.reply_text("Nama dasar tidak boleh kosong. Coba lagi.")
        return AWAIT_BASE_NAME_NUMBERS
        
    context.user_data['base_contact_name'] = base_name
    await update.message.reply_text(
        f"👍 Nama dasar diatur ke `{base_name}`.\n\n"
        "Apakah Anda ingin membagi kontak ke beberapa file?\n"
        "➡️ Kirim **jumlah kontak per file** (misal: `50`).\n"
        "➡️ Kirim /skip jika tidak ingin dibagi.",
        parse_mode='Markdown'
    )
    return AWAIT_SPLIT_NUMBER

async def choice_handler_structured(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani pilihan untuk file terstruktur."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'convert_all':
        context.user_data['contacts_per_file'] = None
        await query.edit_message_text(
            "Baik, semua kontak akan digabung. Masukkan nama file output (tanpa ekstensi) atau kirim /skip untuk nama default (`kontak`)."
        )
        return AWAIT_FILENAME
    elif query.data == 'split':
        await query.edit_message_text("Anda memilih membagi kontak. Masukkan jumlah kontak per file (misal: `50`).")
        return AWAIT_SPLIT_NUMBER

async def get_split_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima jumlah untuk membagi file."""
    try:
        split_number = int(update.message.text)
        if split_number <= 0: raise ValueError
        context.user_data['contacts_per_file'] = split_number
        await update.message.reply_text(f"Baik, kontak akan dibagi {split_number} per file.")
    except (ValueError, TypeError):
        await update.message.reply_text("Input tidak valid. Harap masukkan angka positif.")
        return AWAIT_SPLIT_NUMBER

    await update.message.reply_text("Masukkan nama dasar untuk file output (tanpa ekstensi) atau kirim /skip untuk nama default (`kontak`).")
    return AWAIT_FILENAME

async def skip_split(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Melewatkan langkah pembagian file."""
    context.user_data['contacts_per_file'] = None
    await update.message.reply_text("Oke, semua kontak akan dijadikan satu file.")
    await update.message.reply_text("Masukkan nama untuk file output (tanpa ekstensi) atau kirim /skip untuk nama default (`kontak`).")
    return AWAIT_FILENAME

async def get_filename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menerima nama file output dan memicu proses akhir."""
    filename = update.message.text.strip()
    # Sanitasi nama file
    context.user_data['custom_filename'] = "".join(c for c in filename if c.isalnum() or c in ('_', '-'))
    await process_and_send(update, context)
    return ConversationHandler.END

async def skip_filename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menggunakan nama file default dan memicu proses akhir."""
    context.user_data['custom_filename'] = 'kontak'
    await process_and_send(update, context)
    return ConversationHandler.END

async def process_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fungsi akhir untuk memproses semua data dan mengirim file."""
    chat_id = context.user_data['chat_id']
    await context.bot.send_message(chat_id, "⏳ Mohon tunggu, sedang memproses file Anda...")
    
    try:
        # Panggil fungsi generate_vcf dengan semua argumen yang relevan
        output_files, count = generate_vcf(
            txt_file_path=context.user_data['txt_file_path'],
            output_dir=str(chat_id),
            is_numbers_only=context.user_data['is_numbers_only'],
            base_contact_name=context.user_data.get('base_contact_name'),
            contacts_per_file=context.user_data.get('contacts_per_file'),
            custom_filename=context.user_data.get('custom_filename', 'kontak')
        )

        if count == 0:
            await context.bot.send_message(chat_id, "Tidak ada kontak valid yang ditemukan dalam file.")
        elif len(output_files) > 1:
            zip_name = os.path.join(str(chat_id), f"{context.user_data.get('custom_filename', 'kontak')}.zip")
            zip_path = create_zip_file(output_files, zip_name)
            await context.bot.send_document(chat_id, document=open(zip_path, 'rb'), caption=f"✅ Selesai! {count} kontak telah dibagi dan disimpan dalam file ZIP.")
        else:
            await context.bot.send_document(chat_id, document=open(output_files[0], 'rb'), caption=f"✅ Selesai! {count} kontak berhasil dikonversi.")
    
    except Exception as e:
        logger.error(f"Error saat proses: {e}")
        await context.bot.send_message(chat_id, f"Terjadi kesalahan: {e}")
    finally:
        cleanup(context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan percakapan."""
    await update.message.reply_text("Proses dibatalkan.")
    cleanup(context)
    return ConversationHandler.END

def main() -> None:
    """Menjalankan bot."""
    application = Application.builder().token("TOKEN_BOT_ANDA").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AWAIT_FILE: [MessageHandler(filters.Document.TXT, get_file)],
            AWAIT_CHOICE_STRUCTURED: [CallbackQueryHandler(choice_handler_structured)],
            AWAIT_BASE_NAME_NUMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_base_name_numbers)],
            AWAIT_SPLIT_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_split_number),
                CommandHandler("skip", skip_split)
            ],
            AWAIT_FILENAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_filename),
                CommandHandler("skip", skip_filename)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
