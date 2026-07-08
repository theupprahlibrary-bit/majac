import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from apify_client import ApifyClient

# --- Setup ---
logging.basicConfig(level=logging.INFO)

# --- Apify Client ---
APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

if not APIFY_API_TOKEN or not TELEGRAM_TOKEN:
    raise ValueError("Missing required environment variables!")

client = ApifyClient(APIFY_API_TOKEN)

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *AnswerPublicBot*\n\n"
        "Send me a keyword or a question, and I'll use AnswerThePublic to find "
        "what people are searching for!\n\n"
        "Example: `how to bake a cake`",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()

    if len(keyword) < 2:
        await update.message.reply_text("Please enter a keyword with at least 2 characters.")
        return

    await update.message.reply_text(f"🔎 Researching: *{keyword}*...\n\nThis may take a moment.", parse_mode='Markdown')

    try:
        # Run the Answer The Public Actor on Apify
        run_input = {
            "keywords": [keyword],
        }
        run = client.actor("deadlyaccurate/answer-the-public").call(run_input=run_input)

        # Fetch results
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            await update.message.reply_text("No results found for that keyword.")
            return

        # Format a summary for Telegram
        summary = f"📊 *Results for '{keyword}':*\n\n"
        count = 0
        for item in results[:10]:  # Limit to first 10 results
            if 'question' in item:
                summary += f"❓ {item['question'][:100]}\n"
                count += 1
            if count >= 5:
                break

        summary += "\n🔗 Check the full dataset at: https://console.apify.com/storage/datasets/" + run["defaultDatasetId"]
        await update.message.reply_text(summary, parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("Sorry, something went wrong while fetching data. Please try again later.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 AnswerPublicBot is starting with long polling...")
    app.run_polling()

if __name__ == '__main__':
    main()
