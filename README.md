# Telegram Lead Tools Bot

This Telegram bot has two options:

## Filter Leads
Upload a `.txt` file where each lead is one line.

Only leads with these email domains are kept:
- gmail.com
- googlemail.com
- outlook.com
- outlook.co.uk
- hotmail.com
- hotmail.co.uk
- yahoo.com
- yahoo.co.uk

The bot returns `filtered_leads.txt`.

## Extract Numbers
Upload a `.txt` file and the bot scans the whole file for UK mobile and landline numbers.

It:
- converts recognized UK numbers to +44 format
- removes duplicates
- returns `extracted_numbers.txt`

## Setup
Create a Telegram bot with BotFather.

Add your token as an environment variable:

BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN

Install:
pip install -r requirements.txt

Run:
python bot.py

## Railway
Connect the GitHub repo to Railway, add the BOT_TOKEN variable, and use:

python bot.py
