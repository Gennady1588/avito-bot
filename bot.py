from flask import Flask, request
import telebot
import os
import re 

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БОТА И СЕРВЕРА ---
# ВНИМАНИЕ: Убедитесь, что эти переменные установлены в окружении Render
TOKEN = os.environ['TOKEN']
OWNER_ID = int(os.environ['OWNER_ID']) # ID администратора (вас)
bot = telebot.TeleBot(TOKEN)

# ИМИТАЦИЯ БАЗЫ ДАННЫХ 
user_balances = {} 
user_data = {} 

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА, КАРТЫ И ЦЕН ---
MANAGER_USERNAME = "Hiluxe56"
# !!! ВАША КАРТА !!!
YOUR_CARD_NUMBER = "2204320348572225" 
MIN_DEPOSIT_AMOUNT = 400

# ПРАЙС-ЛИСТ: ЦЕНЫ ЗА 1 ПФ в день
PRICE_PER_PF_DAILY = 1.0 

# Коэффициенты для длительности (Скидки за объем)
DURATION_COEFFICIENTS = {
    '1d': 1.0,   
    '2d': 1.9,   
    '3d': 2.7,   
    '5d': 4.0,   
    '7d': 5.0,   
    '30d': 18.0  
}
DURATION_NAMES = {
    '1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', 
    '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц'
}

# --- ФУНКЦИИ РАСЧЕТА СТОИМОСТИ ---

def calculate_price(duration_key, pf_count):
    """Рассчитывает общую стоимость заказа."""
    
    try:
        pf_count = int(pf_count)
    except ValueError:
        return 0.0
        
    daily_cost = PRICE_PER_PF_DAILY * pf_count
    coefficient = DURATION_COEFFICIENTS.get(duration_key, 1.0)
    total_price = daily_cost * coefficient
    
    return round(total_price, 2)

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
    # Оформление по аналогии с видео конкурентов и вашими данными (1000059968.mp4, 1000059794.jpg)
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

def get_duration_markup():
    # Цены убраны с этого шага (согласно вашему запросу и видео 1000059966.mp4)
    markup = telebot.types.InlineKeyboardMarkup()
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'День', callback_data='duration_1d'),
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
    # На основе 1000059754.jpg
    markup = telebot.types.InlineKeyboardMarkup()
    
    price_50 = calculate_price(duration_key, 50)
    price_100 = calculate_price(duration_key, 100)
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'50 ПФ ({price_50}₽)', callback_data='pf_count_50'),
        telebot.types.InlineKeyboardButton(text=f'100 ПФ ({price_100}₽)', callback_data='pf_count_100')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_duration') 
    )
    return markup

def get_account_markup():
    # На основе 1000059792.jpg
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
    # На основе 1000059779.jpg, 1000059791.jpg
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
    
    try:
        if hasattr(message, 'message_id'):
            sent_msg = bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=deposit_request_text,
                parse_mode='Markdown'
            )
        else:
            raise Exception("No message_id") 
    except Exception:
        safe_delete_message(chat_id, getattr(message, 'message_id', None))
        sent_msg = bot.send_message(
            chat_id, 
            deposit_request_text, 
            parse_mode='Markdown'
        )

    bot.register_next_step_handler(sent_msg, process_deposit_amount)

def process_deposit_amount(message):
    chat_id = message.chat.id
    
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
        # Очистка и конвертация
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

    # --- ИНСТРУКЦИЯ ПО ОПЛАТЕ ДЛЯ КЛИЕНТА (ОТОБРАЖАЕТ ВАШУ КАРТУ) ---
    payment_instruction = (
        f"✅ *Ваш запрос на пополнение на {amount} ₽ принят!*\n\n"
        f"Для оплаты переведите *{amount} ₽* на карту:\n"
        f"💳 **{YOUR_CARD_NUMBER}**\n\n" # <--- ВАША КАРТА
        "❗️ *Обязательно переводите ТОЧНО эту сумму. Менеджер вручную "
        "проверит поступление и зачислит средства.*\n\n"
        f"Для подтверждения оплаты напишите нашему менеджеру: **@{MANAGER_USERNAME}**"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='✍️ Связаться с менеджером', url=f'https://t.me/{MANAGER_USERNAME}')
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
    
    if current_balance < total_price:
        required = round(total_price - current_balance, 2)
        
        insufficient_funds_text = (
            "❌ *Недостаточно средств!*\n\n"
            f"Стоимость заказа: *{total_price} ₽*\n"
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
        f"💰 *Заказ на {total_price} ₽.* Средства будут списаны после подтверждения.\n\n"
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
        
        request_links(type('obj', (object,), {'chat': type('chat', (object,), {'id': chat_id})})())
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
        
        balance_status = f"*Списано {total_price} ₽*. Новый баланс: *{get_user_balance(chat_id)} ₽*."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания.* Недостаточно средств или цена заказа 0 ₽. Заказ отменен."
    
    duration_text = DURATION_NAMES.get(duration_key, 'Неизвестно')
    
    order_summary_for_admin = (
        "🔥 *НОВЫЙ ЗАКАЗ ПФ* 🔥\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Сумма заказа: *{total_price} ₽*\n"
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
            f"✅ *Ваш заказ принят и оплачен!*\n\n"
            f"Стоимость: *{total_price} ₽*. {balance_status}\n\n"
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
        
        if account_key in ['orders', 'partner']:
            bot.send_message(chat_id, f"Раздел '{account_key.capitalize()}' временно недоступен или находится в разработке.", reply_markup=get_account_markup())
            
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

    elif call.data == 'order_pf':
        order_text = "Выберите вариант:"
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

    elif call.data.startswith('pf_count_'):
        pf_count = call.data.split('_')[2] 
        user_data[chat_id]['pf_count'] = pf_count
        
        safe_delete_message(chat_id, message_id)
        
        request_links(call.message)
        
    elif call.data == 'back_to_duration':
        order_text = "Выберите вариант:"
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
        

# --- ОБРАБОТЧИК СООБЩЕНИЙ КЛИЕНТОВ (для вопросов) ---
@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID and m.text and not m.reply_to_message)
def client_msg(m):
    user_id = m.chat.id
    username = m.from_user.username or "без_юзернейма"
    text = m.text
    
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
    safe_delete_message(user_id, m.message_id)


# --- ОБРАБОТЧИК ОТВЕТОВ АДМИНИСТРАТОРА (для ответов и пополнения) ---
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply_text = m.reply_to_message.text
    
    try:
        # 1. Парсинг ID клиента
        client_id_match = re.search(r'ID: `(\d+)`', reply_text)
        client_id = 0
        if client_id_match:
            client_id = int(client_id_match.group(1))

        if client_id == 0:
            raise ValueError("ID клиента не найден.")

        # 2. Обработка команды зачисления
        if m.text.lower().startswith('/add_balance '):
            try:
                amount_str = m.text.split(' ')[1]
                amount_to_add = round(float(re.sub(r'[^\d\.]', '', amount_str.replace(',', '.'))), 2)
                
                if amount_to_add > 0:
                    user_balances[client_id] = get_user_balance(client_id) + amount_to_add
                    new_balance = user_balances[client_id]
                    
                    # ОТПРАВКА СООБЩЕНИЯ КЛИЕНТУ О ПОПОЛНЕНИИ
                    bot.send_message(
                        client_id, 
                        f"✅ *Баланс пополнен!* 🎉\n\n" # <--- Сообщение для клиента
                        f"На счет зачислено *{amount_to_add} ₽*.\n"
                        f"Текущий баланс: *{new_balance} ₽*.", 
                        parse_mode='Markdown',
                        reply_markup=get_main_menu_markup() # Возвращаем в основное меню
                    )
                    bot.send_message(OWNER_ID, f"Баланс клиента {client_id} пополнен на {amount_to_add} ₽. Новый баланс: {new_balance} ₽.")
                    return 

            except Exception:
                bot.send_message(OWNER_ID, "Ошибка при зачислении баланса. Формат: `/add_balance 1000`", parse_mode='Markdown')
                return
                
        # 3. Стандартный ответ клиенту
        bot.send_message(client_id, f"🧑‍💻 *Ответ менеджера:*\n\n{m.text}", parse_mode='Markdown')
        bot.send_message(OWNER_ID, "Ответ отправлен клиенту.")
        
    except Exception as e:
        bot.send_message(OWNER_ID, f"Ошибка при обработке реплая: {e}")


# --- WEBHOOK И ЗАПУСК ---
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{TOKEN}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
