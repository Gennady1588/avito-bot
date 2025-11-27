from flask import Flask, request
import telebot
import os
import re
from html import escape

# ========================= КОНФИГУРАЦИЯ =========================
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg'
OWNER_ID = 1641571790  # Твой ID

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# База в памяти
user_balances = {}
user_data = {}

# ========================= ЦЕНЫ =========================
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225"
MIN_DEPOSIT_AMOUNT = 400

# ПФ
PRICE_50_PF_DAILY = 799
PRICE_AVITO_REVIEW = 350

# ПОДПИСЧИКИ НА ПРОФИЛЬ АВИТО
PRICE_PER_FOLLOWER = 200        # 200 рублей за 1 подписчика
MIN_FOLLOWERS_ORDER = 50        # минимум можно заказать 50
MAX_FOLLOWERS_ORDER = 10000     # максимум — 10к

# Длительность ПФ
DURATION_DAYS = {'1d': 1, '2d': 2, '3d': 3, '5d': 5, '7d': 7, '30d': 30}
DURATION_NAMES = {'1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц (30 Дней)'}

# ========================= ВСПОМОГАТЕЛЬНЫЕ =========================
def get_user_balance(user_id):
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    if user_id not in user_data:
        user_data[user_id] = {}
    return round(user_balances[user_id], 2)

def safe_delete_message(chat_id, message_id):
    try:
        if message_id:
            bot.delete_message(chat_id, message_id)
    except:
        pass

def calculate_pf_price(duration_key, pf_count):
    try:
        pf_count = int(pf_count)
        days = DURATION_DAYS.get(duration_key, 1)
    except:
        return 0
    if pf_count == 50:
        daily = PRICE_50_PF_DAILY
    elif pf_count == 100:
        daily = PRICE_50_PF_DAILY * 2
    else:
        return 0
    return round(daily * days)

# ========================= КЛАВИАТУРЫ =========================
def get_main_menu_markup():
    markup = telebot.types.InlineKeyboardMarkup(row_width=1)
    markup.add(telebot.types.InlineKeyboardButton("Заказать ПФ", callback_data='order_pf'))
    markup.add(telebot.types.InlineKeyboardButton("Добавить отзыв", callback_data='order_review'))
    markup.add(telebot.types.InlineKeyboardButton("Подписчики на профиль Авито", callback_data='order_followers'))
    markup.add(telebot.types.InlineKeyboardButton("Личный кабинет", callback_data='my_account'))
    markup.add(telebot.types.InlineKeyboardButton("FAQ / Кейсы", callback_data='faq'))
    markup.add(telebot.types.InlineKeyboardButton("Промокоды", callback_data='promocodes'))
    markup.add(telebot.types.InlineKeyboardButton("Правила", url='https://t.me/Avitounlock/18'))
    markup.add(telebot.types.InlineKeyboardButton("Техподдержка", url='https://t.me/Avitounlock'))
    return markup

def get_deposit_cancel_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Отмена", callback_data='back_to_main_menu'))
    return markup

def get_account_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Пополнить баланс", callback_data='account_deposit'))
    markup.add(telebot.types.InlineKeyboardButton("Мои заказы", callback_data='account_orders'))
    markup.add(telebot.types.InlineKeyboardButton("Назад", callback_data='back_to_main_menu'))
    return markup

# ========================= НОВАЯ УСЛУГА: ПОДПИСЧИКИ =========================
def request_followers_count(message):
    chat_id = message.chat.id
    safe_delete_message(chat_id, message.message_id)
    bot.clear_step_handler_by_chat_id(chat_id)

    text = (
        "Подписчики на профиль Авито\n\n"
        f"Цена: *{PRICE_PER_FOLLOWER} ₽ за 1 подписчика*\n"
        f"Минимум: {MIN_FOLLOWERS_ORDER}, максимум: {MAX_FOLLOWERS_ORDER}\n\n"
        "Введите нужное количество подписчиков:\n"
        "(например: 150, 500, 2000)"
    )
    sent = bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=get_deposit_cancel_markup())
    bot.register_next_step_handler(sent, process_followers_quantity, sent.message_id)

def process_followers_quantity(message, prompt_msg_id):
    chat_id = message.chat.id

    if message.text and message.text.lower() in ['отмена', 'назад', '/start']:
        safe_delete_message(chat_id, message.message_id)
        safe_delete_message(chat_id, prompt_msg_id)
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return

    try:
        qty = int(message.text.strip())
        if qty < MIN_FOLLOWERS_ORDER or qty > MAX_FOLLOWERS_ORDER:
            raise ValueError
    except:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=prompt_msg_id,
            text="Ошибка! Введите число от 50 до 10 000\n\nПример: 300",
            reply_markup=get_deposit_cancel_markup()
        )
        bot.register_next_step_handler(message, process_followers_quantity, prompt_msg_id)
        return

    total_price = qty * PRICE_PER_FOLLOWER
    balance = get_user_balance(chat_id)

    if balance < total_price:
        safe_delete_message(chat_id, prompt_msg_id)
        bot.send_message(chat_id,
            f"Недостаточно средств\n\n"
            f"Стоимость {qty} подписчиков = *{total_price} ₽*\n"
            f"На балансе: *{balance} ₽*\n\n"
            "Пополните баланс →",
            parse_mode='Markdown',
            reply_markup=get_account_markup()
        )
        return

    # Сохраняем данные
    user_data[chat_id]['followers_qty'] = qty
    user_data[chat_id]['followers_price'] = total_price

    safe_delete_message(chat_id, prompt_msg_id)
    safe_delete_message(chat_id, message.message_id)

    sent = bot.send_message(chat_id,
        f"Отлично! Вы заказываете *{qty}* подписчиков\n"
        f"Стоимость: *{total_price} ₽*\n\n"
        "Теперь отправьте ссылку на ваш профиль Авито\n"
        "(кнопка «Поделиться» → «Скопировать ссылку»)",
        parse_mode='Markdown',
        reply_markup=get_deposit_cancel_markup()
    )
    bot.register_next_step_handler(sent, process_followers_link, sent.message_id)

def process_followers_link(message, prompt_msg_id):
    chat_id = message.chat.id

    if message.text and message.text.lower() in ['отмена', 'назад', '/start']:
        safe_delete_message(chat_id, message.message_id)
        safe_delete_message(chat_id, prompt_msg_id)
        start(message)
        return

    link = message.text.strip()
    qty = user_data[chat_id].get('followers_qty', 0)
    price = user_data[chat_id].get('followers_price', 0)

    # Списываем баланс
    user_balances[chat_id] -= price

    # Уведомление тебе (владельцу)
    admin_text = (
        "Новый заказ — ПОДПИСЧИКИ НА ПРОФИЛЬ\n\n"
        f"Пользователь: @{message.from_user.username or 'без имени'} (ID: `{chat_id}`)\n"
        f"Количество: *{qty}* подписчиков\n"
        f"Сумма: *{price} ₽* — оплачено\n"
        f"Ссылка на профиль:\n{link}\n\n"
        "Ответьте реплаем — клиент получит сообщение"
    )
    bot.send_message(OWNER_ID, admin_text, parse_mode='Markdown')

    # Ответ клиенту
    bot.send_message(chat_id,
        f"Заказ принят и оплачен!\n\n"
        f"Подписчики: *{qty} чел.*\n"
        f"Списано: *{price} ₽*\n"
        f"Остаток на балансе: *{get_user_balance(chat_id)} ₽*\n\n"
        "Менеджер запустит накрутку в ближайшее время.\n"
        "Вы получите уведомление о старте",
        parse_mode='Markdown',
        reply_markup=get_main_menu_markup()
    )

    # Очистка
    safe_delete_message(chat_id, message.message_id)
    safe_delete_message(chat_id, prompt_msg_id)
    user_data[chat_id].pop('followers_qty', None)
    user_data[chat_id].pop('followers_price', None)

# ========================= ОБРАБОТКА КНОПОК =========================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)

    if call.data == 'order_followers':
        request_followers_count(call.message)
        return

    # Здесь будут все остальные твои обработчики (ПФ, отзывы, пополнение и т.д.)
    # Вставь сюда свой старый код из callback_query_handler, если он у тебя есть
    # (я не стал его копировать, чтобы не удлинять — просто добавь свой)

    if call.data == 'back_to_main_menu':
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id,
            text="Главное меню", reply_markup=get_main_menu_markup())
    # ... остальные колбэки

# ========================= УДОБНЫЙ ОТВЕТ МЕНЕДЖЕРУ (ТЫ) =========================
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(message):
    try:
        orig_text = message.reply_to_message.text or message.reply_to_message.caption or ""
        client_id = None
        for pattern in [r'ID:?\s*[`\'"]?(\d+)', r'\(ID:?\s*(\d+)']:
            match = re.search(pattern, orig_text)
            if match:
                client_id = int(match.group(1))
                break
        if not client_id:
            bot.reply_to(message, "Не найден ID клиента")
            return

        # Команда пополнения
        if message.text and message.text.lower().startswith('/add_balance'):
            try:
                amount = float(message.text.split()[1])
                user_balances[client_id] = get_user_balance(client_id) + amount
                bot.send_message(client_id, f"Ваш баланс пополнен на *{amount} ₽*\nТекущий баланс: *{get_user_balance(client_id)} ₽*", parse_mode='Markdown')
                bot.reply_to(message, f"Пополнено +{amount} ₽\nБаланс клиента: {get_user_balance(client_id)} ₽")
                return
            except:
                bot.reply_to(message, "Формат: /add_balance 1000")
                return

        # Обычный ответ
        if message.content_type == 'text':
            bot.send_message(client_id, f"<b>Ответ менеджера:</b>\n\n{escape(message.html_text)}", parse_mode='HTML')
        elif message.content_type in ['photo', 'video', 'document', 'voice', 'sticker']:
            caption = f"<b>Ответ менеджера:</b>\n\n{escape(message.caption_html or '')}"
            if message.photo:
                bot.send_photo(client_id, message.photo[-1].file_id, caption=caption, parse_mode='HTML')
            elif message.video:
                bot.send_video(client_id, message.video.file_id, caption=caption, parse_mode='HTML')
            elif message.document:
                bot.send_document(client_id, message.document.file_id, caption=caption, parse_mode='HTML')
            elif message.voice:
                bot.send_voice(client_id, message.voice.file_id, caption=caption, parse_mode='HTML')
            elif message.sticker:
                bot.send_sticker(client_id, message.sticker.file_id)
            else:
                bot.reply_to(message, "Тип не поддерживается")
                return

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("Написать ещё", url=f"https://t.me/{bot.get_me().username}?start={client_id}"))
        bot.reply_to(message, f"Отправлено клиенту {client_id}", reply_markup=markup)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

# ========================= ЗАПУСК =========================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().as_text())
        bot.process_new_updates([update])
        return 'OK', 200
    return '', 403

if __name__ == '__main__':
    print("Бот запущен")
    bot.remove_webhook()
    bot.infinity_polling(timeout=60)