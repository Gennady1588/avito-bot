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

    admin_text = f"💰 ЗАПРОС НА ПОПОЛНЕНИЕ 💰\n\nПользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\nЖелаемая сумма: {amount} ₽\nКарта для проверки: {YOUR_CARD_NUMBER}\n\n➡️ Необходимо проверить поступление: {amount} ₽\nОтветьте реплаем, чтобы подтвердить получение средств. Для зачисления используйте /add_balance {amount}"
    bot.send_message(OWNER_ID, admin_text)

# ====== ИСПРАВЛЕННАЯ ФУНКЦИЯ ОТВЕТА АДМИНИСТРАТОРА (РАБОТАЕТ ЧЕРЕЗ РЕПЛАЙ) ======
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    
    client_chat_id = None
    client_message_id = None
    reply_to = m.reply_to_message
    
    # 1. Приоритет: Если админ отвечает на ПЕРЕСЛАННОЕ сообщение
    if reply_to.forward_from:
        client_chat_id = reply_to.forward_from.id
        client_message_id = reply_to.forward_from_message_id
        
    # 2. Если сообщение не пересылалось и оно пришло от пользователя
    elif reply_to.chat.id != OWNER_ID:
        client_chat_id = reply_to.chat.id
        client_message_id = reply_to.message_id
        
    # 3. Запасной вариант: Ищем ID клиента в тексте лога (ID: 7579757892)
    if not client_chat_id or client_chat_id == OWNER_ID:
        text = reply_to.text or ""
        # Точный поиск ID в формате (ID: [цифры])
        client_id_match = re.search(r'\(ID:\s*(\d{8,12})\)', text)
        if client_id_match:
            client_chat_id = int(client_id_match.group(1))
            client_message_id = None 
        else:
             bot.reply_to(m, "❌ ОШИБКА: ID клиента не найден в тексте реплая! Убедитесь, что ID указан в формате (ID: 123456789).")
             return

    try:
        # Отправляем сообщение администратора
        bot.send_message(
            chat_id=client_chat_id,
            text=m.text,
            reply_to_message_id=client_message_id 
        )
        bot.reply_to(m, f"✅ Отправлено клиенту (ID: {client_chat_id}).")

    except Exception as e:
        bot.reply_to(m, f"⚠️ Ошибка при отправке. Возможно, клиент заблокировал бота. Детали: {e}")

# --- Webhook логика (оставлена, но не используется) ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

# ====== БЛОК ЗАПУСКА Long Polling (для локальной машины) ======
if __name__ == '__main__':
    print("🤖 Бот запущен в режиме Long Polling. Отвечай реплаем на сообщения!")
    try:
        # bot.remove_webhook() гарантирует, что Webhook отключен
        bot.remove_webhook()
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {e}")
