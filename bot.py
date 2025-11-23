from flask import Flask, request
import telebot
import os
import re 

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БОТА И СЕРВЕРА ---
TOKEN = os.environ['TOKEN']
OWNER_ID = int(os.environ['OWNER_ID'])
bot = telebot.TeleBot(TOKEN)

# ИМИТАЦИЯ БАЗЫ ДАННЫХ 
user_balances = {} 
user_data = {} 

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА, КАРТЫ И ЦЕН ---
MANAGER_USERNAME = "Hiluxe56"
# !!! ВАША КАРТА !!!
YOUR_CARD_NUMBER = "2204320348572225" 
MIN_DEPOSIT_AMOUNT = 400

# !!! ИСПРАВЛЕНИЕ ЛОГИКИ ЦЕНЫ !!!
# Базовая цена 50 ПФ за 1 день. Цена 100 ПФ будет в два раза больше.
PRICE_50_PF_DAILY = 799 

# Дни для расчета
DURATION_DAYS = {
    '1d': 1,   
    '2d': 2,   
    '3d': 3,   
    '5d': 5,   
    '7d': 7,   
    '30d': 30  
}

# Имена для отображения
DURATION_NAMES = {
    '1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', 
    '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц (30 Дней)'
}

# --- ФУНКЦИИ РАСЧЕТА СТОИМОСТИ ---

def calculate_price(duration_key, pf_count):
    """
    Рассчитывает общую стоимость заказа без скидок.
    Цена = (Базовая цена за ПФ) * (Количество Дней).
    """
    
    try:
        pf_count = int(pf_count)
        days = DURATION_DAYS.get(duration_key, 1)
    except ValueError:
        return 0.0
        
    # Базовая цена за 1 день работы с выбранным количеством ПФ
    if pf_count == 50:
        daily_cost = PRICE_50_PF_DAILY
    elif pf_count == 100:
        daily_cost = PRICE_50_PF_DAILY * 2 # 1598 руб.
    else:
        # Для других значений ПФ, если они появятся
        return 0.0 
    
    # Общая стоимость
    total_price = daily_cost * days
    
    return round(total_price, 0) # Округляем до целого рубля

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
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

# --- ФУНКЦИИ КЛАВИАТУР ---

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

def get_duration_markup(pf_count='50'):
    # На этом шаге показываем только базовую цену за 1 день, 
    # так как цена зависит от ПФ (50 или 100), который еще не выбран.
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
    # Цены рассчитаны и отображаются на кнопках выбора ПФ
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
    # ДОБАВЛЕНИЕ КНОПКИ ОТМЕНЫ ПРЯМО НА ШАГЕ ЗАПРОСА СУММЫ
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад', callback_data='back_to_main_menu')
    )
    
    sent_msg = None
    try:
        # Пытаемся отредактировать сообщение (если это колбэк)
        if hasattr(message, 'message_id'):
            sent_msg = bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=deposit_request_text,
                reply_markup=markup, # Добавил сюда клавиатуру
                parse_mode='Markdown'
            )
        else:
            # Если это обычное сообщение (менее вероятно, но для страховки)
            safe_delete_message(chat_id, getattr(message, 'message_id', None))
            sent_msg = bot.send_message(
                chat_id, 
                deposit_request_text, 
                reply_markup=markup, # Добавил сюда клавиатуру
                parse_mode='Markdown'
            )
    except Exception:
        # Если редактирование не удалось, удаляем старое и отправляем новое
        safe_delete_message(chat_id, getattr(message, 'message_id', None))
        sent_msg = bot.send_message(
            chat_id, 
            deposit_request_text, 
            reply_markup=markup, # Добавил сюда клавиатуру
            parse_mode='Markdown'
        )

    # Важно: регистрируем следующий шаг
    if sent_msg:
        bot.register_next_step_handler(sent_msg, process_deposit_amount)
    else:
        # Если отправка сообщения не удалась, просто отправляем его без next_step, 
        # чтобы бот не завис.
        bot.send_message(
            chat_id, 
            "⚠️ Пожалуйста, введите сумму пополнения. Бот не смог перейти к следующему шагу автоматически, но продолжит работу.", 
            reply_markup=markup,
            parse_mode='Markdown'
        )


def process_deposit_amount(message):
    chat_id = message.chat.id
    
    # ПРОВЕРКА: Если пользователь нажал на кнопку, а не ввел текст, то это отмена.
    if message.text and message.text.lower().startswith('/start'):
        # Если это /start, то обрабатываем его как /start и выходим
        start(message)
        return
    
    if not message.text:
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода.* Пожалуйста, введите сумму только *цифрами*.",
            parse_mode='Markdown',
            reply_markup=get_account_markup()
        )
        safe_delete_message(chat_id, message.message_id)
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
        safe_delete_message(chat_id, message.message_id)
        return

    # !!! Четкое отображение карты !!!
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
    # Кнопка отмены
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Отмена / Назад', callback_data='back_to_main_menu')
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
    
    safe_delete_message(chat_id, message.message_id)
    
    bot.send_message(
        chat_id, 
        payment_instruction,
        reply_markup=markup,
        parse_mode='Markdown'
    )


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА (логика order_pf) ---

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
        
    # Цена убрана с этого шага 
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
        
        # Повторно запрашиваем ссылки, чтобы не потерять контекст
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
    
    bot.send_message(
        OWNER_ID, 
        order_summary_for_admin, 
        parse_mode='Markdown'
    )
    
    if paid:
        confirmation_text = (
            f"✅ *Ваш заказ принят и оплачен!*\n\n" # <--- Итоговая цена отображается здесь
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

    safe_delete_message(chat_id, message.message_id)
    
    bot.send_message(
        chat_id, 
        confirmation_text,
        reply_markup=get_main_menu_markup(),
        parse_mode='Markdown'
    )
    
    user_data[chat_id]['duration'] = None
    user_data[chat_id]['pf_count'] = None


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.chat.id
    get_user_balance(user_id) 
    
    safe_delete_message(user_id, m.message_id) 

    message_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito (ПФ) — это "
        "инструмент, который помогает поднять ваше объявление на 1-ю "
        "позицию в результатах поиска...\n\n"
        "В InkarMedia мы уже более 4 лет помогаем тысячам клиентам... "
        "Наша репутация основана на реальных отзывах — на данный момент их уже более 2750+ ‼️\n"
        "Ознакомьтесь с ними в нашем [Телеграм канале](https://t.me/Avitounlock) ✅ "
        "и убедитесь в качестве нашей работы!\n\n"
        "* Полное соблюдение правил Авито! Безопасно и надежно!\n"
        "* Круглосуточная работа! Наш бот работает 24/7, не пропускайте ни одной "
        "возможности продвинуть объявления! 🤖\n\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП!_"
    )
    
    bot.send_message(
        user_id, 
        message_text, 
        reply_markup=get_main_menu_markup(),
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Эта строка обязательна для предотвращения таймаутов, 
    # которые могут быть причиной "вылетов".
    bot.answer_callback_query(call.id) 
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if chat_id not in user_data:
        get_user_balance(chat_id) 
        
    main_menu_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito (ПФ)... (текст сокращен) ...\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП!_"
    )
    
    if call.data == 'back_to_main_menu':
        try:
            # Сбрасываем все активные next_step_handler для этого чата
            bot.clear_step_handler_by_chat_id(chat_id) 
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
        # Сбрасываем все активные next_step_handler для этого чата
        bot.clear_step_handler_by_chat_id(chat_id)
        
        balance = get_user_balance(chat_id)
        referral_link = f"https://t.me/avitoup1_bot?start={chat_id}" 
        referrals_count = 0 
        
        account_text = (
            "🚪 *Личный кабинет*\n\n"
            f"Ваш баланс: *{balance}₽*\n"
            f"Ваша реферальная ссылка: `{referral_link}`\n"
            f"Количество рефералов: *{referrals_count}*\n\n"
            "Telegram\n"
            "ПФ на Авито\n"
            "Группа с новостями и остальными услугами по Авито и не только - @avitoup_official\n"
            "Связь с создателем @inkarmedia"
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

    elif call.data.startswith('account_'):
        account_key = call.data.replace('account_', '')
        
        if account_key == 'deposit':
            safe_delete_message(chat_id, message_id)
            request_deposit_amount(call.message)
            return
        
        if account_
