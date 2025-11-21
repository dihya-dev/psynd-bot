import logging
import os
import json
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from sheets import SheetsClient

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === ENV VARIABLES ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDENTIALS_JSON = os.getenv("CREDENTIALS_JSON")  # JSON string

if not TELEGRAM_TOKEN:
    raise ValueError("ERROR: TELEGRAM_TOKEN missing in Railway Variables")
if not SPREADSHEET_ID:
    raise ValueError("ERROR: SPREADSHEET_ID missing in Railway Variables")
if not CREDENTIALS_JSON:
    raise ValueError("ERROR: CREDENTIALS_JSON missing in Railway Variables")

# convert string -> dict
creds_dict = json.loads(CREDENTIALS_JSON)

# init sheets client
sheets = SheetsClient(creds_dict, SPREADSHEET_ID)

# === BOT COMMANDS ===
async def start(update, context):
    msg = (
        "Assalamu'alaikum 👋\n\n"
        "Selamat datang di Bot Posyandu.\n\n"
        "Gunakan perintah:\n"
        "`/register <child_id> <PIN>`\n"
        "`/latest`\n"
        "`/history [n]`\n"
        "`/profile`\n"
        "`/help`\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_cmd(update, context):
    msg = (
        "Daftar perintah:\n"
        "/start\n/help\n/register\n/latest\n/history\n/profile"
    )
    await update.message.reply_text(msg)

async def register(update, context):
    user = update.effective_user
    args = context.args

    if len(args) < 2:
        await update.message.reply_text("Format: /register <child_id> <PIN>")
        return

    child_id, pin = args[0], args[1]
    child = sheets.find_child(child_id)

    if not child:
        await update.message.reply_text(f"Child ID `{child_id}` tidak ditemukan.", parse_mode="Markdown")
        return

    if str(child.get("pin", "")).strip() != pin:
        await update.message.reply_text("PIN tidak cocok.")
        return

    sheets.add_mapping_row_if_not_exists(user.id, child_id)
    await update.message.reply_text(f"Berhasil terdaftar untuk anak *{child.get('nama')}* (ID: {child_id}).", parse_mode="Markdown")

def get_current_child_id_from_mapping(telegram_id):
    mapping = sheets.get_mapping_for_telegram(telegram_id)
    return mapping.get("child_id") if mapping else None

async def profile(update, context):
    user = update.effective_user
    child_id = get_current_child_id_from_mapping(user.id)
    if not child_id:
        await update.message.reply_text("Anda belum terdaftar. Gunakan /register")
        return

    child = sheets.find_child(child_id)
    if not child:
        await update.message.reply_text("Profil anak tidak ditemukan.")
        return

    msg = (
        f"Profil Anak:\n"
        f"Nama: {child.get('nama')}\n"
        f"Child ID: {child.get('child_id')}\n"
        f"TTL: {child.get('ttl')}\n"
        f"Jenis kelamin: {child.get('jenis_kelamin')}\n"
        f"Orang tua: {child.get('orang_tua')}\n"
    )
    await update.message.reply_text(msg)

async def latest(update, context):
    user = update.effective_user
    child_id = get_current_child_id_from_mapping(user.id)
    if not child_id:
        await update.message.reply_text("Anda belum terdaftar.")
        return

    latest_rec = sheets.get_latest(child_id)
    if not latest_rec:
        await update.message.reply_text("Belum ada data.")
        return

    msg = (
        f"Rekaman Terbaru:\n"
        f"Tanggal: {latest_rec.get('date')}\n"
        f"BB: {latest_rec.get('bb')} kg\n"
        f"TB: {latest_rec.get('tb')} cm\n"
        f"Imunisasi: {latest_rec.get('imunisasi')}\n"
        f"Catatan: {latest_rec.get('keterangan')}\n"
        f"Petugas: {latest_rec.get('petugas')}\n"
    )
    await update.message.reply_text(msg)

async def history(update, context):
    user = update.effective_user
    args = context.args
    limit = int(args[0]) if args and args[0].isdigit() else None

    child_id = get_current_child_id_from_mapping(user.id)
    if not child_id:
        await update.message.reply_text("Anda belum terdaftar.")
        return

    records = sheets.get_history(child_id)
    if not records:
        await update.message.reply_text("Belum ada data histori.")
        return

    if limit:
        records = records[:limit]

    lines = [f"{r.get('date')}: BB={r.get('bb')}, TB={r.get('tb')}, Imun={r.get('imunisasi')}" for r in records]
    await update.message.reply_text("Histori:\n" + "\n".join(lines))

async def unknown(update, context):
    await update.message.reply_text("Perintah tidak dikenal.")

# === MAIN ===
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("latest", latest))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Bot running...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

