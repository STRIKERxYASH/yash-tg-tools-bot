from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup
import threading
import time
import os

API_TOKEN = '7002347339:AAGwZsG4naKcuhHBHFgk136JamOpa2OgMY8'  # <-- अपना बॉट टोकन यहाँ डालो
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

user_channels = {}
user_votes = {}
broadcast_users = set()
scheduled_messages = []
spam_tasks = {}

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📢 Update Channel", "❤️ Vote")
    markup.add("⌛ Schedule Msg", "📨 Spam Msg")
    markup.add("💌 Broadcast", "🔰 Bot Owner")
    return markup

def get_connect_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("➕ CONNECT YOUR CHANNEL", url="https://t.me/YOUR_BOT_USERNAME?startchannel"))
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    broadcast_users.add(message.chat.id)
    user_id = message.from_user.id

    if user_id in user_channels:
        channel_name = user_channels[user_id]
        connected_button = InlineKeyboardMarkup()
        connected_button.add(InlineKeyboardButton(channel_name, callback_data='channel_connected'))
        bot.send_message(message.chat.id, "🎉 WELCOME YASH TOOLS\nCONNECTED ✅", reply_markup=connected_button)
        bot.send_message(message.chat.id, "🔘 Choose an option:", reply_markup=get_main_menu())
    else:
        bot.send_message(message.chat.id, "🎉 WELCOME YASH TOOLS\nCONNECT YOUR BOT IN YOUR CHANNEL", reply_markup=get_connect_keyboard())

@bot.message_handler(commands=['connect_test'])
def simulate_connection(message):
    user_channels[message.from_user.id] = "@YourConnectedChannel"
    bot.send_message(message.chat.id, "✅ Channel connected successfully!\nUse /start again.")

@bot.message_handler(func=lambda m: m.text == "💌 Broadcast")
def handle_broadcast(message):
    bot.send_message(message.chat.id, "✍️ Send your broadcast message:")
    bot.register_next_step_handler(message, do_broadcast)

def do_broadcast(message):
    for user_id in broadcast_users:
        try:
            bot.send_message(user_id, f"📣 Broadcast:\n\n{message.text}")
        except:
            pass
    bot.send_message(message.chat.id, "✅ Broadcast sent!")

@bot.message_handler(func=lambda m: m.text == "❤️ Vote")
def handle_vote(message):
    msg = bot.send_message(message.chat.id, "Vote by clicking:", reply_markup=vote_buttons())
    user_votes[msg.message_id] = {}

def vote_buttons():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("👍 0", callback_data="vote👍"),
        InlineKeyboardButton("👎 0", callback_data="vote👎")
    )
    return markup

@bot.callback_query_handler(func=lambda c: c.data.startswith("vote"))
def handle_vote_click(call):
    emoji = call.data[4:]
    msg_id = call.message.message_id
    user_id = call.from_user.id

    votes = user_votes.get(msg_id, {})
    if emoji not in votes:
        votes[emoji] = []

    if any(user_id in v for v in votes.values()):
        bot.answer_callback_query(call.id, "❌ You already voted!")
        return

    votes[emoji].append(user_id)
    user_votes[msg_id] = votes

    markup = InlineKeyboardMarkup()
    for e, users in votes.items():
        markup.add(InlineKeyboardButton(f"{e} {len(users)}", callback_data=f"vote{e}"))
    bot.edit_message_reply_markup(call.message.chat.id, msg_id, reply_markup=markup)
    bot.answer_callback_query(call.id, "✅ Vote counted!")

@bot.message_handler(func=lambda m: m.text == "⌛ Schedule Msg")
def ask_schedule_message(message):
    bot.send_message(message.chat.id, "📨 Send the message to schedule:")
    bot.register_next_step_handler(message, ask_schedule_time)

def ask_schedule_time(message):
    msg_text = message.text
    bot.send_message(message.chat.id, "🕒 After how many seconds to send?")
    bot.register_next_step_handler(message, lambda m: save_schedule(m, msg_text))

def save_schedule(message, msg_text):
    try:
        delay = int(message.text)
        send_at = time.time() + delay
        scheduled_messages.append({"chat_id": message.chat.id, "text": msg_text, "send_at": send_at})
        bot.send_message(message.chat.id, f"✅ Message scheduled in {delay} seconds!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid time. Try again.")

def scheduler_thread():
    while True:
        now = time.time()
        for item in scheduled_messages[:]:
            if item['send_at'] <= now:
                try:
                    bot.send_message(item['chat_id'], f"⏰ Scheduled:\n\n{item['text']}")
                except:
                    pass
                scheduled_messages.remove(item)
        time.sleep(1)

threading.Thread(target=scheduler_thread, daemon=True).start()

@bot.message_handler(func=lambda m: m.text == "📨 Spam Msg")
def handle_spam(message):
    bot.send_message(message.chat.id, "📝 Send your spam message:")
    bot.register_next_step_handler(message, ask_spam_interval)

def ask_spam_interval(message):
    msg_text = message.text
    chat_id = message.chat.id
    bot.send_message(chat_id, "⏱️ Enter repeat time (e.g., '5 sec', '2 min', '1 hour'):")

    def schedule_spam(m):
        interval_text = m.text.lower()
        delay = None

        try:
            if "sec" in interval_text:
                delay = int(interval_text.split()[0])
            elif "min" in interval_text:
                delay = int(interval_text.split()[0]) * 60
            elif "hour" in interval_text:
                delay = int(interval_text.split()[0]) * 3600
            else:
                raise ValueError

            stop_event = threading.Event()
            spam_tasks[chat_id] = stop_event

            def spam_loop():
                while not stop_event.is_set():
                    try:
                        bot.send_message(chat_id, msg_text)
                    except:
                        pass
                    time.sleep(delay)

            threading.Thread(target=spam_loop, daemon=True).start()
            bot.send_message(chat_id, f"✅ Spam started. Send /stop to stop anytime.")

        except:
            bot.send_message(chat_id, "❌ Invalid format. Please send like '5 sec', '2 min' or '1 hour'.")

    bot.register_next_step_handler(message, schedule_spam)

@bot.message_handler(commands=['stop'])
def stop_spam(message):
    chat_id = message.chat.id
    if chat_id in spam_tasks:
        spam_tasks[chat_id].set()
        del spam_tasks[chat_id]
        bot.send_message(chat_id, "🛑 Spam stopped.")
    else:
        bot.send_message(chat_id, "⚠️ No active spam found.")

@bot.message_handler(func=lambda m: m.text == "🔰 Bot Owner")
def handle_owner_contact(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📩 Contact Owner", url="https://t.me/STRIKERxYASH"))
    bot.send_message(message.chat.id, "👇 Tap below to message bot owner", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def fallback(message):
    if message.text not in ["📢 Update Channel", "❤️ Vote", "⌛ Schedule Msg", "📨 Spam Msg", "💌 Broadcast", "🔰 Bot Owner"]:
        bot.send_message(message.chat.id, "USE ONLY KEYBOARD BUTTONS\nANY PROBLEM DM ME\nOWNER - @STRIKERxYASH")

@app.route('/' + API_TOKEN, methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return '', 200

@app.route('/')
def index():
    return "Bot is running"

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=f"https://yash-tg-tools-bot.onrender.com/7002347339:AAGwZsG4naKcuhHBHFgk136JamOpa2OgMY8")  # <== यहाँ अपना Render URL डालो
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
