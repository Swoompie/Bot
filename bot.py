print("СТАРТ БОТА")
import os
import random
import asyncio
from datetime import date

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
)
# Подключаем Supabase клиент
from supabase import create_client, Client

TOKEN = os.getenv("BOT_TOKEN")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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


# Инициализация клиента Supabase теперь будет работать через скрытые переменные
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


def redistribute_weights(winner_id, column_name):
    users = get_users()
    winner = next((u for u in users if u["user_id"] == winner_id), None)
    if not winner:
        return

    current_weight = winner[column_name]
    decrease = 40

    if current_weight <= 60:
        return

    new_weight = current_weight - decrease
    # Обновляем вес победителя в облаке
    supabase.table("users").update({column_name: new_weight}).eq("user_id", winner_id).execute()

    others = [u for u in users if u["user_id"] != winner_id]
    if others:
        bonus = decrease / len(others)
        for user in others:
            old_weight = user[column_name]
            supabase.table("users").update({column_name: old_weight + bonus}).eq("user_id", user["user_id"]).execute()

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
        "/duel @username — Вызвать на дуэль на минутную дуэль, и попытаться отстаять свою честь 🔫\n"
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
    
    # Проверяем существование
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not res.data or not res.data[0].get("is_active", True):
        await update.message.reply_text("Тебя и так нет в игре, можешь в окно выйти, лол.")
        return

    # Вместо удаления просто выключаем флаг активности и сбрасываем веса до базовых
    supabase.table("users").update({
        "is_active": False,
        "pidor_weight": 100.0,
        "kras_weight": 100.0
    }).eq("user_id", user.id).execute()
    
    await update.message.reply_text(f"🚪 {user.first_name} ты реально ливнул? Твоя статистика сохранена, так что не прощаемся - дешёвка!")

async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Обнуляем счетчики побед и возвращаем базовые веса всем игрокам в Supabase
    supabase.table("users").update({
        "pidor_count": 0, 
        "kras_count": 0, 
        "pidor_weight": 100.0, 
        "kras_weight": 100.0
    }).neq("user_id", 0).execute()  # .neq("user_id", 0) хак, чтобы обновить вообще всех юзеров разом
    
    # Полностью очищаем таблицу сегодняшних победителей
    supabase.table("daily_winners").delete().neq("user_id", 0).execute()
    
    await update.message.reply_text("🔄 *Вся статистика обнулена!* Счетчик подопытных сброшен, шансы участников снова равны.", parse_mode="Markdown")


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

    if new_count == 5:
        await update.message.reply_text(f"🎉 *РАЗОГРЕВ ОКОНЧЕН!* {name} косячит уже 5-й раз! Начало положено, но до клуба великих данжн мастеров далеко! 🎖", parse_mode="Markdown")
    elif new_count in jokes:
        await update.message.reply_text(jokes[new_count], parse_mode="Markdown")

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

    jokes = {
        10: f"👑 *ОГО, 10 РАЗ!* {name}, аккуратнее на поворотах, а то нимб упадёт и ноги отдавит! Чат, расступаемся, тут идёт мисс/мистер Обаяние! 📸",
        20: f"🎩 *20 ПОБЕД!* {name} так часто выигрывает, что уже целует своё отражение в зеркале по утрам. Завязывай с самолюбованием, нам завидно! 🔥",
        30: f"🏆 *30-й СТРАЙК!* {name}, признайся, ты подкрутил этот код или просто подкупил бота? Чат требует проверку на коддинг! 🚨",
        40: f"✨ *40 РАЗ КРАСАВЧИК!* Уровень эго {name} превысил все допустимые нормы. Скоро тебе понадобится отдельная комната для твоей короны! 🗄",
        50: f"🎖 *ПОЛУВЕКОВОЙ ЮБИЛЕЙ!* 50 побед! {name}, мы скидываемся тебе на памятник при жизни в полный рост. Из чистого золота, естественно! 🏅",
        60: f"🎰 *60 ПОБЕД!* {name} официально признан главным нарциссом этого чата. Датчики привлекательности сгорели от такого пафоса! ⚡️",
        70: f"🛰 *КОСМИЧЕСКИЙ КРАСАВЧИК!* 70-й раз! {name}, твоё великолепие ослепляет даже спутники наблюдения! Надень маску, побереги наши глаза! 🌌",
        80: f"🛡 *80 РАЗ! СВЕРХЛЮДИ СРЕДИ НАС!* К {name} уже выстроилась очередь за автографами. Не забудь упомянуть этот чат, когда поедешь на Мисс/Мистер Вселенная! 🦾",
        90: f"🏛 *90 ПОБЕД!* {name} одной ногой в зале славы великих Чэдов. Ещё чуть-чуть, и твоё лицо напечатают на обложках всех журналов! 🧛‍♂️",
        100: f"👑🍾 *ЛЕГЕНДА ВЕКА! СТОКРАТНЫЙ КРАСАВЧИК!* 🎉💥 {name} официально прошёл эту игру! 100 побед! Абсолютный рекордсмен, икона стиля и босс этого чата! Салют чемпиону! 🏆🌟"
    }

    if new_count == 5:
        await update.message.reply_text(f"🎉 *5 ПОБЕД!* {name} вступает в клуб самовлюбленных! Начало положено, но до настоящих Чэдов тебе ещё пилить и пилить! 🎖", parse_mode="Markdown")
    elif new_count in jokes:
        await update.message.reply_text(jokes[new_count], parse_mode="Markdown")

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

    # 3. Проверяем КД команды (1 раз в календарную неделю)
    # Вытаскиваем данные стрелочника из базы
    user_res = supabase.table("users").select("last_switch_date").eq("user_id", user.id).execute()
    if user_res.data and user_res.data[0]["last_switch_date"]:
        last_date = date.fromisoformat(user_res.data[0]["last_switch_date"])
        # Считаем, сколько дней прошло с последнего понедельника
        current_week_start = today - timedelta(days=today.weekday())
        if last_date >= current_week_start:
            await update.message.reply_text("❌ Ты уже использовал «карту UNO» на этой неделе. Лимит исчерпан!")
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

    # Интригующие сообщения
    intro = [
        f"🃏 *МЕМНЫЙ РЕВЕРС!* {user.first_name} активирует карту «UNO» и пытается перевести позор на {target_username}!",
        "🎲 Вероятность успеха всего 5%... Высшие силы взвешивают шансы...",
    ]
    for phrase in intro:
        await context.bot.send_message(chat_id=chat_id, text=phrase, parse_mode="Markdown")
        await asyncio.sleep(1.5)

    # Крутим шанс 5% (выбираем число от 1 до 100)
    is_success = random.randint(1, 100) <= 5

    if is_success:
        # УДАЧА (5%): Перекидываем титул
        # 1. Откатываем стату и веса стрелочнику (ведь он спасся)
        supabase.table("users").update({
            "pidor_count": user_res.data[0].get("pidor_count", 1) - 1, # если у тебя в коде каунт уже вырос, уменьшаем на 1
            "pidor_weight": 100.0 # возвращаем вес в базу
        }).eq("user_id", user.id).execute()
        
        # 2. Наказываем жертву
        supabase.table("users").update({
            "pidor_count": victim["pidor_count"] + 1,
            "pidor_weight": 60.0 # даем штраф
        }).eq("user_id", victim["user_id"]).execute()

        # 3. Меняем победителя дня в истории daily_winners
        supabase.table("daily_winners").update({"user_id": victim["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()

        await update.message.reply_text(
            f"💥 *ЭТО ПРОСТО НЕВЕРОЯТНО! ЧАТ, СЕНСАЦИЯ!* 💥\n\n"
            f"Карта UNO сработала! Магия 5% сработала!\n"
            f"👑 {user.first_name} полностью очищен от подозрений.\n\n"
            f"🤡 Новый официальный ПИДОР ДНЯ — {victim['first_name']} ({target_username})! Смирись с этим!", 
            parse_mode="Markdown"
        )
    else:
        # НЕУДАЧА (95%): Стрела сорвалась, вес возвращается к 100
        supabase.table("users").update({"pidor_weight": 100.0}).eq("user_id", user.id).execute()
        
        await update.message.reply_text(
            f"❌ *КАРТА UNO ПОРВАЛАСЬ ВО ВРЕМЯ ИСПОЛЬЗОВАНИЯ!* {user.first_name}, боги рандома не помогли в этот раз.\n\n"
            f"Титул Пидора дня остается на тебе. В наказание твой процентаж аннулирован и..."
            f"Завтра у тебя будут большие шансы выпасть снова! 🤡"
            f"p.s. через недельку, можешь попробовать снова (за выдачу новой карты, 50р на карту)", 
            parse_mode="Markdown"
        )

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что команду вызвали в группе/чате, а не в личке у бота
    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Дуэли разрешены только в групповых чатах!")
        return

    challenger = update.effective_user  # Тот, кто вызвал команду
    
    # Проверяем, тегнул ли кого-то вызывающий
    if not context.args or not update.message.entities:
        await update.message.reply_text("❌ Кого на дуэль-то вызывать? Тегни соперника через @username!")
        return

       # Ищем упомянутого пользователя (улучшенный поиск для любых чатов)
    target_username = None
    
    # Способ 1: Ищем через entities
    if update.message.entities:
        for entity in update.message.entities:
            if entity.type == "mention":
                target_username = update.message.text[entity.offset:entity.offset + entity.length]
                break

    # Способ 2: Если Telegram скрыл entity в этом чате, вытаскиваем руками из текста
    if not target_username and context.args:
        for arg in context.args:
            if arg.startswith("@"):
                target_username = arg
                break

    if not target_username:
        await update.message.reply_text("❌ Ошибка! Нужно именно тегнуть соперника через @упоминание.")
        return

    # Защита от дуэли с самим собой
    if challenger.username and f"@{challenger.username}".lower() == target_username.lower():
        await update.message.reply_text("🤡 Ты не можешь вызвать на дуэль самого себя. Психушка на другой улице!")
        return

    # Формируем имя вызывающего (с тегом, если есть)
    challenger_name = f"@{challenger.username}" if challenger.username else challenger.first_name

    # Кидаем жребий 50/50
    # True — победил бросивший вызов, False — победил тот, кого тегнули
    challenger_wins = random.choice([True, False])

    # Смешные подводки перед результатом дуэли
    duel_intro = [
        f"⚔️ *ДУЭЛЬ ЧЕСТИ!* {challenger_name} бросает перчатку в лицо {target_username}!",
        "💨 Воздух в чате накалился до предела... Секунданты замерли...",
        "🔫 Звучит выстрел стартового пистолета! Иииии..."
    ]

    # Отправляем заставки по очереди, как в рулетке
    chat_id = update.effective_chat.id
    for phrase in duel_intro:
        await context.bot.send_message(chat_id=chat_id, text=phrase, parse_mode="Markdown")
        await asyncio.sleep(1)

    # Выдаем финальный результат реплаем на исходный вызов
    if challenger_wins:
        winner = challenger_name
        loser = target_username
    else:
        winner = target_username
        loser = challenger_name

    result_text = (
        f"🎉 В ожесточенном споре и ментальной битве побеждает {winner}! \n\n"
        f"🤡 А вот {loser} официально признается *ПИДОРОМ ЭТОЙ МИНУТЫ!* \n"
        f"_Чат, закидайте его помидорами!_"
    )

    await update.message.reply_text(result_text, parse_mode="Markdown")


# ---------------- ЗАПУСК (ВЕБХУК) ----------------

# Переименуем функцию main в асинхронную
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(CommandHandler("switch", switch))
    app.add_handler(CommandHandler("unreg", unreg))
    app.add_handler(CommandHandler("reset", reset_stats))
    app.add_handler(CommandHandler("pidor", pidor))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("procents", procents))
    app.add_handler(CommandHandler("records", records))

    if RENDER_URL:
        print("Бот запускается в режиме Webhook на Render...")
        PORT = int(os.getenv("PORT", 10000))
        
        # Для вебхуков на Python 3.14+ инициализируем приложение вручную перед стартом
        await app.initialize()
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
        await app.start()
        print("Вебхук успешно запущен и слушает порт!")
        
        # Оставляем бота запущенным в бесконечном цикле, пока сервер работает
        while True:
            await asyncio.sleep(3600)
    else:
        print("Бот запущен локально в режиме Polling!")
        app.run_polling()

if __name__ == "__main__":
    # Запускаем асинхронный main() через правильный asyncio.run()
    asyncio.run(main())
