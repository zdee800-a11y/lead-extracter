import os
import re
import tempfile
import logging

from telegram import Update
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


def normalize_uk_number(raw_number: str):
    """
    Normalize UK mobile and landline numbers to +44 format.

    Examples:
    07784540644       -> +447784540644
    +447784540644     -> +447784540644
    00447784540644    -> +447784540644
    447784540644      -> +447784540644

    020 7946 0958     -> +442079460958
    +44 20 7946 0958  -> +442079460958
    0161 496 0000     -> +441614960000
    """

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

    # Handles +44 (0)20... style numbers
    if national.startswith("0"):
        national = national[1:]

    if not national.isdigit():
        return None

    # UK mobile numbers
    if len(national) == 10 and national.startswith("7"):
        return "+44" + national

    # UK geographic landlines
    if len(national) in (9, 10) and national.startswith(("1", "2")):
        return "+44" + national

    # UK 03 numbers
    if len(national) == 10 and national.startswith("3"):
        return "+44" + national

    # UK 08 numbers
    if len(national) == 10 and national.startswith("8"):
        return "+44" + national

    return None


def extract_numbers(text: str):
    """
    Scan an entire text file for UK mobile and landline numbers.

    Supports formats such as:
    07784 540644
    +44 7784 540644
    0044 7784 540644
    447784540644
    020 7946 0958
    +44 (0)20 7946 0958
    0161 496 0000
    0330 123 4567
    0800 123 4567
    """

    pattern = re.compile(
        r"""
        (?<!\d)
        (
            \+44
            [\s().\-]*
            (?:0[\s().\-]*)?
            \d
            (?:[\s().\-]*\d){8,9}

            |

            0044
            [\s().\-]*
            (?:0[\s().\-]*)?
            \d
            (?:[\s().\-]*\d){8,9}

            |

            44
            [\s().\-]*
            \d
            (?:[\s().\-]*\d){8,9}

            |

            0
            \d
            (?:[\s().\-]*\d){8,9}

            |

            7
            (?:[\s().\-]*\d){9}
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


def read_text_file(path: str):
    for encoding in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue

    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 UK Number Extractor\n\n"
        "Upload a .txt file and I will:\n"
        "• scan the entire file\n"
        "• extract UK mobile and landline numbers\n"
        "• convert them to +44 format\n"
        "• remove duplicates\n"
        "• send the results back as a .txt file"
    )


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document:
        return

    filename = document.file_name or "file.txt"

    if not filename.lower().endswith(".txt"):
        await update.message.reply_text("❌ Please upload a .txt file.")
        return

    status = await update.message.reply_text("🔍 Looking through the file...")

    telegram_file = await document.get_file()

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = os.path.join(temp_dir, "input.txt")
        output_path = os.path.join(temp_dir, "extracted_numbers.txt")

        await telegram_file.download_to_drive(input_path)

        text = read_text_file(input_path)

        if text is None:
            await status.edit_text("❌ I couldn't read this text file.")
            return

        numbers = extract_numbers(text)

        if not numbers:
            await status.edit_text("❌ No valid-looking UK numbers were found.")
            return

        with open(output_path, "w", encoding="utf-8") as output:
            output.write("\n".join(numbers) + "\n")

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
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
