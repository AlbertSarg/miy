import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials

TOKEN = "8531259676:AAG2gX9g0QL2WVoFW9LS8SzI9lcind6YZ1Y"
bot = telebot.TeleBot(TOKEN)

# ---------------- USER STATES ----------------
# Словарь для хранения состояния пользователей

user_states = {}
def set_state(user_id, screen, prev=None, role=None):
    user_states[user_id] = {
        "screen": screen,
        "prev": prev,
        "role": role
    }

def get_state(user_id):
    return user_states.get(user_id, {})


# ---------------- UNIVERSAL BACK BUTTON ----------------
@bot.message_handler(func=lambda m: m.text == "⬅️ Назад")
def go_back(message):
    user_id = message.from_user.id
    state = get_state(user_id)

    prev = state.get("prev")

    if not prev:
        start(message)
        return

    if prev == "start":
        start(message)
    elif prev == "seller_menu":
        seller_menu(message)
    elif prev == "blogger_menu":
        blogger_menu(message)


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
sheet_blogers = spreadsheet.worksheet("Blogers")  # новый лист для блогеров

# ---------------- START ----------------
MODERATOR_ID = 942268623   # <-- твой Telegram ID

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Если модератор — показываем панель модерации
    if user_id == MODERATOR_ID:
        markup = types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "🛠 Панель модерации:", reply_markup=markup)
        show_moderation_panel(message)
        return

    # Общий приветственный пост с фото
    welcome_text = (
        "👋 Привет!\n\n"
        "Добро пожаловать на платформу сотрудничества продавцов на маркетплейсах и блогеров!\n\n"
        "Здесь ты можешь размещать товары, откликаться на запросы и строить свой профиль.\n"
        "Выбери, кем ты являешься ниже."
    )

    # Отправка фото из локального файла
    try:
        with open("welcome.png", "rb") as photo:
            bot.send_photo(chat_id, photo, caption=welcome_text)
    except FileNotFoundError:
        # Если фото не найдено, просто отправляем текст
        bot.send_message(chat_id, welcome_text)

    # Кнопки выбора роли
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🛒 Я продавец", "📣 Я блогер")
    bot.send_message(chat_id, "Выбери, кто ты:", reply_markup=keyboard)



# ---------------- МОДЕРАЦИЯ ----------------
def show_moderation_panel(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📋 Заявки блогеров", "📊 Статистика")
    keyboard.add("🔎 Объявления", "⬅️ В главное меню")
    
    bot.send_message(message.chat.id, "🛠 Панель модерации:", reply_markup=keyboard)

# Обработчики кнопок модератора
@bot.message_handler(func=lambda message: message.text == "📋 Заявки блогеров")
def moderator_pending_bloggers(message):
    records = sheet_blogers.get_all_records()
    pending = [r for r in records if r.get('Status','') != 'Одобрено']

    if not pending:
        bot.send_message(message.chat.id, "✅ Нет блогеров на модерацию.")
        return

    for r in pending:
        text = (
            f"📣 Резюме блогера:\n\n"
            f"👤 Ник: {r.get('Username','')}\n"
            f"🏷 Ниша: {r.get('Niche','')}\n"
            f"👥 Подписчики: {r.get('Subscribers','')}\n"
            f"🎬 Форматы: {r.get('Formats','')}\n"
            f"💰 Тип: {r.get('Payment_Type','')}\n"
            f"💵 Цена: {r.get('Price','')}\n"
            f"📍 Город: {r.get('City','')}\n"
            f"🔗 Ссылка: {r.get('Links','')}"
        )
        keyboard = types.InlineKeyboardMarkup()
        approve_btn = types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{r.get('ID')}")
        reject_btn = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{r.get('ID')}")
        keyboard.add(approve_btn, reject_btn)

        bot.send_message(message.chat.id, text, reply_markup=keyboard)


@bot.message_handler(func=lambda message: message.text == "📊 Статистика")
def moderator_stats(message):
    records_blogers = sheet_blogers.get_all_records()
    records_requests = sheet_requests.get_all_records()

    total_blogers = len(records_blogers)
    approved = sum(1 for r in records_blogers if r.get('Status') == 'Одобрено')
    pending = total_blogers - approved
    total_requests = len(records_requests)

    text = (
        f"📊 Статистика платформы:\n\n"
        f"👥 Блогеров всего: {total_blogers}\n"
        f"✅ Одобрено: {approved}\n"
        f"⏳ На модерации: {pending}\n"
        f"📦 Запросов на товары: {total_requests}"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda message: message.text == "🔎 Объявления")
def moderator_requests(message):
    records_requests = sheet_requests.get_all_records()
    if not records_requests:
        bot.send_message(message.chat.id, "📦 Нет активных запросов.")
        return
    text = "📦 Все запросы на платформе:\n\n"
    for r in records_requests:
        text += f"🛍 Товар: {r.get('Name')}\nСсылка: {r.get('Link')}\nБартер/оплата: {r.get('Payment')}\n\n"
    bot.send_message(message.chat.id, text)



@bot.message_handler(func=lambda message: message.text == "🔎 Объявления")
def moderator_requests(message):
    records_requests = sheet_requests.get_all_records()
    if not records_requests:
        bot.send_message(message.chat.id, "📦 Нет активных запросов.")
        return
    text = "📦 Все запросы на платформе:\n\n"
    for r in records_requests:
        text += f"🛍 Товар: {r.get('Name')}\nСсылка: {r.get('Link')}\nБартер/оплата: {r.get('Payment')}\n\n"
    bot.send_message(message.chat.id, text)


@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def moderation_callback(call):
    action, blogger_id = call.data.split("_")
    blogger_id = int(blogger_id)
    
    records = sheet_blogers.get_all_records()
    row_idx = None
    for i, r in enumerate(records, start=2):  # +2, т.к. заголовок
        if str(r.get('ID','')) == str(blogger_id):
            row_idx = i
            break
    if not row_idx:
        bot.answer_callback_query(call.id, "❌ Блогер не найден.")
        return

    if action == "approve":
        sheet_blogers.update_cell(row_idx, 10, "Одобрено")  # Столбец Status
        bot.answer_callback_query(call.id, "✅ Блогер одобрен!")
        bot.send_message(blogger_id, "🎉 Ваше резюме одобрено и теперь доступно для продавцов!")
    elif action == "reject":
        sheet_blogers.update_cell(row_idx, 10, "Отклонено")
        bot.answer_callback_query(call.id, "❌ Блогер отклонен!")
        bot.send_message(blogger_id, "⚠️ Ваше резюме отклонено модератором. Попробуйте исправить данные.")


# ---------------- SELLER MENU ----------------
# ---------------- SELLER MENU ----------------
def seller_menu(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()
    user_requests = [r for r in records if r['Seller_ID'] == user_id]

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("➕ Разместить запрос")
    keyboard.add("📦 Мои объявления")
    if user_requests:
        keyboard.add("🗑 Удалить объявление")  # появляется только если есть объявления
    keyboard.add("⬅️ Назад")

    bot.send_message(message.chat.id, "🛒 Меню продавца:", reply_markup=keyboard)


# ---------------- BUTTON HANDLERS ----------------
@bot.message_handler(func=lambda message: message.text == "🛒 Я продавец")
def seller_entry(message):
    seller_menu(message)


@bot.message_handler(func=lambda message: message.text == "📣 Я блогер")
def blogger_entry(message):
    blogger_menu(message)


@bot.message_handler(func=lambda message: message.text == "⬅️ Назад")
def back_to_start(message):
    start(message)



# ---------------- DELETE REQUEST ----------------
@bot.message_handler(func=lambda message: message.text == "🗑 Удалить объявление")
def delete_request(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()

    # Находим индекс строки пользователя
    row_index = next((i for i, r in enumerate(records) if r['Seller_ID'] == user_id), None)
    if row_index is None:
        bot.send_message(message.chat.id, "❌ У вас нет объявлений для удаления.")
        seller_menu(message)
        return

    # Удаляем строку (новый метод gspread)
    sheet_requests.delete_rows(row_index + 2)  # +2: первая строка — заголовок, +0-индекс

    bot.send_message(message.chat.id, "✅ Ваше объявление удалено.")
    seller_menu(message)

    # Иначе продолжаем добавление запроса
    user_states[user_id] = "ADD_REQUEST"
    msg = bot.send_message(
        message.chat.id,
        "Введите название товара:\n\n⬅ Нажмите «Назад», чтобы отменить",
        reply_markup=back_keyboard()
    )
    bot.register_next_step_handler(msg, process_name)


# ---------------- BLOGGER MENU ----------------
def safe_get(record, key, default=""):
    return record.get(key, default)

@bot.message_handler(func=lambda message: message.text == "📣 Я блогер")
def blogger_menu(message):
    user_id = message.from_user.id
    records = sheet_blogers.get_all_records()
    user_data = next((r for r in records if str(r.get('ID','')) == str(user_id)), None)

    if user_data:
        show_blogger_resume(message, user_data)
    else:
        start_blogger_registration(message)

def show_blogger_resume(message, data):

    # Проверка статуса модерации
    if data.get('Status') != "Одобрено":
        bot.send_message(
            message.chat.id,
            "⏳ Ваше резюме на модерации. Как только я проверю, его можно будет использовать."
        )
        return  # Выходим, не показываем резюме до одобрения
    
    text = (
        f"📣 Ваше резюме:\n\n"
        f"👤 Ник: {safe_get(data,'Username')}\n"
        f"🏷 Ниша: {safe_get(data,'Niche')}\n"
        f"👥 Подписчики: {safe_get(data,'Subscribers')}\n"
        f"🎬 Форматы: {safe_get(data,'Formats')}\n"
        f"💰 Тип: {safe_get(data,'Payment_Type')}\n"
        f"💵 Цена: {safe_get(data,'Price')}\n"
        f"📍 Город: {safe_get(data,'City')}\n"
        f"🔗 Ссылка: {safe_get(data,'Links')}"
    )
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🔍 Смотреть запросы", "🤝 Мои отклики")
    keyboard.add("✏️ Редактировать резюме", "🗑 Удалить резюме")
    keyboard.add("⬅️ Назад")
    bot.send_message(message.chat.id, text, reply_markup=keyboard)

MODERATOR_ID = 942268623  # <- сюда твой Telegram ID, чтобы получать уведомления о новых блогерах

# ---------------- РЕГИСТРАЦИЯ БЛОГЕРА ----------------
def start_blogger_registration(message):
    msg = bot.send_message(message.chat.id, "Введите ваш ник в Instagram / Telegram:")
    bot.register_next_step_handler(msg, process_username)

def process_username(message):
    username = message.text.strip()
    if not username or len(username) > 50:
        msg = bot.send_message(message.chat.id, "❌ Ник должен быть от 1 до 50 символов. Введите ещё раз:")
        bot.register_next_step_handler(msg, process_username)
        return
    start_niche_step(message, username)

def start_niche_step(message, username):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Мода", "Еда", "Спорт", "Техника", "Другое")
    msg = bot.send_message(message.chat.id, "Выберите нишу:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, lambda m: process_niche(m, username))

def process_niche(message, username):
    niche = message.text.strip()
    allowed = ["Мода", "Еда", "Спорт", "Техника", "Другое"]
    if niche not in allowed:
        msg = bot.send_message(message.chat.id, "❌ Выберите нишу из предложенных кнопок:")
        bot.register_next_step_handler(msg, lambda m: process_niche(m, username))
        return
    start_subscribers_step(message, username, niche)

def start_subscribers_step(message, username, niche):
    msg = bot.send_message(message.chat.id, "Введите количество подписчиков (пример: 1000-5000):")
    bot.register_next_step_handler(msg, lambda m: process_subscribers(m, username, niche))

def process_subscribers(message, username, niche):
    subs = message.text.strip()
    import re
    if not re.match(r"^\d+(-\d+)?$", subs):
        msg = bot.send_message(message.chat.id, "❌ Введите корректное число или диапазон подписчиков (пример: 1000 или 1000-5000):")
        bot.register_next_step_handler(msg, lambda m: process_subscribers(m, username, niche))
        return
    start_formats_step(message, username, niche, subs)

def start_formats_step(message, username, niche, subscribers):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Фото", "Видео", "Сторис", "Reels", "Другое")
    msg = bot.send_message(message.chat.id, "Выберите форматы контента (можно несколько через запятую):", reply_markup=keyboard)
    bot.register_next_step_handler(msg, lambda m: process_formats(m, username, niche, subscribers))

def process_formats(message, username, niche, subscribers):
    formats = [f.strip() for f in message.text.split(",")]
    allowed = ["Фото", "Видео", "Сторис", "Reels", "Другое"]
    if not all(f in allowed for f in formats):
        msg = bot.send_message(message.chat.id, "❌ Выберите форматы из предложенных кнопок (через запятую, если несколько):")
        bot.register_next_step_handler(msg, lambda m: process_formats(m, username, niche, subscribers))
        return
    start_payment_step(message, username, niche, subscribers, ", ".join(formats))

def start_payment_step(message, username, niche, subscribers, formats):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Бартер", "Оплата")
    msg = bot.send_message(message.chat.id, "Выберите тип сотрудничества:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, lambda m: process_payment_type(m, username, niche, subscribers, formats))

def process_payment_type(message, username, niche, subscribers, formats):
    payment_type = message.text.strip()
    if payment_type not in ["Бартер", "Оплата"]:
        msg = bot.send_message(message.chat.id, "❌ Выберите тип сотрудничества через кнопки:")
        bot.register_next_step_handler(msg, lambda m: process_payment_type(m, username, niche, subscribers, formats))
        return
    start_price_step(message, username, niche, subscribers, formats, payment_type)

def start_price_step(message, username, niche, subscribers, formats, payment_type):
    msg = bot.send_message(message.chat.id, "Укажите цену за пост (если Бартер — можно написать 0):")
    bot.register_next_step_handler(msg, lambda m: process_price(m, username, niche, subscribers, formats, payment_type))

def process_price(message, username, niche, subscribers, formats, payment_type):
    price = message.text.strip()
    if not price.isdigit():
        msg = bot.send_message(message.chat.id, "❌ Введите корректное число (0 если Бартер):")
        bot.register_next_step_handler(msg, lambda m: process_price(m, username, niche, subscribers, formats, payment_type))
        return
    start_city_step(message, username, niche, subscribers, formats, payment_type, price)

def start_city_step(message, username, niche, subscribers, formats, payment_type, price):
    msg = bot.send_message(message.chat.id, "Укажите город / регион аудитории:")
    bot.register_next_step_handler(msg, lambda m: process_city(m, username, niche, subscribers, formats, payment_type, price))

def process_city(message, username, niche, subscribers, formats, payment_type, price):
    city = message.text.strip()
    if not city:
        msg = bot.send_message(message.chat.id, "❌ Город не может быть пустым. Введите ещё раз:")
        bot.register_next_step_handler(msg, lambda m: process_city(m, username, niche, subscribers, formats, payment_type, price))
        return
    start_links_step(message, username, niche, subscribers, formats, payment_type, price, city)

def start_links_step(message, username, niche, subscribers, formats, payment_type, price, city):
    msg = bot.send_message(message.chat.id, "Укажите ссылку на ваш Instagram (обязательно на Instagram):")
    bot.register_next_step_handler(msg, lambda m: process_links(m, username, niche, subscribers, formats, payment_type, price, city))

def process_links(message, username, niche, subscribers, formats, payment_type, price, city):
    links = message.text.strip()
    import re
    pattern = r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9._-]+/?"
    if not re.match(pattern, links):
        msg = bot.send_message(message.chat.id, "❌ Ссылка должна быть на Instagram. Попробуйте снова:")
        bot.register_next_step_handler(msg, lambda m: process_links(m, username, niche, subscribers, formats, payment_type, price, city))
        return

    user_id = message.from_user.id

    # ---------- СОХРАНЯЕМ В GOOGLE SHEETS СТАТУС НА МОДЕРАЦИИ ----------
    user_data = [user_id, username, niche, subscribers, formats, payment_type, price, city, links, "На модерации"]
    sheet_blogers.append_row(user_data)

    bot.send_message(
        message.chat.id,
        "⏳ Ваше резюме на модерации. Как только я проверю, его можно будет использовать."
    )

    # ---------- УВЕДОМЛЕНИЕ МОДЕРАТОРА ----------
    bot.send_message(
        MODERATOR_ID,
        f"Новый блогер ожидает модерации:\n"
        f"Блогер: @{username}\n"
        f"Ниша: {niche}\n"
        f"Подписчики: {subscribers}\n"
        f"Форматы: {formats}\n"
        f"Тип: {payment_type}\n"
        f"Цена: {price}\n"
        f"Город: {city}\n"
        f"Ссылка: {links}\n"
        f"Статус: На модерации"
    )


@bot.message_handler(commands=['approve'])
def approve_resume(message):
    # Ожидаем ID строки или ник блогера
    msg = bot.send_message(message.chat.id, "Введите ID блогера для одобрения:")
    bot.register_next_step_handler(msg, process_approve)

def process_approve(message):
    blogger_id = message.text.strip()
    records = sheet_blogers.get_all_records()
    row_idx = None
    for i, r in enumerate(records, start=2):
        if str(r.get("ID","")) == blogger_id:
            row_idx = i
            break
    if row_idx:
        col_idx = sheet_blogers.row_values(1).index("Status") + 1
        sheet_blogers.update_cell(row_idx, col_idx, "Одобрено")
        bot.send_message(message.chat.id, f"✅ Резюме блогера {blogger_id} одобрено!")
        bot.send_message(blogger_id, "✅ Ваше резюме прошло модерацию и теперь доступно продавцам.")
    else:
        bot.send_message(message.chat.id, "❌ Блогер с таким ID не найден.")


# ---------------- EDIT / DELETE RESUME ----------------
@bot.message_handler(func=lambda message: message.text == "✏️ Редактировать резюме")
def edit_resume(message):
    user_id = message.from_user.id
    records = sheet_blogers.get_all_records()
    user_data = next((r for r in records if str(r.get('ID','')) == str(user_id)), None)

    if not user_data:
        bot.send_message(message.chat.id, "❌ Резюме не найдено. Сначала создайте его через меню блогера.")
        start_blogger_registration(message)
        return

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Ник", "Ниша", "Подписчики", "Форматы", "Тип сотрудничества", "Цена", "Город", "Ссылка на Instagram")
    keyboard.add("⬅️ Назад")
    msg = bot.send_message(message.chat.id, "Выберите поле, которое хотите редактировать:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, lambda m: process_edit_field(m, user_data))

def process_edit_field(message, user_data):
    field_map = {
        "Ник": "Username",
        "Ниша": "Niche",
        "Подписчики": "Subscribers",
        "Форматы": "Formats",
        "Тип сотрудничества": "Payment_Type",
        "Цена": "Price",
        "Город": "City",
        "Ссылка на Instagram": "Links"
    }
    if message.text not in field_map:
        bot.send_message(message.chat.id, "❌ Выберите поле из предложенных кнопок.")
        show_blogger_resume(message, user_data)
        return
    field = field_map[message.text]
    msg = bot.send_message(message.chat.id, f"Введите новое значение для {message.text}:")
    bot.register_next_step_handler(msg, lambda m: save_edited_field(m, user_data, field))

def save_edited_field(message, user_data, field):
    new_value = message.text.strip()
    import re
    if field == "Subscribers" and not re.match(r"^\d+(-\d+)?$", new_value):
        msg = bot.send_message(message.chat.id, "❌ Введите корректное количество подписчиков (например 1000 или 1000-5000):")
        bot.register_next_step_handler(msg, lambda m: save_edited_field(m, user_data, field))
        return
    if field == "Links" and not re.match(r"(https?://)?(www\.)?instagram\.com/[A-Za-z0-9._-]+/?", new_value):
        msg = bot.send_message(message.chat.id, "❌ Ссылка должна быть на Instagram. Попробуйте снова:")
        bot.register_next_step_handler(msg, lambda m: save_edited_field(m, user_data, field))
        return

    records = sheet_blogers.get_all_records()
    row_idx = None
    for i, r in enumerate(records, start=2):
        if str(r.get("ID","")) == str(user_data["ID"]):
            row_idx = i
            break
    if row_idx:
        headers = sheet_blogers.row_values(1)
        col_idx = headers.index(field) + 1
        sheet_blogers.update_cell(row_idx, col_idx, new_value)
        bot.send_message(message.chat.id, f"✅ Поле {field} обновлено!")

    show_blogger_resume(message, user_data)

@bot.message_handler(func=lambda message: message.text == "🗑 Удалить резюме")
def delete_resume(message):
    user_id = message.from_user.id
    records = sheet_blogers.get_all_records()
    row_idx = None
    for i, r in enumerate(records, start=2):
        if str(r.get("ID","")) == str(user_id):
            row_idx = i
            break
    if row_idx:
        sheet_blogers.delete_rows(row_idx)
        bot.send_message(message.chat.id, "✅ Ваше резюме удалено.")
    else:
        bot.send_message(message.chat.id, "❌ Резюме не найдено.")
    start(message)

# ---------------- BACK KEYBOARD ----------------
def back_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

# ---------------- ADD REQUEST ----------------
# ---------------- ADD REQUEST ----------------
@bot.message_handler(func=lambda message: message.text == "➕ Разместить запрос")
def add_request_button(message):
    user_id = message.from_user.id

    # Проверяем, есть ли уже активное объявление
    records = sheet_requests.get_all_records()
    if any(r['Seller_ID'] == user_id for r in records):
        bot.send_message(message.chat.id, "❌ У вас уже есть активное объявление. Сначала удалите его, чтобы создать новое.")
        return

    user_states[user_id] = {"stage": "ADD_NAME"}
    msg = bot.send_message(
        message.chat.id,
        "Введите название товара:\n\n⬅ Нажмите «Назад», чтобы отменить",
        reply_markup=back_keyboard()
    )
    bot.register_next_step_handler(msg, process_name)

def process_name(message):
    user_id = message.from_user.id
    if message.text == "⬅ Нажмите «Назад», чтобы отменить":
        bot.send_message(message.chat.id, "❌ Добавление отменено.")
        seller_menu(message)
        return

    name = message.text
    msg = bot.send_message(message.chat.id, "Введите ссылку на товар:")
    bot.register_next_step_handler(msg, lambda m: process_link(m, name))


def process_link(message, name):
    user_id = message.from_user.id
    if message.text == "⬅ Нажмите «Назад», чтобы отменить":
        bot.send_message(message.chat.id, "❌ Добавление отменено.")
        seller_menu(message)
        return

    link = message.text
    # Тут можно добавить проверку на валидность ссылок WB/Озон
    msg = bot.send_message(message.chat.id, "Отправьте фото товара:")
    bot.register_next_step_handler(msg, lambda m: process_photo(m, name, link))


def process_photo(message, name, link):
    user_id = message.from_user.id
    # Обработка нажатия назад
    if message.text == "⬅ Нажмите «Назад», чтобы отменить":
        bot.send_message(message.chat.id, "❌ Добавление отменено.")
        seller_menu(message)
        return

    if not message.photo:
        msg = bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте фото товара:")
        bot.register_next_step_handler(msg, lambda m: process_photo(m, name, link))
        return

    file_id = message.photo[-1].file_id
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Бартер", "Оплата")
    msg = bot.send_message(message.chat.id, "Выберите тип сделки:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, lambda m: process_payment_final(m, name, link, file_id))


def process_payment_final(message, name, link, file_id):
    user_id = message.from_user.id
    if message.text == "⬅ Нажмите «Назад», чтобы отменить":
        bot.send_message(message.chat.id, "❌ Добавление отменено.")
        seller_menu(message)
        return

    payment = message.text
    sheet_requests.append_row([None, user_id, name, link, "", file_id, payment, "Ожидает", "", ""])
    markup = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, f"✅ Ваш запрос на товар '{name}' добавлен!", reply_markup=markup)
    seller_menu(message)
    
    file_id = message.photo[-1].file_id
    user_id = message.from_user.id
    user_states[user_id]["photo_fileid"] = file_id
    user_states[user_id]["stage"] = "ADD_PAYMENT"

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add("Бартер", "Оплата")
    msg = bot.send_message(message.chat.id, "Выберите тип сделки:", reply_markup=keyboard)
    bot.register_next_step_handler(msg, process_payment)

def process_payment(message):
    if message.text == "⬅ Назад":
        seller_menu(message)
        return

    payment_type = message.text
    user_id = message.from_user.id
    data = user_states.get(user_id)

    # Сохраняем объявление в таблицу
    sheet_requests.append_row([
        None,                   # ID (пусто, Google Sheets создаст)
        user_id,                # Seller_ID
        data["name"],           # Name
        data["link"],           # Link
        "—",                    # Description/ТЗ (можно расширить)
        data["photo_fileid"],   # Photo_FileID
        payment_type,           # Payment
        "—",                    # Status
        None,                   # Applicant_ID
        None                    # Applicant_Username
    ])

    bot.send_message(message.chat.id, f"✅ Ваше объявление на товар '{data['name']}' добавлено!", reply_markup=types.ReplyKeyboardRemove())
    user_states.pop(user_id, None)
    seller_menu(message)

# ---------------- MY REQUESTS (SELLER) ----------------
@bot.message_handler(func=lambda message: message.text == "📦 Мои объявления")
def my_requests(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()
    user_requests = [r for r in records if r['Seller_ID'] == user_id]

    if not user_requests:
        bot.send_message(message.chat.id, "📦 У вас пока нет объявлений.\nНажмите ➕ «Разместить запрос», чтобы создать первое.")
        return

    for r in user_requests:
        text = (
            f"📦 Ваше объявление:\n"
            f"🛍 Товар: {r.get('Name','—')}\n"
            f"Ссылка: {r.get('Link','—')}\n"
            f"Описание/ТЗ: {r.get('Description','—')}\n"
            f"Бартер/Оплата: {r.get('Payment','—')}"
        )
        keyboard = types.InlineKeyboardMarkup()
        delete_btn = types.InlineKeyboardButton("🗑 Удалить объявление", callback_data=f"delete_{r.get('ID')}")
        keyboard.add(delete_btn)

        bot.send_message(message.chat.id, text, reply_markup=keyboard)

        photo_id = r.get("Photo_FileID")
        if photo_id:
            try:
                bot.send_photo(message.chat.id, photo_id)
            except:
                bot.send_message(message.chat.id, "❌ Не удалось показать фото (невалидный file_id)")

# ---------------- CALLBACK HANDLER ----------------
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def callback_delete(call):
    record_id = call.data.split("_")[1]
    # Найти строку по ID и удалить через API Google Sheets
    all_records = sheet_requests.get_all_records()
    for i, r in enumerate(all_records, start=2):  # start=2 потому что 1-я строка заголовки
        if str(r.get('ID')) == record_id:
            sheet_requests.delete_rows(i)
            bot.answer_callback_query(call.id, "🗑 Объявление удалено!")
            bot.send_message(call.message.chat.id, "✅ Объявление удалено.")
            return



MODERATOR_ID = 942268623  # <- твой Telegram ID

# ---------------- КНОПКА ДЛЯ МОДЕРАТОРА ----------------
@bot.message_handler(commands=['moderation'])
def start_moderation(message):
    if message.from_user.id != MODERATOR_ID:
        bot.send_message(message.chat.id, "❌ У вас нет доступа к панели модерации.")
        return

    records = sheet_blogers.get_all_records()
    pending = [r for r in records if r.get('Status') == "На модерации"]

    if not pending:
        bot.send_message(message.chat.id, "Нет блогеров на модерации.")
        return

    for i, r in enumerate(pending):
        keyboard = types.InlineKeyboardMarkup()
        approve = types.InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_{i}")
        reject = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_{i}")
        keyboard.add(approve, reject)

        text = (
            f"📣 Блогер на модерации:\n"
            f"Блогер: @{r['Username']}\n"
            f"Ниша: {r['Niche']}\n"
            f"Подписчики: {r['Subscribers']}\n"
            f"Форматы: {r['Formats']}\n"
            f"Тип: {r['Payment_Type']}\n"
            f"Цена: {r['Price']}\n"
            f"Город: {r['City']}\n"
            f"Ссылка: {r['Links']}\n"
            f"Статус: {r['Status']}"
        )

        bot.send_message(message.chat.id, text, reply_markup=keyboard)

# ---------------- CALLBACK ДЛЯ КНОПОК ----------------
@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def moderation_callback(call):
    if call.from_user.id != MODERATOR_ID:
        bot.answer_callback_query(call.id, "❌ У вас нет доступа.")
        return

    action, idx = call.data.split("_")
    idx = int(idx)

    records = sheet_blogers.get_all_records()
    pending = [r for r in records if r.get('Status') == "На модерации"]
    blogger = pending[idx]

    # Находим строку в листе
    row_idx = None
    all_rows = sheet_blogers.get_all_records()
    for i, r in enumerate(all_rows, start=2):  # +2, так как пропускается заголовок
        if str(r.get("ID")) == str(blogger["ID"]):
            row_idx = i
            break

    if row_idx is None:
        bot.answer_callback_query(call.id, "❌ Ошибка. Блогер не найден.")
        return

    if action == "approve":
        sheet_blogers.update_cell(row_idx, 10, "Одобрено")  # 10-й столбец = Status
        bot.send_message(blogger["ID"], "✅ Ваше резюме одобрено! Теперь вы можете использовать платформу.")
        bot.answer_callback_query(call.id, "Блогер одобрен!")
    elif action == "reject":
        sheet_blogers.update_cell(row_idx, 10, "Отклонено")
        bot.send_message(blogger["ID"], "❌ Ваше резюме отклонено. Попробуйте отправить заново.")
        bot.answer_callback_query(call.id, "Блогер отклонён!")

    # Можно обновить сообщение модератора, чтобы убрать кнопки
    bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)




# ---------------- VIEW REQUESTS (BLOGGERS) ----------------
@bot.message_handler(func=lambda message: message.text == "🔍 Смотреть запросы")
def view_requests_button(message):
    records = sheet_requests.get_all_records()
    if not records:
        bot.send_message(message.chat.id, "Нет открытых запросов.")
        return
    for i, r in enumerate(records):
        keyboard = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("Откликаюсь", callback_data=f"apply_{i}")
        keyboard.add(button)
        text = (
            f"{i+1}. {r['Name']}\n"
            f"Ссылка: {r['Link']}\n"
            f"Бартер/Оплата: {r['Payment']}"
        )
        bot.send_message(message.chat.id, text, reply_markup=keyboard)
        bot.send_photo(message.chat.id, r['Photo_FileID'])

# ---------------- CALLBACK APPLY ----------------
# Обработчик нажатия "Откликаюсь" у блогера
@bot.callback_query_handler(func=lambda call: call.data.startswith("apply_"))
def callback_apply(call):
    idx = int(call.data.split("_")[1])
    records = sheet_requests.get_all_records()
    req = records[idx]

    # Сохраняем отклик блогера в колонках Applicant_ID и Applicant_Username
    # Добавьте эти колонки в лист Requests
    sheet_requests.update_cell(idx + 2, 8, call.from_user.id)        # Applicant_ID
    sheet_requests.update_cell(idx + 2, 9, call.from_user.username)  # Applicant_Username

    # Уведомляем продавца
    bot.send_message(req['Seller_ID'], f"Блогер @{call.from_user.username} откликнулся на ваш товар '{req['Name']}'!")
    bot.answer_callback_query(call.id, "Вы откликнулись!")

# ---------------- MY APPLICATIONS (BLOGGER) ----------------
# Обработчик кнопки "🤝 Мои отклики" для блогеров
@bot.message_handler(func=lambda message: message.text == "🤝 Мои отклики")
def my_applications(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()

    # Все заявки, на которые откликался этот блогер
    user_responses = [r for r in records if str(r.get('Applicant_ID','')) == str(user_id)]

    if not user_responses:
        bot.send_message(message.chat.id, "📭 У тебя пока нет откликов на заявки.")
        return

    for r in user_responses:
        text = (
            f"📦 Объявление: {r.get('Name','')}\n"
            f"Ссылка: {r.get('Link','')}\n"
            f"Бартер/оплата: {r.get('Payment','')}\n"
            f"Продавец: @{r.get('Seller_Username','')}"
        )
        bot.send_message(message.chat.id, text)
        if r.get('Photo_FileID'):
            bot.send_photo(message.chat.id, r['Photo_FileID'])


# ---------------- MY REQUESTS (SELLER) ----------------
@bot.message_handler(func=lambda message: message.text == "📦 Мои объявления")
def my_requests(message):
    user_id = message.from_user.id
    records = sheet_requests.get_all_records()

    user_requests = [r for r in records if str(r.get('Seller_ID')) == str(user_id)]

    if not user_requests:
        bot.send_message(
            message.chat.id,
            "📦 У тебя пока нет объявлений.\n\n"
            "Нажми ➕ «Разместить запрос», чтобы создать первое."
        )
        return

    for r in user_requests:
        text = (
            f"📦 Твое объявление:\n"
            f"🛍 Товар: {r.get('Name', '—')}\n"
            f"🔗 Ссылка: {r.get('Links', '—')}\n"
            f"💰 Тип: {r.get('Payment', '—')}"
        )

        bot.send_message(message.chat.id, text)

        photo_id = r.get('Photo_FileID')
        if photo_id:
            bot.send_photo(message.chat.id, photo_id)

# ---------------- BOT POLLING ----------------
bot.polling()
