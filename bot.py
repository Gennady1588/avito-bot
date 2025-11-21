from flask import Flask, request
import telebot
import os

app = Flask(__name__)

# --- КОНФИГУРАЦИЯ ---
# Используются переменные окружения для токена и ID владельца
TOKEN = os.environ['TOKEN']
OWNER_ID = int(os.environ['OWNER_ID'])
bot = telebot.TeleBot(TOKEN)
orders = {}
# Временный словарь для хранения данных заказа пользователя (ВНИМАНИЕ: Сбрасывается при перезапуске)
user_data = {} 

# --- ФУНКЦИИ ДЛЯ КЛАВИАТУР ---

def get_main_menu_markup():
    """Создает Inline Keyboard для главного меню."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='🚀 Заказать ПФ', callback_data='order_pf'),
        telebot.types.InlineKeyboardButton(text='🚪 Личный кабинет', callback_data='my_account')
    )
    markup.row(
        # TODO: Заменить заглушки на реальные URL-адреса
        telebot.types.InlineKeyboardButton(text='📗 Правила пользования', url='https://your-rules.com'),
        telebot.types.InlineKeyboardButton(text='🧑‍💻 Тех поддержка', url='https://t.me/your_manager')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='💬 FAQ / Кейсы', callback_data='faq'),
        telebot.types.InlineKeyboardButton(text='🎁 Промокоды', callback_data='promocodes')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Подбор стратегии', callback_data='strategy')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='➖', callback_data='_divider')
    )
    markup.row(
        # ИСПОЛЬЗУЕМ ССЫЛКУ, которую вы предоставили
        telebot.types.InlineKeyboardButton(text='Есть ли на Авито бан за ПФ!?', url='https://t.me/Avitounlock/19'),
        telebot.types.InlineKeyboardButton(text='➡️ /start', callback_data='start_again')
    )
    return markup

def get_duration_markup():
    """Создает Inline Keyboard для выбора дней (ШАГ 1 ЗАКАЗА)."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='День', callback_data='duration_1d'),
        telebot.types.InlineKeyboardButton(text='2 дня', callback_data='duration_2d'),
        telebot.types.InlineKeyboardButton(text='3 дня', callback_data='duration_3d')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='5 дней', callback_data='duration_5d'),
        telebot.types.InlineKeyboardButton(text='7 дней', callback_data='duration_7d'),
        telebot.types.InlineKeyboardButton(text='Месяц', callback_data='duration_30d')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_main_menu')
    )
    return markup

def get_pf_count_markup():
    """Создает Inline Keyboard для выбора количества ПФ в день (ШАГ 2 ЗАКАЗА)."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='50', callback_data='pf_count_50'),
        telebot.types.InlineKeyboardButton(text='100', callback_data='pf_count_100')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_duration') 
    )
    return markup

def get_account_markup():
    """Создает Inline Keyboard для меню Личного кабинета."""
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
    """Создает Inline Keyboard для меню FAQ / Кейсы."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Вопросы и ответы', callback_data='faq_intro') 
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Как работают поведенческие факторы', callback_data='faq_pf_how')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Иксы на авито не работают', callback_data='faq_x_fail')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Кейсы и отзывы', callback_data='faq_cases')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu') 
    )
    return markup


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.chat.id
    # Инициализация данных пользователя при старте
    if user_id not in user_data:
        user_data[user_id] = {}
    
    message_text = (
        "📈 *ПФ на Авито*\n"
        "бот\n\n"
        "позицию в результатах поиска. чем больше ПФ, тем выше ваше объявление в "
        "выдаче и тем больше людей его увидят!\n\n"
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
    
    # --- НАВИГАЦИЯ НАЗАД К ГЛАВНОМУ МЕНЮ ---
    if call.data == 'back_to_main_menu':
        # Удаляем сообщение, которое привело к возврату
        bot.delete_message(chat_id, call.message.message_id)
        
    elif call.data == 'start_again':
        start(call.message)
        
    # --- ЛИЧНЫЙ КАБИНЕТ ---
    elif call.data == 'my_account':
        # TODO: Получать данные из БД!
        balance = 155
        referral_link = f"https://t.me/avitoup1_bot?start={chat_id}" 
        referrals_count = 0
        
        account_text = (
            "Личный кабинет\n\n"
            f"Ваш баланс: *{balance}₽*\n"
            f"Ваша реферальная ссылка: `{referral_link}`\n"
            f"Количество рефералов: *{referrals_count}*\n\n"
            "Telegram\n"
            "ПФ на Авито\n"
            "Группа с новостями и остальными услугами по Авито и не только - @avitoup_official\n"
            "Связь с создателем @inkarmedia"
        )
        
        bot.send_message(
            chat_id, 
            account_text, 
            reply_markup=get_account_markup(),
            parse_mode='Markdown'
        )
        
    # --- FAQ / КЕЙСЫ ---
    elif call.data == 'faq':
        bot.send_message(
            chat_id, 
            "Вопросы и ответы", 
            reply_markup=get_faq_markup()
        )
        
    # --- ДЕЙСТВИЯ ВНУТРИ FAQ (ЗАГЛУШКИ) ---
    elif call.data.startswith('faq_'):
        faq_key = call.data.split('_')[1]
        
        # TODO: Заменить на реальный контент
        if faq_key == 'cases':
            bot.send_message(chat_id, "Вот наши лучшие **кейсы и отзывы**: [ссылка на канал/текст]", parse_mode='Markdown')
        else:
            bot.send_message(chat_id, f"Вы выбрали тему: **{faq_key}** (здесь будет подробный ответ).", parse_mode='Markdown')
            
    # --- ЗАКАЗ ПФ (ШАГ 1): Вызов выбора дней ---
    elif call.data == 'order_pf':
        bot.send_message(
            chat_id, 
            "Выберите вариант:", 
            reply_markup=get_duration_markup()
        )
        
    # --- ЗАКАЗ ПФ (ШАГ 2): Выбор длительности -> переход к выбору ПФ в день ---
    elif call.data.startswith('duration_'):
        duration_key = call.data.split('_')[1] 
        user_data[chat_id]['duration'] = duration_key
        
        # Удаляем предыдущее сообщение
        bot.delete_message(chat_id, call.message.message_id) 
        bot.send_message(
            chat_id, 
            "Выберите количество ПФ в день:", 
            reply_markup=get_pf_count_markup()
        )

    # --- ЗАКАЗ ПФ (ШАГ 3): Выбор количества ПФ -> переход к запросу ссылки ---
    elif call.data.startswith('pf_count_'):
        pf_count = call.data.split('_')[2] 
        user_data[chat_id]['pf_count'] = pf_count
        
        # Удаляем предыдущее сообщение
        bot.delete_message(chat_id, call.message.message_id) 
        
        final_text = (
            "Если вы будете запускать на несколько \n"
            "объявлений - КАЖДАЯ ССЫЛКА С \n"
            "НОВОЙ СТРОКИ 'CTRL+ENTER'."
        )
        
        final_markup = telebot.types.InlineKeyboardMarkup()
        final_markup.row(
            telebot.types.InlineKeyboardButton(text='Назад', callback_data='back_to_pf_count')
        )
        
        bot.send_message(
            chat_id, 
            final_text, 
            reply_markup=final_markup
        )
        # TODO: Здесь бот должен перейти в состояние ожидания текстового сообщения (ссылки)
        
    # --- НАВИГАЦИЯ НАЗАД В ПРОЦЕССЕ ЗАКАЗА ---
    elif call.data == 'back_to_duration':
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(
            chat_id, 
            "Выберите вариант:", 
            reply_markup=get_duration_markup()
        )
        
    elif call.data == 'back_to_pf_count':
        bot.delete_message(chat_id, call.message.message_id)
        bot.send_message(
            chat_id, 
            "Выберите количество ПФ в день:", 
            reply_markup=get_pf_count_markup()
        )

    # --- ЗАГЛУШКИ ДЛЯ КНОПОК БЕЗ ФУНКЦИОНАЛА ---
    elif call.data in ['promocodes', 'strategy', 'account_deposit', 'account_orders', 'account_partner']:
        bot.send_message(chat_id, f"Вы нажали кнопку: {call.data}. Здесь будет соответствующая логика.")


# --- ОБРАБОТЧИК СООБЩЕНИЙ КЛИЕНТОВ (ВКЛЮЧАЯ ССЫЛКИ НА ЗАКАЗ) ---
@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID)
def client_msg(m):
    user_id = m.chat.id
    username = m.from_user.username or "без_юзернейма"
    text = m.text
    
    # TODO: Здесь нужно добавить проверку состояния заказа, чтобы понять, 
    # является ли это сообщение ссылкой на объявление или простым вопросом.
    
    # Текущий функционал (любое сообщение идет админу)
    bot.send_message(
        OWNER_ID,
        f"Новый заказ от @{username} (ID: {user_id})\n\nСообщение: {text}\n\nОтветьте реплаем — клиент увидит:"
    )
    bot.send_message(user_id, "Сообщение принято! Ожидайте ответа от менеджера...")

# --- ОБРАБОТЧИК ОТВЕТОВ АДМИНИСТРАТОРА ---
@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply = m.reply_to_message.text
    if "Новый заказ от" in reply or "Сообщение:" in reply:
        try:
            # Парсинг ID клиента
            start_index = reply.find("ID: ") + 4
            end_index = reply.find(")", start_index)
            client_id = int(reply[start_index:end_index])
            
            bot.send_message(client_id, f"Ответ от менеджера:\n{m.text}")
            bot.send_message(OWNER_ID, "Отправлено клиенту.")
        except Exception as e:
            bot.send_message(OWNER_ID, f"Ошибка ID или парсинга. Проверьте формат. Ошибка: {e}")

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
