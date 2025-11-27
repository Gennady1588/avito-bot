from flask import Flask, request
import telebot
import re
from html import escape

# ========================= КОНФИГ =========================
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790  # Твой ID
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# База в памяти
user_balances = {}
user_data = {}

# Настройки
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"
MIN_DEPOSIT = 400

PRICE_REVIEW = 350
PRICE_PER_FOLLOWER = 200
MIN_FOLLOWERS = 50
MAX_FOLLOWERS = 10000

# ПФ
PRICE_50_DAILY = 799
DURATIONS = {'1d':1, '3d':3, '7d':7, '30d':30}
DURATION_NAMES = {'1d':'1 день', '3d':'3 дня', '7d':'7 дней', '30d':'30 дней'}

# ========================= ВСПОМОГАТЕЛЬНОЕ =========================
def get_balance(uid):
    if uid not in user_balances: user_balances[uid] = 0
    if uid not in user_data: user_data[uid] = {}
    return user_balances[uid]

def delete(cid, mid):
    try: bot.delete_message(cid, mid)
    except: pass

# ========================= КЛАВИАТУРЫ =========================
def main_menu():
    k = telebot.types.InlineKeyboardMarkup(row_width=1)
    k.add(telebot.types.InlineKeyboardButton("Заказать ПФ", callback_data="order_pf"))
    k.add(telebot.types.InlineKeyboardButton("Добавить отзыв", callback_data="order_review"))
    k.add(telebot.types.InlineKeyboardButton("Подписчики на профиль", callback_data="order_followers"))
    k.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data="account"))
    k.add(telebot.types.InlineKeyboardButton("FAQ / Кейсы", callback_data="faq"))
    k.add(telebot.types.InlineKeyboardButton("Правила", url="https://t.me/Avitounlock/18"))
    k.add(telebot.types.InlineKeyboardButton("Поддержка", url="https://t.me/Avitounlock"))
    return k

def cancel_btn():
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Отмена", callback_data="cancel"))
    return k

# ========================= СТАРТ =========================
@bot.message_handler(commands=['start'])
def start(m):
    bot.clear_step_handler_by_chat_id(m.chat.id)
    bot.send_message(m.chat.id,
        "Avito ПФ Услуги 2025\n\n"
        "Поднимаем объявления в ТОП с помощью поведенческих факторов\n\n"
        "Выберите услугу:",
        reply_markup=main_menu())

# ========================= ПОПОЛНЕНИЕ =========================
@bot.callback_query_handler(func=lambda c: c.data == "account")
def account(c):
    balance = get_balance(c.message.chat.id)
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Пополнить баланс", callback_data="deposit"))
    k.add(telebot.types.InlineKeyboardButton("Назад", callback_data="cancel"))
    bot.edit_message_text(f"Личный кабинет\n\nБаланс: *{balance}₽*", c.message.chat.id, c.message.message_id,
                          parse_mode='Markdown', reply_markup=k)

@bot.callback_query_handler(func=lambda c: c.data == "deposit")
def deposit_start(c):
    msg = bot.send_message(c.message.chat.id,
        f"Пополнение баланса\n\nМинимальная сумма: *{MIN_DEPOSIT}₽*\n\nВведите сумму:",
        parse_mode='Markdown', reply_markup=cancel_btn())
    bot.register_next_step_handler(msg, deposit_process)

def deposit_process(m):
    if m.text and m.text.lower() in ['отмена', '/start']:
        delete(m.chat.id, m.message_id)
        start(m)
        return
    try:
        amount = int(''.join(filter(str.isdigit, m.text)))
        if amount < MIN_DEPOSIT: raise
    except:
        bot.send_message(m.chat.id, "Введите корректную сумму (минимум 400₽)")
        return

    delete(m.chat.id, m.message_id)

    text = (
        f"Запрос на пополнение: *{amount}₽*\n\n"
        f"Переведите ровно эту сумму на карту:\n`{YOUR_CARD_NUMBER}`\n\n"
        f"После оплаты нажмите кнопку ниже → менеджер проверит"
    )
    k = telebot.types.InlineKeyboardMarkup()
    k.add(telebot.types.InlineKeyboardButton("Связаться с менеджером", url=f"t.me/{MANAGER_USERNAME}"))
    bot.send_message(m.chat.id, text, parse_mode='Markdown', reply_markup=k)

    # Уведомление админу — ID в чистом формате
    admin_text = (
        "ЗАПРОС НА ПОПОЛНЕНИЕ\n\n"
        f"Пользователь: @{m.from_user.username or 'нет'}\n"
        f"ID клиента: {m.chat.id}\n"
        f"Сумма: *{amount}₽*\n"
        f"Карта: `{YOUR_CARD_NUMBER}`\n\n"
        f"Для зачисления: `/add_balance {amount}`"
    )
    bot.send_message(OWNER_ID, admin_text, parse_mode='Markdown')

# ========================= ПОДПИСЧИКИ =========================
@bot.callback_query_handler(func=lambda c: c.data == "order_followers")
def followers_start(c):
    msg = bot.send_message(c.message.chat.id,
        f"Подписчики на профиль Авито\n\n"
        f"Цена: *{PRICE_PER_FOLLOWER}₽ за 1*\n"
        f"Минимум {MIN_FOLLOWERS}, максимум {MAX_FOLLOWERS}\n\n"
        "Введите количество:",
        parse_mode='Markdown', reply_markup=cancel_btn())
    bot.register_next_step_handler(msg, followers_qty)

def followers_qty(m):
    if m.text and m.text.lower() in ['отмена', '/start']:
        start(m); return
    try:
        qty = int(''.join(filter(str.isdigit, m.text)))
        if not MIN_FOLLOWERS <= qty <= MAX_FOLLOWERS: raise
    except:
        bot.send_message(m.chat.id, f"Введите число от {MIN_FOLLOWERS} до {MAX_FOLLOWERS}")
        return

    price = qty * PRICE_PER_FOLLOWER
    if get_balance(m.chat.id) < price:
        bot.send_message(m.chat.id, f"Недостаточно средств!\nНужно: {price}₽\nУ вас: {get_balance(m.chat.id)}₽")
        return

    user_data[m.chat.id]['f_qty'] = qty
    user_data[m.chat.id]['f_price'] = price
    msg = bot.send_message(m.chat.id, f"*{qty}* подписчиков = *{price}₽*\n\nОтправьте ссылку на профиль Авито:", parse_mode='Markdown', reply_markup=cancel_btn())
    bot.register_next_step_handler(msg, followers_link)

def followers_link(m):
    qty = user_data[m.chat.id]['f_qty']
    price = user_data[m.chat.id]['f_price']
    link = m.text.strip()

    user_balances[m.chat.id] -= price

    admin_msg = (
        "НОВЫЙ ЗАКАЗ — ПОДПИСЧИКИ\n\n"
        f"Пользователь: @{m.from_user.username or 'нет'}\n"
        f"ID клиента: {m.chat.id}\n"
        f"Количество: *{qty}*\n"
        f"Сумма: *{price}₽*\n"
        f"Ссылка: {link}"
    )
    bot.send_message(OWNER_ID, admin_msg, parse_mode='Markdown')

    bot.send_message(m.chat.id,
        f"Заказ принят!\n*{qty}* подписчиков → *{price}₽*\nБаланс: *{get_balance(m.chat.id)}₽*",
        parse_mode='Markdown', reply_markup=main_menu())

# ========================= АДМИН-ОТВЕТ С АВТОПОДСТАНОВКОЙ =========================
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    try:
        orig = m.reply_to_message
        orig_text = (orig.text or orig.caption or "")

        # Супер-парсер ID — ловит твой формат (ID: 7579757892)
        client_id = None
        for pattern in [
            r'ID клиента[:\s]*(\d+)',
            r'ID[:\s]*[:\s]*(\d+)',
            r'\(ID[:\s]*(\d+)\)',
            r'ID[:\s]*[`\'"]?(\d+)[`\'"]?',
            r'Пользователь.*?(\d{8,12})',
            r'(\d{8,12})'  # Последний запасной
        ]:
            match = re.search(pattern, orig_text)
            if match:
                client_id = int(match.group(1))
                break

        if not client_id:
            bot.reply_to(m, "ID не найден! Убедитесь, что отвечаете на уведомление бота.")
            return

        # Если просто нажал "Ответить" (пустое сообщение) — авто подстановка
        if not m.text or m.text.strip() == "":
            # Ищем сумму в сообщении (например, 400)
            amount_match = re.search(r'Сумма[:\s]*[:\s]*(\d+)|(\d+) ?₽', orig_text)
            amount = amount_match.group(1) or amount_match.group(2) or "400"

            # Удаляем пустой реплай и отправляем готовую команду
            delete(OWNER_ID, m.message_id)
            bot.send_message(
                OWNER_ID,
                f"/add_balance {amount}",  # ← Готовая команда, сумма из сообщения
                reply_to_message_id=orig.message_id,
                reply_markup=telebot.types.ForceReply(selective=True)  # Автоподстановка в поле ввода
            )
            return

        # Если написал /add_balance — зачисляем (сумму можно изменить)
        if m.text.strip().startswith("/add_balance"):
            try:
                parts = m.text.strip().split()
                amount = float(parts[1]) if len(parts) >= 2 else 0
                if amount <= 0:
                    raise ValueError
            except:
                bot.reply_to(m, "Правильно: `/add_balance 500`", parse_mode="Markdown")
                return

            user_balances[client_id] = get_balance(client_id) + amount

            bot.send_message(client_id,
                f"Баланс пополнен на *{amount}₽*\nТекущий баланс: *{get_balance(client_id)}₽*",
                parse_mode="Markdown", reply_markup=main_menu())

            kb = telebot.types.InlineKeyboardMarkup()
            kb.add(telebot.types.InlineKeyboardButton("Написать клиенту", url=f"t.me/{bot.get_me().username}?start={client_id}"))
            bot.reply_to(m, f"Зачислено +{amount}₽\nБаланс: {get_balance(client_id)}₽", reply_markup=kb)
            return

        # Обычный ответ (текст, фото и т.д.) — на любое сообщение
        caption = f"*Ответ менеджера:*\n\n{escape(m.text or m.caption or '')}"

        if m.text:
            bot.send_message(client_id, caption, parse_mode="Markdown")
        elif m.photo:
            bot.send_photo(client_id, m.photo[-1].file_id, caption=caption, parse_mode="Markdown")
        elif m.video:
            bot.send_video(client_id, m.video.file_id, caption=caption, parse_mode="Markdown")
        elif m.document:
            bot.send_document(client_id, m.document.file_id, caption=caption, parse_mode="Markdown")
        elif m.voice:
            bot.send_voice(client_id, m.voice.file_id)
            if m.caption:
                bot.send_message(client_id, caption, parse_mode="Markdown")
        elif m.sticker:
            bot.send_sticker(client_id, m.sticker.file_id)
        else:
            bot.reply_to(m, "Тип сообщения не поддерживается")
            return

        kb = telebot.types.InlineKeyboardMarkup()
        kb.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"t.me/{bot.get_me().username}?start={client_id}"))
        bot.reply_to(m, f"Отправлено → ID {client_id}", reply_markup=kb)

    except Exception as e:
        bot.reply_to(m, f"Ошибка: {e}")

# ========================= ОТМЕНА =========================
@bot.callback_query_handler(func=lambda c: c.data == "cancel")
def cancel(c):
    bot.edit_message_text("Отменено", c.message.chat.id, c.message.message_id, reply_markup=main_menu())

# ========================= ВЕБХУК =========================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Error', 403

# ========================= ЗАПУСК =========================
if __name__ == '__main__':
    print("Бот запущен!")
    bot.remove_webhook()
    bot.infinity_polling(none_stop=True)