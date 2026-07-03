print("СТАРТ БОТА")
import os
import random
import asyncio
from datetime import date
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from supabase import create_client, Client

# Настройка Supabase и бота
TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ВРЕМЕННЫЙ ЛОГ ДЛЯ ПРОВЕРКИ ПЕРЕМЕННЫХ
print(f"--- ПРОВЕРКА ОБЛАКА ---")
print(f"SUPABASE_URL заполнен?: {bool(SUPABASE_URL)}")
print(f"SUPABASE_KEY заполнен?: {bool(SUPABASE_KEY)}")
if SUPABASE_KEY:
    print(f"Длина SUPABASE_KEY: {len(SUPABASE_KEY)} символов")
    print(f"Первые 5 символов ключа: {SUPABASE_KEY[:5]}")
print(f"------------------------")

# Инициализация
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- ФРАЗЫ ----------------

PIDOR_PHRASES = [
    "📂 Поднимаем архив компромата...",
    "🧠 Замеряем концентрацию сомнительных мыслей...",
    "🚨 Получен анонимный донос, начинаем проверку...",
    "🎰 Запускаем генератор неловких ситуаций...",
    "🛰️ Получаем данные со спутников наблюдения..."
]

KRAS_PHRASES = [
    "🔥 Замеряем температуру крутости...",
    "📸 Подсчитываем удачные фотографии...",
    "🎩 Проверяем наличие природного обаяния...",
    "🏆 Сверяем данные с реестром красавчиков...",
    "✨ Калибруем датчики привлекательности..."
]

# ---------------- ВСПОМОГАТЕЛЬНЫЕ (Supabase) ----------------

def get_users():
    # Вытаскиваем всех юзеров из облака
    res = supabase.table("users").select("*").execute()
    # Возвращаем в виде списка словарей
    return res.data


def get_today_winner(role):
    today_str = str(date.today())
    # Ищем победителя на сегодня
    res = supabase.table("daily_winners").select("user_id").eq("game_date", today_str).eq("role", role).execute()
    if res.data:
        user_id = res.data[0]["user_id"]
        # Ищем самого юзера
        user_res = supabase.table("users").select("*").eq("user_id", user_id).execute()
        return user_res.data[0] if user_res.data else None
    return None


def get_opposite_winner_id(role):
    today_str = str(date.today())
    opp_role = "krasavchik" if role == "pidor" else "pidor"
    res = supabase.table("daily_winners").select("user_id").eq("game_date", today_str).eq("role", opp_role).execute()
    return res.data[0]["user_id"] if res.data else None


def save_daily_winner(role, user_id):
    today_str = str(date.today())
    supabase.table("daily_winners").insert({
        "game_date": today_str,
        "role": role,
        "user_id": user_id
    }).execute()


def weighted_choice(users, column_name):
    # В Supabase данные приходят как словари, поэтому заменяем индексы на ключи
    total_weight = sum(user[column_name] for user in users)
    if total_weight <= 0:
        return random.choice(users)

    rnd = random.uniform(0, total_weight)
    current = 0
    for user in users:
        current += user[column_name]
        if rnd <= current:
            return user


def redistribute_weights(winner_id, weight_column):
    # 1. Получаем всех активных пользователей из базы
    users = supabase.table("users").select("*").eq("is_active", True).execute().data
    if not users:
        return

    # Рассчитываем штраф для сегодняшнего победителя
    for user in users:
        if user["user_id"] == winner_id:
            current_weight = user[weight_column]
            # Победитель получает штраф -40.0, но не ниже капа 60.0
            new_winner_weight = max(70.0, current_weight - 30.0)
            supabase.table("users").update({weight_column: new_winner_weight}).eq("user_id", winner_id).execute()
            break

    # 2. Пересчитываем веса для ВСЕХ ОСТАЛЬНЫХ участников розыгрыша
    for user in users:
        if user["user_id"] == winner_id:
            continue  # Пропускаем сегодняшнего победителя

        current_weight = user[weight_column]

        if current_weight < 100.0:
            # Если игрок в зоне защиты (недавно выигрывал) — плавно возвращаем к норме на +4.0
            new_weight = min(100.0, current_weight + 4.0)
        else:
            # Если игрок НЕ выигрывал сегодня — даем ему микро-прирост +1.0 к весу (шанс растет).
            # Но если его вес за прошлые дни уже улетел слишком высоко (например, выше 120.0),
            # система плавно сдувает его излишки на -2.0 обратно к балансу.
            if current_weight > 120.0:
                new_weight = max(100.0, current_weight - 2.0)
            else:
                new_weight = current_weight + 1.0

        # Обновляем значение веса конкретного участника в Supabase
        supabase.table("users").update({weight_column: new_weight}).eq("user_id", user["user_id"]).execute()

# ---------------- КОМАНДЫ ----------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📜 *Список доступных команд:*\n\n"
        "/register — Зарегистрироваться в рулетке\n"
        "/pidor — Найти Пидора дня 🤡\n"
        "/run — Найти Красавчика дня 😎\n"
        "/stats — Посмотреть общую статистику побед 📊\n"
        "/procents — Узнать свои шансы на победу 🎯\n"
        "/records — Узнать лидеров чата 👀\n"
        "/switch @username — Использовать карту UNO и перевести от себя пидора (Шанс 5%, КД 1 неделя) 🃏\n"
        "/mystats — Узнать свою статистику и карту UNO 👀\n"
        "/unreg — Выйти из рулетки и удалить данные (нет) 🚪\n"
        "/help — Показать это сообщение еще раз (но на кое хер?)"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # 1. Проверяем, был ли пользователь вообще когда-то в базе
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    
    if res.data:
        player = res.data[0]
        # Если он есть, но отключен (is_active == False) — возвращаем его в игру
        if not player.get("is_active", True):
            supabase.table("users").update({"is_active": True}).eq("user_id", user.id).execute()
            await update.message.reply_text(f"✅ {user.first_name}, с возвращением дешёвка! Твоя старая статистика восстановлена.")
        else:
            await update.message.reply_text(f"Вы уже зарегистрированы, {user.first_name}!")
        return

    # 2. Если пользователя вообще нет в базе — создаем с нуля
    supabase.table("users").insert({
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "pidor_weight": 100.0,
        "kras_weight": 100.0,
        "pidor_count": 0,
        "kras_count": 0,
        "is_active": True  # Явно указываем, что активен
    }).execute()
    
    await update.message.reply_text(f"✅ {user.first_name} успешно зарегистрирован в рулетке с нуля!")


async def unreg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Проверяем существование пользователя в базе
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not res.data or not res.data[0].get("is_active", True):
        await update.message.reply_text("Тебя и так нет в игре, можешь в окно выйти, лол.")
        return

    # ОБНОВЛЕННЫЙ БЛОК: Выключаем только флаг активности, ВЕСА НЕ ТРОГАЕМ!
    supabase.table("users").update({
        "is_active": False
    }).eq("user_id", user.id).execute()
    
    # Твой текст и отправка стикера реплаем (без риска упасть из-за chat_id)
    await update.message.reply_text(f"🚪 {user.first_name} ты реально ливнул? Твоя статистика сохранена, так что не прощаемся - дешёвка!")
    await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReQ5qQ3ghClnZvA6qP2Cx0lGm8NIjBwACMlIAAv-BOEl-zu7LwscR5DwE')

async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обнуляем счетчики побед и возвращаем базовые веса всем игрокам в Supabase
    supabase.table("users").update({
        "pidor_count": 0, 
        "kras_count": 0, 
        "pidor_weight": 100.0, 
        "kras_weight": 100.0
    }).neq("user_id", 0).execute()  # .neq("user_id", 0) хак, чтобы обновить вообще всех юзеров разом
    
    # Полностью очищаем таблицу "победителей"
    supabase.table("daily_winners").delete().neq("user_id", 0).execute()
    
    await update.message.reply_text("🔄 *Вся статистика обнулена!* Счетчик подопытных сброшен, шансы участников снова равны.", parse_mode="Markdown")
    
    # ИСПРАВЛЕНО: Используем reply_sticker вместо send_sticker, чтобы бот не падал из-за отсутствия chat_id
    await update.message.reply_sticker(sticker='CAACAgQAAxkBAAEReRBqQ3htVR15fuIwV3C_4QUWL8_xxQACbhwAAltJOVMTctyzCRD65jwE')


async def pidor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_users()
    if len(users) < 1:
        await update.message.reply_text("В боте еще никто не зарегистрировался. Напишите /register")
        return

    already_winner = get_today_winner("pidor")
    if already_winner:
        username = f" (@{already_winner['username']})" if already_winner['username'] else ""
        await update.message.reply_text(f"Сегодня этот выбор уже сделан! 🤡 Пидор дня — {already_winner['first_name']}{username}")
        return

    opposite_id = get_opposite_winner_id("pidor")
    filtered_users = [u for u in users if u["user_id"] != opposite_id]

    if not filtered_users:
        await update.message.reply_text("Все участники уже заняли свои титулы на сегодня! Больше выбирать некого.")
        return

    # --- ИСПРАВЛЕННЫЙ БЛОК ЗАСТАВОК ---
    # Отправляем фразы как обычные сообщения в чат, БЕЗ реплая на команду
    chat_id = update.effective_chat.id
    for phrase in random.sample(PIDOR_PHRASES, len(PIDOR_PHRASES)):
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1)
    # ----------------------------------

    # Выбираем победителя, используя имя колонки весов из Supabase
    winner = weighted_choice(filtered_users, "pidor_weight")

    # Рассчитываем новое количество побед
    new_count = winner["pidor_count"] + 1

    # Обновляем счетчик пидоров в Supabase
    supabase.table("users").update({"pidor_count": new_count}).eq("user_id", winner["user_id"]).execute()
    
    redistribute_weights(winner["user_id"], "pidor_weight")
    save_daily_winner("pidor", winner["user_id"])

    username = f" (@{winner['username']})" if winner['username'] else ""
    # Финальный вердикт делаем красивым ответом (реплаем) на самое первое сообщение пользователя
    await update.message.reply_text(f"🤡 Пидор дня — {winner['first_name']}{username}")

    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ ----------------
    name = winner["first_name"]

    # Мемные стикеры для пидорских юбилеев (вставь сюда 3-5 разных ID)
    pidor_stickers_pool = [
        'CAACAgIAAxkBAAEReO5qQ22SmZkDyLqKq0vP6-ELBjPTUAACjnQAAihj2EtnaWFztIKP7DwE',
        'CAACAgIAAxkBAAERePBqQ27RxFYFJcHGEaZ9kPTDkhO1EAACSk4AAuAKOUlEfzO0OLfimzwE',
        'CAACAgIAAxkBAAERePJqQ27guzCAFe3IqBMNm9Rsq4tlIwACxVQAAsfrOEk6oSm-WVc9QjwE',
        'CAACAgIAAxkBAAERePRqQ28nWDjJOWNP0amyxIzJUiJwgAACckYAArr9OUlyV8svBKf4PzwE',
        'CAACAgIAAxkBAAERePZqQ29RyTAuFB6ryyH6BApiXpfNtgAC3EoAAmsNOUmTv1vWKkSg7TwE',
        'CAACAgIAAxkBAAERePhqQ29fvKDHMorjySaOzDQ013gcdgACNUoAAoRQOEkf13J-sHIrqTwE'
    ]
        
    # Список фраз-шуток для круглых десятков
    jokes = {
        10: f"🎂 *ОГО, 10 РАЗ!* {name}, поздравляем! Первый юбилей на дне. Давай, расскажи всем, что это просто «случайность» и «рандом сломался»! 🤡",
        20: f"👑 *УЖЕ 20 ПОБЕД!* {name} официально переходит в Высшую лигу сомнительных парней. Тебе уже пора выдавать именную корону из картона и скотча! 🎪",
        30: f"🚨 *30-й СТРАЙК!* {name}, это уже не шутка, это карьера. Ты стабилен как швейцарские часы. Стабильно плох, но всё же! 🛑",
        40: f"🗄 *КРИЗИС СРЕДНЕГО ВОЗРАСТА!* {name} отмечает 40 побед! Архив компромата переполнен! 📂",
        50: f"🎖 *ПОЛУВЕКОВОЙ ЮБИЛЕЙ!* 50 раз! {name} получает золотую медаль и пожизненную путевку в гейбар! 🏅",
        60: f"🎰 *МАСТЕР СВОЕГО ДЕЛА!* 60 побед у {name}! Датчики сомнительных мыслей просто зашкаливают, не шали! ⚡️",
        70: f"🛰 *КОСМИЧЕСКИЙ УРОВЕНЬ!* 70-й раз! {name} твоё гейство видно даже со спутников наблюдения! 🌌",
        80: f"🦾 *ТИФЛОНОВЫЙ СТАТУС!* 80 раз! К {name} уже просто ничего не липнет (особенно люди противоположного пола), это абсолютный иммунитет! 🛡",
        90: f"🧛‍♂️ *ДРЕВНИЙ ОЛДХЭД!* 90 побед! {name} выходит на финишную прямую к великому залу славы ГЕЙмастеров! 🏛",
        100: f"🏆 *ЛЕГЕНДА ВЕКА! СТО КРАТНЫЙ ПИДОР!* 🎉💥 {name} полностью прошёл эту жизнь с обратной стороны! Исторический момент, чат, салютуйте главному боссу этой игры! 👑🍾"
    }

    # 1. Отправляем текст (как и было)
    is_anniversary = False # флаг, чтобы понять, круглое ли число
    
    if new_count == 5:
        await update.message.reply_text(f"🎉 *РАЗОГРЕВ ОКОНЧЕН!* {name} косячит уже 5-й раз! Начало положено, но до клуба великих данжн мастеров далеко! 🎖", parse_mode="Markdown")
        is_anniversary = True
    elif new_count in jokes:
        await update.message.reply_text(jokes[new_count], parse_mode="Markdown")
        is_anniversary = True
         # 2. Если это юбилей (5 или круглый десяток) — кидаем СЛУЧАЙНЫЙ стикер!
    if is_anniversary:
        random_sticker = random.choice(pidor_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_users()
    if len(users) < 1:
        await update.message.reply_text("В боте еще никто не зарегистрировался. Напишите /register")
        return

    already_winner = get_today_winner("krasavchik")
    if already_winner:
        username = f" (@{already_winner['username']})" if already_winner['username'] else ""
        await update.message.reply_text(f"Сегодня этот выбор уже сделан! 😎 Красавчик дня — {already_winner['first_name']}{username}")
        return

    opposite_id = get_opposite_winner_id("krasavchik")
    filtered_users = [u for u in users if u["user_id"] != opposite_id]

    if not filtered_users:
        await update.message.reply_text("Все участники уже заняли свои титулы на сегодня! Больше выбирать некого.")
        return

    # --- ИСПРАВЛЕННЫЙ БЛОК ЗАСТАВОК ---
    # Отправляем фразы как обычные сообщения в чат, БЕЗ реплая на команду
    chat_id = update.effective_chat.id
    for phrase in random.sample(KRAS_PHRASES, len(KRAS_PHRASES)):
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1)
    # ----------------------------------

    # Выбираем победителя по весам красавчика
    winner = weighted_choice(filtered_users, "kras_weight")

    # Считаем новое значение
    new_count = winner["kras_count"] + 1

    # Обновляем счетчик красавчиков в Supabase
    supabase.table("users").update({"kras_count": new_count}).eq("user_id", winner["user_id"]).execute()
    
    redistribute_weights(winner["user_id"], "kras_weight")
    save_daily_winner("krasavchik", winner["user_id"])

    username = f" (@{winner['username']})" if winner['username'] else ""
    # Финальный вердикт делаем красивым ответом (реплаем) на самое первое сообщение пользователя
    await update.message.reply_text(f"😎 Красавчик дня — {winner['first_name']}{username}")

    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ С ИЗДЁВКОЙ ----------------
    name = winner["first_name"]
    
    # Мемные стикеры для пидорских юбилеев (вставь сюда 3-5 разных ID)
    kras_stickers_pool = [
        'CAACAgIAAxkBAAERePpqQ3C50Eqg_2plBXsHEFEtGOtmnQACk1QAAgmZ4EkPKsG3ATUGIDwE',
        'CAACAgIAAxkBAAERePxqQ3FkKQTrDt2Kt3E3v09Q90uUzgAC5zMAAvyF0EhRH0ZM6KsQGjwE',
        'CAACAgIAAxkBAAEReP5qQ3GP592jnDm3vTPxPH5LqTK3rgACrhQAAo4n0EqxFZIn-u6dajwE',
        'CAACAgIAAxkBAAEReQABakNxn4mZ1mhxrJf0em63Qj9qEb8AAs4ZAAKJEBBKhq0wFniF8sA8BA',
        'CAACAgIAAxkBAAEReQJqQ3HbH2OkT4mcPqJovAXsFJh5bQAClyAAAt88OUtsjjyKWQ5bXjwE',
        'CAACAgIAAxkBAAEReQRqQ3Ldb-x4CbDRQhozMvG6zY9vqQACagADJeuTHyg3EZuaMZFnPAQ'
    ]

    jokes = {
        10: f"👑 *ОГО, 10 РАЗ!* {name}, аккуратнее на поворотах, а то нимб упадёт и ноги отдавит! Чат, расступаемся, тут идёт мисс/мистер Обаяние! 📸",
        20: f"🎩 *20 ПОБЕД!* {name} так часто выигрывает, что уже целует своё отражение в зеркале по утрам. Завязывай с самолюбованием, нам завидно! 🔥",
        30: f"🏆 *30-й СТРАЙК!* {name}, признайся, ты подкрутил этот код или просто подкупил бота? Чат требует проверку на коддинг! 🚨",
        40: f"✨ *40 РАЗ КРАСАВЧИК!* Уровень эго {name} превысил все допустимые нормы. Скоро тебе понадобится отдельная комната для твоей короны! 🗄",
        50: f"🎖 *ПОЛУВЕКОВОЙ ЮБИЛЕЙ!* 50 побед! {name}, мы скидываемся тебе на памятник при жизни в полный рост. Из чистого золота, естественно! 🏅",
        60: f"🎰 *60 ПОБЕД!* {name} официально признан главным нарциссом этого чата. Датчики привлекательности сгорели от такого пафоса! ⚡️",
        70: f"🛰 *КОСМИЧЕСКИЙ КРАСАВЧИК!* 70-й раз! {name}, твоё великолепие ослепляет даже спутники наблюдения! Надень маску, побереги наши глаза! 🌌",
        80: f"🛡 *80 РАЗ! СВЕРХЛЮДИ СРЕДИ НАС!* К {name} уже выстроилась очередь за автографами. Не забудь упомянуть этот чат, когда поедешь на Мисс/Мистер Вселенная! 🦾",
        90: f"🏛 *90 ПОБЕД!* {name} одной ногой в зале славы великих Победителей. Ещё чуть-чуть, и твоё лицо напечатают на обложках всех журналов! 🧛‍♂️",
        100: f"👑🍾 *ЛЕГЕНДА ВЕКА! СТОКРАТНЫЙ КРАСАВЧИК!* 🎉💥 {name} официально прошёл эту игру! 100 побед! Абсолютный рекордсмен, икона стиля и босс этого чата! Салют чемпиону! 🏆🌟"
    }

     # 1. Отправляем текст (как и было)
    is_anniversary = False # флаг, чтобы понять, круглое ли число
    
    if new_count == 5:
        await update.message.reply_text(f"🎉 *5 ПОБЕД!* {name} вступает в клуб самовлюбленных! Начало положено, но до настоящих победителей тебе ещё пилить и пилить! 🎖", parse_mode="Markdown")
        is_anniversary = True
    elif new_count in jokes:
        await update.message.reply_text(jokes[new_count], parse_mode="Markdown")
        is_anniversary = True
        
         # 2. Если это юбилей (5 или круглый десяток) — кидаем СЛУЧАЙНЫЙ стикер!
    if is_anniversary:
        random_sticker = random.choice(kras_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Функция get_users() уже возвращает только тех, у кого is_active == True
    users = get_users()
    if not users:
        await update.message.reply_text("В игре пока нет активных участников.")
        return

    # 1. Сортируем пользователей для топа Пидоров (от максимума к минимуму)
    pidors_sorted = sorted(users, key=lambda x: x["pidor_count"], reverse=True)
    
    # 2. Сортируем пользователей для топа Красавчиков (от максимума к минимуму)
    kras_sorted = sorted(users, key=lambda x: x["kras_count"], reverse=True)

    message = "📊 *СТАТИСТИКА*\n\n"

    # Формируем колонку / блок Пидоров
    message += "🤡 *Топ Пидоров чата:*\n"
    for i, user in enumerate(pidors_sorted, start=1):
        username = f" (@{user['username']})" if user['username'] else ""
        message += f"{i}. *{user['first_name']}{username}* — {user['pidor_count']} раз(а)\n"

    message += "\n" + "—" * 15 + "\n\n" # Визуальный разделитель блоков

    # Формируем колонку / блок Красавчиков
    message += "😎 *Топ Красавчиков чата:*\n"
    for i, user in enumerate(kras_sorted, start=1):
        username = f" (@{user['username']})" if user['username'] else ""
        message += f"{i}. *{user['first_name']}{username}* — {user['kras_count']} раз(а)\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def procents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Функция get_users() автоматически возвращает только тех, у кого is_active == True
    users = get_users()
    if not users:
        await update.message.reply_text("В игре пока нет активных участников.")
        return

    # Считаем суммарные веса только среди активных игроков
    total_p_weight = sum(user["pidor_weight"] for user in users)
    total_k_weight = sum(user["kras_weight"] for user in users)

    # 1. Сортируем пользователей по шансу стать Пидором (от большего к меньшему)
    # Сразу рассчитываем процент внутри сортировки, чтобы выстроить правильный топ
    pidors_by_chance = sorted(
        users, 
        key=lambda x: (x["pidor_weight"] / total_p_weight * 100) if total_p_weight > 0 else 0, 
        reverse=True
    )
    
    # 2. Сортируем пользователей по шансу стать Красавчиком (от большего к меньшему)
    kras_by_chance = sorted(
        users, 
        key=lambda x: (x["kras_weight"] / total_k_weight * 100) if total_k_weight > 0 else 0, 
        reverse=True
    )

    message = "🎯 *ТЕКУЩИЕ ШАНСЫ УЧАСТНИКОВ*\n\n"

    # Блок шансов на Пидора
    message += "🔥 *Шансы стать Пидором дня:*\n"
    for i, user in enumerate(pidors_by_chance, start=1):
        username = f" (@{user['username']})" if user['username'] else ""
        p_chance = (user["pidor_weight"] / total_p_weight * 100) if total_p_weight > 0 else 0
        message += f"{i}. *{user['first_name']}{username}* — {p_chance:.1f}%\n"

    message += "\n" + "—" * 15 + "\n\n" # Визуальный разделитель блоков

    # Блок шансов на Красавчика
    message += "✨ *Шансы стать Красавчиком дня:*\n"
    for i, user in enumerate(kras_by_chance, start=1):
        username = f" (@{user['username']})" if user['username'] else ""
        k_chance = (user["kras_weight"] / total_k_weight * 100) if total_k_weight > 0 else 0
        message += f"{i}. *{user['first_name']}{username}* — {k_chance:.1f}%\n"

    await update.message.reply_text(message, parse_mode="Markdown")

async def records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Функция get_users() автоматически возвращает только активных (is_active == True)
    users = get_users()
    if not users:
        await update.message.reply_text("В игре пока нет активных участников для фиксации рекордов.")
        return

    # Сортируем: по КРАСАВЧИКАМ (минус перед значением делает сортировку по убыванию),
    # а при равенстве — по ПИДОРАМ (без минуса, то есть по возрастанию).
    champions_sorted = sorted(users, key=lambda x: (-x["kras_count"], x["pidor_count"]))
    
    leader = champions_sorted[0]
    leader_username = f" (@{leader['username']})" if leader['username'] else ""

    # Проверяем, были ли вообще игры, чтобы не выводить пустой рекорд при нулевой статистике
    if leader["kras_count"] == 0 and leader["pidor_count"] == 0:
        await update.message.reply_text("⚖️ Статистика еще пуста, рекорды не зафиксированы. Пора крутить рулетку!")
        return

    message = (
        "🥇 *АБСОЛЮТНЫЙ ЧЕМПИОН ЧАТА* 🥇\n\n"
        f"Человек, которого фортуна целует в обе щеки, а радужные мысли обходят стороной. "
        f"Максимум благословений и минимум позора! Поприветствуйте легенду:\n\n"
        f"👑 *{leader['first_name']}{leader_username}*\n"
        f"   └ 😎 Красавчик: {leader['kras_count']} раз(а)\n"
        f"   └ 🤡 Пидор: {leader['pidor_count']} раз(а)\n\n"
        f"_Остальным соболезнуем, тренируйте удачу!_ 👇"
    )

    await update.message.reply_text(message, parse_mode="Markdown")
from datetime import timedelta

async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    # 1. Проверяем, что команду вызвали в группе
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Переводить стрелы можно только в групповых чатах!")
        return

    # 2. Проверяем, является ли вызвавший ПИДОРОМ СЕГОДНЯШНЕГО ДНЯ
    today_winner = get_today_winner("pidor")
    if not today_winner or today_winner["user_id"] != user.id:
        await update.message.reply_text("🤡 Ты не сегодняшний пидор дня, чтобы стрелки переводить. Сиди тихо!")
        return

        # 3. Проверяем КД команды (строго 7 дней с момента последнего использования)
    user_res = supabase.table("users").select("last_switch_date").eq("user_id", user.id).execute()
    if user_res.data and user_res.data[0]["last_switch_date"]:
        last_date = date.fromisoformat(user_res.data[0]["last_switch_date"])
        
        # Считаем разницу между сегодня и датой использования
        days_passed = (today - last_date).days
        
        if days_passed < 6:
            days_left = 6 - days_passed
            # Склоняем слово "день" в зависимости от остатка
            if days_left == 1:
                day_word = "день"
            elif days_left in [2, 3, 4]:
                day_word = "дня"
            else:
                day_word = "дней"
                
            await update.message.reply_text(
                f"❌ Ты уже использовал «карту UNO». \n"
                f"Твоя новая карта всё еще в процессе доставки! Доступ появится через *{days_left} {day_word}*."
            )
            await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReRpqQ3-pZ9QRME44W1Es3DPWTGUPNAACkAIAAladvQoy0qlxuNTQtTwE')
            return

    # 4. Проверяем, тегнул ли он кого-то
    if not context.args or not update.message.entities:
        await update.message.reply_text("❌ На кого стрелу переводим? Тегни жертву через @username!")
        return

    target_username = None
    for entity in update.message.entities:
        if entity.type == "mention":
            target_username = update.message.text[entity.offset:entity.offset + entity.length]
            break

    if not target_username:
        await update.message.reply_text("❌ Нужно именно тегнуть жертву через @упоминание.")
        return

    # Ищем жертву в нашей базе данных по юзернейму (без значка @)
    clean_username = target_username.replace("@", "")
    target_res = supabase.table("users").select("*").eq("username", clean_username).eq("is_active", True).execute()
    
    if not target_res.data:
        await update.message.reply_text(f"❌ Юзера {target_username} нет в рулетке или он ливнул!")
        return
    
    victim = target_res.data[0]

    # Защита от перевода на самого себя
    if victim["user_id"] == user.id:
        await update.message.reply_text("🎭 Перевести стрелу на самого себя? Гениально (нет).")
        return

    # Защита: нельзя перевести на Красавчика дня
    krasavchik_today = get_today_winner("krasavchik")
    if krasavchik_today and krasavchik_today["user_id"] == victim["user_id"]:
        await update.message.reply_text(f"🛡 Нельзя перевести стрелу на {target_username}, он сегодня неприкосновенный Красавчик дня!")
        return

        # Записываем стрелочнику дату использования команды
    supabase.table("users").update({"last_switch_date": str(today)}).eq("user_id", user.id).execute()

    # --- ИСПРАВЛЕННЫЙ БЛОК (УБРАН MARKDOWN ДЛЯ ЗАЩИТЫ ОТ ПАДЕНИЯ ИЗ-ЗА НИКНЕЙМОВ) ---
    intro = [
        f"🃏 МЕМНЫЙ РЕВЕРС! {user.first_name} активирует карту «UNO» и пытается перевести позор на {target_username}!",
        "🎲 Вероятность успеха всего 5%... Высшие силы взвешивают шансы...",
    ]
    for phrase in intro:
    # Без parse_mode бот гарантированно отправит сообщение с любым юзернеймом жертвы
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1.5)

    # Крутим шанс 5% (выбираем число от 1 до 100)
    is_success = random.randint(1, 100) <= 5

    # Вытаскиваем текущие данные стрелочника, чтобы узнать его реальный pidor_count
    current_user_data = supabase.table("users").select("pidor_count").eq("user_id", user.id).execute().data[0]
    current_pidor_count = current_user_data.get("pidor_count", 1)

    if is_success:
        # УДАЧА (5%): Перекидываем титул
        # 1. Откатываем стату и веса стрелочнику (уменьшаем его реальный счетчик на 1)
        supabase.table("users").update({
            "pidor_count": current_pidor_count - 1, 
            "pidor_weight": 90.0 
        }).eq("user_id", user.id).execute()
        
        # 2. Наказываем жертву
        supabase.table("users").update({
            "pidor_count": victim["pidor_count"] + 1,
            "pidor_weight": 65.0 
        }).eq("user_id", victim["user_id"]).execute()

        # 3. Меняем победителя дня в истории daily_winners
        supabase.table("daily_winners").update({"user_id": victim["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()

        await update.message.reply_text(
            f"💥 ЭТО ПРОСТО НЕВЕРОЯТНО! ЧАТ, СЕНСАЦИЯ! 💥\n\n"
            f"Карта UNO сработала! Магия 5% сработала!\n"
            f"👑 {user.first_name} полностью очищен от подозрений.\n\n"
            f"🤡 Новый официальный ПИДОР ДНЯ — {victim['first_name']} ({target_username})! Смирись с этим!"
        )
         # 📥 СТИКЕР УСПЕХА: Вставь сюда ID стикера, когда карта сработала (5%)
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQxqQ3c1Ul6X4NVVPO-Fd7SdNeiqIgACx04AAnJSgEuFrKam1iO89TwE')
    else:
        # НЕУДАЧА (95%): Стрела сорвалась, вес возвращается к 100
        supabase.table("users").update({"pidor_weight": 100.0}).eq("user_id", user.id).execute()
        
        await update.message.reply_text(
            f"❌ КАРТА UNO ПОРВАЛАСЬ ВО ВРЕМЯ ИСПОЛЬЗОВАНИЯ! {user.first_name}, боги рандома не помогли в этот раз.\n\n"
            f"Титул Пидора дня остается на тебе. В наказание твой процентаж аннулирован и...\n"
            f"Завтра у тебя будут большие шансы выпасть снова! 🤡\n"
            f"p.s. через недельку, можешь попробовать снова (за выдачу новой карты, 50р на карту)"
        )
        # 📥 СТИКЕР ПРОВАЛА: Вставь сюда ID стикера, когда карта порвалась (95%)
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    today = date.today()
    
    # Вытаскиваем данные конкретного юзера из Supabase
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not res.data:
        await update.message.reply_text("❌ Тебя еще нет в игре! Напиши /register")
        return
        
    player = res.data[0]
    
    # Проверяем статус КД карты UNO
    uno_status = "🟢 ГОТОВА К БОЮ!"
    if player.get("last_switch_date"):
        last_date = date.fromisoformat(player["last_switch_date"])
        days_passed = (today - last_date).days
        if days_passed < 7:
            days_left = 7 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            uno_status = f"🔴 НА ПЕРЕЗАРЯДКЕ (еще {days_left} {day_word})"

    username = f" (@{player['username']})" if player['username'] else ""
    message = (
        f"👤 *ЛИЧНОЕ ДОСЬЕ ИГРОКА*:\n\n"
        f"Участник: *{player['first_name']}{username}*\n"
        f"🤡 Статус Пидора: {player['pidor_count']} раз(а)\n"
        f"😎 Статус Красавчика: {player['kras_count']} раз(а)\n\n"
        f"🃏 *Карта UNO:* {uno_status}"
    )
    await update.message.reply_text(message, parse_mode="Markdown")

# ---------------- ЗАПУСК (ВЕБХУК) ----------------

# Переименуем функцию main в асинхронную
async def main():
    app = Application.builder().token(TOKEN).build()
# Инициализируем очередь задач, если она не создалась автоматически
    if app.job_queue is None:
         print("Критическая ошибка: Планировщик задач не инициализирован. Проверьте requirements.txt")
        
    # Добавляем все хэндлеры
    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("unreg", unreg))
    app.add_handler(CommandHandler("reset", reset_stats))
    app.add_handler(CommandHandler("pidor", pidor))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("procents", procents))
    app.add_handler(CommandHandler("switch", switch))
    app.add_handler(CommandHandler("records", records))
    app.add_handler(CommandHandler("mystats", my_stats))

    if RENDER_URL:
        print("Бот запускается в режиме Webhook на Render...")
        PORT = int(os.getenv("PORT", 10000))
        
        await app.initialize()
        # Принудительно запускаем планировщик задач для таймеров таймаута
        if app.job_queue:
            await app.job_queue.start()
            
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
        await app.start()
        print("Вебхук и Таймеры успешно запущены!")
        
        while True:
            await asyncio.sleep(3600)
    else:
        print("Бот запущен локально в режиме Polling!")
        app.run_polling()

if __name__ == "__main__":
    # Запускаем асинхронный main() через правильный asyncio.run()
    asyncio.run(main())
