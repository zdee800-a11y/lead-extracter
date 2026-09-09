# Telegram UK Number Extractor

A simple Telegram bot that accepts `.txt` files, scans the entire file for UK phone numbers, removes duplicates, converts valid-looking UK numbers to `+44` format, and sends the cleaned numbers back in a `.txt` file.

## Supported formats

Examples:

- `07784540644`
- `+447784540644`
- `447784540644`
- `00447784540644`
- `020 7946 0958`
- `0161 496 0000`
- `+44 (0)20 7946 0958`
- `0330 123 4567`
- `0800 123 4567`

## Setup

1. Create a Telegram bot using BotFather.
2. Copy your bot token.
3. Add an environment variable named:

```text
BOT_TOKEN
```

Do not put the real token directly inside `bot.py`.

## Local install

```bash
pip install -r requirements.txt
python bot.py
```

## Railway

Upload this project to GitHub and deploy the repository on Railway.

Add this Railway variable:

```text
BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
```

Use this start command:

```text
python bot.py
```

## Output

The bot sends back:

```text
extracted_numbers.txt
```

All recognized UK numbers are normalized to `+44` format.
