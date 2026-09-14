print("СТАРТ БОТА")
import os
import random
import asyncio
import json
from datetime import date, datetime, timedelta
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
    "🛰️ Получаем данные со спутников наблюдения...",
    "🤡 Сверяем биометрию с базой данных клоунов...",
    "🕵️‍♂️ Изучаем историю браузера участников...",
    "📜 Разворачиваем свиток древних косяков...",
    "📻 Ловим тайные сигналы из кулуаров...",
    "🔎 Сканируем чат на наличие подозрительной активности...",
    "🚧 Внимание! Обнаружена критическая утечка адекватности...",
    "🖨️ Печатаем ордер на принудительное клеймение...",
    "🗄️ Перебираем старые папки с позорными мемами...",
    "🧨 Атмосфера накаляется, стрелка позорометра дрожит...",
    "🎭 Маски сброшены! Запускаем финальный анализ грехов...",
    "🧬 Сверяем ДНК с реестром главных бедолаг чата...",
    "🧼 Готовим мыло для чистки кармы...",
    "🛎️ Звонок из Турнирного Комитета, протокол активирован...",
    "🛎️ Звонок из отдела по борьбе с адекватностью...",
    "🎱 Скрытая кость Крупье катится по столу...",
    "🌪️ Ворвался вихрь рандома, сейчас кого-то привалит...",
    "🧾 Подсчитываем общую сумму кринжа за неделю...",
    "🛑 Сигнализация чатека взревела, обнаружен нарушитель...",
    "🪓 Пробиваем дно по спец-тарифу казино...",
    "🦨 Наводка подтвердилась, источник душности локализован...",
    "💊 Раздаем таблетки от глупости, но кому-то не хватило...",
    "🧪 Выводим формулу идеального косячника на сегодня...",
    "⛓️ Наручники позора начищены, конвой уже выехал...",
    "🎪 Труппа бродячего цирка определила нового лидера...",
    "☠️ Кости брошены, пиратский совет выносит чёрную метку...",
    "📉 График адекватности чата пробил Марианскую впадину..."
]

KRAS_PHRASES = [
    "🔥 Замеряем температуру крутости...",
    "📸 Подсчитываем удачные фотографии...",
    "🎩 Проверяем наличие природного обаяния...",
    "🏆 Сверяем данные с реестром красавчиков...",
    "✨ Калибруем датчики привлекательности...",
    "👑 Готовим королевский трон к примерке...",
    "🌟 Включаем прожекторы на полную мощность...",
    "💎 Сканируем чат на наличие скрытых бриллиантов...",
    "⚡ Вспышка стиля! Уровень харизмы пробивает потолок...",
    "🥂 Разливаем виртуальное шампанское фаворитам...",
    "🦄 Проверяем участников на запредельную исключительность...",
    "📈 График сексуальности резко пошёл вверх...",
    "🪞 Зеркало, зеркало на стене, кто прекрасней в этой весне?...",
    "🚀 Ракетные двигатели пафоса запущены...",
    "🕺 Проверяем чёткость утренней походки...",
    "🎟️ Билет на пьедестал почёта загружается...",
    "⚜️ Аристократический совет казино начинает заседание...",
    "🎨 Прорисовываем нимб над будущим победителем...",
    "👑 Наденьте очки, сейчас в чате станет слишком ярко...",
    "🎬 Камера, мотор! Запускаем кастинг на главную роль...",
    "🏎️ Выезжаем на гоночный трек чистой эстетики...",
    "💎 Алмазный фонд чата пополнится новым экспонатом...",
    "🌌 Созвездия сошлись, боги флекса указывают на одного...",
    "🎸 Огненное соло на гитаре в честь будущего красавчика...",
    "🦁 Проверяем альфа-самочность местных ковбоев...",
    "💸 Все фишки казино летят на сектор максимального пафоса...",
    "🎙️ Микрофон включен, трибуны скандируют имя чемпиона...",
    "🌊 Накатила волна непревзойденного стиля и шарма...",
    "🔮 Магический шар зафиксировал аномальный концентрат красоты...",
    "🦅 Орёл Лиги Дуэлей расправляет крылья над фаворитом..."
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


def g_text(player_obj, boy_str, girl_str):
    """
    Универсальный гендерный фильтр Салуна. 
    Принимает объект игрока из базы и два варианта текста.
    """
    if player_obj and player_obj.get("gender") == "girl":
        return girl_str
    return boy_str


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
            # Победитель получает штраф -30.0. 
            # Ограничение в 70.0 полностью убрано, вес может падать глубоко вниз.
            # Ставим жесткий нижний пол в 1.0, чтобы вес не ушел в минус.
            new_winner_weight = max(1.0, current_weight - 30.0)
            supabase.table("users").update({weight_column: new_winner_weight}).eq("user_id", winner_id).execute()
            break

    # 2. Пересчитываем веса для ВСЕХ ОСТАЛЬНЫХ участников розыгрыша (кто сегодня отдыхает)
    for user in users:
        if user["user_id"] == winner_id:
            continue  # Пропускаем сегодняшнего победителя

        current_weight = user[weight_column]

        # === 🚨 ТВОЯ НОВАЯ МАТЕМАТИКА: ТУРБО-КАМБЭК ДО 80.0 🚨 ===
        if current_weight < 80.0:
            # На всём промежутке от 1.0 до 80.0 вес летит вверх по +10.0 за раз!
            new_weight = min(80.0, current_weight + 10.0)
            
        elif current_weight < 100.0:
            # Когда перешагнули 80.0 — плавно дотягиваем до нормы на +3.0
            new_weight = min(100.0, current_weight + 3.0)
            
        else:
            # Если игрок НЕ выигрывал, и его вес равен 100 или выше — даем микро-прирост +1.0 (шанс растет).
            # Но если его вес за прошлые дни улетел слишком высоко (выше 120.0),
            # система плавно сдувает излишки на -2.0 обратно к балансу, чтобы не было вечных фаворитов.
            if current_weight > 120.0:
                new_weight = max(100.0, current_weight - 2.0)
            else:
                new_weight = current_weight + 1.0

        # Обновляем веса текущего юзера в Supabase
        supabase.table("users").update({weight_column: new_weight}).eq("user_id", user["user_id"]).execute()
    
    # === 📅 ЕЖЕНЕДЕЛЬНЫЙ АВТОСБРОС ЗАВИСШИХ ДУЭЛЕЙ ПО ПОНЕДЕЛЬНИКАМ ===
    # weekday() == 0 — это строго понедельник. Сжигаем несыгранные перчатки.
    if date.today().weekday() == 0:
        supabase.table("users").update({"duel_target_id": None}).neq("user_id", 0).execute()

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
        "/switch @username — Использовать карту UNO и перевести от себя пидора (КД 6 дней) 🃏\n"
        "/dice — Кинуть кубик кармы (2 в неделю) , но надо быть осторожным, возможны аномальные колебания процентов 🎲\n"
        "/duel @username — Устроить дикую перестрелку, за честь 🔫\n"
        "/mimic @username — Мимикрировать под другого игрока с удвоением статуса, КД 14 дней 🎭\n"
        "/mystats — Узнать свою статистику и карту UNO 👀\n"
        "/unostats — Узнать свои переводы карты UNO 👀\n"
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
        "dice_count": 0,
        "dice_start_balance": 0.0,
        "is_active": True,
        "last_switch_date": None,
        "mimic_target_id": None,    
        "last_mimic_date": None,
        "duel_target_id": None,
        "duel_wins": 0,
        "duel_losses": 0,
        "duel_count": 0
    }).execute()
    
    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перевели приветствие на HTML, прямой send_message по chat_id и добавили инструкцию для девчонок
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎉 <b>Добро пожаловать в наше казино, {user.first_name}!</b>\n\n"
            f"Ты успешно зарегистрирован в рулетке с нуля. Твои стартовые шансы равны 100%, готовься к утренним прокрутам! 🎰\n\n"
            f"👩‍🦰 <b>Важное инфо для прекрасных леди чата:</b> Напиши команду <code>/girl</code>, чтобы Крупье в казино обращался к тебе уважительно и правильно склонял все глаголы в игре! 💅"
        ),
        parse_mode="HTML"
    )
    
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
    # Собираем динамический глагол и финальный подкол для парня / девушки
    livnul_text = g_text(player, "реально ливнул", "реально ливнула")
    deshevka_text = g_text(player, "- дешёвка! 🤡", "- ну и ладно, больно надо! 💅")

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🚪 <b>{user.first_name}</b>, ты {livnul_text}? Твоя статистика бережно сохранена в архивах казино, так что не прощаемся {deshevka_text}",
        parse_mode="HTML"
    )

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
        "kras_weight": 100.0,
        "dice_count": 0,
        "dice_start_balance": 0.0,
        "last_switch_date": None,
        "mimic_target_id": None,
        "last_mimic_date": None,
        "duel_target_id": None,
        "duel_wins": 0,
        "duel_losses": 0,
        "duel_count": 0
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
        # ЖЕЛЕЗНЫЙ ФИКС: Явно заставляем Telegram читать строку как HTML. Теперь подчёркивания бессильны!
        await update.message.reply_text(
            f"Сегодня этот выбор уже сделан! 🤡 Пидор дня — {already_winner['first_name']}{username}",
            parse_mode="HTML"
        )
        return

    opposite_id = get_opposite_winner_id("pidor")
    filtered_users = [u for u in users if u["user_id"] != opposite_id]

    if not filtered_users:
        await update.message.reply_text("Все участники уже заняли свои титулы на сегодня! Больше выбирать некого.")
        return

    # === ИСПРАВЛЕННЫЙ БЛОК ЗАСТАВОК: Берёт 5 рандомных фраз из мешка ===
    chat_id = update.effective_chat.id
    for phrase in random.sample(PIDOR_PHRASES, 5): # <-- ПОСТАВИЛИ ЦИФРУ 5!
        await context.bot.send_message(chat_id=chat_id, text=phrase)
        await asyncio.sleep(1)

    # Выбираем победителя по умолчанию
    winner = weighted_choice(filtered_users, "pidor_weight")

    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Отправляем напрямую через send_message по chat_id!
    # Теперь удаление сообщения Артёма больше никогда не подвесит бота.
    username = f" (@{winner['username']})" if winner['username'] else ""
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🤡 Пидор дня — {winner['first_name']}{username}"
    )

    # === 🤡 МНОЖИТЕЛЬ ПОЗОРА С ПОД КРУТКОЙ ОТ СТРИКА МАКС-ШАНСА В SUPABASE ===
    total_pidor_weight = sum(u["pidor_weight"] for u in users)
    max_chat_pidor_weight = max(u["pidor_weight"] for u in filtered_users)
    pidor_chance = (winner["pidor_weight"] / total_pidor_weight) * 100
    
    multiplier = 1
    multiplier_text = ""
    is_accumulated_loser = False

    # ЖЕЛЕЗНО ИСПРАВЛЕНО: При равном максимальном позоре стрик капает обоим!
    for u in filtered_users:
        if u["pidor_weight"] >= max_chat_pidor_weight:
            current_streak = u.get("pidor_streak", 0) or 0
            supabase.table("users").update({"pidor_streak": current_streak + 1}).eq("user_id", u["user_id"]).execute()
        else:
            supabase.table("users").update({"pidor_streak": 0}).eq("user_id", u["user_id"]).execute()

    # Считываем свежий стрик Пидора для победителя
    winner_res = supabase.table("users").select("pidor_streak").eq("user_id", winner["user_id"]).execute()
    streak_days = winner_res.data[0]["pidor_streak"] if (winner_res.data and len(winner_res.data) > 0) else 0

    # Если победитель — это фаворит, и его стрик удержания топа длится 3 дня или дольше
    if winner["pidor_weight"] == max_chat_pidor_weight and streak_days >= 3:
        is_accumulated_loser = True
        
        # Крутим скрытую кость от 1 до 100
        bonus_roll = random.randint(1, 100)
        
        # === 🤡 ЗЕРКАЛЬНАЯ НАСТРОЙКА ВЕСОВ ПОЗОРА (ШКАЛА 5 / 10 / 15 ДНЕЙ) ===
        if streak_days >= 15:
            # 15+ дней удержания Топ-1 шанса: Осечки нет! х5 равен ровно 15% (от 86 до 100)
            if bonus_roll <= 35:
                multiplier = 2
                multiplier_text = "🎪 *ЦИРКОВАЯ КУРТКА (х2)!!!* Скрытая кость бьёт наотмашь — лови двойной позор и *+2 к счётчику* позора! "
            elif bonus_roll <= 85:
                multiplier = 3
                multiplier_text = "📣 *ПАРАД ПОЗОРА (х3)!!!* Матрица казино взломана мега-застоем — забирай сразу *+3 пидора* в досье! "
            else:
                multiplier = 5
                multiplier_text = "💀 *ТОТАЛЬНЫЙ АПОКАЛИПСИС СТАТИСТИКИ (х5)!!!!!* Смертельный джекпот за рекордные 15+ дней топа! Получай *+5 позоров* разом! 🎪🤡"
        
        elif streak_days >= 10:
            # 10-14 дней удержания Топ-1 шанса: Осечка падает до 5%, х5 поднят до 10%
            if bonus_roll <= 45:
                multiplier = 2
                multiplier_text = "🎪 *ЦИРКОВАЯ КУРТКА (х2)!!!* Скрытая кость бьёт наотмашь — лови двойной позор и *+2 к счётчику* позора! "
            elif bonus_roll <= 85:
                multiplier = 3
                multiplier_text = "📣 *ПАРАД ПОЗОРА (х3)!!!* Матрица казино взломана мега-застоем — забирай сразу *+3 пидора* в досье! "
            elif bonus_roll <= 90:
                multiplier = 1  # Осечка множителя, бот промолчит для секретности!
            else:
                multiplier = 5
                multiplier_text = "💀 *ТОТАЛЬНЫЙ АПОКАЛИПСИС СТАТИСТИКИ (х5)!!!!!* Смертельный джекпот за рекордные 10+ дней топа! Получай *+5 позоров* разом! 🎪🤡"
        
        elif streak_days >= 5:
            # 5-9 дней удержания Топ-1 шанса: Базовые шансы для запуска колеса
            if bonus_roll <= 50:
                multiplier = 2
                multiplier_text = "🎪 *ЦИРКОВАЯ КУРТКА (х2)!!!* Скрытая кость бьёт наотмашь — лови двойной позор и *+2 к счётчику* позора! "
            elif bonus_roll <= 80:
                multiplier = 3
                multiplier_text = "📣 *ПАРАД ПОЗОРА (х3)!!!* Матрица казино взломана мега-застоем — забирай сразу *+3 пидора* в досье! "
            elif bonus_roll <= 95:
                multiplier = 1  # Осечка множителя, бот промолчит для секретности!
            else:
                multiplier = 5
                multiplier_text = "💀 *ТОТАЛЬНЫЙ АПОКАЛИПСИС СТАТИСТИКИ (х5)!!!!!* Смертельный джекпот за рекордные 5+ дней топа! Получай *+5 позоров* разом! 🎪🤡"

    # Рассчитываем итоговую статистику с учётом множителя позора
    new_count = winner["pidor_count"] + multiplier
    supabase.table("users").update({"pidor_count": new_count}).eq("user_id", winner["user_id"]).execute()
    
    # Сбрасываем стрик победителя обратно в 0
    supabase.table("users").update({"pidor_streak": 0}).eq("user_id", winner["user_id"]).execute()

    # Полная изоляция никнейма от багов разметки Телеграма (в скобки)
    w_username_display = f" (@{winner['username']})" if winner.get('username') else ""
    safe_winner_name = f"{winner['first_name']}{w_username_display}"

    # Бот подаст голос только в том случае, если МНОЖИТЕЛЬ ПОЗОРА СРАБОТАЛ (х2, х3, х5)
    if is_accumulated_loser and multiplier > 1 and multiplier_text:
        # Собираем динамические гендерные слова для сегодняшней жертвы рулетки
        favorit_title = g_text(final_winner, "накопленный фаворит клейма", "накопленная фаворитка клейма")
        uderzhival_text = g_text(final_winner, "удерживал", "удерживала")
        schet_title = g_text(final_winner, "позорный счёт", "позорный счёт леди")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎰 <b>АКТИВАЦИЯ МНОЖИТЕЛЯ ПОЗОРА!</b> 🎰\n\n"
                f"Поскольку {favorit_title} <b>{safe_winner_name}</b> {uderzhival_text} максимальный шанс стать Пидором дня уже <b>{streak_days} дн.</b> подряд, казино активирует бонусное колесо наказаний!\n\n"
                f"{multiplier_text}\n\n"
                f"📊 <i>Личная статистика обновлена. Текущий {schet_title}: {new_count}</i>"
            ),
            parse_mode="HTML"
        )
        if multiplier == 5:
            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgUAAxkBAAERr4pqeX-dpAQpHvj3CZnAcPY0_UmGSQACgggAAjiksVVM5Vj4fvPn0z0E')

    # === 🎪 ПОЗОРНЫЙ ВИНСТРИК ПИДОРА (БЕЗБАГОВЫЙ СБРОС) ===
    # 1. Железный сброс в один клик: обнуляем позорный стрик ВСЕМ, кроме сегодняшнего призера
    supabase.table("users").update({"pidor_win_streak": 0}).neq("user_id", winner["user_id"]).execute()

    # 2. Победителю накидываем +1 к позорному стрику
    current_win_streak = winner.get("pidor_win_streak", 0) or 0
    new_win_streak = current_win_streak + 1
    supabase.table("users").update({"pidor_win_streak": new_win_streak}).eq("user_id", winner["user_id"]).execute()

    # 3. Проверяем и обновляем ВЕЧНЫЙ ИСТОРИЧЕСКИЙ АНТИРЕКОРД подряд в базе данных
    max_pidor_streak = winner.get("max_pidor_win_streak", 0) or 0
    if new_win_streak > max_pidor_streak:
        supabase.table("users").update({"max_pidor_win_streak": new_win_streak}).eq("user_id", winner["user_id"]).execute()

    # 4. Если бедолага ловит клеймо 3 дня подряд или дольше — закидываем мемами!
    if new_win_streak >= 3:
        await asyncio.sleep(1)
        
        # Рассчитываем правильное окончание для дней (3 дня, 5 дней)
        day_word = "дня" if new_win_streak in [3, 4] else "дней"
        
        # Собираем динамические гендерные глаголы и местоимения
        umudryaetsya_text = g_text(final_winner, "умудряется", "умудрилась")
        gender_pronoun = g_text(final_winner, "Его проценты сдулись", "Её проценты растаяли")
        legenda_title = g_text(final_winner, "этого легендарного ковбоя", "эту легендарную леди")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🚨 <b>КОНЦЕНТРАЦИЯ НЕВЕЗЕНИЯ ПОЛУЧЕНА!</b> 🎪\n\n"
                f"Это историческое пробитие дна! <b>{safe_winner_name}</b> {umudryaetsya_text} стать Пидором дня уже <b>{new_win_streak} {day_word} подряд</b>! 😭\n"
                f"{gender_pronoun} до абсолютного минимума, но проклятие рандома казино неумолимо! Запишите {legenda_title} в анналы позора чата! 🤡💣"
            ),
            parse_mode="HTML"
        )

    # Пересчитываем веса под финального победителя и сохраняем его в историю дня
    redistribute_weights(winner["user_id"], "pidor_weight")
    save_daily_winner("pidor", winner["user_id"])

    # === 🎭 БЛОК КАРТЫ МИМИКРИИ: КРАЖА ПИДОРА ===
    mimic_hunter_res = supabase.table("users").select("*").eq("mimic_target_id", winner["user_id"]).execute()
    
    is_mimic_triggered = False
    celebrator_name = winner["first_name"]
    celebrator_count = new_count
    final_pidor_user = winner  # по умолчанию Пидор — это победитель рулетки

    if mimic_hunter_res.data and len(mimic_hunter_res.data) > 0:
        mimic_user = mimic_hunter_res.data[0] # берем индекс первого юзера из базы!
        is_mimic_triggered = True
        final_pidor_user = mimic_user  # теперь финальный Пидор для карты UNO — это Мимик!
        
        # 1. ОТМЕНЯЕМ ПОЗОР ПОСТРАДАВШЕГО
        supabase.table("users").update({"pidor_count": winner["pidor_count"]}).eq("user_id", winner["user_id"]).execute()
        
        # 2. УДВАИВАЕМ ПОЗОР МИМИКУ (+2 вместо +1)
        celebrator_count = mimic_user["pidor_count"] + 2
        supabase.table("users").update({
            "pidor_count": celebrator_count,
            "mimic_target_id": None
        }).eq("user_id", mimic_user["user_id"]).execute()
        
        # 3. ПЕРЕБИВАЕМ ИСТОРИЮ
        supabase.table("daily_winners").update({"user_id": mimic_user["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()

        mimic_username = f" (@{mimic_user['username']})" if mimic_user.get("username") else ""
        celebrator_name = mimic_user["first_name"]

        # Собираем гендерные глаголы и титулы для Агрессора (mimic_user)
        hotel_text = g_text(mimic_user, "хотел украсть", "хотела украсть")
        clown_title = g_text(mimic_user, "Клоун года! 🎪", "Королева цирка! 💅")
        zabiraet_text = g_text(mimic_user, "забирает", "забирает")

        # Собираем гендерные глаголы для Мирного (winner)
        chisty_title = g_text(winner, "чистый перед законом", "чистая перед законом")
        suh_text = g_text(winner, "выходит сухоньким из воды с каменным лицом", "выходит сухонькой из воды с элегантной улыбкой")

        # Экранируем имена для безопасности HTML-верстки Телеграма
        safe_winner_name = winner['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        safe_mimic_name = mimic_user['first_name'].replace("<", "&lt;").replace(">", "&gt;")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎪 <b>КАРМИЧЕСКАЯ КАРА! МИМИКРИЯ ДАЛА ОСЕЧКУ!</b> 🎪\n\n"
                f"Пидором дня должен был стать <b>{safe_winner_name}</b>...\n"
                f"Но <b>{safe_mimic_name}{mimic_username}</b> так сильно {hotel_text} чужую удачу, что {g_text(mimic_user, 'попал', 'попала')} в собственную ловушку! 🎭\n\n"
                f"🤡 Карма удваивает позор! {celebrator_name} {zabiraet_text} клеймо и получает <b>сразу +2 к счетчику Пидоров</b>! {clown_title}\n"
                f"👑 А {chisty_title} <b>{safe_winner_name}</b> {suh_text}!"
            ),
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERl4dqYxpwoMRaj3A9CUnnJrevQTll7AACUncAAoWfcEkaYUBMkirIqT0E')

    # --- МИКРО-ПОДСКАЗКА ПРО КАРТУ UNO (ТЕПЕРЬ УЧИТЫВАЕТ РЕАЛЬНОГО ПИДОРА) ---
    uno_status_text = ""
    rules_memo = (
        "\n\n📊 <b>Сетка шансов на перевод карты UNO:</b>"
        "\n └ 👑 На Красавчика дня — <b>15%</b>"
        "\n └ 🃏 На обычного мирного — <b>30%</b>"
        "\n └ 🎯 На раненого в монетку — <b>45%</b>"
        "\n\n⚠️ <b>ВНИМАНИЕ:</b> В случае провала промаха активируется кармическая расплата. Рискуй с умом! 😈🎰"
    )

    if final_pidor_user.get("last_switch_date"):
        last_date = date.fromisoformat(final_pidor_user["last_switch_date"])
        days_passed = (today - last_date).days
        
        if days_passed < 6:
            days_left = 6 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            uno_status_text = f"\n\n🃏 Кстати, твоя карта UNO на перезарядке. Ждать еще {days_left} {day_word}."
        else:
            uno_status_text = f"\n\n🃏 *ОП-ПА! Твоя карта UNO ПЕРЕЗАРЯЖЕНА!* Можешь попробовать защититься, пиши: `/switch @username`{rules_memo}"
    else:
        uno_status_text = f"\n\n🃏 *ОП-ПА! Твоя карта UNO ГОТОВА!* Защищайся, пиши: `/switch @username`{rules_memo}"

    if uno_status_text:
        try:
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Заменили Markdown на HTML для поддержки новых жирных тегов!
            await context.bot.send_message(
                chat_id=chat_id, 
                text=uno_status_text, 
                parse_mode="HTML"
            )
        except Exception as e:
            # Предохранитель: если в чат не улетело, тихо шлём админу, но не вешаем бота
            print(f"Ошибка вывода утреннего уно-статуса: {e}")
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_TG_ID, 
                    text=f"⚠️ Ошибка утреннего Крупье UNO в чате <code>{chat_id}</code>: <code>{e}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ ПИДОРА ----------------
    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Убрали затирание имени, celebrator_name берется из логики Мимика выше!
    pidor_stickers_pool = [
        'CAACAgIAAxkBAAEReO5qQ22SmZkDyLqKq0vP6-ELBjPTUAACjnQAAihj2EtnaWFztIKP7DwE',
        'CAACAgIAAxkBAAERePBqQ27RxFYFJcHGEaZ9kPTDkhO1EAACSk4AAuAKOUlEfzO0OLfimzwE',
        'CAACAgIAAxkBAAERePJqQ27guzCAFe3IqBMNm9Rsq4tlIwACxVQAAsfrOEk6oSm-WVc9QjwE',
        'CAACAgIAAxkBAAERePRqQ28nWDjJOWNP0amyxIzJUiJwgAACckYAArr9OUlyV8svBKf4PzwE',
        'CAACAgIAAxkBAAERePZqQ29RyTAuFB6ryyH6BApiXpfNtgAC3EoAAmsNOUmTv1vWKkSg7TwE',
        'CAACAgIAAxkBAAERePhqQ29fvKDHMorjySaOzDQ013gcdgACNUoAAoRQOEkf13J-sHIrqTwE'
    ]
        
    # Готовим гендерные переменные для юбилеев (на основе объекта final_winner)
    parney_title = g_text(final_winner, "сомнительных парней", "сомнительных леди 💅")
    ploh_title = g_text(final_winner, "Стабильно плох!", "Стабильно плоха! 💅")
    bar_title = g_text(final_winner, "пожизненную путевку в гейбар! 🏅", "пожизненную путевку на женский стриптиз! 🏅")
    geystvo_title = g_text(final_winner, "твоё гейство видно даже со спутников наблюдения!", "твой позорный шлейф видно даже из космоса!")
    gaymaster_title = g_text(final_winner, "ГЕЙмастеров! 🏛", "Королев Драмы! 🏛")
    proshel_title = g_text(final_winner, "полностью прошёл эту жизнь", "полностью прошла эту жизнь")

    jokes = {
        10: f"🎂 <b>ОГО, 10 РАЗ!</b> {celebrator_name}, поздравляем! Первый юбилей на дне. Давай, расскажи всем, что это просто «случайность»! 🤡",
        20: f"👑 <b>УЖЕ 20 ПОБЕД!</b> {celebrator_name} официально переходит в Высшую лигу {parney_title}. Корона из картона готова! 🎪",
        30: f"🚨 <b>30-й СТРАЙК!</b> {celebrator_name}, это уже карьера. Ты стабилен как швейцарские часы. {ploh_title} 🛑",
        40: f"🗄 <b>КРИЗИС СРЕДНЕГО ВОЗРАСТА!</b> {celebrator_name} отмечает 40 побед! Архив компромата переполнен! 📂",
        50: f"🎖 <b>ПОЛУВЕКОВОЙ ЮБИЛЕЙ!</b> 50 раз! {celebrator_name} получает золотую медаль и {bar_title}",
        60: f"🎰 <b>МАСТЕР СВОЕГО ДЕЛА!</b> 60 побед у {celebrator_name}! Датчики сомнительных мыслей зашкаливают! ⚡️",
        70: f"🚨 <b>КОСМИЧЕСКИЙ УРОВЕНЬ!</b> 70-й раз! {celebrator_name}, {geystvo_title} 🌌",
        80: f"🦾 <b>ТИФЛОНОВЫЙ СТАТУС!</b> 80 раз! К {celebrator_name} уже просто ничего не липнет, это абсолютный иммунитет! 🛡",
        90: f"🧛‍♂️ <b>ДРЕВНИЙ ОЛДХЭД!</b> 90 побед! {celebrator_name} выходит на финишную прямую к великому залу славы {gaymaster_title}",
        100: f"🏆 <b>ЛЕГЕНДА ВЕКА! СТОКРАТНЫЙ ПИДОР!</b> 🎉💥 {celebrator_name} {proshel_title} с обратной стороны! 👑🍾"
    }

    is_anniversary = False
    
    if celebrator_count == 5 or (is_mimic_triggered and celebrator_count == 6):
        await update.message.reply_text(f"🎉 *РАЗОГРЕВ ОКОНЧЕН!* {celebrator_name} косячит уже 5-й раз! Начало положено, но до клуба великих данжн мастеров далеко! 🎖", parse_mode="Markdown")
        is_anniversary = True
    elif celebrator_count in jokes or (is_mimic_triggered and (celebrator_count - 1) in jokes):
        actual_joke_count = celebrator_count if celebrator_count in jokes else (celebrator_count - 1)
        await update.message.reply_text(jokes[actual_joke_count], parse_mode="Markdown")
        is_anniversary = True
         
    if is_anniversary:
        random_sticker = random.choice(pidor_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)
        
async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import date
    game_today = date.today()
    # 1. Вытаскиваем только АКТИВНЫХ игроков (is_active == True)
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
    if len(users) < 1:
        await update.message.reply_text("В боте еще никто не зарегистрировался. Напишите /register")
        return

    already_winner = get_today_winner("krasavchik")
    if already_winner:
        username = f" (@{already_winner['username']})" if already_winner['username'] else ""
        await update.message.reply_text(
            f"Сегодня этот выбор уже сделан! 😎 Красавчик дня — {already_winner['first_name']}{username}",
            parse_mode="HTML"
        )
        return

    opposite_id = get_opposite_winner_id("krasavchik")
    filtered_users = [u for u in users if u["user_id"] != opposite_id]

    if not filtered_users:
        await update.message.reply_text("Все участники уже заняли свои титулы на сегодня! Больше выбирать некого.")
        return

    # === ИСПРАВЛЕННЫЙ БЛОК ЗАСТАВОК КРАСАВЧИКА ===
    chat_id = update.effective_chat.id
    for phrase in random.sample(KRAS_PHRASES, 5): # <-- ПОСТАВИЛИ ЦИФРУ 5!
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

        # Собираем динамический глагол победы на основе пола Топ-1 фаворита (favorit)
        dolzhen_text = g_text(favorit, "Должен был победить", "Должна была победить")

        # Экранируем имена для безопасности HTML-верстки Телеграма
        safe_favorit_name = favorit['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        safe_contender_name = contender['first_name'].replace("<", "&lt;").replace(">", "&gt;")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎰 <b>Красавчик дня определён... СТОП, ЧТО?!</b> 🎰\n\n"
                f"{dolzhen_text} <b>{safe_favorit_name}{favorit_username}</b>, но монетка внезапно упала РЕБРОМ! 💥\n"
                f"Датчики крутости казино зафиксировали аномалию. На кону дикий баттл!\n\n"
                f"⚡️ <b>{safe_favorit_name}</b> против <b>{safe_contender_name}{contender_username}</b>! ⚡️\n"
                f"Бросаем финальный кубик судьбы 1-3, 4-6... подкидываем монетку (50/50)..."
            ),
            parse_mode="HTML"
        )

        await asyncio.sleep(2.5) # Пауза для нагнетания валидола
        
        # Мгновенный баттл 50/50 между ними
        if random.randint(1, 100) <= 50:
            final_winner = favorit
            coin_loser = contender  # Неудачник монетки
            
            # Экранируем имена для безопасности HTML-верстки Телеграма
            safe_winner_name = final_winner['first_name'].replace("<", "&lt;").replace(">", "&gt;")
            safe_loser_name = coin_loser['first_name'].replace("<", "&lt;").replace(">", "&gt;")

            # Гендерные глаголы и титулы для первого исхода
            protect_text = g_text(final_winner, "свою крутость защищает", "свою крутость защищает") # Универсально
            loser_title = g_text(coin_loser, "проигравший", "проигравшая")

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🪙 <b>МОНЕТКА ОСТАЕТСЯ НА СТОРОНЕ ПЕРВОГО!</b>\n\n"
                    f"😎 В жестком баттле {protect_text} <b>{safe_winner_name}{favorit_username}</b>! Справедливость восторжествовала!\n"
                    f"🤡 А {loser_title} <b>{safe_loser_name}</b> получает утешительные повышенные шансы к Красавчику на завтра!"
                ),
                parse_mode="HTML"
            )
        else:
            final_winner = contender
            coin_loser = favorit  # Неудачник монетки
            
            # Экранируем имена для безопасности HTML-верстки Телеграма
            safe_winner_name = final_winner['first_name'].replace("<", "&lt;").replace(">", "&gt;")
            safe_loser_name = coin_loser['first_name'].replace("<", "&lt;").replace(">", "&gt;")

            # Гендерные титулы для второго исхода
            favorit_title = g_text(coin_loser, "рук фаворита", "рук фаворитки")
            obvorovanniy_title = g_text(coin_loser, "обворованный", "обворованная 💅")

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🪙 <b>ОГРАБЛЕНИЕ В ФИНАЛЕ! ОНА ПЕРЕВЕРНУЛАСЬ!</b>\n\n"
                    f"😎 Монетка решает в пользу претендента! <b>{safe_winner_name}{contender_username}</b> вырывает победу из {favorit_title}!\n"
                    f"🤡 А {obvorovanniy_title} <b>{safe_loser_name}</b> получает утешительные повышенные шансы к Красавчику на завтра!"
                ),
                parse_mode="HTML"
            )

        # 💾 СОХРАНЯЕМ НЕУДАЧНИКА В БАЗУ ДАННЫХ SUPABASE (Сейв от спячки Render)
        save_daily_winner("coin_loser", coin_loser["user_id"])
        
        # ИСПРАВЛЕНО: Твой верный вариант с индексом [0]
        loser_base = supabase.table("users").select("kras_weight").eq("user_id", coin_loser["user_id"]).execute().data
        current_kras_weight = loser_base[0]["kras_weight"] if loser_base else 100.0
        
        supabase.table("users").update({"kras_weight": current_kras_weight + 30.0}).eq("user_id", coin_loser["user_id"]).execute()
    else:
        # ================= ✨ ПУТЬ А: СТАНДАРТНЫЙ ПРОКРУТ (70%) =================
        # Тут тоже отправляем напрямую в чат, чтобы застраховаться от удаления сообщений!
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"😎 Красавчик дня — {final_winner['first_name']}{favorit_username}"
        )

    # === 👑 МНОЖИТЕЛЬ ЧЕМПИОНА С ПОД КРУТКОЙ ОТ СТРИКА МАКС-ШАНСА В SUPABASE ===
    total_kras_weight = sum(u["kras_weight"] for u in users)
    max_chat_weight = max(u["kras_weight"] for u in filtered_users)
    kras_chance = (final_winner["kras_weight"] / total_kras_weight) * 100
    
    multiplier = 1
    multiplier_text = ""
    is_accumulated_champion = False

    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Если у нескольких людей макс вес одинаковый — стрик капает ВСЕМ!
    for u in filtered_users:
        if u["kras_weight"] >= max_chat_weight: # Используем >= на случай микро-погрешностей
            current_streak = u.get("kras_streak", 0) or 0
            supabase.table("users").update({"kras_streak": current_streak + 1}).eq("user_id", u["user_id"]).execute()
        else:
            supabase.table("users").update({"kras_streak": 0}).eq("user_id", u["user_id"]).execute()

    # Считываем свежий стрик Красавчика для победителя
    winner_res = supabase.table("users").select("kras_streak").eq("user_id", final_winner["user_id"]).execute()
    streak_days = winner_res.data[0]["kras_streak"] if (winner_res.data and len(winner_res.data) > 0) else 0

    # Если победитель — это именно фаворит, и его стрик удержания топа длится 3 дня или дольше
    if final_winner["kras_weight"] == max_chat_weight and streak_days >= 3:
        is_accumulated_champion = True
        
        # Крутим скрытую кость от 1 до 100
        bonus_roll = random.randint(1, 100)
        
        # === 👑 ЗЕРКАЛЬНАЯ НАСТРОЙКА ВЕСОВ ЧЕМПИОНА (ШКАЛА 5 / 10 / 15 ДНЕЙ) ===
        if streak_days >= 15:
            # 15+ дней удержания Топ-1 шанса: Осечки нет вообще! Шанс на х5 увеличен до 25%!
            if bonus_roll <= 30:
                multiplier = 2
                multiplier_text = "🔥 *КРАТНЫЙ УДАР (х2)!* Монетка упала удачно — лови сразу *+2 к счётчику* в досье! "
            elif bonus_roll <= 75:
                multiplier = 3
                multiplier_text = "🚀 *КОРОЛЕВСКИЙ ТРИУМФ (х3)!* Матрица казино взломана фаворитом — забирай *+3*! "
            else:
                multiplier = 5
                multiplier_text = "💥 *ЛЕГЕНДАРНЫЙ ДЖЕКПОТ (х5)!!!* История чата переписана! Колесо фортуны выдало максимальный сектор — лови сразу *+5*, красавчик! 👑🥂"
        
        elif streak_days >= 10:
            # 10-14 дней удержания Топ-1 шанса: Осечка падает до 5%, шансы на х3 и х5 повышены
            if bonus_roll <= 45:
                multiplier = 2
                multiplier_text = "🔥 *КРАТНЫЙ УДАР (х2)!* Монетка упала удачно — лови сразу *+2 к счётчику* в досье! "
            elif bonus_roll <= 85:
                multiplier = 3
                multiplier_text = "🚀 *КОРОЛЕВСКИЙ ТРИУМФ (х3)!* Матрица казино взломана фаворитом — забирай *+3*! "
            elif bonus_roll <= 90:
                multiplier = 1  # Осечка джекпота, бот промолчит для секретности!
            else:
                multiplier = 5
                multiplier_text = "💥 *ЛЕГЕНДАРНЫЙ ДЖЕКПОТ (х5)!!!* История чата переписана! Колесо фортуны выдало максимальный сектор — лови сразу *+5*, красавчик! 👑🥂"
        
        elif streak_days >= 5:
            # 5-9 дней удержания Топ-1 шанса: Базовые шансы для запуска колеса
            if bonus_roll <= 50:
                multiplier = 2
                multiplier_text = "🔥 *КРАТНЫЙ УДАР (х2)!* Монетка упала удачно — лови сразу *+2 к счётчику* в досье! "
            elif bonus_roll <= 80:
                multiplier = 3
                multiplier_text = "🚀 *КОРОЛЕВСКИЙ ТРИУМФ (х3)!* Матрица казино взломана фаворитом — забирай *+3*! "
            elif bonus_roll <= 95:
                multiplier = 1  # Осечка джекпота, бот промолчит для секретности!
            else:
                multiplier = 5
                multiplier_text = "💥 *ЛЕГЕНДАРНЫЙ ДЖЕКПОТ (х5)!!!* История чата переписана! Колесо фортуны выдало максимальный сектор — лови сразу *+5*, красавчик! 👑🥂"

    # Рассчитываем итоговое начисление с учётом множителя
    new_count = final_winner["kras_count"] + multiplier
    supabase.table("users").update({"kras_count": new_count}).eq("user_id", final_winner["user_id"]).execute()
    
    # После победы фаворита сбрасываем его личный стрик макс-шанса обратно в 0
    supabase.table("users").update({"kras_streak": 0}).eq("user_id", final_winner["user_id"]).execute()

    # Защищаем никнейм от багов разметки Телеграма (изолируем в скобки)
    safe_winner_name = f"{final_winner['first_name']}{favorit_username}"

    # Бот подаст голос только в том случае, если МНОЖИТЕЛЬ СРАБОТАЛ (х2, х3, х5)
    if is_accumulated_champion and multiplier > 1 and multiplier_text:
        # Собираем динамические гендерные слова для сегодняшнего чемпиона рулетки
        favorit_title = g_text(final_winner, "накопленный фаворит дня", "накопленная фаворитка дня")
        uderzhival_text = g_text(final_winner, "удерживал", "удерживала")
        schet_title = g_text(final_winner, "Текущие красавчики", "Текущие короны красавицы")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎰 <b>АКТИВАЦИЯ МНОЖИТЕЛЯ ЧЕМПИОНА!</b> 🎰\n\n"
                f"Поскольку {favorit_title} <b>{safe_winner_name}</b> {uderzhival_text} максимальный шанс в чате уже <b>{streak_days} дн.</b> подряд, казино активирует бонусное колесо фортуны!\n\n"
                f"{multiplier_text}\n\n"
                f"📊 <i>Личная статистика обновлена. {schet_title}: {new_count}</i>"
            ),
            parse_mode="HTML"
        )

        if multiplier == 5:
            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERr31qeWv80Ku9FF7n2t9x4eyLRpX9eAAC1jcAAvbPQUmGw6z4J9_owD0E')
    
    # === 🏆 УЛЬТРА-ВИНСТРИК КРАСАВЧИКА (БЕЗБАГОВЫЙ СБРОС) ===
    # 1. Железный сброс в один клик: обнуляем стрик ВСЕМ, кроме финального победителя
    supabase.table("users").update({"kras_win_streak": 0}).neq("user_id", final_winner["user_id"]).execute()

    # 2. Победителю накидываем +1 к его текущему победному стрику
    current_win_streak = final_winner.get("kras_win_streak", 0) or 0
    new_win_streak = current_win_streak + 1
    supabase.table("users").update({"kras_win_streak": new_win_streak}).eq("user_id", final_winner["user_id"]).execute()

    # 3. Проверяем и обновляем ВЕЧНЫЙ ИСТОРИЧЕСКИЙ РЕКОРД подряд в базе данных
    max_kras_streak = final_winner.get("max_kras_win_streak", 0) or 0
    if new_win_streak > max_kras_streak:
        supabase.table("users").update({"max_kras_win_streak": new_win_streak}).eq("user_id", final_winner["user_id"]).execute()

    # 4. Если везунчик забирает титул 3 дня подряд или дольше — взрываем чат!
    if new_win_streak >= 3:
        await asyncio.sleep(1) # Небольшая пауза для эффекта сюрприза
        
        # Рассчитываем правильное окончание для дней (3 дня, 5 дней)
        day_word = "дня" if new_win_streak in else "дней"
        
        # Собираем динамические гендерные глаголы, местоимения и титулы
        kak_on_text = g_text(final_winner, "Да как он это делает?!", "Да как она это делает?! 💅")
        vzlomal_text = g_text(final_winner, "взломал", "взломала")
        lubimchik_title = g_text(final_winner, "Настоящий любимчик фортуны!", "Настоящая любимица фортуны! ✨")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎰 <b>БОЖЕСТВЕННЫЙ ХЕТ-ТРИК КАЗИНО!</b> 👑\n\n"
                f"{kak_on_text} <b>{safe_winner_name}</b> {g_text(final_winner, 'умудряется', 'умудряется')} забрать титул Красавчика дня аж <b>{new_win_streak} {day_word} подряд</b>! 🤯\n"
                f"Имея минимальный процент, {g_text(final_winner, 'он', 'она')} всё равно {vzlomal_text} рандом! {lubimchik_title} 🥂"
            ),
            parse_mode="HTML"
        )

    # Пересчитываем веса под финального победителя и сохраняем его в историю дня
    redistribute_weights(final_winner["user_id"], "kras_weight")
    save_daily_winner("krasavchik", final_winner["user_id"])

    # === 🎭 БЛОК КАРТЫ МИМИКРИИ: КРАЖА КРАСАВЧИКА (ВЫНЕСЕНО ВВЕРХ!) ===
    mimic_hunter_res = supabase.table("users").select("*").eq("mimic_target_id", final_winner["user_id"]).execute()
    
    is_mimic_triggered = False
    celebrator_name = final_winner["first_name"]
    celebrator_count = new_count

    if mimic_hunter_res.data and len(mimic_hunter_res.data) > 0:
        mimic_user = mimic_hunter_res.data[0]
        is_mimic_triggered = True
        
        # 1. ОТМЕНЯЕМ ПОБЕДУ ПОСТРАДАВШЕГО (Срезаем обратно начисленный +1)
        supabase.table("users").update({"kras_count": final_winner["kras_count"]}).eq("user_id", final_winner["user_id"]).execute()
        
        # 2. УДВАИВАЕМ КУШ МИМИКУ (+2 победы вместо +1) и сбрасываем цель
        celebrator_count = mimic_user["kras_count"] + 2
        supabase.table("users").update({
            "kras_count": celebrator_count,
            "mimic_target_id": None
        }).eq("user_id", mimic_user["user_id"]).execute()
        
        # 3. ПЕРЕБИВАЕМ ИСТОРИЮ НА МИМИКА
        supabase.table("daily_winners").update({"user_id": mimic_user["user_id"]}).eq("game_date", str(game_today)).eq("role", "krasavchik").execute()

        mimic_username = f" (@{mimic_user['username']})" if mimic_user.get("username") else ""
        celebrator_name = mimic_user["first_name"]

        # Собираем гендерные глаголы и титулы для Агрессора (mimic_user)
        predskazal_text = g_text(mimic_user, "чёртов мимик предсказал", "хитрая мимикиня предсказала 💅")
        voruet_text = g_text(mimic_user, "ворует", "ворует")

        # Собираем гендерные титулы для пострадавшего Красавчика (final_winner)
        dolzhen_text = g_text(final_winner, "должен был стать", "должна была стать")
        obvorovanniy_title = g_text(final_winner, "обворованный", "обворованная 💔")
        ostalsya_text = g_text(final_winner, "остаётся с каменным лицом 🗿 и с абсолютным ничем", "остаётся ни с чем, но держит марку 💅")

        # Экранируем имена для безопасности HTML-верстки Телеграма
        safe_winner_name = final_winner['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        safe_mimic_name = mimic_user['first_name'].replace("<", "&lt;").replace(">", "&gt;")

        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"💥 <b>МИМИКРИЯ СРАБОТАЛА УХА-ХА-ХА!</b> 💥\n\n"
                f"Красавчиком дня {dolzhen_text} <b>{safe_winner_name}</b>...\n"
                f"Но <b>{safe_mimic_name}{mimic_username}</b> — {predskazal_text} твою победу! 🎭\n\n"
                f"👑 Куш удваивается! {celebrator_name} {voruet_text} корону и получает <b>сразу +2 победы</b> к статусу! 😎\n"
                f"А {obvorovanniy_title} <b>{safe_winner_name}</b> {ostalsya_text}!"
            ),
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERl5ZqYzAUBU7z06cdM38fa4YZfog1xAACYwEAAnHpkDYtQnUiFYhhSj0E')

    # Если никто победителя не мимикрировал, сжигаем все остальные сегодняшние ставки участников
    supabase.table("users").update({"mimic_target_id": None}).neq("user_id", 0).execute()

    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ С ИЗДЁВКОЙ ----------------
    kras_stickers_pool = [
        'CAACAgIAAxkBAAERePpqQ3C50Eqg_2plBXsHEFEtGOtmnQACk1QAAgmZ4EkPKsG3ATUGIDwE',
        'CAACAgIAAxkBAAERePxqQ3FkKQTrDt2Kt3E3v09Q90uUzgAC5zMAAvyF0EhRH0ZM6KsQGjwE',
        'CAACAgIAAxkBAAEReP5qQ3GP592jnDm3vTPxPH5LqTK3rgACrhQAAo4n0EqxFZIn-u6dajwE',
        'CAACAgIAAxkBAAEReQABakNxn4mZ1mhxrJf0em63Qj9qEb8AAs4ZAAKJEBBKhq0wFniF8sA8BA',
        'CAACAgIAAxkBAAEReQJqQ3HbH2OkT4mcPqJovAXsFJh5bQAClyAAAt88OUtsjjyKWQ5bXjwE',
        'CAACAgIAAxkBAAEReQRqQ3Ldb-x4CbDRQhozMvG6zY9vqQACagADJeuTHyg3EZuaMZFnPAQ'
    ]

    # Готовим гендерные переменные для юбилеев Красавчика (на основе объекта final_winner)
    miss_mr_title = g_text(final_winner, "мистер Обаяние! 📸", "мисс Обаяние! 💅📸")
    podkrutil_text = g_text(final_winner, "подкрутил", "подкрутила")
    podkupil_text = g_text(final_winner, "подкупил", "подкупила")
    narciss_title = g_text(final_winner, "главным нарциссом этого чата.", "главной нарцисской этого чата! 💅")
    mister_vselennaya = g_text(final_winner, "Мистер Вселенная! 🦾", "Мисс Вселенная! 💅🦾")
    pobeditel_title = g_text(final_winner, "великих Победителей.", "великих Победительниц. ✨")
    boss_title = g_text(final_winner, "икона стиля и босс этого чата! Салют чемпиону!", "икона стиля и королева этого чата! Салют чемпионке! 💅")
    proshel_game = g_text(final_winner, "полностью прошёл эту игру!", "полностью прошла эту игру! 💅")

    jokes = {
        10: f"👑 <b>ОГО, 10 РАЗ!</b> {celebrator_name}, аккуратнее на поворотах, а то нимб упадёт и ноги отдавит! Чат, расступаемся, тут идёт {miss_mr_title}",
        20: f"🎩 <b>20 ПОБЕД!</b> {celebrator_name} так часто выигрывает, что уже целует своё отражение в зеркале по утрам. Завязывай с самолюбованием, нам завидно! 🔥",
        30: f"🏆 <b>30-й СТРАЙК!</b> {celebrator_name}, признайся, ты {podkrutil_text} этот код или просто {podkupil_text} бота? Чат требует проверку на коддинг! 🚨",
        40: f"✨ <b>40 РАЗ КРАСАВЧИК!</b> Уровень эго {celebrator_name} превысил все допустимые нормы. Скоро тебе понадобится отдельная комната для твоей короны! 🗄",
        50: f"🎖 <b>ПОЛУВЕКОВОЙ ЮБИЛЕЙ!</b> 50 побед! {celebrator_name}, мы скидываемся тебе на памятник при жизни в полный рост. Из чистого золота, естественно! 🏅",
        60: f"🎰 <b>60 ПОБЕД!</b> {celebrator_name} официально признан {narciss_title} Датчики привлекательности сгорели от такого пафоса! ⚡️",
        70: f"🛰 <b>КОСМИЧЕСКИЙ КРАСАВЧИК!</b> 70-й раз! {celebrator_name}, твоё великолепие ослепляет даже спутники наблюдения! Надень маску, побереги наши глаза! 🌌",
        80: f"🛡 <b>80 РАЗ! СВЕРХЛЮДИ СРЕДИ НАС!</b> К {celebrator_name} уже выстроилась очередь за автографами. Не забудь упомянуть этот чат, когда поедешь на {mister_vselennaya}",
        90: f"🏛 <b>90 ПОБЕД!</b> {celebrator_name} одной ногой в зале славы {pobeditel_title} Ещё чуть-чуть, и твоё лицо напечатают на обложках всех журналов! 🧛‍♂️",
        100: f"👑🍾 <b>ЛЕГЕНДА ВЕКА! СТОКРАТНЫЙ КРАСАВЧИК!</b> 🎉💥 {celebrator_name} официально {proshel_game} 100 побед! {boss_title} 🏆🌟"
    }

    is_anniversary = False 
    
    # ИСПРАВЛЕНО: Если сработал Мимик и пролетел мимо 5, проверим точечно юбилеи или прыжок через него
    if celebrator_count == 5 or (is_mimic_triggered and celebrator_count == 6):
        await update.message.reply_text(f"🎉 *5 ПОБЕД!* {celebrator_name} вступает в клуб самовлюбленных! Начало положено! 🎖", parse_mode="Markdown")
        is_anniversary = True
    elif celebrator_count in jokes or (is_mimic_triggered and (celebrator_count - 1) in jokes):
        # Защита на случай если из-за +2 мимик перешагнул точную цифру юбилея (например с 9 сразу на 11)
        actual_joke_count = celebrator_count if celebrator_count in jokes else (celebrator_count - 1)
        await update.message.reply_text(jokes[actual_joke_count], parse_mode="Markdown")
        is_anniversary = True

    if is_anniversary:
        random_sticker = random.choice(kras_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)

    # ================= 🎲 СВОДКА ПО ДОСТУПНЫМ КУБИКАМ СУДЬБЫ =================
    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Объявляем дату и используем твой рабочий вариант с!
    current_week_num = game_today.isocalendar()[1]
    dice_ready_players = []

    # Перебираем только АКТИВНЫХ игроков из базы
    for u in users:
        db_dice_value = u.get("dice_count", 0)
        
        # ЗАЩИТА ОТ ДЕФОЛТНЫХ НУЛЕЙ
        if db_dice_value == 0:
            last_dice_week = current_week_num
            current_attempts = 0
        else:
            last_dice_week = db_dice_value // 10
            current_attempts = db_dice_value % 10

        # Если неделя в базе старая (прошлонедельная), сбрасываем попытки в 0
        if current_week_num != last_dice_week:
            current_attempts = 0

        dice_left = 2 - current_attempts
        if dice_left > 0:
            # БЕЗОПАСНЫЙ ТЕГ: защита от пустых username в базе
            username_tag = f" (@{u['username']})" if u.get("username") else ""
            
            # Экранируем имя игрока, чтобы спецсимволы в никах не ломали разметку HTML
            safe_f_name = u['first_name'].replace("<", "&lt;").replace(">", "&gt;")
            
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Заменили звездочки на HTML-теги <b>...</b>
            dice_ready_players.append(f" └ <b>{safe_f_name}{username_tag}</b> — доступно: {dice_left} из 2")
            
# Формируем и отправляем сообщение крупье ТОЛЬКО если есть хотя бы один кубик!
    if dice_ready_players:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перевели весь утренний информер Крупье на HTML-теги <b> и <code>
        dice_memo_text = (
            f"\n\n🎰 <b>ИНФОРМАЦИЯ ОТ КРУПЬЕ:</b> 🎰\n"
            f"У следующих участников на этой неделе ещё остались заряженные кубики судьбы:\n"
            f"{'\n'.join(dice_ready_players)}\n\n"
            f"🎲 Напиши <code>/dice</code>, чтобы подбавить себе пару процентов, а в каком именно месте — зависит от твоей удачи! 😏"
        )
        try:
            # Заменили parse_mode на HTML для стопроцентной защиты никнеймов от багов
            await context.bot.send_message(chat_id=chat_id, text=dice_memo_text, parse_mode="HTML")
        except Exception as e:
            # ТИХОЕ УВЕДОМЛЕНИЕ АДМИНУ: Если отправка упадет, ошибку пришлет тебе в ЛС
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_TG_ID, 
                    text=f"⚠️ Ошибка отправки крупье в чат <code>{chat_id}</code>: <code>{e}</code>",
                    parse_mode="HTML"
                )
            except Exception:
                print(f"Даже админу не удалось отправить лог ошибки: {e}")

    # --- ТИХИЙ БЭКАП ПОСЛЕ ИГРЫ ---
    context.application.create_task(silent_backup(context))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # ИСПРАВЛЕНО: Вытаскиваем всех и берем строго активных участников
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
    if not users:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перевели отлуп на HTML и прямой send_message по chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text="В игре пока нет активных участников.",
            parse_mode="HTML"
        )
        return

    # 1. Сортируем пользователей для топа Пидоров (от максимума к минимуму)
    pidors_sorted = sorted(users, key=lambda x: x["pidor_count"], reverse=True)
    
    # 2. Сортируем пользователей для топа Красавчиков (от максимума к минимуму)
    kras_sorted = sorted(users, key=lambda x: x["kras_count"], reverse=True)

    # Перевели шапку на HTML
    message = "📊 <b>СТАТИСТИКА ЧАТА</b>\n\n"

    # Формируем колонку / блок Пидоров
    message += "🤡 <b>Топ Пидоров чата:</b>\n"
    for i, user_data in enumerate(pidors_sorted, start=1):
        username = f" (@{user_data['username']})" if user_data['username'] else ""
        # Экранируем имена от багов HTML
        safe_name = user_data['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        message += f"{i}. <b>{safe_name}{username}</b> — {user_data['pidor_count']} раз(а)\n"

    message += "\n" + "—" * 15 + "\n\n" # Визуальный разделитель блоков

    # Формируем колонку / блок Красавчиков
    message += "😎 <b>Топ Красавчиков чата:</b>\n"
    for i, user_data in enumerate(kras_sorted, start=1):
        username = f" (@{user_data['username']})" if user_data['username'] else ""
        # Экранируем имена от багов HTML
        safe_name = user_data['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        message += f"{i}. <b>{safe_name}{username}</b> — {user_data['kras_count']} раз(а)\n"
    
    try:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Прямой send_message по chat_id на HTML-парсер
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка вывода общей статистики stats: {e}")

async def procents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # ИСПРАВЛЕНО: Вытаскиваем всех и считаем шансы СТРОГО среди active участников
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
    if not users:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Заменили на send_message по HTML
        await context.bot.send_message(
            chat_id=chat_id,
            text="В игре пока нет активных участников.",
            parse_mode="HTML"
        )
        return

    # Считаем суммарные веса только среди активных игроков
    total_p_weight = sum(user["pidor_weight"] for user in users)
    total_k_weight = sum(user["kras_weight"] for user in users)

    # 1. Сортируем пользователей по шансу стать Пидором (от большего к меньшему)
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

    # Перевели шапку на HTML
    message = "🎯 <b>ТЕКУЩИЕ ШАНСЫ УЧАСТНИКОВ</b>\n\n"

    # Блок шансов на Пидора
    message += "🔥 <b>Шансы стать Пидором дня:</b>\n"
    for i, user_data in enumerate(pidors_by_chance, start=1):
        username = f" (@{user_data['username']})" if user_data['username'] else ""
        p_chance = (user_data["pidor_weight"] / total_p_weight * 100) if total_p_weight > 0 else 0
        # Экранируем имя от багов HTML
        safe_name = user_data['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        message += f"{i}. <b>{safe_name}{username}</b> — {p_chance:.1f}%\n"

    message += "\n" + "—" * 15 + "\n\n" # Визуальный разделитель блоков

    # Блок шансов на Красавчика
    message += "✨ <b>Шансы стать Красавчиком дня:</b>\n"
    for i, user_data in enumerate(kras_by_chance, start=1):
        username = f" (@{user_data['username']})" if user_data['username'] else ""
        k_chance = (user_data["kras_weight"] / total_k_weight * 100) if total_k_weight > 0 else 0
        # Экранируем имя от багов HTML
        safe_name = user_data['first_name'].replace("<", "&lt;").replace(">", "&gt;")
        message += f"{i}. <b>{safe_name}{username}</b> — {k_chance:.1f}%\n"

    try:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Прямой send_message по chat_id на HTML-парсер
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка вывода таблицы процентов: {e}")

async def records(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # ИСПРАВЛЕНО: Вытаскиваем всех и ищем чемпиона СТРОГО среди активных участников
    all_users = get_users()
    users = [u for u in all_users if u.get("is_active", True)]
    
    if not users:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Заменили на send_message по HTML
        await context.bot.send_message(
            chat_id=chat_id,
            text="В игре пока нет активных участников для фиксации рекордов.",
            parse_mode="HTML"
        )
        return

    # Сортируем: по КРАСАВЧИКАМ (по убыванию), а при равенстве — по ПИДОРАМ (по возрастанию)
    champions_sorted = sorted(users, key=lambda x: (-x["kras_count"], x["pidor_count"]))
    
    leader = champions_sorted[0]
    leader_username = f" (@{leader['username']})" if leader['username'] else ""

    # Проверяем, были ли вообще игры
    if leader["kras_count"] == 0 and leader["pidor_count"] == 0:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Заменили на send_message по HTML
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚖️ <b>Статистика еще пуста, рекорды не зафиксированы.</b> Пора крутить рулетку!",
            parse_mode="HTML"
        )
        return

    # Экранируем имя лидера чата, чтобы спецсимволы не ломали разметку HTML
    safe_leader_name = leader['first_name'].replace("<", "&lt;").replace(">", "&gt;")

    # Собираем динамические гендерные титулы для Лидера таблицы (на основе объекта leader)
    human_title = g_text(leader, "Человек, которого", "Леди, которую")
    legend_title = g_text(leader, "легенду казино", "королеву игрового стола! 💅")

    # Пересобрали текст СТРОГО на HTML-тегах <b> и <i> вместо звездочек
    message = (
        "🥇 <b>АБСОЛЮТНЫЙ ЧЕМПИОН КАЗИНО Im🎰</b> 🥇\n\n"
        f"{human_title} фортуна целует в обе щеки, а радужные мысли обходят стороной. "
        f"Максимум благословений и чистый кайф по жизни! Поприветствуйте {legend_title}:\n\n"
        f"👑 <b>{safe_leader_name}{leader_username}</b>\n"
        f"   └ 😎 Статус Красавчика: {leader['kras_count']} раз(а)\n"
        f"   └ 🤡 Статус Пидора: {leader['pidor_count']} раз(а)\n\n"
        f"<i>Остальным участникам за игровым столом соболезнуем, тренируйте удачу!</i> 👇"
    )

    try:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Прямой send_message по chat_id на HTML-парсер
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка вывода абсолютного лидера records: {e}")

async def mimic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Активировать Мимика можно только в групповых чатах!")
        return

    # 1. Вытаскиваем данные Стрелочника из базы
    user_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not user_res.data:
        await update.message.reply_text("❌ Тебя нет в рулетке! Напиши /register")
        return
    current_user = user_res.data[0]

    # 2. ПРОВЕРКА КУЛДАУНА (14 ДНЕЙ) С УМНЫМ ПАРСИНГОМ ТИПА DATE
    if current_user.get("last_mimic_date"):
        last_db_date = current_user["last_mimic_date"]
        last_date = date.fromisoformat(last_db_date) if isinstance(last_db_date, str) else last_db_date
        days_passed = (today - last_date).days
        
        if days_passed < 14:
            days_left = 14 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Прямой send_message на HTML-разметке защитит от комы при удалении команды
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Способность Мимикрия еще на перезарядке! Доступ появится через <b>{days_left} {day_word}</b>.",
                parse_mode="HTML"
            )
            # Переписали стикер на прямой send_sticker по chat_id для ультимативной стабильности
            await context.bot.send_sticker(
                chat_id=chat_id, 
                sticker='CAACAgIAAxkBAAEReRpqQ3-pZ9QRME44W1Es3DPWTGUPNAACkAIAAladvQoy0qlxuNTQtTwE'
            )
            return

    # 3. УЛЬТИМАТИВНЫЙ ПАРСИНГ ЖЕРТВЫ (Твоя схема из карты UNO)
    if not context.args and not update.message.entities:
        await update.message.reply_text("❌ Под кого мимикрируем? Тегни цель: `/mimic @username` или кликни по имени в списке!")
        return

    target_username = None
    target_user_id = None

    for entity in update.message.entities:
        if entity.type == "mention":
            target_username = update.message.text[entity.offset:entity.offset + entity.length].replace("@", "")
            break
        elif entity.type == "text_mention":
            target_user_id = entity.user.id
            break

    # Ищем жертву в базе
    if target_user_id:
        target_res = supabase.table("users").select("*").eq("user_id", target_user_id).eq("is_active", True).execute()
    elif target_username:
        target_res = supabase.table("users").select("*").eq("username", target_username).eq("is_active", True).execute()
    else:
        await update.message.reply_text("❌ Нужно именно тегнуть игрока!")
        return
    
    if not target_res.data or len(target_res.data) == 0:
        await update.message.reply_text("❌ Этого юзера нет в рулетке, или он ливнул!")
        return
    
    victim = target_res.data[0]
    
    if victim["user_id"] == user.id:
        # Собираем динамический ироничный титул на основе пола игрока (player)
        megamozg_title = g_text(player, "мегамозг, ничего не скажешь", "гениальная леди, ничего не скажешь 💅")
        choose_target_text = g_text(player, "выбери другую цель", "выбери другую цель, подруга")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎭 <b>Мимикрировать под самого себя?</b> Ну ты {megamozg_title}! {choose_target_text}.",
            parse_mode="HTML"
        )
        return

    # 4. ЗАЩИТА ОТ ПЕРЕКРЁСТНОЙ МИМИКРИИ И ЛИМИТОВ
    # Проверяем, не нацелилась ли ЖЕРТВА уже на кого-то сегодня
    if victim.get("mimic_target_id"):
        # Собираем динамические гендерные подколы для вызывающего (player)
        opozdal_text = g_text(player, "ОПОЗДАЛ", "ОПОЗДАЛА")
        sama_text = g_text(player, "сам вышел", "сама вышла")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🗿 <b>{opozdal_text}!</b> Эта жертва уже активировала свои датчики маскировки и {sama_text} на охоту! Перекрёстная мимикрия заблокирована казино!",
            parse_mode="HTML"
        )
        return

    # Проверяем, не занята ли жертва кем-то другим сегодня
    all_users = supabase.table("users").select("*").eq("is_active", True).execute().data
    for u in all_users:
        if u.get("mimic_target_id") == victim["user_id"]:
            # Динамическая поговорка для парня / девушки
            tapki_text = g_text(player, "Кто первый успел, того и тапки.", "В казино правила просты: кто первая успела, за той и куш! 💅")
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🙅‍♂️ На этого игрока уже нацелен другой Мимик! {tapki_text}",
                parse_mode="HTML"
            )
            return

    # 5. ЗАПИСЫВАЕМ СТАВКУ В БАЗУ SUPABASE (Строго на 1 день)
    supabase.table("users").update({
        "mimic_target_id": victim["user_id"],
        "last_mimic_date": str(today)
    }).eq("user_id", user.id).execute()

    username_display = f" (@{victim['username']})" if victim.get("username") else ""
    victim_name = f"{victim['first_name']}{username_display}"

    # Собираем динамические гендерные глаголы для вызывающего (player)
    razvorachivaet_text = g_text(player, "разворачивает карту Мимика", "разворачивает карту Мимикрии 💅")
    podkl_text = g_text(player, "Подключаемся к датчикам", "Подключилась к датчикам")

    mimic_phrases = [
        f"🎭 <b>ЗЕРКАЛЬНЫЙ ПРОТОКОЛ ЗАПУЩЕН!</b> <b>{user.first_name}</b> {razvorachivaet_text}!",
        f"📡 {podkl_text} удачи <b>{victim_name}</b>... Ставка принята! Куда упадёт монета рулетки казино — туда улетит и твоя карма! 🗿"
    ]

    for phrase in mimic_phrases:
        await context.bot.send_message(chat_id=chat_id, text=phrase, parse_mode="Markdown")
        await asyncio.sleep(1.5)

    # Мемный стикер наведения цели
    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERl5RqYy9g5SuIKeL-HYdt9H78f80S9wACGTkAAnsn4UlP1wuYX7Od8j0E')

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()
    current_week_num = today.isocalendar()[1]

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Устраивать дуэли можно только в групповых чатах!")
        return

    # 1. Вытаскиваем данные стрелка из базы
    shooter_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not shooter_res.data:
        await update.message.reply_text("❌ Тебя нет в рулетке! Напиши /register")
        return
    shooter = shooter_res.data[0]
    
    # === 🛡 ПРОВЕРКА ПУСТОГО СТВОЛА СТРЕЛКА (На взлёте) ===
    db_shooter_duel = shooter.get("duel_count", 0)
    shooter_week = db_shooter_duel // 100 if db_shooter_duel != 0 else current_week_num
    shooter_attempts = db_shooter_duel % 100 if db_shooter_duel != 0 else 0
    if current_week_num != shooter_week:
        shooter_attempts = 0

    if shooter_attempts >= 6:
        # Экранируем имя стрелка, чтобы спецсимволы в никах не ломали HTML-верстку
        safe_shooter_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")

        # Собираем динамические гендерные глаголы и обращения для Стрелка (player)
        prish_text = g_text(player, "ты пришёл в игровую зону", "ты пришла в игровую зону 💅")
        rasstrel_text = g_text(player, "ты уже расстрелял", "ты уже расстреляла")
        pozo_text = g_text(player, "не позорься", "не расстраивайся, подруга! 💅")

        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Полный переход на стиль комфортного казино и HTML-броню
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💨 <b>Осечка! Обойма пуста...</b>\n\n"
                 f"{safe_shooter_name}, {prish_text} с разряженным маркером! Все 6 патронов на этой неделе {rasstrel_text}. 🤦‍♂️\n"
                 f"❌ КРУПЬЕ ЗАКРЫВАЕТ ДОСТУП! Отдохни от азарта за барной стойкой до понедельника и {pozo_text}!",
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERocZqavV1gUjQriQqP3uLpw6uz9qdAwAChhEAAoC6wEokCKx8CQHogD0E')
        return

    # 2. УЛЬТИМАТИВНЫЙ ПАРСИНГ ЖЕРТВЫ (Твоя схема из карты UNO)
    if not context.args and not update.message.entities:
        await update.message.reply_text("❌ Кого вызываем на дуэль? Тегни цель: `/duel @username` или @ и выбери имя из списка!")
        return

    target_username = None
    target_user_id = None

    for entity in update.message.entities:
        if entity.type == "mention":
            target_username = update.message.text[entity.offset:entity.offset + entity.length].replace("@", "")
            break
        elif entity.type == "text_mention":
            target_user_id = entity.user.id
            break

    # Ищем жертву в базе
    if target_user_id:
        target_res = supabase.table("users").select("*").eq("user_id", target_user_id).eq("is_active", True).execute()
    elif target_username:
        target_res = supabase.table("users").select("*").eq("username", target_username).eq("is_active", True).execute()
    else:
        await update.message.reply_text("❌ Нужно именно тегнуть игрока!")
        return
    
    if not target_res.data or len(target_res.data) == 0:
        await update.message.reply_text("❌ Этого юзера нет в рулетке, или он ливнул!")
        return
    
    victim = target_res.data[0]
    victim_id = victim["user_id"]

    if victim_id == user.id:
        # Собираем динамический ироничный отлуп на основе пола игрока (player)
        samostrel_text = g_text(player, "Стрелять в самого себя?", "Устроить дуэль с самой собой?")
        choose_target_text = g_text(player, "выбери другую цель", "выбери другого оппонента, подруга")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎯 <b>{samostrel_text}</b> Казино такого не одобряет, {choose_target_text}.",
            parse_mode="HTML"
        )
        return

        
    # === 🛡 ПРОВЕРКА РОМЫ: Есть ли вообще патроны у жертвы на этой неделе? ===
    db_victim_duel = victim.get("duel_count", 0)
    victim_week = db_victim_duel // 100 if db_victim_duel != 0 else current_week_num
    victim_attempts = db_victim_duel % 100 if db_victim_duel != 0 else 0
    
    if current_week_num != victim_week:
        victim_attempts = 0

    # Проверяем лимиты патронов жертвы (на основе объекта victim)
    if victim_attempts >= 6:
        # Собираем динамические гендерные глаголы и атмосферные фразы для Жертвы
        drug_title = g_text(victim, "Наш завсегдатай", "Прекрасная леди")
        otstrel_text = g_text(victim, "отстрелял все свои патроны подчистую", "использовала все свои попытки на этой неделе")
        relax_text = g_text(victim, "закинул ноги на соседний стул, цедит бурбон", "отдыхает в лаунж-зоне, цедит коктейль 🍸")
        alko_text = g_text(victim, "свой бурбон", "свой напиток(мы понимаем какого содержания)")
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🥃 <b>Священный барный час!</b> {drug_title} <b>{victim['first_name']}</b> {otstrel_text}. "
                 f"Сейчас {g_text(victim, 'он', 'она')} {relax_text} и не {g_text(victim, 'настроен', 'настроена')} на глупости. 🥂\n\n"
                 f"❌ Отставить вызовы! Дай человеку спокойно допить {alko_text}.",
            parse_mode="HTML"
        )
        return

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERocRqavSrSDLKuprwdNbdTUucfvAVIgACkREAAj7PkUlwAAH9MmAfvmE9BA')
        return

    # 3. ЛОГИКА ВЗАИМНОГО ВЫЗОВА
    # Проверяем, не вызвала ли жертва уже нашего стрелка ранее
    if victim.get("duel_target_id") == user.id:
        # МАТЧ! Взаимный вызов зафиксирован -> Запуск дуэли!
        
        # Сразу очищаем цели дуэлей у обоих в базе, чтобы закрыть лазейки для спама
        supabase.table("users").update({"duel_target_id": None}).eq("user_id", user.id).execute()
        supabase.table("users").update({"duel_target_id": None}).eq("user_id", victim_id).execute()

        # Красивые имена для вывода
        v_username_display = f" (@{victim['username']})" if victim.get("username") else ""
        v_name = f"{victim['first_name']}{v_username_display}"
        
        # Собираем динамические гендерные статусы для обоих участников дуэли
        # player — тот, кто принял вызов (текущий user), victim — тот, кто его бросил
        p_title = g_text(player, "Ковбой", "Леди")
        v_title = g_text(victim, "ковбой", "леди")
        
        # Динамический глагол для описания пары
        if player.get("gender") == "girl" and victim.get("gender") == "girl":
            shodyatsya_text = "Прекрасные леди"
        elif player.get("gender") == "boy" and victim.get("gender") == "boy":
            shodyatsya_text = "Игроки"
        else:
            shodyatsya_text = "Участники"

        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Полный переход на стиль комфортного казино и HTML-броню
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"💥 <b>ВЗАИМНЫЙ ВЫЗОВ ПРИНЯТ!</b> 💥\n\n"
                f"{shodyatsya_text} <b>{user.first_name}</b> и <b>{v_name}</b> сходятся за игровым столом...\n"
                f"Атмосфера накалена до предела! Все ставки сделаны, фортуна начинает свой ход! 🎰🎲"
            ),
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERnotqaMvN6_wsk1CPke39HxtwJyuPDwACUhEAArywIErXQg4EzgXGxj0E')
        await asyncio.sleep(3.5) # Валидольная пауза для нагнетания

        # Разбираем обойму ПРИНЯВШЕГО дуэль (shooter)
        db_shooter_duel = shooter.get("duel_count", 0)
        shooter_week = db_shooter_duel // 100 if db_shooter_duel != 0 else current_week_num
        shooter_attempts = db_shooter_duel % 100 if db_shooter_duel != 0 else 0
        if current_week_num != shooter_week:
            shooter_attempts = 0

        # Разбираем обойму ВЫЗВАВШЕГО дуэль (victim)
        db_victim_duel = victim.get("duel_count", 0)
        victim_week = db_victim_duel // 100 if db_victim_duel != 0 else current_week_num
        victim_attempts = db_victim_duel % 100 if db_victim_duel != 0 else 0
        if current_week_num != victim_week:
            victim_attempts = 0

        # Рандом боя 50/50
        if random.randint(1, 100) <= 50:
            winner = shooter
            loser = victim
        else:
            winner = victim
            loser = shooter

        # Списываем по одному патрону у обоих участников (записываем новую неделю + попытку)
        new_db_shooter = (current_week_num * 100) + (shooter_attempts + 1)
        new_db_victim = (current_week_num * 100) + (victim_attempts + 1)
        supabase.table("users").update({"duel_count": new_db_shooter}).eq("user_id", shooter["user_id"]).execute()
        supabase.table("users").update({"duel_count": new_db_victim}).eq("user_id", victim_id).execute()

        # Сколько патронов осталось у каждого ковбоя на этой неделе
        shooter_bullets_left = 6 - (shooter_attempts + 1)
        victim_bullets_left = 6 - (victim_attempts + 1)

        # Обновляем статистику побед и поражений
        new_wins = winner.get("duel_wins", 0) + 1
        supabase.table("users").update({"duel_wins": new_wins}).eq("user_id", winner["user_id"]).execute()

        new_losses = loser.get("duel_losses", 0) + 1
        supabase.table("users").update({"duel_losses": new_losses}).eq("user_id", loser["user_id"]).execute()

        # Считаем остаток патронов для вывода конкретно для победителя и лузера
        winner_left = shooter_bullets_left if winner["user_id"] == shooter["user_id"] else victim_bullets_left
        loser_left = victim_bullets_left if winner["user_id"] == shooter["user_id"] else shooter_bullets_left

        # Собираем динамические гендерные глаголы для Победителя (winner)
        vystrel_text = g_text(winner, "Метким выстрелом", "Точным выстрелом 💥")
        vyrval_text = g_text(winner, "победу вырывает", "победу вырывает") # Универсально

        # Собираем динамические гендерные титулы для Проигравшего (loser)
        pobezh_title = g_text(loser, "поражённый оппонент", "поражённая леди 🐍")
        otprav_text = g_text(loser, "отправляется перезаряжать ствол", "отправляется на перезарядку своего дерринджер")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎰 <b>РАУНД ЗАВЕРШЕН! ВСЕ СТАВКИ СЫГРАЛИ!</b> 🎰\n\n"
                 f"🎯 {vystrel_text} главную победу {vyrval_text} <b>{winner['first_name']}</b>! 👑 <i>(осталось патронов в обойме: {winner_left}/6)</i>\n"
                 f"🐌 А {pobezh_title} <b>{loser['first_name']}</b> {otprav_text}! <i>(осталось патронов в обойме: {loser_left}/6)</i>\n\n"
                 f"📊 <i>Рейтинг лиги обновлен. Очки успешно зачислены, дуэлянты продолжают копить серии выстрелов для получения наград от администрации казино 🎰!</i> 🏆",
            parse_mode="HTML"
        )

        await asyncio.sleep(1.5)

        # === 🏆 ПРОВЕРКА НАКОПИТЕЛЬНЫХ БОНУСОВ СЕРИИ ПОВТОРОВ (КРАТНО 5) ===
        if new_wins % 5 == 0:
            supabase.table("users").update({
                "kras_weight": winner.get("kras_weight", 100.0) + 10.0,
                "pidor_weight": max(50.0, winner.get("pidor_weight", 100.0) - 5.0)
            }).eq("user_id", winner["user_id"]).execute()
            
            # Собираем динамические гендерные статусы и глаголы для Чемпиона (winner)
            champion_title = g_text(winner, "ЧЕМПИОН ЛИГИ ДУЭЛЕЙ", "ЧЕМПИОНКА ЛИГИ ДУЭЛЕЙ 👑")
            nabivaet_text = g_text(winner, "набивает", "забирает")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔥 <b>НЕУДЕРЖИМЫЙ {champion_title}!</b> 🔥\n\n"
                     f"Игрок <b>{winner['first_name']}</b> {nabivaet_text} юбилейную серию из <b>{new_wins} побед</b>!\n"
                     f"Администрация казино 🎰 активирует тайное благословение за игровым столом:\n\n"
                     f"👑 Твоя базовая удача стать Красавчиком дня ВЫРОСЛА, а шансы поймать клеймо Пидора — чутка снизились! 🎰",
                parse_mode="HTML"
            )

            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERnoVqaMte344WUNdSgVyflZHrOJlKuQACVh8AAkl06UqcZ7snP84WFz0E')

        if new_losses % 5 == 0:
            supabase.table("users").update({
                "pidor_weight": loser.get("pidor_weight", 100.0) + 10.0,
                "kras_weight": max(50.0, loser.get("kras_weight", 100.0) - 5.0)
            }).eq("user_id", loser["user_id"]).execute()

            # Собираем динамические гендерные статусы и глаголы для Неудачника серии (loser)
            bedolaga_title = g_text(loser, "Бедолага", "Грустная леди")
            slit_text = g_text(loser, "слить", "уступить")
            meshok_title = g_text(loser, "МЕШОК ТЫ ДЛЯ ТРЕНИРОВОК", "ЖЕРТВА РУССКОЙ РУЛЕТКИ")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🎪 <b>{meshok_title}!</b> 🎪\n\n"
                     f"{bedolaga_title} <b>{loser['first_name']}</b> умудряется {slit_text} уже <b>{new_losses} дуэлей</b> за сезон!\n"
                     f"Высшие силы казино наказывают за слабость:\n\n"
                     f"🤡 Проклятие рулетки активировано! Твоя притягательность к позорному титулу Пидора дня стала выше! Берегись следующего утреннего прокрута! 🛑",
                parse_mode="HTML"
            )

            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERnolqaMu2DjAqCDeG0IT2CB73uWoaawACZRIAAq7CwUpOdz-pcVw-UT0E')

    else:
        # Обычный первичный вызов: записываем цель дуэли стрелку в базу
        supabase.table("users").update({"duel_target_id": victim_id}).eq("user_id", user.id).execute()
        
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перешли на стандарт 100, чтобы остаток патронов выводился честно!
        db_shooter_duel = shooter.get("duel_count", 0)
        shooter_attempts = db_shooter_duel % 100 if (db_shooter_duel != 0 and (db_shooter_duel // 100) == current_week_num) else 0
        bullets_now = 6 - shooter_attempts

        # Создаем красивое имя жертвы для этой ветки кода
        v_username_display = f" (@{victim['username']})" if victim.get("username") else ""
        v_name = f"{victim['first_name']}{v_username_display}"

        # Собираем динамические гендерные фразы для Стрелка (player)
        vyzval_text = g_text(player, "вызывает на дуэль", "бросает элегантный, но опасный вызов 💥")
        zhdem_text = g_text(player, "Ждем ответного вызова от цели.", "Ждем, пока цель примет вызов.")

        # УЛЬТРА-ФИКС: Полностью убрали ВСЕ звёздочки из этого текста. Перевели на чистый HTML!
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"⚔️ <b>ВЫЗОВ БРОШЕН! ПЕРЧАТКА В ЛИЦО!</b> ⚔️\n\n"
                f"Игрок <b>{user.first_name}</b> {vyzval_text} <b>{v_name}</b>!\n"
                f"🎯 Твой остаток патронов в обойме: <b>{bullets_now} из 6</b>\n\n"
                f"{zhdem_text} Напиши команду <code>/duel</code> на этого игрока, чтобы взвести курок и запустить раунд! 🔫"
            ),
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERnnhqaMio_yi6YSjV0Ysi5q16lPq1ogAC9xIAAvmEAUtGFDZQ8K2jFj0E')
    
async def switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    if update.effective_chat.type == "private":
        await context.bot.send_message(chat_id=chat_id, text="❌ Юзать карту UNO можно только в групповых чатах!")
        return

    # 1. Проверяем, является ли вызвавший ПИДОРОМ СЕГОДНЯШНЕГО ДНЯ
    today_winner = get_today_winner("pidor")
    if not today_winner or today_winner["user_id"] != user.id:
        await context.bot.send_message(chat_id=chat_id, text="🤡 Ты не сегодняшний пидор дня, чтобы активировать карту UNO. Сиди тихо!")
        return

    # 2. Проверяем КД команды (Умная детекция 6 обычных или 12 штрафных дней)
    user_res = supabase.table("users").select("last_switch_date").eq("user_id", user.id).execute()
    
    if user_res.data and len(user_res.data) > 0 and user_res.data[0].get("last_switch_date"): 
        last_date = date.fromisoformat(user_res.data[0]["last_switch_date"]) 
        days_passed = (today - last_date).days
        
        # Если прошло меньше 6 дней от записанной даты (с учетом штрафного сдвига — КД заблокирован)
        if days_passed < 6:
            days_left = 6 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            
            # --- 👑 [НОВОЕ] ДЕТЕКЦИЯ КОРОЛЕВСКОГО ПОЗОРА (Если кулдаун больше 6 дней) ---
            if days_left > 6:
                # Собираем динамические гендерные глаголы для Стрелка (player)
                promazal_text = g_text(player, "ты позорно промазал", "ты позорно промазала 🐍")
                poluchil_text = g_text(player, "получил удвоенное наказание", "получила удвоенное наказание")

                cd_message = (
                    f"❌ <b>Твоя карта UNO заблокирована владельцем казино!</b>\n\n"
                    f"При попытке ограбить Красавчика дня {promazal_text}, поэтому {poluchil_text}.\n"
                    f"Отдохни пока от карт в лаунж-зоне за барной стойкой, доступ вернётся только через <b>{days_left} {day_word}</b>! ⏳🎰"
                )

            else:
                # Обычный стандартный кулдаун на 6 дней
                cd_message = f"❌ Твоя карта UNO всё еще на перезарядке! Доступ появится через <b>{days_left} {day_word}</b>."

            await context.bot.send_message(
                chat_id=chat_id,
                text=cd_message,
                parse_mode="HTML"
            )
            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReRpqQ3-pZ9QRME44W1Es3DPWTGUPNAACkAIAAladvQoy0qlxuNTQtTwE')
            return

    # 3. УЛЬТИМАТИВНЫЙ ПАРСИНГ ЖЕРТВЫ (Защита от юзеров без Username)
    if not context.args and not update.message.entities:
        await context.bot.send_message(chat_id=chat_id, text="❌ На кого перевод? Тегни жертву через @username или кликни по его имени в меню упоминаний!")
        return

    target_username = None
    target_user_id = None

    for entity in update.message.entities:
        if entity.type == "mention":
            target_username = update.message.text[entity.offset:entity.offset + entity.length].replace("@", "")
            break
        elif entity.type == "text_mention":
            target_user_id = entity.user.id
            break

    if target_user_id:
        target_res = supabase.table("users").select("*").eq("user_id", target_user_id).eq("is_active", True).execute()
    elif target_username:
        target_res = supabase.table("users").select("*").eq("username", target_username).eq("is_active", True).execute()
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Нужно именно тегнуть игрока! Выбери его имя из выпадающего списка Телеграма, когда пишешь /switch @.")
        return
    
    if not target_res.data or len(target_res.data) == 0:
        await context.bot.send_message(chat_id=chat_id, text="❌ Этого юзера нет в рулетке, или он ливнул из игры!")
        return
    
    victim = target_res.data[0]

    if victim["user_id"] == user.id:
        # Собираем динамические гендерные подколы для игрока (player)
        genius_title = g_text(player, "гений мысли, ничего не скажешь", "хитрая леди, ничего не скажешь 🐍")
        another_target = g_text(player, "выбери другую цель", "выбери другого оппонента")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎭 <b>Переводить карту на самого себя?</b> Ну ты {genius_title}! Оригинальный ход, но правила казино едины для всех — {another_target}. 🎰",
            parse_mode="HTML"
        )
        return

    # === 🛡️ ИСТОЧНИК БЕЗОПАСНЫХ ИМЕН ДЛЯ ВСЕЙ ОСТАВШЕЙСЯ ФУНКЦИИ ===
    v_username = f" (@{victim['username']})" if victim.get('username') else ""
    victim_name = f"{victim['first_name']}{v_username}"
    
    safe_user_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")
    safe_victim_name = victim_name.replace("<", "&lt;").replace(">", "&gt;")

    # Проверяем, является ли это ВТОРОЙ попыткой перевода
    is_retry_attempt = context.user_data.get("switch_retry", False)
    
    # БЕЗОПАСНАЯ УМНАЯ ПРОВЕРКА КРАСАВЧИКА 
    kras_today_res = supabase.table("daily_winners").select("*").eq("game_date", str(today)).eq("role", "krasavchik").execute()
    
    is_robbing_chad = False
    if kras_today_res.data and len(kras_today_res.data) > 0:
        if kras_today_res.data[0]["user_id"] == victim["user_id"]:
            is_robbing_chad = True

    # Вытаскиваем неудачника монетки напрямую из Supabase
    coin_loser_res = supabase.table("daily_winners").select("user_id").eq("game_date", str(today)).eq("role", "coin_loser").execute()
    
    is_coin_loser_target = False
    if coin_loser_res.data and len(coin_loser_res.data) > 0:
        if coin_loser_res.data[0]["user_id"] == victim["user_id"]:
            is_coin_loser_target = True
    # ================= ФИКС ОТОБРАЖЕНИЯ ИМЕНИ =================
    # Бот создаст красивое имя жертвы для вывода в чат, даже если у него нет @username
    username_display = f" (@{victim['username']})" if victim.get("username") else ""
    victim_name = f"{victim['first_name']}{username_display}"
    
    # Готовим абсолютно безопасные HTML-имена для интро и выводов
    safe_user_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")
    safe_victim_name = victim_name.replace("<", "&lt;").replace(">", "&gt;")
    
    # Готовим динамические гендерные глаголы и обращения для Стрелочника (player)
    resh_text = g_text(player, "решил", "решила 🐍")
    retry_hand_text = g_text(player, "трясущимися руками повторно активирует", "элегантным, но рискованным жестом повторно активирует")

    # Готовим динамические гендерные глаголы для Жертвы (victim)
    loser_coin_text = g_text(victim, "проиграл", "проиграла")

    # 4. ВЫДАЕМ ИНТРО-ТЕКСТ С УЧЕТОМ ДИНАМИЧЕСКИХ ШАНСОВ И ГЕНДЕРОВ (ЖЕЛЕЗНО НА HTML)
    if is_robbing_chad:
        intro = [
            f"👑 <b>КРАЖА ВЕКА!</b> Пидор дня <b>{safe_user_name}</b> активирует карту «UNO» против Красавчика <b>{safe_victim_name}</b>!",
            f"🎲 Это Королевское Ограбление! Шанс 15%. Если сработает, титулы поменяются за игровым столом, а карта ОСТАНЕТСЯ ЦЕЛОЙ! 🔥",
        ]
    elif is_coin_loser_target:
        intro = [
            f"🎯 <b>ДОБИВАНИЕ РАНЕНОГО!</b> <b>{safe_user_name}</b> активирует карту «UNO» против <b>{safe_victim_name}</b>!",
            f"🎲 Этот оппонент сегодня и так эпично {loser_coin_text} в монетку, а ты {resh_text} его добить? Рискованный азарт! Шанс перевода повышен до 45%! 🔥\n⚠️ Внимание: в случае провала твой утренний позорный коэффициент умножится на 3!",
        ]
    else:
        if is_retry_attempt:
            intro = [
                f"🔥 <b>ВТОРОЙ ШАНС!</b> <b>{safe_user_name}</b> {retry_hand_text} карту «UNO» против мирного <b>{safe_victim_name}</b>!",
                f"🎲 На этот раз боги рандома шутить не будут. Вероятность 20%. Либо забираешь куш, либо сгораешь окончательно...",
            ]
        else:
            intro = [
                f"🃏 <b>МЕМНЫЙ РЕВЁРС!</b> <b>{safe_user_name}</b> активирует карту «UNO» и пытается скинуть утреннее клеймо на <b>{safe_victim_name}</b>!",
                f"🎲 Шанс перевода 30%... Крупье казино взвешивает ставки... 🎰",
            ]

    for phrase in intro:
        await context.bot.send_message(chat_id=chat_id, text=phrase, parse_mode="HTML")
        await asyncio.sleep(1.0) # Оптимизировали паузу до 1 секунды для ускорения функции

    # --- 🎰 ПОВЫШЕННЫЙ РАСЧЕТ ШАНСОВ (15% / 30% / 15% / 75%) ---
    if is_robbing_chad:
        success_chance = 15  
    elif is_coin_loser_target:
        success_chance = 45 
    elif is_retry_attempt:
        success_chance = 50  
    else:
        success_chance = 30  

    is_success = random.randint(1, 100) <= success_chance

    # --- 📊 [ЧЕСТНЫЙ ФИКС]: СЧИТАЕМ СИЛУ ТОЛЬКО СЕГОДНЯШНЕГО УТРЕННЕГО ПОЗОРА ---
    fresh_winner_res = supabase.table("users").select("pidor_count").eq("user_id", user.id).execute()
    fresh_pidor_count = fresh_winner_res.data[0]["pidor_count"] if fresh_winner_res.data else today_winner["pidor_count"]
    
    # Сила утреннего позора (сколько прилетело сегодня: 1, 2, 3 или 5)
    today_gained_pidors = max(1, fresh_pidor_count - today_winner["pidor_count"])
    
    if is_coin_loser_target:
        # Х3 НАКАЗАНИЕ ЗА РАНЕНОГО: Утренний позор умножается на 3. 
        # Значит, чистая прибавка в базу равна утренней дозе, умноженной на 2!
        added_penalty = today_gained_pidors * 2
        total_day_gained = today_gained_pidors * 3
    else:
        # Х2 НАКАЗАНИЕ ДЛЯ ОСТАЛЬНЫХ: Утренний позор умножается на 2. 
        # Значит, чистая прибавка в базу равна ровно одной утренней дозе!
        added_penalty = today_gained_pidors
        total_day_gained = today_gained_pidors * 2

    # Переменная для вывода в текст сообщения теперь СТРОГО равна чистой прибавке в базу!
    penalty_p_count = added_penalty

    # Жесткое х3 наказание за провал добивания раненого (Вес взлетает до 150.0)
    if not is_success and is_coin_loser_target:
        # Прибавляем ЧИСТУЮ добавку added_penalty к текущему счету
        supabase.table("users").update({
            "last_switch_date": str(today), 
            "pidor_count": fresh_pidor_count + added_penalty,
            "pidor_weight": 150.0
        }).eq("user_id", user.id).execute()
        
        # Записываем провал в лог
        try:
            supabase.table("uno_logs").insert({
                "sender_name": user.first_name,
                "victim_name": victim["first_name"],
                "game_date": str(today),
                "multiplier": total_day_gained, # Запишет финальный итог (3, 6 или 9)
                "is_krasavchik": False
            }).execute()
        except Exception:
            pass
        # Собираем динамический глагол промаха на основе пола Стрелка (player)
        umudrilsya_text = g_text(player, "умудрился", "умудрилась")
        nakazali_text = g_text(player, "карают тебя за излишний риск", "карают тебя за излишний риск, леди 🐍")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>ТОТАЛЬНОЕ КАРМИЧЕСКОЕ ПРАВОСУДИЕ!</b> ❌\n\n"
                 f"Карта UNO расплавилась в руках <b>{safe_user_name}</b> при попытке забрать куш у уязвимого оппонента! Шанс был 45%, но ты {umudrilsya_text} промазать!\n\n"
                 f"Боги рандома {nakazali_text} в тройном размере: твой утренний позор умножается на 3! Получай ещё <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>! Штрафной вес взлетает до 150.0! 🤡💥💣",
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
        return  

    # ================= 🎉🎉🎉 УСПЕШНЫЙ ПЕРЕВОД 🎉🎉🎉 =================
    if is_success:
        context.user_data.pop("switch_retry", None) # очищаем память ретрая
        
        # 👑 ПУТЬ А: УСПЕШНОЕ ОГРАБЛЕНИЕ КРАСАВЧИКА (КД НЕ ЗАПИСЫВАЕМ!)
        if is_robbing_chad:
            # 1. Обновляем Стрелочника (берем старый pidor_count/kras_count из today_winner)
            supabase.table("users").update({
                "pidor_count": max(0, today_winner["pidor_count"] - 1), 
                "kras_count": today_winner["kras_count"] + 1, 
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

            # [ЛОГ УНО] Записываем Королевское ограбление в историю
            supabase.table("uno_logs").insert({
                "sender_name": user.first_name,
                "victim_name": victim["first_name"],
                "game_date": str(today),
                "multiplier": pidor_multiplier, # Сохраняем текущий множитель
                "is_krasavchik": True          # МАРКЕР: УКРАЛ КРАСАВЧИКА!
            }).execute()

            try:
                # Собираем динамические гендерные статусы для Победителя (player) и Жертвы (victim)
                winner_status = g_text(player, "СТАНОВИТСЯ НОВЫМ КРАСАВЧИКОМ ДНЯ!", "СТАНОВИТСЯ НОВОЙ КРАСАВИЦЕЙ ДНЯ! 👑")
                victim_status = g_text(victim, "признаётся <b>ПИДОРОМ ДНЯ</b>!", "признаётся <b>ПИДОРОМ ДНЯ</b>!")
                fallen_text = g_text(victim, "с позором падает на дно и", "теряет всё за игровым столом и")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"💥 <b>БОЖЕ МОЙ, ЭТО ИСТОРИЧЕСКИЙ МОМЕНТ! КАРТА ОСТАЕТСЯ ЦЕЛОЙ!</b> 💥\n\n"
                        f"Королевское ограбление завершилось полным триумфом за игровым столом!\n"
                        f"😎 <b>{safe_user_name}</b> забирает главный куш и {winner_status}\n\n"
                        f"🤡 А вот <b>{safe_victim_name}</b> {fallen_text} {victim_status}"
                    ),
                    parse_mode="HTML"
                )
                
            except Exception as e:
                print(f"Ошибка вывода триумфа ограбления: {e}")
                    parse_mode="HTML"
                )
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERfwtqSi0WKXA0-slyXjuDMUAC14PGkAAC6BMAAp7K8UkQAAGdV1VM7UI8BA')
                
            except Exception as e:
                print(f"Ошибка вывода триумфа UNO: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🔧 <b>Сука, опять вы всё сломали!</b> 🤦‍♂️\n\nКоролевское ограбление Красавчика зависло в текстурах Телеграма! Корона украдена, админ пошёл чинить!",
                    parse_mode="HTML"
                )
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERv_1qh-RMBre9eek9ykdsovu3gf-SvwACCnUAAlgXsEkCKvJjaqw9iT0E')

        # 🃏 ПУТЬ Б: УСПЕШНЫЙ ОБЫЧНЫЙ ПЕРЕВОД / ДОБИВАНИЕ (ВЫЧИСЛЯЕМ МНОЖИТЕЛЬ ПОЗОРА)
        if not is_robbing_chad:
            # Записываем КД стрелочнику
            supabase.table("users").update({"last_switch_date": str(today)}).eq("user_id", user.id).execute()
            
            # --- 📊 ДИНАМИЧЕСКИЙ РАСЧЕТ МНОЖИТЕЛЯ ПОЗОРА (Честность для чата) ---
            # Вытаскиваем свежие данные Ани из базы ПОСЛЕ рулетки, чтобы понять, сколько ей начислило
            fresh_winner_res = supabase.table("users").select("pidor_count").eq("user_id", user.id).execute()
            
            # Если в базе уже 13, а в today_winner (до рулетки) было 10, то позор_джекпот = 3
            fresh_pidor_count = fresh_winner_res.data[0]["pidor_count"] if fresh_winner_res.data else today_winner["pidor_count"]
            
            # Вычисляем, какой множитель прилетел сегодня (х1, х2, х3 или х5)
            pidor_multiplier = max(1, fresh_pidor_count - today_winner["pidor_count"])
            
            # 1. Обновляем Стрелочника (списываем ВСЕ начисленные сегодня позоры под ноль!)
            supabase.table("users").update({
                "pidor_count": max(0, fresh_pidor_count - pidor_multiplier), 
                "pidor_weight": 85.0
            }).eq("user_id", user.id).execute()
            
            # 2. Обновляем Жертву (навешиваем ей ВЕСЬ сегодняшний джекпот целиком!)
            supabase.table("users").update({
                "pidor_count": victim["pidor_count"] + pidor_multiplier, 
                "pidor_weight": 80.0
            }).eq("user_id", victim["user_id"]).execute()
            
            # Точечно перебиваем историю сегодняшнего дня в daily_winners
            supabase.table("daily_winners").update({"user_id": victim["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()
            
            # [ЛОГ УНО] Записываем успешный перевод в историю
            supabase.table("uno_logs").insert({
                "sender_name": user.first_name,
                "victim_name": victim["first_name"],
                "game_date": str(today),
                "multiplier": pidor_multiplier,
                "is_krasavchik": False
            }).execute()

# --- 🛡️ БРОНЕБОЙНАЯ ОТВЕТКА С УЧЕТОМ МНОЖИТЕЛЯ ---
        try:
            if is_coin_loser_target:
                # 🪓 УСПЕШНОЕ ДОБИВАНИЕ РАНЕНОГО В МОНЕТКУ (45% ШАНС)
                # Собираем динамические глаголы и обращения для Стрелка (player)
                strelok_action = g_text(player, "активировал карту", "активировала карту 💥")
                hitry_title = g_text(player, "хитрый", "хитрая 🐍")
                spis_text = g_text(player, "нагло списывает себе пидора", "технично списывает с себя позор")

                # Собираем динамические титулы для жертвы (victim)
                victim_status = g_text(victim, "лежал без защиты после проигрыша", "лежала без защиты после проигрыша")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🪓 <b>БЕЗЖАЛОСТНОЕ ДОБИВАНИЕ ОФОРМЛЕНО!</b> 🪓\n\n"
                        f"Игрок <b>{safe_user_name}</b> {strelok_action} против раненого <b>{safe_victim_name}</b> и пробил его защиту с 45% шансом! ⚡️\n\n"
                        f"🎯 <b>{safe_victim_name}</b> {victim_status} в монетку, а теперь забирает клеймо ПИДОРА ДНЯ себе! Полное фиаско за игровым столом! 🗿\n"
                        f"😎 А {hitry_title} <b>{safe_user_name}</b> {spis_text} и уходит отдыхать в лаунж-зону!"
                    ),
                    parse_mode="HTML"
                )

                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERl5ZqYzAUBU7z06cdM38fa4YZfog1xAACYwEAAnHpkDYtQnUiFYhhSj0E')
            
            elif is_retry_attempt:
                # 🦊 УСПЕШНЫЙ ВТОРОЙ ШАНС (20% ШАНС) — ЧИСТЫЙ ВАРИАНТ БЕЗ TRY
                # Собираем динамические титулы и глаголы для Стрелка (player)
                fox_title = g_text(player, "ХИТРЫЙ ЛИС В ДЕЛЕ", "ХИТРАЯ ЛИСА В ДЕЛЕ 🦊")
                ochishen_text = g_text(player, "полностью очищен от подозрений, мастер тактики", "полностью очищена от подозрений, королева интуиции 💎")

                # Собираем динамические статусы для пострадавшего оппонента (victim)
                victim_status = g_text(victim, "официально становится <b>ПИДОРОМ ДНЯ</b>", "официально становится <b>ПИДОРОМ ДНЯ</b>")
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🦊 <b>КАК ТАК-ТО?! {fox_title}!</b> 🦊\n\n"
                        f"Первая карта задымилась, но со второго шанса <b>{safe_user_name}</b> {g_text(player, 'совершает невозможное', 'совершает невозможное')} и выбивает заветные 20%!\n"
                        f"👑 Ты {ochishen_text}!\n\n"
                        f"🤡 А вот <b>{safe_victim_name}</b> {victim_status} со второй подачи за игровым столом! Ставки приняты! 🎰"
                    ),
                    parse_mode="HTML"
                )

                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERg8xqT1rvV4e9QOkd5krbAdwHGMbORQACrB8AAi-rqEswnXHdk_VAETwE')
            
            else:
                # 💥 ОБЫЧНЫЙ ПЕРЕВОД (30% ШАНС) — ТЕПЕРЬ С ГЕНДЕРАМИ ПАЦАНОВ И ДЕВЧОНОК
                multiplier_alert = f" (с учётом множителя х{pidor_multiplier}!)" if pidor_multiplier > 1 else ""
                    
                # Собираем глаголы очищения для Стрелочника и позора для Жертвы
                sender_clean_text = g_text(player, "полностью очищен от подозрений", "полностью очищена от подозрений")
                victim_status_text = g_text(victim, "становится <b>ПИДОРОМ ДНЯ</b>", "становится <b>ПИДОРОМ ДНЯ</b>")
                victim_accept_text = g_text(victim, "Смирись!", "Смирись, подруга! 💅")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"💥 <b>КАРТА ПЕРЕВЕДЕНА!</b> Магия 30% сработала!\n\n"
                        f"👑 <b>{safe_user_name}</b> {sender_clean_text}.\n"
                        f"🤡 Новая официальная жертва: <b>{safe_victim_name}</b> {victim_status_text}! {victim_accept_text}{multiplier_alert}"
                    ),
                    parse_mode="HTML"
                )

                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQxqQ3c1Ul6X4NVVPO-Fd7SdNeiqIgACx04AAnJSgEuFrKam1iO89TwE')

        except Exception as e:
            print(f"Ошибка вывода результата UNO: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="🔧 <b>Сука, опять вы всё сломали!</b> 🤦‍♂️\n\nКарта UNO отработала в базе, но сообщение улетело в молоко. Щас починим!",
                parse_mode="HTML"
            )
            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERv_1qh-RMBre9eek9ykdsovu3gf-SvwACCnUAAlgXsEkCKvJjaqw9iT0E')

# ================= ❌❌❌ ВЫПАЛ ПРОВАЛ (ГЕНДЕРНАЯ ТИТАНОВАЯ БРОНЯ) =================
    if not is_success:
        safe_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")

        # Готовим динамические глаголы провала для Стрелочника (player)
        promazal_text = g_text(player, "промазал", "промазала")
        poluchil_text = g_text(player, "получил", "получила")
        nakazali_text = g_text(player, "наказали тебя за жестокость", "наказали тебя за жестокость, подруга")
        umudrilsya_text = g_text(player, "умудрился", "умудрилась")

        try:
            if is_robbing_chad:
                # Провал Красавчика: 12 дней КД и х2 утреннего штрафа
                fake_cd_date = today - timedelta(days=6)
                supabase.table("users").update({
                    "last_switch_date": str(fake_cd_date), 
                    "pidor_count": fresh_pidor_count + added_penalty,
                    "pidor_weight": 110.0
                }).eq("user_id", user.id).execute()
                
                try:
                    supabase.table("uno_logs").insert({
                        "sender_name": user.first_name,
                        "victim_name": victim["first_name"],
                        "game_date": str(today),
                        "multiplier": total_day_gained,
                        "is_krasavchik": True
                    }).execute()
                except Exception:
                    pass

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ <b>КОРОЛЕВСКОЕ ОГРАБЛЕНИЕ ПРОВАЛЕНО!</b> ❌\n\n"
                         f"Королевская защита Красавчика оказалась непробиваемой. Карта UNO рассыпалась в прах!\n\n"
                         f"<b>{safe_name}</b>, за покушение на Корону твой утренний позор удваивается: получай <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>!\n"
                         f"⏳ А за наглость шериф изымает карту UNO на <b>12 ДНЕЙ ПЕРЕЗАРЯДКИ</b>! 🤡💣",
                    parse_mode="HTML"
                )
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
                return
                
            elif is_coin_loser_target:
                # Жесткое х3 наказание за провал добивания раненого (Вес 150.0)
                supabase.table("users").update({
                    "last_switch_date": str(today), 
                    "pidor_count": fresh_pidor_count + added_penalty,
                    "pidor_weight": 150.0
                }).eq("user_id", user.id).execute()
                
                try:
                    supabase.table("uno_logs").insert({
                        "sender_name": user.first_name,
                        "victim_name": victim["first_name"],
                        "game_date": str(today),
                        "multiplier": total_day_gained,
                        "is_krasavchik": False
                    }).execute()
                except Exception:
                    pass

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ <b>ТОТАЛЬНОЕ КАРМИЧЕСКОЕ ПРАВОСУДИЕ!</b> ❌\n\n"
                         f"Карта UNO расплавилась в руках <b>{safe_name}</b> при попытке добить раненого! Шанс был 45%, но ты {umudrilsya_text} промазать!\n\n"
                         f"Боги рандома {nakazali_text} в тройном размере: твой утренний позор умножается на 3! Получай ещё <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>! Штрафной вес взлетает до 150.0! 🤡💥💣",
                    parse_mode="HTML"
                )
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
                return

            else:
                if is_retry_attempt:
                    # Вторая попытка провалилась — сжигаем карту с х2 штрафом от утра
                    supabase.table("users").update({
                        "last_switch_date": str(today), 
                        "pidor_count": fresh_pidor_count + added_penalty,
                        "pidor_weight": 95.0
                    }).eq("user_id", user.id).execute()
                    context.user_data.pop("switch_retry", None)

                    # Динамический титул Стрелочника / Стрелочницы
                    streloch_title = g_text(player, "СТРЕЛОЧНИК", "СТРЕЛОЧНИЦА")

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"💀 <b>ПОЛНОЕ ФИАСКО, {streloch_title}!</b> Второй шанс тоже провален! 💀\n\n"
                             f"Твоя карта UNO превратилась в пепел. Твой сегодняшний позор удваивается: получай ещё <b>+{added_penalty} пидора</b> <i>(всего {total_day_gained} за сегодня)</i>. Кулдаун 6 дней взведён! 🤡",
                        parse_mode="HTML"
                    )
                    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERg9tqT2Lb7EssiCPdH7XeEz1W5sbVswAC6S8AApkAAYhJDcx-Vp6-Sco8BA')
                else:
                    # Первый провал на мирного — крутим скрытые 5% на "Второй Шанс"
                    has_second_chance = random.randint(1, 100) <= 5
                    
                    if has_second_chance:
                        context.user_data["switch_retry"] = True 
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"⚡️ <b>ОПА, ОСЕЧКА... ИЛИ НЕТ?!</b> ⚡️\n\n"
                                 f"<b>{safe_name}</b>, твоя карта UNO задымилась, но боги рандома дали тебе <b>ВТОРОЙ ШАНС</b>! Шанс перевода всё ещё 30%!\n"
                                 f"Кулдаун НЕ активирован! Быстро пиши команду <code>/switch</code> ещё раз, пока лазейка не закрылась! 🃏",
                            parse_mode="HTML"
                        )
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERg85qT110qgTm1RJWyqRuKm0QwbCoLwAC9B4AAiNcOEtYh2FNKYLHdDwE')
                    else:
                        # Стандартный провал на мирного с первого раза с честным х2
                        supabase.table("users").update({
                            "last_switch_date": str(today), 
                            "pidor_count": fresh_pidor_count + added_penalty,
                            "pidor_weight": 100.0
                        }).eq("user_id", user.id).execute()
                        
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ <b>КАРТА UNO ПОРВАЛАСЬ!</b> ❌\n\n"
                                 f"Перевод сорвался и отрикошетил обратно в <b>{safe_name}</b>. "
                                 f"Твой сегодняшний позор честно удваивается: лови ещё <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>! Карта уходит на КД 6 дней! 🤡",
                            parse_mode="HTML"
                        )
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')

        except Exception as e:
            print(f"Ошибка вывода провала UNO: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text="🔧 <b>Сука, опять вы всё сломали!</b> 🤦‍♂️\n\nПровал карты UNO застрял в текстурах. База всё записала, честное кратное наказание выдано, админ чинит!",
                parse_mode="HTML"
            )
            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERv_1qh-RMBre9eek9ykdsovu3gf-SvwACCnUAAlgXsEkCKvJjaqw9iT0E')

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()
    
    # 1. Вытаскиваем ВСЕХ пользователей для расчета общей суммы весов
    all_users = get_users()
    active_users = [u for u in all_users if u.get("is_active", True)]
    
    # Ищем среди них конкретно нашего игрока
    player = next((u for u in active_users if u["user_id"] == user.id), None)
    
    if not player:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перевели стартовый отлуп на HTML и безопасный send_message
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ <b>Тебя еще нет в игре!</b> Напиши /register",
            parse_mode="HTML"
        )
        return

    # 2. РАССЧИТЫВАЕМ ПРОЦЕНТЫ ШАНСОВ НА ТЕКУЩИЙ МОМЕНТ (Как в /procents)
    total_pidor_weight = sum(u.get("pidor_weight", 100.0) for u in active_users)
    total_kras_weight = sum(u.get("kras_weight", 100.0) for u in active_users)
    
    # Считаем чистый процент (защита от деления на ноль)
    pidor_chance = (player.get("pidor_weight", 100.0) / total_pidor_weight * 100) if total_pidor_weight > 0 else 0.0
    kras_chance = (player.get("kras_weight", 100.0) / total_kras_weight * 100) if total_kras_weight > 0 else 0.0

    # 3. Проверяем статус КД карты UNO
    uno_status = "🟢 ГОТОВА К БОЮ!"
    if player.get("last_switch_date"):
        last_date = date.fromisoformat(player["last_switch_date"])
        days_passed = (today - last_date).days
        if days_passed < 6:
            days_left = 6 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            uno_status = f"🔴 НА ПЕРЕЗАРЯДКЕ (еще {days_left} {day_word})"

    # === 🎭 3.5 Проверяем статус КД МИМИКРИИ (14 ДНЕЙ) ===
    mimic_status = "🟢 ГОТОВА!"
    if player.get("last_mimic_date"):
        last_m_db = player["last_mimic_date"]
        # Умный парсинг даты из Supabase (если пришла строкой — переведем, если датой — оставим)
        last_m_date = date.fromisoformat(last_m_db) if isinstance(last_m_db, str) else last_m_db
        m_days_passed = (today - last_m_date).days
        if m_days_passed < 14:
            m_days_left = 14 - m_days_passed
            m_day_word = "день" if m_days_left == 1 else ("дня" if m_days_left in [2, 3, 4] else "дней")
            mimic_status = f"🔴 НА ПЕРЕЗАРЯДКЕ (еще {m_days_left} {m_day_word})"

    # 4. Рассчитываем еженедельный остаток кармических кубиков (Лимит 2)
    current_week_num = today.isocalendar()[1]
    db_dice_value = player.get("dice_count", 0)
    last_dice_week = db_dice_value // 10
    current_attempts = db_dice_value % 10
    
    if current_week_num != last_dice_week:
        current_attempts = 0
        
    dice_left = 2 - current_attempts
    dice_status = "🔴 ИСЧЕРПАНЫ (0 из 2 на этой неделе)" if dice_left == 0 else f"🟢 ДОСТУПНО: {dice_left} из 2 на этой неделе"

    # Рассчитываем еженедельный остаток патронов для дуэлей
    db_duel_value = player.get("duel_count", 0)
    last_duel_week = db_duel_value // 100
    current_duel_attempts = db_duel_value % 100
    
    if current_week_num != last_duel_week:
        current_duel_attempts = 0
        
    duel_bullets_left = 6 - current_duel_attempts
    duel_bullet_status = f"🟢 ДОСТУПНО: {duel_bullets_left} из 6 выстрелов" if duel_bullets_left > 0 else "🔴 ОБОЙМА ПУСТА (0 из 6)"

    # Вытаскиваем дуэльные очки из карточки игрока (дефолт 0, если пусто)
    d_wins = player.get("duel_wins", 0) if player.get("duel_wins") is not None else 0
    d_losses = player.get("duel_losses", 0) if player.get("duel_losses") is not None else 0
    d_total = d_wins + d_losses
    
    max_k_streak = player.get("max_kras_win_streak", 0) or 0
    max_p_streak = player.get("max_pidor_win_streak", 0) or 0
    
    # === 🃏 УМНЫЙ ПОДГРУЗ СТАТИСТИКИ ИЗ ТАБЛИЦЫ ЛОГОВ UNO ===
    # Считаем, сколько раз имя этого игрока записано вsender_name (его успешные переводы)
    uno_wins_res = supabase.table("uno_logs").select("id").eq("sender_name", player["first_name"]).execute()
    uno_wins_total = len(uno_wins_res.data) if uno_wins_res.data else 0
    
    # Экранируем имена, чтобы спецсимволы в никах не ломали разметку Телеграма
    safe_first_name = player['first_name'].replace("<", "&lt;").replace(">", "&gt;")
    username = f" (@{player['username']})" if player['username'] else ""
    
    # Прокачиваем гендерные статусы для карточки досье
    status_title = g_text(player, "Суровый Ковбой", "Прекрасная Леди")
    kras_record_title = g_text(player, "Красавчика", "Красавицы")
    pidor_record_title = g_text(player, "Пидора", "Пидорессы")

    # 5. Собираем ультимативное досье (СТРОГО НА HTML-ТЕГАХ С УЧЁТОМ АРХИВА UNO И ГЕНДЕРА)
    message = (
        f"👤 <b>ЛИЧНОЕ ДОСЬЕ ИГРОКА</b>:\n\n"
        f"Статус: <b>{status_title}</b>\n"
        f"Участник: <b>{safe_first_name}{username}</b>\n"
        f"🤡 Статус Пидора: <b>{player['pidor_count']}</b> раз(а)\n"
        f"😎 Статус Красавчика: <b>{player['kras_count']}</b> раз(а)\n"
        f"⚔️ Лига Дуэлей: <b>{d_total}</b> боёв <i>({d_wins} В / {d_losses} П)</i>\n"
        f"🃏 Спецоперации UNO: <b>{uno_wins_total}</b> усп. перевод(ов)\n\n"
        f"📊 <b>ТЕКУЩИЕ ШАНСЫ</b>:\n"
        f" └ 🤡 Стать Пидором: <code>{pidor_chance:.1f}%</code> \n"
        f" └ 😎 Стать Красавчиком: <code>{kras_chance:.1f}%</code> \n\n"
        f"📈 Рекорд {kras_record_title} подряд: {max_k_streak} дн.\n"
        f"📉 Рекорд {pidor_record_title} подряд: {max_p_streak} дн.\n\n"
        f"🃏 <b>Карта UNO:</b> {uno_status}\n"
        f"🎭 <b>Карта Мимик:</b> {mimic_status}\n"
        f"🎲 <b>Кубики судьбы:</b> {dice_status}\n"
        f"🔫 <b>Патроны дуэлей:</b> {duel_bullet_status}"
    )

    try:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Прямой send_message по chat_id на HTML-парсер
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка вывода досье mystats: {e}")

async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()
    
    # Получаем чистый номер текущей недели в году
    current_week_num = today.isocalendar()[1]

    # 1. Вытаскиваем данные игрока из Supabase
    res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not res.data:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Убрали reply_text во избежание крашей
        await context.bot.send_message(
            chat_id=chat_id,
            text="❌ <b>Куда кубики бросаешь?</b> Тебя нет в игре! Напиши /register",
            parse_mode="HTML"
        )
        return
        
    player = res.data[0]
    
    # Защита: ливнувшие не играют
    if not player.get("is_active", True):
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Убрали reply_text во избежание крашей
        await context.bot.send_message(
            chat_id=chat_id,
            text="🚪 <b>Ты ливнул из рулетки.</b> Сначала вернись через /register!",
            parse_mode="HTML"
        )
        return

    # 2. МАТЕМАТИЧЕСКИЙ РАСЧЕТ ЕЖЕНЕДЕЛЬНОГО ЛИМИТА
    db_dice_value = player.get("dice_count", 0)
    
    last_dice_week = db_dice_value // 10       
    current_attempts = db_dice_value % 10      

    # Если наступила новая неделя — сбрасываем попытки на лету!
    if current_week_num != last_dice_week:
        current_attempts = 0
        
    if current_attempts >= 2:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перевели отлуп лимита кубиков на HTML и безопасный send_message по chat_id
        await context.bot.send_message(
            chat_id=chat_id,
            text="🛑 <b>Хватит испытывать судьбу!</b> Твой лимит (2 раза в НЕДЕЛЮ) исчерпан. Крупье убирает кубики до следующего понедельника! 🎲",
            parse_mode="HTML"
        )
        return

    # -----------------------------------------------------------------
    # Словарь твоих проверенных Telegram ID стикеров для каждой грани
    DICE_VISUAL_POOL = {
        1: 'CAACAgIAAxkBAAERk_5qX21KuAjAdNoYVo7juR7StF-tdwACYm4AAp7OCwABPf4vNIQDD-09BA',
        2: 'CAACAgIAAxkBAAERlAABal9tVSZA9B_9CaJTUQ0DV-ONxFEAAgdzAAKezgsAAR07kgHWZQ9OPQQ',
        3: 'CAACAgEAAxkBAAERlAZqX22qau2-25EdNSCSc-J86MItZgACPggAAuN4BAAB0kf4L4OeGK09BA',
        4: 'CAACAgEAAxkBAAERlAJqX21iw7fuqnVuXVVmNrkOf3UBywACPwgAAuN4BAABz9rP-UMjaHs9BA',
        5: 'CAACAgEAAxkBAAERlAhqX22_wWbFXZmLN564Ld9p9zVopgACQAgAAuN4BAABu_X0236xZro9BA',
        6: 'CAACAgEAAxkBAAERlARqX21v6CNHbfVaerJZxz16xn_WgQACQQgAAuN4BAABiZOUd1ZcghM9BA'
    }
    # -----------------------------------------------------------------

    # 3. БРОСАЕМ КАРМИЧЕСКИЙ КУБИК
    dice_value = random.randint(1, 6)
    
    await context.bot.send_sticker(chat_id=chat_id, sticker=DICE_VISUAL_POOL[dice_value])
    await asyncio.sleep(3) 

    # Считаем попытки и кодируем пак для базы
    new_attempts = current_attempts + 1
    remains = 2 - new_attempts
    
    # Перевели текст остатка бросков под будущий HTML-формат
    remains_text = f" Осталось бросков на этой неделе: <b>{remains}</b>." if remains > 0 else " Это был твой <b>последний</b> бросок на этой неделе!"
    new_db_value = (current_week_num * 10) + new_attempts
    # === 🧮 РАССЧИТЫВАЕМ ПРОГРЕССИВНЫЕ ВЕСА И ДИНАМИКУ ПРОЦЕНТОВ ===
    safe_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")
    
    # Извлекаем баланс первого броска для детекции дублей
    prev_balance = player.get("dice_start_balance", 0.0) if player.get("dice_start_balance") is not None else 0.0

    # 📊 МАТЕМАТИКА 1: Считаем СТАРЫЕ проценты ДО броска кубика
    all_users_before = get_users()
    active_users_before = [u for u in all_users_before if u.get("is_active", True)]
    
    total_p_before = sum(u.get("pidor_weight", 100.0) for u in active_users_before)
    total_k_before = sum(u.get("kras_weight", 100.0) for u in active_users_before)
    
    old_p_chance = (player.get("pidor_weight", 100.0) / total_p_before * 100) if total_p_before > 0 else 0.0
    old_k_chance = (player.get("kras_weight", 100.0) / total_k_before * 100) if total_k_before > 0 else 0.0

    # Разветвление весов
    if dice_value <= 3:
        # ======= 🤡 ВЕТКА ПОЗОРА (1, 2, 3) =======
        step = 3.0 if dice_value == 3 else (7.0 if dice_value == 2 else 12.0)
        k_minus = 1.0 if dice_value == 3 else (4.0 if dice_value == 2 else 7.0)
        
        new_pidor_weight = player["pidor_weight"] + step
        new_kras_weight = max(1.0, player["kras_weight"] - k_minus)
        
        current_dice_gain = -4.0 if dice_value == 3 else (-11.0 if dice_value == 2 else -19.0)
        saved_balance = current_dice_gain if current_attempts == 0 else prev_balance

        supabase.table("users").update({
            "pidor_weight": new_pidor_weight,
            "kras_weight": new_kras_weight,
            "dice_count": new_db_value,
            "dice_start_balance": saved_balance
        }).eq("user_id", user.id).execute()
        
        # Умная кастомизация: для парней проседает шарм, для девчонок — обаяние
        charm_title = g_text(player, "личный шарм заметно просел", "женское обаяние слегка пошатнулось 💔")

        if dice_value == 1:
            power_text = "💥 <b>КРИТИЧЕСКИЙ УДАР ПО СТАВКАМ!</b> 💥 Твоя вероятность забрать позорное клеймо резко увеличилась, а шансы на корону Красавчика крупно скользнули вниз!"
        elif dice_value == 2:
            power_text = f"ощутимый заплыв в сомнительную сторону. Твои риски на Пидора дня увеличились, а {charm_title}."
        else:
            power_text = "микро-осечка за игровым столом. Косметический сдвиг: шансы на Пидора лишь слегка скорректировались вверх."

        intro_text = f"🎲 На кубике выпадает: <b>{dice_value}</b>!\n\n🤡 <b>ФОРТУНА ОТВЕРНУЛАСЬ!</b> <b>{safe_name}</b>, это {power_text}"
            
    else:
        # ======= 😎 ВЕТКА УДАЧИ (4, 5, 6) =======
        step = 3.0 if dice_value == 4 else (7.0 if dice_value == 5 else 12.0)
        p_minus = 1.0 if dice_value == 4 else (4.0 if dice_value == 5 else 7.0)
        
        new_kras_weight = player["kras_weight"] + step
        new_pidor_weight = max(1.0, player["pidor_weight"] - p_minus)
        
        current_dice_gain = 4.0 if dice_value == 4 else (11.0 if dice_value == 5 else 19.0)
        saved_balance = current_dice_gain if current_attempts == 0 else prev_balance

        supabase.table("users").update({
            "kras_weight": new_kras_weight,
            "pidor_weight": new_pidor_weight,
            "dice_count": new_db_value,
            "dice_start_balance": saved_balance
        }).eq("user_id", user.id).execute()
        
        # Умная кастомизация: для парней прибывает шарм, для девчонок — обаяние (на основе player)
        charm_gain = g_text(player, "мощный прилив шарма", "мощный прилив обаяния ✨")
        pobeda_word = g_text(player, "на победу", "на корону Красавицы")

        if dice_value == 6:
            power_text = "👑 <b>АБСОЛЮТНЫЙ ДЖЕКПОТ КАЗИНО!</b> 👑 Твои показатели привлекательности за столом засияли максимальным блеском, а позорные риски рулетки неплохо так снизились!"
        elif dice_value == 5:
            power_text = f"{charm_gain}! Проценты {pobeda_word} уверенно поползли вверх, а вероятность поймать позорное клеймо тает на глазах."
        else:
            power_text = "скромный шаг к успеху за игровым столом. Чуть-чуть подбавил уверенности в стату, риски позора символически снижены."

        intro_text = f"🎲 На кубике выпадает: <b>{dice_value}</b>!\n\n😎 <b>ФОРТУНА УЛЫБАЕТСЯ ТЕБЕ!</b> <b>{safe_name}</b>, это {power_text}"

    # 📊 МАТЕМАТИКА 2: [ЖЕЛЕЗНО ОПТИМИЗИРОВАНО] Пересчитываем новые проценты в памяти без повторного запроса к базе!
    if dice_value <= 3:
        # Ветка позора: сумма пидоров чата выросла на step, а красавчиков упала на k_minus
        total_p_after = total_p_before + step
        total_k_after = max(1.0, total_k_before - k_minus)
    else:
        # Ветка удачи: сумма красавчиков чата выросла на step, а пидоров упала на p_minus
        total_k_after = total_k_before + step
        total_p_after = max(1.0, total_p_before - p_minus)
    
    # Считаем точные новые проценты игрока на основе его свежих весов, сохраненных в ветках выше
    new_p_chance = (new_pidor_weight / total_p_after * 100) if total_p_after > 0 else 0.0
    new_k_chance = (new_kras_weight / total_k_after * 100) if total_k_after > 0 else 0.0

    # --- 🚨 ПЕРЕХВАТ ДУБЛЕЙ (С НОВЫМИ ПРОЦЕНТАМИ И ГЕНДЕРАМИ ВНУТРИ) ---
    if current_attempts == 1 and prev_balance == -19.0 and dice_value == 1:
        # Собираем динамические гендерные слова для дубля (на основе player)
        status_title = g_text(player, "Игрок", "Леди")
        vjsh_text = g_text(player, "умудряется выбить", "умудряется выбросить")
        bro_text = g_text(player, "бро", "леди")
        ego_text = g_text(player, "твоему авторитету", "твоим ставкам")

        result_text = (
            f"🎲 На кубике выпадает: <b>1</b> (Дубль!)\n\n"
            f"🚨 <b>ЧЁРНЫЙ ДЕНЬ ДЛЯ СТАВОК! ПРОБИТИЕ МАТЕМАТИЧЕСКОГО ДНА!</b> 🎪\n\n"
            f"{status_title} <b>{safe_name}</b> {vjsh_text} дубль <b>1 и 1</b> за неделю! 😭\n"
            f"Да уж, соболезнуем {ego_text}, {bro_text}! Крупье за игровым столом вытирает слёзы жалости.\n\n"
            f"📊 <b>ДИНАМИКА ТВОИХ ШАНСОВ:</b>\n"
            f" └ 🤡 Шанс Пидора: <code>{old_p_chance:.1f}%</code> ➡️ <b>{new_p_chance:.1f}%</b> 📈\n"
            f" └ 😎 Шанс Красавчика: <code>{old_k_chance:.1f}%</code> ➡️ <b>{new_k_chance:.1f}%</b> 📉\n\n"
            f"{remains_text}"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')

    elif current_attempts == 1 and prev_balance == 19.0 and dice_value == 6:
        # Собираем динамические гендерные титулы и фразы для везунчика (на основе player)
        status_title = g_text(player, "Игрок", "Леди")
        vybros_text = g_text(player, "выбрасывает", "выбрасывает ✨")
        style_title = g_text(player, "наглый любимчик фортуны", "настоящая икона стиля 💎")

        result_text = (
            f"🎲 На кубике выпадает: <b>6</b> (Дубль!)\n\n"
            f"🎰 <b>ОБНАРУЖЕН ЧИТЕР! ВЫ С КЕМ ТАМ НАВЕРХУ ДОГОВОРИЛИСЬ?!</b> 👑\n\n"
            f"{status_title} <b>{safe_name}</b> {vybros_text} дубль <b>6 и 6</b> за неделю! 🤯\n"
            f"Администрация казино официально заявляет: этот игровой стол поддался от такой наглой удачи, ты — {style_title}!\n\n"
            f"📊 <b>ДИНАМИКА ТВОИХ ШАНСОВ:</b>\n"
            f" └ 🤡 Шанс Пидора: <code>{old_p_chance:.1f}%</code> ➡️ <b>{new_p_chance:.1f}%</b> 📉\n"
            f" └ 😎 Шанс Красавчика: <code>{old_k_chance:.1f}%</code> ➡️ <b>{new_k_chance:.1f}%</b> 📈\n\n"
            f"{remains_text}"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERfwtqSi0WKXA0-slyXjuDMUAC14PGkAAC6BMAAp7K8UkQAAGdV1VM7UI8BA')

    else:
        # СТАНДАРТНЫЙ ВЫВОД С ДИНАМИЧЕСКИМ СРАВНЕНИЕМ ПРОЦЕНТОВ
        result_text = (
            f"{intro_text}\n\n"
            f"📊 <b>ДИНАМИКА ТВОИХ ШАНСОВ:</b>\n"
            f" └ 🤡 Шанс Пидора: <code>{old_p_chance:.1f}%</code> ➡️ <b>{new_p_chance:.1f}%</b>\n"
            f" └ 😎 Шанс Красавчика: <code>{old_k_chance:.1f}%</code> ➡️ <b>{new_k_chance:.1f}%</b>\n\n"
            f"{remains_text}"
        )

    # === 🛡️ ФИНАЛЬНЫЙ ПУЛЕНЕПРОБИВАЕМЫЙ ВЫВОД В ЧАТ ПО CHAT_ID ===
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=result_text,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка вывода результатов кубиков dice: {e}")
    # =================================================================
    # 🎰 ПОДВЕДЕНИЕ ТОЧНЫХ СУММАРНЫХ ИТОГОВ НЕДЕЛИ (СТРОГО НА 2-Й БРОСОК)
    # =================================================================
    if remains == 0:
        await asyncio.sleep(2) # Оптимизировали паузу до 2 секунд для ускорения функции
        
        # Вытаскиваем из базы финальные веса ПОСЛЕ второго броска
        fresh_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
        if fresh_res.data:
            fresh_player = fresh_res.data[0]
            
            # Узнаем вес ВТОРОГО кубика (вычитаем из новых весов старые)
            second_dice_gain = (fresh_player["kras_weight"] - fresh_player["pidor_weight"]) - (player["kras_weight"] - player["pidor_weight"])
            # Берем из базы чистый вес ПЕРВОГО кубика
            first_dice_gain = fresh_player.get("dice_start_balance", 0.0)
            
            # Чистый профит — это строго сумма весов двух кубиков!
            total_net_gain = first_dice_gain + second_dice_gain
            
            # ПРОВЕРКА: Если это БЫЛ ультра-дубль (1-1 или 6-6), скипаем банальные итоги, чтобы не спамить чат!
            is_absolute_jackpot = (first_dice_gain == 19.0 and dice_value == 6)
            is_absolute_fiasco = (first_dice_gain == -19.0 and dice_value == 1)
            
            if not is_absolute_jackpot and not is_absolute_fiasco:
                try:
                    if total_net_gain > 0:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="📈 <b>ИТОГ СЕССИИ: ЧИСТЫЙ СТОНКС!</b>\nПо результатам двух бросков твоя карма ушла в уверенный плюс. Проценты крутости на высоте! 😎",
                            parse_mode="HTML"
                        )
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERlJpqX8w3FNDgCPWSvVnsuCCj4FRCgwACTkkAAqsfMUmHRIhIKo8OmT0E')
                    elif total_net_gain < 0:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="📉 <b>ИТОГ СЕССИИ: NOT STONKS...</b>\nПо итогам двух бросков карма утянула тебя вниз, как и твои проценты. Риск на позор повышен! 🤡",
                            parse_mode="HTML"
                        )
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERlJxqX8yRTjidyacJymAE9dpIfo2cxAAC0wEAAsVnCAABVsYsrVbM7hg9BA')
                    else:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text="⚖️ <b>ИТОГ СЕССИИ: ИДЕАЛЬНЫЙ БАЛАНС!</b>\nТвои еженедельные броски полностью уравновесили друг друга. Карма осталась нетронутой, вселенная в равновесии! 🌌",
                            parse_mode="HTML"
                        )
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERlJ5qX8z9Vf5rs4yCRMFo0Tw2XqOetwACcgADvFR8E62VWTguIRO5PQQ')
                except Exception as e:
                    print(f"Ошибка вывода недельных итогов кубиков: {e}")

async def uno_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Готовим безопасное HTML-имя вызывающего игрока
    safe_sender_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")

    # Вытягиваем из базы ВООБЩЕ ВСЕ логи, где sender_name равен имени этого игрока
    res = supabase.table("uno_logs").select("*").eq("sender_name", user.first_name).order("id", desc=True).execute()
    
    if not res.data or len(res.data) == 0:
        # Собираем динамические гендерные подколы для пустой хроники (на основе player)
        smog_text = g_text(player, "смог успешно перевести карту", "смогла успешно перевести карту 🐍")
        nevezet_text = g_text(player, "чертовски не везёт на переводы, либо ты слишком мирный ковбой", "не везёт на риски, либо ты слишком мирная леди")

        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"🃏 <b>{safe_sender_name}</b>, твоя личная хроника UNO пуста!\n\nТы ещё ни разу в истории чатика не {smog_text}. Либо тебе {nevezet_text}! 😏", 
            parse_mode="HTML"
        )
        return

    # Шапка персонального досье
    header = f"🃏 <b>ЛИЧНАЯ ХРОНИКА СПЕЦОПЕРАЦИЙ: {safe_sender_name.upper()}</b> 🃏\n"
    header += f"<i>Крупье поднял архивные записи казино... Вот твои успешные переводы стрелок за игровым столом:</i>\n\n"
    
    lines = []
    
    for log in res.data:
        # Форматируем дату в красивый вид (12.09)
        try:
            raw_date = date.fromisoformat(log["game_date"])
            formatted_date = raw_date.strftime("%d.%m")
        except Exception:
            formatted_date = log["game_date"]

        # Экранируем имя жертвы
        safe_victim = log["victim_name"].replace("<", "&lt;").replace(">", "&gt;")
        mult = log.get("multiplier", 1)

        # === 🕵️‍♂️ АВТОМАТИЧЕСКИЙ ПРОБИВ ПОЛА ЖЕРТВЫ ИЗ БАЗЫ SUPABASE ===
        # Вытаскиваем гендер жертвы по её имени прямо из таблицы users
        victim_user_res = supabase.table("users").select("gender").eq("first_name", log["victim_name"]).execute()
        
        # Если нашли игрока в базе — берём его реальный пол, если не нашли (вдруг ливнул) — по дефолту boy
        if victim_user_res.data and len(victim_user_res.data) > 0:
            victim_gender = victim_user_res.data[0].get("gender", "boy")
        else:
            victim_gender = "boy"

        # Проверяем, девушка ли Автор лога (/unostats) и девушка ли Жертва
        is_sender_girl = (player.get("gender") == "girl")
        is_victim_girl = (victim_gender == "girl")

        # === 🎰 РАССТАВЛЯЕМ ГЛАГОЛЫ НА ОСНОВЕ ЧЕТЫРЕХ КОМБИНАЦИЙ (М/М, М/Ж, Ж/М, Ж/Ж) ===
        if not is_sender_girl and not is_victim_girl:
            # 👦 ➡️ 👦 (Парень на Парня)
            perevel_action = f"ты перевёл стрелки на <b>{safe_victim}</b>! Жертва ушёл на дно! 🤡"
            tehn_action = f"ты технично перевёл позорный статус на <b>{safe_victim}</b>"
        elif not is_sender_girl and is_victim_girl:
            # 👦 ➡️ 👩 (Парень на Девушку)
            perevel_action = f"ты перевёл стрелки на <b>{safe_victim}</b>! Она ушла на дно от такого наката! 🤡💣"
            tehn_action = f"ты технично перевёл позорный статус на <b>{safe_victim}</b>"
        elif is_sender_girl and not is_victim_girl:
            # 👩 ➡️ 👦 (Девушка на Парня)
            perevel_action = f"ты перевела стрелки на <b>{safe_victim}</b>! Жертва ушёл на дно! 🤡"
            tehn_action = f"ты технично перевела позорный статус на <b>{safe_victim}</b>"
        else:
            # 👩 ➡️ 👩 (Девушка на Девушку)
            perevel_action = f"ты перевела стрелки на <b>{safe_victim}</b>! Она ушла на дно! 🤡🐍"
            tehn_action = f"ты технично перевела позорный статус на <b>{safe_victim}</b>"

        # Собираем остальные кастомные фразы для автора
        ofigel_text = g_text(player, "ты вообще офигел и <b>Украл статус Красавчика дня</b>", "ты проявила дерзость и <b>Забрала статус Красавицы дня</b> 👑")
        ahuel_text = g_text(player, "ты вообще ахуел и умудрился спиздить множитель Красавчика", "ты устроила абсолютный разнос и перехватила джекпот Красавицы")

        # 👑 РАЗВЕТВЛЕНИЕ ТЕКСТА ПО ТИПАМ ГРАБЕЖЕЙ ДЛЯ СТРОКИ АРХИВА
        if log.get("is_krasavchik", False):
            if mult >= 5:
                action_text = f"{ahuel_text} <b>[х{mult}]</b>! Это легендарный раунд! 🤯🚀"
            else:
                action_text = f"{ofigel_text}! Королевский налёт! 💎"
        else:
            if mult > 1:
                action_text = f"{perevel_action} с жёстким множителем позора <b>[х{mult}]</b>! 💣"
            else:
                action_text = f"{tehn_action}. Чистая работа! 💥"

        lines.append(f"📅 <code>{formatted_date}</code> — {action_text}")

    # Финальная сборка и отправка
    final_text = header + "\n".join(lines)
    await context.bot.send_message(chat_id=chat_id, text=final_text, parse_mode="HTML")

# === 🎰 АВТО-РАЗБИВКА НА ЧАСТИ (ЗАЩИТА ОТ ЛИМИТОВ ТЕЛЕГРАМА С ГЕНДЕРОМ) ===
    chunk_size = 30
    try:
        # Собираем сочный динамический финал для подведения итогов в казино (на основе player)
        end_phrase = g_text(player, "каждого твоего подлеца, друг... 😏⚔️", "каждую твою хитрую комбинацию за столом... 😏🔮")

        if len(lines) <= chunk_size:
            full_message = header + "\n".join(lines) + f"\n\n<i>Архивы казино помнят {end_phrase}</i>"
            await context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode="HTML")
        else:
            await context.bot.send_message(chat_id=chat_id, text=header, parse_mode="HTML")
            for chunk_index in range(0, len(lines), chunk_size):
                chunk = lines[chunk_index:chunk_index + chunk_size]
                chunk_message = "\n".join(chunk)
                if chunk_index + chunk_size >= len(lines):
                    chunk_message += f"\n\n<i>Архивы казино помнят {end_phrase}</i>"
                await context.bot.send_message(chat_id=chat_id, text=chunk_message, parse_mode="HTML")
                await asyncio.sleep(0.5)

    except Exception as e:
        print(f"Ошибка вывода личной уно-статистики: {e}")

async def set_gender_boy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    supabase.table("users").update({"gender": "boy"}).eq("user_id", user.id).execute()
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"🤠 <b>{user.first_name}</b>, статус обновлён! Крупье зафиксировал в досье: <b>Суровый Ковбой</b>. Ствол смазан, шпоры звенят!",
        parse_mode="HTML"
    )

async def set_gender_girl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    supabase.table("users").update({"gender": "girl"}).eq("user_id", user.id).execute()
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"💃 <b>{user.first_name}</b>, статус обновлён! Крупье зафиксировал в досье: <b>Прекрасная Леди</b>. Стол заряжен вашим шармом!",
        parse_mode="HTML"
    )

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
    app.add_handler(CommandHandler("mimic", mimic))
    app.add_handler(CommandHandler("procents", procents))
    app.add_handler(CommandHandler("switch", switch))
    app.add_handler(CommandHandler("records", records))
    app.add_handler(CommandHandler("mystats", my_stats))
    app.add_handler(CommandHandler("backup", manual_backup))
    app.add_handler(CommandHandler("dice", dice_command))
    app.add_handler(CommandHandler("duel", duel))
    app.add_handler(CommandHandler("unostats", uno_stats))
    app.add_handler(CommandHandler("boy", set_gender_boy))
    app.add_handler(CommandHandler("girl", set_gender_girl))


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
