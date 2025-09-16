
import os
import json
from telegram import Update, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with a button that opens the web app."""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Открыть приложение",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Добро пожаловать в кафе "Мандарин"!\nНажмите на кнопку, чтобы открыть приложение',
        reply_markup=reply_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming WebAppData from the Web App."""
    if update.effective_message and update.effective_message.web_app_data:
        data = update.effective_message.web_app_data.data
        button_text = update.effective_message.web_app_data.button_text

        # The data sent from the WebApp is a string. If it's JSON, you'll need to parse it.
        try:
            parsed_data = json.loads(data)
            response_text = f"Received data from Web App: {parsed_data}\n(Button text: {button_text})"
            # You can now process parsed_data, e.g., save to DB, trigger another action
            user_id = update.effective_user.id
            print(f"User {user_id} sent data: {parsed_data}") # For logging
        except json.JSONDecodeError:
            response_text = f"Received raw data from Web App: {data}\n(Button text: {button_text})"
            print(f"Raw data from Web App: {data}") # For logging

        await update.message.reply_text(response_text)
    else:
        await update.message.reply_text("Received something from Web App, but no data.")


def main() -> None:
    """Runs the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    # Add a MessageHandler to process data sent back from the Web App
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
