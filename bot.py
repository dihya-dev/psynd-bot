# bot.py
import logging
import json
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from sheets import SheetsClient

# logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# load config
import os
import json

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
SPREADSHEET_ID = os.environ["SPREADSHEET_ID"]

# credentials JSON disimpan dalam ENV, bukan file
CREDENTIALS_JSON = os.environ["CREDENTIALS_JSON"]
with open("credentials.json", "w") as f:
    f.write(CREDENTIALS_JSON)
CREDENTIALS_FILE = "credentials.json"

# init sheets client
sheets = SheetsClient(CREDENTIALS_FILE, SPREADSHEET_ID)

def start(update, context):
    user = update.effective_user
    msg = ("Assalamu'alaikum 👋\n\n"
           "Selamat datang di Bot Posyandu.\n\n"
           "Untuk mendaftar/link akun anak ke Telegram Anda, gunakan perintah:\n"
           "`/register <child_id> <PIN>`\n\n"
           "Contoh: `/register C12345 987654`\n\n"
           "Setelah terdaftar, gunakan:\n"
           "`/latest` - data terakhir\n"
           "`/history [n]` - n entri terakhir (default semua)\n"
           "`/profile` - profil anak\n"
           "`/help` - bantuan\n")
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')

def help_cmd(update, context):
    msg = ("Daftar perintah:\n"
           "/start - Mulai\n"
           "/register <child_id> <PIN> - Daftar anak\n"
           "/latest - Lihat rekam terakhir\n"
           "/history [n] - Lihat histori (opsional parameter n)\n"
           "/profile - Lihat profil anak\n"
           "/help - Bantuan")
    context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

def register(update, context):
    chat_id = update.effective_chat.id
    user = update.effective_user
    args = context.args
    if len(args) < 2:
        context.bot.send_message(chat_id=chat_id, text="Format: /register <child_id> <PIN>\nContoh: /register C12345 987654")
        return
    child_id = args[0]
    pin = args[1]

    child = sheets.find_child(child_id)
    if not child:
        context.bot.send_message(chat_id=chat_id, text=f"Child ID `{child_id}` tidak ditemukan. Mohon cek kembali.", parse_mode='Markdown')
        return

    # cek PIN
    sheet_pin = str(child.get('pin', '')).strip()
    if sheet_pin != str(pin).strip():
        context.bot.send_message(chat_id=chat_id, text="PIN tidak cocok. Mohon cek PIN yang diberikan posyandu.")
        return

    # register mapping
    try:
        sheets.add_mapping_row_if_not_exists(user.id, child_id)
        context.bot.send_message(chat_id=chat_id, text=f"Berhasil terdaftar untuk anak *{child.get('nama')}* (ID: {child_id}).", parse_mode='Markdown')
    except Exception as e:
        logger.exception("Error register")
        context.bot.send_message(chat_id=chat_id, text="Terjadi error saat registrasi. Coba lagi nanti.")

def get_current_child_id_from_mapping(telegram_id):
    mapping = sheets.get_mapping_for_telegram(telegram_id)
    if not mapping:
        return None
    return mapping.get('child_id')

def profile(update, context):
    chat_id = update.effective_chat.id
    user = update.effective_user
    child_id = get_current_child_id_from_mapping(user.id)
    if not child_id:
        context.bot.send_message(chat_id=chat_id, text="Anda belum terdaftar. Silakan /register <child_id> <PIN>.")
        return
    child = sheets.find_child(child_id)
    if not child:
        context.bot.send_message(chat_id=chat_id, text="Profil anak tidak ditemukan di sheet.")
        return
    # format profile
    msg = ("Profil Anak:\n"
           f"Nama: {child.get('nama')}\n"
           f"Child ID: {child.get('child_id')}\n"
           f"TTL: {child.get('ttl')}\n"
           f"Jenis kelamin: {child.get('jenis_kelamin')}\n"
           f"Orang tua: {child.get('orang_tua')}\n")
    context.bot.send_message(chat_id=chat_id, text=msg)

def latest(update, context):
    chat_id = update.effective_chat.id
    user = update.effective_user
    child_id = get_current_child_id_from_mapping(user.id)
    if not child_id:
        context.bot.send_message(chat_id=chat_id, text="Anda belum terdaftar. Silakan /register <child_id> <PIN>.")
        return
    latest_rec = sheets.get_latest(child_id)
    if not latest_rec:
        context.bot.send_message(chat_id=chat_id, text="Belum ada data perkembangan untuk anak ini.")
        return
    msg = ("Rekaman Terbaru:\n"
           f"Tanggal: {latest_rec.get('date')}\n"
           f"Berat badan (kg): {latest_rec.get('bb')}\n"
           f"Tinggi (cm): {latest_rec.get('tb')}\n"
           f"Imunisasi: {latest_rec.get('imunisasi')}\n"
           f"Keterangan: {latest_rec.get('keterangan')}\n"
           f"Petugas: {latest_rec.get('petugas')}\n")
    context.bot.send_message(chat_id=chat_id, text=msg)

def history(update, context):
    chat_id = update.effective_chat.id
    user = update.effective_user
    args = context.args
    limit = None
    if args and args[0].isdigit():
        limit = int(args[0])
    child_id = get_current_child_id_from_mapping(user.id)
    if not child_id:
        context.bot.send_message(chat_id=chat_id, text="Anda belum terdaftar. Silakan /register <child_id> <PIN>.")
        return
    records = sheets.get_history(child_id)
    if not records:
        context.bot.send_message(chat_id=chat_id, text="Belum ada data histori untuk anak ini.")
        return
    if limit:
        records = records[:limit]
    # build message
    lines = []
    for r in records:
        lines.append(f"{r.get('date')}: BB={r.get('bb')} kg, TB={r.get('tb')} cm, Imun:{r.get('imunisasi')}, Note:{r.get('keterangan')}")
    msg = "Histori:\n" + "\n".join(lines)
    context.bot.send_message(chat_id=chat_id, text=msg)

def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Maaf, perintah tidak dikenal. Ketik /help untuk daftar perintah.")

def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # handlers
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_cmd))
    dp.add_handler(CommandHandler('register', register, pass_args=True))
    dp.add_handler(CommandHandler('profile', profile))
    dp.add_handler(CommandHandler('latest', latest))
    dp.add_handler(CommandHandler('history', history, pass_args=True))
    dp.add_handler(MessageHandler(Filters.command, unknown))
    dp.add_error_handler(error)

    # start polling
    updater.start_polling()
    logger.info("Bot started. Listening for messages...")
    updater.idle()

if __name__ == '__main__':
    main()

