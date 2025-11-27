from flask import Flask, request
import telebot
import re
import time

TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Используйте базу данных (например, SQLite), а не словарь, для реального проекта!
user_balances = {} 
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"

def get_balance(uid):
    return user_balances.get(uid, 0)

def main_menu():
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account"))
    return k

# ----------------- ОБРАБОТЧИКИ КЛИЕНТА -----------------

@bot.message_handler(commands=['start'])
def start(m):
    bot.send_message(m.chat.id, "Avito ПФ Услуги 2025", reply_markup=main_menu())

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

    # Лог для администратора
    admin_text = f"💰 ЗАПРОС НА ПОПОЛНЕНИЕ 💰\n\nПользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\nЖелаемая сумма: {amount} ₽\nКарта для проверки: {YOUR_CARD_NUMBER}\n\n➡️ Необходимо проверить поступление: {amount} ₽\nОтветьте реплаем, чтобы подтвердить получение средств. Для зачисления используйте /add_balance {amount}"
    bot.send_message(OWNER_ID, admin_text)

# ----------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ АДМИНИСТРАТОРА -----------------

def find_client_id(message):
    """Находит ID клиента из текста лога, даже если отвечают на реплай."""
    text = message.text or ""
    
    # 1. Поиск в тексте текущего сообщения
    client_id_match = re.search(r'\(ID:\s*(\d{8,12})\)', text)
    
    # 2. Если не найден, поиск в цитируемом сообщении
    if not client_id_match and message.reply_to_message:
         original_log_text = message.reply_to_message.text or ""
         client_id_match = re.search(r'\(ID:\s*(\d{8,12})\)', original_log_text)
         
    return client_id_match

# ----------------- ОБРАБОТЧИКИ АДМИНИСТРАТОРА -----------------

# 1. ОБРАБОТЧИК ДЛЯ НАЧИСЛЕНИЯ БАЛАНСА (через команду)
@bot.message_handler(commands=['add_balance'], func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def add_balance_command(m):
    try:
        amount = int(m.text.split()[1])
    except:
        return bot.reply_to(m, "❌ ОШИБКА: Используйте формат /add_balance {сумма}")

    client_id_match = find_client_id(m.reply_to_message)
    
    if client_id_match:
        client_chat_id = int(client_id_match.group(1))
        
        # Начисление баланса
        user_balances[client_chat_id] = user_balances.get(client_chat_id, 0) + amount
        
        # Отправка подтверждения администратору
        bot.reply_to(m, f"✅ Баланс клиента (ID: {client_chat_id}) пополнен на {amount} ₽.")
        
        # Отправка уведомления клиенту
        try:
            bot.send_message(
                chat_id=client_chat_id,
                text=f"✅ Баланс пополнен на **{amount} ₽**. Ваш текущий баланс: **{user_balances[client_chat_id]} ₽**.",
                parse_mode='Markdown'
            )
        except Exception as e:
            bot.reply_to(m, f"⚠️ Баланс начислен, но не удалось уведомить клиента (ID: {client_chat_id}). Детали: {e}")
            
    else:
        bot.reply_to(m, "❌ ID клиента не найден в сообщении, на которое вы отвечаете. Начисление отменено.")

# 2. ОБРАБОТЧИК ДЛЯ ПРОСТОГО ТЕКСТОВОГО ОТВЕТА (без ID и команд)
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    
    client_chat_id = None
    client_message_id = None
    reply_to = m.reply_to_message
    
    # Находим ID клиента, используя новую надежную функцию
    client_id_match = find_client_id(reply_to)
    
    if reply_to.forward_from:
        client_chat_id = reply_to.forward_from.id
        client_message_id = reply_to.forward_from_message_id
        
    elif reply_to.chat.id != OWNER_ID:
        client_chat_id = reply_to.chat.id
        client_message_id = reply_to.message_id
        
    elif client_id_match: # Используем ID, найденный в логе
        client_chat_id = int(client_id_match.group(1))
        # client_message_id остается None, если отвечаем на лог, и сообщение не будет реплаем
    
    if not client_chat_id:
         # Это будет видно, только если не сработал ни один из методов поиска
         bot.reply_to(m, "❌ КРИТИЧЕСКАЯ ОШИБКА: ID клиента не найден. Пожалуйста, ответьте на **самый первый лог-запрос**.")
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
    return '', 403

# ====== БЛОК ЗАПУСКА Long Polling (для локальной машины) ======
if __name__ == '__main__':
    print("🤖 Бот запущен в режиме Long Polling. Отвечай реплаем на сообщения!")
    try:
        bot.remove_webhook()
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {e}")
