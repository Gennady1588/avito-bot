from flask import Flask, request
import telebot
import os

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ ---
TOKEN = os.environ['TOKEN']
OWNER_ID = int(os.environ['OWNER_ID'])
bot = telebot.TeleBot(TOKEN)
orders = {}
user_data = {} 
# ИМИТАЦИЯ БАЗЫ ДАННЫХ (для хранения балансов)
# В реальном приложении это должна быть внешняя база данных (PostgreSQL/SQLite)
user_balances = {} 

# --- КОНФИГУРАЦИЯ МЕНЕДЖЕРА И КАРТЫ ---
MANAGER_USERNAME = "Hiluxe56"
# ПРЕДОСТАВЛЕННЫЙ ВАМИ НОМЕР КАРТЫ
YOUR_CARD_NUMBER = "2204320348572225" 
MIN_DEPOSIT_AMOUNT = 400

# --- ПРАЙС-ЛИСТ (ЦЕНЫ ЗА 1 ДЕНЬ) ---
# Цены за 1 ПФ в день
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
    
    # 1. Стоимость за 1 день
    daily_cost = PRICE_PER_PF_DAILY * pf_count
    
    # 2. Общая стоимость с учетом скидки/коэффициента
    coefficient = DURATION_COEFFICIENTS.get(duration_key, 1.0)
    total_price = daily_cost * coefficient
    
    # Округляем до 2 знаков для рублей
    return round(total_price, 2)

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО УДАЛЕНИЯ ---
def safe_delete_message(chat_id, message_id):
    """Пытается удалить сообщение, игнорируя ошибки, если сообщение уже удалено или недоступно."""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        # print(f"Warning: Could not delete message {message_id} in chat {chat_id}. Error: {e}")
        pass 
        
def get_user_balance(user_id):
    """Получает баланс пользователя, инициализируя его, если он новый."""
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    return round(user_balances[user_id], 2)

# --- ФУНКЦИИ ДЛЯ КЛАВИАТУР ---

# (Функции get_main_menu_markup, get_duration_markup, get_pf_count_markup, get_account_markup и т.д.
# остаются без изменений, кроме тех, что влияют на вывод цен и баланса)

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

def get_duration_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Отображаем примерные цены в кнопках, чтобы скопировать логику avitoup1_bot
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
    """Создает Inline Keyboard для выбора количества ПФ в день (ШАГ 2 ЗАКАЗА) с учетом выбранной длительности."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Рассчитываем цены для конкретной длительности
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


# --- ФУНКЦИИ ОБРАБОТКИ ПОПОЛНЕНИЯ (С номером карты) ---

def request_deposit_amount(message):
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
    chat_id = message.chat.id
    deposit_text = message.text.strip()
    amount = 0

    try:
        cleaned_text = deposit_text.lower().replace('р', '').replace('p', '').replace(' ', '')
        amount = int(float(cleaned_text))
        
        if amount < MIN_DEPOSIT_AMOUNT:
            raise ValueError("Сумма меньше минимальной")
        
    except ValueError:
        bot.send_message(
            chat_id, 
            f"🚫 *Ошибка ввода.* Пожалуйста, введите корректную сумму (минимум {MIN_DEPOSIT_AMOUNT} ₽) только цифрами (например, 500).",
            parse_mode='Markdown'
        )
        safe_delete_message(chat_id, message.message_id)

        bot.send_message(
            chat_id, 
            "Пожалуйста, попробуйте снова, нажав на '💳 Пополнить баланс'.",
            reply_markup=get_account_markup()
        )
        return

    # --- ИНСТРУКЦИЯ ПО ОПЛАТЕ ДЛЯ КЛИЕНТА (С ВАШИМ НОМЕРОМ КАРТЫ) ---
    
    payment_instruction = (
        f"✅ *Ваш запрос на пополнение на {amount} ₽ принят!*\n\n"
        f"Для оплаты переведите *{amount} ₽* на карту:\n"
        f"💳 **{YOUR_CARD_NUMBER}**\n\n"
        "❗️ *Обязательно переводите ТОЧНО эту сумму. Менеджер вручную "
        "проверит поступление и зачислит средства.*\n\n"
        f"Для подтверждения оплаты напишите нашему менеджеру: **@{MANAGER_USERNAME}**"
    )
    
    # Кнопка для связи с менеджером
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
        "Ответьте реплаем, чтобы подтвердить получение средств."
    )
    
    bot.send_message(
        OWNER_ID, 
        deposit_summary_for_admin, 
        parse_mode='Markdown'
    )
    
    # --- ОТПРАВКА ИНСТРУКЦИИ КЛИЕНТУ ---
    safe_delete_message(chat_id, message.message_id)
    
    bot.send_message(
        chat_id, 
        payment_instruction,
        reply_markup=markup,
        parse_mode='Markdown'
    )


# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА (Списание баланса) ---

def request_links(message):
    chat_id = message.chat.id
    
    # 1. Проверяем баланс и цену перед тем, как запросить ссылки
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
        
        # Удаляем лишние сообщения и возвращаем в меню
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
        f"💰 *Заказ на {total_price} ₽.* Средства будут списаны после подтверждения.\n\n"
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
    chat_id = message.chat.id
    links = message.text
    
    if 'awaiting_links_msg_id' in user_data.get(chat_id, {}):
        safe_delete_message(chat_id, user_data[chat_id]['awaiting_links_msg_id'])
        del user_data[chat_id]['awaiting_links_msg_id']
    
    # --- 1. СПИСАНИЕ СРЕДСТВ ---
    duration_key = user_data[chat_id].get('duration', 'N/A')
    pf_count = int(user_data[chat_id].get('pf_count', 0))
    total_price = calculate_price(duration_key, pf_count)
    
    if get_user_balance(chat_id) >= total_price:
        user_balances[chat_id] -= total_price
        user_balances[chat_id] = round(user_balances[chat_id], 2)
        
        balance_status = f"*Списано {total_price} ₽*. Новый баланс: *{get_user_balance(chat_id)} ₽*."
        paid = True
    else:
        # На всякий случай, если клиент успел потратить деньги, пока вводил ссылки
        balance_status = "❌ *Ошибка списания.* Недостаточно средств. Заказ отменен."
        paid = False
        
    # --- 2. УВЕДОМЛЕНИЕ АДМИНИСТРАТОРА ---
    
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
    
    # --- 3. ОТВЕТ КЛИЕНТУ ---
    
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
    if user_id not in user_data:
        user_data[user_id] = {}
    
    # Инициализация баланса (если пользователь новый)
    get_user_balance(user_id) 
    
    safe_delete_message(user_id, m.message_id) 

    message_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "🚀 Мы работаем с Поведенческими Факторами на Avito (ПФ) — это "
        "инструмент, который помогает поднять ваше объявление на 1-ю "
        "позицию в результатах поиска. ... (текст сокращен) ...\n"
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
    
    main_menu_text = "..." # Сокращено для читабельности
    
    if call.data == 'back_to_main_menu':
        # ... (логика возврата к главному меню)
        pass 
        
    elif call.data == 'faq':
        # ... (логика FAQ)
        pass 
            
    elif call.data.startswith('faq_'):
        # ... (логика ответов FAQ)
        pass

    elif call.data == 'my_account':
        balance = get_user_balance(chat_id)
        referral_link = f"https://t.me/avitoup1_bot?start={chat_id}" 
        referrals_count = 0 
        
        # Обновленный текст с актуальным балансом
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
        
        # ... (остальная логика Личного кабинета)
        pass


    elif call.data == 'promocodes':
        # ... (логика промокодов)
        pass

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
        
        # Обновляем текст с учетом выбранной длительности
        duration_name = DURATION_NAMES.get(duration_key, 'Заказ')
        duration_text = f"Выбран срок: *{duration_name}*. Теперь выберите количество ПФ в день:"
        
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=duration_text, 
                reply_markup=get_pf_count_markup(duration_key), # Передаем ключ для расчета цен
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
        
        request_links(call.message)
        
    # --- НАВИГАЦИЯ НАЗАД В ПРОЦЕССЕ ЗАКАЗА ---
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
        

# --- ОБРАБОТЧИК СООБЩЕНИЙ АДМИНИСТРАТОРА (для ручного пополнения баланса) ---
# Это основной способ, которым вы можете зачислять средства клиентам!
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply_text = m.reply_to_message.text
    
    try:
        if 'ID:' in reply_text:
            # 1. Парсинг ID клиента
            start_index = reply_text.find("ID: `") + 5
            if start_index == 4: start_index = reply_text.find("ID: ") + 4
            end_index = reply_text.find("`", start_index)
            if end_index == -1: end_index = reply_text.find("\n", start_index)
            client_id = int(reply_text[start_index:end_index].strip().strip('`'))
            
            # 2. Обработка команды зачисления
            if m.text.lower().startswith('/add_balance '):
                # Сценарий: Админ вручную зачисляет баланс
                try:
                    amount_to_add = round(float(m.text.split(' ')[1]), 2)
                    
                    if amount_to_add > 0:
                        user_balances[client_id] = get_user_balance(client_id) + amount_to_add
                        new_balance = user_balances[client_id]
                        
                        # Уведомление клиента
                        bot.send_message(
                            client_id, 
                            f"✅ *Баланс пополнен!*\n\n"
                            f"На счет зачислено *{amount_to_add} ₽*.\n"
                            f"Текущий баланс: *{new_balance} ₽*.", 
                            parse_mode='Markdown'
                        )
                        # Уведомление админа
                        bot.send_message(OWNER_ID, f"Баланс клиента {client_id} пополнен на {amount_to_add} ₽. Новый баланс: {new_balance} ₽.")
                        return 

                except Exception as e:
                    bot.send_message(OWNER_ID, f"Ошибка при зачислении баланса: {e}. Формат: /add_balance 1000")
                    
            # 3. Стандартный ответ клиенту
            bot.send_message(client_id, f"🧑‍💻 *Ответ менеджера:*\n\n{m.text}", parse_mode='Markdown')
            bot.send_message(OWNER_ID, "Ответ отправлен клиенту.")
            
        else:
            bot.send_message(OWNER_ID, "Ошибка: Не удалось найти ID клиента в исходном сообщении.")

    except Exception as e:
        bot.send_message(OWNER_ID, f"Ошибка при парсинге ID или отправке ответа. Ошибка: {e}")

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
