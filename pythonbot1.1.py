import telebot
from telebot import types
import feedparser
import time
import json
import os

TOKEN = '6234035704:AAFnKMchmh0IRp3LWxRGhuiJuNFlIYKWk2Q'
bot = telebot.TeleBot(TOKEN)

user_rss = {}
user_notifications = {}
tracked_podcasts_file = 'tracked_podcasts.json'

if os.path.exists(tracked_podcasts_file):
    with open(tracked_podcasts_file, 'r') as f:
        user_rss = json.load(f)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard = True) #Изменен размер кнопок 
    itembtn1 = types.KeyboardButton('Найти выпуски подкаста')
    itembtn2 = types.KeyboardButton('Мои подкасты')
    itembtn3 = types.KeyboardButton('Добавить подкаст')
    markup.add(itembtn1, itembtn2, itembtn3)
    bot.send_message(message.chat.id, "Привет! Выберите опцию:", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == 'Найти выпуски подкаста')
def find_podcasts(message):
    msg = bot.send_message(message.chat.id, 'Отправьте ссылку на rss:')
    bot.register_next_step_handler(msg, get_podcast_links)


def get_podcast_links(message):
    url = message.text
    feed = feedparser.parse(url)
    episodes = []

    for entry in feed.entries:
        episodes.append({'title': entry.title, 'link': entry.enclosures[0].href})

    user_rss[message.chat.id] = episodes
    send_inline_keyboard(message)


def send_inline_keyboard(message, page=0, edit=False):
    markup = types.InlineKeyboardMarkup()
    start_idx = page * 10
    end_idx = start_idx + 10
    episodes = user_rss[message.chat.id][start_idx:end_idx]

    for idx, episode in enumerate(episodes):
        markup.add(types.InlineKeyboardButton(text=f'{episode["title"]}', callback_data=f'episode_{start_idx + idx}'))

    if len(user_rss[message.chat.id]) > end_idx:
        markup.add(types.InlineKeyboardButton(text='Следующая страница', callback_data=f'next_page_{page + 1}'))

    if page > 0:
        markup.add(types.InlineKeyboardButton(text='Предыдущая страница', callback_data=f'prev_page_{page - 1}'))

    if edit:
        bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id, text='Выберите выпуск подкаста:',
                              reply_markup=markup)
    else:
        bot.send_message(message.chat.id, 'Выберите выпуск подкаста:', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('next_page_') or call.data.startswith('prev_page_'))
def paginate_podcasts(call):
    page = int(call.data.split('_')[2])
    send_inline_keyboard(call.message, page, edit=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith('episode_'))
def send_episode(call):
    episode_idx = int(call.data.split('_')[1])
    bot.send_message(call.message.chat.id, f'Ссылка на выпуск: {user_rss[call.message.chat.id][episode_idx]["link"]}')


@bot.message_handler(func=lambda message: message.text == 'Мои подкасты')
def show_my_podcasts(message):
    chat_id = str(message.chat.id)
    if chat_id in user_notifications:
        send_my_podcasts_keyboard(message)
    else:
        bot.send_message(message.chat.id, "У вас пока нет подкастов. Добавьте их, используя кнопку 'Добавить подкаст'.")


def send_my_podcasts_keyboard(message):
    chat_id = str(message.chat.id)
    if chat_id in user_notifications:
        markup = types.InlineKeyboardMarkup()
        podcasts = user_notifications[chat_id]

        for idx, podcast in enumerate(podcasts):
            status = '🔔' if podcast['enabled'] else '🔕'
            markup.add(types.InlineKeyboardButton(text=f"{status} {podcast['title']}", callback_data=f'toggle_{idx}'))

        markup.add(types.InlineKeyboardButton(text='Добавить подкаст', callback_data='add_podcast'))
        bot.send_message(message.chat.id, 'Ваши подкасты:', reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "У вас пока нет подкастов. Добавьте их, используя кнопку 'Добавить подкаст'.")


@bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_'))
def toggle_notification(call):
    chat_id = str(call.message.chat.id)
    podcast_idx = int(call.data.split('_')[1])
    user_notifications[chat_id][podcast_idx]['enabled'] = not user_notifications[chat_id][podcast_idx]['enabled']
    send_my_podcasts_keyboard(call.message)


@bot.message_handler(func=lambda message: message.text == 'Добавить подкаст')
def add_podcast(message):
    msg = bot.send_message(message.chat.id, 'Отправьте ссылку на rss подкаста, который хотите добавить:')
    bot.register_next_step_handler(msg, add_podcast_to_list)


def add_podcast_to_list(message):
    url = message.text
    chat_id = str(message.chat.id)
    feed = feedparser.parse(url)

    if 'title' not in feed.feed:
        bot.send_message(message.chat.id, 'Не удалось добавить подкаст. Проверьте ссылку на rss и попробуйте снова.')
        return

    podcast_title = feed.feed.title
    podcast_info = {'title': podcast_title, 'url': url, 'enabled': True}

    if chat_id in user_notifications:
        user_notifications[chat_id].append(podcast_info)
    else:
        user_notifications[chat_id] = [podcast_info]

    save_notifications()
    bot.send_message(message.chat.id, f"Подкаст '{podcast_title}' добавлен в список.")


def save_notifications():
    with open(tracked_podcasts_file, 'w') as f:
        json.dump(user_notifications, f)


bot.polling(non_stop=True)
