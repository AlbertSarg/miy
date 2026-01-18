import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8531259676:AAG2gX9g0QL2WVoFW9LS8SzI9lcind6YZ1Y"
bot = telebot.TeleBot(TOKEN)

# ---------------- USER STATES ----------------
# ---------------- STATES ----------------
STATE_NONE = "NONE"
STATE_ADD_NAME = "ADD_NAME"
STATE_ADD_LINK = "ADD_LINK"
STATE_ADD_PHOTO = "ADD_PHOTO"
STATE_ADD_PAYMENT = "ADD_PAYMENT"

user_states = {}
temp_data = {}

def set_state(user_id, state, prev=None, role=None):
    user_states[user_id] = {
        "state": state,
        "prev": prev,
        "role": role
    }

def get_state(user_id):
    return user_states.get(user_id)

def clear_state(user_id):
    if user_id in user_states:
        del user_states[user_id]
    if user_id in temp_data:
        del temp_data[user_id]

@bot.message_handler(commands=['restart'])
def restart_bot(message):
    user_id = message.from_user.id
    clear_state(user_id)  # очищаем состояние и временные данные
    bot.send_message(message.chat.id, "♻️ Бот перезапущен. Начнем заново!")
    start(message)  # показываем стартовое меню

@bot.message_handler(func=lambda m: m.text == "⬅ Назад")
def go_back(message):
    user_id = message.from_user.id

    user_states[user_id] = STATE_NONE
    temp_data.pop(user_id, None)

    seller_menu(message)



# ---------------- GOOGLE SHEETS ----------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    r"C:\Users\user\CollabBotRU\credentials.json",
    scope
)
client = gspread.authorize(creds)
spreadsheet = client.open("BlogersPlatform")
sheet_requests = spreadsheet.worksheet("Requests")
sheet_blogers = spreadsheet.worksheet("Blogers")

MODERATOR_ID = 942268623  # твой Telegram ID

# ---------------- UNIVERSAL BACK ----------------
def back_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

@bot.message_handler(func=lambda m: m.text == "⬅ Назад")
def go_back(message):
    user_id = message.from_user.id

    user_states[user_id] = STATE_NONE
    temp_data.pop(user_id, None)

    seller_menu(message)


# ---------------- START ----------------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if user_id == MODERATOR_ID:
        show_moderation_panel(message)
        return

    welcome_text = (
        "👋 Привет!\n\n"
        "Добро пожаловать на платформу сотрудничества продавцов и блогеров!\n"
        "Выбери, кем ты являешься."
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🛒 Я продавец", "📣 Я блогер")

    try:
        with open("welcome.png", "rb") as photo:
            # Прикрепляем кнопки к фото сразу
            bot.send_photo(chat_id, photo, caption=welcome_text, reply_markup=keyboard)
    except FileNotFoundError:
        bot.send_message(chat_id, welcome_text, reply_markup=keyboard)




    # ADMIN
    
def show_moderation_panel(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📋 Объявления на модерации")
    markup.add("⬅ Назад")

    bot.send_message(
        message.chat.id,
        "🛠 Панель модератора",
        reply_markup=markup
    )


@bot.message_handler(commands=['restart'])
def restart_bot(message):
    if message.from_user.id != MODERATOR_ID:
        bot.send_message(message.chat.id, "⛔ Команда недоступна")
        return

    user_states.clear()
    temp_data.clear()

    bot.send_message(
        message.chat.id,
        "♻️ Бот перезапущен логически.\n"
        "Состояния очищены.\n\n"
        "Можно продолжать тестирование."
    )

    start(message)


# ---------------- SELLER MENU ----------------
def seller_menu(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()
    user_requests = [r for r in records if str(r['Seller_ID']) == str(user_id)]

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Разместить запрос")
    keyboard.add("📦 Мои объявления")
    if user_requests:
        keyboard.add("🗑 Удалить объявление")
    keyboard.add("⬅️ Назад")
    bot.send_message(message.chat.id, "🛒 Меню продавца:", reply_markup=keyboard)
    set_state(user_id, "seller_menu", prev="start", role="seller")

# ---------------- ADD REQUEST ----------------
@bot.message_handler(func=lambda m: m.text == "➕ Разместить запрос")
def add_request_button(message):
    user_id = message.from_user.id

    # Проверяем, есть ли уже активное объявление
    records = sheet_requests.get_all_records()
    if any(str(r['Seller_ID']) == str(user_id) for r in records):
        bot.send_message(message.chat.id, "❌ У вас уже есть активное объявление. Сначала удалите его.")
        return

    temp_data[user_id] = {}  # создаем временный словарь для данных
    user_states[user_id] = STATE_ADD_NAME

    msg = bot.send_message(message.chat.id, "Введите название товара:")
    bot.register_next_step_handler(msg, process_name)

def process_name(message):
    user_id = message.from_user.id
    if message.text == "⬅️ Назад":
        user_states[user_id] = STATE_NONE
        seller_menu(message)
        return

    temp_data[user_id]['name'] = message.text
    user_states[user_id] = STATE_ADD_LINK
    msg = bot.send_message(message.chat.id, "Введите ссылку на товар:")
    bot.register_next_step_handler(msg, process_link)

def process_link(message):
    user_id = message.from_user.id
    if message.text == "⬅️ Назад":
        user_states[user_id] = STATE_NONE
        seller_menu(message)
        return

    temp_data[user_id]['link'] = message.text
    user_states[user_id] = STATE_ADD_PHOTO
    msg = bot.send_message(message.chat.id, "Отправьте фото товара:")
    bot.register_next_step_handler(msg, process_photo)

def process_photo(message):
    user_id = message.from_user.id
    if message.text == "⬅️ Назад":
        user_states[user_id] = STATE_NONE
        seller_menu(message)
        return

    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте фото товара:")
        bot.register_next_step_handler(msg, process_photo)
        return

    temp_data[user_id]['photo'] = message.photo[-1].file_id
    user_states[user_id] = STATE_ADD_PAYMENT
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Бартер", "Оплата")
    msg = bot.send_message(message.chat.id, "Выберите тип сделки:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, add_payment)

def add_payment(message):
    user_id = message.from_user.id
    if message.text == "⬅️ Назад":
        user_states[user_id] = STATE_NONE
        seller_menu(message)
        return

    temp_data[user_id]['payment'] = message.text

    # Сохраняем в Google Sheets
    data = temp_data[user_id]
    sheet_requests.append_row([
        "",                 # ID
        user_id,            # Seller_ID
        data['name'],       # Name
        data['link'],       # Link
        "",                 # Description
        data['photo'],      # Photo_FileID
        data['payment'],    # Payment
        "active",           # Status
        "",                 # Applicant_ID
        ""                  # Applicant_Username
    ])

    user_states[user_id] = STATE_NONE
    temp_data.pop(user_id, None)
    bot.send_message(message.chat.id, f"✅ Ваше объявление '{data['name']}' успешно создано!", reply_markup=types.ReplyKeyboardRemove())
    seller_menu(message)



# ---------------- DELETE REQUEST ----------------
@bot.message_handler(func=lambda m: m.text == "🗑 Удалить объявление")
def delete_request(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()
    row_index = next((i for i, r in enumerate(records) if str(r['Seller_ID']) == str(user_id)), None)
    if row_index is None:
        bot.send_message(message.chat.id, "❌ У вас нет объявлений для удаления.")
        seller_menu(message)
        return
    sheet_requests.delete_rows(row_index + 2)  # +2: заголовок + индекс
    bot.send_message(message.chat.id, "✅ Ваше объявление удалено.")
    seller_menu(message)

# ---------------- MY REQUESTS ----------------
@bot.message_handler(func=lambda m: m.text == "📦 Мои объявления")
def my_requests(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()
    user_requests = [r for r in records if str(r['Seller_ID']) == str(user_id)]
    if not user_requests:
        bot.send_message(message.chat.id, "📦 У вас пока нет объявлений.")
        return
    for r in user_requests:
        text = f"🛍 Товар: {r.get('Name', '—')}\n🔗 Ссылка: {r.get('Link', '—')}\n💰 Тип: {r.get('Payment','—')}"
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🗑 Удалить объявление", callback_data=f"delete_{r.get('ID')}"))
        bot.send_message(message.chat.id, text, reply_markup=keyboard)
        photo_id = r.get("Photo_FileID")
        if photo_id:
            try: bot.send_photo(message.chat.id, photo_id)
            except: bot.send_message(message.chat.id, "❌ Не удалось показать фото")

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def callback_delete(call):
    record_id = call.data.split("_")[1]
    all_records = sheet_requests.get_all_records()
    for i, r in enumerate(all_records, start=2):
        if str(r.get('ID')) == record_id:
            sheet_requests.delete_rows(i)
            bot.answer_callback_query(call.id, "🗑 Объявление удалено!")
            bot.send_message(call.message.chat.id, "✅ Объявление удалено.")
            return

# ---------------- BLOGGER MENU ----------------
def blogger_menu(message):
    user_id = message.from_user.id
    records = sheet_blogers.get_all_records()
    user_data = next((r for r in records if str(r.get('ID','')) == str(user_id)), None)
    if user_data:
        show_blogger_resume(message, user_data)
    else:
        start_blogger_registration(message)

def show_blogger_resume(message, data):
    text = (
        f"📣 Ваше резюме:\n"
        f"👤 Ник: {data.get('Username','—')}\n"
        f"🏷 Ниша: {data.get('Niche','—')}\n"
        f"👥 Подписчики: {data.get('Subscribers','—')}\n"
        f"🎬 Форматы: {data.get('Formats','—')}\n"
        f"💰 Тип: {data.get('Payment_Type','—')}\n"
        f"💵 Цена: {data.get('Price','—')}\n"
        f"📍 Город: {data.get('City','—')}\n"
        f"🔗 Ссылка: {data.get('Links','—')}"
    )
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔍 Смотреть запросы", "🤝 Мои отклики")
    keyboard.add("✏️ Редактировать резюме", "🗑 Удалить резюме")
    keyboard.add("⬅️ Назад")
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == "📣 Я блогер")
def blogger_entry(message):
    blogger_menu(message)

# ---------------- START BOT ----------------
bot.polling()
