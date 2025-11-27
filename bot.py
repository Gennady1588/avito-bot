from flask import Flask, request
import telebot
import re
import time

TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790 # ID Геннадия
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

    # ОТПРАВЛЯЕМ ЕДИНЫЙ ЛОГ-ТЕКСТ
    admin_text = f"💰 ЗАПРОС НА ПОПОЛНЕНИЕ 💰\n\nПользователь: @{m.from_user.username or 'нет'} (ID: {m.chat.id})\nЖелаемая сумма: {amount} ₽\nКарта для проверки: {YOUR_CARD_NUMBER}\n\n➡️ Необходимо проверить поступление: {amount} ₽\nОтветьте реплаем, чтобы подтвердить получение средств. Для зачисления используйте /add_balance {amount}"
    
    bot.send_message(OWNER_ID, admin_text)

# ----------------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ АДМИНИСТРАТОРА -----------------

def extract_client_id_from_text(text):
    """
    Находит ID клиента в тексте сообщения, используя регулярное выражение.
    """
    if not text:
        return None
    # Ищем ID в формате (ID: [цифры])
    match = re.search(r'\(ID:\s*(\d{8,12})\)', text) 
    if match:
        return int(match.group(1))
    return None

# ----------------- ОБРАБОТЧИК АДМИНИСТРАТОРА (УНИФИЦИРОВАННЫЙ) -----------------

@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_action_handler(m):
    
    replied_message_text = m.reply_to_message.text
    client_chat_id = extract_client_id_from_text(replied_message_text)
    
    if not client_chat_id:
        # Это старая ошибка, но теперь она должна срабатывать только если ID действительно нет
        return bot.reply_to(m, "❌ КРИТИЧЕСКАЯ ОШИБКА: ID клиента не найден. Убедитесь, что отвечаете реплаем на лог-сообщение, где четко указано (ID: 123456789).")


    # --- ЛОГИКА ДЛЯ /add_balance ---
    if m.text and m.text.lower().startswith('/add_balance'):
        
        # 1. Извлекаем сумму, удаляя все лишнее (скобки, пробелы)
        try:
            amount_str = re.sub(r'[{} ]', '', m.text.lower().replace('/add_balance', '', 1).strip())
            amount = int(amount_str)
        except:
            return bot.reply_to(m, "❌ ОШИБКА ФОРМАТА: Используйте /add_balance 400 (только цифры). Начисление отменено.")

        # 2. Начисление баланса
        user_balances[client_chat_id] = user_balances.get(client_chat_id, 0) + amount
        
        # 3. Отправка подтверждения администратору
        bot.reply_to(m, f"✅ Баланс клиента (ID: {client_chat_id}) пополнен на {amount} ₽. Текущий баланс: {user_balances[client_chat_id]} ₽.")
        
        # 4. Отправка уведомления клиенту
        try:
            bot.send_message(
                chat_id=client_chat_id,
                text=f"✅ Баланс пополнен на **{amount} ₽**. Ваш текущий баланс: **{user_balances[client_chat_id]} ₽**.",
                parse_mode='Markdown'
            )
        except Exception as e:
            bot.reply_to(m, f"⚠️ Баланс начислен, но не удалось уведомить клиента (ID: {client_chat_id}). Детали: {e}")
            
    # --- ЛОГИКА ДЛЯ ОБЫЧНОГО ОТВЕТА (ЛЮБОЙ ТЕКСТ) ---
    else:
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
