import json
import telebot
from telebot import types
from telebot.types import Message
from telebot import custom_filters
from telebot.storage import StateMemoryStorage
import datetime

import api
from config import BOT_TOKEN, DEFAULT_LANG
from states import States

# инициализация, токен из config
storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, state_storage=storage)
available_langs = api.get_langs()

# задачи
tasks = {}

# кнопки меню
def createKeyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('💡 Добавить задачу'))
    keyboard.add(types.KeyboardButton('📄 10 последних задач'))
    keyboard.add(types.KeyboardButton('👩‍💻 Задачи на день'))
    keyboard.add(types.KeyboardButton('✅ Отметить как выполненную'))
    keyboard.add(types.KeyboardButton('📓 Сервис Яндекс.Словари'))

    return keyboard

# приветствие
@bot.message_handler(commands=['start'])
def welcom(message):
    bot.send_message(message.chat.id, "Хай!🖐 Я виртуальный помощник по планированию задач. Что ты хочешь сделать?🧐", reply_markup=createKeyboard())

# добавить задачу
@bot.message_handler(func=lambda message: message.text == "💡 Добавить задачу")
def addTask(message):
    rpl = bot.send_message(message.chat.id, "Напишите дату (дд.мм.гггг) и описание задачи")
    bot.register_next_step_handler(rpl, processTaskStep)

def processTaskStep(message):
    try:
        parts = message.text.strip().split(' ', 1)
        if len(parts) != 2:
            raise ValueError("❗️Неверный формат")

        _date, descript = parts
        date = datetime.datetime.strptime(_date, '%d.%m.%Y').date()

        _id = message.chat.id
        if _id not in tasks:
            tasks[_id] = {}
        if date not in tasks[_id]:
            tasks[_id][date] = []

        tasks[_id][date].append({
            'description' : descript,
            'completed' : False,
            'created' : datetime.datetime.now()
        })

        bot.send_message(message.chat.id, f"Задача добавлена на {_date}")
    
    except Exception as e:
        bot.send_message(message.chat.id, "❗️Неправильный формат. Используйте: дд.мм.гггг описание задачи")

# последние 10 задач
@bot.message_handler(func=lambda message : message.text == "📄 10 последних задач")
def showLastTasks(message):
    _id = message.chat.id
    if _id not in tasks or not any(tasks[_id].values()):
        bot.reply_to(message, "Список задач пуст")
        return
    
    all_tasks = []
    for date in tasks[_id]:
        for task in tasks[_id][date]:
            all_tasks.append((task['created'], date, task))
    
    all_tasks.sort(reverse=True, key=lambda x : x[0])
    last_tasks = all_tasks[:10]

    response = "10 последних задач:\n"
    for i, (created, date, task) in enumerate(last_tasks, 1):
        if task['completed']:
            status = "✅"
        else:
            status = "🔹"
        response += f"{i}. {date.strftime('%d.%m.%Y')} [{status}] {task['description']}\n"
    
    bot.send_message(message.chat.id, response)

# задачи на день
@bot.message_handler(func=lambda message : message.text == '👩‍💻 Задачи на день')
def showTodayTasks(message):
    _id = message.chat.id
    today = datetime.date.today()

    if _id not in tasks or today not in tasks[_id]:
        bot.reply_to(message, "Список задач на сегодня пуст")
        return

    response = f"Задачи на {today.strftime('%d.%m.%Y')}:\n"
    for i, task in enumerate(tasks[_id][today], 1):
        if task['completed']:
            status = "✅"
        else:
            status = "🔹"
        response += f"{i}. [{status}] {task['description']}\n"
    
    bot.send_message(message.chat.id, response)

# отметить выполненным
@bot.message_handler(func=lambda message : message.text == '✅ Отметить как выполненную')
def markCompleted(message):
    rpl = bot.send_message(message.chat.id, "Введите номер задачи из списка задач на сегодня")
    bot.register_next_step_handler(rpl, processMarkCompleted)

def processMarkCompleted(message):
    try:
        _id = message.chat.id
        n = int(message.text) - 1
        today = datetime.date.today()

        if _id not in tasks or today not in tasks[_id]:
            bot.send_message(message.chat.id, "На сегодня задач нет")
            return
        
        if 0 <= n < len(tasks[_id][today]):
            tasks[_id][today][n]['completed'] = True
            bot.send_message(message.chat.id, f"Задача {n + 1} отмечена как выполненная")
        else:
            bot.send_message(message.chat.id, "❗️Номер задачи неверный")
    
    except ValueError:
        bot.send_message(message.chat.id, "Введите номер задачи")

#словари
@bot.message_handler(func=lambda message : message.text == '📓 Сервис Яндекс.Словари')
def about_dict(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        current_lang = data.get('lang', DEFAULT_LANG)

    lang_dispplay = {'en-ru': '🇬🇧 → 🇷🇺 Английский-Русский',\
                     'ru-en': '🇷🇺 → 🇬🇧 Русский-Английский'}.get(current_lang, current_lang)
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('/set_lang (выбрать язык)'))
    keyboard.add(types.KeyboardButton('/lookup (перевести)'))
    keyboard.add(types.KeyboardButton('🔙 Главное меню'))
    
    bot.send_message(message.chat.id, f"📓 *Яндекс.Словари*\n\n"
                     f"Текущее направление: _{lang_dispplay}_\n\n"
                    "Выберите действие:",
                    reply_markup=keyboard,
                    parse_mode='Markdown')
    
    bot.set_state(message.from_user.id, States.base, message.chat.id)

@bot.message_handler(func=lambda message : message.text == '🔙 Главное меню', state='*')
def back_to_main(message):
    bot.send_message(message.chat.id, "Возвращаемся в главное меню", reply_markup=createKeyboard())
    bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(commands=['lookup'])
def lookup_command(message: Message) -> None:
    bot.send_message(
        message.chat.id,
        'Введите слово для поиска.\n'
        'Для смены направления напишите /set_lang'
    )
    bot.set_state(message.from_user.id, States.lookup, message.chat.id)

@bot.message_handler(commands=['set_lang'])
def set_lang_command(message : Message) -> None:
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(types.KeyboardButton('🇬🇧 → 🇷🇺 Английский-Русский'))
    keyboard.add(types.KeyboardButton('🇷🇺 → 🇬🇧 Русский-Английский'))

    bot.send_message(message.chat.id, f'Выберите направление перевода:', reply_markup=keyboard)
    bot.set_state(message.from_user.id, States.lang, message.chat.id)

@bot.message_handler(state=States.lang)
def set_lang(message: Message) -> None:
    lang_map = {'🇬🇧 → 🇷🇺 Английский-Русский': 'en-ru', \
                '🇷🇺 → 🇬🇧 Русский-Английский': 'ru-en'}
    
    chosen = message.text
    if chosen not in lang_map:
        bot.send_message(message.chat.id, 'Пожалуйста, выберите вариант из кнопок')
        return
    
    lang = lang_map[chosen]
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['lang'] = lang
        bot.send_message(message.chat.id, f'Выбрано: {chosen}', reply_markup=types.ReplyKeyboardRemove())

    bot.send_message(message.chat.id, "Теперь введите /lookup для перевода")
    bot.set_state(message.from_user.id, States.base, message.chat.id)

@bot.message_handler(state=States.lookup)
def lookup(message: Message) -> None:
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        result = api.lookup(text=message.text, lang=data.get('lang', DEFAULT_LANG))
        json_raw = json.dumps(result, ensure_ascii=False, indent=2)
        bot.send_message(message.chat.id, f'<pre>{json_raw}</pre>', parse_mode='html')
    bot.send_message(message.chat.id, 'Введите слово для поиска.')

# запуск
if __name__ == '__main__':
    bot.add_custom_filter(custom_filters.StateFilter(bot))
    bot.set_my_commands([
        telebot.types.BotCommand("set_lang", "Сменить направление перевода"),
        telebot.types.BotCommand("lookup", "Поиск слова или фразы")
    ])
    print("Бот запущен")
    bot.infinity_polling()