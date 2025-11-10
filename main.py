import os
import requests
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = "8429747697:AAFdL7uUTnGWHYcvCfTqeH9X1KnY6j5wUvM"

class VideoDownloader:
    @staticmethod
    def download_video(url, quality='720'):
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
                
            return file_path, info['title']
            
        except Exception as e:
            raise Exception(f"Ошибка: {str(e)}")

downloader = VideoDownloader()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎬 Video Bot - отправьте ссылку на YouTube/TikTok")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    
    if 'youtube.com' in url or 'youtu.be' in url:
        keyboard = [
            [InlineKeyboardButton("📹 1080p", callback_data="quality_1080")],
            [InlineKeyboardButton("📹 720p", callback_data="quality_720")],
            [InlineKeyboardButton("🎵 Аудио", callback_data="quality_audio")],
        ]
    elif 'tiktok.com' in url:
        keyboard = [[InlineKeyboardButton("📹 Скачать", callback_data="quality_tiktok")]]
    else:
        await update.message.reply_text("❌ Неподдерживаемая ссылка")
        return
    
    context.user_data['url'] = url
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите качество:", reply_markup=reply_markup)

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    quality = query.data.replace('quality_', '')
    url = context.user_data.get('url')
    
    await query.edit_message_text(f"⏬ Скачиваю...")
    
    try:
        file_path, title = downloader.download_video(url, quality)
        
        with open(file_path, 'rb') as file:
            await context.bot.send_video(
                chat_id=query.message.chat_id,
                video=file,
                caption=f"🎬 {title}"
            )
        
        os.remove(file_path)
        await query.edit_message_text("✅ Готово!")
        
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')
    
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_quality, pattern="^quality_"))
    
    print("Бот запущен!")
    application.run_polling()

if __name__ == "__main__":
    main()
