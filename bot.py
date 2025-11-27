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

    # ЛОГ: УКАЗЫВАЕМ НОВУЮ КОМАНДУ ДЛЯ АДМИНА
    admin_text = f"💰 ЗАПРОС НА ПОПОЛНЕНИЕ 💰\n\nПользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\nЖелаемая сумма: {amount} ₽\nКарта для проверки: {YOUR_CARD_NUMBER}\n\n➡️ Начислить: /add {m.chat.id} {amount}"
    
    bot.send_message(OWNER_ID, admin_text)

# ----------------- ОБРАБОТЧИКИ АДМИНИСТРАТОРА -----------------

# 🔥 НОВЫЙ ОБРАБОТЧИК: НАЧИСЛЕНИЕ БАЛАНСА ЧЕРЕЗ ПРЯМУЮ КОМАНДУ
@bot.message_handler(commands=['add'], func=lambda m: m.chat.id == OWNER_ID)
def add_balance_direct(m):
    
    parts = m.text.split()
    if len(parts) != 3:
        return bot.reply_to(m, "❌ ОШИБКА: Используйте формат /add {ID_клиента} {сумма}, например: /add 7579757892 400")

    try:
        client_chat_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        return bot.reply_to(m, "❌ ОШИБКА: ID клиента и сумма должны быть числами.")

    # Начисление баланса
    user_balances[client_chat_id] = user_balances.get(client_chat_id, 0) + amount
    
    # Отправка подтверждения администратору
    bot.reply_to(m, f"✅ Баланс клиента (ID: {client_chat_id}) пополнен на {amount} ₽. Текущий баланс: {user_balances[client_chat_id]} ₽.")
    
    # Отправка уведомления клиенту
    try:
        bot.send_message(
            chat_id=client_chat_id,
            text=f"✅ Баланс пополнен на **{amount} ₽**. Ваш текущий баланс: **{user_balances[client_chat_id]} ₽**.",
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.reply_to(m, f"⚠️ Баланс начислен, но не удалось уведомить клиента (ID: {client_chat_id}). Детали: {e}")
            

# ----------------- ОБРАБОТЧИК ДЛЯ ОТВЕТА (ПЕРЕПИСКА) -----------------
# Этот обработчик должен срабатывать, только если это ответ на ЧТО-ТО, что не является командой /add
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply_simple(m):
    
    replied_message_text = m.reply_to_message.text
    # Используем старую логику, но теперь она вспомогательная и не для начисления
    client_chat_id = None
    client_id_match = re.search(r'\(ID:\s*(\d{8,12})\)', replied_message_text)
    if client_id_match:
        client_chat_id = int(client_id_match.group(1))

    if not client_chat_id:
        return bot.reply_to(m, "❌ ID клиента для пересылки ответа не найден. Ответьте на лог-сообщение.")

    try:
        # Отправляем сообщение администратора
        bot.send_message(
            chat_id=client_chat_id,
            text=m.text 
        )
        bot.reply_to(m, f"✅ Сообщение '{m.text}' отправлено клиенту (ID: {client_chat_id}).")

    except Exception as e:
        bot.reply_to(m, f"⚠️ Ошибка при отправке. Возможно, клиент заблокировал бота. Детали: {e}")


# --- Webhook логика ---
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
