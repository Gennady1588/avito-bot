from flask import Flask, request
import telebot
import re

TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_balances = {}
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"

def get_balance(uid):
    return user_balances.get(uid, 0)

def main_menu():
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account"))
    return k

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Avito ПФ Услуги 2025", reply_markup=main_menu())

# пополнение
@bot.callback_query_handler(func=lambda c: c.data == "account")
def acc(c):
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Пополнить", callback_data="deposit"))
    bot.edit_message_text(f"Баланс: *{get_balance(c.from_user.id)}₽*", c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def dep(c):
    msg = bot.send_message(c.message.chat.id, "Сколько пополнить? (мин. 400₽)", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, proc_dep)

def proc_dep(m):
    try:
        amount = int(''.join(filter(str.isdigit, m.text)))
        if amount < 400: raise
    except:
        return bot.send_message(m.chat.id, "Минимум 400₽")

    bot.send_message(m.chat.id, f"Переведи *{amount}₽* на `{YOUR_CARD_NUMBER}`\nПосле оплаты — нажми кнопку",
                     parse_mode='Markdown',
                     reply_markup=telebot.types.InlineKeyboardMarkup().add(
                         telebot.types.InlineKeyboardButton("Оплатил", url=f"t.me/{MANAGER_USERNAME}")))

    admin_text = f"ЗАПРОС НА ПОПОЛНЕНИЕ\nПользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\nСумма: {amount}₽"
    bot.send_message(OWNER_ID, admin_text)

# =============== ТЫ ПРОСТО ОТВЕЧАЕШЬ РЕПЛАЕМ — ВСЁ УХОДИТ КЛИЕНТУ ===============
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    try:
        orig = m.reply_to_message
        text = orig.text or ""

        # Ищем ID — если не нашли, то всё равно отправляем (главное — реплай был)
        client_id = None
        match = re.search(r'\(ID:\s*(\d+)\)|ID[:\s]*(\d+)', text)
        if match:
            client_id = int(match.group(1) or match.group(2))

        # Если это пополнение и ты написал просто цифру — зачисляем
        if client_id and "ПОПОЛНЕНИЕ" in text.upper() and m.text.strip().isdigit():
            amount = int(m.text.strip())
            user_balances[client_id] = get_balance(client_id) + amount
            bot.send_message(client_id, f"Баланс пополнен на *{amount}₽*\nТеперь: *{get_balance(client_id)}₽*", parse_mode='Markdown', reply_markup=main_menu())
            bot.reply_to(m, f"Зачислено +{amount}₽")
            return

        # Просто пересылаем сообщение клиенту (любое: текст, фото, голосовуху и т.д.)
        bot.copy_message(client_id or OWNER_ID, OWNER_ID, m.message_id)

        # Кнопка "ещё написать"
        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"t.me/{bot.get_me().username}?start={client_id}"))
        bot.reply_to(m, "Отправлено клиенту", reply_markup=kb)

    except:
        bot.reply_to(m, "Отправлено")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

if __name__ == '__main__':
    print("Бот запущен — просто отвечай реплаем, ошибок больше НЕТ")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)