from flask import Flask, request
import telebot
import re
from html import escape

# ========================= КОНФИГ =========================
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790  # ← Твой Telegram ID
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Базы
user_balances = {}
user_data = {}

# Настройки
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"
MIN_DEPOSIT = 400

# ========================= ВСПОМОГАТЕЛЬНОЕ =========================
def get_balance(uid):
    if uid not in user_balances:
        user_balances[uid] = 0
    return user_balances[uid]

def delete_msg(chat_id, msg_id):
    try: bot.delete_message(chat_id, msg_id)
    except: pass

# ========================= МЕНЮ =========================
def main_menu():
    k = telebot.types.InlineKeyboardMarkup(row_width=1)
    k.add(telebot.types.InlineKeyboardButton("Заказать ПФ", callback_data="order_pf"))
    k.add(telebot.types.InlineKeyboardButton("Добавить отзыв", callback_data="order_review"))
    k.add(telebot.types.InlineKeyboardButton("Подписчики", callback_data="order_followers"))
    k.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account"))
    k.add(telebot.types.InlineKeyboardButton("Поддержка", url="https://t.me/Avitounlock"))
    return k

# ========================= СТАРТ =========================
@bot.message_handler(commands=['start'])
def start(m):
    bot.clear_step_handler_by_chat_id(m.chat.id)
    bot.send_message(m.chat.id,
        "Avito ПФ Услуги 2025\n\nВыберите услугу:",
        reply_markup=main_menu())

# ========================= ЛИЧНЫЙ КАБИНЕТ =========================
@bot.callback_query_handler(func=lambda c: c.data == "account")
def account(c):
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Пополнить баланс", callback_data="deposit"))
    k.add(telebot.types.InlineKeyboardButton("Назад", callback_data="back_main"))
    bot.edit_message_text(
        f"Личный кабинет\n\nБаланс: *{get_balance(c.from_user.id)}₽*",
        c.message.chat.id, c.message.message_id,
        parse_mode='Markdown', reply_markup=k
    )

@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def back_main(c):
    bot.edit_message_text("Главное меню", c.message.chat.id, c.message.message_id, reply_markup=main_menu())

# ========================= ПОПОЛНЕНИЕ =========================
@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def deposit(c):
    msg = bot.send_message(c.message.chat.id, "Введите сумму (минимум 400₽):", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, deposit_amount)

def deposit_amount(m):
    try:
        amount = int(''.join(filter(str.isdigit, m.text)))
        if amount < MIN_DEPOSIT:
            raise ValueError
    except:
        bot.send_message(m.chat.id, "Ошибка! Минимум 400₽")
        return

    delete_msg(m.chat.id, m.message_id)

    bot.send_message(m.chat.id,
        f"Переведите *{amount}₽* на карту:\n`{YOUR_CARD_NUMBER}`\n\nПосле оплаты — напишите менеджеру",
        parse_mode='Markdown',
        reply_markup=telebot.types.InlineKeyboardMarkup().add(
            telebot.types.InlineKeyboardButton("Написать менеджеру", url=f"t.me/{MANAGER_USERNAME}")
        ))

    # Уведомление админу
    admin_text = (
        f"ЗАПРОС НА ПОПОЛНЕНИЕ\n\n"
        f"Пользователь: @{m.from_user.username or 'нет'}\n"
        f"ID клиента: {m.chat.id}\n"
        f"Сумма: {amount}₽\n"
        f"Карта: `{YOUR_CARD_NUMBER}`"
    )
    bot.send_message(OWNER_ID, admin_text, parse_mode='Markdown')

# ========================= ГЛАВНОЕ: АДМИН-ОТВЕТ =========================
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    try:
        orig_text = (m.reply_to_message.text or m.reply_to_message.caption or "")

        # Ловим ID в ЛЮБОМ формате навсегда
        client_id = None
        patterns = [
            r'ID клиента[:\s]*(\d+)',
            r'ID[:\s]*[:\s]*(\d+)',
            r'\(ID[:\s]*(\d+)\)',
            r'ID[:\s]*[`\'"]?(\d+)[`\'"]?',
            r'клиента[:\s]*(\d+)',
            r'(\d{8,12})'  # последняя страховка
        ]
        for p in patterns:
            match = re.search(p, orig_text, re.IGNORECASE)
            if match:
                client_id = int(match.group(1))
                break

        if not client_id:
            bot.reply_to(m, "ID клиента не найден!\n\nОтветьте реплаем на сообщение, где есть ID пользователя.")
            return

        # Просто нажал "Ответить" — автоподстановка
        if not m.text or m.text.strip() == "":
            amount = "400"
            if match := re.search(r'Сумма[:\s]*(\d+)|(\d+) ?₽', orig_text):
                amount = match.group(1) or match.group(2) or "400"

            delete_msg(OWNER_ID, m.message_id)
            bot.send_message(
                OWNER_ID,
                f"/add_balance {amount}",
                reply_to_message_id=m.reply_to_message.message_id,
                reply_markup=telebot.types.ForceReply(selective=True)
            )
            return

        # Команда пополнения
        if m.text.strip().startswith("/add_balance"):
            try:
                amount = float(m.text.strip().split()[1])
            except:
                bot.reply_to(m, "Правильно: `/add_balance 500`", parse_mode="Markdown")
                return

            user_balances[client_id] = get_balance(client_id) + amount

            bot.send_message(client_id,
                f"Баланс пополнен!\n+*{amount}₽*\nТеперь: *{get_balance(client_id)}₽*",
                parse_mode='Markdown', reply_markup=main_menu())

            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton("Написать клиенту", url=f"t.me/{bot.get_me().username}?start={client_id}"))
            bot.reply_to(m, f"Зачислено +{amount}₽\nБаланс клиента: {get_balance(client_id)}₽", reply_markup=kb)
            return

        # Обычный ответ
        if m.text:
            bot.send_message(client_id, f"*Ответ менеджера:*\n\n{escape(m.text)}", parse_mode="Markdown")

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"t.me/{bot.get_me().username}?start={client_id}"))
        bot.reply_to(m, f"Отправлено → ID {client_id}", reply_markup=kb)

    except Exception as e:
        bot.reply_to(m, f"Ошибка: {e}")

# ========================= ВЕБХУК =========================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().as_text()
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# ========================= ЗАПУСК =========================
if __name__ == '__main__':
    print("Бот запущен и работает!")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)