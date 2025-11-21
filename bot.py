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
    
    markup.row(
        telebot.types.InlineKeyboardButton(text='🚀 Заказать ПФ', callback_data='order_pf'),
        telebot.types.InlineKeyboardButton(text='🚪 Личный кабинет', callback_data='my_account')
    )
    markup.row(
        telebot.types.InlineKeyboardButton(text='📗 Правила пользования', url='https://your-rules.com'),
        telebot.types.InlineKeyboardButton(text='🧑‍💻 Тех поддержка', url='https://t.me/Avitounlock') 
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

# --- ОСНОВНЫЕ ОБРАБОТЧИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    user_id = m.chat.id
    if user_id not in user_data:
        user_data[user_id] = {}
    
    # 1. Удаляем команду /start
    safe_delete_message(user_id, m.message_id) 

    # Текст из скриншотов
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
             # Если edit не удался (например, сообщение слишком старое), удаляем и отправляем новое
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                main_menu_text, 
                reply_markup=get_main_menu_markup(),
                parse_mode='Markdown'
            )
        
    elif call.data == 'start_again':
        # Принудительная очистка, затем отправка нового меню
        safe_delete_message(chat_id, message_id)
        start(call.message)
        
    # --- ГЛАВНОЕ МЕНЮ: FAQ / КЕЙСЫ ---
    elif call.data == 'faq':
        # УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ ДЛЯ ЧИСТОТЫ ДИАЛОГА
        safe_delete_message(chat_id, message_id)
        bot.send_message(
            chat_id, 
            "Выберите интересующий Вас раздел:", 
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

        # ИСПОЛЬЗУЕМ EDIT_MESSAGE_TEXT
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response_text,
                reply_markup=get_back_to_faq_markup(),
                parse_mode='Markdown'
            )
        except Exception as e:
            # Если edit не удался, удаляем и отправляем новое
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
        
        # Используем edit_message_text для навигации из главного меню
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=account_text,
                reply_markup=get_account_markup(),
                parse_mode='Markdown'
            )
        except Exception:
            # Если edit не удался, удаляем и отправляем новое
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
                "Здесь будет отображаться информация о ваших активных и выполненных "
                "заказах. Пока история пуста. \n"
                "Вы можете [заказать ПФ сейчас](/order_pf)."
            )
            
        elif account_key == 'partner':
            referral_link = f"https://t.me/avitoup1_bot?start={chat_id}"
            response_text = (
                "🤝 *Партнерская программа*\n\n"
                "Приглашайте друзей и партнеров и получайте *10%* от их пополнений "
                "на свой баланс!\n\n"
                f"Ваша реферальная ссылка: `{referral_link}`"
            )
        
        else:
            response_text = f"Ошибка: Неизвестный раздел Личного кабинета: {account_key}"

        # Редактируем сообщение для показа ответа
        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response_text,
                reply_markup=get_back_to_account_markup(),
                parse_mode='Markdown'
            )
        except Exception as e:
            # Если edit не удался, удаляем и отправляем новое
            safe_delete_message(chat_id, message_id)
            bot.send_message(
                chat_id, 
                response_text, 
                reply_markup=get_back_to_account_markup(),
                parse_mode='Markdown'
            )


    # --- ГЛАВНОЕ МЕНЮ: ПРОМОКОДЫ ---
    elif call.data == 'promocodes':
        response_text = (
            "🎁 *Промокоды*\n\n"
            "Промокоды на скидку регулярно публикуются в нашем основном "
            "канале - [@avitoup_official]. Не пропустите, чтобы сэкономить!"
        )

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response_text,
                reply_markup=get_back_to_main_markup(),
                parse_mode='Markdown'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, response_text, reply_markup=get_back_to_main_markup(), parse_mode='Markdown')


    # --- ГЛАВНОЕ МЕНЮ: ПОДБОР СТРАТЕГИИ ---
    elif call.data == 'strategy':
        response_text = (
            "📈 *Подбор стратегии*\n\n"
            "Не уверены, какой вариант подойдет именно вам? \n"
            "Обратитесь к нашему менеджеру для бесплатной консультации и подбора "
            "индивидуальной стратегии продвижения на Авито:\n"
            "🧑‍💻 [Тех поддержка](https://t.me/Avitounlock)"
        )

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=response_text,
                reply_markup=get_back_to_main_markup(),
                parse_mode='Markdown'
            )
        except Exception:
            safe_delete_message(chat_id, message_id)
            bot.send_message(chat_id, response_text, reply_markup=get_back_to_main_markup(), parse_mode='Markdown')


    # --- ЗАКАЗ ПФ: ЛОГИКА ---
    elif call.data == 'order_pf':
        # УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ ДЛЯ ЧИСТОТЫ ДИАЛОГА
        safe_delete_message(chat_id, message_id)
        bot.send_message(
            chat_id, 
            "Выберите вариант:", 
            reply_markup=get_duration_markup()
        )
        
    elif call.data.startswith('duration_'):
        duration_key = call.data.split('_')[1] 
        user_data[chat_id]['duration'] = duration_key
        
        # УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ ДЛЯ ЧИСТОТЫ ДИАЛОГА
        safe_delete_message(chat_id, message_id)
        bot.send_message(
            chat_id, 
            "Выберите количество ПФ в день:", 
            reply_markup=get_pf_count_markup()
        )

    elif call.data.startswith('pf_count_'):
        pf_count = call.data.split('_')[2] 
        user_data[chat_id]['pf_count'] = pf_count
        
        # УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ ДЛЯ ЧИСТОТЫ ДИАЛОГА
        safe_delete_message(chat_id, message_id)
        
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
        
    # --- НАВИГАЦИЯ НАЗАД В ПРОЦЕССЕ ЗАКАЗА ---
    elif call.data == 'back_to_duration':
        # УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ ДЛЯ ЧИСТОТЫ ДИАЛОГА
        safe_delete_message(chat_id, message_id)
        bot.send_message(
            chat_id, 
            "Выберите вариант:", 
            reply_markup=get_duration_markup()
        )
        
    elif call.data == 'back_to_pf_count':
        # УДАЛЯЕМ СТАРОЕ СООБЩЕНИЕ И ОТПРАВЛЯЕМ НОВОЕ ДЛЯ ЧИСТОТЫ ДИАЛОГА
        safe_delete_message(chat_id, message_id)
        bot.send_message(
            chat_id, 
            "Выберите количество ПФ в день:", 
            reply_markup=get_pf_count_markup()
        )


# --- ОБРАБОТЧИК СООБЩЕНИЙ КЛИЕНТОВ ---
@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID)
def client_msg(m):
    user_id = m.chat.id
    username = m.from_user.username or "без_юзернейма"
    text = m.text
    
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
