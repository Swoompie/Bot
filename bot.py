print("СТАРТ БОТА")
import os
import random
import asyncio
import json
from datetime import date
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from supabase import create_client, Client
from io import BytesIO

ADMIN_TG_ID = 646119167

# Настройка Supabase и бота
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

# ---------------- КОД ТИХОГО БЭКАПА ----------------
async def silent_backup(context: ContextTypes.DEFAULT_TYPE):
    try:
        # Выкачиваем актуальные таблицы из Supabase
        users_data = supabase.table("users").select("*").execute().data
        winners_data = supabase.table("daily_winners").select("*").execute().data
        
        # Собираем их в один словарь
        backup_dict = {
            "backup_date": str(date.today()),
            "tables": {
                "users": users_data,
                "daily_winners": winners_data
            }
        }
        
        # Упаковываем в JSON-файл прямо в оперативной памяти
        json_data = json.dumps(backup_dict, ensure_ascii=False, indent=4)
        file_stream = BytesIO(json_data.encode('utf-8'))
        file_stream.name = f"backup_{date.today()}.json"
        
        # Отправляем файл строго админу в личку (в чате этого никто не увидит)
        await context.bot.send_document(
            chat_id=ADMIN_TG_ID,
            document=file_stream,
            caption=f"📦 *Ежедневный фоновый слепок базы*\n📅 Дата: {date.today()}\n\nВсе данные успешно зарезервированы!",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"❌ Ошибка фонового бэкапа: {e}")
        
async def manual_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Доступ только для тебя!
    if update.effective_user.id != ADMIN_TG_ID:
        await update.message.reply_text("🤡 Куда руки тянешь? Эта команда только для Создателя бота!")
        return
        
    await update.message.reply_text("⏳ Формирую слепок базы данных вручную, секунду...")
    # Просто вызываем уже готовую логику бэкапа и шлем в текущий чат (или личку)
    await silent_backup(context)

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
            # Победитель получает штраф -30.0, но не ниже капа 70.0
            new_winner_weight = max(70.0, current_weight - 30.0)
            supabase.table("users").update({weight_column: new_winner_weight}).eq("user_id", winner_id).execute()
            break

    # 2. Пересчитываем веса для ВСЕХ ОСТАЛЬНЫХ участников розыгрыша
    for user in users:
        if user["user_id"] == winner_id:
            continue  # Пропускаем сегодняшнего победителя

        current_weight = user[weight_column]

        if current_weight < 100.0:
            # Если игрок в зоне защиты (недавно выигрывал) — плавно возвращаем к норме на +3.0
            new_weight = min(100.0, current_weight + 3.0)
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
        "/switch @username — Использовать карту UNO и перевести от себя пидора (Шанс 5/10/20%?, КД 6 дней) 🃏\n"
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
        # Если он есть, но отключен (is_active == False) — ВОЗВРАЩАЕМ В ИГРУ
        if not player.get("is_active", True):
            supabase.table("users").update({"is_active": True}).eq("user_id", user.id).execute()
            
            # Текст для тех, кто ливал и вернулся
            await update.message.reply_text(f"✅ {user.first_name}, с возвращением, дешёвка! Твоя старая статистика восстановлена. Больше не бегай!")
            
            # 📥 СТИКЕР ДЛЯ ВОЗВРАЩЕНЦА: вставь сюда ID стикера (например, клоун или "я вернулся")
            await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReQ5qQ3ghClnZvA6qP2Cx0lGm8NIjBwACMlIAAv-BOEl-zu7LwscR5DwE')
        else:
            # Если он и так активен в базе
            await update.message.reply_text(f"Куда ты жмёшь, {user.first_name}? Ты уже и так в игре, расслабься!")
        return

    # 2. Если пользователя вообще нет в базе — СОЗДАЕМ С НУЛЯ
    supabase.table("users").insert({
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "pidor_weight": 100.0,
        "kras_weight": 100.0,
        "pidor_count": 0,
        "kras_count": 0,
        "is_active": True  
    }).execute()
    
    # Текст для абсолютного новичка
    await update.message.reply_text(f"🎉 Добро пожаловать в наше казино, {user.first_name}! Ты успешно зарегистрирован в рулетке с нуля. Твои шансы равны 100%, готовься к прокрутам!")
    
    # 📥 СТИКЕР ДЛЯ НОВИЧКА: вставь сюда ID стикера (например, добро пожаловать в клуб или приветствие)
    await update.message.reply_sticker(sticker='CAACAgIAAxkBAAERfsVqSV-02VP19CvVOwAB7so57DV18eIAAtAeAALu9ShIWVtSKDbs0pY8BA')

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
    # ИСПРАВЛЕНО: Полная защита базы. Доступ только для тебя!
    if update.effective_user.id != ADMIN_TG_ID:
        await update.message.reply_text("🤡 Куда руки тянешь? Сбрасывать казино может только Создатель бота!")
        return

    # Обнуляем счетчики побед и возвращаем базовые веса всем игрокам в Supabase
    supabase.table("users").update({
        "pidor_count": 0, 
        "kras_count": 0, 
        "pidor_weight": 100.0, 
        "kras_weight": 100.0
    }).neq("user_id", 0).execute()
    
    # Полностью очищаем таблицу "победителей"
    supabase.table("daily_winners").delete().neq("user_id", 0).execute()
    
    await update.message.reply_text("🔄 *Вся статистика обнулена!* Счетчик подопытных сброшен, шансы участников снова равны.", parse_mode="Markdown")
    await update.message.reply_sticker(sticker='CAACAgQAAxkBAAEReRBqQ3htVR15fuIwV3C_4QUWL8_xxQACbhwAAltJOVMTctyzCRD65jwE')

async def pidor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    
    # 1. Вытаскиваем только АКТИВНЫХ игроков (is_active == True)
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
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
    chat_id = update.effective_chat.id
    for phrase in random.sample(PIDOR_PHRASES, len(PIDOR_PHRASES)):
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1)
    
    # Выбираем победителя
    winner = weighted_choice(filtered_users, "pidor_weight")
    new_count = winner["pidor_count"] + 1

    # Обновляем счетчик в Supabase
    supabase.table("users").update({"pidor_count": new_count}).eq("user_id", winner["user_id"]).execute()
    
    redistribute_weights(winner["user_id"], "pidor_weight")
    save_daily_winner("pidor", winner["user_id"])

    username = f" (@{winner['username']})" if winner['username'] else ""
    await update.message.reply_text(f"🤡 Пидор дня — {winner['first_name']}{username}")

    # --- МИКРО-ПОДСКАЗКА ПРО КАРТУ UNO ---
    uno_status_text = ""
    # Изящная тактическая памятка без раскрытия сухих цифр весов
    rules_memo = (
        "\n\n📊 *Сетка шансов на перевод:* "
        "\n └ 👑 На Красавчика дня — *5%*"
        "\n └ 🃏 На обычного мирного — *10%*"
        "\n └ 🎯 На проигравшего в монетку — *20%* _(если таковой появится, но при провале твои шансы на Пидора взлетят!)_"
    )

    if winner.get("last_switch_date"):
        last_date = date.fromisoformat(winner["last_switch_date"])
        days_passed = (today - last_date).days
        
        if days_passed < 6:
            days_left = 6 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            uno_status_text = f"\n\n🃏 _Кстати, твоя карта UNO на перезарядке. Ждать еще {days_left} {day_word}._"
        else:
            uno_status_text = f"\n\n🃏 *ОП-ПА! Твоя карта UNO ПЕРЕЗАРЯЖЕНА!* Можешь попробовать защититься, пиши: `/switch @username`{rules_memo}"
    else:
        # Если чел вообще ни разу не юзал карту
        uno_status_text = f"\n\n🃏 *ОП-ПА! Твоя карта UNO ГОТОВА!* Защищайся, пиши: `/switch @username`{rules_memo}"

    # Если есть статус — докидываем его отдельным тихим сообщением для Пидора
    if uno_status_text:
        await context.bot.send_message(chat_id=chat_id, text=uno_status_text, parse_mode="Markdown")

    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ ----------------
    name = winner["first_name"]

    pidor_stickers_pool = [
        'CAACAgIAAxkBAAEReO5qQ22SmZkDyLqKq0vP6-ELBjPTUAACjnQAAihj2EtnaWFztIKP7DwE',
        'CAACAgIAAxkBAAERePBqQ27RxFYFJcHGEaZ9kPTDkhO1EAACSk4AAuAKOUlEfzO0OLfimzwE',
        'CAACAgIAAxkBAAERePJqQ27guzCAFe3IqBMNm9Rsq4tlIwACxVQAAsfrOEk6oSm-WVc9QjwE',
        'CAACAgIAAxkBAAERePRqQ28nWDjJOWNP0amyxIzJUiJwgAACckYAArr9OUlyV8svBKf4PzwE',
        'CAACAgIAAxkBAAERePZqQ29RyTAuFB6ryyH6BApiXpfNtgAC3EoAAmsNOUmTv1vWKkSg7TwE',
        'CAACAgIAAxkBAAERePhqQ29fvKDHMorjySaOzDQ013gcdgACNUoAAoRQOEkf13J-sHIrqTwE'
    ]
        
    jokes = {
        10: f"🎂 *ОГО, 10 РАЗ!* {name}, поздравляем! Первый юбилей на дне. Давай, расскажи всем, что это просто «случайность» и «рандом сломался»! 🤡",
        20: f"👑 *УЖЕ 20 ПОБЕД!* {name} официально переходит в Высшую лигу сомнительных парней. Тебе уже пора выдавать именную корону из картона и скотча! 🎪",
        30: f"🚨 *30-й СТРАЙК!* {name}, это уже не шутка, это карьера. Ты стабилен как швейцарские часы. Стабильно плох, но всё же! 🛑",
        40: f"🗄 *КРИЗИС СРЕДНЕГО ВОЗРАСТА!* {name} отмечает 40 побед! Архив компромата переполнен! 📂",
        50: f"🎖 *ПОЛУВЕКОВОЙ ЮБИЛЕЙ!* 50 раз! {name} получает золотую медаль и пожизненную путевку в гейбар! 🏅",
        60: f"🎰 *МАСТЕР СВОЕГО ДЕЛА!* 60 побед у {name}! Датчики сомнительных мыслей просто зашкаливают, не шали! ⚡️",
        70: f"🚨 *КОСМИЧЕСКИЙ УРОВЕНЬ!* 70-й раз! {name} твоё гейство видно даже со спутников наблюдения! 🌌",
        80: f"🦾 *ТИФЛОНОВЫЙ СТАТУС!* 80 раз! К {name} уже просто ничего не липнет (особенно люди противоположного пола), это абсолютный иммунитет! 🛡",
        90: f"🧛‍♂️ *ДРЕВНИЙ ОЛДХЭД!* 90 побед! {name} выходит на финишную прямую к великому залу славы ГЕЙмастеров! 🏛",
        100: f"🏆 *ЛЕГЕНДА ВЕКА! СТО КРАТНЫЙ ПИДОР!* 🎉💥 {name} полностью прошёл эту жизнь с обратной стороны! Исторический момент, чат, салютуйте главному боссу этой игры! 👑🍾"
    }

    is_anniversary = False
    
    if new_count == 5:
        await update.message.reply_text(f"🎉 *РАЗОГРЕВ ОКОНЧЕН!* {name} косячит уже 5-й раз! Начало положено, но до клуба великих данжн мастеров далеко! 🎖", parse_mode="Markdown")
        is_anniversary = True
    elif new_count in jokes:
        await update.message.reply_text(jokes[new_count], parse_mode="Markdown")
        is_anniversary = True
         
    if is_anniversary:
        random_sticker = random.choice(pidor_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Вытаскиваем только АКТИВНЫХ игроков (is_active == True)
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
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

    # --- БЛОК ЗАСТАВОК ---
    chat_id = update.effective_chat.id
    for phrase in random.sample(KRAS_PHRASES, len(KRAS_PHRASES)):
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1)
    
    # 1. Первичный честный выбор фаворита по весам красавчика
    favorit = weighted_choice(filtered_users, "kras_weight")
    final_winner = favorit  # По умолчанию побеждает он

    # 2. КРУТИМ ШАНС АНОМАЛИИ (30%)
    is_anomaly = random.randint(1, 100) <= 30
    favorit_username = f" (@{favorit['username']})" if favorit['username'] else ""

    if is_anomaly and len(filtered_users) > 1:
        # ================= 🎰 ПУТЬ Б: СРАБОТАЛА АНОМАЛИЯ (30%) =================
        # Втихую выбираем второго кандидата из оставшихся (исключая фаворита)
        other_users = [u for u in filtered_users if u["user_id"] != favorit["user_id"]]
        contender = random.choice(other_users)
        contender_username = f" (@{contender['username']})" if contender['username'] else ""

        # Выдаем интригующий текст аномалии в чат
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎰 *Красавчик дня определён... СТОП, ЧТО?!* 🎰\n\n"
                 f"Должен был победить *{favorit['first_name']}{favorit_username}*, но монетка внезапно упала РЕБРОМ! 💥\n"
                 f"Датчики крутости зафиксировали аномалию. На кону дикий баттл!\n\n"
                 f"⚡️ *{favorit['first_name']}* против *{contender['first_name']}{contender_username}*! ⚡️\n"
                 f"Бросаем финальный кубик судьбы 1-3, 4-6... подкидываем монетку (50/50)...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(3.5) # Пауза для нагнетания валидола
        
        # Мгновенный баттл 50/50 между ними
        if random.randint(1, 100) <= 50:
            final_winner = favorit
            coin_loser = contender  # Неудачник монетки
            
            await update.message.reply_text(
                f"🪙 *МОНЕТКА ОСТАЕТСЯ НА СТОРОНЕ ПЕРВОГО!*\n\n"
                f"😎 В жестком баттле свою крутость защищает *{final_winner['first_name']}{favorit_username}*! Справедливость восторжествовала!\n"
                f"🤡 А проигравший *{coin_loser['first_name']}* получает утешительные повышенные шансы к Красавчику на завтра!",
                parse_mode="Markdown"
            )
        else:
            final_winner = contender
            coin_loser = favorit  # Неудачник монетки
            
            await update.message.reply_text(
                f"🪙 *ОГРАБЛЕНИЕ В ФИНАЛЕ! ОНА ПЕРЕВЕРНУЛАСЬ!*\n\n"
                f"😎 Монетка решает в пользу претендента! *{final_winner['first_name']}{contender_username}* вырывает победу из рук фаворита!\n"
                f"🤡 А обворованный *{coin_loser['first_name']}* получает утешительные повышенные шансы к Красавчику на завтра!",
                parse_mode="Markdown"
            )

        # 💾 СОХРАНЯЕМ НЕУДАЧНИКА В БАЗУ ДАННЫХ SUPABASE (Сейв от спячки Render)
        save_daily_winner("coin_loser", coin_loser["user_id"])
        
        # ИСПРАВЛЕНО: Твой верный вариант с индексом [0]
        loser_base = supabase.table("users").select("kras_weight").eq("user_id", coin_loser["user_id"]).execute().data
        current_kras_weight = loser_base[0]["kras_weight"] if loser_base else 100.0
        
        supabase.table("users").update({"kras_weight": current_kras_weight + 50.0}).eq("user_id", coin_loser["user_id"]).execute()
    else:
        # ================= ✨ ПУТЬ А: СТАНДАРТНЫЙ ПРОКРУТ (70%) =================
        await update.message.reply_text(f"😎 Красавчик дня — {final_winner['first_name']}{favorit_username}")

    # Считаем новое значение побед для финального счастливчика
    new_count = final_winner["kras_count"] + 1

    # Обновляем счетчик красавчиков в Supabase
    supabase.table("users").update({"kras_count": new_count}).eq("user_id", final_winner["user_id"]).execute()
    
    # Пересчитываем веса под финального победителя и сохраняем его в историю дня
    redistribute_weights(final_winner["user_id"], "kras_weight")
    save_daily_winner("krasavchik", final_winner["user_id"])

    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ С ИЗДЁВКОЙ ----------------
    name = final_winner["first_name"]
    
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

    is_anniversary = False 
    
    if new_count == 5:
        await update.message.reply_text(f"🎉 *5 ПОБЕД!* {name} вступает в клуб самовлюбленных! Начало положено, но до настоящих победителей тебе ещё пилить и пилить! 🎖", parse_mode="Markdown")
        is_anniversary = True
    elif new_count in jokes:
        await update.message.reply_text(jokes[new_count], parse_mode="Markdown")
        is_anniversary = True

    if is_anniversary:
        random_sticker = random.choice(kras_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)

    # --- ТИХИЙ БЭКАП ПОСЛЕ ИГРЫ ---
    context.application.create_task(silent_backup(context))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ИСПРАВЛЕНО: Вытаскиваем всех и берем строго активных участников
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
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
    # ИСПРАВЛЕНО: Вытаскиваем всех и считаем шансы СТРОГО среди активных участников
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
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
    # ИСПРАВЛЕНО: Вытаскиваем всех и ищем чемпиона СТРОГО среди активных участников
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
    if not users:
        await update.message.reply_text("В игре пока нет активных участников для фиксации рекордов.")
        return

    # Сортируем: по КРАСАВЧИКАМ (по убыванию), а при равенстве — по ПИДОРАМ (по возрастанию)
    champions_sorted = sorted(users, key=lambda x: (-x["kras_count"], x["pidor_count"]))
    
    leader = champions_sorted[0]
    leader_username = f" (@{leader['username']})" if leader['username'] else ""

    # Проверяем, были ли вообще игры
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

async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Юзать карту UNO можно только в групповых чатах!")
        return

    # 1. Проверяем, является ли вызвавший ПИДОРОМ СЕГОДНЯШНЕГО ДНЯ
    today_winner = get_today_winner("pidor")
    if not today_winner or today_winner["user_id"] != user.id:
        await update.message.reply_text("🤡 Ты не сегодняшний пидор дня, чтобы активировать карту UNO. Сиди тихо!")
        return

      # 2. Проверяем КД команды (6 дней)
    user_res = supabase.table("users").select("last_switch_date").eq("user_id", user.id).execute()
    
    # Проверяем, что игрок есть в базе и у него вообще заполнена дата прошлого КД
    if user_res.data and len(user_res.data) > 0 and user_res.data[0].get("last_switch_date"): 
        last_date = date.fromisoformat(user_res.data[0]["last_switch_date"]) 
        days_passed = (today - last_date).days
        
        # Если прошло меньше 6 дней — включаем железный отлуп со стикером
        if days_passed < 6:
            days_left = 6 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            
            # Бот четко выведет, сколько дней осталось ждать пацанам
            await update.message.reply_text(f"❌ Твоя карта UNO всё еще на перезарядке! Доступ появится через *{days_left} {day_word}*.", parse_mode="Markdown")
            await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReRpqQ3-pZ9QRME44W1Es3DPWTGUPNAACkAIAAladvQoy0qlxuNTQtTwE')
            return

     # 3. Парсим жертву
    if not context.args or not update.message.entities:
        await update.message.reply_text("❌ На кого переводим карту UNO? Тегни жертву через @username!")
        return

    target_username = None
    for entity in update.message.entities:
        if entity.type == "mention":
            target_username = update.message.text[entity.offset:entity.offset + entity.length]
            break

    if not target_username:
        await update.message.reply_text("❌ Нужно именно тегнуть игрока через /switch @упоминание.")
        return

    clean_username = target_username.replace("@", "")
    target_res = supabase.table("users").select("*").eq("username", clean_username).eq("is_active", True).execute()
    
    if not target_res.data or len(target_res.data) == 0:
        await update.message.reply_text(f"❌ Юзера {target_username} нет в рулетке или он ливнул!")
        return
    
    # ТЕПЕРЬ СОЗДАЕМ ЖЕРТВУ
    victim = target_res.data[0]

    if victim["user_id"] == user.id:
        await update.message.reply_text("🎭 Переводить карту на самого себя? Оригинально, но нет.")
        return

    # Проверяем, является ли это ВТОРОЙ попыткой перевода
    is_retry_attempt = context.user_data.get("switch_retry", False)
    
    # 🔥 И ВОТ ТЕПЕРЬ БЕЗОПАСНАЯ УМНАЯ ПРОВЕРКА КРАСАВЧИКА (Бот знает, кто такой victim)
    kras_today_res = supabase.table("daily_winners").select("*").eq("game_date", str(today)).eq("role", "krasavchik").execute()
    
    is_robbing_chad = False
    if kras_today_res.data and len(kras_today_res.data) > 0:
        if kras_today_res.data[0]["user_id"] == victim["user_id"]:
            is_robbing_chad = True

    # 🔍 ИСПРАВЛЕНО ДЛЯ БАЗЫ ДАННЫХ: Вытаскиваем неудачника монетки напрямую из Supabase
    coin_loser_res = supabase.table("daily_winners").select("user_id").eq("game_date", str(today)).eq("role", "coin_loser").execute()
    
    is_coin_loser_target = False
    if coin_loser_res.data and len(coin_loser_res.data) > 0:
        # ДОБАВЛЕН ИНДЕКС: база возвращает список, заходим внутрь первой строки
        if coin_loser_res.data[0]["user_id"] == victim["user_id"]:
            is_coin_loser_target = True

    # 4. ВЫДАЕМ ИНТРО-ТЕКСТ С УЧЕТОМ ДИНАМИЧЕСКИХ ШАНСОВ
    if is_robbing_chad:
        intro = [
            f"👑 КРАЖА ВЕКА! Пидор дня {user.first_name} активирует карту «UNO» против Красавчика {target_username}!",
            "🎲 Это Королевское Ограбление! Шанс 5%. Если сработает, титулы поменяются, а карта ОСТАНЕТСЯ ЦЕЛОЙ! 🔥",
        ]
    elif is_coin_loser_target:
        # Специальная жесткая фраза для добивания неудачника монетки
        intro = [
            f"🎯 ДОБИВАНИЕ РАНЕНОГО! {user.first_name} активирует карту «UNO» против {target_username}!",
            "🎲 Он сегодня и так эпично проиграл в монетку, а мы решили его добить? Похвально, но наказуемо! Шанс перевода повышен до 20%! 🔥\n⚠️ Внимание: в случае провала твои шансы на Пидора взлетят до небес!",
        ]
    else:
        if is_retry_attempt:
            intro = [
                f"🔥 ВТОРОЙ ШАНС! {user.first_name} трясущимися руками активирует карту «UNO» ПОВТОРНО против мирного {target_username}!",
                "🎲 На этот раз боги шутить не будут. Вероятность 15%. Либо пан, либо пропал...",
            ]
        else:
            intro = [
                f"🃏 МЕМНЫЙ РЕВЁРС! {user.first_name} активирует карту «UNO» и пытается скинуть клеймо Пидора на {target_username}!",
                "🎲 Шанс перевода 10%... Высшие силы взвешивают шансы...",
            ]

    for phrase in intro:
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1.5)

    # --- 🎰 РАЗДЕЛЬНЫЙ РАСЧЕТ ШАНСОВ (5% / 10% / 15% / 20%) ---
    if is_robbing_chad:
        success_chance = 5
    elif is_coin_loser_target:
        success_chance = 20  # Повышенный шанс на добивание
    elif is_retry_attempt:
        success_chance = 15  # Раздельный повышенный второй шанс на мирного
    else:
        success_chance = 10  # Раздельный базовый шанс на мирного

    is_success = random.randint(1, 100) <= success_chance
    
    # Запрашиваем свежие данные стрелочника из базы для точного вычитания
    current_user_data = supabase.table("users").select("*").eq("user_id", user.id).execute().data
    current_user = current_user_data[0] if current_user_data else None

    # Добавляем фиксацию штрафного веса 120.0 при провале добивания
    if not is_success and is_coin_loser_target and current_user:
        # Перебиваем стандартный вес на жесткие 120.0
        supabase.table("users").update({"last_switch_date": str(today), "pidor_weight": 120.0}).eq("user_id", user.id).execute()
        await update.message.reply_text(
            f"❌ КАРМА СУЩЕСТВУЕТ! Карта UNO СГОРЕЛА при попытке добить раненого!\n\n"
            f"{user.first_name}, боги рандома наказали тебя за жестокость. Карта уходит на КД, а твой штрафной процент Пидора взлетает до небес! 🤡",
            parse_mode="Markdown"
        )
        await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
        return  # Прерываем функцию, провал обработан особым образом!

    if is_success and current_user:
        # ================= 🎉🎉🎉 УСПЕШНЫЙ ПЕРЕВОД (5%) 🎉🎉🎉 =================
        context.user_data.pop("switch_retry", None) # очищаем память ретрая
        
        if is_robbing_chad:
            # 👑 ПУТЬ А: УСПЕШНОЕ ОГРАБЛЕНИЕ КРАСАВЧИКА (КД НЕ ЗАПИСЫВАЕМ!)
                        
            # 1. Обновляем Стрелочника (минус пидор, плюс красавчик, веса 95/80)
            supabase.table("users").update({
                "pidor_count": max(0, current_user["pidor_count"] - 1), 
                "kras_count": current_user["kras_count"] + 1, 
                "pidor_weight": 95.0, 
                "kras_weight": 80.0
            }).eq("user_id", user.id).execute()
            
            # 2. Обновляем Жертву (минус красавчик, плюс пидор, веса 70/70)
            supabase.table("users").update({
                "kras_count": max(0, victim["kras_count"] - 1), 
                "pidor_count": victim["pidor_count"] + 1, 
                "pidor_weight": 70.0, 
                "kras_weight": 70.0
            }).eq("user_id", victim["user_id"]).execute()
            
            # 3. Перебиваем историю сегодняшнего дня в daily_winners строго по ролям
            supabase.table("daily_winners").update({"user_id": victim["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()
            supabase.table("daily_winners").update({"user_id": user.id}).eq("game_date", str(today)).eq("role", "krasavchik").execute()

            await update.message.reply_text(
                f"💥 БОЖЕ МОЙ, ЭТО ИСТОРИЧЕСКИЙ МОМЕНТ! КАРТА ОСТАЕТСЯ ЦЕЛОЙ! 💥\n\n"
                f"Королевское ограбление завершилось полным триумфом!\n"
                f"😎 {user.first_name} ворует корону и СТАНОВИТСЯ НОВЫМ КРАСАВЧИКОМ ДНЯ!\n\n"
                f"🤡 А вот {victim['first_name']} ({target_username}) с позором падает на дно и признается ПИДОРОМ ДНЯ!"
            )
            await update.message.reply_sticker(sticker='CAACAgIAAxkBAAERfwtqSi0WKXA0-slyXjuDMUAC14PGkAAC6BMAAp7K8UkQAAGdV1VM7UI8BA')

        else:
            # 🃏 ПУТЬ Б: УСПЕШНЫЙ ОБЫЧНЫЙ ПЕРЕВОД НА МИРНОГО (Записываем КД)
            # Записываем стрелочнику дату использования карты UNO
            supabase.table("users").update({"last_switch_date": str(today)}).eq("user_id", user.id).execute()
            
            # Обновляем Стрелочника: минус позор, и даем ему вес 85.0 
            supabase.table("users").update({
                "pidor_count": max(0, current_user["pidor_count"] - 1), 
                "pidor_weight": 85.0
            }).eq("user_id", user.id).execute()
            
            # Обновляем Жертву: плюс позор, и даем штрафной вес 80.0
            supabase.table("users").update({
                "pidor_count": victim["pidor_count"] + 1, 
                "pidor_weight": 80.0
            }).eq("user_id", victim["user_id"]).execute()
            
            # Точечно перебиваем историю сегодняшнего дня в daily_winners
            supabase.table("daily_winners").update({"user_id": victim["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()

            # --- РАЗВЕТВЛЕНИЕ ТЕКСТА И СТИКЕРОВ В ЗАВИСИМОСТИ ОТ ПОПЫТКИ ---
            if is_retry_attempt:
                # ИСПРАВЛЕНО: Текст обновлен под новые 15% раздельного свитча
                await update.message.reply_text(
                    f"🦊 *КАК ОН ЭТО ДЕЛАЕТ?! ХИТРЫЙ ЛИС В ДЕЛЕ!* 🦊\n\n"
                    f"Первая карта порвалась, но со второго шанса {user.first_name} совершает невозможное и выбивает 15%!\n"
                    f"👑 Ты полностью очищен от подозрений, легенда кубиков!\n\n"
                    f"🤡 А вот {victim['first_name']} ({target_username}) официально становится ПИДOPOМ ДНЯ со второй подачи! Отлетай!",
                    parse_mode="Markdown"
                )
                await update.message.reply_sticker(sticker='CAACAgIAAxkBAAERg8xqT1rvV4e9QOkd5krbAdwHGMbORQACrB8AAi-rqEswnXHdk_VAETwE')
            else:
                # ИСПРАВЛЕНО: Текст обновлен под новые 10% базового свитча
                await update.message.reply_text(
                    f"💥 *КАРТА ПЕРЕВЕДЕНА!* Магия 10% сработала!\n\n"
                    f"👑 {user.first_name} полностью очищен от подозрений.\n"
                    f"🤡 Новый официальный ПИДОР ДНЯ — {victim['first_name']} ({target_username})! Смирись!",
                    parse_mode="Markdown"
                )
                await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReQxqQ3c1Ul6X4NVVPO-Fd7SdNeiqIgACx04AAnJSgEuFrKam1iO89TwE')
            
            # После успешного исхода в любом случае очищаем пометку ретрая из памяти бота
            context.user_data.pop("switch_retry", None)

    else:
        # ================= ❌❌❌ ВЫПАЛ ПРОВАЛ (КАРТА СГОРЕЛА ИЛИ ОСЕЧКА) =================
        if is_robbing_chad:
            # На Красавчика только ОДНА попытка. Сразу вешаем КД на 6 дней за провал!
            supabase.table("users").update({"last_switch_date": str(today), "pidor_weight": 100.0}).eq("user_id", user.id).execute()
            await update.message.reply_text(
                f"❌ ТРЮК ПРОВАЛЕН! Королевская карта UNO СГОРЕЛА ВО ВРЕМЯ ПОПЫТКИ КРАЖИ! \n\n"
                f"{user.first_name}, попытка ограбить Красавчика провалилась, боги рандома изымают карту на 6 дней.\n"
                f"Титул Пидора дня остается на тебе! 🤡"
            )
            await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
            
        else:
            # Провал при обычном переводе на мирного (Включается логика Второго Шанса)
            if is_retry_attempt:
                # Вторая попытка на мирного провалилась — сжигаем карту окончательно
                supabase.table("users").update({"last_switch_date": str(today), "pidor_weight": 85.0}).eq("user_id", user.id).execute()
                context.user_data.pop("switch_retry", None)

                await update.message.reply_text(
                    f"💀 ПОЛНОЕ ФИАСКО, СТРЕЛОЧНИК! Второй шанс тоже провален! \n\n"
                    f"{user.first_name}, твоя карта UNO окончательно ПРЕВРАТИЛАСЬ В ПЕПЕЛ. "
                    f"Кулдаун 6 дней активирован. Завтра твои шансы максимальны! 🤡"
                )
                await update.message.reply_sticker(sticker='CAACAgIAAxkBAAERg9tqT2Lb7EssiCPdH7XeEz1W5sbVswAC6S8AApkAAYhJDcx-Vp6-Sco8BA')
            else:
                # Первый провал на мирного — крутим скрытые 5% на "Второй Шанс"
                has_second_chance = random.randint(1, 100) <= 5
                
                if has_second_chance:
                    context.user_data["switch_retry"] = True # включаем триггер повтора
                    await update.message.reply_text(
                        f"⚡️ ОПА, ОСЕЧКА... ИЛИ НЕТ?! ⚡️\n\n"
                        f"{user.first_name}, твоя карта UNO задымилась, но боги рандома дали тебе **ВТОРОЙ ШАНС**! "
                        f"Кулдаун НЕ активирован! Быстро пиши команду `/switch` ещё раз на любую мирную цель, пока лазейка не закрылась! 🃏"
                    )
                    await update.message.reply_sticker(sticker='CAACAgIAAxkBAAERg85qT110qgTm1RJWyqRuKm0QwbCoLwAC9B4AAiNcOEtYh2FNKYLHdDwE')
                else:
                    # Стандартный провал на мирного с первого раза
                    supabase.table("users").update({"last_switch_date": str(today), "pidor_weight": 90.0}).eq("user_id", user.id).execute()
                    await update.message.reply_text(
                        f"❌ КАРТА UNO ПОРВАЛАСЬ! {user.first_name}, перевод сорвался и полетел обратно в тебя.\n\n"
                        f"Титул остается на тебе. Карта уходит на перезарядку на 6 дней. 🤡"
                    )
                    await update.message.reply_sticker(sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')

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
        if days_passed < 6:
            days_left = 6 - days_passed
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

async def main():
    # Собираем приложение бота
    app = Application.builder().token(TOKEN).build()
    
    # ИСПРАВЛЕНО: Ровный отступ для проверки планировщика
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
    app.add_handler(CommandHandler("backup", manual_backup))

    if RENDER_URL:
        print("Бот запускается в режиме Webhook на Render...")
        PORT = int(os.getenv("PORT", 10000))
        
        # Правильный асинхронный запуск вебхука без зависания потока
        await app.initialize()
        if app.job_queue:
            await app.job_queue.start()
            
        await app.start()
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
        print("Вебхук и Таймеры успешно запущены!")
        
        # Вместо кривого while True используем встроенный асинхронный ожидалщик библиотеки
        from asyncio import Event
        await Event().wait()
    else:
        # ИСПРАВЛЕНО: Безопасный запуск поллинга для тестов на ПК
        print("Бот запущен локально в режиме Polling!")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        from asyncio import Event
        await Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
