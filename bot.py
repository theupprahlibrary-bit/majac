import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Check Environment Variables ---
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN')

# Log which variables are missing for debugging
if not TELEGRAM_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is not set!")
if not APIFY_API_TOKEN:
    logger.error("❌ APIFY_API_TOKEN is not set!")

# Only import Apify if token exists
if APIFY_API_TOKEN:
    from apify_client import ApifyClient
    client = ApifyClient(APIFY_API_TOKEN)
else:
    client = None
    logger.warning("⚠️ Apify client disabled - missing API token")

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔍 *AnswerPublicBot*\n\n"
        "Send me a keyword or a question, and I'll find what people are searching for!\n\n"
        "Example: `how to bake a cake`",
        parse_mode='Markdown'
    )
    
    # Check if API tokens are available
    if not APIFY_API_TOKEN:
        await update.message.reply_text(
            "⚠️ *Warning:* Apify API token is not configured. "
            "Please contact the bot administrator.",
            parse_mode='Markdown'
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.strip()

    if len(keyword) < 2:
        await update.message.reply_text("Please enter a keyword with at least 2 characters.")
        return

    # Check if Apify is available
    if not APIFY_API_TOKEN or client is None:
        await update.message.reply_text(
            "❌ Apify API is not configured. Please set the APIFY_API_TOKEN environment variable."
        )
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
        for item in results[:10]:
            if 'question' in item:
                summary += f"❓ {item['question'][:100]}\n"
                count += 1
                if count >= 5:
                    break

        if count == 0:
            summary += "No questions found in the results."

        summary += "\n🔗 Full dataset: https://console.apify.com/storage/datasets/" + run["defaultDatasetId"]
        await update.message.reply_text(summary, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "Sorry, something went wrong while fetching data. Please try again later.\n"
            f"Error: {str(e)[:100]}"
        )

def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ Cannot start bot - TELEGRAM_BOT_TOKEN is missing!")
        logger.error("Please add TELEGRAM_BOT_TOKEN to Railway environment variables.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 AnswerPublicBot is starting with long polling...")
    app.run_polling()

if __name__ == '__main__':
    main()
