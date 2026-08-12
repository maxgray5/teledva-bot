import os
import re
import json
from datetime import datetime, timedelta

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== КОНФИГУРАЦИЯ =====
TOKEN = "8771127514:AAH0xHFZIY_e_vfUH8KjWb8NmQDwXk92p0c"  # Вставь свой токен
SHEET_NAME = "Промокоды ТелеДва"  # Название таблицы

# ===== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS =====
def get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials_json = os.environ.get('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise Exception("Переменная GOOGLE_CREDENTIALS не найдена!")
    creds_dict = json.loads(credentials_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# ===== ПРОВЕРКА: получал ли пользователь промокод за последние 24 часа =====
def can_get_promo(phone, sheet):
    records = sheet.get_all_values()
    for row in records[1:]:  # Пропускаем заголовки
        if len(row) >= 3 and row[1] == phone:
            last_time_str = row[2]
            if last_time_str:
                last_time = datetime.strptime(last_time_str, "%Y-%m-%d %H:%M")
                if datetime.now() - last_time < timedelta(hours=24):
                    return False, last_time
    return True, None

# ===== ВЫДАЧА ПЕРВОГО СВОБОДНОГО ПРОМОКОДА ИЗ ТАБЛИЦЫ =====
def assign_promo(phone, sheet):
    records = sheet.get_all_values()
    # Идём по строкам, начиная со второй (первая — заголовки)
    for i, row in enumerate(records[1:], start=2):
        if len(row) >= 1 and row[0]:  # Если в колонке A есть промокод
            # Проверяем, что колонка B (телефон) пустая — промокод не выдан
            if len(row) < 2 or not row[1]:
                sheet.update(f'B{i}', phone)
                sheet.update(f'C{i}', datetime.now().strftime("%Y-%m-%d %H:%M"))
                return row[0]
    return None  # Свободных промокодов нет

# ===== ОБРАБОТЧИК КОМАНДЫ /start =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("📱 Отправить номер телефона", request_contact=True)
    reply_markup = ReplyKeyboardMarkup([[button]], resize_keyboard=True)
    await update.message.reply_text(
        "👋 Привет! Я бот ТелеДва.\n\n"
        "Нажми на кнопку ниже, чтобы получить персональный промокод на скидку 28%.",
        reply_markup=reply_markup
    )

# ===== ОБРАБОТЧИК НОМЕРА ТЕЛЕФОНА =====
async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    phone = re.sub(r'[^0-9]', '', contact.phone_number)

    sheet = get_sheet()
    allowed, last_time = can_get_promo(phone, sheet)

    if not allowed:
        await update.message.reply_text(
            f"⏳ Вы уже получали промокод {last_time.strftime('%d.%m.%Y в %H:%M')}.\n"
            "Следующий промокод будет доступен завтра."
        )
        return

    promo = assign_promo(phone, sheet)

    if promo:
        await update.message.reply_text(
            f"✅ Ваш промокод:\n\n"
            f"<b>{promo}</b>\n\n"
            f"Покажите его в любом салоне ТелеДва (салоны связи Т2) и получите скидку 28% на защитную плёнку.\n"
            f"📍 Адреса салонов: https://teledva.tilda.ws/",
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text(
            "😕 К сожалению, все промокоды разобраны. Новые появятся позже."
        )

# ===== ЗАПУСК БОТА =====
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
