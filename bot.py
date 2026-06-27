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
        "/reset — Стереть всю статистику побед 🔄\n"
        "/unreg — Выйти из рулетки и удалить данные 🚪\n"
        "/help — Показать это сообщение"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем, есть ли юзер в Supabase
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if res.data:
        await update.message.reply_text(f"Вы уже зарегистрированы, {user.first_name}!")
        return

    # Если нет — добавляем запись в облако
    supabase.table("users").insert({
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "pidor_weight": 100.0,
        "kras_weight": 100.0,
        "pidor_count": 0,
        "kras_count": 0
    }).execute()
    
    await update.message.reply_text(f"✅ {user.first_name} успешно зарегистрирован в рулетке!")

async def unreg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Проверяем существование пользователя
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not res.data:
        await update.message.reply_text("Вы и так не зарегистрированы в рулетке.")
        return

    # Удаляем пользователя из базы данных
    supabase.table("users").delete().eq("user_id", user.id).execute()
    await update.message.reply_text(f"🚪 {user.first_name} успешно ливнул из рулетки. Ваши очки обнулены!")

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

    for phrase in random.sample(PIDOR_PHRASES, len(PIDOR_PHRASES)):
        await update.message.reply_text(phrase)
        await asyncio.sleep(1)

    # Выбираем победителя, используя имя колонки весов из Supabase
    winner = weighted_choice(filtered_users, "pidor_weight")

    # Рассчитываем новое количество побед
    new_count = winner["pidor_count"] + 1

    # Обновляем счетчик пидоров в Supabase
    supabase.table("users").update({"pidor_count": new_count}).eq("user_id", winner["user_id"]).execute()
    
    redistribute_weights(winner["user_id"], "pidor_weight")
    save_daily_winner("pidor", winner["user_id"])

    username = f" (@{winner['username']})" if winner['username'] else ""
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

    for phrase in random.sample(KRAS_PHRASES, len(KRAS_PHRASES)):
        await update.message.reply_text(phrase)
        await asyncio.sleep(1)

    # Выбираем победителя по весам красавчика
    winner = weighted_choice(filtered_users, "kras_weight")

    # Считаем новое значение
    new_count = winner["kras_count"] + 1

    # Обновляем счетчик красавчиков в Supabase
    supabase.table("users").update({"kras_count": new_count}).eq("user_id", winner["user_id"]).execute()
    
    redistribute_weights(winner["user_id"], "kras_weight")
    save_daily_winner("krasavchik", winner["user_id"])

    username = f" (@{winner['username']})" if winner['username'] else ""
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
    users = get_users()
    if not users:
        await update.message.reply_text("В базе данных пока нет зарегистрированных участников.")
        return

    message = "📊 *Общая статистика рулетки:*\n\n"
    for user in users:
        username = f" (@{user['username']})" if user['username'] else ""
        message += f"👤 *{user['first_name']}{username}*:\n   🤡 Пидор: {user['pidor_count']} раз(а) | 😎 Красавчик: {user['kras_count']} раз(а)\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def procents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_users()
    if not users:
        await update.message.reply_text("В базе данных пока нет зарегистрированных участников.")
        return

    total_p_weight = sum(user["pidor_weight"] for user in users)
    total_k_weight = sum(user["kras_weight"] for user in users)

    message = "🎯 *Текущие шансы участников:*\n\n"
    for user in users:
        username = f" (@{user['username']})" if user['username'] else ""
        p_chance = (user["pidor_weight"] / total_p_weight * 100) if total_p_weight > 0 else 0
        k_chance = (user["kras_weight"] / total_k_weight * 100) if total_k_weight > 0 else 0
        
        message += f"👤 *{user['first_name']}{username}*:\n   Шанс на пидора: {p_chance:.1f}% | Шанс на красавчика: {k_chance:.1f}%\n\n"

    await update.message.reply_text(message, parse_mode="Markdown")

# ---------------- ЗАПУСК (ВЕБХУК) ----------------

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("unreg", unreg))
    app.add_handler(CommandHandler("reset", reset_stats))
    app.add_handler(CommandHandler("pidor", pidor))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("procents", procents))

    # Автоматическое определение режима запуска (Локально или на Render)
    if RENDER_URL:
        print("Бот запускается в режиме Webhook на Render...")
        PORT = int(os.getenv("PORT", 10000))
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
    else:
        print("Бот запущен локально в режиме Polling!")
        app.run_polling()


if __name__ == "__main__":
    main()
