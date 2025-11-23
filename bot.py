from flask import Flask, request
import telebot
import os

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ БОТА И СЕРВЕРА ---
TOKEN = os.environ['TOKEN']
OWNER_ID = int(os.environ['OWNER_ID'])
bot = telebot.TeleBot(TOKEN)

# ИМИТАЦИЯ БАЗЫ ДАННЫХ (для хранения балансов и временных данных)
# Внимание: эти данные будут СБРАСЫВАТЬСЯ при каждом перезапуске сервера (например, на Render)
user_balances = {} 
user_data = {} 
orders = {} # Пока не используется

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА, КАРТЫ И ЦЕН ---
MANAGER_USERNAME = "Hiluxe56"
YOUR_CARD_NUMBER = "2204320348572225" # ВАША КАРТА
MIN_DEPOSIT_AMOUNT = 400

# ПРАЙС-ЛИСТ: ЦЕНЫ ЗА 1 ПФ в день
PRICE_PER_PF_DAILY = 1.0 # 1 рубль за 1 ПФ

# Коэффициенты для длительности (Скидки за объем)
DURATION_COEFFICIENTS = {
    '1d': 1.0,   # День
    '2d': 1.9,   # 2 дня (скидка ~5%)
    '3d': 2.7,   # 3 дня (скидка ~10%)
    '5d': 4.0,   # 5 дней (скидка ~20%)
    '7d': 5.0,   # 7 дней (скидка ~28%)
    '30d': 18.0  # Месяц (скидка ~40%)
}
DURATION_NAMES = {
    '1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', 
    '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц'
}

# --- ФУНКЦИИ РАСЧЕТА СТОИМОСТИ ---

def calculate_price(duration_key, pf_count):
    """Рассчитывает общую стоимость заказа."""
    
    daily_cost = PRICE_PER_PF_DAILY * pf_count
    coefficient = DURATION_COEFFICIENTS.get(duration_key, 1.0)
    total_price = daily_cost * coefficient
    
    return round(total_price, 2)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def safe_delete_message(chat_id, message_id):
    """Пытается удалить сообщение, игнорируя ошибки."""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass 
        
def get_user_balance(user_id):
    """Получает баланс пользователя, инициализируя его, если он новый."""
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    # Инициализация user_data
    if user_id not in user_data:
        user_data[user_id] = {}
        
    return round(user_balances[user_id], 2)

# --- ФУНКЦИИ КЛАВИАТУР ---

def get_main_menu_markup():
    """Главное меню."""
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
    """Меню выбора дней с отображением цены за 50 ПФ."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    price_1d_50 = calculate_price('1d', 50)
    price_2d_50 = calculate_price('2d', 50)
    price_3d_50 = calculate_price('3d', 50)
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'День ({price_1d_50}₽/50ПФ)', callback_data='duration_1d'),
        telebot.types.InlineKeyboardButton(text=f'2 дня ({price_2d_50}₽/50ПФ)', callback_data='duration_2d'),
        telebot.types.InlineKeyboardButton(text=f'3 дня ({price_3d_50}₽/50ПФ)', callback_data='duration_3d')
    )
    
    price_5d_50 = calculate_price('5d', 50)
    price_7d_50 = calculate_price('7d', 50)
    price_30d_50 = calculate_price('30d', 50)
    
    markup.row(
        telebot.types.InlineKeyboardButton(text=f'5 дней ({price_5d_50}₽/50ПФ)', callback_data='duration_5d'),
        telebot.types.InlineKeyboardButton(text=f'7 дней ({price_7d_50}₽/50ПФ)', callback_data='duration_7d'),
        telebot.types.InlineKeyboardButton(text=f'Месяц ({price_30d_50}₽/50ПФ)', callback_data='duration_30d')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_main_menu')
    )
    return markup

def get_pf_count_markup(duration_key):
    """Меню выбора количества ПФ с отображением итоговой цены."""
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
    """Меню Личного кабинета."""
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

# (Остальные функции клавиатур, как `get_faq_markup` и т.д., опущены для краткости, но включены в полный код)

# --- ФУНКЦИИ ОБРАБОТКИ ПОПОЛНЕНИЯ ---

def request_deposit_amount(message):
    """Запрашивает сумму пополнения."""
    chat_id = message.chat.id
    
    deposit_request_text = (
        "💳 *Пополнить баланс*\n\n"
        f"❗️ Минимальная сумма пополнения - *{MIN_DEPOSIT_AMOUNT} ₽*\n\n"
        "Введите желаемую сумму пополнения:"
    )
    
    try:
        sent_msg = bot.edit_message_text(
            chat_id=chat_id,
            message_id=message.message_id,
            text=deposit_request_text,
            parse_mode='Markdown'
        )
    except Exception:
        safe_delete_message(chat_id, message.message_id)
        sent_msg = bot.send_message(
            chat_id, 
            deposit_request_text, 
            parse_mode='Markdown'
        )

    bot.register_next_step_handler(sent_msg, process_deposit_amount)

def process_deposit_amount(message):
    """Обрабатывает сумму, выдает реквизиты и уведомляет администратора."""
    chat_id = message.chat.id
    deposit_text = message.text.strip()
    
    # 1. Проверка и парсинг суммы
    try:
        cleaned_text = deposit_text.lower().replace('р', '').replace('p', '').replace(' ', '')
        amount = int(float(cleaned_text))
        
        if amount < MIN_DEPOSIT_AMOUNT:
            raise ValueError("Сумма меньше минимальной")
        
    except ValueError:
        # Если ввод неверен, просим ввести снова
        bot.send_message(
            chat_id, 
            f"🚫 *Ошибка ввода.* Пожалуйста, введите корректную сумму (минимум {MIN_DEPOSIT_AMOUNT} ₽) только цифрами.",
            parse_mode='Markdown'
        )
        safe_delete_message(chat_id, message.message_id)
        bot.send_message(
            chat_id, 
            "Пожалуйста, попробуйте снова, нажав на '💳 Пополнить баланс'.",
            reply_markup=get_account_markup()
        )
        return

    # 2. Инструкция по оплате для клиента
    payment_instruction = (
        f"✅ *Ваш запрос на пополнение на {amount} ₽ принят!*\n\n"
        f"Для оплаты переведите *{amount} ₽* на карту:\n"
        f"💳 **{YOUR_CARD_NUMBER}**\n\n"
        "❗️ *Обязательно переводите ТОЧНО эту сумму. Менеджер вручную "
        "проверит поступление и зачислит средства.*\n\n"
        f"Для подтверждения оплаты напишите нашему менеджеру: **@{MANAGER_USERNAME}**"
    )
    
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='✍️ Связаться с менеджером', url=f'https://t.me/{MANAGER_USERNAME}')
    )

    # 3. Уведомление администратора
    deposit_summary_for_admin = (
        "💰 *ЗАПРОС НА ПОПОЛНЕНИЕ* 💰\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Желаемая сумма: *{amount} ₽*\n"
        f"Карта для проверки: `{YOUR_CARD_NUMBER}`\n\n"
        f"➡️ *Необходимо проверить поступление:* **{amount} ₽**\n"
        "Ответьте реплаем, чтобы подтвердить получение средств."
    )
    
    bot.send_message(
        OWNER_ID, 
        deposit_summary_for_admin, 
        parse_mode='Markdown'
    )
    
    # 4. Отправка инструкции клиенту
    safe_delete_message(chat_id, message.message_id)
    
    bot.send_message(
        chat_id, 
        payment_instruction,
        reply_markup=markup,
        parse_mode='Markdown'
    )


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА ---

def request_links(message):
    """Проверяет баланс и запрашивает ссылки, если средств достаточно."""
    chat_id = message.chat.id
    
    # 1. Проверяем баланс и цену
    duration_key = user_data[chat_id]['duration']
    pf_count = int(user_data[chat_id]['pf_count'])
    total_price = calculate_price(duration_key, pf_count)
    current_balance = get_user_balance(chat_id)
    
    if current_balance < total_price:
        # Недостаточно средств
        required = total_price - current_balance
        
        insufficient_funds_text = (
            "❌ *Недостаточно средств!*\n\n"
            f"Стоимость заказа: *{total_price} ₽*\n"
            f"Ваш баланс: *{current_balance} ₽*\n"
            f"Необходимо пополнить: *{required} ₽*\n\n"
            "Пожалуйста, пополните баланс в разделе 'Личный кабинет'."
        )
        
        safe_delete_message(chat_id, message.message_id)
        
        bot.send_message(
            chat_id, 
            insufficient_funds_text,
            reply_markup=get_account_markup(),
            parse_mode='Markdown'
        )
        # Очищаем временные данные заказа
        user_data[chat_id]['duration'] = None
        user_data[chat_id]['pf_count'] = None
        return 
        
    # 2. Если средств достаточно, запрашиваем ссылки
    final_text = (
        f"💰 *Заказ на {total_price} ₽.* Средства будут списаны после обработки ссылок.\n\n"
        "🔗 *Отправьте ссылки*\n"
        "КАЖДАЯ ССЫЛКА С НОВОЙ СТРОКИ (`CTRL+ENTER`)."
    )
    
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
    
    # 1. Проверка на текстовое сообщение
    if not message.text:
        # Если пришел не текст, просим ввести снова
        
        if 'awaiting_links_msg_id' in user_data.get(chat_id, {}):
            safe_delete_message(chat_id, user_data[chat_id]['awaiting_links_msg_id'])
            del user_data[chat_id]['awaiting_links_msg_id']
        
        bot.send_message(
            chat_id, 
            "🚫 *Ошибка ввода.* Пожалуйста, отправьте ссылки в виде *текста*.",
            parse_mode='Markdown'
        )
        
        request_links(message)
        return

    links = message.text
    
    # Удаляем сообщение с инструкцией
    if 'awaiting_links_msg_id' in user_data.get(chat_id, {}):
        safe_delete_message(chat_id, user_data[chat_id]['awaiting_links_msg_id'])
        del user_data[chat_id]['awaiting_links_msg_id']
    
    # 2. Списание средств
    duration_key = user_data[chat_id].get('duration', 'N/A')
    pf_count = int(user_data[chat_id].get('pf_count', 0))
    total_price = calculate_price(duration_key, pf_count)
    
    if get_user_balance(chat_id) >= total_price:
        # Выполняем списание
        user_balances[chat_id] -= total_price
        user_balances[chat_id] = round(user_balances[chat_id], 2)
        
        balance_status = f"*Списано {total_price} ₽*. Новый баланс: *{get_user_balance(chat_id)} ₽*."
        paid = True
    else:
        balance_status = "❌ *Ошибка списания.* Недостаточно средств. Заказ отменен."
        paid = False
    
    # 3. Уведомление администратора
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
    
    # 4. Ответ клиенту
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
            "❌ *Заказ отменен из-за нехватки средств.*\n\n"
            "Пожалуйста, пополните баланс и повторите заказ."
        )

    safe_delete_message(chat_id, message.message_id)
    safe_delete_message(chat_id, message.message_id - 1) # Попытка удалить предыдущее сообщение с кнопками
    
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
    get_user_balance(user_id) # Инициализация баланса и user_data
    
    safe_delete_message(user_id, m.message_id) 

    message_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito (ПФ) — это "
        "инструмент, который помогает поднять ваше объявление на 1-ю "
        "позицию в результатах поиска. Чем больше ПФ, тем выше ваше объявление "
        "в выдаче и тем больше людей его увидят!\n\n"
        "В InkarMedia мы уже более 4 лет помогаем тысячам клиентам достигать "
        "отличных результатов на Авито и других платформах. Наша репутация "
        "основана на реальных отзывах — на данный момент их уже более 2750+ ‼️\n"
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
    
    # --- НАВИГАЦИЯ ---
    if call.data == 'back_to_main_menu':
        # ... (логика возврата к главному меню)
        pass 
        
    # --- ЛИЧНЫЙ КАБИНЕТ ---
    elif call.data == 'my_account':
        balance = get_user_balance(chat_id)
        referral_link = f"https://t.me/avitoup1_bot?start={chat_id}" 
        referrals_count = 0 
        
        account_text = (
            "🚪 *Личный кабинет*\n\n"
            f"Ваш баланс: *{balance}₽*\n"
            "..." # Сокращенный текст ЛК
        )
        # ... (отправка сообщения ЛК)
        
    elif call.data.startswith('account_'):
        account_key = call.data.replace('account_', '')
        
        if account_key == 'deposit':
            safe_delete_message(chat_id, message_id)
            request_deposit_amount(call.message)
            return
        # ... (логика остальных разделов ЛК)

    # --- ЗАКАЗ ПФ ---
    elif call.data == 'order_pf':
        order_text = "Выберите вариант:"
        # ... (отправка меню get_duration_markup)
        
    elif call.data.startswith('duration_'):
        duration_key = call.data.split('_')[1] 
        user_data[chat_id]['duration'] = duration_key
        
        duration_name = DURATION_NAMES.get(duration_key, 'Заказ')
        duration_text = f"Выбран срок: *{duration_name}*. Теперь выберите количество ПФ в день:"
        
        # ... (отправка меню get_pf_count_markup)
        
    elif call.data.startswith('pf_count_'):
        pf_count = call.data.split('_')[2] 
        user_data[chat_id]['pf_count'] = pf_count
        
        # Запускаем логику проверки баланса и запроса ссылок
        request_links(call.message)
        
    # --- ПРОЧЕЕ ---
    elif call.data == 'faq':
        # ... (логика FAQ)
        pass 
            
    elif call.data.startswith('faq_'):
        # ... (логика ответов FAQ)
        pass

    elif call.data == 'promocodes':
        # ... (логика промокодов)
        pass

    # ... (Остальные обработчики 'back_to_...')
    
    # Блок с try/except для предотвращения ошибок редактирования сообщений
    # ...

# --- ОБРАБОТЧИК СООБЩЕНИЙ КЛИЕНТОВ (для вопросов) ---
@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID and m.text and not m.reply_to_message)
def client_msg(m):
    # Этот обработчик ловит вопросы от клиента, которые не являются частью order_pf или deposit
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
        "Ваше сообщение принято! Ожидайте ответа от менеджера. Чтобы оформить заказ, нажмите '🚀 Заказать ПФ'."
    )
    safe_delete_message(user_id, m.message_id)


# --- ОБРАБОТЧИК ОТВЕТОВ АДМИНИСТРАТОРА (для ответов и пополнения) ---
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply_text = m.reply_to_message.text
    
    try:
        # 1. Парсинг ID клиента
        # (Логика парсинга ID)
        
        # 2. Обработка команды зачисления
        if m.text.lower().startswith('/add_balance '):
            # Сценарий: Админ вручную зачисляет баланс
            try:
                amount_to_add = round(float(m.text.split(' ')[1]), 2)
                
                if amount_to_add > 0:
                    user_balances[client_id] = get_user_balance(client_id) + amount_to_add
                    new_balance = user_balances[client_id]
                    
                    bot.send_message(
                        client_id, 
                        f"✅ *Баланс пополнен!*\n\n"
                        f"На счет зачислено *{amount_to_add} ₽*.\n"
                        f"Текущий баланс: *{new_balance} ₽*.", 
                        parse_mode='Markdown'
                    )
                    bot.send_message(OWNER_ID, f"Баланс клиента {client_id} пополнен на {amount_to_add} ₽. Новый баланс: {new_balance} ₽.")
                    return 

            except Exception:
                bot.send_message(OWNER_ID, "Ошибка при зачислении баланса. Формат: `/add_balance 1000`")
                return
                
        # 3. Стандартный ответ клиенту
        bot.send_message(client_id, f"🧑‍💻 *Ответ менеджера:*\n\n{m.text}", parse_mode='Markdown')
        bot.send_message(OWNER_ID, "Ответ отправлен клиенту.")

    except Exception:
        bot.send_message(OWNER_ID, "Ошибка при обработке реплая. Возможно, неверный формат ID.")


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
