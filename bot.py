from flask import Flask, request
import telebot
import re
import time

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

# ----------------- ОБРАБОТЧИКИ КЛИЕНТА -----------------
# (Без изменений)

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

    # 🔥 ИЗМЕНЕНИЕ: ОТПРАВКА ЛОГА ИЗМЕНЕНА НА ПЕРЕСЫЛКУ
    admin_text = f"💰 ЗАПРОС НА ПОПОЛНЕНИЕ 💰\n\nЖелаемая сумма: {amount} ₽\nКарта для проверки: {YOUR_CARD_NUMBER}\n\n➡️ Ответьте реплаем на **пересланное** сообщение клиента, чтобы отправить ему ответ. Используйте /add_balance {amount} для начисления."
    
    # 1. Отправляем лог-текст
    bot.send_message(OWNER_ID, admin_text)
    
    # 2. Пересылаем сообщение клиента, на которое админ будет отвечать
    bot.forward_message(OWNER_ID, m.chat.id, m.message_id) 
    
    # Чтобы избежать путаницы, мы теперь отвечаем реплаем на ПЕРЕСЛАННОЕ сообщение клиента.


# ----------------- ОБРАБОТЧИК АДМИНИСТРАТОРА (НАДЕЖНАЯ ПЕРЕСЫЛКА) -----------------

@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    
    reply_to = m.reply_to_message
    
    # 🔥 Главная проверка: Ищем ID в объекте 'forward_from'
    if reply_to.forward_from:
        client_chat_id = reply_to.forward_from.id
        client_message_id = reply_to.forward_from_message_id
    
    # Если это не пересланное сообщение, а просто сообщение от клиента (например, если админ отвечает не на лог)
    elif reply_to.chat.id != OWNER_ID:
        client_chat_id = reply_to.chat.id
        client_message_id = reply_to.message_id
    
    else:
        # Если ни одно из условий не сработало, значит, вы отвечаете на лог-текст, 
        # который не содержит ID в виде forward_from. 
        return bot.reply_to(m, "❌ ОШИБКА: Отвечайте реплаем только на **пересланное сообщение клиента** (где написано 'Переслано от...').")
        
    # --- Если ID найден, отправляем обычное сообщение ---
    
    # 1. Если это команда /add_balance, передаем ее в отдельный обработчик
    if m.text.startswith('/add_balance'):
        # Имитируем вызов команды, если нужно
        add_balance_command(m)
        return
        
    try:
        # Отправляем обычное сообщение администратора
        bot.send_message(
            chat_id=client_chat_id,
            text=m.text,
            reply_to_message_id=client_message_id 
        )
        bot.reply_to(m, f"✅ Сообщение '{m.text}' отправлено клиенту (ID: {client_chat_id}).")

    except Exception as e:
        bot.reply_to(m, f"⚠️ Ошибка при отправке. Возможно, клиент заблокировал бота. Детали: {e}")

# ----------------- ОБРАБОТЧИК ДЛЯ НАЧИСЛЕНИЯ БАЛАНСА (ЧЕРЕЗ КОМАНДУ) -----------------
# (Этот обработчик остается, но теперь он вызывается из admin_reply)
def add_balance_command(m):
    try:
        amount = int(m.text.split()[1])
    except:
        return bot.reply_to(m, "❌ ОШИБКА: Используйте формат /add_balance 400")

    client_id_match = m.reply_to_message.forward_from.id
    
    if client_id_match:
        client_chat_id = client_id_match
        
        # Начисление баланса
        user_balances[client_chat_id] = user_balances.get(client_chat_id, 0) + amount
        
        bot.reply_to(m, f"✅ Баланс клиента (ID: {client_chat_id}) пополнен на {amount} ₽.")
        
        try:
            bot.send_message(
                chat_id=client_chat_id,
                text=f"✅ Баланс пополнен на **{amount} ₽**. Ваш текущий баланс: **{user_balances[client_chat_id]} ₽**.",
                parse_mode='Markdown'
            )
        except Exception as e:
            bot.reply_to(m, f"⚠️ Баланс начислен, но не удалось уведомить клиента (ID: {client_chat_id}). Детали: {e}")
            
    else:
        bot.reply_to(m, "❌ ID клиента не найден. Убедитесь, что отвечаете на пересланное сообщение.")


# --- Webhook логика ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    return '', 403

# ====== БЛОК ЗАПУСКА Long Polling ======
if __name__ == '__main__':
    print("🤖 Бот запущен в режиме Long Polling. Отвечай реплаем на сообщения!")
    try:
        bot.remove_webhook()
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {e}")
