print("СТАРТ БОТА")
import os
import random
import asyncio
import json
from datetime import date, datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters, TypeHandler
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

# ---------------- 🪐 [ГЛОБАЛЬНЫЙ МИДЛВАРЬ-ЩИТ СИСТЕМЫ] ----------------
async def global_anti_spam_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from telegram.ext import ApplicationHandlerStop
    
    # 1. Если это скрытое служебное уведомление Телеграма (смена титула, аватарка, права)
    # у него в пакете НЕТ полноценного объекта message. Выжигаем на подлёте!
    if not update.message:
        raise ApplicationHandlerStop()
        
    # 2. Проверяем скрытые сервисные флаги (смена титулов админа часто прилетает без текста как pinned или системный фид)
    if update.message.pinned_message or update.message.new_chat_members or update.message.left_chat_member:
        raise ApplicationHandlerStop()

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


def save_daily_winner(role, user_id, multiplier=1):
    today_str = str(date.today())
    
    # Принудительно страхуемся от дробных чисел Питона
    clean_user_id = int(user_id)
    clean_multiplier = int(multiplier)
    
    try:
        # План А: Пробуем записать со всеми наворотами и множителем
        supabase.table("daily_winners").insert({
            "game_date": today_str,
            "role": role,
            "user_id": clean_user_id,
            "multiplier": clean_multiplier
        }).execute()
        print(f"🎰 [БАЗА]: Успешно записан победитель {role} с множителем {clean_multiplier}")
    except Exception as e1:
        print(f"⚠️ План А не прошёл (возможно, нет колонки multiplier): {e1}")
        try:
            # План Б (Аварийный): Пишем по старой классической схеме без multiplier!
            supabase.table("daily_winners").insert({
                "game_date": today_str,
                "role": role,
                "user_id": clean_user_id
            }).execute()
            print(f"🎰 [БАЗА]: Сработал аварийный План Б! Победитель {role} зафиксирован.")
        except Exception as e2:
            print(f"❌ ПОЛНЫЙ ОТКАЗ БАЗЫ ДАННЫХ SUPABASE: {e2}")

def safe_parse_date(db_value):
    """
    Универсальный сейф-парсер дат Казиныча.
    Защищает от капризов типов данных Supabase (str, date, datetime).
    """
    if not db_value:
        return None
    if isinstance(db_value, str):
        # Если пришла строка — безопасно парсим её, отсекая время, если оно прилипло
        return date.fromisoformat(db_value.split("T")[0])
    if hasattr(db_value, "date"):
        # If это объект datetime — выдёргиваем чистую дату
        return db_value.date()
    return db_value # Если это уже объект date — отдаём как есть


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
    chat_id = update.effective_chat.id
    
    help_text = (
        "🎰 <b>ДОБРО ПОЖАЛОВАТЬ В ИГРОВОЙ ЗАЛ КАЗИНО!</b> 🎰\n"
        "<i>Крупье приветствует участников за столом. Текущие протоколы:</i>\n\n"

        "👑 <b>УТРЕННИЕ РУЛЕТКИ (Старт каждый день)</b>\n"
        " ├ <code>/pidor</code> — Найти Пидора дня 🤡\n"
        " ├ <code>/run</code> — Найти Красавчика дня 😎\n"
        " ├ <code>/stats</code> — Посмотреть общую статистику побед 📊\n"
        " ├ <code>/procents</code> — Узнать свои шансы на победу 🎯\n"
        " └ <code>/records</code> — Узнать лидеров чата 👀\n\n"

        "⚔️ <b>ЛИГА ДУЭЛЕЙ И АЗАРТНЫЙ РАНДОМ</b>\n"
        " ├ <code>/duel @username</code> — Устроить перестрелку в обойме на 6 патронов за игровой стол 🔫\n"
        " └ <code>/dice</code> — Кинуть кубик кармы (2 в неделю), но надо быть осторожным, возможны аномальные колебания процентов 🎲📉\n\n"

        "🃏 <b>ТАКТИЧЕСКИЕ КАРТЫ (Перехват инициативы)</b>\n"
        " ├ <code>/switch @username</code> — Использовать карту UNO и перевести от себя пидора (КД 6 дней) 🃏⚡️\n"
        " ├ <code>/mimic @username</code> — Mimic-протокол: мимикрировать под другого игрока с удвоением статуса (КД 14 дней) 🎭\n"
        " ├ <code>/mystats</code> — Узнать свою личную статистику и карту UNO 📊\n"
        " └ <code>/unostats</code> — Узнать свои архивные переводы карты UNO 📜\n\n"

        "📢 <b>СТЕНА СУДЕБНОГО ГЛУМЛЕНИЯ (Доступно участникам перевода дня)</b>\n"
        " ├ <code>/notbed</code> — Вальяжно заявить оппоненту: <i>'Я перевёл, сучки, учитесь!'</i> 😎🥂\n"
        " └ <code>/sosamba</code> — Триумфально объявить сосамбу, если чужая карта UNO взорвалась рикошетом 🤡💣\n\n"
        
        "🚪 <b>ВЕРИФИКАЦИЯ И ДВЕРЬ НА ВЫХОД</b>\n"
        " ├ <code>/register</code> — Зарегистрироваться в рулетке и войти в игру 📑\n"
        " ├ <code>/boy</code> — Выбрать статус Ковбоя 👦⚓️\n"
        " ├ <code>/girl</code> — Выбрать статус Леди (чтобы Крупье включил фем-фильтр) 💅🐍\n"
        " ├ <code>/unreg</code> — Выйти из рулетки и удалить данные (нет) 🚪\n"
        " └ <code>/help</code> — Показать это сообщение еще раз (но на кой хер?)\n\n"
        "<i>Все ставки сделаны, фортуна начинает свой ход... 🍸🎰</i>"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=help_text,
        parse_mode="HTML"
    )


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id  #ФИКС БАГА: Объявили переменную!
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
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Запрашиваем профиль игрока из базы
    user_db_res = supabase.table("users").select("is_active", "status_wait").eq("user_id", user.id).execute()
    
    if not user_db_res.data or len(user_db_res.data) == 0:
        await context.bot.send_message(chat_id=chat_id, text="❌ Ты даже не зарегистрирован в казино! Пиши <code>/register</code>", parse_mode="HTML")
        return
        
    user_db = user_db_res.data[0]
    
    # Проверяем, не висит ли уже заявка в нашем НОВОМ столбце
    if user_db.get("status_wait") == "wait":
        await context.bot.send_message(chat_id=chat_id, text="⏳ Твоя заявка на выход уже лежит на столе у Администратора. Ожидай приговора!", parse_mode="HTML")
        return
    elif not user_db.get("is_active", True):
        await context.bot.send_message(chat_id=chat_id, text="🚪 Ты уже покинул игровой зал.", parse_mode="HTML")
        return

    # Включаем режим ожидания лива в НОВОМ столбце, а основной рубильник пока НЕ ТРОГАЕМ!
    supabase.table("users").update({"status_wait": "wait"}).eq("user_id", user.id).execute()

    safe_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🔔 <b>ЗАЯВКА НА ДЕПОРТАЦИЮ ИЗ КАЗИНО!</b> 🔔\n\n"
            f"Игрок <b>{safe_name}</b> пытается в панике покинуть игровой зал и запустить протокол удаления данных!\n"
            f"⚠️ Статус аккаунта переведён в режим ожидания одобрения.\n\n"
            f"👑 <i>Администратор чата должен утвердить или отклонить депортацию командами <code>/ok</code> или <code>/nook</code>!</i>"
        ),
        parse_mode="HTML"
    )

    await update.message.reply_sticker(sticker='CAACAgIAAxkBAAESFSBq2dcIzjAd5J-6HXO_obfg3BhUoQACDhcAAu1KuUpYsB3DvK50BT0E')

async def admin_ok(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    # Мега-фикс: Твоя глобальная админская валидация!
    if user.id != ADMIN_TG_ID:
        await context.bot.send_message(chat_id=chat_id, text="🙅‍♂️ Протокол доступен только Главному Администратору казино!", parse_mode="HTML")
        return

    # Находим пачкой всех бунтарей в новом столбце status_wait
    waiting_users = supabase.table("users").select("user_id", "first_name").eq("status_wait", "wait").execute().data
    
    if not waiting_users:
        await context.bot.send_message(chat_id=chat_id, text="🗄 Список ожидания пуст. Никто не пытается дезертировать.", parse_mode="HTML")
        return

    # Массово отключаем их через оригинальный is_active и зачищаем статус ожидания
    names_list = []
    for u in waiting_users:
        supabase.table("users").update({
            "is_active": False,        # Вот теперь отключаем от утренних рулеток!
            "status_wait": "none"       # Зачищаем заявку
        }).eq("user_id", u["user_id"]).execute()
        names_list.append(f"<b>{u['first_name']}</b>")

    joined_names = ", ".join(names_list)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🚪 <b>ПРОТОКОЛ ДЕПОРТАЦИИ УТВЕРЖДЁН!</b> 👑\n\n"
            f"По решению Администрации чата, следующие беглецы официально лишаются фишек и вышвыриваются за двери заведения:\n"
            f"👉 {joined_names}\n\n"
            f"<i>Данные заморожены, кулдауны запечатаны. Скатертью дорожка! 🤡💥💣</i>"
        ),
        parse_mode="HTML"
    )
    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAESFR5q2dbrfiQ17VRuHt9GA5NE72j8IAACSw4AAo6m-UrpTynx0QZUQT0E')

async def admin_nook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    if user.id != ADMIN_TG_ID:
        await context.bot.send_message(chat_id=chat_id, text="🙅‍♂️ Протокол доступен только Главному Администратору казино!", parse_mode="HTML")
        return

    waiting_users = supabase.table("users").select("user_id", "first_name").eq("status_wait", "wait").execute().data
    
    if not waiting_users:
        await context.bot.send_message(chat_id=chat_id, text="🗄 На столе нет активных заявок на выход.", parse_mode="HTML")
        return

    # Возвращаем всех бунтарей обратно, просто стерев wait в статус none!
    names_list = []
    for u in waiting_users:
        supabase.table("users").update({"status_wait": "none"}).eq("user_id", u["user_id"]).execute()
        names_list.append(f"<b>{u['first_name']}</b>")

    joined_names = ", ".join(names_list)
    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"🛑 <b>В ДЕПОРТАЦИИ ОТКАЗАНО! АЗАРТ ПРОДОЛЖАЕТСЯ!</b> 👑\n\n"
            f"Администрация казино порвала заявления на уход! Следующие игроки возвращаются за игровой стол принудительно:\n"
            f"👉 {joined_names}\n\n"
            f"<i>Куда собрались? Играем до последнего цента! Всем выдать по бокалу напитка за счёт заведения! 🎰🥂🔥</i>"
        ),
        parse_mode="HTML"
    )
    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAESFRxq2dYneDC5RlgjM2dqmtZGCMZ5DgAC6hgAAgbLGEhPQhiCKu75Yz0E')
    
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
    user = update.effective_user  # ЖЕЛЕЗНЫЙ ФИКС: Вытащили профиль нажавшего!
    
    # === 🛡️ ТИТАНОВЫЙ АВТО-ОБНОВИТЕЛЬ ТЕГОВ КАЗИНО: ЗАЩИТА ОТ СМЕНЫ НИКНЕЙМОВ ===
    # Как только игрок жмёт кнопку, база на лету освежает его актуальный тег и имя!
    if user and user.username:
        try:
            supabase.table("users").update({"username": user.username, "first_name": user.first_name}).eq("user_id", user.id).execute()
        except Exception:
            pass
            
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

    # === 🕵️‍♂️ [МЕГА-ФИКС]: ФИКСИРУЕМ СЧЁТ ДО ВСЕХ ОБНОВЛЕНИЙ И МНОЖИТЕЛЕЙ ===
    # Сохраняем чистый счёт игрока до начисления сегодняшних очков
    old_count = winner.get("pidor_count", 0)

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

    # === 🎰 [ФИКС РОМЫ №1]: ЗАПОМИНАЕМ УТРЕННИЙ МНОЖИТЕЛЬ ДЛЯ КАРТЫ UNO ===
    if context.bot_data is None:
        context.bot_data = {}
    context.bot_data["today_pidor_multiplier"] = multiplier
    
    # Рассчитываем итоговую статистику с учётом множителя позора
    new_count = winner["pidor_count"] + multiplier

    # =====================================================================
    # 🚨 [МЕГА-ФИКС РОМЫ + SUPABASE]: СНАЧАЛА ТРАНЗАКЦИЯ, ПОТОМ ПРАЗДНИК! 🚨
    # =====================================================================
    try:
        # 1. Сразу фиксируем начисление позора в профиль игрока
        supabase.table("users").update({"pidor_count": new_count}).eq("user_id", winner["user_id"]).execute()
        
        # 2. Сбрасываем стрик удержания веса победителя обратно в 0
        supabase.table("users").update({"pidor_streak": 0}).eq("user_id", winner["user_id"]).execute()
        
        # 3. Сохраняем победителя в daily_winners и ЖЁСТКО запечатываем МНОЖИТЕЛЬ в базу!
        # Убедись, что добавил колонку multiplier (тип int8) со значением 1 по умолчанию в daily_winners!
        save_daily_winner("pidor", winner["user_id"], multiplier=multiplier)
        
        # 4. Пересчитываем веса под финального победителя
        redistribute_weights(winner["user_id"], "pidor_weight")
    except Exception as db_err:
        print(f"Критическая ошибка сохранения транзакции рулетки /pidor в базу: {db_err}")
        return  # Предохранитель: если база упала, прерываемся и не спамим в чат


    # =====================================================================
    # 🎉 ОФОРМЛЕНИЕ И ВЫВОД В ЧАТ (Полностью защищено от NameError)
    # =====================================================================
    # Полная изоляция никнейма от багов разметки Телеграма (в скобки)
    w_username_display = f" (@{winner['username']})" if winner.get('username') else ""
    safe_winner_name = f"{winner['first_name']}{w_username_display}"

    # Бот подаст голос только в том случае, если МНОЖИТЕЛЬ ПОЗОРА СРАБОТАЛ (х2, х3, х5)
    if is_accumulated_loser and multiplier > 1 and multiplier_text:
        # Собираем динамические гендерные слова для сегодняшней жертвы рулетки
        favorit_title = g_text(winner, "накопленный фаворит клейма", "накопленная фаворитка клейма")
        uderzhival_text = g_text(winner, "удерживал", "удерживала")
        schet_title = g_text(winner, "позорный счёт", "позорный счёт леди")

        try:
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
        except Exception as tg_err:
            print(f"Косметическая ошибка отправки плашки множителя: {tg_err}")


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
        umudryaetsya_text = g_text(winner, "умудряется", "умудрилась")
        gender_pronoun = g_text(winner, "Его проценты сдулись", "Её проценты растаяли")
        legenda_title = g_text(winner, "этого легендарного ковбоя", "эту легендарную леди")

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
        "\n └ 🎯 На проигравшего в монетку — <b>45%</b>"
        "\n\n⚠️ <b>ВНИМАНИЕ:</b> В случае провала промаха активируется кармическая расплата. Рискуй с умом! 😈🎰"
    )

    if final_pidor_user.get("last_switch_date"):
        last_date = safe_parse_date(final_pidor_user.get("last_switch_date"))
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
        
    # Юбилейные шаблоны для Пидора дня (без вызова несуществующих переменных!)
    jokes = {
        10: "🎂 <b>ОГО, 10 РАЗ!</b> {celebrator_name}, поздравляем! Первый юбилей на дне. Давай, расскажи всем, что это просто «случайность»! 🤡",
        20: "👑 <b>УЖЕ 20 ПОБЕД!</b> {celebrator_name} официально переходит в Высшую лигу {parney_title}. Корона из картона готова! 🎪",
        30: "🚨 <b>30-й СТРАЙК!</b> {celebrator_name}, это уже карьера. Ты стабилен как швейцарские часы. {ploh_title} 🛑",
        40: "🗄 <b>КРИЗИС СРЕДНЕГО ВОЗРАСТА!</b> {celebrator_name} отмечает 40 побед! Архив компромата переполнен! 📂",
        50: "🎖 <b>ПОЛУВЕКОВОЙ ЮБИЛЕЙ!</b> 50 раз! {celebrator_name} получает золотую медаль и {bar_title}",
        60: "🎰 <b>МАСТЕР СВОЕГО ДЕЛА!</b> 60 побед у {celebrator_name}! Датчики сомнительных мыслей зашкаливают! ⚡️",
        70: "🚨 <b>КОСМИЧЕСКИЙ УРОВЕНЬ!</b> 70-й раз! {celebrator_name}, {geystvo_title} 🌌",
        80: "🦾 <b>ТИФЛОНОВЫЙ СТАТУС!</b> 80 раз! К {celebrator_name} уже просто ничего не липнет, это абсолютный иммунитет! 🛡",
        90: "🧛‍♂️ <b>ДРЕВНИЙ ОЛДХЭД!</b> 90 побед! {celebrator_name} выходит на финишную прямую к великому залу славы {gaymaster_title}",
        100: "🏆 <b>ЛЕГЕНДА ВЕКА! СТОКРАТНЫЙ ПИДОР!</b> 🎉💥 {celebrator_name} {proshel_title} с обратной стороны! 👑🍾"
    }


    is_anniversary = False
    
    # ЖЕЛЕЗНЫЙ АВТОМАТ: Сравниваем новый счёт со старым (old_count нужно сохранить в самом начале функции, до апдейта в базе!)
    triggered_joke_count = None
    for j_key in jokes.keys():
        if celebrator_count >= j_key and old_count < j_key:
            triggered_joke_count = j_key
            break

    # Проверка на разогрев (5-й раз)
    if celebrator_count >= 5 and old_count < 5:
        kos_text = g_text(winner, "косячит", "рискует за игровым столом")
        masters_text = g_text(winner, "данжн мастеров", "королев драмы")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 <b>РАЗОГРЕВ ОКОНЧЕН!</b> {celebrator_name} {kos_text} уже 5-й раз! Начало положено, но до клуба великих {masters_text} далеко! 🎖",
            parse_mode="HTML"
        )
        is_anniversary = True
        
    elif triggered_joke_count is not None:
        # Считаем гендерные переменные СТРОГО в момент триггера юбилея на основе winner
        parney_title = g_text(winner, "сомнительных парней", "сомнительных леди 💅")
        ploh_title = g_text(winner, "Стабильно плох!", "Стабильно плоха! 💅")
        bar_title = g_text(winner, "пожизненную путевку в гейбар! 🏅", "пожизненную путевку на мужской стриптиз! 🏅")
        geystvo_title = g_text(winner, "твоё гейство видно даже со спутников наблюдения!", "твой позорный шлейф видно даже из космоса!")
        gaymaster_title = g_text(winner, "ГЕЙмастеров! 🏛", "Королев Драмы! 🏛")
        proshel_title = g_text(winner, "полностью прошёл эту жизнь", "полностью прошла эту жизнь")

        # Достаем текстовый шаблон из словаря по пойманному ключу перешагивания!
        raw_joke = jokes[triggered_joke_count]
        formatted_joke = raw_joke.format(
            celebrator_name=celebrator_name,
            parney_title=parney_title,
            ploh_title=ploh_title,
            bar_title=bar_title,
            geystvo_title=geystvo_title,
            gaymaster_title=gaymaster_title,
            proshel_title=proshel_title
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=formatted_joke,
            parse_mode="HTML"
        )
        is_anniversary = True
         
    if is_anniversary:
        random_sticker = random.choice(pidor_stickers_pool)
        await context.bot.send_sticker(chat_id=chat_id, sticker=random_sticker)

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from datetime import date
    game_today = date.today()

    # === 🛡️ [ЗАКОН КАЗИНО]: ЗАПРЕТ НА КРАСАВЧИКА БЕЗ ПИДОРА ===
    # Проверяем, был ли уже выбран Пидор дня за сегодня
    pidor_already_chosen = get_today_winner("pidor")
    
    if not pidor_already_chosen:
        # 1. Сначала отправляем HTML-текст отказа
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                f"🎰 <b>ОТКАЗ В ДОСТУПЕ ЗА ИГРОВОЙ СТОЛ!</b> 🎰\n\n"
                f"Эй, в казино соблюдаются строгие правила! Колесо Красавчика дня <code>/run</code> заблокировано, "
                f"пока чат не узнает имя своего сегодняшнего <b>Пидора дня</b> через команду <code>/pidor</code>! 🤡💥\n\n"
                f"<i>Сначала разберитесь с позором, а уже потом делите чемпионские кроны! С уважением, Крупье. 🥂</i>"
            ),
            parse_mode="HTML"
        )
        
        # 2. Следом отправляем твой кастомный стикер блокировки
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id, 
            sticker='CAACAgIAAxkBAAER_thqxMc638Oc9rHMYqxBUCmK0T9dDgAC5BgAAi1aSUrLNwihSebbBD0E'
        )
        
        # 3. И только теперь окончательно выходим из функции!
        return

    # === 🛡️ ТИТАНОВЫЙ АВТО-ОБНОВИТЕЛЬ ТЕГОВ КАЗИНО: ЗАЩИТА ОТ СМЕНЫ НИКНЕЙМОВ ===
    # Как только игрок жмёт кнопку /run, база на лету освежает его актуальный тег и имя!
    user = update.effective_user
    if user and user.username:
        try:
            supabase.table("users").update({"username": user.username, "first_name": user.first_name}).eq("user_id", user.id).execute()
        except Exception:
            pass
        
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
                f"Бросаем финальный кубик судьбы... подкидываем монетку (50/50)..."
            ),
            parse_mode="HTML"
        )

        await asyncio.sleep(2.5) # Пауза для нагнетания валидола
        
        # Мгновенный баттл 50/50 между фаворитом и претендентом
        if random.randint(1, 100) <= 50:
            final_winner = favorit
            coin_loser = contender  # 🤡 Проиграл Претендент (кого выбрало "ребро")
            added_bonus_weight = 15.0  # Тихо накидываем утешительный приз под капотом
            
            # Экранируем имена для безопасности HTML-верстки Телеграма
            safe_winner_name = final_winner['first_name'].replace("<", "&lt;").replace(">", "&gt;")
            safe_loser_name = coin_loser['first_name'].replace("<", "&lt;").replace(">", "&gt;")

            protect_text = g_text(final_winner, "свою крутость защищает", "свою крутость защищает")
            loser_title = g_text(coin_loser, "проигравший претендент", "проигравшая леди-претендент 💅")

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🪙 <b>МОНЕТКА ОСТАЕТСЯ НА СТОРОНЕ ПЕРВОГО!</b>\n\n"
                    f"😎 В жестком баттле {protect_text} <b>{safe_winner_name}{favorit_username}</b>! Изначальный фаворит отстоял свой статус!\n"
                    f"🤡 А {loser_title} <b>{safe_loser_name}</b> не вывозит апсет и получает лишь <b>небольшой утешительный приз на завтра</b> за красивую попытку штурма! 🎰"
                ),
                parse_mode="HTML"
            )
        else:
            final_winner = contender
            coin_loser = favorit  # 🤡 Проиграл истинный Фаворит (у кого украли победу)
            added_bonus_weight = 50.0  # Тихо накидываем мощную компенсацию под капотом
            
            # Экранируем имена для безопасности HTML-верстки Телеграма
            safe_winner_name = final_winner['first_name'].replace("<", "&lt;").replace(">", "&gt;")
            safe_loser_name = coin_loser['first_name'].replace("<", "&lt;").replace(">", "&gt;")

            favorit_title = g_text(coin_loser, "рук фаворита", "рук фаворитки")
            obvorovanniy_title = g_text(coin_loser, "обворованный фаворит", "обворованная фаворитка 💅")

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🪙 <b>ОГРАБЛЕНИЕ В ФИНАЛЕ! ОНА ПЕРЕВЕРНУЛАСЬ!</b>\n\n"
                    f"😎 Монетка решает в пользу претендента! <b>{safe_winner_name}{contender_username}</b> вырывает победу из {favorit_title}!\n"
                    f"🤡 Абсолютный облом! {obvorovanniy_title} <b>{safe_loser_name}</b> теряет заслуженную корону на финише, но администрация казино выдаёт ему <b>МОЩНЫЙ БУСТ на завтра</b> в качестве компенсации за дикий нефорт! 🛸🔥"
                ),
                parse_mode="HTML"
            )

        # 💾 СОХРАНЯЕМ НЕУДАЧНИКА В БАЗУ ДАННЫХ SUPABASE
        save_daily_winner("coin_loser", coin_loser["user_id"])
        
        # Вытаскиваем текущий вес неудачника из базы
        loser_base = supabase.table("users").select("kras_weight").eq("user_id", coin_loser["user_id"]).execute().data
        current_kras_weight = loser_base[0]["kras_weight"] if loser_base else 100.0
        
        # Начисляем ДИНАМИЧЕСКИЙ вес втихую (+15.0 или +50.0), игрокам это видеть незачем!
        supabase.table("users").update({"kras_weight": current_kras_weight + added_bonus_weight}).eq("user_id", coin_loser["user_id"]).execute()

    else:
        # ================= ✨ ПУТЬ А: СТАНДАРТНЫЙ ПРОКРУТ (70%) =================
        # Тут тоже отправляем напрямую в чат, чтобы застраховаться от удаления сообщений!
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"😎 Красавчик дня — {final_winner['first_name']}{favorit_username}"
        )

    # === 🕵️‍♂️ [МЕГА-ФИКС]: ФИКСИРУЕМ СЧЁТ ДО ВСЕХ ОБНОВЛЕНИЙ И МНОЖИТЕЛЕЙ ===
    # Вытаскиваем чистый счёт итогового победителя ДО начисления сегодняшних крон!
    old_count = final_winner.get("kras_count", 0)

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

    # =====================================================================
    # 🚨 [МЕГА-ФИКС + SUPABASE]: СНАЧАЛА ТРАНЗАКЦИЯ, ПОТОМ ПРАЗДНИК! 🚨
    # =====================================================================
    try:
        # 1. Сразу фиксируем начисление крон в профиль чемпиона
        supabase.table("users").update({"kras_count": new_count}).eq("user_id", final_winner["user_id"]).execute()
        
        # 2. После победы фаворита сбрасываем его личный стрик макс-шанса обратно в 0
        supabase.table("users").update({"kras_streak": 0}).eq("user_id", final_winner["user_id"]).execute()
        
        # 3. Пересчитываем веса под финального победителя
        redistribute_weights(final_winner["user_id"], "kras_weight")
        
        # 4. Сохраняем победителя в daily_winners и ЖЁСТКО запечатываем МНОЖИТЕЛЬ Красавчика в базу!
        save_daily_winner("krasavchik", final_winner["user_id"], multiplier=multiplier)
    except Exception as db_err:
        print(f"Критическая ошибка сохранения транзакции рулетки /run в базу: {db_err}")
        return  # Предохранитель: если база упала, прерываемся

    # =====================================================================
    # 🎉 КОСМЕТИКА И ОФОРМЛЕНИЕ ЧЕМПИОНА (ПОЛНОСТЬЮ ЗАЩИЩЕНО ОТ NAMEERROR)
    # =====================================================================
    # Защищаем никнейм от багов разметки Телеграма (изолируем в скобки)
    safe_winner_name = f"{final_winner['first_name']}{favorit_username}"

    # Бот подаст голос только в том случае, если МНОЖИТЕЛЬ СРАБОТАЛ (х2, х3, х5)
    if is_accumulated_champion and multiplier > 1 and multiplier_text:
        favorit_title = g_text(final_winner, "накопленный фаворит дня", "накопленная фаворитка дня")
        uderzhival_text = g_text(final_winner, "удерживал", "удерживала")
        schet_title = g_text(final_winner, "Текущие красавчики", "Текущие короны красавицы")

        try:
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
        except Exception as tg_err:
            print(f"Косметическая ошибка отправки плашки множителя Красавчика: {tg_err}")
    
    # === 🏆 УЛЬТРА-ВИНСТРИК КРАСАВЧИКА (БЕЗБАГОВЫЙ СБРОС) ===
    try:
        supabase.table("users").update({"kras_win_streak": 0}).neq("user_id", final_winner["user_id"]).execute()

        current_win_streak = final_winner.get("kras_win_streak", 0) or 0
        new_win_streak = current_win_streak + 1
        supabase.table("users").update({"kras_win_streak": new_win_streak}).eq("user_id", final_winner["user_id"]).execute()

        max_kras_streak = final_winner.get("max_kras_win_streak", 0) or 0
        if new_win_streak > max_kras_streak:
            supabase.table("users").update({"max_kras_win_streak": new_win_streak}).eq("user_id", final_winner["user_id"]).execute()

        if new_win_streak >= 3:
            await asyncio.sleep(1)
            day_word = "дня" if new_win_streak in [3, 4] else "дней"
            kak_on_text = g_text(final_winner, "Да как он это делает?!", "Да как она это делает?! 💅")
            vzlomal_text = g_text(final_winner, "взломал", "взломала")
            lubimchik_title = g_text(final_winner, "Настоящий любимчик фортуны!", "Настоящая любимица фортуны! ✨")

            await context.bot.send_message(
                chat_id=chat_id,
                text=(
                    f"🎰 <b>БОЖЕСТВЕННЫЙ ХЕТ-ТРИК КАЗИНО!</b> 👑\n\n"
                    f"{kak_on_text} <b>{safe_winner_name}</b> умудряется забрать титул Красавчика дня аж <b>{new_win_streak} {day_word} подряд</b>! 🤯\n\n"
                    f"Имея минимальный процент, {g_text(final_winner, 'он', 'она')} всё равно {vzlomal_text} рандом! {lubimchik_title} 🥂"
                ),
                parse_mode="HTML"
            )
    except Exception as streak_err:
        print(f"Ошибка расчета винстриков Красавчика: {streak_err}")

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
        
    # === 🎭 [УМНЫЙ ФИКС РОМЫ]: ФИКСАЦИЯ СГОРЕВШИХ МИМИКОВ ===
    # Если у игрока до сих пор висит цель, но дата last_mimic_date старая (значит, сегодня он НЕ выигрывал)
    # переводим его цель в статус "failed" (сгорела), а не затираем втихую в None!
    try:
        supabase.table("users").update({"mimic_target_id": "failed"}).neq("last_mimic_date", str(game_today)).neq("mimic_target_id", None).execute()
        print("🎭 Все несыгравшие сегодня карты мимикрии официально признаны сгоревшими.")
    except Exception as mimic_clear_err:
        print(f"Ошибка фиксации сгоревших мимиков: {mimic_clear_err}")


    # ---------------- БЛОК ЮБИЛЕЙНЫХ ПОЗДРАВЛЕНИЙ С ИЗДЁВКОЙ ----------------
    kras_stickers_pool = [
        'CAACAgIAAxkBAAERePpqQ3C50Eqg_2plBXsHEFEtGOtmnQACk1QAAgmZ4EkPKsG3ATUGIDwE',
        'CAACAgIAAxkBAAERePxqQ3FkKQTrDt2Kt3E3v09Q90uUzgAC5zMAAvyF0EhRH0ZM6KsQGjwE',
        'CAACAgIAAxkBAAEReP5qQ3GP592jnDm3vTPxPH5LqTK3rgACrhQAAo4n0EqxFZIn-u6dajwE',
        'CAACAgIAAxkBAAEReQABakNxn4mZ1mhxrJf0em63Qj9qEb8AAs4ZAAKJEBBKhq0wFniF8sA8BA',
        'CAACAgIAAxkBAAEReQJqQ3HbH2OkT4mcPqJovAXsFJh5bQAClyAAAt88OUtsjjyKWQ5bXjwE',
        'CAACAgIAAxkBAAEReQRqQ3Ldb-x4CbDRQhozMvG6zY9vqQACagADJeuTHyg3EZuaMZFnPAQ'
    ]

    # Юбилейные шаблоны для Красавчика дня (чистый текст!)
    jokes = {
        10: "👑 <b>ОГО, 10 РАЗ!</b> {celebrator_name}, аккуратнее на поворотах, а то нимб упадёт и ноги отдавит! Чат, расступаемся, тут идёт {miss_mr_title}",
        20: "🎩 <b>20 ПОБЕД!</b> {celebrator_name} так часто выигрывает, что уже целует своё отражение в зеркале по утрам. Завязывай с самолюбованием, нам завидно! 🔥",
        30: "🏆 <b>30-й СТРАЙК!</b> {celebrator_name}, признайся, ты {podkrutil_text} этот код или просто {podkupil_text} бота? Чат требует проверку на коддинг! 🚨",
        40: "✨ <b>40 РАЗ КРАСАВЧИК!</b> Уровень эго {celebrator_name} превысил все допустимые нормы. Скоро тебе понадобится отдельная комната для твоей короны! 🗄",
        50: "🎖 <b>ПОЛУВЕКОВОЙ ЮБИЛЕЙ!</b> 50 побед! {celebrator_name}, мы скидываемся тебе на памятник при жизни в полный рост. Из чистого золота, естественно! 🏅",
        60: "🎰 <b>60 ПОБЕД!</b> {celebrator_name} официально признан {narciss_title} Датчики привлекательности сгорели от такого пафоса! ⚡️",
        70: "🛰 <b>КОСМИЧЕСКИЙ КРАСАВЧИК!</b> 70-й раз! {celebrator_name}, твоё великолепие ослепляет даже спутники наблюдения! Надень маску, побереги наши глаза! 🌌",
        80: "🛡 <b>80 РАЗ! СВЕРХЛЮДИ СРЕДИ НАС!</b> К {celebrator_name} уже выстроилась очередь за автографами. Не забудь упомянуть этот чат, когда поедешь на {mister_vselennaya}",
        90: "🏛 <b>90 ПОБЕД!</b> {celebrator_name} одной ногой в зале славы {pobeditel_title} Ещё чуть-чуть, и твоё лицо напечатают на обложках всех журналов! 🧛‍♂️",
        100: "👑🍾 <b>ЛЕГЕНДА ВЕКА! СТОКРАТНЫЙ КРАСАВЧИК!</b> 🎉💥 {celebrator_name} официально {proshel_game} 100 побед! {boss_title} 🏆🌟"
    }


    is_anniversary = False
    
    # УЛЬТИМАТИВНЫЙ АВТОМАТ ДЛЯ КРОН: Проверяем перешагивание юбилея
    triggered_joke_count = None
    for j_key in jokes.keys():
        if celebrator_count >= j_key and old_count < j_key:
            triggered_joke_count = j_key
            break

    # Проверка на разогрев (5-й раз Красавчика)
    if celebrator_count >= 5 and old_count < 5:
        kras_5_title = g_text(final_winner, "набирает обороты", "сияет на игровом столе ✨")
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎉 <b>РАЗОГРЕВ ОКОНЧЕН!</b> {celebrator_name} {kras_5_title} уже 5-й раз! Начало положено, но до зала великой славы ещё нужно дойти! 🎖",
            parse_mode="HTML"
        )
        is_anniversary = True
        
    elif triggered_joke_count is not None:
        # Считаем гендерные переменные СТРОГО при срабатывании на основе final_winner
        miss_mr_title = g_text(final_winner, "мистер Обаяние! 📸", "мисс Обаяние! ✨📸")
        podkrutil_text = g_text(final_winner, "подкрутил", "подкрутила")
        podkupil_text = g_text(final_winner, "подкупил", "подкупила")
        narciss_title = g_text(final_winner, "главным нарциссом этого чата.", "главной нарцисской этого чата! 💖")
        mister_vselennaya = g_text(final_winner, "Мистер Вселенная! 🦾", "Мисс Вселенная! ✨🦾")
        pobeditel_title = g_text(final_winner, "великих Победителей.", "великих Победительниц. ✨")
        boss_title = g_text(final_winner, "икона стиля и босс этого чата! Салют чемпиону!", "икона стиля и королева этого чата! Салют чемпионке! ✨")
        proshel_game = g_text(final_winner, "полностью прошёл эту игру!", "полностью прошла эту игру! ✨")

        # Наполняем шаблон юбилея Красавчика
        raw_joke = jokes[triggered_joke_count]
        formatted_joke = raw_joke.format(
            celebrator_name=celebrator_name,
            miss_mr_title=miss_mr_title,
            podkrutil_text=podkrutil_text,
            podkupil_text=podkupil_text,
            narciss_title=narciss_title,
            mister_vselennaya=mister_vselennaya,
            pobeditel_title=pobeditel_title,
            proshel_game=proshel_game,
            boss_title=boss_title
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=formatted_joke,
            parse_mode="HTML"
        )
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

async def procents_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    all_users = get_users()
    active_users = [u for u in all_users if u.get("is_active", True)]
    
    if len(active_users) <= 1:
        await context.bot.send_message(chat_id=chat_id, text="Недостаточно игроков за столом.", parse_mode="HTML")
        return

    # Константы Ромы-Монте-Карло для Красавчика
    m = 0.30  
    q = 0.50  

    # Проверяем, кто уже занял титулы сегодня, чтобы исключить их из реальных пулов
    today_pidor = get_today_winner("pidor")
    today_kras = get_today_winner("krasavchik")

    # =====================================================================
    # 🤡 1. ЧЕСТНЫЙ РАСЧЁТ ПИДОРА ДНЯ
    # =====================================================================
    # Исключаем из пула сегодняшнего Красавчика (как в функции pidor())
    opposite_kras_id = today_kras["user_id"] if today_kras else get_opposite_winner_id("pidor")
    filtered_p_users = [u for u in active_users if u["user_id"] != opposite_kras_id]
    if not filtered_p_users:
        filtered_p_users = active_users

    total_p_weight = sum(u.get("pidor_weight", 100.0) for u in filtered_p_users)
    
    pidor_list = []
    for u in active_users:
        safe_name = u["first_name"].replace("<", "&lt;").replace(">", "&gt;")
        username_str = f" (@{u['username']})" if u.get("username") else ""
        display_name = f"{safe_name}{username_str}"

        if today_pidor:
            # Если Пидор дня УЖЕ выбран — у победителя 100%, у остальных 0%
            chance_pct = 100.0 if u["user_id"] == today_pidor["user_id"] else 0.0
        elif u["user_id"] not in [user["user_id"] for user in filtered_p_users]:
            # Если игрока нет в пуле кандидатов рулетки — строго 0%
            chance_pct = 0.0
        else:
            # Честная доля веса в РЕАЛЬНОМ пуле кандидатов
            chance_pct = (u.get("pidor_weight", 100.0) / total_p_weight) * 100
            
        pidor_list.append({"display": display_name, "chance": chance_pct})
    
    # Сортируем от большего к меньшему
    pidor_list = sorted(pidor_list, key=lambda x: x["chance"], reverse=True)

    # =====================================================================
    # 👑 2. ЧЕСТНЫЙ РАСЧЁТ КРАСАВЧИКА ДНЯ
    # =====================================================================
    # Исключаем из пула сегодняшнего Пидора (как в функции run_command())
    opposite_pidor_id = today_pidor["user_id"] if today_pidor else get_opposite_winner_id("krasavchik")
    filtered_k_users = [u for u in active_users if u["user_id"] != opposite_pidor_id]
    if not filtered_k_users:
        filtered_k_users = active_users

    N_kras = len(filtered_k_users)
    total_k_weight = sum(u.get("kras_weight", 100.0) for u in filtered_k_users)

    kras_list = []
    for u in active_users:
        safe_name = u["first_name"].replace("<", "&lt;").replace(">", "&gt;")
        username_str = f" (@{u['username']})" if u.get("username") else ""
        display_name = f"{safe_name}{username_str}"

        if today_kras:
            # Если Красавчик дня УЖЕ выбран — у победителя 100%, у остальных 0%
            chance_pct = 100.0 if u["user_id"] == today_kras["user_id"] else 0.0
        elif u["user_id"] not in [user["user_id"] for user in filtered_k_users]:
            # Если игрок исключён (он сегодняшний Пидор) — строго 0%
            chance_pct = 0.0
        else:
            # Базовая вероятность внутри реального усечённого пула
            p_i = u.get("kras_weight", 100.0) / total_k_weight
            if N_kras > 1:
                # Применяем формулу Ромы-Монте-Карло строго к усечённому знаменателю N_kras!
                real_chance = (1 - m) * p_i + m * (q * p_i + ((1 - p_i) / (N_kras - 1)) * q)
                chance_pct = real_chance * 100
            else:
                chance_pct = p_i * 100
                
        kras_list.append({"name": display_name, "chance": chance_pct})
    
    # Сортируем от большего к меньшему
    kras_list = sorted(kras_list, key=lambda x: x["chance"], reverse=True)

    # =====================================================================
    # 🎯 3. УМНОЕ ДИНАМИЧЕСКОЕ ФОРМИРОВАНИЕ ТЕКСТА ШАПКИ
    # =====================================================================
    # Чекаем, завершён ли полностью сегодняшний день
    if today_pidor and today_kras:
        response = "🏆 <b>ИТОГИ СЕГОДНЯШНИХ РОЗЫГРЫШЕЙ</b> 🏆\n"
        response += "<i>(Все ставки на сегодня сыграли, крупье зафиксировал результаты)</i>\n\n"
    else:
        response = "🎯 <b>ТЕКУЩИЕ ШАНСЫ УЧАСТНИКОВ</b>\n"
        response += "<i>(Коэффициенты рассчитаны с учётом живого пула и переброса монетки)</i>\n\n"
    
    # Вывод Пидора
    response += "🔥 <b>Шансы стать Пидором дня:</b>\n"
    for idx, item in enumerate(pidor_list, 1):
        response += f"{idx}. {item['display']} — <code>{item['chance']:.1f}%</code>\n"

    response += "\n———————————————\n\n"

    # Вывод Красавчика
    response += "👑 <b>Шансы стать Красавчиком дня:</b>\n"
    for idx, item in enumerate(kras_list, 1):
        response += f"{idx}. {item['name']} — <code>{item['chance']:.1f}%</code>\n"

    # Динамический финал-подсказка для лаундж-зоны
    if today_pidor and today_kras:
        response += (
            "\n🎰 <i>Новые коэффициенты на завтрашнее утро загрузятся ровно в полночь (00:00)! "
            "А если хочешь узнать процент на завтра пораньше, пиши <code>/mystats</code>! 🔥🥂</i>"
        )
    else:
        response += "\n🎰 <i>Казино играет честно. Фортуна начинает свой ход... 🍸</i>"

    await context.bot.send_message(chat_id=chat_id, text=response, parse_mode="HTML")

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
        "🥇 <b>АБСОЛЮТНЫЙ ЧЕМПИОН КАЗИНО 🎰</b> 🥇\n\n"
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
    # === 🛡️ ЖЕЛЕЗНЫЙ АНТИ-РЕПЛАЙ ЩИТ КАЗИНО: ЗАЩИТА ОТ ФАНТОМНЫХ ТЕГОВ ===
    if update.message and update.message.text:
        if not update.message.text.strip().startswith("/mimic"):
            return

    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Активировать Мимика можно только в групповых чатах!")
        return

    # === 🚨 [ЗАКОН КАЗИНО]: НЕЛЬЗЯ МИМИКРИРОВАТЬ ПОСЛЕ /pidor ДО /run 🚨 ===
    # 1. Проверяем, выбраны ли сегодняшние победители рулеток
    pidor_today = get_today_winner("pidor")
    kras_today = get_today_winner("krasavchik")

    # 2. Если Пидор УЖЕ откручен, а Красавчик ЕЩЁ НЕ выбран — шпионы идут нахер!
    if pidor_today and not kras_today:
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"🎰 <b>ПРОТОКОЛ МИМИКРИИ ЗАБЛОКИРОВАН!</b> 🎭\n\n"
                f"Эй, лазейка закрыта! Карта Мимикрии настраивается строго <b>ДО начала утренних рулеток</b>!\n"
                f"Чат уже узнал имя своего сегодняшнего Пидора дня, а Колесо Красавчика <code>/run</code> ещё не запущено! "
                f"Казино запрещает подсматривать результаты и включать радары на ходу!\n\n"
                f"<i>Приходите после открута, ну или завтра с утра, шпионы! С уважением, Шериф. 🤠🔫</i>"
            ),
            parse_mode="HTML"
        )
        # Отправляем стикер
        await context.bot.send_sticker(
            chat_id=chat_id, 
            sticker='CAACAgIAAxkBAAESHMBq4YIrKGYudo11XtQ-X2LH-n3yLgACvzcAApy_UErp84UcgOcPmT0E'
        )
        return

    # === 🕵️‍♂️ [ФИКС] ВЫТАСКИВАЕМ МИМИКА ИЗ БАЗЫ ДЛЯ ГЕНДЕРНОГО АВТОМАТА ===
    player_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    player = player_res.data[0] if player_res.data and len(player_res.data) > 0 else {"gender": "boy"}

    if update.effective_chat.type == "private":
        await update.message.reply_text("❌ Активировать Мимика можно только в групповых чатах!")
        return

    # 1. Вытаскиваем данные Стрелочника из базы
    user_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    if not user_res.data:
        await update.message.reply_text("❌ Тебя нет в рулетке! Напиши /register")
        return
    current_user = user_res.data[0]

    # ЖЕЛЕЗНЫЙ ФИКС РОМЫ: Ливнувшие или висящие в wait не имеют права юзать карты!
    if not current_user.get("is_active", True) or current_user.get("status_wait") == "wait":
        await context.bot.send_message(
            chat_id=chat_id, 
            text="🚪 <b>Доступ заблокирован!</b> Ты находишься в процессе депортации или покинул игровой зал. Карты UNO и Мимикрии для тебя недоступны!", 
            parse_mode="HTML"
        )
        return
        
    # 2. ПРОВЕРКА КУЛДАУНА (14 ДНЕЙ) С УМНЫМ ПАРСИНГОМ ТИПА DATE
    if current_user.get("last_mimic_date"):
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Прогоняем через наш универсальный сейф-парсер!
        last_date = safe_parse_date(current_user.get("last_mimic_date"))
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

    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Перевели интригующие фразы мимика на HTML-броню
    for phrase in mimic_phrases:
        await context.bot.send_message(
            chat_id=chat_id, 
            text=phrase, 
            parse_mode="HTML"
        )
        await asyncio.sleep(1.5)

    # Мемный стикер наведения цели
    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERl5RqYy9g5SuIKeL-HYdt9H78f80S9wACGTkAAnsn4UlP1wuYX7Od8j0E')

async def duel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # === 🛡️ ЖЕЛЕЗНЫЙ АНТИ-РЕПЛАЙ ЩИТ КАЗИНО: ЗАЩИТА ОТ ФАНТАНМНЫХ ТЕГОВ ===
    if update.message and update.message.text:
        if not update.message.text.strip().startswith("/duel"):
            return

    user = update.effective_user
    chat_id = update.effective_chat.id

    # === 🛡️ ТИТАНОВЫЙ ГЛОБАЛЬНЫЙ ПРОБИВ ИГРОКА С ТОЧНЫМ ИНДЕКСОМ [0] ===
    player_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    player = player_res.data[0] if player_res.data and len(player_res.data) > 0 else {"gender": "boy"}

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
        prish_text = g_text(player, "ты пришёл в игровую зону", "ты пришла в игровую зону")
        rasstrel_text = g_text(player, "ты уже расстрелял", "ты уже расстреляла")
        pozo_text = g_text(player, "не позорься", "не расстраивайся, подруга! 💅")

        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Полный переход на стиль комфортного казино и HTML-броню
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"💨 <b>Осечка! Обойма пуста...</b>\n\n"
                 f"{safe_shooter_name}, {prish_text} с разряженным пистолетом! Все 6 патронов на этой неделе {rasstrel_text}. 🤦‍♂️\n"
                 f"❌ КРУПЬЕ ЗАКРЫВАЕТ ДОСТУП! Отдохни от азарта за барной стойкой до понедельника и {pozo_text}!",
            parse_mode="HTML"
        )

        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERocZqavV1gUjQriQqP3uLpw6uz9qdAwAChhEAAoC6wEokCKx8CQHogD0E')
        return

    # 2. УЛЬТИМАТИВНЫЙ ПАРСИНГ ЖЕРТВЫ (Твоя схема из карты UNO)
    if not context.args and not update.message.entities:
        await update.message.reply_text("❌ Кого вызываем на дуэль? Тегни цель: `/duel @username` или @ и выбери имя из списка!")
        return

    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Защита от callback_query (инлайн-кнопок), чтобы бот не падал в NoneType
    target_username = None
    target_user_id = None

    if update.message and update.message.entities:
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
        p_title = g_text(player, "Ковбой", "Леди")
        v_title = g_text(victim, "ковбой", "леди")
        
        # Определяем пол участников для выбора стикера и текста
        is_p_girl = (player.get("gender") == "girl")
        is_v_girl = (victim.get("gender") == "girl")

        # Настраиваем текст и подбираем стикер под каждую пару игроков
        if is_p_girl and is_v_girl:
            # 💃 🆚 💃 (Девушка против Девушки)
            shodyatsya_text = "Прекрасные леди"
            # TODO: Сюда вставим твой кастомный стикер для Ж/Ж боёв
            duel_sticker = 'CAACAgIAAxkBAAER50ZqqOZiWVgDQmmArJGbLOYmve4H-AAC36YAApMjSUknNw-DrlBDXz0E' 
        elif not is_p_girl and not is_v_girl:
            # 👦 🆚 👦 (Парень против Парня)
            shodyatsya_text = "Судари"
            # Твой родной стикер дуэли ковбоев
            duel_sticker = 'CAACAgIAAxkBAAERnotqaMvN6_wsk1CPke39HxtwJyuPDwACUhEAArywIErXQg4EzgXGxj0E' 
        else:
            # 👦 🆚 💃 или 💃 🆚 👦 (Смешанный баттл полов)
            shodyatsya_text = "Участники"
            # TODO: Сюда вставим твой кастомный стикер для М/Ж боёв
            duel_sticker = 'CAACAgIAAxkBAAER50hqqOZj7ESY27DpLtaGKkN5zrcRLQAC_J8AAuE9SEmMN6q09r1cVz0E'

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

        # Отправляем точечный стикер под конкретную пару!
        await context.bot.send_sticker(chat_id=chat_id, sticker=duel_sticker)

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
        pobezh_title = g_text(loser, "поражённый оппонент", "поражённая леди ")
        otprav_text = g_text(loser, "отправляется перезаряжать ствол", "отправляется на перезарядку своего дерринджера")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎰 <b>РАУНД ЗАВЕРШЕН! ВСЕ СТАВКИ СЫГРАЛИ!</b> 🎰\n\n"
                 f"🎯 {vystrel_text} главную {vyrval_text} <b>{winner['first_name']}</b>! 👑 <i>(осталось патронов в обойме: {winner_left}/6)</i>\n"
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
    # === 🛡️ ЖЕЛЕЗНЫЙ АНТИ-РЕПЛАЙ ЩИТ КАЗИНО: ЗАЩИТА ОТ ФАНТОМНЫХ ТЕГОВ ===
    if update.message and update.message.text:
        if not update.message.text.strip().startswith("/switch"):
            return # Если сообщение просто содержит тег, но не начинается с команды — тихо игнорируем!

    # === 🕵️‍♂️ [ФИКС] ВЫТАСКИВАЕМ СТРЕЛОЧНИКА ДЛЯ ГЕНДЕРНОГО АВТОМАТА ===
    user = update.effective_user
    player_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    player = player_res.data[0] if player_res.data and len(player_res.data) > 0 else {"gender": "boy"}
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

    # 2. ПРОВЕРКА КУЛДАУНА (Стандартные 6 дней или штрафные 12 дней за кражу короны)
    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Безопасный забор данных из списка player_res.data Питона!
    if player_res.data and len(player_res.data) > 0 and player_res.data[0].get("last_switch_date"): 
        last_date = safe_parse_date(player_res.data[0].get("last_switch_date"))
        days_passed = (today - last_date).days
        
        # Если days_passed меньше 6 (включая отрицательные числа от штрафного сдвига) — КД активен!
        if days_passed < 6:
            days_left = 6 - days_passed
            day_word = "день" if days_left == 1 else ("дня" if days_left in [2, 3, 4] else "дней")
            
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Теперь если days_left больше 6 — это легитимный королевский штраф!
            if days_left > 6:
                promazal_text = g_text(player, "ты позорно промазал", "ты позорно промазала")
                poluchil_text = g_text(player, "получил удвоенное наказание", "получила удвоенное наказание")

                cd_message = (
                    f"❌ <b>Твоя карта UNO заблокирована владельцем казино!</b>\n\n"
                    f"При попытке ограбить Красавчика дня {promazal_text}, поэтому {poluchil_text}.\n"
                    f"Отдохни пока от карт в лаунж-зоне за барной стойкой, доступ вернётся только через <b>{days_left} {day_word}</b>! ⏳🎰"
                )
            else:
                # Обычный стандартный кулдаун на 6 дней
                cd_message = f"❌ Твоя карта UNO всё еще на перезарядке! Доступ появится через <b>{days_left} {day_word}</b>."

            await context.bot.send_message(chat_id=chat_id, text=cd_message, parse_mode="HTML")
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

    # Инициализируем переменную под запрос, чтобы застраховаться от NameError!
    target_res = None

    if target_user_id:
        target_res = supabase.table("users").select("*").eq("user_id", target_user_id).eq("is_active", True).execute()
    elif target_username:
        target_res = supabase.table("users").select("*").eq("username", target_username).eq("is_active", True).execute()
    else:
        await context.bot.send_message(chat_id=chat_id, text="❌ Нужно именно тегнуть игрока! Выбери его имя из выпадающего списка Телеграма, когда пишешь /switch @.")
        return
    
    if not target_res or not target_res.data or len(target_res.data) == 0:
        await context.bot.send_message(chat_id=chat_id, text="❌ Этого юзера нет в рулетке, или он ливнул из игры!")
        return
    
    victim = target_res.data[0]

    if victim["user_id"] == user.id:
        # Собираем динамические гендерные подколы для игрока (player)
        genius_title = g_text(player, "гений мысли, ничего не скажешь", "хитрая леди, ничего не скажешь ")
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
    resh_text = g_text(player, "решил", "решила")
    retry_hand_text = g_text(player, "трясущимися руками повторно активирует", "элегантным, но рискованным жестом повторно активирует")

    # Готовим динамические гендерные глаголы для Жертвы (victim)
    loser_coin_text = g_text(victim, "проиграл", "проиграла")
    victim_title = g_text(victim, "Этот оппонент", "Эта леди")
    victim_pronoun = g_text(victim, "его", "её")
    # ФИКС ЗАГОЛОВКА: Динамическое добивание раненого / раненой
    dobivanie_title = g_text(victim, "ДОБИВАНИЕ РАНЕНОГО!", "ДОБИВАНИЕ РАНЕНОЙ!")

    # 4. ВЫДАЕМ ИНТРО-ТЕКСТ С УЧЕТОМ ДИНАМИЧЕСКИХ ШАНСОВ И ГЕНДЕРОВ (ЖЕЛЕЗНО НА HTML)
    if is_robbing_chad:
        intro = [
            f"👑 <b>КРАЖА ВЕКА!</b> Пидор дня <b>{safe_user_name}</b> активирует карту «UNO» против Красавчика <b>{safe_victim_name}</b>!",
            f"🎲 Это Королевское Ограбление! Шанс 15%. Если сработает, титулы поменяются за игровым столом, а карта ОСТАНЕТСЯ ЦЕЛОЙ! 🔥",
        ]
    elif is_coin_loser_target:
        intro = [
            f"🎯 <b>{dobivanie_title}</b> <b>{safe_user_name}</b> активирует карту «UNO» против <b>{safe_victim_name}</b>!",
            f"🎲 {victim_title} сегодня и так эпично {loser_coin_text} в монетку, а ты {resh_text} {victim_pronoun} добить? Рискованный азарт! Шанс перевода повышен до 45%! 🔥\n⚠️ Внимание: в случае провала твой утренний позорный коэффициент умножится на 3!",
        ]
    else:
        if is_retry_attempt:
            intro = [
                f"🔥 <b>ВТОРОЙ ШАНС!</b> <b>{safe_user_name}</b> {retry_hand_text} карту «UNO» против мирного <b>{safe_victim_name}</b>!",
                f"🎲 На этот раз боги рандома шутить не будут. Вероятность 50%. Либо забираешь куш, либо сгораешь окончательно...",
            ]
        else:
            intro = [
                f"🃏 <b>МЕМНЫЙ РЕВЁРС!</b> <b>{safe_user_name}</b> активирует карту «UNO» и пытается скинуть утреннее клеймо на <b>{safe_victim_name}</b>!",
                f"🎲 Шанс перевода 30%... Крупье казино взвешивает ставки... 🎰",
            ]

    for phrase in intro:
        await context.bot.send_message(chat_id=chat_id, text=phrase, parse_mode="HTML")
        await asyncio.sleep(1.0) # Оптимизировали паузу до 1 секунды для ускорения функции

    # --- 🎰 ПОВЫШЕННЫЙ РАСЧЕТ ШАНСОВ (15% / 45% / 50% / 30%) ---
    if is_robbing_chad:
        success_chance = 15  
    elif is_coin_loser_target:
        success_chance = 45 
    elif is_retry_attempt:
        success_chance = 50  
    else:
        success_chance = 30  

    is_success = random.randint(1, 100) <= success_chance

    # === 🧮 [ТИТАНОВЫЙ ОПЕРАТИВНЫЙ ФИКС]: ДОСТАЕМ МНОЖИТЕЛЬ НАПРЯМУЮ ИЗ ПАМЯТИ ===
    if context.bot_data and "today_pidor_multiplier" in context.bot_data:
        today_gained_pidors = int(context.bot_data["today_pidor_multiplier"])
    else:
        today_gained_pidors = 1
    
    if is_coin_loser_target:
        # Х3 НАКАЗАНИЕ ЗА РАНЕНОГО: Утренний позор умножается на 3. 
        added_penalty = int(today_gained_pidors * 2)
        total_day_gained = int(today_gained_pidors * 3)
    else:
        # Х2 НАКАЗАНИЕ ДЛЯ ОСТАЛЬНЫХ: Утренний позор умножается на 2. 
        added_penalty = int(today_gained_pidors)
        total_day_gained = int(today_gained_pidors * 2)

    # Сила утреннего позора для записи в логи и тексты сообщений
    pidor_multiplier = today_gained_pidors  
    penalty_p_count = added_penalty
    
    # Считываем свежий счёт Пидора для дальнейших обновлений
    fresh_winner_res = supabase.table("users").select("pidor_count").eq("user_id", user.id).execute()
    fresh_pidor_count = fresh_winner_res.data[0]["pidor_count"] if (fresh_winner_res.data and len(fresh_winner_res.data) > 0) else today_winner["pidor_count"]
    # Жесткое х3 наказание за провал добивания раненого (Вес взлетает на +30.0)
    if not is_success and is_coin_loser_target:
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Безопасный забор веса из уже существующего локального объекта player!
        current_p_weight = player[0].get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
        new_p_weight = current_p_weight + 30.0  # Локально плюсуем 30 веса!
        
        # Прибавляем ЧИСТУЮ добавку added_penalty к текущему счету и обновляем вес
        supabase.table("users").update({
            "last_switch_date": str(today), 
            "pidor_count": fresh_pidor_count + added_penalty,
            "pidor_weight": new_p_weight  # Записали идеальное динамическое число!
        }).eq("user_id", user.id).execute()
        
        # Записываем провал в лог
        try:
            supabase.table("uno_logs").insert({
                "sender_name": user.first_name,
                "victim_name": victim["first_name"],
                "game_date": str(today),
                "multiplier": 0, # ЖЕЛЕЗНО ИСПРАВЛЕНО: 0 вместо -1, теперь база пропустит сожжённую карту!
                "is_krasavchik": False
            }).execute()
        except Exception as uno_log_err:
            print(f"Ошибка сохранения лога провала UNO: {uno_log_err}")

        # Собираем динамический глагол промаха на основе пола Стрелка (player)
        umudrilsya_text = g_text(player, "умудрился", "умудрилась")
        nakazali_text = g_text(player, "карают тебя за излишний риск", "карают тебя за излишний риск, леди ")

        # АВТОМАТ ДЛЯ ЖЕРТВЫ: проверяем пол того, на кого переводили карту (victim)
        victim_target_text = g_text(victim, "уязвимого оппонента", "у дамы ")

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ <b>ТОТАЛЬНОЕ КАРМИЧЕСКОЕ ПРАВОСУДИЕ!</b> ❌\n\n"
                 f"Карта UNO расплавилась в руках <b>{safe_user_name}</b> при попытке забрать куш {victim_target_text}! Шанс был 45%, но ты {umudrilsya_text} промазать!\n\n"
                 f"Боги рандома {nakazali_text} in тройном размере: твой утренний позор умножается на 3! Получай ещё <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>! 🤡💥💣",
            parse_mode="HTML"
        )

        try:
            await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
        except Exception:
            pass
        return  

    # ================= 🎉🎉🎉 УСПЕШНЫЙ ПЕРЕВОД 🎉🎉🎉 =================
    if is_success:
        context.user_data.pop("switch_retry", None) # очищаем память ретрая
        
        # ЖЕЛЕЗНЫЙ ФИКС БАГА: Объявляем дефолтный множитель, чтобы не было NameError при краже короны!
        pidor_multiplier = 1 
        
        # 👑 ПУТЬ А: УСПЕШНОЕ ОГРАБЛЕНИЕ КРАСАВЧИКА (КД НЕ ЗАПИСЫВАЕМ!)
        if is_robbing_chad:
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Безопасный забор весов Стрелочника из списка player
            current_kras_w = player[0].get("kras_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
            current_pidor_w = player[0].get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
            
            # Считаем динамические дельты (+20 к красавчику и -15 к пидору)
            new_kras_w = current_kras_w + 20.0
            new_pidor_w = max(1.0, current_pidor_w - 15.0)  # Жесткий пол 1.0 от ухода в минус
            
            # 1. Обновляем Стрелочника (берем старый pidor_count/kras_count из today_winner)
            supabase.table("users").update({
                "pidor_count": max(0, today_winner["pidor_count"] - 1), 
                "kras_count": today_winner["kras_count"] + 1, 
                "pidor_weight": new_pidor_w, 
                "kras_weight": new_kras_w
            }).eq("user_id", user.id).execute()

            # 2. Обновляем Жертву (минус красавчик, плюс пидор, веса: -10 к красавчику +10 к пидору)
            current_vic_kras_w = victim.get("kras_weight", 100.0)
            current_vic_pidor_w = victim.get("pidor_weight", 100.0)
            
            new_vic_kras_w = max(1.0, current_vic_kras_w - 10.0)  # Страховка от ухода в минус
            new_vic_pidor_w = current_vic_pidor_w + 10.0
            
            supabase.table("users").update({
                "kras_count": max(0, victim["kras_count"] - 1), 
                "pidor_count": victim["pidor_count"] + 1, 
                "pidor_weight": new_vic_pidor_w, 
                "kras_weight": new_vic_kras_w
            }).eq("user_id", victim["user_id"]).execute()
            # 3. Перебиваем историю сегодняшнего дня в daily_winners строго по ролям
            supabase.table("daily_winners").update({"user_id": victim["user_id"]}).eq("game_date", str(today)).eq("role", "pidor").execute()
            supabase.table("daily_winners").update({"user_id": user.id}).eq("game_date", str(today)).eq("role", "krasavchik").execute()

            # [ЛОГ УНО] Записываем Королевское ограбление в историю
            supabase.table("uno_logs").insert({
                "sender_name": user.first_name,
                "victim_name": victim["first_name"],
                "game_date": str(today),
                "multiplier": 1,  # Вместо pidor_multiplier ставим 1! Баг уничтожен.
                "is_krasavchik": True
            }).execute()

        # === 🚨 КАТАСТРОФОУСТОЙЧИВЫЙ БЛОК ОТПРАВКИ ТРИУМФА ОГРАБЛЕНИЯ КРАСАВЧИКА 🚨 ===
        try:
            # 1. Собираем динамические гендерные статусы и глаголы
            winner_status = g_text(player, "СТАНОВИТСЯ НОВЫМ КРАСАВЧИКОМ ДНЯ!", "СТАНОВИТСЯ НОВОЙ КРАСАВИЦЕЙ ДНЯ! 👑")
            victim_status = g_text(victim, "признаётся <b>ПИДОРОМ ДНЯ</b>!", "признаётся <b>ПИДОРОМ ДНЯ</b>! ")
            fallen_text = g_text(victim, "с позором падает на дно и", "теряет всё за игровым столом и")

            # 2. Формируем чистый текст без вложенных скобок внутри вызова
            success_text = (
                f"💥 <b>БОЖЕ МОЙ, ЭТО ИСТОРИЧЕСКИЙ МОМЕНТ! КАРТА ОСТАЕТСЯ ЦЕЛОЙ!</b> 💥\n\n"
                f"Королевское ограбление завершилось полным триумфом за игровым столом!\n\n"
                f"😎 <b>{safe_user_name}</b> забирает главный куш и {winner_status}\n\n"
                f"🤡 А вот <b>{safe_victim_name}</b> {fallen_text} {victim_status}"
            )

            # 3. Отправляем готовое сообщение в чат
            await context.bot.send_message(
                chat_id=chat_id,
                text=success_text,
                parse_mode="HTML"
            )
        except Exception as tg_text_err:
            print(f"Косметическая ошибка отправки текста триумфа ограбления: {tg_text_err}")
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="🔧 <b>Сука, опять вы всё сломали!</b> 🤦‍♂️\n\nКоролевское ограбление Красавчика зависло в текстурах Телеграма! Корона украдена, база всё записала, админ пошёл чинить!",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            
        try:
            # 4. Следом пробуем отправить твой чемпионский стикер триумфа
            await context.bot.send_sticker(
                chat_id=chat_id, 
                sticker='CAACAgIAAxkBAAERfwtqSi0WKXA0-slyXjuDMUAC14PGkAAC6BMAAp7K8UkQAAGdV1VM7UI8BA'
            )
        except Exception as tg_sticker_err:
            print(f"Косметическая ошибка отправки стикера триумфа ограбления: {tg_sticker_err}")
            try:
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERv_1qh-RMBre9eek9ykdsovu3gf-SvwACCnUAAlgXsEkCKvJjaqw9iT0E')
            except Exception:
                pass

        # 🃏 ПУТЬ Б: УСПЕШНЫЙ ОБЫЧНЫЙ ПЕРЕВОД / ДОБИВАНИЕ (ВЫЧИСЛЯЕМ МНОЖИТЕЛЬ ПОЗОРА)
        if not is_robbing_chad:
            # Записываем КД стрелочнику
            supabase.table("users").update({"last_switch_date": str(today)}).eq("user_id", user.id).execute()
            
            # --- 📊 ДИНАМИЧЕСКИЙ РАСЧЕТ МНОЖИТЕЛЯ ПОЗОРА (Честность для чата) ---
            fresh_winner_res = supabase.table("users").select("pidor_count").eq("user_id", user.id).execute()
            
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Безопасный забор элемента из массива fresh_winner_res.data
            fresh_pidor_count = fresh_winner_res.data[0]["pidor_count"] if (fresh_winner_res.data and len(fresh_winner_res.data) > 0) else today_winner["pidor_count"]
            
            # Вычисляем, какой множитель прилетел сегодня (х1, х2, х3 или х5)
            pidor_multiplier = max(1, fresh_pidor_count - today_winner["pidor_count"])
            
            # === 🃏 ПУТЬ Б: УСПЕШНЫЙ ОБЫЧНЫЙ ПЕРЕВОД ===
            # ЖЕЛЕЗНО ИСПРАВЛЕНО: Забираем вес из готового локального объекта player, предотвращая AttributeError!
            current_sender_w = player.get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
            current_victim_w = victim.get("pidor_weight", 100.0)
            
            new_sender_w = max(1.0, current_sender_w - 10.0)  # Жесткий пол 1.0 от ухода в минус
            new_victim_w = max(1.0, current_victim_w - 10.0)
            # 1. Обновляем Стрелочника (списываем ВСЕ начисленные сегодня позоры под ноль!)
            supabase.table("users").update({
                "pidor_count": max(0, fresh_pidor_count - pidor_multiplier), 
                "pidor_weight": new_sender_w
            }).eq("user_id", user.id).execute()
            
            # 2. Обновляем Жертву (навешиваем ей ВЕСЬ сегодняшний джекпот целиком!)
            supabase.table("users").update({
                "pidor_count": victim["pidor_count"] + pidor_multiplier, 
                "pidor_weight": new_victim_w
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

                try:
                    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERl5ZqYzAUBU7z06cdM38fa4YZfog1xAACYwEAAnHpkDYtQnUiFYhhSj0E')
                except Exception:
                    pass
            
            elif is_retry_attempt:
                # 🦊 УСПЕШНЫЙ ВТОРОЙ ШАНС (50% ШАНС) — ЧИСТЫЙ ВАРИАНТ БЕЗ TRY
                # Собираем динамические титулы и глаголы для Стрелка (player)
                fox_title = g_text(player, "ХИТРЫЙ ЛИС В ДЕЛЕ", "ХИТРАЯ ЛИСА В ДЕЛЕ 🦊")
                ochishen_text = g_text(player, "полностью очищен от подозрений, мастер тактики", "полностью очищена от подозрений, королева интуиции 💎")

                # Собираем динамические статусы для пострадавшего оппонента (victim)
                victim_status = g_text(victim, "официально становится <b>ПИДОРОМ ДНЯ</b>", "официально становится <b>ПИДОРОМ ДНЯ</b>")
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🦊 <b>КАК ТАК-ТО?! {fox_title}!</b> 🦊\n\n"
                        f"Первая карта задымилась, но со второго шанса <b>{safe_user_name}</b> {g_text(player, 'совершает невозможное', 'совершает невозможное')} и выбивает заветные 50%!\n"
                        f"👑 Ты {ochishen_text}!\n\n"
                        f"🤡 А вот <b>{safe_victim_name}</b> {victim_status} со второй подачи за игровым столом! Ставки приняты! 🎰"
                    ),
                    parse_mode="HTML"
                )

                try:
                    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERg8xqT1rvV4e9QOkd5krbAdwHGMbORQACrB8AAi-rqEswnXHdk_VAETwE')
                except Exception:
                    pass
            
            else:
                # 💥 ОБЫЧНЫЙ ПЕРЕВОД (30% ШАНС) — ТЕПЕРЬ С ГЕНДЕРАМИ ПАЦАНОВ И ДЕВЧОНОК
                multiplier_alert = f" (с учётом множителя х{pidor_multiplier}!)" if pidor_multiplier > 1 else ""
                    
                # Собираем глаголы очищения для Стрелочника и позора для Юзера
                sender_clean_text = g_text(player, "полностью очищен от подозрений", "полностью очищена от подозрений")
                victim_status_text = g_text(victim, "становится <b>ПИДОРОМ ДНЯ</b>", "становится <b>ПИДОРОЙ ДНЯ</b>")
                victim_accept_text = g_text(victim, "Смирись!", "Принимай правила игры!")

                # ЖЕЛЕЗНО ИСПРАВЛЕНО: Запоминаем: Стрелок (user.id) затащил, Жертва (victim["user_id"]) пострадал
                if context.chat_data is None:
                    context.chat_data = {}
                context.chat_data["last_switch_clash"] = {
                    "winner_id": user.id,
                    "loser_id": victim["user_id"],
                    "status": "success",
                    "date": str(date.today())
                }

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"💥 <b>СТРЕЛКИ УСПЕШНО ПЕРЕВЕДЕНЫ!</b> 💥\n\n"
                        f"Игрок <b>{safe_user_name}</b> {sender_clean_text} за игровым столом!\n"
                        f"🤡 А вот <b>{safe_victim_name}</b> {victim_status_text}{multiplier_alert}! {victim_accept_text} 🎰"
                    ),
                    parse_mode="HTML"
                )

                try:
                    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQxqQ3c1Ul6X4NVVPO-Fd7SdNeiqIgACx04AAnJSgEuFrKam1iO89TwE')
                except Exception:
                    pass

        except Exception as e:
            print(f"Ошибка вывода результата успешного блока UNO: {e}")
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

        if is_robbing_chad:
            # Вытаскиваем текущий позорный вес Стрелочника до промаха карты
            current_p_weight = player.get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
            new_p_weight = current_p_weight + 20.0  # Локально накидываем +20 к пидор-весу!

            # Сдвигаем кулдаун на +6 дней в будущее, чтобы суммарно вышло 12 дней КД!
            fake_cd_date = today + timedelta(days=6)
            supabase.table("users").update({
                "last_switch_date": str(fake_cd_date), 
                "pidor_count": fresh_pidor_count + added_penalty,
                "pidor_weight": new_p_weight  
            }).eq("user_id", user.id).execute()

            try:
                # ЖЕЛЕЗНО ИСПРАВЛЕНО: Записываем 0 вместо -1, теперь база пропустит транзакцию лога!
                supabase.table("uno_logs").insert({
                    "sender_name": user.first_name,
                    "victim_name": victim["first_name"],
                    "game_date": str(today),
                    "multiplier": 0,  
                    "is_krasavchik": True
                }).execute()
            except Exception as e_log:
                print(f"Ошибка сохранения уно-лога провала на красавчика: {e_log}")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>КОРОЛЕВСКОЕ ОГРАБЛЕНИЕ ПРОВАЛЕНО!</b> ❌\n\n"
                     f"Королевская защита Красавчика оказалась непробиваемой. Карта UNO рассыпалась в прах!\n\n"
                     f"<b>{safe_name}</b>, за покушение на Корону твой утренний позор удваивается: получай <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>!\n"
                     f"⏳ А за наглость шериф изымает карту UNO на <b>12 ДНЕЙ ПЕРЕЗАРЯДКИ</b>! 🤡💣",
                parse_mode="HTML"
            )
            try:
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
            except Exception:
                pass
            return
            
        elif is_coin_loser_target:
            # Вытаскиваем текущий позорный вес Стрелочника до промаха карты
            current_p_weight = player.get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
            new_p_weight = current_p_weight + 30.0  # Локально накидываем +30 за провал добивания раненого!

            # Жесткое х3 наказание за провал добивания раненого
            supabase.table("users").update({
                "last_switch_date": str(today), 
                "pidor_count": fresh_pidor_count + added_penalty,
                "pidor_weight": new_p_weight  
            }).eq("user_id", user.id).execute()
            
            try:
                # ЖЕЛЕЗНО ИСПРАВЛЕНО: Записываем 0 вместо -1
                supabase.table("uno_logs").insert({
                    "sender_name": user.first_name,
                    "victim_name": victim["first_name"],
                    "game_date": str(today),
                    "multiplier": 0,
                    "is_krasavchik": False
                }).execute()
            except Exception as e_log:
                print(f"Ошибка сохранения уно-лога провала добивания: {e_log}")

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ <b>ТОТАЛЬНОЕ КАРМИЧЕСКОЕ ПРАВОСУДИЕ!</b> ❌\n\n"
                     f"Карта UNO расплавилась в руках <b>{safe_name}</b> при попытке добить раненого! Шанс был 45%, но ты {umudrilsya_text} промазать!\n\n"
                     f"Боги рандома {nakazali_text} в тройном размере: твой утренний позор умножается на 3! Получай ещё <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>! 🤡💥💣",
                parse_mode="HTML"
            )
            try:
                await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
            except Exception:
                pass
            return

        else:
            if is_retry_attempt:
                # Вытаскиваем текущий позорный вес Стрелочника до промаха карты
                current_p_weight = player.get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
                new_p_weight = current_p_weight + 5.0  # Локально накидываем +5 за тотал-неудачника!

                # Вторая попытка провалилась — сжигаем карту с х2 штрафом от утра и +5 к весу позора
                supabase.table("users").update({
                    "last_switch_date": str(today), 
                    "pidor_count": fresh_pidor_count + added_penalty,
                    "pidor_weight": new_p_weight
                }).eq("user_id", user.id).execute()
                context.user_data.pop("switch_retry", None)

                try:
                    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Записываем 0 вместо -1
                    supabase.table("uno_logs").insert({
                        "game_date": str(date.today()),
                        "sender_name": user.first_name,
                        "victim_name": victim["first_name"],
                        "multiplier": 0,  
                        "is_krasavchik": False
                    }).execute()
                except Exception as e_log:
                    print(f"Ошибка сохранения уно-лога провала ретрая: {e_log}")

                streloch_title = g_text(player, "СТРЕЛОЧНИК", "СТРЕЛОЧНИЦА")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"💀 <b>ПОЛНОЕ ФИАСКО, {streloch_title}!</b> Второй шанс тоже провален! 💀\n\n"
                         f"Твоя карта UNO превратилась в пепел. Твой сегодняшний позор удваивается: получай ещё <b>+{added_penalty} пидора</b> <i>(всего {total_day_gained} за сегодня)</i>. Кулдаун 6 дней взведён! 🤡",
                    parse_mode="HTML"
                )
                try:
                    await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERg9tqT2Lb7EssiCPdH7XeEz1W5sbVswAC6S8AApkAAYhJDcx-Vp6-Sco8BA')
                except Exception:
                    pass
                return  

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
                    try:
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAERg85qT110qgTm1RJWyqRuKm0QwbCoLwAC9B4AAiNcOEtYh2FNKYLHdDwE')
                    except Exception:
                        pass
                    return
                else:
                    # Стандартный провал на мирного с первого раза с честным х2
                    current_p_weight = player.get("pidor_weight", 100.0) if (player and isinstance(player, list) and len(player) > 0) else 100.0
                    
                    # КАЗИНОВСКИЙ РАНДОМ: накидываем случайный штраф от +5.0 до +25.0 к текущему весу!
                    random_penalty_weight = random.uniform(5.0, 25.0)
                    new_p_weight = current_p_weight + random_penalty_weight

                    supabase.table("users").update({
                        "last_switch_date": str(today), 
                        "pidor_count": fresh_pidor_count + added_penalty,
                        "pidor_weight": round(new_p_weight, 1)  
                    }).eq("user_id", user.id).execute()

                    try:
                        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Записываем 0 вместо -1
                        supabase.table("uno_logs").insert({
                            "game_date": str(date.today()),
                            "sender_name": user.first_name,
                            "victim_name": victim["first_name"],
                            "multiplier": 0,  
                            "is_krasavchik": False
                        }).execute()
                    except Exception as e_log:
                        print(f"Ошибка сохранения лога стандартного провала: {e_log}")

                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ <b>КАРТА UNO ПОРВАЛАСЬ!</b> ❌\n\n"
                             f"Перевод сорвался и отрикошетил обратно в <b>{safe_name}</b>. "
                             f"Твой сегодняшний позор честно удваивается: лови ещё <b>+{added_penalty} пидора</b> в досье <i>(всего {total_day_gained} за сегодня)</i>! Карта уходит на КД 6 дней! 🤡",
                        parse_mode="HTML"
                    )
                    
                    # ИЗОЛИРОВАЛИ СТИКЕР: Теперь он в своём закрытом боксе и никому не мешает
                    try:
                        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAEReQpqQ3adafSczLOzJ3WEyKHoQvfvJAACNhUAAjhx-EmeBZwsT5kj1TwE')
                    except Exception as s_err:
                        print(f"Микро-сбой отправки стикера провала: {s_err}")
                    return

    except Exception as global_uno_err:
        # ЭТОТ БЛОК ОСТАЁТСЯ СТРОГО ОДИН В САМОМ КОНЦЕ ДЛЯ ОТЛОВЛИ КРИТИЧЕСКИХ ПАДЕНИЙ ФУНКЦИИ
        print(f"❌ Глобальный сбой функции switch: {global_uno_err}")

async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    today = date.today()
    
    # === 🛡️ ТИТАНОВЫЙ АВТО-ОБНОВИТЕЛЬ ТЕГОВ КАЗИНО: ЗАЩИТА ОТ СМЕНЫ НИКНЕЙМОВ ===
    # Как только игрок запрашивает досье, база на лету освежает его актуальный тег и имя!
    if user and user.username:
        try:
            supabase.table("users").update({"username": user.username, "first_name": user.first_name}).eq("user_id", user.id).execute()
        except Exception:
            pass
    
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

    # 2. РАССЧИТЫВАЕМ ЧЕСТНЫЕ ПРОЦЕНТЫ ШАНСОВ (Математическая синхронизация с /procents)
    total_pidor_weight = sum(u.get("pidor_weight", 100.0) for u in active_users)
    total_kras_weight = sum(u.get("kras_weight", 100.0) for u in active_users)
    
    # Константы Ромы-Монте-Карло для точности Красавчика
    m = 0.30  
    q = 0.50  

    # Честный процент Пидора (без аномалий)
    pidor_chance = (player.get("pidor_weight", 100.0) / total_pidor_weight * 100) if total_pidor_weight > 0 else 0.0
    
    # ЖЕЛЕЗНО ИСПРАВЛЕНО: Заменили фантомную N на рабочий len(active_users) чата!
    if total_kras_weight > 0 and len(active_users) > 1:
        p_i = player.get("kras_weight", 100.0) / total_kras_weight
        real_kras_chance = (1 - m) * p_i + m * (q * p_i + ((1 - p_i) / (len(active_users) - 1)) * q)
        kras_chance = real_kras_chance * 100
    else:
        kras_chance = (player.get("kras_weight", 100.0) / total_kras_weight * 100) if total_kras_weight > 0 else 0.0

    # 3. Проверяем статус КД карты UNO
    uno_status = "🟢 ГОТОВА К БОЮ!"
    if player.get("last_switch_date"):
        last_date = safe_parse_date(player.get("last_switch_date"))
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
    uno_wins_res = supabase.table("uno_logs").select("id").eq("sender_name", player["first_name"]).gt("multiplier", 0).execute()
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

    # === 🎲 [БАЛАНСИРОВАННАЯ КАРМА]: КУБИКИ СУДЬБЫ (МАКСИМУМ 30.0) ===
    if dice_value <= 3:
        # ======= 🤡 ВЕТКА ПОЗОРА (1, 2, 3) =======
        # ШАГ СБАЛАНСИРОВАН: Грань 3 -> +5, Грань 2 -> +15, Грань 1 -> +30 к позорному весу!
        step = 5.0 if dice_value == 3 else (15.0 if dice_value == 2 else 30.0)
        k_minus = 2.0 if dice_value == 3 else (5.0 if dice_value == 2 else 10.0)
        
        new_pidor_weight = player["pidor_weight"] + step
        new_kras_weight = max(1.0, player["kras_weight"] - k_minus)
        
        # Пересчитали чистый профит сессии под максимум 30
        current_dice_gain = -7.0 if dice_value == 3 else (-20.0 if dice_value == 2 else -40.0)
        saved_balance = current_dice_gain if current_attempts == 0 else prev_balance

        supabase.table("users").update({
            "pidor_weight": new_pidor_weight,
            "kras_weight": new_kras_weight,
            "dice_count": new_db_value,
            "dice_start_balance": saved_balance
        }).eq("user_id", user.id).execute()
        
        charm_title = g_text(player, "личный шарм заметно просел", "женское обаяние слегка пошатнулось 💔")

        if dice_value == 1:
            power_text = "💥 <b>КРИТИЧЕСКИЙ УДАР ПО СТАВКАМ! (+30 к позору)!</b> 💥 Твоя вероятность забрать позорное клеймо увеличилась, а шансы на корону Красавчика скользнули вниз!"
        elif dice_value == 2:
            power_text = f"ощутимый заплыв в сомнительную сторону (+15 к позору). Твои риски на Пидора дня увеличились, а {charm_title}."
        else:
            power_text = "микро-осечка за игровым столом (+5 к позору). Коэффициенты скорректировались вверх, фортуна выражает недовольство."

        intro_text = f"🎲 На кубике выпадает: <b>{dice_value}</b>!\n\n🤡 <b>ФОРТУНА ОТВЕРНУЛАСЬ!</b> <b>{safe_name}</b>, это {power_text}"
            
    else:
        # ======= 😎 ВЕТКА УДАЧИ (4, 5, 6) =======
        # ШАГ СБАЛАНСИРОВАН: Грань 4 -> +5, Грань 5 -> +15, Грань 6 -> +30 к чемпионскому весу!
        step = 5.0 if dice_value == 4 else (15.0 if dice_value == 5 else 30.0)
        p_minus = 2.0 if dice_value == 4 else (5.0 if dice_value == 5 else 10.0)
        
        new_kras_weight = player["kras_weight"] + step
        new_pidor_weight = max(1.0, player["pidor_weight"] - p_minus)
        
        # Пересчитали чистый профит сессии под максимум 30
        current_dice_gain = 7.0 if dice_value == 4 else (20.0 if dice_value == 5 else 40.0)
        saved_balance = current_dice_gain if current_attempts == 0 else prev_balance

        supabase.table("users").update({
            "kras_weight": new_kras_weight,
            "pidor_weight": new_pidor_weight,
            "dice_count": new_db_value,
            "dice_start_balance": saved_balance
        }).eq("user_id", user.id).execute()
        
        charm_gain = g_text(player, "мощный прилив шарма", "мощный прилив обаяния ✨")
        pobeda_word = g_text(player, "на победу", "на корону Красавицы")

        if dice_value == 6:
            power_text = "👑 <b>АБСОЛЮТНЫЙ ДЖЕКПОТ КАЗИНО (+30 к весу)!</b> 👑 Твои показатели привлекательности за столом засияли ярким блеском, а позорные риски рулетки неплохо так снизились!"
        elif dice_value == 5:
            power_text = f"{charm_gain} (+15 к весу)! Проценты {pobeda_word} уверенно поползли вверх, а вероятность поймать позорное клеймо тает."
        else:
            power_text = "скромный шаг к успеху за игровым столом (+5 к весу). Чуть-чуть подбавил веса в стату, риски позора символически снижены."

        intro_text = f"🎲 На кубике выпадает: <b>{dice_value}</b>!\n\n😎 <b>ФОРТУНА УЛЫБАЕТСЯ ТЕБЕ!</b> <b>{safe_name}</b>, это {power_text}"

    # 📊 МАТЕМАТИКА 2: Пересчитываем точные суммы чата с учётом клампинга веса игрока!
    if dice_value <= 3:
        real_kras_delta = player.get("kras_weight", 100.0) - new_kras_weight
        total_p_after = total_p_before + step
        total_k_after = total_k_before - real_kras_delta
    else:
        real_pidor_delta = player.get("pidor_weight", 100.0) - new_pidor_weight
        total_k_after = total_k_before + step
        total_p_after = total_p_before - real_pidor_delta
    
    new_p_chance = (new_pidor_weight / total_p_after * 100) if total_p_after > 0 else 0.0
    new_k_chance = (new_kras_weight / total_k_after * 100) if total_k_after > 0 else 0.0


    # --- 🚨 ПЕРЕХВАТ ДУБЛЕЙ (ЖЕЛЕЗНО ПЕРЕПИСАЛИ ИЗ-ЗА НОВЫХ ШАГОВ НА БАЛАНС 40.0) ---
    if current_attempts == 1 and prev_balance == -40.0 and dice_value == 1:
        status_title = g_text(player, "Игрок", "Леди")
        vjsh_text = g_text(player, "умудряется выбить", "умудряется выбросить")
        bro_text = g_text(player, "бро", "леди")
        ego_text = g_text(player, "твоему авторитету", "твоим ставкам")

        result_text = (
            f"🎲 На кубике выпадает: <b>1</b> (Дубль!)\n\n"
            f"🚨 <b>ЧЁРНЫЙ ДЕНЬ ДЛЯ СТАВОК! КРИТИЧЕСКОЕ ПРОБИТИЕ ДНА В ВЕСАХ!</b> 🎪\n\n"
            f"{status_title} <b>{safe_name}</b> {vjsh_text} дубль <b>1 и 1</b> за неделю! Это суммарно +60 к позору! 😭\n"
            f"Да уж, соболезнуем {ego_text}, {bro_text}! Крупье за игровым столом вытирает слёзы жалости.\n\n"
            f"📊 <b>ДИНАМИКА ТВОИХ ШАНСОВ:</b>\n"
            f" └ 🤡 Шанс Пидора: <code>{old_p_chance:.1f}%</code> ➡️ <b>{new_p_chance:.1f}%</b> 📈\n"
            f" └ 😎 Шанс Красавчика: <code>{old_k_chance:.1f}%</code> ➡️ <b>{new_k_chance:.1f}%</b> 📉\n\n"
            f"{remains_text}"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgUAAxkBAAERr4pqeX-dpAQpHvj3CZnAcPY0_UmGSQACgggAAjiksVVM5Vj4fvPn0z0E')

    elif current_attempts == 1 and prev_balance == 40.0 and dice_value == 6:
        # Собираем динамические гендерные титулы и фразы для везунчика (на основе player)
        status_title = g_text(player, "Игрок", "Леди")
        vybros_text = g_text(player, "выбрасывает", "выбрасывает ✨")
        style_title = g_text(player, "наглый любимчик фортуны", "настоящая икона стиля 💎")

        result_text = (
            f"🎲 На кубике выпадает: <b>6</b> (Дубль!)\n\n"
            f"🎰 <b>ОБНАРУЖЕН ЧИТЕР! ВЫ С КЕМ ТАМ НАВЕРХУ ДОГОВОРИЛИСЬ?!</b> 👑\n\n"
            f"{status_title} <b>{safe_name}</b> {vybros_text} дубль <b>6 и 6</b> за неделю! Это суммарно +60 к весу Красавчика! 🤯\n"
            f"Администрация казино официально заявляет: этот игровой стол поддался от такой наглой удачи, ты — {style_title}!\n\n"
            f"📊 <b>ДИНАМИКА ТВОИХ ШАНСОВ:</b>\n"
            f" └ 🤡 Шанс Пидора: <code>{old_p_chance:.1f}%</code> ➡️ <b>{new_p_chance:.1f}%</b> 📉\n"
            f" └ 😎 Шанс Красавчика: <code>{old_k_chance:.1f}%</code> ➡️ <b>{new_k_chance:.1f}%</b> 📈\n\n"
            f"{remains_text}"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgQAAxkBAAERlA5qX28PoaHLw_vQlr61kl4t7WzyFgACUAgAAtRigFLWQCl12cGV0z0E')

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
            
            # ЖЕЛЕЗНЫЙ МАТЕМАТИЧЕСКИЙ ФИКС: Сверяем дубли строго по новому шагу баланса 40.0!
            is_absolute_jackpot = (first_dice_gain == 40.0 and dice_value == 6)
            is_absolute_fiasco = (first_dice_gain == -40.0 and dice_value == 1)
            
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
    
    # 1. ЖЕЛЕЗНЫЙ ВЕРНЫЙ ЗАПРОС: Вытаскиваем только успешные переводы (multiplier > 0)
    # Сортируем по id от свежих к старым сразу в базе!
    res = supabase.table("uno_logs").select("*").eq("sender_name", user.first_name).gt("multiplier", 0).order("id", desc=True).execute()

    player_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    player = player_res.data[0] if player_res.data and len(player_res.data) > 0 else {"gender": "boy"}
    safe_sender_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")

    # Проверяем на пустоту ОДИН РАЗ
    if not res.data or len(res.data) == 0:
        smog_text = g_text(player, "смог успешно перевести карту", "смогла успешно перевести карту")
        nevezet_text = g_text(player, "чертовски не везёт на переводы, либо ты слишком мирный ковбой", "не везёт на риски, либо ты слишком мирная леди")
        await context.bot.send_message(
            chat_id=chat_id, 
            text=f"🃏 <b>{safe_sender_name}</b>, твоя личная хроника UNO пуста!\n\nТы ещё ни разу в истории чатика не {smog_text}. Либо тебе {nevezet_text}! 😏", 
            parse_mode="HTML"
        )
        return

    # Шапка досье
    header = f"🃏 <b>ЛИЧНАЯ ХРОНИКА : {safe_sender_name.upper()}</b> 🃏\n"
    header += f"<i>Крупье поднял архивные записи казино... Вот твои успешные переводы стрелок за игровым столом:</i>\n\n"
    
    lines = []
    for log in res.data:
        try:
            raw_date = date.fromisoformat(log["game_date"])
            formatted_date = raw_date.strftime("%d.%m")
        except Exception:
            formatted_date = log["game_date"]

        safe_victim = log["victim_name"].replace("<", "&lt;").replace(">", "&gt;")
        mult = log.get("multiplier", 1)

        # === 🛡️ УЛЬТИМАТИВНЫЙ ФИКС ТЁЗОК ОТ РОМЫ: ИЩЕМ ЖЕРТВУ БЕЗ ОШИБОК ===
        # Пытаемся вытащить юзернейм из victim_name, если он там есть в скобках (например, "Артём (@artem)")
        import re
        username_match = re.search(r'\(@([\w_]+)\)', log["victim_name"])
        
        if username_match:
            # Если у жертвы есть ник — бьём по базе со стопроцентной точностью!
            victim_user_res = supabase.table("users").select("gender").eq("username", username_match.group(1)).execute()
        else:
            # Если ника нет, страхуемся по имени, забирая первую попавшуюся запись
            victim_user_res = supabase.table("users").select("gender").eq("first_name", log["victim_name"]).execute()
            
        # ЖЕЛЕЗНО ИСПРАВЛЕНО: Безопасный забор элемента [0] только если список НЕ пустой!
        if victim_user_res.data and len(victim_user_res.data) > 0:
            victim_gender = victim_user_res.data[0].get("gender", "boy")
        else:
            victim_gender = "boy"

        # Объявляем логические флаги полов для развилки текстов
        is_sender_girl = (player.get("gender") == "girl")
        is_victim_girl = (victim_gender == "girl")

        if not is_sender_girl and not is_victim_girl:
            perevel_action = f"ты перевёл стрелки на <b>{safe_victim}</b>! Жертва ушёл на дно! 🤡"
            tehn_action = f"ты технично перевёл позорный статус на <b>{safe_victim}</b>"
        elif not is_sender_girl and is_victim_girl:
            perevel_action = f"ты перевёл стрелки на <b>{safe_victim}</b>! Она ушла на дно! 🤡💣"
            tehn_action = f"ты технично перевёл позорный статус на <b>{safe_victim}</b>"
        elif is_sender_girl and not is_victim_girl:
            perevel_action = f"ты перевела стрелки на <b>{safe_victim}</b>! Жертва ушёл на дно! 🤡"
            tehn_action = f"ты технично перевела позорный статус на <b>{safe_victim}</b>"
        else:
            perevel_action = f"ты перевела стрелки на <b>{safe_victim}</b>! Она ушла на дно! 🤡"
            tehn_action = f"ты технично перевела позорный статус на <b>{safe_victim}</b>"

        ofigel_text = g_text(player, "ты вообще офигел и <b>Украл статус Красавчика дня</b>", "ты проявила дерзость и <b>Забрала статус Красавицы дня</b> 👑")
        ahuel_text = g_text(player, "ты вообще ахуел и умудрился спиздить множитель Красавчика", "ты устроила абсолютный разнос и перехватила джекпот Красавицы")

        if log.get("is_krasavchik", False):
            action_text = f"{ahuel_text} <b>[х{mult}]</b>! Это легендарный раунд! 🤯🚀" if mult >= 5 else f"{ofigel_text}! Королевский налёт! 💎"
        else:
            action_text = f"{perevel_action} с жёстким множителем позора <b>[х{mult}]</b>! 💣" if mult > 1 else f"{tehn_action}. Чистая работа! 💥"

        lines.append(f"📅 <code>{formatted_date}</code> — {action_text}")

    # === 🔥 ИСПРАВЛЕННЫЙ БЛОК ВЫВОДА (СПАМ УНИЧТОЖЕН!) ===
    chunk_size = 30
    end_phrase = g_text(player, "каждого твоего подлеца, друг... 😏⚔️", "каждую твою хитрую комбинацию за столом... 😏🔮")

    if len(lines) <= chunk_size:
        # Отправляем ВСЕГО ОДНО сообщение, если логов мало!
        full_message = header + "\n".join(lines) + f"\n\n<i>Архивы казино помнят {end_phrase}</i>"
        await context.bot.send_message(chat_id=chat_id, text=full_message, parse_mode="HTML")
    else:
        # Бьём по чанкам, только если логов реально огромная гора
        for chunk_index in range(0, len(lines), chunk_size):
            chunk = lines[chunk_index:chunk_index + chunk_size]
            chunk_message = "\n".join(chunk)
            if chunk_index == 0:
                chunk_message = header + chunk_message
            if chunk_index + chunk_size >= len(lines):
                chunk_message += f"\n\n<i>Архивы казино помнят {end_phrase}</i>"
            await context.bot.send_message(chat_id=chat_id, text=chunk_message, parse_mode="HTML")
            await asyncio.sleep(0.5)


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

async def command_notbed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    today_str = str(date.today())
    
    res = supabase.table("uno_logs").select("*").eq("game_date", today_str).order("id").execute()
    
    if not res.data or len(res.data) == 0:
        await context.bot.send_message(chat_id=chat_id, text="🃏 За игровым столом сегодня не было активированных карт UNO. Команда недоступна!", parse_mode="HTML")
        return

    clash = res.data[-1]
    sender_name = clash.get("sender_name")
    victim_name = clash.get("victim_name")
    mult = clash.get("multiplier", 1)

    if mult == -1:
        await context.bot.send_message(chat_id=chat_id, text="🙅‍♂️ Какой 'notbad'? В последнем замесе карта UNO дала жёсткую осечку! Тут уместна другая команда... 😏💣", parse_mode="HTML")
        return

    # УЛЬТИМАТИВНЫЙ ЛЕНИВЫЙ ФИКС: Вытаскиваем реальные профили участников по их именам из лога
    db_sender = supabase.table("users").select("user_id").eq("first_name", sender_name).execute().data
    db_victim = supabase.table("users").select("user_id").eq("first_name", victim_name).execute().data
    
    sender_id = db_sender[0]["user_id"] if db_sender else None
    victim_id = db_victim[0]["user_id"] if db_victim else None

    # Проверяем причастность строго по железным цифровым ID Телеграма!
    if user.id != sender_id and user.id != victim_id:
        await context.bot.send_message(chat_id=chat_id, text="🙅‍♂️ Ты не участвовал в сегодняшнем карточном замесе. Не лезь за чужой игровой стол!", parse_mode="HTML")
        return

    player_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    player = player_res.data[0] if player_res.data and len(player_res.data) > 0 else {"gender": "boy"}
    safe_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")

    if user.id == sender_id:
        msg_boy = "Чистая тактика, пацаны! Я перевёл, сучки, учитесь, пока я добрый! Коддинг высокого уровня! 😎🎰"
        msg_girl = "Абсолютная грация, мальчики! Забрала этот раунд на чистом интуитивном расчёте. Учитесь! 💎💅"
        await context.bot.send_message(chat_id=chat_id, text=f"🥂 <b>{safe_name}</b> вальяжно откидывается на стуле и объявляет:\n\n🔥 <b>{g_text(player, msg_boy, msg_girl)}</b>", parse_mode="HTML")
    else:
        msg_boy = "Признаю, разыграно красиво... Технично подловил. Но игровой день ещё длинный, я отыграюсь! 🚬"
        msg_girl = "Это был дерзкий выпад, признаю... Но фортуна в казино капризна, мой ход ещё впереди! 🐍"
        await context.bot.send_message(chat_id=chat_id, text=f"🐌 <b>{safe_name}</b> грустно цедит свой напиток у барной стойки и бормочет:\n\n🎭 <i>{g_text(player, msg_boy, msg_girl)}</i>", parse_mode="HTML")


async def command_sosamba(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    today_str = str(date.today())
    
    res = supabase.table("uno_logs").select("*").eq("game_date", today_str).order("id").execute()
    
    if not res.data or len(res.data) == 0:
        await context.bot.send_message(chat_id=chat_id, text="🃏 Вокруг тишина. Сосамба взводится только после реального экшена за столом!", parse_mode="HTML")
        return

    clash = res.data[-1]
    sender_name = clash.get("sender_name")
    victim_name = clash.get("victim_name")
    mult = clash.get("multiplier", 1)

    if mult != -1:
        await context.bot.send_message(chat_id=chat_id, text="🙅‍♂️ Оппонент успешно перевёл стрелки, какая тут сосамба? Зализывай раны! 🐌", parse_mode="HTML")
        return

    # УЛЬТИМАТИВНЫЙ ЛЕНИВЫЙ ФИКС: Вытаскиваем реальные профили участников по их именам из лога
    db_sender = supabase.table("users").select("user_id").eq("first_name", sender_name).execute().data
    db_victim = supabase.table("users").select("user_id").eq("first_name", victim_name).execute().data
    
    sender_id = db_sender[0]["user_id"] if db_sender else None
    victim_id = db_victim[0]["user_id"] if db_victim else None

    # Проверяем причастность строго по железным цифровым ID Телеграма!
    if user.id != sender_id and user.id != victim_id:
        await context.bot.send_message(chat_id=chat_id, text="🙅‍♂️ Ты не причастен к этой разборке, право на глумление имеют только участники!", parse_mode="HTML")
        return

    player_res = supabase.table("users").select("*").eq("user_id", user.id).execute()
    player = player_res.data[0] if player_res.data and len(player_res.data) > 0 else {"gender": "boy"}
    safe_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")

    loser_res = supabase.table("users").select("pidor_weight").eq("first_name", sender_name).execute()
    is_karma_triple = False
    if loser_res.data and len(loser_res.data) > 0:
        if loser_res.data[0].get("pidor_weight", 100.0) >= 150.0:
            is_karma_triple = True

    if user.id == victim_id:
        if is_karma_triple:
            msg_boy = "<b>СОСАМБА, БРАТИК!</b> Хотел перевести на меня, но сам сожрал свой позор в тройном размере! Карма — вещь! 😂💣"
            msg_girl = "<b>СОСАМБА, МИЛАЯ!</b> Пыталась скинуть на меня клеймо, а в итоге сама улевела в тройной позор! Учись играть! 💅🔥"
        else:
            msg_boy = "<b>СОСАМБА, БРАТИК!</b> Хотел перевести на меня, но твоя пушка дала осечку и выдала тебе двойной рикошет по лбу! 😂 Оформляй досье!"
            msg_girl = "<b>СОСАМБА, МИЛАЯ!</b> Попытка интриги провалилась. Лови чистый рикошет обратно в своё досье! Отдыхай! 💅"
            
        await context.bot.send_message(chat_id=chat_id, text=f"🎪 <b>{safe_name}</b> триумфально указывает пальцем на поверженного оппонента:\n\n📢 {g_text(player, msg_boy, msg_girl)}", parse_mode="HTML")
    else:
        if is_karma_triple:
            msg_boy = "Сам себе оформил тотальную сосамбу в тройном размере... Карма — жесткая сука, пацаны. 💀"
            msg_girl = "Устроила кармический самоподрыв... Ловушка рандома уничтожила меня в тройном объёме. 🤦‍♀️"
        else:
            msg_boy = "Сам себе оформил сосамбу на рикошете... Хотел красиво перевести стрелки, а получил х2 в досье. Косяк. 💀"
            msg_girl = "Поймала собственный рикошет... Карта UNO порвалась прямо у меня в руках, лови удваивание. 🤦‍♀️"
            
        await context.bot.send_message(chat_id=chat_id, text=f"🤡 <b>{safe_name}</b> сокрушённо констатирует факт своего фиаско:\n\n👀 <i>{g_text(player, msg_boy, msg_girl)}</i>", parse_mode="HTML")

async def pizdec_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    today = date.today()
    today_str = str(today)

    if update.effective_chat.type == "private":
        await context.bot.send_message(chat_id=chat_id, text="❌ Протокол тотального пиздеца активируется только при свидетелях в групповом чате!")
        return

    # 1. Вытаскиваем живой профиль игрока из базы для гендерного автомата и чека весов
    all_users = get_users()
    active_users = [u for u in all_users if u.get("is_active", True)]
    player = next((u for u in active_users if u["user_id"] == user.id), None)

    if not player:
        await context.bot.send_message(chat_id=chat_id, text="❌ Ты даже не зарегистрирован в казино! Пиши <code>/register</code>", parse_mode="HTML")
        return

    # === 🕵️‍♂️ РАЗВЕДКА КАРМИЧЕСКИХ СТАТУСОВ ИГРОКА НА СЕГОДНЯ ===
    is_today_pidor = False
    is_uno_failed = False
    is_horrible_dice = False
    is_max_chance_leader = False

    # Условие A: Выпал ли человек сегодня Пидором дня?
    today_pidor_res = get_today_winner("pidor")
    if today_pidor_res and today_pidor_res["user_id"] == user.id:
        is_today_pidor = True

    # Условие B: НЕ смог ли перевести карту UNO (запись в логах с multiplier == -1)
    uno_fail_res = supabase.table("uno_logs").select("id").eq("game_date", today_str).eq("sender_name", user.first_name).eq("multiplier", 0).execute()
    if uno_fail_res.data and len(uno_fail_res.data) > 0:
        is_uno_failed = True

    # Условие C: Выпали паршивые кости? Проверяем дубли 1/1, 1/2 или 2/2 на этой неделе
    current_week_num = today.isocalendar()[1]
    db_dice_value = player.get("dice_count", 0) or 0
    last_dice_week = db_dice_value // 10
    current_attempts = db_dice_value % 10
    prev_balance = player.get("dice_start_balance", 0.0) or 0.0

    # Если игрок открутил оба кубика на ЭТОЙ неделе
    if last_dice_week == current_week_num and current_attempts == 2:
        # prev_balance == -40.0 означает, что первый кубик был равен 1 (Грань 1 -> -40 по балансу весов)
        # Наш сбалансированный шаг для кубика 1 равен просадке в -40.0, для кубика 2 равен -20.0
        # Чекаем комбинации: 1/1 (баланс улетел в -80), 1/2 или 2/2 (баланс просел ниже нуля)
        if prev_balance < 0:
            is_horrible_dice = True

    # Условие D: Имеет ли он максимальный позорный вес (шанс) в чате прямо сейчас?
    if active_users:
        max_pidor_weight_in_chat = max(u.get("pidor_weight", 100.0) for u in active_users)
        if player.get("pidor_weight", 100.0) >= max_pidor_weight_in_chat:
            is_max_chance_leader = True

    # === 🎰 ГЕНДЕРНО-ОРКЕСТРОВАННЫЙ ВЫВОД СТЕНЫ ПЛАЧА ===
    safe_name = user.first_name.replace("<", "&lt;").replace(">", "&gt;")
    
    # 💥 ВЕТКА 1: ДИНАМИЧЕСКИЙ ДВОЙНОЙ/ТРОЙНОЙ КОМБО-ПИЗДЕЦ (Полный разнос по пунктам!)
    if sum([is_today_pidor, is_uno_failed, is_horrible_dice, is_max_chance_leader]) >= 2:
        # Собираем индивидуальный список грехов игрока на сегодня
        pizdec_reasons = []
        if is_today_pidor:
            pizdec_reasons.append(" ├ 🤡 Официально заклеймён главным <b>Пидором дня</b>")
        if is_uno_failed:
            pizdec_reasons.append(" ├ 🃏 Позорно проебал карту UNO, поймав рикошет")
        if is_horrible_dice:
            pizdec_reasons.append(" ├ 🎲 Выбросил паршивые кости в кубиках кармы")
        if is_max_chance_leader:
            pizdec_reasons.append(" └ 🎯 Удерживает максимальный шанс на пидора в чате")

        joined_reasons = "\n".join(pizdec_reasons)

        # Сочные гендерные панчлайны под комбо-удар
        msg_boy = (
            f"попал в сингулярность тотального пиздеца! Карма устроила ему групповой расстрел, "
            f"парень уничтожен как личность за игровым столом! Крупье сочувственно наливает за счёт заведения. 💀💣🎰"
        )
        msg_girl = (
            f"попала в эпицентр космического пиздеца! Боги рандома устроили ей абсолютный разнос, "
            f"леди официально и громко негодует, требуя сжечь это казино к чертям! 🔥🎪"
        )

        # ДИНАМИЧЕСКОЕ ОПРЕДЕЛЕНИЕ МЕСТОИМЕНИЯ ДЛЯ ПАЦАНОВ И ДЕВЧОНОК
        gender_pronoun = g_text(player, "Так он ещё и", "Так она ещё и ")

        combo_text = (
            f"☢️ <b>УЛЬТРА-ПИЗДЕЦ ЗАФИКСИРОВАН! СИНГУЛЯРНОСТЬ БОЛИ!</b> ☢️\n\n"
            f"Мало того, что игрок <b>{safe_name}</b> умудрился собрать комбо-страйк неудачника:\n"
            f"{joined_reasons}\n\n"
            f"🎯 {gender_pronoun} {g_text(player, msg_boy, msg_girl)}"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=combo_text,
            parse_mode="HTML"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgUAAxkBAAERr4pqeX-dpAQpHvj3CZnAcPY0_UmGSQACgggAAjiksVVM5Vj4fvPn0z0E')
        return


    # 🎲 ВЕТКА 2: ПАРШИВЫЕ КОСТИ В КУБИКАХ СУДЬБЫ
    if is_horrible_dice:
        msg_boy = "смотрит на эти ебучие кубики кармы и проклинает этот день! Выбросил паршивые кости (1/1, 1/2 или 2/2) и намертво засадил свои проценты в болото! 🎲📉"
        msg_girl = "выкинула паршивые кости на этой неделе и изящно топает каблуком от злости! Её шансы на Пидорессу поднялись, леди у барной стойки дико негодует! 💔🎲"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎲 <b>ПРОТОКОЛ ПИЗДЕЦА: ЕБУЧИЕ КОСТИ!</b> 🎲\n\n🤡 <b>{safe_name}</b> {g_text(player, msg_boy, msg_girl)}",
            parse_mode="HTML"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAESGyNq4Ha80GhfCpNeS51OZF0-Syb24QAC-gADq3tGJJ4tNCyp1pByPQQ')
        return

    # 🤡 ВЕТКА 3: СЕГОДНЯШНИЙ ПИДОР ДНЯ
    if is_today_pidor:
        msg_boy = "негодует от полученного статуса Пидора дня на сегодня! Клеймо позора жжёт ему лоб, Салун глумится во весь голос! 🎪🤡"
        msg_girl = "негодует от утреннего вердикта Крупье! Статус Пидорессы дня обрушил её настроение, леди требует перезагрузить этот чертов автомат! 😡🔥"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🤡 <b>ПРОТОКОЛ ПИЗДЕЦА: СЕГОДНЯШНИЙ ПОЗОР!</b> 🤡\n\n👉 <b>{safe_name}</b> {g_text(player, msg_boy, msg_girl)}",
            parse_mode="HTML"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAESGx1q4HRbOozCsnD1qAF-3XBAUE71wAACVxsAApox0EqHiM2ENpsl9D0E')
        return

    # 🎯 ВЕТКА 4: МАКСИМАЛЬНЫЙ ШАНС СТАТЬ ПИДОРОМ (ЛИДЕР СЕТКИ ПОЗОРНЫХ ВЕСОВ)
    if is_max_chance_leader:
        msg_boy = "прямо сейчас сидит на пороховой бочке! У него максимальный шанс на Пидора в чате на текущий момент, парень люто негодует! 🌋🚨"
        msg_girl = "возглавляет позорный рейтинг шансов на завтрашнее утро! Её проценты взлетели в топ, прекрасная леди за игровым столом дико паникует и негодует! 🚨"
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🚨 <b>ПРОТОКОЛ ПИЗДЕЦА: ФАВОРИТ КЛЕЙМА!</b> 🚨\n\n👀 Наш парень/леди с максимальным шансом на пидора на текущий момент негодует:\n👉 <b>{safe_name}</b> {g_text(player, msg_boy, msg_girl)}",
            parse_mode="HTML"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAESGx9q4HV0YjRZMVJdve5jX0pXLGQfiQAC7gADxSPMB-w67DIZkjqMPQQ')
        return

    # === 😎 ВЕТКА 5: БЕЛАЯ КОСТЬ ИЛИ ПРИНУДИТЕЛЬНОЕ УНИЖЕНИЕ МАЗУРИКОВ-ВЕЗУНЧИКОВ ===
    # Проверяем, не является ли этот нытик сегодняшним Красавчиком дня
    today_krasavchik_res = get_today_winner("krasavchik")
    is_today_krasavchik = False
    if today_krasavchik_res and today_krasavchik_res["user_id"] == user.id:
        is_today_krasavchik = True

    # 💎 СУПЕР-ВЕТКА 5.А: ЕСЛИ ЭТО ОБНАГЛЕВШИЙ КРАСАВЧИК ДНЯ 💎
    if is_today_krasavchik:
        msg_kras_boy = (
            "ты чё, вообще ахуел на столько?! У тебя ни одного позора, кости в порядке, "
            "так ты ещё и официальный <b>КРАСАВЧИК ДНЯ</b> сегодня! 👑 Сними корону, не жми "
            "кнопку для бедолаг и скройся с глаз Крупье, пока пацаны тебе лицо не начистили! 🥂🔥🎰"
        )
        msg_kras_girl = (
            "вы чё, вообще ахуели на столько, милая?! Ни единого косяка в досье, проценты чистые, "
            "так вы ещё и официальная <b>КРАСАВИЦА ДНЯ</b> сегодня! 👑 Корона чата на месте, "
            "хватит отжимать кнопки у местных неудачников казино, идите праздновать! ✨💅🥂"
        )
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"👑 <b>ОТКАЗ В ИСПУСКАНЬЕ НЫТЬЯ ДЛЯ ЭЛИТЫ!</b> 👑\n\nЭй, <b>{safe_name}</b>, {g_text(player, msg_kras_boy, msg_kras_girl)}",
            parse_mode="HTML"
        )
        await context.bot.send_sticker(chat_id=chat_id, sticker='CAACAgIAAxkBAAESGyVq4HrsCHg7IpSVnDOWNC0J5pjuDQACHgADEEN3JZQnNINQ0cI2PQQ')
        return

    # ⚪️ СТАНДАРТНАЯ ВЕТКА 5.Б: ЧИСТЫЙ МИРНЫЙ ВЕЗУНЧИК
    msg_lucky_boy = "Ты какого хера тут сопли развёл? Ты чист перед законом, проценты кубов в порядке, утреннего клейма нет. Скройся с глаз Крупье, пока фортуна не передумала! 🥂"
    msg_lucky_girl = "У вас всё идеально, милая! Никаких позоров, проценты в полном порядке (как минимум не в топе). Оставьте эту стену плача для местных неудачников Казиныча! ✨💅"
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=f"😎 <b>ОТКАЗ В ИСПУСКАНЬЕ НЫТЬЯ!</b> 😎\n\nЭй, <b>{safe_name}</b>! {g_text(player, msg_lucky_boy, msg_lucky_girl)}",
        parse_mode="HTML"
    )

# ---------------- ЗАПУСК (ВЕБХУК) ----------------

async def main():
    # Собираем приложение бота
    app = Application.builder().token(TOKEN).build()
    
    # ИСПРАВЛЕНО: Ровный отступ для проверки планировщика
    if app.job_queue is None:
        print("Критическая ошибка: Планировщик задач не инициализирован. Проверьте requirements.txt")
        
    # === 🛡️ АКТИВАЦИЯ ТИТАНОВОГО КУПОЛА КАЗИНО ОТ АДМИНСКОГО СПАМА НИКИТЫ ===
    # Привязываем мидлварь к рождённому приложению в приоритетную группу -1!
    app.add_handler(TypeHandler(Update, global_anti_spam_middleware), group=-1)
        
    # Все команды теперь реагируют СТРОГО на живой пользовательский текст!
    app.add_handler(CommandHandler("start", help_command, filters=filters.TEXT))
    app.add_handler(CommandHandler("help", help_command, filters=filters.TEXT))
    app.add_handler(CommandHandler("register", register, filters=filters.TEXT))
    app.add_handler(CommandHandler("unreg", unreg, filters=filters.TEXT))
    app.add_handler(CommandHandler("reset", reset_stats, filters=filters.TEXT))
    app.add_handler(CommandHandler("pidor", pidor, filters=filters.TEXT))
    app.add_handler(CommandHandler("run", run_command, filters=filters.TEXT))
    app.add_handler(CommandHandler("stats", stats, filters=filters.TEXT))
    app.add_handler(CommandHandler("mimic", mimic, filters=filters.TEXT))
    app.add_handler(CommandHandler("procents", procents_command, filters=filters.TEXT))
    app.add_handler(CommandHandler("switch", switch, filters=filters.TEXT))
    app.add_handler(CommandHandler("records", records, filters=filters.TEXT))
    app.add_handler(CommandHandler("mystats", my_stats, filters=filters.TEXT))
    app.add_handler(CommandHandler("backup", manual_backup, filters=filters.TEXT))
    app.add_handler(CommandHandler("dice", dice_command, filters=filters.TEXT))
    app.add_handler(CommandHandler("duel", duel, filters=filters.TEXT))
    app.add_handler(CommandHandler("unostats", uno_stats, filters=filters.TEXT))
    app.add_handler(CommandHandler("boy", set_gender_boy, filters=filters.TEXT))
    app.add_handler(CommandHandler("girl", set_gender_girl, filters=filters.TEXT))
    app.add_handler(CommandHandler("notbed", command_notbed, filters=filters.TEXT))
    app.add_handler(CommandHandler("sosamba", command_sosamba, filters=filters.TEXT))
    app.add_handler(CommandHandler("ok", admin_ok, filters=filters.TEXT))
    app.add_handler(CommandHandler("nook", admin_nook, filters=filters.TEXT))
    app.add_handler(CommandHandler("pizdec", pizdec_command, filters=filters.TEXT))


    if RENDER_URL:
        print("Бот запускается в режиме Webhook на Render...")
        PORT = int(os.getenv("PORT", 10000))
        
        # ЖЕЛЕЗНЫЙ БЭКЕНД-ФИКС РОМЫ: Инициализируем приложение. 
        # Метод start() сам правильно и безопасно поднимет JobQueue под капотом!
        await app.initialize()
        await app.start()
        
        # Запускаем сам вебхук
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
        print("Вебхук успешно запущен! Планировщик активен.")
        
        from asyncio import Event
        await Event().wait()
    else:
        print("Бот запущен локально в режиме Polling!")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        from asyncio import Event
        await Event().wait()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
