from flask import Flask, request
import telebot
import re
from html import escape

TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_balances = {}

MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"
MIN_DEPOSIT = 400

def get_balance(uid):
    return user_balances.get(uid, 0)

def main_menu():
    k = telebot.types.InlineKeyboardMarkup(row_width=1)
    k.add(telebot.types.InlineKeyboardButton("Заказать ПФ", callback_data="pf"))
    k.add(telebot.types.InlineKeyboardButton("Добавить отзыв", callback_data="review"))
    k.add(telebot.types.InlineKeyboardButton("Подписчики", callback_data="followers"))
    k.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account"))
    k.add(telebot.types.InlineKeyboardButton("Поддержка", url="https://t.me/Avitounlock"))
    return k

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Avito ПФ Услуги 2025\nВыберите услугу:", reply_markup=main_menu())

# пополнение
@bot.callback_query_handler(func=lambda c: c.data == "account")
def acc(c):
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Пополнить", callback_data="deposit"))
    bot.edit_message_text(f"Баланс: *{get_balance(c.from_user.id)}₽*", c.message.chat.id, c.message.message_id,
                          parse_mode='Markdown', reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def dep(c):
    msg = bot.send_message(c.message.chat.id, "Сумма пополнения (мин. 400₽):", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, proc_dep)

def proc_dep(m):
    try:
        amount = int(''.join(filter(str.isdigit, m.text)))
        if amount < 400: raise
    except:
        return bot.send_message(m.chat.id, "Минимум 400₽")

    bot.send_message(m.chat.id,
        f"Переведи *{amount}₽* на `{YOUR_CARD_NUMBER}`\nПосле оплаты — нажми кнопку",
        parse_mode='Markdown',
        reply_markup=telebot.types.InlineKeyboardMarkup().add(
            telebot.types.InlineKeyboardButton("Оплатил", url=f"t.me/{MANAGER_USERNAME}")))

    # Теперь всегда один формат — с (ID: )
    admin_text = (
        f"ЗАПРОС НА ПОПОЛНЕНИЕ\n\n"
        f"Пользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\n"
        f"Желаемая сумма: {amount} ₽\n"
        f"Карта для проверки: {YOUR_CARD_NUMBER}"
    )
    bot.send_message(OWNER_ID, admin_text)

# === ГЛАВНЫЙ ХЕНДЛЕР — РАБОТАЕТ НА ВСЕХ СТАРЫХ И НОВЫХ УВЕДОМЛЕНИЯХ ===
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    text = (m.reply_to_message.text or m.reply_to_message.caption or "")

    # Ловим ЛЮБОЙ возможный ID в истории твоего бота
    client_id = None
    patterns = [
        r'\(ID:\s*(\d+)\)',           # ← точно твой старый формат
        r'ID[:\s]*(\d+)',
        r'ID клиента[:\s]*(\d+)',
        r'ID[:\s=]+\s*(\d+)',
        r'(\d{8,12})'                 # запасной
    ]
    for p in patterns:
        if match := re.search(p, text):
            client_id = int(match.group(1))
            break

    if not client_id:
        return bot.reply_to(m, "ID не найден")

    # Если написал просто цифру на запрос пополнения — зачисляем
    if "ПОПОЛНЕНИЕ" in text and m.text.strip().isdigit():
        amount = int(m.text.strip())
        user_balances[client_id] = get_balance(client_id) + amount
        bot.send_message(client_id, f"Баланс пополнен на *{amount}₽*\nТеперь: *{get_balance(client_id)}₽*", 
                         parse_mode='Markdown', reply_markup=main_menu())
        return bot.reply_to(m, f"Зачислено +{amount}₽")

    # Обычные сообщения
    if m.text:
        bot.send_message(client_id, m.text)
    elif m.photo:
        bot.send_photo(client_id, m.photo[-1].file_id, caption=m.caption)
    elif m.voice:
        bot.send_voice(client_id, m.voice.file_id)
    elif m.video:
        bot.send_video(client_id, m.video.file_id, caption=m.caption)
    elif m.document:
        bot.send_document(client_id, m.document.file_id, caption=m.caption)
    elif m.sticker:
        bot.send_sticker(client_id, m.sticker.file_id)

    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"t.me/{bot.get_me().username}?start={client_id}"))
    bot.reply_to(m, "Отправлено", reply_markup=kb)

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

if __name__ == '__main__':
    print("Бот запущен — теперь ВСЁ работает")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)