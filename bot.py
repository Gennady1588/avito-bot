from flask import Flask, request
import telebot
import re
from html import escape

TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_balances = {}
user_data = {}

MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"
MIN_DEPOSIT = 400

def get_balance(uid):
    if uid not in user_balances:
        user_balances[uid] = 0
    return user_balances[uid]

def main_menu():
    k = telebot.types.InlineKeyboardMarkup(row_width=1)
    k.add(telebot.types.InlineKeyboardButton("Заказать ПФ", callback_data="order_pf"))
    k.add(telebot.types.InlineKeyboardButton("Добавить отзыв", callback_data="order_review"))
    k.add(telebot.types.InlineKeyboardButton("Подписчики", callback_data="order_followers"))
    k.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account"))
    k.add(telebot.types.InlineKeyboardButton("Поддержка", url="https://t.me/Avitounlock"))
    return k

@bot.message_handler(commands=['start'])
def start(m):
    bot.clear_step_handler_by_chat_id(m.chat.id)
    bot.send_message(m.chat.id, "Avito ПФ Услуги 2025\nВыберите услугу:", reply_markup=main_menu())

# ==================== ПОПОЛНЕНИЕ ====================
@bot.callback_query_handler(func=lambda c: c.data == "account")
def account(c):
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Пополнить баланс", callback_data="deposit"))
    bot.edit_message_text(f"Баланс: *{get_balance(c.from_user.id)}₽*", c.message.chat.id, c.message.message_id,
                          parse_mode='Markdown', reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def deposit(c):
    msg = bot.send_message(c.message.chat.id, "Сколько пополнить? (мин. 400₽)", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, process_deposit)

def process_deposit(m):
    try:
        amount = int(''.join(filter(str.isdigit, m.text)))
        if amount < 400: raise
    except:
        bot.send_message(m.chat.id, "Ошибка! Минимум 400₽")
        return

    bot.send_message(m.chat.id,
        f"Переведите *{amount}₽* на карту `{YOUR_CARD_NUMBER}`\nПосле оплаты — напиши менеджеру",
        parse_mode='Markdown',
        reply_markup=telebot.types.InlineKeyboardMarkup().add(
            telebot.types.InlineKeyboardButton("Написать менеджеру", url=f"t.me/{MANAGER_USERNAME}")))

    admin_text = (
        f"ЗАПРОС НА ПОПОЛНЕНИЕ\n"
        f"Пользователь: @{m.from_user.username or 'нет'}\n"
        f"ID: {m.chat.id}\n"
        f"Сумма: {amount}₽"
    )
    bot.send_message(OWNER_ID, admin_text, parse_mode='Markdown')

# ==================== АДМИН — ПРОСТЫЕ ОТВЕТЫ ====================
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_simple_reply(m):
    try:
        orig_text = (m.reply_to_message.text or m.reply_to_message.caption or "")

        # Ищем ID клиента — ловит абсолютно всё
        client_id = None
        for pattern in [r'ID[:\s]*[:=\s]*(\d+)', r'\(ID[:\s]*(\d+)\)', r'ID[:\s]*(\d+)', r'(\d{8,12})']:
            match = re.search(pattern, orig_text)
            if match:
                client_id = int(match.group(1))
                break

        if not client_id:
            bot.reply_to(m, "Не смог найти ID клиента в этом сообщении.")
            return

        # Если это пополнение и ты написал просто цифру (например 500) — зачисляем автоматически
        if "ПОПОЛНЕНИЕ" in orig_text.upper() and m.text.strip().isdigit():
            amount = int(m.text.strip())
            user_balances[client_id] = get_balance(client_id) + amount
            bot.send_message(client_id,
                f"Баланс пополнен на *{amount}₽*\nТеперь: *{get_balance(client_id)}₽*",
                parse_mode='Markdown', reply_markup=main_menu())
            bot.reply_to(m, f"Зачислено +{amount}₽ клиенту {client_id}")
            return

        # Обычный ответ — просто пересылаем как есть
        if m.text:
            bot.send_message(client_id, f"*{escape(m.text)}*", parse_mode='Markdown')
        elif m.photo:
            bot.send_photo(client_id, m.photo[-1].file_id, caption=escape(m.caption or ''), parse_mode='Markdown')
        elif m.voice:
            bot.send_voice(client_id, m.voice.file_id)
        elif m.video:
            bot.send_video(client_id, m.video.file_id, caption=escape(m.caption or ''), parse_mode='Markdown')
        elif m.document:
            bot.send_document(client_id, m.document.file_id, caption=escape(m.caption or ''), parse_mode='Markdown')
        elif m.sticker:
            bot.send_sticker(client_id, m.sticker.file_id)
        else:
            bot.reply_to(m, "Сообщение отправлено")
            return

        # Кнопка «ещё написать»
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"t.me/{bot.get_me().username}?start={client_id}"))
        bot.reply_to(m, "Отправлено клиенту", reply_markup=kb)

    except Exception as e:
        bot.reply_to(m, f"Ошибка: {e}")

# ==================== ВЕБХУК ====================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

if __name__ == '__main__':
    print("Бот запущен — теперь отвечаешь как человек!")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)