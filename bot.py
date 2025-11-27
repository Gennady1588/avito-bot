from flask import Flask, request
import telebot
import re
from html import escape

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790  # ← Твой Telegram ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# База в памяти (для теста)
user_balances = {}
user_data = {}

# ========================= НАСТРОЙКИ =========================
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"
MIN_DEPOSIT_AMOUNT = 400

PRICE_50_PF_DAILY = 799
PRICE_AVITO_REVIEW = 350
PRICE_PER_FOLLOWER = 200
MIN_FOLLOWERS_ORDER = 50
MAX_FOLLOWERS_ORDER = 10000

DURATION_DAYS = {'1d':1,'2d':2,'3d':3,'5d':5,'7d':7,'30d':30}
DURATION_NAMES = {'1d':'1 День','2d':'2 Дня','3d':'3 Дня','5d':'5 Дней','7d':'7 Дней','30d':'Месяц'}

# ========================= ВСПОМОГАТЕЛЬНОЕ =========================
def get_user_balance(uid):
    if uid not in user_balances: user_balances[uid] = 0.0
    if uid not in user_data: user_data[uid] = {}
    return round(user_balances[uid], 2)

def safe_delete(cid, mid):
    try: bot.delete_message(cid, mid)
    except: pass

def calc_pf_price(duration, count):
    days = DURATION_DAYS.get(duration, 1)
    daily = PRICE_50_PF_DAILY * 2 if count == '100' else PRICE_50_PF_DAILY
    return int(daily * days)

# ========================= КЛАВИАТУРЫ =========================
def main_menu():
    m = telebot.types.InlineKeyboardMarkup(row_width=1)
    m.add(telebot.types.InlineKeyboardButton("Заказать ПФ", callback_data='order_pf'))
    m.add(telebot.types.InlineKeyboardButton("Добавить отзыв", callback_data='order_review'))
    m.add(telebot.types.InlineKeyboardButton("Подписчики на профиль Авито", callback_data='order_followers'))
    m.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data='my_account'))
    m.add(telebot.types.InlineKeyboardButton("FAQ / Кейсы", callback_data='faq'))
    m.add(telebot.types.InlineKeyboardButton("Промокоды", callback_data='promocodes'))
    m.add(telebot.types.InlineKeyboardButton("Правила", url='https://t.me/Avitounlock/18'))
    m.add(telebot.types.InlineKeyboardButton("Техподдержка", url='https://t.me/Avitounlock'))
    return m

def cancel_btn():
    m = telebot.types.InlineKeyboardMarkup()
    m.add(telebot.types.InlineKeyboardButton("Отмена", callback_data='cancel'))
    return m

# ========================= СТАРТ =========================
@bot.message_handler(commands=['start'])
def start(m):
    bot.clear_step_handler_by_chat_id(m.chat.id)
    bot.send_message(m.chat.id,
        "Avito ПФ Услуги 2025\n\n"
        "Выберите услугу:",
        reply_markup=main_menu())

# ========================= ПОДПИСЧИКИ =========================
def followers_start(msg):
    safe_delete(msg.chat.id, msg.message_id)
    txt = f"Подписчики на профиль Авито\n\nЦена: *{PRICE_PER_FOLLOWER}₽ за 1*\nМинимум {MIN_FOLLOWERS_ORDER}, максимум {MAX_FOLLOWERS_ORDER}\n\nВведите количество:"
    s = bot.send_message(msg.chat.id, txt, parse_mode='Markdown', reply_markup=cancel_btn())
    bot.register_next_step_handler(s, followers_qty, s.message_id)

def followers_qty(m, pid):
    if m.text and m.text.lower() in ['отмена','назад','/start']:
        safe_delete(m.chat.id, m.message_id); safe_delete(m.chat.id, pid); start(m); return
    try:
        qty = int(m.text)
        if not MIN_FOLLOWERS_ORDER <= qty <= MAX_FOLLOWERS_ORDER: raise
    except:
        bot.edit_message_text("Введите число от 50 до 10000", m.chat.id, pid, reply_markup=cancel_btn())
        bot.register_next_step_handler(m, followers_qty, pid); return

    price = qty * PRICE_PER_FOLLOWER
    if get_user_balance(m.chat.id) < price:
        bot.send_message(m.chat.id, f"Недостаточно средств\nНужно: {price}₽\nУ вас: {get_user_balance(m.chat.id)}₽")
        return

    user_data[m.chat.id]['f_qty'] = qty
    user_data[m.chat.id]['f_price'] = price
    safe_delete(m.chat.id, pid); safe_delete(m.chat.id, m.message_id)
    s = bot.send_message(m.chat.id, f"Заказ: *{qty}* подписчиков → *{price}₽*\n\nОтправьте ссылку на профиль Авито:", parse_mode='Markdown', reply_markup=cancel_btn())
    bot.register_next_step_handler(s, followers_link, s.message_id)

def followers_link(m, pid):
    qty = user_data[m.chat.id]['f_qty']
    price = user_data[m.chat.id]['f_price']
    link = m.text.strip()

    user_balances[m.chat.id] -= price

    admin_msg = (
        "НОВЫЙ ЗАКАЗ — ПОДПИСЧИКИ\n\n"
        f"Пользователь: @{m.from_user.username or 'нет'} (ID: `{m.chat.id}`)\n"
        f"Количество: *{qty}*\n"
        f"Сумма: *{price}₽* (списано)\n"
        f"Ссылка: {link}\n\n"
        "Ответьте реплаем"
    )
    bot.send_message(OWNER_ID, admin_msg, parse_mode='Markdown')

    bot.send_message(m.chat.id,
        f"Заказ принят!\n*{qty}* подписчиков → *{price}₽*\nОстаток: *{get_user_balance(m.chat.id)}₽*",
        parse_mode='Markdown', reply_markup=main_menu())

    safe_delete(m.chat.id, m.message_id); safe_delete(m.chat.id, pid)
    user_data[m.chat.id].pop('f_qty', None); user_data[m.chat.id].pop('f_price', None)

# ========================= УМНЫЙ ОТВЕТ АДМИНА (ГЛАВНОЕ ИСПРАВЛЕНИЕ) =========================
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    try:
        orig_text = (m.reply_to_message.text or m.reply_to_message.caption or "")

        # СУПЕР-ПАРСЕР ID — ловит всё!
        client_id = None
        for pattern in [
            r'ID[:\s]*[`\'"]?(\d{7,12})[`\'"]?',
            r'\(ID[:\s]*[`\'"]?(\d{7,12})[`\'"]?\)',
            r'ID[:\s]*(\d{7,12})',
            r'пользователь.*?(\d{7,12})',
            r'(\d{9,12})'
        ]:
            match = re.search(pattern, orig_text)
            if match:
                client_id = int(match.group(1))
                break

        if not client_id:
            bot.reply_to(m, "ID клиента не найден!\nОтветьте на сообщение, где есть ID пользователя.")
            return

        # === /add_balance ===
        if m.text and m.text.strip().lower().startswith('/add_balance'):
            parts = m.text.strip().split()
            if len(parts) == 1:
                bot.reply_to(m, f"Напишите сумму, например:\n`/add_balance 500`", parse_mode='Markdown')
                return
            try:
                amount = float(parts[1])
                if amount <= 0: raise
                user_balances[client_id] = get_user_balance(client_id) + amount
                bot.send_message(client_id, f"Баланс пополнен на *{amount}₽*\nТеперь: *{get_user_balance(client_id)}₽*", parse_mode='Markdown')
                bot.reply_to(m, f"Зачислено +{amount}₽\nБаланс клиента: {get_user_balance(client_id)}₽")
                return
            except:
                bot.reply_to(m, "Неверная сумма. Пример: `/add_balance 500`", parse_mode='Markdown')
                return

        # === ОБЫЧНЫЙ ОТВЕТ ===
        sent = False
        if m.text:
            bot.send_message(client_id, f"*Ответ менеджера:*\n\n{escape(m.text)}", parse_mode='Markdown')
            sent = True
        elif m.photo:
            bot.send_photo(client_id, m.photo[-1].file_id, caption=f"*Ответ менеджера:*\n\n{escape(m.caption or '')}", parse_mode='Markdown')
            sent = True
        elif m.video:
            bot.send_video(client_id, m.video.file_id, caption=f"*Ответ менеджера:*\n\n{escape(m.caption or '')}", parse_mode='Markdown')
            sent = True
        elif m.document:
            bot.send_document(client_id, m.document.file_id, caption=f"*Ответ менеджера:*\n\n{escape(m.caption or '')}", parse_mode='Markdown')
            sent = True
        elif m.voice:
            bot.send_voice(client_id, m.voice.file_id)
            if m.caption:
                bot.send_message(client_id, f"*Ответ менеджера:*\n\n{escape(m.caption)}", parse_mode='Markdown')
            sent = True
        elif m.sticker:
            bot.send_sticker(client_id, m.sticker.file_id)
            sent = True

        if sent:
            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"t.me/{bot.get_me().username}?start={client_id}"))
            bot.reply_to(m, f"Отправлено клиенту {client_id}", reply_markup=kb)
        else:
            bot.reply_to(m, "Тип сообщения не поддерживается")

    except Exception as e:
        bot.reply_to(m, f"Ошибка: {e}")

# ========================= КОЛБЭКИ =========================
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    cid = c.message.chat.id
    bot.answer_callback_query(c.id)

    if c.data == 'order_followers':
        followers_start(c.message)
    elif c.data == 'cancel':
        try:
            bot.edit_message_text("Отменено", cid, c.message.message_id, reply_markup=main_menu())
        except:
            bot.send_message(cid, "Отменено", reply_markup=main_menu())

# ========================= ВЕБХУК =========================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

# ========================= ЗАПУСК =========================
if __name__ == '__main__':
    print("Бот запущен!")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True, interval=0)