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

    bot.send_message(m.chat.id, f"Переведи *{amount}₽* на `{YOUR_CARD_NUMBER}`", parse_mode='Markdown',
                     reply_markup=telebot.types.InlineKeyboardMarkup().add(
                         telebot.types.InlineKeyboardButton("Оплатил", url=f"t.me/{MANAGER_USERNAME}")))

    admin_text = f"ЗАПРОС НА ПОПОЛНЕНИЕ\nПользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\nСумма: {amount}₽"
    bot.send_message(OWNER_ID, admin_text)

# ====== ТЫ ПРОСТО ОТВЕЧАЕШЬ РЕПЛАЕМ — ВСЁ УХОДИТ КЛИЕНТУ КАК РЕПЛАЙ. БЕЗ ПРОВЕРОК. ======
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    # m.reply_to_message — это сообщение, на которое ответил админ.
    # Нам нужно найти ID чата пользователя и ID сообщения, на которое нужно ответить.
    
    client_chat_id = None
    client_message_id = None
    
    # 1. Попытка получить ID чата пользователя из пересланного сообщения
    if m.reply_to_message.forward_from:
        client_chat_id = m.reply_to_message.forward_from.id
        client_message_id = m.reply_to_message.forward_from_message_id
    elif m.reply_to_message.chat.id != OWNER_ID:
        # 2. Если сообщение не пересылалось и оно пришло от пользователя (не лог от бота)
        client_chat_id = m.reply_to_message.chat.id
        client_message_id = m.reply_to_message.message_id
    
    # 3. Запасной вариант: Ищем ID клиента в тексте реплая (например, в логе "ЗАПРОС НА ПОПОЛНЕНИЕ (ID: ...)")
    if not client_chat_id or client_chat_id == OWNER_ID:
        text = m.reply_to_message.text or ""
        # Ищем ID в формате "ID: 123456789"
        client_id_match = re.search(r'ID: (\d{8,12})', text) 
        if client_id_match:
            client_chat_id = int(client_id_match.group(1))
            # В этом случае message_id неизвестен, реплай не получится
            client_message_id = None
        else:
             bot.reply_to(m, "Не удалось найти ID клиента для ответа.")
             return # Прерываем, так как не знаем, кому отвечать

    try:
        if client_message_id:
            # Отправляем сообщение администратора как реплай
            bot.send_message(
                chat_id=client_chat_id,
                text=m.text, # Используем текст сообщения админа
                reply_to_message_id=client_message_id
            )
        else:
            # Если message_id не найден, просто отправляем сообщение
            bot.send_message(
                chat_id=client_chat_id,
                text=m.text
            )
            
        bot.reply_to(m, f"Отправлено клиенту (ID: {client_chat_id}).")

    except Exception as e:
        bot.reply_to(m, f"Ошибка при отправке: {e}")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

if __name__ == '__main__':
    print("Бот запущен. Для ответов клиентам используй реплай на их сообщения в чате с ботом.")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)
