from flask import Flask, request
import telebot
import os
import re 

# --- КОНФИГУРАЦИЯ БОТА И СЕРВЕРА ---
# ВАЖНО: Убедитесь, что TOKEN и OWNER_ID установлены как переменные окружения
# Данные внесены по запросу пользователя:
TOKEN = '8216604919:AAFLW0fNyp97RfgPmo7zVdIe3XLtR-EJg' 
OWNER_ID = 1641571790 # ID владельца 

# Инициализация бота
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ИМИТАЦИЯ БАЗЫ ДАННЫХ (глобальные переменные для примера)
# В реальном приложении это должно быть заменено на БД (например, Redis/Postgres)
user_balances = {} 
user_data = {} 

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА, КАРТЫ И ЦЕН ---
MANAGER_USERNAME = "Hiluxe56" # Юзернейм менеджера без @
YOUR_CARD_NUMBER = "2204320348572225" # Номер карты для пополнения
MIN_DEPOSIT_AMOUNT = 400

# Цены и длительность
PRICE_50_PF_DAILY = 799 
PRICE_AVITO_REVIEW = 350 # Цена за 1 отзыв

DURATION_DAYS = {
    '1d': 1, '2d': 2, '3d': 3, 
    '5d': 5, '7d': 7, '30d': 30  
}

DURATION_NAMES = {
    '1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', 
    '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц (30 Дней)'
}

# --- НОВЫЙ РЕГУЛЯРНЫЙ ШАБЛОН ДЛЯ ПОИСКА ID ---
# Добавлен более универсальный шаблон, который ищет ID в разных форматах сообщений
ID_REGEX = re.compile(r'ID: `?(\d+)`?') 


# --- ФУНКЦИИ РАСЧЕТА И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

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

# --- ФУНКЦИИ КЛАВИАТУР (Markup functions) ---

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
    
def get_duration_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text=DURATION_NAMES['1d'], callback_data='duration_1d'),
        telebot.types.InlineKeyboardButton(text=DURATION_NAMES['3d'], callback_data='duration_3d'),
        telebot.types.InlineKeyboardButton(text=DURATION_NAMES['7d'], callback_data='duration_7d')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text=DURATION_NAMES['30d'], callback_data='duration_30d')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')
    )
    return markup

def get_pf_count_markup(duration_key):
    total_price_50 = calculate_price(duration_key, 50)
    total_price_100 = calculate_price(duration_key, 100)
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'50 ПФ ({int(total_price_50)} ₽)', callback_data='pf_count_50')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'100 ПФ ({int(total_price_100)} ₽)', callback_data='pf_count_100')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад к сроку', callback_data='back_to_duration')
    )
    return markup

def get_deposit_cancel_markup():
    """Отдельная кнопка отмены для пошаговых функций."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад в меню', callback_data='back_to_main_menu')
    )
    return markup
    
def get_faq_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='Как работают ПФ?', url='https://t.me/Avitounlock/2'),
        telebot.types.InlineKeyboardButton(text='Иксы не работают!', url='https://t.me/Avitounlock/1')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Кейсы и отзывы', url='https://t.me/Avitounlock/12'),
        telebot.types.InlineKeyboardButton(text='Вопросы и ответы', callback_data='faq_qna')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu')
    )
    return markup

# --- ФУНКЦИИ ОБРАБОТКИ ПОПОЛНЕНИЯ (логика deposit) ---

def request_deposit_amount(message):
    """Запрашивает сумму пополнения."""
    chat_id = message.chat.id
    
    # 1. Удаляем сообщение, которое инициировало этот запрос (например, кнопку "Пополнить")
    safe_delete_message(chat_id, message.message_id) 
    
    # 2. Очищаем предыдущий хэндлер, чтобы не было конфликтов
    bot.clear_step_handler_by_chat_id(chat_id) 

    deposit_request_text = (
        "💳 *Пополнить баланс*\n\n"
        f"❗️ Минимальная сумма пополнения - *{MIN_DEPOSIT_AMOUNT} ₽* \n\n"
        "Введите желаемую сумму пополнения:"
    )
    
    # 3. Отправляем новое сообщение, на которое будет зарегистрирован хэндлер
    sent_msg = bot.send_message(
        chat_id, 
        deposit_request_text, 
        reply_markup=get_deposit_cancel_markup(), # Используем новую кнопку отмены
        parse_mode='Markdown'
    )
    
    # 4. Регистрируем хэндлер
    bot.register_next_step_handler(sent_msg, process_deposit_amount, sent_msg.message_id)


def process_deposit_amount(message, prompt_message_id):
    """Обрабатывает введенную сумму пополнения."""
    chat_id = message.chat.id
    
    # 1. Сброс, если ввели /start или другую команду
    if message.text and message.text.lower().startswith(('/', 'отмена', 'назад')):
        # Удаляем введенную команду и старое приглашение
        safe_delete_message(chat_id, message.message_id)
        safe_delete_message(chat_id, prompt_message_id)
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return
        
    # 2. Удаляем введенную сумму
    safe_delete_message(chat_id, message.message_id) 
    
    if not message.text:
        # Если пришел не текст (например, стикер), просто игнорируем его
        return
        
    deposit_text = message.text.strip()
    amount = 0

    try:
        # Чистим ввод от лишних символов и переводим в int
        cleaned_text = re.sub(r'[^\d\.]', '', deposit_text.lower().replace(',', '.'))
        amount = int(float(cleaned_text))
        
        if amount < MIN_DEPOSIT_AMOUNT:
            raise ValueError("Сумма меньше минимальной")
        
    except ValueError:
        # 3. Обработка неверного ввода
        error_text = f"🚫 *Ошибка ввода.* Пожалуйста, введите корректную сумму (минимум {MIN_DEPOSIT_AMOUNT} ₽) только *цифрами* (например, 500)."
        
        # Редактируем старое сообщение-подсказку, чтобы не засорять чат, или отправляем новое
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=prompt_message_id,
                text=error_text,
                reply_markup=get_deposit_cancel_markup(),
                parse_mode='Markdown'
            )
            # Повторно регистрируем хэндлер на отредактированное сообщение
            bot.register_next_step_handler(message, process_deposit_amount, prompt_message_id)
        except Exception:
            # Если не смогли отредактировать, отправляем новое сообщение
            bot.send_message(chat_id, error_text, parse_mode='Markdown')
            new_prompt_msg = bot.send_message(
                chat_id, 
                "Введите желаемую сумму пополнения:", 
                reply_markup=get_deposit_cancel_markup()
            )
            bot.register_next_step_handler(new_prompt_msg, process_deposit_amount, new_prompt_msg.message_id)
            
        return

    # 4. Успешный ввод: удаляем приглашение и отправляем инструкцию
    safe_delete_message(chat_id, prompt_message_id)
    
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

    deposit_summary_for_admin = (
        "💰 *ЗАПРОС НА ПОПОЛНЕНИЕ* 💰\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Желаемая сумма: *{amount} ₽*\n"
        f"Карта для проверки: `{YOUR_CARD_NUMBER}`\n\n"
        f"➡️ *Необходимо проверить поступление:* **{amount} ₽**\n"
        "Для зачисления баланса используйте: `/add_balance {сумма}`"
    )
    
    try:
        bot.send_message(
            OWNER_ID, 
            deposit_summary_for_admin, 
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"Error sending admin deposit notification for chat {chat_id}: {e}") 
    
    try:
        bot.send_message(
            chat_id, 
            payment_instruction,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception:
        fallback_text = (
            f"❌ Критическая ошибка. Номер карты для перевода: {YOUR_CARD_NUMBER}. "
            f"Свяжитесь с менеджером @{MANAGER_USERNAME}."
        )
        bot.send_message(chat_id, fallback_text)


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА ПФ ---

def request_links(message):
    """Проверяет баланс и запрашивает ссылки, если средств достаточно."""
    chat_id = message.chat.id
    
    # 1. Проверка наличия данных о заказе
    if chat_id not in user_data or 'duration' not in user_data[chat_id] or 'pf_count' not in user_data[chat_id]:
        # Если пришел колбэк, удаляем его
        safe_delete_message(chat_id, getattr(message, 'message_id', None))
        bot.send_message(chat_id, "❌ *Ошибка.* Данные о заказе потеряны. Начните, пожалуйста, заново.", parse_mode='Markdown', reply_markup=get_main_menu_markup())
        return
        
    duration_key = user_data[chat_id]['duration']
    pf_count = user_data[chat_id]['pf_count']
    total_price = calculate_price(duration_key, pf_count)
    current_balance = get_user_balance(chat_id)
    duration_name = DURATION_NAMES.get(duration_key, 'N/A')
    
    # 2. Проверка баланса
    if current_balance < total_price:
        required = round(total_price - current_balance, 2)
        
        insufficient_funds_text = (
            "❌ *Недостаточно средств!*\n\n"
            f"Стоимость заказа: *{int(total_price)} ₽*\n"
            f"Ваш баланс: *{current_balance} ₽*\n"
            f"Необходимо пополнить: *{required} ₽*\n\n"
            "Пожалуйста, пополните баланс в разделе 'Личный кабинет'."
        )
        
        # Удаляем сообщение, которое инициировало этот запрос
        safe_delete_message(chat_id, getattr(message, 'message_id', None)) 
        
        bot.send_message(
            chat_id, 
            insufficient_funds_text,
            reply_markup=get_account_markup(),
            parse_mode='Markdown'
        )
        # Очищаем временные данные о заказе
        user_data[chat_id]['duration'] = None
        user_data[chat_id]['pf_count'] = None
        return 
        
    # 3. Запрос ссылок
    final_text = (
        f"✅ *Параметры заказа выбраны*\n\n"
        f"ПФ в день: *{pf_count}*\n"
        f"Длительность: *{duration_name}*\n"
        f"Сумма к оплате: *{int(total_price)} ₽*\n\n"
        "🔗 *Отправьте ссылки*\n"
        "КАЖДАЯ ССЫЛКА С НОВОЙ СТРОКИ (`CTRL+ENTER`)."
    )
    
    # Удаляем сообщение, которое инициировало этот запрос
    safe_delete_message(chat_id, getattr(message, 'message_id', None))
    
    bot.clear_step_handler_by_chat_id(chat_id)
    
    sent_msg = bot.send_message(
        chat_id, 
        final_text, 
        parse_mode='Markdown',
        reply_markup=get_deposit_cancel_markup()
    )
    
    # Регистрируем хэндлер с ID сообщения-приглашения
    bot.register_next_step_handler(sent_msg, process_links_and_send_order, sent_msg.message_id)


def process_links_and_send_order(message, prompt_message_id):
    """Обрабатывает ссылки, списывает баланс и отправляет заказ админу."""
    chat_id = message.chat.id
    
    # 1. Обработка сброса
    if message.text and message.text.lower().startswith(('/', 'отмена', 'назад')):
        safe_delete_message(chat_id, message.message_id)
        safe_delete_message(chat_id, prompt_message_id)
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return
    
    # 2. Проверка ввода
    if not message.text:
        safe_delete_message(chat_id, message.message_id)
        
        # Редактируем старое сообщение для повторного запроса
        error_text = "🚫 *Ошибка ввода.* Пожалуйста, отправьте ссылки в виде *текста*.\n\n" + message.text
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=prompt_message_id,
                text=error_text,
                reply_markup=get_deposit_cancel_markup(),
                parse_mode='Markdown'
            )
            # Повторно регистрируем хэндлер на отредактированное сообщение
            bot.register_next_step_handler(message, process_links_and_send_order, prompt_message_id)
        except Exception:
            bot.send_message(chat_id, "Пожалуйста, отправьте ссылки в виде *текста*.", parse_mode='Markdown')
            new_prompt_msg = bot.send_message(chat_id, "🔗 *Отправьте ссылки*", reply_markup=get_deposit_cancel_markup())
            bot.register_next_step_handler(new_prompt_msg, process_links_and_send_order, new_prompt_msg.message_id)

        return
    
    # 3. Финализация заказа
    links = message.text
    safe_delete_message(chat_id, message.message_id)
    safe_delete_message(chat_id, prompt_message_id)
    
    duration_key = user_data[chat_id].get('duration', 'N/A')
    pf_count = user_data[chat_id].get('pf_count', 0)
    total_price = calculate_price(duration_key, pf_count)
    
    paid = False
    balance_status = ""
    
    # Списание средств
    if get_user_balance(chat_id) >= total_price and total_price > 0:
        user_balances[chat_id] -= total_price
        user_balances[chat_id] = round(user_balances[chat_id], 2)
        balance_status = f"*Списано {int(total_price)} ₽*. Новый баланс: *{get_user_balance(chat_id)} ₽*."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания.* Недостаточно средств или цена заказа 0 ₽."
    
    duration_text = DURATION_NAMES.get(duration_key, 'Неизвестно')
    
    # 4. Отправка админу
    order_summary_for_admin = (
        "🔥 *НОВЫЙ ЗАКАЗ ПФ* 🔥\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Сумма заказа: *{int(total_price)} ₽*\n"
        f"Статус оплаты: {'✅ Оплачен' if paid else '❌ Не оплачен (Ошибка)'}\n"
        f"Продолжительность: *{duration_text}*\n"
        f"Количество ПФ в день: *{pf_count}*\n"
        "--- ССЫЛКИ НА ОБЪЯВЛЕНИЯ ---\n"
        f"{links}\n"
        "------------------------------\n"
        "Для ответа клиенту используйте реплай на это сообщение."
    )
    
    try:
        bot.send_message(OWNER_ID, order_summary_for_admin, parse_mode='Markdown')
    except Exception as e:
        print(f"Error sending PF order to admin: {e}")
    
    # 5. Ответ клиенту
    if paid:
        confirmation_text = (
            f"✅ *Ваш заказ принят и оплачен!*\n\n" 
            f"Стоимость: *{int(total_price)} ₽*. {balance_status}\n\n"
            "Менеджер проверит ссылки и, в случае успеха, заказ будет запущен. "
            "Вам придет оповещение о запуске.\n\n"
            "⏳ *Ожидайте...*"
        )
    else:
        confirmation_text = (
            "❌ *Заказ отменен из-за нехватки средств или ошибки.*\n\n"
            "Пожалуйста, пополните баланс и повторите заказ."
        )
    
    bot.send_message(
        chat_id, 
        confirmation_text,
        reply_markup=get_main_menu_markup(),
        parse_mode='Markdown'
    )
    
    # 6. Очистка временных данных
    user_data[chat_id]['duration'] = None
    user_data[chat_id]['pf_count'] = None


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА ОТЗЫВА ---

def request_review_quantity(message):
    """Шаг 1: Запрашивает количество отзывов."""
    chat_id = message.chat.id
    
    safe_delete_message(chat_id, message.message_id) 
    bot.clear_step_handler_by_chat_id(chat_id) 

    review_request_text = (
        "⭐ *Заказ отзыва на Авито*\n\n"
        f"Цена за 1 отзыв: *{PRICE_AVITO_REVIEW} ₽*.\n"
        "Введите желаемое *количество* отзывов (от 1 шт):"
    )
    
    sent_msg = bot.send_message(
        chat_id, 
        review_request_text, 
        reply_markup=get_deposit_cancel_markup(), 
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(sent_msg, process_review_quantity, sent_msg.message_id)


def process_review_quantity(message, prompt_message_id):
    """Шаг 2: Обрабатывает количество, проверяет баланс и переходит к деталям."""
    chat_id = message.chat.id
    
    # 1. Обработка сброса
    if message.text and message.text.lower().startswith(('/', 'отмена', 'назад')):
        safe_delete_message(chat_id, message.message_id)
        safe_delete_message(chat_id, prompt_message_id)
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return

    safe_delete_message(chat_id, message.message_id) 
    
    if not message.text:
        return

    review_count_text = message.text.strip()
    count = 0

    try:
        cleaned_text = re.sub(r'[^\d]', '', review_count_text)
        count = int(cleaned_text)
        
        if count < 1:
            raise ValueError("Количество меньше минимального")
        
    except ValueError:
        error_text = f"🚫 *Ошибка ввода.* Пожалуйста, введите корректное количество отзывов (минимум 1)."
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=prompt_message_id,
                text=error_text,
                reply_markup=get_deposit_cancel_markup(),
                parse_mode='Markdown'
            )
            bot.register_next_step_handler(message, process_review_quantity, prompt_message_id)
        except Exception:
            bot.send_message(chat_id, error_text, parse_mode='Markdown')
            new_prompt_msg = bot.send_message(
                chat_id, 
                "Введите желаемое *количество* отзывов (от 1 шт):", 
                reply_markup=get_deposit_cancel_markup()
            )
            bot.register_next_step_handler(new_prompt_msg, process_review_quantity, new_prompt_msg.message_id)
        return

    # 2. Расчет цены
    total_price = count * PRICE_AVITO_REVIEW
    current_balance = get_user_balance(chat_id)
    
    # 3. Проверка баланса
    if current_balance < total_price:
        safe_delete_message(chat_id, prompt_message_id)
        required = round(total_price - current_balance, 2)
        
        insufficient_funds_text = (
            "❌ *Недостаточно средств!*\n\n"
            f"Стоимость {count} отзывов: *{int(total_price)} ₽*\n"
            f"Ваш баланс: *{current_balance} ₽*\n"
            f"Необходимо пополнить: *{required} ₽*\n\n"
            "Пожалуйста, пополните баланс в разделе 'Личный кабинет'."
        )
        
        bot.send_message(
            chat_id, 
            insufficient_funds_text,
            reply_markup=get_account_markup(),
            parse_mode='Markdown'
        )
        return

    # 4. Сохраняем данные и переходим к деталям
    safe_delete_message(chat_id, prompt_message_id)
    user_data[chat_id]['review_count'] = count
    user_data[chat_id]['review_price'] = total_price
    
    request_review_details(chat_id, count, total_price)


def request_review_details(chat_id, count, price):
    """Шаг 3: Запрашивает ссылку и текст отзыва."""
    
    bot.clear_step_handler_by_chat_id(chat_id)
    
    details_request_text = (
        f"✅ *Заказ {count} отзыв(а/ов) на {price} ₽*\n\n"
        "Отправьте следующую информацию *одним* сообщением:\n\n"
        "1. *Ссылка* на профиль Авито, куда нужно добавить отзыв.\n"
        "2. *Текст* отзыва (или тексты, если их несколько, разделенные пустой строкой).\n\n"
        "🔗 *Формат сообщения:*\n"
        "`[Ссылка на профиль]`\n"
        "`[Текст отзыва 1]`\n"
        "`[Текст отзыва 2 (если есть)]`"
    )
    
    sent_msg = bot.send_message(
        chat_id, 
        details_request_text, 
        reply_markup=get_deposit_cancel_markup(), 
        parse_mode='Markdown'
    )
    
    bot.register_next_step_handler(sent_msg, process_review_order, sent_msg.message_id)


def process_review_order(message, prompt_message_id):
    """Шаг 4: Финализация заказа отзыва, списание и отправка админу."""
    chat_id = message.chat.id
    
    # 1. Обработка сброса
    if message.text and message.text.lower().startswith(('/', 'отмена', 'назад')):
        safe_delete_message(chat_id, message.message_id)
        safe_delete_message(chat_id, prompt_message_id)
        bot.clear_step_handler_by_chat_id(chat_id)
        start(message)
        return
    
    # 2. Проверка ввода
    if not message.text:
        safe_delete_message(chat_id, message.message_id)
        # Отправляем в главное меню
        bot.send_message(chat_id, "🚫 *Ошибка ввода.* Заказ отменен. Пожалуйста, попробуйте заказать отзыв снова.", parse_mode='Markdown', reply_markup=get_main_menu_markup())
        return
        
    safe_delete_message(chat_id, message.message_id)
    safe_delete_message(chat_id, prompt_message_id)
    
    review_details = message.text
    count = user_data[chat_id].get('review_count', 0)
    total_price = user_data[chat_id].get('review_price', 0)

    paid = False
    balance_status = ""
    
    # 3. Списание средств
    if get_user_balance(chat_id) >= total_price and total_price > 0:
        user_balances[chat_id] -= total_price
        user_balances[chat_id] = round(user_balances[chat_id], 2)
        balance_status = f"*Списано {int(total_price)} ₽*. Новый баланс: *{get_user_balance(chat_id)} ₽*."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания.* Недостаточно средств или цена заказа 0 ₽."

    # 4. Отправка админу
    order_summary_for_admin = (
        "⭐ *НОВЫЙ ЗАКАЗ ОТЗЫВА НА АВИТО* ⭐\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Сумма заказа: *{int(total_price)} ₽*\n"
        f"Статус оплаты: {'✅ Оплачен' if paid else '❌ Не оплачен (Ошибка)'}\n"
        f"Количество отзывов: *{count}*\n"
        "--- ДЕТАЛИ ЗАКАЗА ---\n"
        f"{review_details}\n"
        "------------------------------\n"
        "Для ответа клиенту используйте реплай на это сообщение."
    )
    
    try:
        bot.send_message(OWNER_ID, order_summary_for_admin, parse_mode='Markdown')
    except Exception as e:
        print(f"Error sending review order to admin: {e}")
    
    # 5. Ответ клиенту
    if paid:
        confirmation_text = (
            f"✅ *Ваш заказ на отзыв(ы) принят и оплачен!*\n\n" 
            f"Стоимость: *{int(total_price)} ₽*. {balance_status}\n\n"
            "Менеджер проверит детали и запустит выполнение. Вам придет оповещение о завершении.\n\n"
            "⏳ *Ожидайте...*"
        )
    else:
        confirmation_text = (
            "❌ *Заказ отменен из-за нехватки средств или ошибки.*\n\n"
            "Пожалуйста, пополните баланс и повторите заказ."
        )
    
    bot.send_message(
        chat_id, 
        confirmation_text,
        reply_markup=get_main_menu_markup(),
        parse_mode='Markdown'
    )
    
    # 6. Очистка данных
    if 'review_count' in user_data.get(chat_id, {}): del user_data[chat_id]['review_count']
    if 'review_price' in user_data.get(chat_id, {}): del user_data[chat_id]['review_price']


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.chat.id
    get_user_balance(user_id) 
    
    # Обязательно очищаем все активные Step Handlers
    bot.clear_step_handler_by_chat_id(user_id)
    
    message_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito (ПФ) — это "
        "инструмент, который помогает поднять ваше объявление на 1-ю "
        "позицию в результатах поиска... \n\n"
        "В **Avitounlock** мы уже более 4 лет помогаем тысячам клиентам... "
        "Наша репутация основана на реальных отзывах — на данный момент их уже более 2750+ ‼️\n"
        "Ознакомьтесь с ними в нашем [Телеграм канале](https://t.me/Avitounlock) ✅ "
        "и убедитесь в качестве нашей работы!\n"
        "* Полное соблюдение правил Авито! Безопасно и надежно!\n"
        "* Круглосуточная работа! Наш бот работает 24/7, не пропускайте ни одной "
        "возможности продвинуть объявления! 🤖\n\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП!_"
    )
    
    hide_keyboard = telebot.types.ReplyKeyboardRemove()
    
    # Отправляем два сообщения: первое с текстом, второе с меню
    bot.send_message(
        user_id, 
        message_text, 
        reply_markup=hide_keyboard, 
        parse_mode='Markdown'
    )
    
    bot.send_message(
        user_id,
        "Выберите действие:",
        reply_markup=get_main_menu_markup(),
        parse_mode='Markdown'
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
        "🚀 Мы работаем с Поведенческими Факторами на Avito (ПФ)... (текст сокращен) ...\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП!_"
    )
    
    # Очищаем хэндлер при навигации по меню
    if call.data in ['back_to_main_menu', 'my_account', 'faq', 'promocodes', 'back_to_duration']:
        bot.clear_step_handler_by_chat_id(chat_id)

    # --- Навигация и меню ---
    if call.data == 'back_to_main_menu':
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=main_menu_text, 
                reply_markup=get_main_menu_markup(),
                parse_mode='Markdown'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, main_menu_text, reply_markup=get_main_menu_markup(), parse_mode='Markdown')
            
    elif call.data == 'my_account':
        balance = get_user_balance(chat_id)
        referral_link = f"https://t.me/avitoup1_bot?start={chat_id}" 
        referrals_count = 0 
        
        account_text = (
            "🚪 *Личный кабинет*\n\n"
            f"Ваш баланс: *{balance}₽* \n"
            f"Ваша реферальная ссылка: `{referral_link}`\n"
            f"Количество рефералов: *{referrals_count}*\n\n"
            "Telegram\n"
            "ПФ на Авито\n"
            "Группа с новостями и остальными услугами по Авито и не только - @avitoup_official\n"
            "Связь с создателем **@Avitounlock**"
        )
        
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=account_text,
                reply_markup=get_account_markup(),
                parse_mode='Markdown'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                account_text, 
                reply_markup=get_account_markup(),
                parse_mode='Markdown'
            )

    # --- Обработка аккаунта ---
    elif call.data.startswith('account_'):
        account_key = call.data.replace('account_', '')
        
        if account_key == 'deposit':
            # Сразу вызываем функцию запроса суммы
            request_deposit_amount(call.message)
            return
        
        if account_key in ['orders', 'partner']:
            # Удаляем старое меню и отправляем новое сообщение
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, f"Раздел '{account_key.capitalize()}' временно недоступен или находится в разработке.", reply_markup=get_account_markup())
            
    # --- Заказ отзыва ---
    elif call.data == 'order_review':
        # Сразу вызываем функцию запроса количества
        request_review_quantity(call.message)
        return
            
    # --- Заказ ПФ (выбор длительности) ---
    elif call.data == 'order_pf':
        order_text = "Выберите желаемую длительность заказа:"
        # Очистка старых данных о заказе, если они есть
        user_data[chat_id]['duration'] = None
        user_data[chat_id]['pf_count'] = None

        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=order_text, 
                reply_markup=get_duration_markup()
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                order_text, 
                reply_markup=get_duration_markup()
            )
        
    # --- Заказ ПФ (сохранение длительности и выбор количества) ---
    elif call.data.startswith('duration_'):
        duration_key = call.data.split('_')[1] 
        user_data[chat_id]['duration'] = duration_key
        
        duration_name = DURATION_NAMES.get(duration_key, 'Заказ')
        
        duration_text = f"Выбран срок: *{duration_name}*. Теперь выберите количество ПФ в день:"
        
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=duration_text, 
                reply_markup=get_pf_count_markup(duration_key),
                parse_mode='Markdown'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                duration_text, 
                reply_markup=get_pf_count_markup(duration_key),
                parse_mode='Markdown'
            )

    # --- Заказ ПФ (сохранение количества и переход к ссылке) ---
    elif call.data.startswith('pf_count_'):
        pf_count = call.data.split('_')[2] 
        user_data[chat_id]['pf_count'] = pf_count
        
        request_links(call.message)
        
    # --- Возврат к выбору длительности ---
    elif call.data == 'back_to_duration':
        user_data[chat_id]['duration'] = None
        user_data[chat_id]['pf_count'] = None
        order_text = "Выберите желаемую длительность заказа:"
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=order_text, 
                reply_markup=get_duration_markup()
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                order_text, 
                reply_markup=get_duration_markup()
            )
            
    # --- FAQ / Промокоды (старая логика сохранена) ---
    elif call.data == 'faq':
        faq_text = "Выберите интересующий Вас раздел:"
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=faq_text, reply_markup=get_faq_markup())
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, faq_text, reply_markup=get_faq_markup())
            
    elif call.data.startswith('faq_'):
        topic = call.data.split('_', 1)[1]
        
        answer_text = f"Вы выбрали тему: {topic} (здесь будет подробный ответ)." 
        
        if topic == 'qna':
             answer_text = "Оглавление: Вопросы и ответы\n\n1. Как работают поведенческие факторы\n2. Иксы на авито не работают (Переход на пост)\n3. Кейсы и отзывы (Переход на пост)\n4. Вопросы и ответы (Вы здесь)\n\nДля выбора вернитесь в предыдущее меню, нажав 'Назад'."

        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text='Назад', callback_data='faq'))
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=answer_text, reply_markup=markup, parse_mode='Markdown')
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, answer_text, reply_markup=markup, parse_mode='Markdown')
            
    elif call.data == 'promocodes':
        promo_text = "🎁 *Промокоды*\n\nНа данный момент активных промокодов нет."
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_main_menu'))
        
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=promo_text, reply_markup=markup, parse_mode='Markdown')
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, promo_text, reply_markup=markup, parse_mode='Markdown')


# --- ОБРАБОТЧИК СООБЩЕНИЙ КЛИЕНТОВ (для вопросов) ---
@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID and m.text and not m.reply_to_message)
def client_msg(m):
    user_id = m.chat.id
    username = m.from_user.username or "без_юзернейма"
    text = m.text
    
    # Сбрасываем все активные пошаговые обработчики, если пришло произвольное сообщение
    bot.clear_step_handler_by_chat_id(user_id)
    
    bot.send_message(
        OWNER_ID,
        f"📩 *СООБЩЕНИЕ ОТ КЛИЕНТА* 📩\n\n"
        f"Пользователь: @{username} (ID: `{user_id}`)\n"
        f"Сообщение: {text}\n\n"
        "Ответьте реплаем — клиент увидит:",
        parse_mode='Markdown'
    )
    
    bot.send_message(
        user_id, 
        "Ваше сообщение принято! Ожидайте ответа от менеджера. Чтобы оформить заказ, нажмите '🚀 Заказать ПФ'.",
        reply_markup=get_main_menu_markup()
    )


# --- ОБРАБОТЧИК ОТВЕТОВ АДМИНИСТРАТОРА (УСИЛЕННЫЙ И ИСПРАВЛЕННЫЙ) ---
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply_text = m.reply_to_message.text
    
    try:
        # ИСПРАВЛЕНИЕ: Использование универсального шаблона ID_REGEX, который ищет ID в разных форматах
        client_id_match = ID_REGEX.search(reply_text)
        client_id = 0
        if client_id_match:
            client_id = int(client_id_match.group(1)) # Группа 1 - это сам ID

        if client_id == 0:
            bot.send_message(
                OWNER_ID, 
                "❌ *ОШИБКА: ID клиента не найден!* Убедитесь, что отвечаете на оригинальное сообщение, содержащее ID клиента в формате `ID: 123456`.",
                parse_mode='Markdown'
            )
            return

        # 2. Обработка команды пополнения баланса
        if m.text and m.text.lower().startswith('/add_balance'): 
            
            parts = m.text.split()
            if len(parts) < 2:
                bot.send_message(OWNER_ID, "❌ *Ошибка.* Не указана сумма. Формат: `/add_balance 1000`", parse_mode='Markdown')
                return
            
            try:
                amount_str = parts[1]
                cleaned_amount_str = re.sub(r'[^\d\.]', '', amount_str.lower().replace(',', '.'))
                amount_to_add = round(float(cleaned_amount_str), 2)
                
                if amount_to_add > 0:
                    user_balances[client_id] = get_user_balance(client_id) + amount_to_add
                    new_balance = user_balances[client_id]
                    
                    # Уведомление КЛИЕНТА
                    bot.send_message(
                        client_id, 
                        f"✅ *Баланс пополнен!* 🎉\n\n" 
                        f"На счет зачислено *{amount_to_add} ₽*.\n"
                        f"Текущий баланс: *{new_balance} ₽*.", 
                        parse_mode='Markdown',
                        reply_markup=get_main_menu_markup()
                    )
                    # Уведомление АДМИНИСТРАТОРА
                    bot.send_message(OWNER_ID, f"✅ Баланс клиента {client_id} пополнен на {amount_to_add} ₽. Новый баланс: {new_balance} ₽.")
                    return 
                else:
                    bot.send_message(OWNER_ID, "❌ *Ошибка.* Сумма должна быть положительной.", parse_mode='Markdown')
                    return

            except ValueError:
                bot.send_message(OWNER_ID, "❌ *Ошибка.* Некорректный формат суммы. Формат: `/add_balance 1000`", parse_mode='Markdown')
                return
        
        # 3. Отправка обычного ответа
        # ИСПРАВЛЕНИЕ: Используем HTML-теги для форматирования ответа менеджера. 
        # Это более надежно, чем Markdown вложенный в другой Markdown, и сохраняет переводы строк.
        
        # Экранируем специальные символы HTML, чтобы не сломать разметку, если текст содержит <, >, &
        from html import escape
        safe_admin_text = escape(m.text) 
        
        response_to_client = f"🧑‍💻 <b>Ответ менеджера:</b>\n\n{safe_admin_text}"
        
        try:
            bot.send_message(client_id, response_to_client, parse_mode='HTML')
            bot.send_message(OWNER_ID, "✅ Ответ успешно отправлен клиенту.")
        except Exception as send_e:
            # Если отправка с HTML не удалась, пробуем отправить как обычный текст
            try:
                 bot.send_message(client_id, f"🧑‍💻 Ответ менеджера:\n\n{m.text}")
                 bot.send_message(OWNER_ID, "⚠️ Ответ отправлен клиенту как обычный текст из-за ошибки форматирования.")
            except Exception as fallback_e:
                 bot.send_message(OWNER_ID, f"❌ *КРИТИЧЕСКАЯ ОШИБКА ОТПРАВКИ КЛИЕНТУ* `{client_id}`:\n\nНе удалось отправить ответ клиенту. Ошибка: `{send_e}` / `{fallback_e}`", parse_mode='Markdown')

        
    except Exception as e:
        bot.send_message(OWNER_ID, f"🚨 *КРИТИЧЕСКАЯ ОШИБКА* при обработке реплая:\n\n`{e}`\n\nСообщение: {m.text}", parse_mode='Markdown')


# --- WEBHOOK И ЗАПУСК (Обязательный блок для Flask) ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    # Проверяем, что запрос пришел не от Flask
    if request.headers.get('content-type') == 'application/json':
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return 'OK', 200
        except Exception as e:
            print(f"Webhook processing error: {e}")
            return 'BAD REQUEST', 400
    return 'NOT JSON', 403

if __name__ == '__main__':
    # Эта часть запускается, если вы запускаете файл локально для тестирования
    # В облачной среде (Render) она обычно не используется, там используется gunicorn/uwsgi
    # Для локального тестирования можно использовать режим Polling, закомментировав блок app.run
    print("Starting bot in local polling mode (for debugging)...")
    bot.remove_webhook()
    bot.infinity_polling()

# Если вы деплоите на платформу с вебхуками (например, Render), вам нужно, чтобы этот блок выполнялся:
# if __name__ == '__main__':
#     # Устанавливаем вебхук при запуске
#     WEBHOOK_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'your-fallback-url')}/{TOKEN}"
#     bot.remove_webhook()
#     bot.set_webhook(url=WEBHOOK_URL)
#     # Запускаем Flask
#     app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
