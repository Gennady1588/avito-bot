from flask import Flask, request
import telebot
import re
import logging

logging.basicConfig(level=logging.INFO)

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

user_balances = {}
user_data = {}

# ========================= НАСТРОЙКИ =========================
MIN_DEPOSIT_AMOUNT = 400
PRICE_50_PF_DAILY = 799
PRICE_AVITO_REVIEW = 350
PRICE_PER_FOLLOWER = 200
MIN_FOLLOWERS = 50
MAX_FOLLOWERS = 10000

DURATION_DAYS = {'1d':1, '2d':2, '3d':3, '5d':5, '7d':7, '30d':30}
DURATION_NAMES = {'1d':'1 День', '2d':'2 Дня', '3d':'3 Дня', '5d':'5 Дней', '7d':'7 Дней', '30d':'Месяц'}

MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"

# ========================= ВСПОМОГАТЕЛЬНЫЕ =========================
def get_user_balance(uid):
    if uid not in user_balances: user_balances[uid] = 0.0
    if uid not in user_data: user_data[uid] = {}
    return round(user_balances[uid], 2)

def safe_delete(cid, mid):
    try:
        bot.delete_message(cid, mid)
    except:
        pass

# ========================= КЛАВИАТУРЫ =========================
def main_menu():
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    m.add(telebot.types.InlineKeyboardButton("🚀 Заказать ПФ", callback_data='order_pf'))
    m.add(telebot.types.InlineKeyboardButton("⭐ Добавить отзыв", callback_data='order_review'))
    m.add(telebot.types.InlineKeyboardButton("👥 Подписчики на профиль", callback_data='order_followers'))
    m.add(telebot.types.InlineKeyboardButton("🚪 Личный кабинет", callback_data='my_account'))
    m.add(telebot.types.InlineKeyboardButton("💬 FAQ", callback_data='faq'))
    m.add(telebot.types.InlineKeyboardButton("🎁 Промокоды", callback_data='promocodes'))
    m.add(telebot.types.InlineKeyboardButton("📗 Правила", url='https://t.me/Avitounlock/18'))
    m.add(telebot.types.InlineKeyboardButton("🧑‍💻 Поддержка", url='https://t.me/Avitounlock'))
    return m

def cancel_markup():
    m = telebot.types.InlineKeyboardMarkup()
    m.add(telebot.types.InlineKeyboardButton("🔙 Отмена", callback_data='back_main'))
    return m

# ========================= СТАРТ =========================
@bot.message_handler(commands=['start'])
def start(m):
    print(f"START from {m.chat.id}")  # Для логов
    bot.clear_step_handler_by_chat_id(m.chat.id)
    text = "📈 *Avito ПФ бот*\n\n🚀 Выберите услугу:"
    bot.send_message(m.chat.id, text, reply_markup=main_menu(), parse_mode='Markdown')

# ========================= ПОПОЛНЕНИЕ =========================
def deposit_request(m):
    safe_delete(m.chat.id, m.message_id)
    text = f"💳 *Пополнение*\n\nМин. {MIN_DEPOSIT_AMOUNT}₽\n\nВведите сумму:"
    s = bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=cancel_markup())
    bot.register_next_step_handler(s, deposit_process, s.message_id)

def deposit_process(m, pid):
    if m.text.lower() in ['отмена', '/start']:
        safe_delete(m.chat.id, m.message_id)
        safe_delete(m.chat.id, pid)
        start(m)
        return
    try:
        amount = int(re.sub(r'[^\d]', '', m.text))
        if amount < MIN_DEPOSIT_AMOUNT:
            raise ValueError
    except:
        bot.edit_message_text(f"Ошибка! Мин. {MIN_DEPOSIT_AMOUNT}₽ (только цифры)", m.chat.id, pid, reply_markup=cancel_markup())
        bot.register_next_step_handler(m, deposit_process, pid)
        return

    safe_delete(m.chat.id, pid)
    safe_delete(m.chat.id, m.message_id)

    text = f"✅ Запрос на {amount}₽\n\nПереведите на карту: `{YOUR_CARD_NUMBER}`\n\nСвяжитесь с @{MANAGER_USERNAME}"
    kb = telebot.types.InlineKeyboardMarkup()
    kb.add(telebot.types.InlineKeyboardButton("Менеджер", url=f"https://t.me/{MANAGER_USERNAME}"))
    bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=kb)

    # Админу
    admin_text = f"💰 ПОПОЛНЕНИЕ\n\n@{m.from_user.username or 'нет'} (ID: `{m.chat.id}`)\nСумма: *{amount}₽*\nКарта: `{YOUR_CARD_NUMBER}`\n\n/add_balance {amount}"
    bot.send_message(OWNER_ID, admin_text, parse_mode='Markdown')

# ========================= ПОДПИСЧИКИ =========================
def followers_request(m):
    safe_delete(m.chat.id, m.message_id)
    text = f"👥 *Подписчики*\n\n{PRICE_PER_FOLLOWER}₽/шт\nМин {MIN_FOLLOWERS}, макс {MAX_FOLLOWERS}\n\nКоличество:"
    s = bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=cancel_markup())
    bot.register_next_step_handler(s, followers_qty, s.message_id)

def followers_qty(m, pid):
    if m.text.lower() in ['отмена', '/start']:
        safe_delete(m.chat.id, m.message_id)
        safe_delete(m.chat.id, pid)
        start(m)
        return
    try:
        qty = int(re.sub(r'[^\d]', '', m.text))
        if not MIN_FOLLOWERS <= qty <= MAX_FOLLOWERS:
            raise ValueError
    except:
        bot.edit_message_text("Число от 50 до 10000", m.chat.id, pid, reply_markup=cancel_markup())
        bot.register_next_step_handler(m, followers_qty, pid)
        return

    price = qty * PRICE_PER_FOLLOWER
    if get_user_balance(m.chat.id) < price:
        bot.send_message(m.chat.id, f"Недостаточно! Нужно {price}₽, у вас {get_user_balance(m.chat.id)}₽")
        return

    user_data[m.chat.id]['f_qty'] = qty
    user_data[m.chat.id]['f_price'] = price
    safe_delete(m.chat.id, pid)
    safe_delete(m.chat.id, m.message_id)
    text = f"*{qty}* подписчиков = *{price}₽*\n\nСсылка на профиль:"
    s = bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=cancel_markup())
    bot.register_next_step_handler(s, followers_link, s.message_id)

def followers_link(m, pid):
    qty = user_data[m.chat.id]['f_qty']
    price = user_data[m.chat.id]['f_price']
    link = m.text.strip()

    user_balances[m.chat.id] -= price

    admin_text = f"👥 ЗАКАЗ ПОДПИСЧИКОВ\n\n@{m.from_user.username or 'нет'} (ID: `{m.chat.id}`)\nКол-во: *{qty}*\nСумма: *{price}₽*\nСсылка: {link}"
    bot.send_message(OWNER_ID, admin_text, parse_mode='Markdown')

    bot.send_message(m.chat.id, f"✅ Заказ принят!\n{qty} под. за {price}₽\nБаланс: {get_user_balance(m.chat.id)}₽", parse_mode='Markdown', reply_markup=main_menu())

    safe_delete(m.chat.id, m.message_id)
    safe_delete(m.chat.id, pid)
    user_data[m.chat.id].clear()

# ========================= КОЛБЭКИ =========================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    bot.answer_callback_query(c.id)
    cid = c.message.chat.id
    print(f"Callback: {c.data} from {cid}")  # Логи

    if c.data == 'order_followers':
        followers_request(c.message)
    elif c.data == 'back_main':
        bot.edit_message_text("Главное меню", cid, c.message.message_id, reply_markup=main_menu())
    # Добавь другие колбэки (ПФ, отзывы) по аналогии

# ========================= АДМИН ОТВЕТ =========================
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    orig = m.reply_to_message.text or ""
    # Парсер ID
    cid_match = re.search(r'ID[:\s]*[`\'"]?(\d+)', orig)
    if not cid_match:
        bot.reply_to(m, "ID не найден! Проверьте реплай.")
        return
    client_id = int(cid_match.group(1))

    if m.text.startswith('/add_balance'):
        try:
            amount = float(m.text.split()[1])
            user_balances[client_id] += amount
            bot.send_message(client_id, f"✅ +{amount}₽\nБаланс: {get_user_balance(client_id)}₽", parse_mode='Markdown')
            bot.reply_to(m, f"Зачислено! Новый баланс: {get_user_balance(client_id)}₽")
        except:
            bot.reply_to(m, "Формат: /add_balance 400")
        return

    # Обычный ответ
    bot.send_message(client_id, f"Ответ менеджера:\n\n{m.text}")
    bot.reply_to(m, f"Отправлено {client_id}")

# ========================= WEBHOOK =========================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return 'No', 403

if __name__ == '__main__':
    print("🚀 Бот стартует...")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)
    print("Бот работает!")