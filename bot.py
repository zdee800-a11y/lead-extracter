import os
import re
import tempfile
import logging

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

ALLOWED_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "outlook.com",
    "outlook.co.uk",
    "hotmail.com",
    "hotmail.co.uk",
    "yahoo.com",
    "yahoo.co.uk",
}

MODE_FILTER = "filter_leads"
MODE_EXTRACT = "extract_numbers"


def normalize_uk_number(raw_number: str):
    number = re.sub(r"[^\d+]", "", raw_number)

    if number.startswith("+44"):
        national = number[3:]
    elif number.startswith("0044"):
        national = number[4:]
    elif number.startswith("44"):
        national = number[2:]
    elif number.startswith("0"):
        national = number[1:]
    else:
        national = number

    if national.startswith("0"):
        national = national[1:]

    if not national.isdigit():
        return None

    if len(national) == 10 and national.startswith("7"):
        return "+44" + national

    if len(national) in (9, 10) and national.startswith(("1", "2")):
        return "+44" + national

    if len(national) == 10 and national.startswith(("3", "8")):
        return "+44" + national

    return None


def extract_numbers(text: str):
    pattern = re.compile(
        r"""
        (?<!\d)
        (
            \+44[\s().\-]*(?:0[\s().\-]*)?\d(?:[\s().\-]*\d){8,9}
            |
            0044[\s().\-]*(?:0[\s().\-]*)?\d(?:[\s().\-]*\d){8,9}
            |
            44[\s().\-]*\d(?:[\s().\-]*\d){8,9}
            |
            0\d(?:[\s().\-]*\d){8,9}
            |
            7(?:[\s().\-]*\d){9}
        )
        (?!\d)
        """,
        re.VERBOSE,
    )

    results = []
    seen = set()

    for match in pattern.findall(text):
        normalized = normalize_uk_number(match)
        if normalized and normalized not in seen:
            seen.add(normalized)
            results.append(normalized)

    return results


def extract_email_domain(line: str):
    match = re.search(
        r"\b[A-Z0-9._%+\-]+@([A-Z0-9.\-]+\.[A-Z]{2,})\b",
        line,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).lower()


def filter_leads(text: str):
    kept = []
    removed = 0

    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r\n")

        if not line.strip():
            continue

        domain = extract_email_domain(line)

        if domain in ALLOWED_EMAIL_DOMAINS:
            kept.append(line)
        else:
            removed += 1

    return kept, removed


def read_text_file(path: str):
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return None


def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("Filter Leads")],
            [KeyboardButton("Extract Numbers")],
        ],
        resize_keyboard=True,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("mode", None)
    await update.message.reply_text(
        "Choose what you want to do:",
        reply_markup=main_keyboard(),
    )


async def choose_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = MODE_FILTER

    await update.message.reply_text(
        "📧 Filter Leads selected.\n\n"
        "Upload a .txt file.\n\n"
        "I will keep only leads containing an email from:\n"
        "• gmail.com\n"
        "• googlemail.com\n"
        "• outlook.com\n"
        "• outlook.co.uk\n"
        "• hotmail.com\n"
        "• hotmail.co.uk\n"
        "• yahoo.com\n"
        "• yahoo.co.uk\n\n"
        "Each lead is treated as one full line."
    )


async def choose_extract(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = MODE_EXTRACT

    await update.message.reply_text(
        "📱 Extract Numbers selected.\n\n"
        "Upload a .txt file.\n\n"
        "I will scan the whole file, extract UK mobile and landline numbers, "
        "convert them to +44 format, remove duplicates, and send them back."
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document:
        return

    filename = document.file_name or "file.txt"

    if not filename.lower().endswith(".txt"):
        await update.message.reply_text("❌ Please upload a .txt file.")
        return

    mode = context.user_data.get("mode")

    if mode not in (MODE_FILTER, MODE_EXTRACT):
        await update.message.reply_text(
            "Please choose Filter Leads or Extract Numbers first.",
            reply_markup=main_keyboard(),
        )
        return

    telegram_file = await document.get_file()

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.txt")
        await telegram_file.download_to_drive(input_path)

        text = read_text_file(input_path)

        if text is None:
            await update.message.reply_text("❌ I couldn't read this text file.")
            return

        if mode == MODE_FILTER:
            status = await update.message.reply_text("🔍 Filtering leads...")

            kept, removed = filter_leads(text)

            if not kept:
                await status.edit_text("❌ No leads matched the allowed email domains.")
                return

            output_path = os.path.join(temp_dir, "filtered_leads.txt")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + "\n")

            await status.edit_text(
                f"✅ Kept {len(kept):,} leads and removed {removed:,}."
            )

            with open(output_path, "rb") as result_file:
                await update.message.reply_document(
                    document=result_file,
                    filename="filtered_leads.txt",
                    caption=(
                        f"✅ {len(kept):,} leads kept\n"
                        f"🗑️ {removed:,} leads removed"
                    ),
                )

        elif mode == MODE_EXTRACT:
            status = await update.message.reply_text("🔍 Extracting UK numbers...")

            numbers = extract_numbers(text)

            if not numbers:
                await status.edit_text("❌ No valid-looking UK numbers were found.")
                return

            output_path = os.path.join(temp_dir, "extracted_numbers.txt")

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(numbers) + "\n")

            await status.edit_text(
                f"✅ Found {len(numbers):,} unique UK numbers."
            )

            with open(output_path, "rb") as result_file:
                await update.message.reply_document(
                    document=result_file,
                    filename="extracted_numbers.txt",
                    caption=(
                        f"✅ {len(numbers):,} unique numbers extracted\n"
                        "🇬🇧 All normalized to +44 format\n"
                        "🧹 Duplicates removed"
                    ),
                )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add BOT_TOKEN to your environment variables."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^Filter Leads$"),
            choose_filter,
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(r"^Extract Numbers$"),
            choose_extract,
        )
    )
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
