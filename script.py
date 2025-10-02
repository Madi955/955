import telebot
from PIL import Image
import pytesseract
import requests
from io import BytesIO
import re
import language_tool_python

# Настройки
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
tool = language_tool_python.LanguageTool('ru-RU')  # Для русского языка

# Создание бота
bot = telebot.TeleBot(BOT_TOKEN)

def preprocess_text(text):
    """Предварительная обработка текста"""
    # Убираем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    # Убираем символы, которые могут мешать
    text = re.sub(r'[^\w\s\.\,\!\?\-\:\(\)\"\']', '', text)
    return text.strip()

def correct_text(text):
    """Исправление орфографии и пунктуации"""
    try:
        # Исправляем ошибки с помощью LanguageTool
        matches = tool.check(text)
        corrected_text = language_tool_python.utils.correct(text, matches)
        
        # Дополнительная обработка для улучшения пунктуации
        corrected_text = re.sub(r'\s+([.,!?;:])', r'\1', corrected_text)  # Убираем пробелы перед знаками препинания
        corrected_text = re.sub(r'([.,!?;:])(?=[^\s])', r'\1 ', corrected_text)  # Добавляем пробелы после знаков препинания
        corrected_text = re.sub(r'\s+', ' ', corrected_text)  # Убираем лишние пробелы
        
        # Делаем первую букву предложения заглавной
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
        # Скачиваем изображение
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))
        
        # Используем pytesseract для распознавания текста
        # Указываем язык (rus для русского)
        extracted_text = pytesseract.image_to_string(image, lang='rus')
        
        return extracted_text
    
    except Exception as e:
        print(f"Error in OCR: {e}")
        return None

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Обработчик команд start и help"""
    welcome_text = """
🤖 Добро пожаловать в бот для исправления текста!

📸 Просто отправьте мне фотографию с текстом, и я:
• Распознаю текст с изображения
• Исправлю орфографические ошибки
• Расставлю знаки препинания
• Верну вам исправленный текст

📝 Вы также можете отправить текст напрямую для исправления.

💡 Советы для лучшего результата:
• Используйте четкие фотографии
• Текст должен быть хорошо виден
• Избегайте сильных наклонов
    """
    bot.reply_to(message, welcome_text)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Обработчик текстовых сообщений"""
    try:
        user_text = message.text
        
        # Показываем, что бот работает
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Исправляем текст
        corrected_text = correct_text(user_text)
        
        # Формируем ответ
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
    """Обработчик фотографий"""
    try:
        # Показываем, что бот работает
        bot.send_chat_action(message.chat.id, 'typing')
        
        # Получаем файл фотографии (берем самую большую)
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"
        
        # Извлекаем текст из изображения
        extracted_text = extract_text_from_image(file_url)
        
        if not extracted_text or extracted_text.strip() == '':
            bot.reply_to(message, "❌ Не удалось распознать текст на изображении. Попробуйте с более четким фото.")
            return
        
        # Предварительная обработка
        processed_text = preprocess_text(extracted_text)
        
        if not processed_text or processed_text.strip() == '':
            bot.reply_to(message, "❌ Текст на изображении пуст или нечитаем.")
            return
        
        # Исправляем текст
        corrected_text = correct_text(processed_text)
        
        # Формируем ответ
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
    """Обработчик всех остальных типов сообщений"""
    bot.reply_to(message, "📸 Отправьте мне фотографию с текстом или текст для исправления.")

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling()
