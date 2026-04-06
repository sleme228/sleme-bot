import logging
import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from PIL import Image, ImageEnhance, ImageFilter
import os

# Устанавливаем SelectorEventLoop (важно для Windows)
try:
    from asyncio import WindowsSelectorEventLoopPolicy
    if isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
except Exception:
    pass

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# OCR.Space API
OCR_SPACE_API = "https://api.ocr.space/parse/image"
API_KEY = "K86275494388957"  # Публичный тестовый ключ

# Функция OCR с улучшением изображения
async def ocr_space_photo(file_path):
    # Открываем изображение
    image = Image.open(file_path)

    # 1. Конвертируем в чёрно-белый (усиливаем контраст)
    image = image.convert('L')

    # 2. Увеличиваем резкость
    image = image.filter(ImageFilter.SHARPEN)

    # 3. Повышаем контраст
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)

    # 4. Бинаризация (чёрно-белое по порогу)
    image = image.point(lambda x: 0 if x < 140 else 255, '1')

    # Сохраняем обработанное изображение
    processed_path = 'processed_photo.jpg'
    image.save(processed_path, 'JPEG', quality=95)

    # Отправляем улучшенное фото в OCR
    with open(processed_path, 'rb') as image_file:
        response = requests.post(
            OCR_SPACE_API,
            files={'file': image_file},
            data={
                'apikey': API_KEY,
                'language': 'rus',
                'isOverlayRequired': False,
                'scale': True,
                'detectOrientation': True,
                'OCREngine': 2  # Используем более точный движок
            }
        )

    # Удаляем временные файлы
    if os.path.exists(processed_path):
        os.remove(processed_path)

    result = response.json()
    if result.get("ParsedResults"):
        text = result["ParsedResults"][0]["ParsedText"]
        # Очищаем текст: убираем пустые строки и лишние пробелы
        cleaned_lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(cleaned_lines)
    else:
        return "Не удалось распознать текст."

# Обработчик фото
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📸 Фото получено! Распознаю текст...")

    photo_file = await update.message.photo[-1].get_file()
    file_path = 'downloaded_photo.jpg'
    await photo_file.download_to_drive(file_path)

    extracted_text = await ocr_space_photo(file_path)
    extracted_text = extracted_text.strip()

    if not extracted_text or extracted_text == "":
        extracted_text = "На изображении не найден текст."

    await update.message.reply_text(f"📋 Распознанный текст:\n{extracted_text}")

# Создаём приложение
def create_application():
    app = ApplicationBuilder().token("8696706532:AAEN6IwwzJ9J5DqXhYeUyqVKwM3okGtXOa8").build()
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    return app

# Прямой запуск без asyncio.run()
if __name__ == '__main__':
    # Убедитесь, что цикл — Selector, а не Proactor
    try:
        if isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
    except:
        pass

    # Получаем или создаём цикл
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Создаём приложение
    application = create_application()

    # Запускаем polling напрямую
    try:
        loop.run_until_complete(application.run_polling())
    except KeyboardInterrupt:
        print("Бот остановлен.")
    finally:
        loop.close()