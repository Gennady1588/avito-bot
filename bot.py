from flask import Flask, request
import telebot
import os
import re 

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БОТА И СЕРВЕРА ---
TOKEN = os.environ.get('TOKEN', 'YOUR_BOT_TOKEN_HERE') 
OWNER_ID = int(os.environ.get('OWNER_ID', 123456789)) 
bot = telebot.TeleBot(TOKEN)

# ИМИТАЦИЯ БАЗЫ ДАННЫХ 
user_balances = {} 
user_data = {} 

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА, КАРТЫ И ЦЕН ---
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225" 
MIN_DEPOSIT_AMOUNT = 400

# Цены и длительность (без изменений)
PRICE_50_PF_DAILY = 799 

DURATION_DAYS = {
    '1d': 1, '2d': 2, '3d': 3, 
    '5d': 5, '7d': 7, '30d': 30  
}

DURATION_NAMES = {
    '1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', 
    '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц (30 Дней)'
}

# --- ФУНКЦИИ РАСЧЕТА И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (без изменений) ---

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
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'День (от {int(price_50_1d)}₽)', callback_data='duration_1d'),
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
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'50 ПФ ({int(price_50)}₽)', callback_data='pf_count_50'),
        telebot.types.InlineKeyboardButton(text=f'100 ПФ ({int(price_100)}₽)', callback_data='pf_count_100')
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

# --- ФУНКЦИИ ОБРАБОТКИ ПОПОЛНЕНИЯ (логика deposit) ---

def request_deposit_amount(message):
    chat_id = message.chat.id
    
    deposit_request_text = (
        "💳 *Пополнить баланс*\n\n"
        f"❗️ Минимальная сумма пополнения - *{MIN_DEPOSIT_AMOUNT} ₽*\n\n"
        "Введите желаемую сумму пополнения:"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад', callback_data='back_to_main_menu')
    )
    
    sent_msg = None
    
    # ⚠️ Улучшенная логика: пытаемся редактировать, если не получилось - отправляем новое.
    # ВАЖНО: message.message_id будет только если это колбэк, а не команда /deposit
    is_callback = hasattr(message, 'message_id')
    
    if is_callback:
        try:
            sent_msg = bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=deposit_request_text,
                reply_markup=markup, 
                parse_mode='Markdown'
            )
        except Exception:
             # Если не удалось отредактировать, отправляем как новое
            sent_msg = bot.send_message(
                chat_id, 
                deposit_request_text, 
                reply_markup=markup, 
                parse_mode='Markdown'
            )
    else:
        # Если это не колбэк (например, команда), просто отправляем новое
        sent_msg = bot.send_message(
            chat_id, 
            deposit_request_text, 
            reply_markup=markup, 
            parse_mode='Markdown'
        )

    # ⚠️ КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Регистрируем хэндлер всегда, чтобы не потерять ответ
    if sent_msg:
        bot.register_next_step_handler(sent_msg, process_deposit_amount)
    else:
        # Если по какой-то причине даже send_message не сработал (редко, но возможно),
        # то регистрируем хэндлер на следующее сообщение в чате
        temp_msg = bot.send_message(
            chat_id, 
            "⚠️ Пожалуйста, введите сумму пополнения (снова).", 
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(temp_msg, process_deposit_amount)


def process_deposit_amount(message):
    chat_id = message.chat.id
    
    # Сброс при /start
    if message.text and message.text.lower().startswith('/start'):
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return
    
    if not message.text:
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода.* Пожалуйста, введите сумму только *цифрами*.",
            parse_mode='Markdown',
            reply_markup=get_account_markup()
        )
        return

    deposit_text = message.text.strip()
    amount = 0

    try:
        cleaned_text = re.sub(r'[^\d\.]', '', deposit_text.lower().replace(',', '.'))
        amount = int(float(cleaned_text))
        
        if amount < MIN_DEPOSIT_AMOUNT:
            raise ValueError("Сумма меньше минимальной")
        
    except ValueError:
        bot.send_message(
            chat_id, 
            f"🚫 *Ошибка ввода.* Пожалуйста, введите корректную сумму (минимум {MIN_DEPOSIT_AMOUNT} ₽) только цифрами (например, 500).",
            parse_mode='Markdown',
            reply_markup=get_account_markup()
        )
        return

    # --- ОТВЕТ КЛИЕНТУ (С НОМЕРОМ КАРТЫ) ---
    payment_instruction = (
        f"✅ *Ваш запрос на пополнение на {amount} ₽ принят!*\n\n"
        "Для оплаты переведите *ТОЧНО* эту сумму на карту:\n"
        f"💳 **`{YOUR_CARD_NUMBER}`**\n\n" 
        "❗️ *Обязательно переводите ТОЧНО эту сумму. Менеджер вручную "
        "проверит поступление и зачислит средства.*\n\n"
        f"Для подтверждения оплаты напишите нашему менеджеру: **@{MANAGER_USERNAME}**"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='✍️ Связаться с менеджером', url=f'https://t.me/{MANAGER_USERNAME}')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')
    )

    # --- УВЕДОМЛЕНИЕ АДМИНИСТРАТОРА ---
    deposit_summary_for_admin = (
        "💰 *ЗАПРОС НА ПОПОЛНЕНИЕ* 💰\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Желаемая сумма: *{amount} ₽*\n"
        f"Карта для проверки: `{YOUR_CARD_NUMBER}`\n\n"
        f"➡️ *Необходимо проверить поступление:* **{amount} ₽**\n"
        "Ответьте реплаем, чтобы подтвердить получение средств. Для зачисления используйте `/add_balance {сумма}`"
    )
    
    bot.send_message(
        OWNER_ID, 
        deposit_summary_for_admin, 
        parse_mode='Markdown'
    )
    
    # ГАРАНТИРОВАННАЯ ОТПРАВКА НОМЕРА КАРТЫ
    bot.send_message(
        chat_id, 
        payment_instruction,
        reply_markup=markup,
        parse_mode='Markdown'
    )


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА (без изменений) ---

def request_links(message):
    """Проверяет баланс и запрашивает ссылки, если средств достаточно."""
    chat_id = message.chat.id
    
    if 'duration' not in user_data.get(chat_id, {}) or 'pf_count' not in user_data.get(chat_id, {}):
        bot.send_message(chat_id, "❌ *Ошибка.* Данные о заказе потеряны. Начните, пожалуйста, заново.", parse_mode='Markdown', reply_markup=get_main_menu_markup())
        safe_delete_message(chat_id, getattr(message, 'message_id', None))
        return
        
    duration_key = user_data[chat_id]['duration']
    pf_count = user_data[chat_id]['pf_count']
    total_price = calculate_price(duration_key, pf_count)
    current_balance = get_user_balance(chat_id)
    duration_name = DURATION_NAMES.get(duration_key, 'N/A')
    
    if current_balance < total_price:
        required = round(total_price - current_balance, 2)
        
        insufficient_funds_text = (
            "❌ *Недостаточно средств!*\n\n"
            f"Стоимость заказа: *{int(total_price)} ₽*\n"
            f"Ваш баланс: *{current_balance} ₽*\n"
            f"Необходимо пополнить: *{required} ₽*\n\n"
            "Пожалуйста, пополните баланс в разделе 'Личный кабинет'."
        )
        
        safe_delete_message(chat_id, getattr(message, 'message_id', None)) 
        
        bot.send_message(
            chat_id, 
            insufficient_funds_text,
            reply_markup=get_account_markup(),
            parse_mode='Markdown'
        )
        user_data[chat_id]['duration'] = None
        user_data[chat_id]['pf_count'] = None
        return 
        
    final_text = (
        f"✅ *Параметры заказа выбраны*\n\n"
        f"ПФ в день: *{pf_count}*\n"
        f"Длительность: *{duration_name}*\n\n"
        "🔗 *Отправьте ссылки*\n"
        "КАЖДАЯ ССЫЛКА С НОВОЙ СТРОКИ (`CTRL+ENTER`)."
    )
    
    safe_delete_message(chat_id, getattr(message, 'message_id', None))
    
    sent_msg = bot.send_message(
        chat_id, 
        final_text, 
        parse_mode='Markdown'
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
            "🚫 *Ошибка ввода.* Пожалуйста, отправьте ссылки в виде *текста*.",
            parse_mode='Markdown'
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
        balance_status = f"*Списано {int(total_price)} ₽*. Новый баланс: *{get_user_balance(chat_id)} ₽*."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания.* Недостаточно средств или цена заказа 0 ₽. Заказ отменен."
    
    duration_text = DURATION_NAMES.get(duration_key, 'Неизвестно')
    
    # СВОДКА ДЛЯ АДМИНИСТРАТОРА (со ссылками)
    order_summary_for_admin = (
        "🔥 *НОВЫЙ ЗАКАЗ ПФ* 🔥\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Сумма заказа: *{int(total_price)} ₽*\n"
        f"Статус оплаты: {'✅ Оплачен' if paid else '❌ Не оплачен (Ошибка)'}\n"
        f"Продолжительность: *{duration_text}*\n"
        f"Количество ПФ в день: *{pf_count}*\n"
        "--- ССЫЛКИ НА ОБЪЯВЛЕНИЯ
