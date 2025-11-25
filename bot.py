from flask import Flask, request
import telebot
import os
import re 

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БОТА И СЕРВЕРА ---
# УБЕДИТЕСЬ, ЧТО ЭТИ ПЕРЕМЕННЫЕ УКАЗАНЫ ВАШИМИ ЗНАЧЕНИЯМИ
TOKEN = os.environ.get('TOKEN', 'YOUR_BOT_TOKEN_HERE') 
OWNER_ID = int(os.environ.get('OWNER_ID', 123456789)) # Ваш ID 
bot = telebot.TeleBot(TOKEN)

# ИМИТАЦИЯ БАЗЫ ДАННЫХ 
user_balances = {} 
user_data = {} 

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА, КАРТЫ И ЦЕН ---
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225" 
MIN_DEPOSIT_AMOUNT = 400

# Цены и длительность
PRICE_50_PF_DAILY = 799 
PRICE_AVITO_REVIEW = 350 

DURATION_DAYS = {
    '1d': 1, '2d': 2, '3d': 3, 
    '5d': 5, '7d': 7, '30d': 30  
}

DURATION_NAMES = {
    '1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', 
    '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц (30 Дней)'
}

# --- ФУНКЦИИ РАСЧЕТА И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def escape_markdown(text):
    """
    Экранирует специальные символы Markdown V2, 
    кроме тех, которые нужны для работы ссылок.
    ВНИМАНИЕ: Все сообщения, использующие эту функцию, должны быть отправлены 
    с parse_mode='MarkdownV2'.
    """
    if not isinstance(text, str):
        text = str(text)
    
    # Список символов, которые обязательно нужно экранировать в MarkdownV2
    # _, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !
    
    # Экранируем их все, так как они могут появляться в данных пользователя
    text = text.replace('\\', '\\\\') # Экранируем сам бэкслеш первым
    text = text.replace('_', '\_')
    text = text.replace('*', '\*')
    text = text.replace('[', '\[')
    text = text.replace(']', '\]')
    text = text.replace('(', '\(')
    text = text.replace(')', '\)')
    text = text.replace('~', '\~')
    text = text.replace('`', '\`')
    text = text.replace('>', '\>')
    text = text.replace('#', '\#')
    text = text.replace('+', '\+')
    text = text.replace('-', '\-')
    text = text.replace('=', '\=')
    text = text.replace('|', '\|')
    text = text.replace('{', '\{')
    text = text.replace('}', '\}')
    text = text.replace('.', '\.')
    text = text.replace('!', '\!')
    
    return text

def calculate_price(duration_key, pf_count):
    """Рассчитывает общую стоимость заказа без скидок."""
    try:
        pf_count = int(pf_count)
        days = DURATION_DAYS.get(duration_key, 1)
    except ValueError:
        return 0.0
        
    if pf_count == 50:
        daily_cost = PRICE_50_PF_DAILY
    elif pf_count == 100:
        daily_cost = PRICE_50_PF_DAILY * 2
    else:
        return 0.0 
    
    total_price = daily_cost * days
    
    return round(total_price, 0)

def safe_delete_message(chat_id, message_id):
    """Пытается удалить сообщение, игнорируя ошибки."""
    try:
        if message_id:
            bot.delete_message(chat_id, message_id)
    except Exception:
        pass 
        
def get_user_balance(user_id):
    """Получает баланс пользователя, инициализируя его, если он новый."""
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    if user_id not in user_data:
        user_data[user_id] = {}
        
    return round(user_balances[user_id], 2)

# --- ФУНКЦИИ КЛАВИАТУР (без изменений) ---

def get_main_menu_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🚀 Заказать ПФ', callback_data='order_pf'),
        telebot.types.InlineKeyboardButton(text='🚪 Личный кабинет', callback_data='my_account')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='⭐ Добавить отзыв (от 1 шт)', callback_data='order_review')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='💬 FAQ / Кейсы', callback_data='faq'),
        telebot.types.InlineKeyboardButton(text='🎁 Промокоды', callback_data='promocodes')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='📗 Правила пользования', url='https://t.me/Avitounlock/18'),
        telebot.types.InlineKeyboardButton(text='🧑‍💻 Тех поддержка', url='https://t.me/Avitounlock') 
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Подбор стратегии', url=f'https://t.me/{MANAGER_USERNAME}')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Есть ли на Авито бан за ПФ!?', url='https://t.me/Avitounlock/19')
    )
    return markup

def get_account_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='💳 Пополнить баланс', callback_data='account_deposit')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='📖 Мои заказы', callback_data='account_orders')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🤝 Партнерская программа', callback_data='account_partner')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')
    )
    return markup

def get_duration_markup(pf_count='50'):
    markup = telebot.types.InlineKeyboardMarkup()
    price_50_1d = calculate_price('1d', 50) 
    
    # ⚠️ Экранируем цену, так как она идет в формат MarkdownV2
    safe_price = escape_markdown(str(int(price_50_1d)))
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'День (от {safe_price}₽)', callback_data='duration_1d'),
        telebot.types.InlineKeyboardButton(text=f'2 дня', callback_data='duration_2d'),
        telebot.types.InlineKeyboardButton(text=f'3 дня', callback_data='duration_3d')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'5 дней', callback_data='duration_5d'),
        telebot.types.InlineKeyboardButton(text=f'7 дней', callback_data='duration_7d'),
        telebot.types.InlineKeyboardButton(text=f'Месяц', callback_data='duration_30d')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_main_menu')
    )
    return markup

def get_pf_count_markup(duration_key):
    markup = telebot.types.InlineKeyboardMarkup()
    
    price_50 = calculate_price(duration_key, 50)
    price_100 = calculate_price(duration_key, 100)
    
    # ⚠️ Экранируем цену, так как она идет в формат MarkdownV2
    safe_price_50 = escape_markdown(str(int(price_50)))
    safe_price_100 = escape_markdown(str(int(price_100)))

    markup.row(
        telebot.types.InlineKeyboardButton(text=f'50 ПФ ({safe_price_50}₽)', callback_data='pf_count_50'),
        telebot.types.InlineKeyboardButton(text=f'100 ПФ ({safe_price_100}₽)', callback_data='pf_count_100')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_duration') 
    )
    return markup

def get_faq_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='Вопросы и ответы', callback_data='faq_qna'),
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Как работают поведенческие факторы', callback_data='faq_how_pf_works')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Иксы на авито не работают', callback_data='faq_x_dont_work')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Кейсы и отзывы', callback_data='faq_cases_and_reviews')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_main_menu')
    )
    return markup

# --- ФУНКЦИИ ОБРАБОТКИ ПОПОЛНЕНИЯ ---

def request_deposit_amount(message):
    chat_id = message.chat.id
    
    bot.clear_step_handler_by_chat_id(chat_id) 

    # ⚠️ Экранируем минимальную сумму
    safe_min_amount = escape_markdown(str(MIN_DEPOSIT_AMOUNT))

    deposit_request_text = (
        "💳 *Пополнить баланс*\n\n"
        f"❗️ Минимальная сумма пополнения \- *{safe_min_amount} ₽*\n\n"
        "Введите желаемую сумму пополнения:"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад', callback_data='back_to_main_menu')
    )
    
    safe_delete_message(chat_id, getattr(message, 'message_id', None)) 
    
    sent_msg = bot.send_message(
        chat_id, 
        deposit_request_text, 
        reply_markup=markup, 
        parse_mode='MarkdownV2'
    )
    
    bot.register_next_step_handler(sent_msg, process_deposit_amount)


def process_deposit_amount(message):
    chat_id = message.chat.id
    
    safe_delete_message(chat_id, message.message_id) 
    
    # Проверка на команды и отмену
    if message.text and message.text.lower().startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return
    
    if message.content_type == 'text' and message.text.lower() in ['🔙 отмена / назад', 'отмена']:
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message) 
        return

    if not message.text:
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода\.* Пожалуйста, введите сумму только *цифрами*\.",
            parse_mode='MarkdownV2'
        )
        request_deposit_amount(type('obj', (object,), {'chat': type('chat', (object,), {'id': chat_id}), 'message_id': None})())
        return

    deposit_text = message.text.strip()
    amount = 0

    try:
        cleaned_text = re.sub(r'[^\d\.]', '', deposit_text.lower().replace(',', '.'))
        amount = int(float(cleaned_text))
        
        if amount < MIN_DEPOSIT_AMOUNT:
            raise ValueError("Сумма меньше минимальной")
        
    except ValueError:
        safe_min_amount = escape_markdown(str(MIN_DEPOSIT_AMOUNT))
        bot.send_message(
            chat_id, 
            f"🚫 *Ошибка ввода\.* Пожалуйста, введите корректную сумму \(минимум {safe_min_amount} ₽\) только цифрами \(например, 500\)\.",
            parse_mode='MarkdownV2'
        )
        request_deposit_amount(type('obj', (object,), {'chat': type('chat', (object,), {'id': chat_id}), 'message_id': None})())
        return

    # ⚠️ Экранируем переменные для MarkdownV2
    safe_amount = escape_markdown(str(amount))
    safe_card = escape_markdown(YOUR_CARD_NUMBER)
    safe_manager_username = escape_markdown(MANAGER_USERNAME)

    # --- ОТВЕТ КЛИЕНТУ (С НОМЕРОМ КАРТЫ) - ДОРАБОТАННЫЙ ТЕКСТ ---
    payment_instruction = (
        f"✅ *Запрос на {safe_amount} ₽ принят\!*\n\n"
        "1\. *Переведите ТОЧНО эту сумму* на карту:\n"
        f"💳 **`{safe_card}`**\n\n" 
        "2\. *После перевода* свяжитесь с менеджером, чтобы он проверил поступление и зачислил средства\.\n"
        f"Менеджер: **@{safe_manager_username}**\n\n"
        "❗️ *ВНИМАНИЕ: Менеджер зачисляет средства вручную\. Это может занять от 1 до 5 минут\.*\n"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='✍️ Связаться с менеджером', url=f'https://t.me/{MANAGER_USERNAME}')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')
    )

    # --- УВЕДОМЛЕНИЕ АДМИНИСТРАТОРА ---
    # ⚠️ Экранируем ID и юзернейм клиента для админского уведомления
    client_username = escape_markdown(message.from_user.username or 'без\_юзернейма')
    safe_chat_id = escape_markdown(str(chat_id))

    deposit_summary_for_admin = (
        "💰 *ЗАПРОС НА ПОПОЛНЕНИЕ* 💰\n\n"
        f"Пользователь: @{client_username} \(ID: `{safe_chat_id}`\)\n"
        f"Желаемая сумма: *{safe_amount} ₽*\n"
        f"Карта для проверки: `{safe_card}`\n\n"
        f"➡️ *Необходимо проверить поступление:* **{safe_amount} ₽**\n"
        "Ответьте реплаем, чтобы подтвердить получение средств\. Для зачисления используйте `/add\_balance {сумма}`"
    )
    
    try:
        bot.send_message(
            OWNER_ID, 
            deposit_summary_for_admin, 
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        print(f"Error sending admin deposit notification for chat {chat_id}: {e}") 
    
    # ГАРАНТИРОВАННАЯ ОТПРАВКА НОМЕРА КАРТЫ КЛИЕНТУ
    try:
        bot.send_message(
            chat_id, 
            payment_instruction,
            reply_markup=markup,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        # Запасной текст на случай ошибки
        fallback_text = (
            f"❌ Критическая ошибка\. Произошел сбой при отправке платежных данных\. "
            f"Ваш запрос на {safe_amount} ₽ сохранен\. "
            f"Номер карты для перевода: {safe_card}\. "
            f"Свяжитесь с менеджером @{safe_manager_username}\."
        )
        
        bot.send_message(
            chat_id, 
            fallback_text,
            parse_mode='MarkdownV2' 
        )
        
        try:
            bot.send_message(
                OWNER_ID, 
                f"🚨 *ОШИБКА ОТПРАВКИ КЛИЕНТУ:* Не удалось отправить платежную инструкцию клиенту `{safe_chat_id}`\. "
                f"Сумма: {safe_amount} ₽\. Ошибка: `{escape_markdown(str(e))}`\. Отправлен запасной текст\.",
                parse_mode='MarkdownV2'
            )
        except Exception:
            pass 


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА ПФ ---

def request_links(message):
    """Проверяет баланс и запрашивает ссылки, если средств достаточно."""
    chat_id = message.chat.id
    
    if 'duration' not in user_data.get(chat_id, {}) or 'pf_count' not in user_data.get(chat_id, {}):
        bot.send_message(chat_id, "❌ *Ошибка\.* Данные о заказе потеряны\. Начните, пожалуйста, заново\.", parse_mode='MarkdownV2', reply_markup=get_main_menu_markup())
        safe_delete_message(chat_id, getattr(message, 'message_id', None))
        return
        
    duration_key = user_data[chat_id]['duration']
    pf_count = user_data[chat_id]['pf_count']
    total_price = calculate_price(duration_key, pf_count)
    current_balance = get_user_balance(chat_id)
    duration_name = DURATION_NAMES.get(duration_key, 'N/A')
    
    if current_balance < total_price:
        required = round(total_price - current_balance, 2)
        
        # ⚠️ Экранируем переменные
        safe_total_price = escape_markdown(str(int(total_price)))
        safe_current_balance = escape_markdown(str(current_balance))
        safe_required = escape_markdown(str(required))

        insufficient_funds_text = (
            "❌ *Недостаточно средств\!*\n\n"
            f"Стоимость заказа: *{safe_total_price} ₽*\n"
            f"Ваш баланс: *{safe_current_balance} ₽*\n"
            f"Необходимо пополнить: *{safe_required} ₽*\n\n"
            "Пожалуйста, пополните баланс в разделе 'Личный кабинет'\."
        )
        
        safe_delete_message(chat_id, getattr(message, 'message_id', None)) 
        
        bot.send_message(
            chat_id, 
            insufficient_funds_text,
            reply_markup=get_account_markup(),
            parse_mode='MarkdownV2'
        )
        user_data[chat_id]['duration'] = None
        user_data[chat_id]['pf_count'] = None
        return 
    
    # ⚠️ Экранируем переменные
    safe_pf_count = escape_markdown(str(pf_count))
    safe_duration_name = escape_markdown(duration_name)

    final_text = (
        f"✅ *Параметры заказа выбраны*\n\n"
        f"ПФ в день: *{safe_pf_count}*\n"
        f"Длительность: *{safe_duration_name}*\n\n"
        "🔗 *Отправьте ссылки*\n"
        "КАЖДАЯ ССЫЛКА С НОВОЙ СТРОКИ \(`CTRL\+ENTER`\)\."
    )
    
    safe_delete_message(chat_id, getattr(message, 'message_id', None))
    
    sent_msg = bot.send_message(
        chat_id, 
        final_text, 
        parse_mode='MarkdownV2'
    )
    
    user_data[chat_id]['awaiting_links_msg_id'] = sent_msg.message_id
    
    bot.register_next_step_handler(sent_msg, process_links_and_send_order)


def process_links_and_send_order(message):
    """Обрабатывает ссылки, списывает баланс и отправляет заказ админу."""
    chat_id = message.chat.id
    
    if not message.text:
        if 'awaiting_links_msg_id' in user_data.get(chat_id, {}):
            safe_delete_message(chat_id, user_data[chat_id]['awaiting_links_msg_id'])
            del user_data[chat_id]['awaiting_links_msg_id']
        
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода\.* Пожалуйста, отправьте ссылки в виде *текста*\.",
            parse_mode='MarkdownV2'
        )
        
        request_links(type('obj', (object,), {'chat': type('chat', (object,), {'id': chat_id}), 'message_id': None})()) 
        return

    links = message.text
    
    if 'awaiting_links_msg_id' in user_data.get(chat_id, {}):
        safe_delete_message(chat_id, user_data[chat_id]['awaiting_links_msg_id'])
        del user_data[chat_id]['awaiting_links_msg_id']
    
    duration_key = user_data[chat_id].get('duration', 'N/A')
    pf_count = user_data[chat_id].get('pf_count', 0)
    total_price = calculate_price(duration_key, pf_count)
    
    paid = False
    balance_status = ""
    
    if get_user_balance(chat_id) >= total_price and total_price > 0:
        user_balances[chat_id] -= total_price
        user_balances[chat_id] = round(user_balances[chat_id], 2)
        
        # ⚠️ Экранируем переменные
        safe_total_price = escape_markdown(str(int(total_price)))
        safe_new_balance = escape_markdown(str(get_user_balance(chat_id)))
        
        balance_status = f"*Списано {safe_total_price} ₽*\. Новый баланс: *{safe_new_balance} ₽*\."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания\.* Недостаточно средств или цена заказа 0 ₽\. Заказ отменен\."
    
    duration_text = DURATION_NAMES.get(duration_key, 'Неизвестно')
    
    # ⚠️ Экранируем переменные для админского уведомления
    client_username = escape_markdown(message.from_user.username or 'без\_юзернейма')
    safe_chat_id = escape_markdown(str(chat_id))
    safe_price_admin = escape_markdown(str(int(total_price)))
    safe_duration_text = escape_markdown(duration_text)
    safe_pf_count_admin = escape_markdown(str(pf_count))

    # СВОДКА ДЛЯ АДМИНИСТРАТОРА (со ссылками)
    order_summary_for_admin = (
        "🔥 *НОВЫЙ ЗАКАЗ ПФ* 🔥\n\n"
        f"Пользователь: @{client_username} \(ID: `{safe_chat_id}`\)\n"
        f"Сумма заказа: *{safe_price_admin} ₽*\n"
        f"Статус оплаты: {'✅ Оплачен' if paid else '❌ Не оплачен \(Ошибка\)'}\n"
        f"Продолжительность: *{safe_duration_text}*\n"
        f"Количество ПФ в день: *{safe_pf_count_admin}*\n"
        "--- ССЫЛКИ НА ОБЪЯВЛЕНИЯ ---\n"
        # ⚠️ Здесь не используем escape_markdown, чтобы не ломать ссылки, 
        # но помещаем их в блок кода для предотвращения парсинга
        f"```\n{links}\n```\n" 
        "------------------------------\n"
        "Для ответа клиенту используйте реплай на это сообщение\."
    )
    
    bot.send_message(
        OWNER_ID, 
        order_summary_for_admin, 
        parse_mode='MarkdownV2'
    )
    
    if paid:
        confirmation_text = (
            f"✅ *Ваш заказ принят и оплачен\!*\n\n" 
            f"Стоимость: *{safe_price_admin} ₽*\. {balance_status}\n\n"
            "Менеджер проверит ссылки и, в случае успеха, заказ будет запущен\. "
            "Вам придет оповещение о запуске\.\n\n"
            "⏳ *Ожидайте\.\.\.*"
        )
    else:
        confirmation_text = (
            "❌ *Заказ отменен из-за нехватки средств или ошибки\.*\n\n"
            "Пожалуйста, пополните баланс и повторите заказ\."
        )

    safe_delete_message(chat_id, message.message_id)
    
    bot.send_message(
        chat_id, 
        confirmation_text,
        reply_markup=get_main_menu_markup(),
        parse_mode='MarkdownV2'
    )
    
    user_data[chat_id]['duration'] = None
    user_data[chat_id]['pf_count'] = None


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА ОТЗЫВА ---

def request_review_quantity(message):
    """Шаг 1: Запрашивает количество отзывов."""
    chat_id = message.chat.id
    
    bot.clear_step_handler_by_chat_id(chat_id) 
    
    # ⚠️ Экранируем цену
    safe_price = escape_markdown(str(PRICE_AVITO_REVIEW))

    review_request_text = (
        "⭐ *Заказ отзыва на Авито*\n\n"
        f"Цена за 1 отзыв: *{safe_price} ₽*\.\n"
        "Введите желаемое *количество* отзывов \(от 1 шт\):"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад', callback_data='back_to_main_menu')
    )
    
    safe_delete_message(chat_id, getattr(message, 'message_id', None)) 
    
    sent_msg = bot.send_message(
        chat_id, 
        review_request_text, 
        reply_markup=markup, 
        parse_mode='MarkdownV2'
    )
    
    bot.register_next_step_handler(sent_msg, process_review_quantity)


def process_review_quantity(message):
    """Шаг 2: Обрабатывает количество, проверяет баланс и переходит к деталям."""
    chat_id = message.chat.id
    
    safe_delete_message(chat_id, message.message_id) 
    
    if message.text and message.text.lower().startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return
    
    if not message.text:
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода\.* Пожалуйста, введите количество *цифрами*\.",
            parse_mode='MarkdownV2'
        )
        request_review_quantity(type('obj', (object,), {'chat': type('chat', (object,), {'id': chat_id}), 'message_id': None})())
        return

    review_count_text = message.text.strip()
    count = 0

    try:
        cleaned_text = re.sub(r'[^\d]', '', review_count_text)
        count = int(cleaned_text)
        
        if count < 1:
            raise ValueError("Количество меньше минимального")
        
    except ValueError:
        bot.send_message(
            chat_id, 
            f"🚫 *Ошибка ввода\.* Пожалуйста, введите корректное количество отзывов \(минимум 1\)\.",
            parse_mode='MarkdownV2'
        )
        request_review_quantity(type('obj', (object,), {'chat': type('chat', (object,), {'id': chat_id}), 'message_id': None})())
        return

    # Расчет цены
    total_price = count * PRICE_AVITO_REVIEW
    current_balance = get_user_balance(chat_id)
    
    if current_balance < total_price:
        required = round(total_price - current_balance, 2)
        
        # ⚠️ Экранируем переменные
        safe_count = escape_markdown(str(count))
        safe_total_price = escape_markdown(str(int(total_price)))
        safe_current_balance = escape_markdown(str(current_balance))
        safe_required = escape_markdown(str(required))

        insufficient_funds_text = (
            "❌ *Недостаточно средств\!*\n\n"
            f"Стоимость {safe_count} отзывов: *{safe_total_price} ₽*\n"
            f"Ваш баланс: *{safe_current_balance} ₽*\n"
            f"Необходимо пополнить: *{safe_required} ₽*\n\n"
            "Пожалуйста, пополните баланс в разделе 'Личный кабинет'\."
        )
        
        bot.send_message(
            chat_id, 
            insufficient_funds_text,
            reply_markup=get_account_markup(),
            parse_mode='MarkdownV2'
        )
        return

    # Сохраняем данные для следующего шага
    user_data[chat_id]['review_count'] = count
    user_data[chat_id]['review_price'] = total_price
    
    request_review_details(chat_id, count, total_price)


def request_review_details(chat_id, count, price):
    """Шаг 3: Запрашивает ссылку и текст отзыва."""
    
    safe_count = escape_markdown(str(count))
    safe_price = escape_markdown(str(int(price)))

    details_request_text = (
        f"✅ *Заказ {safe_count} отзыв\(а/ов\) на {safe_price} ₽*\n\n"
        "Отправьте следующую информацию *одним* сообщением:\n\n"
        "1\. *Ссылка* на профиль Авито, куда нужно добавить отзыв\.\n"
        "2\. *Текст* отзыва \(или тексты, если их несколько, разделенные пустой строкой\)\.\n\n"
        "🔗 *Формат сообщения:*\n"
        "\n`[Ссылка на профиль]`\n"
        "`[Текст отзыва 1]`\n"
        "`[Текст отзыва 2 (если есть)]`"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад', callback_data='back_to_main_menu')
    )
    
    sent_msg = bot.send_message(
        chat_id, 
        details_request_text, 
        reply_markup=markup, 
        parse_mode='MarkdownV2'
    )
    
    user_data[chat_id]['awaiting_review_details_msg_id'] = sent_msg.message_id
    
    bot.register_next_step_handler(sent_msg, process_review_order)


def process_review_order(message):
    """Шаг 4: Финализация заказа отзыва, списание и отправка админу."""
    chat_id = message.chat.id
    
    if 'awaiting_review_details_msg_id' in user_data.get(chat_id, {}):
        safe_delete_message(chat_id, user_data[chat_id]['awaiting_review_details_msg_id'])
        del user_data[chat_id]['awaiting_review_details_msg_id']
    
    if not message.text:
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода\.* Пожалуйста, отправьте ссылку и текст отзыва в виде *текста*\.",
            parse_mode='MarkdownV2'
        )
        bot.send_message(chat_id, "Пожалуйста, попробуйте заказать отзыв снова\.", reply_markup=get_main_menu_markup(), parse_mode='MarkdownV2')
        return
        
    review_details = message.text
    count = user_data[chat_id].get('review_count', 0)
    total_price = user_data[chat_id].get('review_price', 0)

    paid = False
    balance_status = ""
    
    safe_count = escape_markdown(str(count))
    safe_total_price = escape_markdown(str(int(total_price)))

    # Списание средств
    if get_user_balance(chat_id) >= total_price and total_price > 0:
        user_balances[chat_id] -= total_price
        user_balances[chat_id] = round(user_balances[chat_id], 2)
        safe_new_balance = escape_markdown(str(get_user_balance(chat_id)))

        balance_status = f"*Списано {safe_total_price} ₽*\. Новый баланс: *{safe_new_balance} ₽*\."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания\.* Недостаточно средств или цена заказа 0 ₽\. Заказ отменен\."

    # СВОДКА ДЛЯ АДМИНИСТРАТОРА (со ссылкой/текстом)
    client_username = escape_markdown(message.from_user.username or 'без\_юзернейма')
    safe_chat_id = escape_markdown(str(chat_id))

    order_summary_for_admin = (
        "⭐ *НОВЫЙ ЗАКАЗ ОТЗЫВА НА АВИТО* ⭐\n\n"
        f"Пользователь: @{client_username} \(ID: `{safe_chat_id}`\)\n"
        f"Сумма заказа: *{safe_total_price} ₽*\n"
        f"Статус оплаты: {'✅ Оплачен' if paid else '❌ Не оплачен \(Ошибка\)'}\n"
        f"Количество отзывов: *{safe_count}*\n"
        "--- ДЕТАЛИ ЗАКАЗА ---\n"
        f"```\n{review_details}\n```\n" # Текст заказа в блоке кода
        "------------------------------\n"
        "Для ответа клиенту используйте реплай на это сообщение\."
    )
    
    bot.send_message(
        OWNER_ID, 
        order_summary_for_admin, 
        parse_mode='MarkdownV2'
    )
    
    if paid:
        confirmation_text = (
            f"✅ *Ваш заказ на отзыв\(ы\) принят и оплачен\!*\n\n" 
            f"Стоимость: *{safe_total_price} ₽*\. {balance_status}\n\n"
            "Менеджер проверит детали и запустит выполнение\. Вам придет оповещение о завершении\.\n\n"
            "⏳ *Ожидайте\.\.\.*"
        )
    else:
        confirmation_text = (
            "❌ *Заказ отменен из-за нехватки средств или ошибки\.*\n\n"
            "Пожалуйста, пополните баланс и повторите заказ\."
        )

    safe_delete_message(chat_id, message.message_id)
    
    bot.send_message(
        chat_id, 
        confirmation_text,
        reply_markup=get_main_menu_markup(),
        parse_mode='MarkdownV2'
    )
    
    # Очистка данных
    if 'review_count' in user_data.get(chat_id, {}): del user_data[chat_id]['review_count']
    if 'review_price' in user_data.get(chat_id, {}): del user_data[chat_id]['review_price']


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ (ОБНОВЛЕНЫ НА MarkdownV2) ---

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.chat.id
    get_user_balance(user_id) 
    
    bot.clear_step_handler_by_chat_id(user_id)
    
    # Текст должен быть в формате MarkdownV2
    message_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito \(ПФ\) — это "
        "инструмент, который помогает поднять ваше объявление на 1\-ю "
        "позицию в результатах поиска... \\n\n"
        "В **Avitounlock** мы уже более 4 лет помогаем тысячам клиентам... "
        "Наша репутация основана на реальных отзывах — на данный момент их уже более 2750\+ ‼️\n"
        "Ознакомьтесь с ними в нашем [Телеграм канале](https://t.me/Avitounlock) ✅ "
        "и убедитесь в качестве нашей работы\! \n"
        "\* Полное соблюдение правил Авито\! Безопасно и надежно\! \n"
        "\* Круглосуточная работа\! Наш бот работает 24/7, не пропускайте ни одной "
        "возможности продвинуть объявления\! 🤖 \n\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП\!_"
    )
    
    hide_keyboard = telebot.types.ReplyKeyboardRemove()
    
    bot.send_message(
        user_id, 
        message_text, 
        reply_markup=hide_keyboard, 
        parse_mode='MarkdownV2' 
    )
    
    bot.send_message(
        user_id,
        "Выберите действие:",
        reply_markup=get_main_menu_markup(),
        parse_mode='MarkdownV2'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    bot.answer_callback_query(call.id) 

    if chat_id not in user_data:
        get_user_balance(chat_id) 
        
    main_menu_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito \(ПФ\)\. "
        "Инструмент, который помогает поднять ваше объявление на 1\-ю "
        "позицию в результатах поиска\. \n\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП\!_"
    )
    
    # Очищаем хэндлер только при навигации
    if call.data in ['back_to_main_menu', 'my_account', 'faq', 'promocodes', 'back_to_duration']:
        bot.clear_step_handler_by_chat_id(chat_id)


    if call.data == 'back_to_main_menu':
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=main_menu_text, 
                reply_markup=get_main_menu_markup(),
                parse_mode='MarkdownV2'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, main_menu_text, reply_markup=get_main_menu_markup(), parse_mode='MarkdownV2')
            
    elif call.data == 'my_account':
        # --- БЛОК ЛИЧНОГО КАБИНЕТА С ФИНАЛЬНЫМИ ИСПРАВЛЕНИЯМИ ---
        
        balance = get_user_balance(chat_id)
        referral_link = f"https://t.me/avitoup1_bot?start={chat_id}" 
        referrals_count = 0 
        
        # ⚠️ Преобразуем баланс и данные в строку и экранируем
        safe_balance = escape_markdown(str(balance)) 
        safe_referral_link = escape_markdown(referral_link) 
        safe_manager_username = escape_markdown(MANAGER_USERNAME)
        
        account_text = (
            "🚪 *Личный кабинет*\n\n"
            f"Ваш баланс: *{safe_balance}₽*\n"
            f"Ваша реферальная ссылка:\n`{safe_referral_link}`\n" 
            f"Количество рефералов: *{escape_markdown(str(referrals_count))}*\n\n"
            "Telegram\n"
            "ПФ на Авито\n"
            "Группа с новостями и остальными услугами по Авито и не только \- @avitoup\_official\n" 
            f"Связь с создателем \*\*@{safe_manager_username}\*\*"
        )
        
        safe_delete_message(chat_id, message_id)
        
        try:
            bot.send_message(
                chat_id, 
                account_text, 
                reply_markup=get_account_markup(),
                parse_mode='MarkdownV2' 
            )
        except Exception as e:
            # Запасной вариант
            bot.send_message(
                chat_id, 
                f"❌ Критическая ошибка при открытии Личного кабинета\. {escape_markdown(str(e))}",
                reply_markup=get_main_menu_markup(),
                parse_mode='MarkdownV2'
            )
        # ------------------------------------------------------------------------

    elif call.data.startswith('account_'):
        account_key = call.data.replace('account_', '')
        
        if account_key == 'deposit':
            safe_delete_message(chat_id, message_id) 
            request_deposit_amount(call.message)
            return
        
        if account_key in ['orders', 'partner']:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, f"Раздел '{escape_markdown(account_key.capitalize())}' временно недоступен или находится в разработке\.", reply_markup=get_account_markup(), parse_mode='MarkdownV2')

            
    elif call.data == 'order_review':
        safe_delete_message(chat_id, message_id)
        request_review_quantity(call.message)
        return
            
    elif call.data == 'faq':
        faq_text = "Выберите интересующий Вас раздел:"
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=faq_text, reply_markup=get_faq_markup(), parse_mode='MarkdownV2')
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, faq_text, reply_markup=get_faq_markup(), parse_mode='MarkdownV2')
            
    elif call.data.startswith('faq_'):
        topic = call.data.split('_', 1)[1]
        
        answer_text = f"Вы выбрали тему: {escape_markdown(topic)} \(здесь будет подробный ответ\)\." 
        
        if topic == 'qna':
             answer_text = "Оглавление: Вопросы и ответы\n\n1\. Как работают поведенческие факторы\n2\. Иксы на авито не работают \(Переход на пост\)\n3\. Кейсы и отзывы \(Переход на пост\)\n4\. Вопросы и ответы \(Вы здесь\)\n\nДля выбора вернитесь в предыдущее меню, нажав 'Назад'\."

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text='Назад', callback_data='faq'))
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=answer_text, reply_markup=markup, parse_mode='MarkdownV2')
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, answer_text, reply_markup=markup, parse_mode='MarkdownV2')
            
    elif call.data == 'promocodes':
        promo_text = "🎁 *Промокоды*\n\nНа данный момент активных промокодов нет\."
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_main_menu'))
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=promo_text, reply_markup=markup, parse_mode='MarkdownV2')
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, promo_text, reply_markup=markup, parse_mode='MarkdownV2')

    elif call.data == 'order_pf':
        order_text = "Выберите желаемую длительность заказа:"
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=order_text, 
                reply_markup=get_duration_markup(),
                parse_mode='MarkdownV2'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                order_text, 
                reply_markup=get_duration_markup(),
                parse_mode='MarkdownV2'
            )
        
    elif call.data.startswith('duration_'):
        duration_key = call.data.split('_')[1] 
        user_data[chat_id]['duration'] = duration_key
        
        duration_name = DURATION_NAMES.get(duration_key, 'Заказ')
        
        safe_duration_name = escape_markdown(duration_name)
        
        duration_text = f"Выбран срок: *{safe_duration_name}*\. Теперь выберите количество ПФ в день:"
        
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=duration_text, 
                reply_markup=get_pf_count_markup(duration_key),
                parse_mode='MarkdownV2'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                duration_text, 
                reply_markup=get_pf_count_markup(duration_key),
                parse_mode='MarkdownV2'
            )

    elif call.data.startswith('pf_count_'):
        pf_count = call.data.split('_')[2] 
        user_data[chat_id]['pf_count'] = pf_count
        
        safe_delete_message(chat_id, message_id)
        
        request_links(call.message)
        
    elif call.data == 'back_to_duration':
        order_text = "Выберите желаемую длительность заказа:"
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=order_text, 
                reply_markup=get_duration_markup(),
                parse_mode='MarkdownV2'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                order_text, 
                reply_markup=get_duration_markup(),
                parse_mode='MarkdownV2'
            )


# --- ОБРАБОТЧИК СООБЩЕНИЙ КЛИЕНТОВ (ОБНОВЛЕН НА MarkdownV2) ---
@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID and m.text and not m.reply_to_message)
def client_msg(m):
    user_id = m.chat.id
    username = m.from_user.username or "без\_юзернейма"
    text = m.text
    
    bot.clear_step_handler_by_chat_id(user_id)
    
    # ⚠️ Экранируем переменные
    client_username = escape_markdown(username)
    safe_user_id = escape_markdown(str(user_id))
    safe_text = escape_markdown(text)
         
    # Отправляем сообщение администратору
    bot.send_message(
        OWNER_ID,
        "📩 *СООБЩЕНИЕ ОТ КЛИЕНТА* 📩\n\n"
        f"Пользователь: @{client_username} \(ID: `{safe_user_id}`\)\n"
        f"Сообщение: {safe_text}\n\n"
        "Ответьте реплаем — клиент увидит:",
        parse_mode='MarkdownV2'
    )
    
    # Отправляем подтверждение клиенту
    bot.send_message(
        user_id, 
        "Ваше сообщение принято\! Ожидайте ответа от менеджера\. Чтобы оформить заказ, нажмите '🚀 Заказать ПФ'\.",
        reply_markup=get_main_menu_markup(),
        parse_mode='MarkdownV2'
    )


# --- ОБРАБОТЧИК ОТВЕТОВ АДМИНИСТРАТОРА (ФИНАЛЬНАЯ ВЕРСИЯ) ---
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply_text = m.reply_to_message.text
    
    try:
        # 1. Попытка найти ID клиента
        client_id_match = re.search(r'ID: [`]?(\d+)[\`]?\)', reply_text) 
        
        if not client_id_match:
             # Ищем "(ID: 123456789)"
             client_id_match = re.search(r'\(ID: (\d+)\)', reply_text) 

        client_id = 0
        if client_id_match:
            client_id = int(client_id_match.group(1))

        if client_id == 0:
            # 2. Если ID не найден, уведомляем администратора и прерываем
            bot.send_message(
                OWNER_ID, 
                "❌ *ОШИБКА: ID клиента не найден\!*\n\n"
                "Вы должны ответить реплаем на исходное уведомление о заказе/сообщении, "
                "где четко указан *ID клиента* в формате: `\(ID: 123456789\)` или `\(ID: 123456789\)`\.",
                parse_mode='MarkdownV2'
            )
            return
        
        # ⚠️ Экранируем ID клиента для админских уведомлений
        safe_client_id = escape_markdown(str(client_id))

        # --- ОБРАБОТКА КОМАНДЫ ПОПОЛНЕНИЯ БАЛАНСА ---
        if m.text and m.text.lower().startswith('/add_balance'): 
            
            parts = m.text.split()
            if len(parts) < 2:
                bot.send_message(OWNER_ID, "❌ *Ошибка\.* Не указана сумма\. Формат: `/add\_balance 1000`", parse_mode='MarkdownV2')
                return
            
            try:
                amount_str = parts[1]
                cleaned_amount_str = re.sub(r'[^\d\.]', '', amount_str.lower().replace(',', '.'))
                amount_to_add = round(float(cleaned_amount_str), 2)
                
                if amount_to_add > 0:
                    user_balances[client_id] = get_user_balance(client_id) + amount_to_add
                    new_balance = user_balances[client_id]
                    
                    # ⚠️ Экранируем суммы
                    safe_amount_to_add = escape_markdown(str(amount_to_add))
                    safe_new_balance = escape_markdown(str(new_balance))

                    # Уведомление КЛИЕНТА
                    try:
                        bot.send_message(
                            client_id, 
                            f"✅ *Баланс пополнен\!* 🎉\n\n" 
                            f"На счет зачислено *{safe_amount_to_add} ₽*\.\n"
                            f"Текущий баланс: *{safe_new_balance} ₽*\.", 
                            parse_mode='MarkdownV2',
                            reply_markup=get_main_menu_markup()
                        )
                        # Уведомление АДМИНИСТРАТОРА об успехе
                        bot.send_message(OWNER_ID, f"✅ Баланс клиента `{safe_client_id}` пополнен на {safe_amount_to_add} ₽\. Новый баланс: {safe_new_balance} ₽\.", parse_mode='MarkdownV2')
                    except Exception as client_send_e:
                        # Уведомление АДМИНИСТРАТОРА о неудаче
                        safe_error = escape_markdown(str(client_send_e))
                        bot.send_message(OWNER_ID, f"⚠️ *Баланс клиента `{safe_client_id}` пополнен в базе*, но сообщение *не отправлено* \(возможно, клиент заблокировал бота\)\. Сумма: {safe_amount_to_add} ₽\. Ошибка: `{safe_error}`", parse_mode='MarkdownV2')
                    
                    return 
                else:
                    bot.send_message(OWNER_ID, "❌ *Ошибка\.* Сумма должна быть положительной\.", parse_mode='MarkdownV2')
                    return

            except ValueError:
                bot.send_message(OWNER_ID, "❌ *Ошибка\.* Некорректный формат суммы\. Формат: `/add\_balance 1000`", parse_mode='MarkdownV2')
                return
        
        # --- ОТПРАВКА ОБЫЧНОГО ОТВЕТА ---
        try:
            # ⚠️ Экранируем текст ответа
            safe_reply_text = escape_markdown(m.text)
            
            bot.send_message(client_id, f"🧑‍💻 *Ответ менеджера:*\n\n{safe_reply_text}", parse_mode='MarkdownV2')
            bot.send_message(OWNER_ID, "✅ Ответ успешно отправлен клиенту\.", parse_mode='MarkdownV2')
        except Exception as send_e:
            safe_error = escape_markdown(str(send_e))
            bot.send_message(OWNER_ID, f"❌ *ОШИБКА ОТПРАВКИ КЛИЕНТУ* `{safe_client_id}`:\n\nНе удалось отправить ответ клиенту\. Возможно, он заблокировал бота\. Ошибка: `{safe_error}`", parse_mode='MarkdownV2')
        
    except Exception as e:
        safe_error = escape_markdown(str(e))
        safe_message = escape_markdown(m.text)
        bot.send_message(OWNER_ID, f"🚨 *КРИТИЧЕСКАЯ ОШИБКА* при обработке реплая:\n\n`{safe_error}`\n\nСообщение: {safe_message}", parse_mode='MarkdownV2')


# --- WEBHOOK И ЗАПУСК (без изменений) ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

if __name__ == '__main__':
    bot.remove_webhook()
    # ⚠️ Убедитесь, что 'your-fallback-url' заменено на ваш реальный домен
    bot.set_webhook(url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-fallback-url')}/{TOKEN}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
