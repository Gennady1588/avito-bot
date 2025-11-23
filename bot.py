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

# --- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ БЕЗОПАСНОГО УДАЛЕНИЯ ---
def safe_delete_message(chat_id, message_id):
    """Пытается удалить сообщение, игнорируя ошибки, если сообщение уже удалено или недоступно."""
    try:
        bot.delete_message(chat_id, message_id)
    except Exception as e:
        # print(f"Warning: Could not delete message {message_id} in chat {chat_id}. Error: {e}")
        pass # Игнорируем ошибку удаления

# --- ФУНКЦИИ ДЛЯ КЛАВИАТУР ---

def get_main_menu_markup():
    """Создает Inline Keyboard для главного меню."""
    markup = telebot.types.InlineKeyboardMarkup()
    
    # Ряд 1: Основной функционал
    markup.row(
        telebot.types.InlineKeyboardButton(text='🚀 Заказать ПФ', callback_data='order_pf'),
        telebot.types.InlineKeyboardButton(text='🚪 Личный кабинет', callback_data='my_account')
    )
    
    # Ряд 2: Информация
    markup.row(
        telebot.types.InlineKeyboardButton(text='💬 FAQ / Кейсы', callback_data='faq'),
        telebot.types.InlineKeyboardButton(text='🎁 Промокоды', callback_data='promocodes')
    )
    
    # Ряд 3: Поддержка и Правила
    markup.row(
        telebot.types.InlineKeyboardButton(text='📗 Правила пользования', url='https://your-rules.com'),
        telebot.types.InlineKeyboardButton(text='🧑‍💻 Тех поддержка', url='https://t.me/Avitounlock') 
    )
    
    # Ряд 4: Стратегия (Теперь прямая ссылка на @Hiluxe56)
    markup.row(
        telebot.types.InlineKeyboardButton(text='Подбор стратегии', url='https://t.me/Hiluxe56')
    )
    
    # Ряд 5: Ссылка на бан
    markup.row(
        telebot.types.InlineKeyboardButton(text='Есть ли на Авито бан за ПФ!?', url='https://t.me/Avitounlock/19')
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
        telebot.types.InlineKeyboardButton(text='Справочник (Оглавление)', callback_data='faq_intro') 
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Как работают поведенческие факторы', callback_data='faq_pf_how')
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Иксы на авито не работают', url='https://t.me/Avitounlock/21') 
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='Кейсы и отзывы', url='https://t.me/Avitounlock/20') 
    )
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu') 
    )
    return markup
    
def get_back_to_faq_markup():
    """Создает кнопку 'Назад' для возврата к меню FAQ."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='faq') 
    )
    return markup

def get_back_to_account_markup():
    """Создает кнопку 'Назад' для возврата в Личный кабинет."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='my_account') 
    )
    return markup

def get_back_to_main_markup():
    """Создает кнопку 'Назад' для возврата в Главное меню."""
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton(text='🔙 Назад', callback_data='back_to_main_menu') 
    )
    return markup

# --- ФУНКЦИИ ОБРАБОТКИ ЗАКАЗА ---

def request_links(message):
    """Функция, которая вызывается после выбора количества ПФ, чтобы запросить ссылки."""
    chat_id = message.chat.id
    
    final_text = (
        "🔗 *Отправьте ссылки*\n\n"
        "Пожалуйста, вставьте ссылки на ваши объявления с новой строки. "
        "Каждая ссылка должна быть на отдельной строке (`CTRL+ENTER`).\n\n"
        "Мы ждем ваш список ссылок..."
    )
    
    # Отправляем сообщение и регистрируем следующий шаг для получения ссылок
    sent_msg = bot.send_message(
        chat_id, 
        final_text, 
        parse_mode='Markdown'
    )
    
    # Сохраняем ID сообщения, которое нужно будет удалить при получении ссылок
    user_data[chat_id]['awaiting_links_msg_id'] = sent_msg.message_id
    
    bot.register_next_step_handler(sent_msg, process_links_and_send_order)


def process_links_and_send_order(message):
    """Обрабатывает полученные ссылки и отправляет заказ администратору."""
    chat_id = message.chat.id
    links = message.text
    
    # 1. Удаляем сообщение с инструкцией по вводу ссылок (для чистоты)
    if 'awaiting_links_msg_id' in user_data.get(chat_id, {}):
        safe_delete_message(chat_id, user_data[chat_id]['awaiting_links_msg_id'])
        del user_data[chat_id]['awaiting_links_msg_id']
    
    # 2. Собираем данные заказа
    duration_map = {'1d': '1 День', '2d': '2 Дня', '3d': '3 Дня', '5d': '5 Дней', '7d': '7 Дней', '30d': 'Месяц'}
    duration_key = user_data[chat_id].get('duration', 'N/A')
    duration_text = duration_map.get(duration_key, f'Неизвестно ({duration_key})')
    pf_count = user_data[chat_id].get('pf_count', 'N/A')
    
    order_summary_for_admin = (
        "🔥 *НОВЫЙ ЗАКАЗ ПФ* 🔥\n\n"
        f"Пользователь: @{message.from_user.username or 'без_юзернейма'} (ID: `{chat_id}`)\n"
        f"Продолжительность: *{duration_text}*\n"
        f"Количество ПФ в день: *{pf_count}*\n"
        "--- ССЫЛКИ НА ОБЪЯВЛЕНИЯ ---\n"
        f"{links}\n"
        "------------------------------\n"
        "Для ответа клиенту используйте реплай на это сообщение."
    )
    
    # 3. Отправляем заказ администратору
    bot.send_message(
        OWNER_ID, 
        order_summary_for_admin, 
        parse_mode='Markdown'
    )
    
    # 4. Отправляем подтверждение клиенту
    confirmation_text = (
        "✅ *Заказ принят в обработку!*\n\n"
        "Ваш заказ (длительность: **{}**, ПФ/день: **{}**) передан менеджеру. "
        "Ожидайте ответ в ближайшее время."
    ).format(duration_text, pf_count)
    
    # Удаляем сообщение с введенными ссылками для чистоты
    safe_delete_message(chat_id, message.message_id)
    
    # Отправляем подтверждение и возвращаем главное меню
    bot.send_message(
        chat_id, 
        confirmation_text,
        reply_markup=get_main_menu_markup(),
        parse_mode='Markdown'
    )
    
    # Очищаем данные заказа из памяти
    user_data[chat_id]['duration'] = None
    user_data[chat_id]['pf_count'] = None


# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    
    # 1. Удаляем команду /start для чистоты
    safe_delete_message(user_id, m.message_id) 

    # Текст Главного меню
    message_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "позицию в результатах поиска. чем больше ПФ, тем выше ваше объявление в "
        "выдаче и тем больше людей его увидят!\n\n"
        "В InkarMedia мы уже больше 4 лет помогаем тысячам клиентам достигать "
        "отличных результатов на Авито и других платформах. Наша репутация "
        "основана на реальных отзывах — на данный момент их уже более 2750+ ‼️\n"
        "Ознакомьтесь с ними в нашем [Телеграм канале](https://t.me/Avitounlock) ✅ "
        "и убедитесь в качестве нашей работы!\n\n"
        "* Полное соблюдение правил Авито! Безопасно и надежно!\n"
        "* Круглосуточная работа! Наш бот работает 24/7, не пропускайте ни одной "
        "возможности продвинуть объявления! 🤖\n\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП!_"
    )
    
    # 2. Отправляем новое меню
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
    
    # --- ТЕКСТ ГЛАВНОГО МЕНЮ (для навигации Назад) ---
    main_menu_text = (
        "📈 *ПФ на Авито* бот\n\n"
        "позицию в результатах поиска. чем больше ПФ, тем выше ваше объявление в "
        "выдаче и тем больше людей его увидят!\n\n"
        "В InkarMedia мы уже больше 4 лет помогаем тысячам клиентам достигать "
        "отличных результатов на Авито и других платформах. Наша репутация "
        "основана на реальных отзывах — на данный момент их уже более 2750+ ‼️\n"
        "Ознакомьтесь с ними в нашем [Телеграм канале](https://t.me/Avitounlock) ✅ "
        "и убедитесь в качестве нашей работы!\n\n"
        "* Полное соблюдение правил Авито! Безопасно и надежно!\n"
        "* Круглосуточная работа! Наш бот работает 24/7, не пропускайте ни одной "
        "возможности продвинуть объявления! 🤖\n\n"
        "🔥 _Закажите накрутку ПФ прямо сейчас и наблюдайте, как Ваши объявления поднимаются в ТОП!_"
    )
    
    # --- НАВИГАЦИЯ НАЗАД К ГЛАВНОМУ МЕНЮ ---
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
             # Если edit не удался, удаляем и отправляем новое
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                main_menu_text, 
                reply_markup=get_main_menu_markup(),
                parse_mode='Markdown'
            )
        
    # --- ГЛАВНОЕ МЕНЮ: FAQ / КЕЙСЫ ---
    elif call.data == 'faq':
        faq_menu_text = "Выберите интересующий Вас раздел:"
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=faq_menu_text, 
                reply_markup=get_faq_markup()
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                faq_menu_text, 
                reply_markup=get_faq_markup()
            )
            
    # --- ДЕЙСТВИЯ ВНУТРИ FAQ ---
    elif call.data.startswith('faq_'):
        faq_key = call.data.replace('faq_', '')
        
        # --- Тексты ответов ---
        pf_how_text = (
            "*Как поведенческие факторы помогают продвинуть объявление в топ:*\n\n"
            "**Ctr объявлений поднимается** и ещё лучше Авито начинает продвигать "
            "объявление так как видит, что много людей интересуются, создают "
            "активность на объявление, просматривают номер телефона, "
            "добавляют в избранное"
        )
        
        faq_intro_text = (
            "*Справочник (Оглавление)*\n\n"
            "Выберите интересующий Вас раздел:\n\n"
            "1. **Как работают поведенческие факторы**\n"
            "2. **Иксы на авито не работают** (Переход на пост)\n"
            "3. **Кейсы и отзывы** (Переход на пост)\n"
            "4. **Справочник** (Вы здесь)\n\n"
            "Для выбора вернитесь в предыдущее меню, нажав '🔙 Назад'."
        )
        
        # --- Определяем текст в зависимости от faq_key ---
        if faq_key == 'pf_how':
            response_text = pf_how_text
        elif faq_key == 'intro':
            response_text = faq_intro_text
        else: 
            response_text = f"Ошибка: Неизвестный ключ FAQ: {faq_key}"

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response_text,
                reply_markup=get_back_to_faq_markup(),
                parse_mode='Markdown'
            )
        except Exception as e:
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                response_text, 
                reply_markup=get_back_to_faq_markup(),
                parse_mode='Markdown'
            )

    # --- ЛИЧНЫЙ КАБИНЕТ ---
    elif call.data == 'my_account':
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

    # --- ДЕЙСТВИЯ ВНУТРИ ЛИЧНОГО КАБИНЕТА ---
    elif call.data.startswith('account_'):
        account_key = call.data.replace('account_', '')
        
        if account_key == 'deposit':
            response_text = (
                "Введите сумму пополнения на баланс\n\n"
                "❗️ Минимальная сумма пополнения - \n"
                "400 ₽"
            )
        
        elif account_key == 'orders':
            response_text = (
                "📖 *Мои заказы*\n\n"
