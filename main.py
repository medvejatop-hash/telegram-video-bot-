import os
import logging
import requests
import re
import threading
from flask import Flask
import yt_dlp

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Ваш токен
BOT_TOKEN = "8429747697:AAFdL7uUTnGWHYcvCfTqeH9X1KnY6j5wUvM"

# Создаем простой веб-сервер для Render
app = Flask('')

@app.route('/')
def home():
    return "Telegram Bot is running!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# Импортируем Telegram бота ПОСЛЕ настройки Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext

class FileHosting:
    @staticmethod
    def upload_to_gofile(file_path):
        """Загружает файл на GoFile (бесплатно, до 10GB)"""
        try:
            response = requests.get('https://api.gofile.io/getServer')
            server_data = response.json()
            
            if server_data['status'] != 'ok':
                return None
                
            server = server_data['data']['server']
            
            with open(file_path, 'rb') as file:
                files = {'file': file}
                upload_response = requests.post(
                    f'https://{server}.gofile.io/uploadFile',
                    files=files
                )
                upload_data = upload_response.json()
            
            if upload_data['status'] == 'ok':
                return {
                    'download_url': upload_data['data']['downloadPage'],
                    'direct_url': upload_data['data']['directLink'],
                    'size': os.path.getsize(file_path),
                    'name': os.path.basename(file_path),
                    'host': 'GoFile'
                }
        except Exception as e:
            logger.error(f"GoFile error: {e}")
        return None

    @staticmethod
    def upload_file(file_path):
        return FileHosting.upload_to_gofile(file_path)

class VideoDownloader:
    @staticmethod
    def download_video(url, quality='720'):
        """Скачивает видео в выбранном качестве"""
        try:
            if quality == '1080':
                format_option = 'best[height<=1080]'
            elif quality == '720':
                format_option = 'best[height<=720]'
            elif quality == 'audio':
                format_option = 'bestaudio'
            else:
                format_option = 'best'
            
            ydl_opts = {
                'format': format_option,
                'outtmpl': 'downloads/%(title)s.%(ext)s',
                'quiet': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
            return file_path, info['title'], 'video'
            
        except Exception as e:
            raise Exception(f"Ошибка скачивания: {str(e)}")

downloader = VideoDownloader()
file_hosting = FileHosting()

def start(update: Update, context: CallbackContext):
    """Команда /start"""
    welcome_text = """
🎬 Video Downloader Pro 🎬

Я скачиваю видео с YouTube и TikTok через внешний хостинг!

📹 Без ограничений размера!
💾 Видео любого размера

Просто отправьте ссылку!
    """
    update.message.reply_text(welcome_text)

def handle_message(update: Update, context: CallbackContext):
    """Обработка текстовых сообщений"""
    url = update.message.text.strip()
    
    if not re.match(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+', url):
        update.message.reply_text("❌ Пожалуйста, отправьте валидную ссылку")
        return
    
    update.message.reply_text("🔍 Анализирую ссылку...")
    
    if 'youtube.com' in url or 'youtu.be' in url:
        keyboard = [
            [InlineKeyboardButton("🎥 4K", callback_data="quality_4k")],
            [InlineKeyboardButton("📹 1080p", callback_data="quality_1080")],
            [InlineKeyboardButton("📹 720p", callback_data="quality_720")],
            [InlineKeyboardButton("🎵 Аудио", callback_data="quality_audio")],
        ]
    elif 'tiktok.com' in url:
        keyboard = [[InlineKeyboardButton("📹 Скачать TikTok", callback_data="quality_tiktok")]]
    else:
        update.message.reply_text("❌ Поддерживаются только YouTube и TikTok")
        return
    
    context.user_data['current_url'] = url
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите качество:", reply_markup=reply_markup)

def handle_quality(update: Update, context: CallbackContext):
    """Обработка выбора качества с внешним хостингом"""
    query = update.callback_query
    query.answer()
    
    quality = query.data.replace('quality_', '')
    url = context.user_data.get('current_url')
    
    if not url:
        query.edit_message_text("❌ Ошибка: ссылка не найдена")
        return
    
    quality_names = {
        '4k': '4K Ultra HD', 
        '1080': '1080p Full HD',
        '720': '720p HD', 
        'audio': 'аудио MP3',
        'tiktok': 'оригинальное качество'
    }
    
    quality_name = quality_names.get(quality, quality)
    
    query.edit_message_text(f"⏬ Скачиваю в качестве {quality_name}...")
    
    try:
        file_path, title, file_type = downloader.download_video(url, quality)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        
        query.edit_message_text(f"📦 Видео скачано: {file_size_mb:.1f} МБ\n🔼 Загружаю на хостинг...")
        
        upload_result = file_hosting.upload_file(file_path)
        
        if not upload_result:
            os.remove(file_path)
            query.edit_message_text("❌ Не удалось загрузить на хостинг.")
            return
        
        message = f"""
🎬 {title}

📹 Качество: {quality_name}
💾 Размер: {file_size_mb:.1f} МБ
🏠 Хостинг: {upload_result['host']}

💡 Скачайте по ссылке ниже:
        """
        
        keyboard = [
            [InlineKeyboardButton("🚀 Скачать сейчас", url=upload_result['download_url'])],
            [InlineKeyboardButton("🔄 Новое видео", callback_data="new_video")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.edit_message_text(
            message,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        
        os.remove(file_path)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        try:
            if 'file_path' in locals():
                os.remove(file_path)
        except:
            pass
        query.edit_message_text(f"❌ Ошибка: {str(e)}")

def handle_new_video(update: Update, context: CallbackContext):
    """Обработка запроса на новое видео"""
    query = update.callback_query
    query.answer()
    query.edit_message_text("🔄 Отправьте новую ссылку на видео")

def main():
    """Запуск бота"""
    # Запускаем веб-сервер для Render
    keep_alive()
    
    # Создаем папку для загрузок
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    # Создаем бота (старая версия API)
    updater = Updater(BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Добавляем обработчики
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CallbackQueryHandler(handle_quality, pattern="^quality_"))
    dispatcher.add_handler(CallbackQueryHandler(handle_new_video, pattern="^new_video"))
    
    # Запускаем бота
    print("🎬 Video Downloader Bot запущен!")
    print("📹 Поддерживает: YouTube 4K/1080p/720p + TikTok")
    print("🌐 Веб-сервер запущен на порту 8080")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()