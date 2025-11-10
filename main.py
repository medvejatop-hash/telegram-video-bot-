import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8429747697:AAFdL7uUTnGWHYcvCfTqeH9X1KnY6j5wUvM"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("🎬 Отправьте ссылку на YouTube видео")

def handle_message(update: Update, context: CallbackContext):
    url = update.message.text
    
    if 'youtube.com' in url or 'youtu.be' in url:
        update.message.reply_text("⏬ Скачиваю видео...")
        
        try:
            ydl_opts = {
                'format': 'best[height<=720]',
                'outtmpl': 'video.%(ext)s',
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = 'video.mp4'
            
            with open(file_path, 'rb') as video_file:
                update.message.reply_video(video=video_file, caption="✅ Ваше видео")
            
            os.remove(file_path)
            
        except Exception as e:
            update.message.reply_text(f"❌ Ошибка: {str(e)}")
    else:
        update.message.reply_text("❌ Отправьте ссылку на YouTube")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_message))
    
    print("Бот запущен!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()