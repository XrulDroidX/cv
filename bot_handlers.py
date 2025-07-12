# bot_handlers.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from utils import get_greeting, cleanup
from core_functions import (
    parse_txt_file, parse_vcf_file, merge_contacts, 
    write_vcf_file, write_csv_file
)

# Definisi State
(
    AWAIT_FIRST_FILE, AWAIT_SECOND_FILE, AWAIT_MERGE_OPTIONS,
    AWAIT_TXT_OPTIONS, AWAIT_VCF_EXPORT_OPTIONS,
    AWAIT_FILENAME
) = range(6)


# --- HANDLER MENU UTAMA & PANDUAN ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menampilkan menu utama."""
    greeting = get_greeting()
    keyboard = [
        [InlineKeyboardButton("🔄 Konversi File Tunggal", callback_data='start_convert')],
        [InlineKeyboardButton("➕ Gabungkan Dua File", callback_data='start_merge')],
        [InlineKeyboardButton("📖 Panduan & Info", callback_data='show_guide')],
        [InlineKeyboardButton("🔒 Kebijakan Privasi", callback_data='show_privacy')],
    ]
    text = (f"👋 Selamat **{greeting}**! Saya **Bot Kontak Ultimate**.\n\n"
            "Pilih layanan yang Anda butuhkan:")
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = ("📖 **Panduan Fitur**\n\n"
            "1️⃣ **Konversi File Tunggal**\n"
            "   - Ubah `TXT/CSV` ke `VCF` atau sebaliknya.\n"
            "   - Opsi ekspor ke format CSV standar atau Google.\n\n"
            "2️⃣ **Gabungkan Dua File**\n"
            "   - Unggah dua file (TXT/VCF), bot akan menggabungkannya.\n"
            "   - Opsi untuk menghapus kontak duplikat secara otomatis.\n\n"
            "Format kolom yang didukung: `Name, Phone, Email, Address, Organization, Job Title, Birthday, Notes`")
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='back_to_main')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_privacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = ("🔒 **Kebijakan Privasi**\n\n"
            "Keamanan data Anda adalah prioritas utama.\n"
            "1. **Tidak Ada Penyimpanan**: Semua file yang Anda unggah dan file hasil konversi akan **dihapus secara permanen** dari server kami segera setelah operasi selesai atau dibatalkan.\n"
            "2. **Tidak Ada Logging Data**: Kami tidak menyimpan atau mencatat isi dari file kontak Anda.\n"
            "3. **Koneksi Aman**: Komunikasi Anda dengan bot ini dienkripsi oleh Telegram.")
    keyboard = [[InlineKeyboardButton("⬅️ Kembali", callback_data='back_to_main')]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


# --- ALUR KONVERSI & GABUNG FILE ---

async def start_conversion_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['mode'] = 'convert'
    await query.edit_message_text("Silakan kirim file `.txt`, `.csv`, atau `.vcf` yang ingin Anda konversi.")
    return AWAIT_FIRST_FILE

async def start_merge_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['mode'] = 'merge'
    await query.edit_message_text("Anda memilih untuk menggabungkan file. Silakan kirim **file pertama**.")
    return AWAIT_FIRST_FILE

async def get_first_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima file pertama dan memprosesnya."""
    chat_id = update.effective_chat.id
    context.user_data['chat_id'] = chat_id
    user_dir = str(chat_id); os.makedirs(user_dir, exist_ok=True)
    
    doc = update.message.document
    file_path = os.path.join(user_dir, "file1" + os.path.splitext(doc.file_name)[1])
    file = await doc.get_file(); await file.download_to_drive(file_path)
    
    try:
        if file_path.endswith(('.txt', '.csv')):
            contacts = parse_txt_file(file_path)
            context.user_data['file1_type'] = 'txt'
        elif file_path.endswith('.vcf'):
            contacts = parse_vcf_file(file_path)
            context.user_data['file1_type'] = 'vcf'
        else:
            await update.message.reply_text("Format file tidak didukung. Harap kirim .txt, .csv, atau .vcf.")
            return AWAIT_FIRST_FILE
        
        context.user_data['contacts1'] = contacts
        await update.message.reply_text(f"✅ File pertama diterima dan berisi {len(contacts)} kontak.")
        
        if context.user_data.get('mode') == 'merge':
            await update.message.reply_text("Sekarang, silakan kirim **file kedua**.")
            return AWAIT_SECOND_FILE
        else: # Mode Konversi
            return await show_export_options(update, context, file_path)

    except Exception as e:
        await update.message.reply_text(f"Gagal memproses file. Pastikan formatnya benar. Error: {e}")
        return ConversationHandler.END

async def get_second_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima file kedua (hanya untuk mode merge)."""
    user_dir = str(context.user_data['chat_id'])
    doc = update.message.document
    file_path = os.path.join(user_dir, "file2" + os.path.splitext(doc.file_name)[1])
    file = await doc.get_file(); await file.download_to_drive(file_path)

    try:
        if file_path.endswith(('.txt', '.csv')):
            contacts = parse_txt_file(file_path)
        elif file_path.endswith('.vcf'):
            contacts = parse_vcf_file(file_path)
        else:
            await update.message.reply_text("Format file kedua tidak didukung.")
            return AWAIT_SECOND_FILE
            
        context.user_data['contacts2'] = contacts
        await update.message.reply_text(f"✅ File kedua diterima dan berisi {len(contacts)} kontak.")
        
        keyboard = [
            [InlineKeyboardButton("Ya, Hapus Duplikat", callback_data='dedup_yes')],
            [InlineKeyboardButton("Tidak, Gabungkan Semua", callback_data='dedup_no')],
        ]
        await update.message.reply_text("Apakah Anda ingin menghapus kontak duplikat (berdasarkan nomor telepon) saat menggabungkan?",
                                      reply_markup=InlineKeyboardMarkup(keyboard))
        return AWAIT_MERGE_OPTIONS

    except Exception as e:
        await update.message.reply_text(f"Gagal memproses file kedua. Error: {e}")
        return ConversationHandler.END

async def handle_merge_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani opsi deduplikasi dan memulai proses merge."""
    query = update.callback_query
    await query.answer()
    
    deduplicate = (query.data == 'dedup_yes')
    
    contacts1 = context.user_data.get('contacts1', [])
    contacts2 = context.user_data.get('contacts2', [])
    
    final_contacts = merge_contacts([contacts1, contacts2], deduplicate=deduplicate)
    context.user_data['final_contacts'] = final_contacts
    
    total_awal = len(contacts1) + len(contacts2)
    total_akhir = len(final_contacts)
    
    await query.edit_message_text(f"Proses penggabungan selesai.\nTotal Kontak Awal: {total_awal}\nTotal Kontak Akhir: {total_akhir}")
    
    return await show_export_options(update, context)

async def show_export_options(update: Update, context: ContextTypes.DEFAULT_TYPE, file_path=None):
    """Menampilkan pilihan format ekspor (VCF atau CSV)."""
    # Jika dari alur konversi file tunggal, final_contacts belum ada
    if 'final_contacts' not in context.user_data:
        context.user_data['final_contacts'] = context.user_data['contacts1']

    # Beri pratinjau
    preview_contact = context.user_data['final_contacts'][0] if context.user_data['final_contacts'] else {}
    preview_text = (f"Nama: {preview_contact.get('Name', 'N/A')}\n"
                    f"Telepon: {preview_contact.get('Phone', 'N/A')}")
    
    keyboard = [
        [InlineKeyboardButton("Export ke VCF (vCard)", callback_data='export_vcf')],
        [InlineKeyboardButton("Export ke CSV (Excel)", callback_data='export_csv')],
    ]
    await (update.callback_query or update).message.reply_text(
        f"**Pratinjau Kontak Pertama:**\n`{preview_text}`\n\nPilih format output yang Anda inginkan:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return AWAIT_VCF_EXPORT_OPTIONS

async def handle_export_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menangani pilihan format ekspor."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'export_vcf':
        context.user_data['export_format'] = 'vcf'
        await query.edit_message_text("Masukkan nama untuk file `.vcf` Anda (tanpa ekstensi).")
        return AWAIT_FILENAME
    elif query.data == 'export_csv':
        keyboard = [
            [InlineKeyboardButton("Format Standar", callback_data='csv_standard')],
            [InlineKeyboardButton("Format Google CSV", callback_data='csv_google')],
        ]
        await query.edit_message_text("Pilih jenis format CSV:", reply_markup=InlineKeyboardMarkup(keyboard))
        return AWAIT_VCF_EXPORT_OPTIONS # Tetap di state ini untuk menerima pilihan CSV

async def handle_csv_format_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['export_format'] = query.data # 'csv_standard' or 'csv_google'
    await query.edit_message_text("Masukkan nama untuk file `.csv` Anda (tanpa ekstensi).")
    return AWAIT_FILENAME

async def get_filename_and_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menerima nama file akhir dan menjalankan proses penulisan file."""
    filename = update.message.text.strip()
    chat_id = context.user_data['chat_id']
    user_dir = str(chat_id)
    contacts = context.user_data['final_contacts']
    export_format = context.user_data['export_format']
    
    await update.message.reply_text("⏳ Sedang membuat file hasil...")
    
    try:
        if export_format == 'vcf':
            output_path = os.path.join(user_dir, f"{filename}.vcf")
            count = write_vcf_file(contacts, output_path)
        else: # CSV
            csv_type = 'google' if export_format == 'csv_google' else 'standard'
            output_path = os.path.join(user_dir, f"{filename}.csv")
            count = write_csv_file(contacts, output_path, format_type=csv_type)
        
        await context.bot.send_document(
            chat_id=chat_id,
            document=open(output_path, 'rb'),
            caption=f"✅ Berhasil! File Anda dengan {count} kontak telah dibuat."
        )
    except Exception as e:
        await update.message.reply_text(f"Gagal membuat file. Error: {e}")
    finally:
        cleanup(context)
        
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Membatalkan semua operasi."""
    await (update.callback_query or update).message.reply_text("Operasi dibatalkan.")
    cleanup(context)
    await start(update, context)
    return ConversationHandler.END