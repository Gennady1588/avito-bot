from flask import Flask, request
import telebot
import re
import time

# --- ВАШИ ДАННЫЕ ---
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790 # ID Геннадия
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__) 

# 💡 ХРАНЕНИЕ БАЛАНСА: Используем словарь для хранения данных клиентов
user_balances = {} 
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"

def get_balance(uid):
    """Функция для получения баланса клиента. Если баланса нет, возвращает 0."""
    return user_balances.get(uid, 0)

# ----------------- КНОПКИ КЛИЕНТА (ТОЛЬКО INLINE) -----------------

def main_menu():
    k = telebot.types.InlineKeyboardMarkup()
    k.add(
        telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account")
    )
    return k

# ----------------- ОБРАБОТЧИКИ КЛИЕНТА -----------------

@bot.message_handler(commands=['start'])
def start(m):
    # Начальное меню с Inline-кнопками
    bot.send_message(m.chat.id, "Добро пожаловать в Avito ПФ Услуги 2025!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "account")
def acc(c):
    # 💡 ОТОБРАЖЕНИЕ БАЛАНСА: Получаем текущий баланс и показываем его
    current_balance = get_balance(c.from_user.id)
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Пополнить", callback_data="deposit"))
    bot.edit_message_text(f"Баланс: *{current_balance}₽*", c.message.chat.id, c.message.message_id, parse_mode='Markdown', reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def dep(c):
    msg = bot.send_message(c.message.chat.id, "Сколько пополнить? (мин. 400₽)", reply_markup=telebot.types.ForceReply())
    bot.register_next_step_handler(msg, proc_dep)

def proc_dep(m):
    try:
        amount = int(''.join(filter(str.isdigit, m.text)))
        if amount < 400: raise
    except:
        return bot.send_message(m.chat.id, "Минимум 400₽", reply_markup=main_menu())

    bot.send_message(m.chat.id, f"Переведи *{amount}₽* на `{YOUR_CARD_NUMBER}`", parse_mode='Markdown',
                     reply_markup=telebot.types.InlineKeyboardMarkup().add(
                         telebot.types.InlineKeyboardButton("Оплатил", url=f"t.me/{MANAGER_USERNAME}")))

    # ЛОГ ДЛЯ АДМИНА: Указываем команду для начисления (без реплая)
    admin_text = f"💰 ЗАПРОС НА ПОПОЛНЕНИЕ 💰\n\nПользователь: @{m.from_user.username or 'нет'} ID: {m.chat.id}\nЖелаемая сумма: {amount} ₽\nКарта для проверки: {YOUR_CARD_NUMBER}\n\n➡️ Начислить: /add {m.chat.id} {amount}"
    
    bot.send_message(OWNER_ID, admin_text)

# ----------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (для поиска ID) -----------------

def extract_client_id_from_text(text):
    """ Агрессивный поиск ID клиента в тексте сообщения """
    if not text:
        return None
    match = re.search(r'ID:\s*(\d{8,12})', text) 
    if match:
        return int(match.group(1))
    return None

# ----------------- ОБРАБОТЧИК АДМИНИСТРАТОРА: НАЧИСЛЕНИЕ (ЧЕРЕЗ КОМАНДУ) -----------------

@bot.message_handler(commands=['add'], func=lambda m: m.chat.id == OWNER_ID)
def add_balance_direct(m):
    
    parts = m.text.split()
    if len(parts) != 3:
        return bot.reply_to(m, "❌ ОШИБКА: Используйте формат /add {ID_клиента} {сумма}, например: /add 7579757892 400")

    try:
        client_chat_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        return bot.reply_to(m, "❌ ID клиента и сумма должны быть числами.")

    # 💡 ОБНОВЛЕНИЕ БАЛАНСА: Начисляем средства
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
            

# ----------------- ОБРАБОТЧИК АДМИНИСТРАТОРА: ОТВЕТ НА СООБЩЕНИЕ (ЧЕРЕЗ РЕПЛАЙ) -----------------

@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply_simple(m):
    
    replied_message_text = m.reply_to_message.text or ""
    client_chat_id = extract_client_id_from_text(replied_message_text)

    # 🤫 Молчаливый выход, если ID не найден в реплае (чтобы не спамить ошибкой)
    if not client_chat_id:
        return 

    try:
        # Отправляем сообщение администратора
        bot.send_message(
            chat_id=client_chat_id,
            text=m.text 
        )
        bot.reply_to(m, f"✅ Сообщение '{m.text}' отправлено клиенту (ID: {client_chat_id}).")

    except Exception as e:
        bot.reply_to(m, f"⚠️ Ошибка при отправке. Возможно, клиент заблокировал бота. Детали: {e}")


# ----------------- ЗАПУСК БОТА -----------------
if __name__ == '__main__':
    print("🤖 Бот запущен в режиме Long Polling. Отвечай реплаем на сообщения!")
    try:
        # Удаляем лишние команды, если они остались
        bot.set_my_commands([])
        bot.remove_webhook()
        bot.infinity_polling(none_stop=True)
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {e}")
