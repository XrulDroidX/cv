# handlers.py
import os
import re
import requests
import logging
from datetime import datetime, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import numexpr as ne

from config import EXCHANGERATE_API_KEY
from core_logic import parse_txt_file_smartly, write_contact_files
from database import get_user_setting, set_user_setting

logger = logging.getLogger(__name__)

# Definisi State
AWAIT_FILE, AWAIT_BASE_NAME, AWAIT_SPLIT_CHOICE, AWAIT_EXPORT_CHOICE, AWAIT_FILENAME = range(5)
AWAIT_NEW_DEFAULT_NAME = range(5, 6)

def get_greeting():
    wib = timezone(timedelta(hours=7)); current_hour = datetime.now(wib).hour
    if 5 <= current_hour < 12: return "Pagi"
    if 12 <= current_hour < 15: return "Siang"
    if 15 <= current_hour < 18: return "Sore"
    return "Malam"

def cleanup(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get('chat_id')
    if chat_id and os.path.exists(str(chat_id)):
        shutil.rmtree(str(chat_id)); logger.info(f"Direktori sementara untuk chat_id {chat_id} telah dihapus.")
    if 'conv_persistence' in context.bot_data:
        if chat_id in context.bot_data['conv_persistence']:
            del context.bot_data['conv_persistence'][chat_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user_setting(user_id, 'default_base_name')
    greeting = get_greeting()
    keyboard = [[InlineKeyboardButton("🚀 Konversi Kontak TXT", callback_data='start_convert')], [InlineKeyboardButton("🧮 Kalkulator & Konverter", callback_data='calculator_menu')], [InlineKeyboardButton("⚙️ Pengaturan", callback_data='settings_menu')], [InlineKeyboardButton("📖 Panduan", callback_data='show_guide'), InlineKeyboardButton("👤 Kontak Owner", callback_data='show_owner')]]
    text = (f"--- **XRX BOT** ---\n\n👋 Selamat **{greeting}**!\n"
            "Saya bot serbaguna. Pilih menu di bawah.")
    if update.callback_query: await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else: await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    text = ("📖 **Panduan Cerdas**\n\n1. **Konversi Kontak**: Bot otomatis mendeteksi format `.txt` Anda (terstruktur atau hanya nomor).\n"
            "2. **Kalkulator**: Gunakan `/calc <ekspresi>`.\n3. **Kurs**: Gunakan `/kurs <jumlah> <ASAL> <TUJUAN>`.\n"
            "4. **Pengaturan**: Gunakan `/settings` untuk kustomisasi.\n\n"
            "Di grup, bot akan merespons pesan matematika/kurs secara otomatis jika Anda mengizinkannya di /settings.")
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='back_to_main')]]), parse_mode='Markdown')

async def show_owner(update, context): query = update.callback_query; await query.answer(); await query.edit_message_text("Hubungi owner saya @Alfyanda", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='back_to_main')]]))

async def show_calculator_menu(update, context): query = update.callback_query; await query.answer(); keyboard = [[InlineKeyboardButton("🔢 Kalkulator Dasar", callback_data='show_calc_guide')], [InlineKeyboardButton("💹 Konversi Mata Uang", callback_data='show_currency_guide')], [InlineKeyboardButton("⬅️ Kembali", callback_data='back_to_main')]]; await query.edit_message_text("Pilih jenis kalkulator/konverter:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_calc_guide(update, context): query = update.callback_query; await query.answer(); await query.edit_message_text("🧮 **Kalkulator Dasar**\n\nGunakan format: `/calc <ekspresi>`\nContoh: `/calc (50 + 50) * 2 / 10`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='calculator_menu')]]))

async def show_currency_guide(update, context): query = update.callback_query; await query.answer(); await query.edit_message_text("💹 **Konversi Mata Uang**\n\nGunakan format: `/kurs <jumlah> <ASAL> <TUJUAN>`\nContoh: `/kurs 10 USD IDR`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali", callback_data='calculator_menu')]]))

async def calculator_handler(update, context):
    if not context.args: await update.message.reply_text("Gunakan: `/calc <ekspresi>`"); return
    try: await update.message.reply_text(f"🔢 Hasil: `{ne.evaluate(' '.join(context.args)).item()}`", parse_mode='Markdown')
    except Exception as e: await update.message.reply_text(f"❌ Error: Ekspresi tidak valid.\n`{e}`", parse_mode='Markdown')

async def currency_converter_handler(update, context):
    if not EXCHANGERATE_API_KEY or EXCHANGERATE_API_KEY == "API_KEY_ANDA": await update.message.reply_text("Fitur ini belum aktif."); return
    if len(context.args) != 3: await update.message.reply_text("Gunakan: `/kurs <jumlah> <ASAL> <TUJUAN>`"); return
    amount, from_currency, to_currency = context.args[0], context.args[1].upper(), context.args[2].upper()
    try: amount_float = float(amount)
    except ValueError: await update.message.reply_text("Jumlah harus angka."); return
    url = f"https://v6.exchangerate-api.com/v6/{EXCHANGERATE_API_KEY}/pair/{from_currency}/{to_currency}/{amount_float}"
    try:
        data = requests.get(url).json()
        if data.get('result') == 'success': await update.message.reply_text(f"📊 `{amount_float:,.2f} {from_currency}` = `{data.get('conversion_result'):,.2f} {to_currency}`\n_Rate: 1 {from_currency} = {data.get('conversion_rate')} {to_currency}_", parse_mode='Markdown')
        else: await update.message.reply_text(f"Error API: {data.get('error-type', 'unknown')}")
    except Exception as e: logger.error(f"Error API mata uang: {e}"); await update.message.reply_text("Gagal menghubungi layanan nilai tukar.")

async def group_message_handler(update, context):
    if not update.message or update.message.chat.type not in ['group', 'supergroup'] or not get_user_setting(update.message.from_user.id, 'group_reply_enabled'): return
    text = update.message.text.lower()
    math_keyword_match = re.search(r'(?:berapa|hitung)\s*(.*?)(?:\?|$)', text)
    expression = text if re.fullmatch(r'^[\d\s()+\-*/.]+$', text) else (math_keyword_match.group(1) if math_keyword_match else None)
    if expression:
        try: await update.message.reply_text(f"Hasilnya: {ne.evaluate(expression).item()}", reply_to_message_id=update.message.message_id); return
        except: pass
    currency_match = re.search(r'(\d+(?:\.\d+)?)\s+([a-zA-Z]{3})\s+(?:to|ke)\s+([a-zA-Z]{3})', text)
    if currency_match: context.args = currency_match.groups(); await currency_converter_handler(update, context); return

async def start_conversion_flow(update, context): query = update.callback_query; await query.answer(); await query.edit_message_text("👋 Halo! Saya XRX BOT...\nKirim file .txt Anda."); return AWAIT_FILE
async def get_file(update, context):
    chat_id = update.effective_chat.id; context.user_data['chat_id'] = chat_id
    user_dir = str(chat_id); os.makedirs(user_dir, exist_ok=True)
    doc = update.message.document
    if not doc.file_name.lower().endswith('.txt'): await update.message.reply_text("Format tidak didukung."); return AWAIT_FILE
    file_path = os.path.join(user_dir, doc.file_name); file = await doc.get_file(); await file.download_to_drive(file_path)
    result = parse_txt_file_smartly(file_path)
    if not result['contacts']: await update.message.reply_text("Tidak ada kontak valid."); cleanup(context); return ConversationHandler.END
    context.user_data['contacts'] = result['contacts']
    report = f"✅ Ditemukan **{len(result['contacts'])}** kontak unik." + (f" ({result['invalid_lines']} baris diabaikan)." if result['invalid_lines'] > 0 else "")
    await update.message.reply_text(report, parse_mode='Markdown')
    if not result['was_structured']: context.user_data['base_name'] = get_user_setting(chat_id, 'default_base_name'); await update.message.reply_text(f"Akan digunakan nama dasar default: `{context.user_data['base_name']}`. Anda bisa mengubahnya di /settings.\n\nLanjut ke opsi pembagian kontak?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Lanjut", callback_data='skip_base_name')]])); return AWAIT_BASE_NAME
    else: context.user_data['base_name'] = ''; await update.message.reply_text("Ingin membagi? Kirim **jumlah per file** atau /skip.", parse_mode='Markdown'); return AWAIT_SPLIT_CHOICE
async def get_base_name(update, context): context.user_data['base_name'] = update.message.text.strip(); await update.message.reply_text("Nama dasar diatur. Ingin membagi? Kirim **jumlah per file** atau /skip.", parse_mode='Markdown'); return AWAIT_SPLIT_CHOICE
async def skip_base_name(update, context): query = update.callback_query; await query.answer(); await query.edit_message_text("Ingin membagi kontak? Kirim **jumlah per file** atau /skip.", parse_mode='Markdown'); return AWAIT_SPLIT_CHOICE
async def get_split_choice(update, context):
    split_number = None
    if update.message.text and not update.message.text.startswith('/'):
        try: split_number = int(update.message.text); await update.message.reply_text(f"Dibagi {split_number} per file.")
        except: await update.message.reply_text("Input tidak valid. Opsi split diabaikan.")
    else: await update.message.reply_text("Oke, digabung.")
    context.user_data['split_number'] = split_number
    await update.message.reply_text("Pilih format output:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Export ke VCF", callback_data='export_vcf')], [InlineKeyboardButton("Export ke CSV", callback_data='export_csv')]])); return AWAIT_EXPORT_CHOICE
async def get_export_choice(update, context): query = update.callback_query; await query.answer(); context.user_data['export_format'] = "vcf" if query.data == 'export_vcf' else "csv"; await query.edit_message_text(f"Format .{context.user_data['export_format']} dipilih. Masukkan nama file atau /skip."); return AWAIT_FILENAME
async def get_filename_and_process(update, context):
    filename = "hasil_kontak"
    if update.message.text and not update.message.text.startswith('/'): filename = "".join(c for c in update.message.text if c.isalnum() or c in ('_', '-')).strip()
    chat_id = context.user_data['chat_id']; await update.message.reply_text("⏳ Memproses file...")
    try:
        output_files, count = write_contact_files(contacts=context.user_data['contacts'], output_dir=str(chat_id), base_name=context.user_data.get('base_name', ''), contacts_per_file=context.user_data.get('split_number'), custom_filename=filename, export_format=context.user_data['export_format'])
        if count > 0:
            caption = f"✅ Berhasil! {count} kontak diproses."
            if len(output_files) > 1: await context.bot.send_message(chat_id, f"{caption} Mengirim {len(output_files)} file...")
            for file_path in output_files:
                with open(file_path, 'rb') as doc_file: await context.bot.send_document(chat_id=chat_id, document=doc_file, caption=(caption if len(output_files) == 1 else None))
        else: await context.bot.send_message(chat_id, "Gagal, tidak ada kontak valid.")
    except Exception as e: logger.error(f"Error proses akhir: {e}"); await context.bot.send_message(chat_id, f"Gagal membuat file. Error: {e}")
    finally:
        await context.bot.send_message(chat_id, "Operasi selesai.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data='back_to_main')]])); cleanup(context)
    return ConversationHandler.END
async def cancel(update, context): await (update.callback_query or update).message.reply_text("Dibatalkan."); cleanup(context); await start(update, context); return ConversationHandler.END
async def settings_menu(update, context):
    query = update.callback_query or update
    user_id = update.effective_user.id
    if hasattr(query, 'answer'): await query.answer()
    base_name = get_user_setting(user_id, 'default_base_name')
    group_reply_text = "AKTIF ✅" if get_user_setting(user_id, 'group_reply_enabled') else "NONAKTIF ❌"
    keyboard = [[InlineKeyboardButton(f"✏️ Nama Dasar: {base_name}", callback_data='set_default_name')], [InlineKeyboardButton(f"💬 Balasan Grup: {group_reply_text}", callback_data='toggle_group_reply')], [InlineKeyboardButton("⬅️ Kembali", callback_data='back_to_main')]]
    text = "⚙️ **Menu Pengaturan**"
    if hasattr(query, 'edit_message_text'): await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    else: await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
async def prompt_set_default_name(update, context): query = update.callback_query; await query.answer(); await query.edit_message_text("Masukkan nama dasar default baru:"); return AWAIT_NEW_DEFAULT_NAME
async def set_new_default_name(update, context):
    user_id = update.effective_user.id; set_user_setting(user_id, 'default_base_name', update.message.text.strip()); await update.message.reply_text("Pengaturan disimpan!")
    class FakeUpdate:
        def __init__(self, original_update): self.effective_user = original_update.effective_user; self.callback_query = None; self.message = original_update.message
    await start(FakeUpdate(update), context)
    return ConversationHandler.END
async def toggle_group_reply(update, context):
    query = update.callback_query; user_id = update.effective_user.id; await query.answer()
    new_status = 0 if get_user_setting(user_id, 'group_reply_enabled') else 1
    set_user_setting(user_id, 'group_reply_enabled', new_status); await settings_menu(query, context)