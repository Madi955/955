import sys
import os

def check_dependencies():
    """Проверка установленных зависимостей"""
    required_packages = [
        'telebot',
        'PIL',
        'pytesseract', 
        'requests',
        'language_tool_python'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            if package == 'PIL':
                __import__('PIL.Image')
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def main():
    print("🔍 Проверка зависимостей...")
    
    missing = check_dependencies()
    if missing:
        print("❌ Отсутствуют следующие пакеты:")
        for package in missing:
            print(f"   - {package}")
        print("\n📦 Установите их командой:")
        print("pip install pyTelegramBotAPI Pillow pytesseract requests language-tool-python")
        input("Нажмите Enter для выхода...")
        return
    
    print("✅ Все зависимости установлены")
    
    try:
        import telebot
        from PIL import Image
        import pytesseract
        import requests
        from io import BytesIO
        import re
        import language_tool_python
        
        print("✅ Все модули успешно импортированы")
        
    except Exception as e:
        print(f"❌ Ошибка при импорте модулей: {e}")
        input("Нажмите Enter для выхода...")
        return
    
    # Проверяем наличие Tesseract
    try:
        pytesseract.get_tesseract_version()
        print("✅ Tesseract OCR найден")
    except Exception as e:
        print(f"❌ Tesseract OCR не найден: {e}")
        print("📥 Установите Tesseract:")
        print("   Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        print("   Linux: sudo apt-get install tesseract-ocr tesseract-ocr-rus")
        print("   Mac: brew install tesseract tesseract-lang")
        input("Нажмите Enter для выхода...")
        return
    
    # Запрос токена бота
    BOT_TOKEN = input("🤖 Введите токен вашего бота (получите у @BotFather): ").strip()
    
    if not BOT_TOKEN:
        print("❌ Токен бота не введен!")
        input("Нажмите Enter для выхода...")
        return
    
    # Создание бота
    try:
        bot = telebot.TeleBot(BOT_TOKEN)
        print("✅ Бот успешно создан")
    except Exception as e:
        print(f"❌ Ошибка создания бота: {e}")
        input("Нажмите Enter для выхода...")
        return
    
    # Инициализация LanguageTool
    try:
        tool = language_tool_python.LanguageTool('ru-RU')
        print("✅ LanguageTool инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации LanguageTool: {e}")
        input("Нажмите Enter для выхода...")
        return

    def preprocess_text(text):
        """Предварительная обработка текста"""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\(\)\"\']', '', text)
        return text.strip()

    def correct_text(text):
        """Исправление орфографии и пунктуации"""
        try:
            matches = tool.check(text)
            corrected_text = language_tool_python.utils.correct(text, matches)
            
            corrected_text = re.sub(r'\s+([.,!?;:])', r'\1', corrected_text)
            corrected_text = re.sub(r'([.,!?;:])(?=[^\s])', r'\1 ', corrected_text)
            corrected_text = re.sub(r'\s+', ' ', corrected_text)
            
            sentences = re.split(r'([.!?])\s*', corrected_text)
            corrected_text = ''
            for i in range(0, len(sentences)-1, 2):
                sentence = sentences[i].strip()
                punctuation = sentences[i+1] if i+1 < len(sentences) else ''
                if sentence:
                    sentence = sentence[0].upper() + sentence[1:]
                    corrected_text += sentence + punctuation + ' '
            
            return corrected_text.strip()
        
        except Exception as e:
            print(f"Error in text correction: {e}")
            return text

    def extract_text_from_image(image_url):
        """Извлечение текста из изображения с помощью OCR"""
        try:
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content))
            extracted_text = pytesseract.image_to_string(image, lang='rus')
            return extracted_text
        
        except Exception as e:
            print(f"Error in OCR: {e}")
            return None

    @bot.message_handler(commands=['start', 'help'])
    def send_welcome(message):
        welcome_text = """
🤖 Добро пожаловать в бот для исправления текста!

📸 Просто отправьте мне фотографию с текстом, и я:
• Распознаю текст с изображения
• Исправлю орфографические ошибки
• Расставлю знаки препинания
• Верну вам исправленный текст

📝 Вы также можете отправить текст напрямую для исправления.
        """
        bot.reply_to(message, welcome_text)

    @bot.message_handler(content_types=['text'])
    def handle_text(message):
        try:
            user_text = message.text
            bot.send_chat_action(message.chat.id, 'typing')
            corrected_text = correct_text(user_text)
            
            response = f"""
📝 **Исходный текст:**
{user_text}

✅ **Исправленный текст:**
{corrected_text}
            """
            
            bot.reply_to(message, response)
        
        except Exception as e:
            bot.reply_to(message, "❌ Произошла ошибка при обработке текста. Попробуйте еще раз.")

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        try:
            bot.send_chat_action(message.chat.id, 'typing')
            
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
            
            extracted_text = extract_text_from_image(file_url)
            
            if not extracted_text or extracted_text.strip() == '':
                bot.reply_to(message, "❌ Не удалось распознать текст на изображении. Попробуйте с более четким фото.")
                return
            
            processed_text = preprocess_text(extracted_text)
            
            if not processed_text or processed_text.strip() == '':
                bot.reply_to(message, "❌ Текст на изображении пуст или нечитаем.")
                return
            
            corrected_text = correct_text(processed_text)
            
            response = f"""
📸 **Распознанный текст:**
{processed_text}

✅ **Исправленный текст:**
{corrected_text}
            """
            
            bot.reply_to(message, response)
        
        except Exception as e:
            print(f"Error: {e}")
            bot.reply_to(message, "❌ Произошла ошибка при обработке изображения. Попробуйте еще раз.")

    @bot.message_handler(func=lambda message: True)
    def handle_other_messages(message):
        bot.reply_to(message, "📸 Отправьте мне фотографию с текстом или текст для исправления.")

    # Запуск бота
    print("🚀 Бот запускается...")
    print("⏹️  Для остановки бота нажмите Ctrl+C")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Ошибка при работе бота: {e}")
        input("Нажмите Enter для выхода...")

if __name__ == "__main__":
    main()
