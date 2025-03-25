from flask import Flask, request, jsonify
import telebot
from threading import Thread
import signal
import sys
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

app = Flask(__name__)
bot = telebot.TeleBot("8194723443:AAHwknMCjVW7e3XAd68ASzYCYRmHs0uD-jo")

# Store subscriber chat IDs
subscribers = set()
flask_thread = None


def signal_handler(sig, frame):
    print('Stopping bot...')
    bot.stop_polling()
    if flask_thread:
        sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def create_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=False)
    keyboard.row(KeyboardButton("📢 Статус подписки"))
    keyboard.row(KeyboardButton("❌ Отписаться"))
    return keyboard


def create_inline_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="✅ Подписаться", callback_data="subscribe"),
        InlineKeyboardButton(text="❌ Отписаться", callback_data="unsubscribe"),
        InlineKeyboardButton(text="📢 Статус подписки", callback_data="status")
    )
    return keyboard


@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        "👋 Добро пожаловать в бот рассылки!\n\n"
        "🔔 Используйте кнопки ниже для управления подпиской:\n"
        "✅ Подписаться - начать получать уведомления\n"
        "❌ Отписаться - перестать получать уведомления\n"
        "📢 Статус подписки - проверить текущий статус"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=create_inline_keyboard())


@bot.message_handler(commands=['status'])
def check_subscription(message):
    if message.chat.id in subscribers:
        status_text = "✅ Вы подписаны на рассылку"
    else:
        status_text = "❌ Вы не подписаны на рассылку"
    bot.send_message(message.chat.id, status_text, reply_markup=create_inline_keyboard())


@bot.message_handler(func=lambda message: message.text == "📢 Статус подписки")
def handle_status_button(message):
    check_subscription(message)


@bot.message_handler(func=lambda message: message.text == "❌ Отписаться")
def handle_unsubscribe_button(message):
    if message.chat.id in subscribers:
        subscribers.discard(message.chat.id)
        bot.send_message(
            message.chat.id,
            "✅ Вы успешно отписались от рассылки",
            reply_markup=create_inline_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ Вы не были подписаны на рассылку",
            reply_markup=create_inline_keyboard()
        )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        if call.data == "subscribe":
            subscribers.add(call.message.chat.id)
            bot.answer_callback_query(call.id, "✅ Вы успешно подписались!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ Вы успешно подписались на рассылку!",
                reply_markup=create_inline_keyboard()
            )
        elif call.data == "unsubscribe":
            subscribers.discard(call.message.chat.id)
            bot.answer_callback_query(call.id, "❌ Вы отписались!")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Вы отписались от рассылки",
                reply_markup=create_inline_keyboard()
            )
        elif call.data == "status":
            status_text = "✅ Вы подписаны на рассылку" if call.message.chat.id in subscribers else "❌ Вы не подписаны на рассылку"
            bot.answer_callback_query(call.id, status_text)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"Статус подписки:\n{status_text}",
                reply_markup=create_inline_keyboard()
            )
    except Exception as e:
        print(f"Error in callback handler: {e}")


@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    message = data['message']
    failed_sends = []
    successful_sends = 0

    for chat_id in subscribers:
        try:
            bot.send_message(
                chat_id,
                f"📢 {message}",
                parse_mode='HTML'
            )
            successful_sends += 1
        except Exception as e:
            failed_sends.append(str(chat_id))
            print(f"Failed to send to {chat_id}: {str(e)}")

    response = {
        'status': 'success' if not failed_sends else 'partial_success',
        'total_subscribers': len(subscribers),
        'successful_sends': successful_sends,
        'failed_sends': failed_sends
    }

    return jsonify(response), 200 if not failed_sends else 207


def run_flask():
    app.run(host='0.0.0.0', port=5000)


if __name__ == "__main__":
    try:
        print("Bot started...")
        flask_thread = Thread(target=run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        print("Бот запущен и готов к работе!")
        print("API сервер доступен по адресу: http://localhost:5000")
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"Error starting bot: {e}")
    finally:
        print("Bot stopped.")
        sys.exit(0)