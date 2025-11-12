from flask import Flask, request
import telebot
import os

app = Flask(__name__)

TOKEN = os.environ['TOKEN']
OWNER_ID = int(os.environ['OWNER_ID'])
bot = telebot.TeleBot(TOKEN)
orders = {}

@bot.message_handler(commands=['start'])
def start(m):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(
        'Сделать заказ ПФ — от 4000 ₽',
        'Разблокировать аккаунт — от 4000 ₽',
        'Удалить отзыв — от 3000 ₽',
        'Пожаловаться на аккаунт — от 3000 ₽',
        'Набрать подписчиков — от 2500 ₽'
    )
    bot.send_message(m.chat.id, 'Привет! Выбери услугу Avito ПФ:', reply_markup=markup)

@bot.message_handler(func=lambda m: m.chat.id != OWNER_ID)
def client_msg(m):
    user_id = m.chat.id
    username = m.from_user.username or "без_юзернейма"
    text = m.text

    bot.send_message(
        OWNER_ID,
        f"Новый заказ от @{username} (ID: {user_id})\n\nУслуга: {text}\n\nОтветь реплаем — клиент увидит:"
    )
    bot.send_message(user_id, "Заказ принят! Ожидайте ответа...")

@bot.message_handler(func=lambda m: m.chat.id == OWNER_ID and m.reply_to_message)
def admin_reply(m):
    reply = m.reply_to_message.text
    if "Новый заказ от" in reply:
        try:
            client_id = int(reply.split("ID: ")[1].split(")")[0])
            bot.send_message(client_id, f"Ответ от менеджера:\n{m.text}")
            bot.send_message(OWNER_ID, "Отправлено клиенту.")
        except:
            bot.send_message(OWNER_ID, "Ошибка ID.")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/{TOKEN}")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
