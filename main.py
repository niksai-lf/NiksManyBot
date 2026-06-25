import logging
import sqlite3
import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, BotCommand

# --- НАСТРОЙКИ БОТА ---
API_TOKEN = '7675571104:AAFGqVBRtg8JNuEwXL7Z1tNrpUw9yMEuDk4'
MAIN_ADMIN_ID = 6266598653
ADMIN_PAYOUTS_CHANNEL = -1004391177606
ADMIN_REVIEWS_CHANNEL = -1004414700976
MANDATORY_CHANNEL = "@NiksMany"
TECH_SUPPORT = "@dskup"
MIN_WITHDRAW = 0.33

# --- ФОТОГРАФИИ (FILE_ID) ---
# Отправь боту фото со своего админ-аккаунта, скопируй ID, который он выдаст, и вставь сюда:
IMG_MAIN = 'AgACAgIAAxkBAAIFrGo9dHbmToheF204Rd3GAqnlkES_AAIEF2sbb1PYSYZqYwq5MCvxAQADAgADeQADPAQ'
IMG_ADMIN = 'AgACAgIAAxkBAAIFqGo9dFZ3O4MzScWJ49gHVRgHam2HAAJ4Gmsbb1PYSdiJjxI6dypyAQADAgADdwADPAQ'
IMG_LANG = 'AgACAgIAAxkBAAIFomo9c88YKsdeu3g4tfWC5-gVIE7XAAIfHGsb4ETpSV0XFrq0C-mVAQADAgADdwADPAQ'
IMG_REF = 'AgACAgIAAxkBAAIFoGo9c8j_lJavfabyvf5ktKaMOSeNAAIgHGsb4ETpSXcv0Lrs0NEVAQADAgADdwADPAQ'
IMG_WITHDRAW = 'AgACAgIAAxkBAAIFnmo9c8A21OtOQ23_foEhFmGHRKyyAAIhHGsb4ETpSavUl5V8cvfdAQADAgADdwADPAQ'
IMG_TASKS = 'AgACAgIAAxkBAAIFnGo9c7yXgvflzHM77u76vBKrIIARAAIiHGsb4ETpSXcTEqW61q_oAQADAgADdwADPAQ'
IMG_PROFILE = 'AgACAgIAAxkBAAIFmGo9c6moGDRgBYA1NlK9g4FMz660AAL3Hmsb4ETpSaw6Mg6pa8xrAQADAgADdwADPAQ' # Сюда ID для картинки профиля
IMG_RULES = 'AgACAgIAAxkBAAIFmmo9c7eUNdHHvTpmqwQiiuY_328iAAL4Hmsb4ETpSabOgpYc2gNbAQADAgADdwADPAQ'   # Сюда ID для картинки правил

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode='HTML')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AdminStates(StatesGroup):
    ban_user = State()
    unban_user = State()
    add_admin = State()
    rem_admin = State()
    add_balance_id = State()
    add_balance_amount = State()
    rem_balance_id = State()
    rem_balance_amount = State()
    broadcast = State()
    task_reward = State()
    task_label = State()
    task_links = State()
    rem_task = State()

class UserStates(StatesGroup):
    withdraw_amount = State()
    writing_review = State()

def init_db():
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, lang TEXT DEFAULT 'ru', balance REAL DEFAULT 0.0, 
                  ref_id INTEGER, is_banned INTEGER DEFAULT 0, mandatory_sub INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (task_id INTEGER PRIMARY KEY AUTOINCREMENT, reward REAL, channels TEXT, label TEXT DEFAULT '')''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_tasks (user_id INTEGER, task_id INTEGER)''')
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MAIN_ADMIN_ID,))
    conn.commit()
    conn.close()

init_db()

async def set_default_commands(dp):
    await dp.bot.set_my_commands([
        BotCommand("start", "Перезапустить бота / Главное меню")
    ])

LANGS = {
    'ru': {
        'btn_profile': "👤 Мой профиль", 'btn_tasks': "🎯 Задания", 'btn_withdraw': "💸 Вывод средств", 'btn_ref': "🤝 Партнерам", 'btn_rules': "📜 Правила", 'btn_info': "ℹ️ О нас", 'btn_lang': "🌍 Язык", 'btn_admin': "⚙️ Админ-панель",
        'btn_details': "📄 Подробней",
        'welcome': "<blockquote>🌴 <b>Добро пожаловать в NiksMany!</b></blockquote>\n<i>Выберите действие в меню ниже 👇</i>",
        'sub_task': "<blockquote>🚨 <b>Доступ ограничен!</b></blockquote>\n<i>Для использования бота подпишитесь на наш официальный канал.</i>\n\n🎁 За подписку вы сразу получите <code>0.01 USDT</code>.",
        'check_sub': "✅ Проверить", 'sub_err': "❌ Вы не подписались! Подпишитесь, чтобы начать зарабатывать.", 'sub_ok': "🎉 Отлично! Вам начислено бонусное вознаграждение.",
        'unsub_pen': "<blockquote>⚠️ <b>Штраф!</b></blockquote>\n<i>Вы отписались от канала-спонсора.</i>\nС баланса списано 0.01 USDT. Подпишитесь снова!",
        'profile': "<blockquote>🪪 <b>КАБИНЕТ ПОЛЬЗОВАТЕЛЯ</b></blockquote>\n━━━━━━━━━━━━━━━━━━\n👤 <i>Пользователь:</i> @{username}\n🆔 <i>Ваш ID:</i> <code>{id}</code>\n\n📊 <i>Статус:</i> <b>{status}</b>\n🎯 <i>Выполнено заданий:</i> <b>{tasks}</b>\n\n💎 <b>Баланс:</b> <code>{balance} USDT</code>\n━━━━━━━━━━━━━━━━━━",
        'rules': "<blockquote>📜 <b>ПРАВИЛА И ИНФОРМАЦИЯ:</b></blockquote>\n\n1️⃣ <b>Минимальный вывод:</b> 0.33 USDT.\n2️⃣ <b>Штрафы:</b> Бот строго следит за вашими подписками. Если вы отпишетесь от спонсора, бот автоматически спишет награду с баланса!\n3️⃣ <b>Рейтинговая система:</b> Ваш ранг зависит от количества выполненных заданий:\n  🥉 Бронза: 1 задание\n  🥈 Сильвер: 2-3 задания\n  🥇 Золото: 4-6 заданий\n  💠 Платина: 7+ заданий\n4️⃣ <b>Рефералы:</b> Приглашайте друзей! Как только ваш друг выполнит 2 задания и достигнет ранга Сильвер, вы получите 0.03 USDT.",
        'info': "<blockquote>🏢 <b>О КОМПАНИИ И НАШЕМ ТРАФИКЕ:</b></blockquote>\n\nБот <b>NiksMany</b> разработан передовой IT-студией <i>NM Global Technologies</i>. Мы являемся лидерами по привлечению целевой аудитории.\n\n🌐 <b>Источники нашего трафика:</b>\n• Telegram\n• Instagram\n• TikTok\n• YouTube\n\n🎯 <b>Основные тематики и ниши аудитории:</b>\n🔹 Криптовалюта и NFT-проекты\n🔹 Игровая индустрия\n🔹 Telegram Stars\n🔹 Спортивные направления\n🔹 Гемблинг и беттинг (лудо-аудитория)\n🔹 Схемы для легкого заработка в сети\n🔹 Разработка скриптов и ботов\n\n🤝 <b>Сотрудничество:</b>\nЕсли вы хотите заказать качественный трафик, добавить свой канал в бота или задать вопрос, обращайтесь в нашу поддержку!",
        'tech_sup_btn': "👨‍💻 Тех. Поддержка",
        'all_tasks': "<blockquote>📋 <b>Доступные задания:</b></blockquote>\n<i>Выберите задание для выполнения:</i>",
        'withdraw_menu': "<blockquote>💸 <b>УПРАВЛЕНИЕ БАЛАНСОМ</b></blockquote>\n\n💎 <i>Доступно для вывода:</i> <code>{bal} USDT</code>\n\nВыберите способ вывода:",
        'with_max_btn': "💰 Вывести всё (MAX)", 'with_man_btn': "✍️ Ввести сумму вручную",
        'withdraw_req': "<blockquote>💰 <i>Введите сумму для вывода вручную (Мин. 0.33 USDT):</i></blockquote>\nИли выберите действие в меню для отмены.", 'with_err_num': "❌ Введите корректное число!", 'with_err_min': "❌ Минимальная сумма вывода 0.33 USDT", 'with_err_bal': "❌ Недостаточно средств на балансе!", 'with_ok': "✅ Заявка создана! Ожидайте чек.",
        'ref_text': "<blockquote>🤝 <b>ПАРТНЕРСКАЯ ПРОГРАММА</b></blockquote>\n\n<i>Приглашайте друзей и получайте бонус!</i>\nЗа каждого друга, достигшего ранга 🥈 Сильвер (2 задания), вы получаете <b>0.03 USDT</b>.\n\n🔗 <b>Ваша ссылка:</b>\n<code>{link}</code>\n\n👥 <i>Приглашено:</i> <b>{count} чел.</b>",
        'rev_ask': "🎁 Ваш чек на выплату: {link}\n\n<i>Хотите оставить отзыв о нашей работе? Ваш отзыв будет опубликован в официальном канале!</i>", 'rev_yes': "✅ Да, хочу", 'rev_no': "❌ Нет", 'rev_write': "✍️ Напишите ваш отзыв одним сообщением (можно прикрепить фото/скриншот):", 'rev_thanks': "✅ Спасибо! Ваш отзыв направлен на публикацию."
    },
    'en': {
        'btn_profile': "👤 My Profile", 'btn_tasks': "🎯 Tasks", 'btn_withdraw': "💸 Withdraw", 'btn_ref': "🤝 Referrals", 'btn_rules': "📜 Rules", 'btn_info': "ℹ️ About Us", 'btn_lang': "🌍 Language", 'btn_admin': "⚙️ Admin-panel",
        'btn_details': "📄 Details",
        'welcome': "<blockquote>🌴 <b>Welcome to NiksMany!</b></blockquote>\n<i>Choose an action in the menu below 👇</i>",
        'sub_task': "<blockquote>🚨 <b>Access restricted!</b></blockquote>\n<i>Please subscribe to our official channel.</i>\n\n🎁 You get <code>0.01 USDT</code> immediately.",
        'check_sub': "✅ Verify", 'sub_err': "❌ Not subscribed! Subscribe to earn.", 'sub_ok': "🎉 Reward credited.",
        'unsub_pen': "<blockquote>⚠️ <b>Penalty!</b></blockquote>\n<i>You unsubscribed.</i>\n0.01 USDT deducted.",
        'profile': "<blockquote>🪪 <b>USER PROFILE</b></blockquote>\n👤 <i>User:</i> @{username}\n🆔 <i>ID:</i> <code>{id}</code>\n📊 <i>Rank:</i> <b>{status}</b>\n🎯 <i>Tasks completed:</i> <b>{tasks}</b>\n💎 <b>Balance:</b> <code>{balance} USDT</code>",
        'rules': "<blockquote>📜 <b>RULES:</b></blockquote>\n1️⃣ <b>Min withdraw:</b> 0.33 USDT.\n2️⃣ <b>Penalty:</b> Unsubscribing causes a penalty!\n3️⃣ <b>Ranks:</b>\n  🥉 Bronze: 1 task\n  🥈 Silver: 2-3 tasks\n  🥇 Gold: 4-6 tasks\n  💠 Platinum: 7+ tasks\n4️⃣ <b>Referrals:</b> 0.03 USDT per friend reaching Silver.",
        'info': "<blockquote>🏢 <b>ABOUT US & OUR TRAFFIC:</b></blockquote>\nDeveloped by NM Global Technologies.\n\n🌐 <b>Traffic Sources:</b>\n• Telegram, Instagram, TikTok, YouTube\n\n🎯 <b>Main Niches:</b>\n🔹 Crypto & NFT\n🔹 Gaming Industry\n🔹 Telegram Stars\n🔹 Sports\n🔹 Gambling & Betting\n🔹 Easy Online Earnings\n🔹 Script & Bot Development\n\n🤝 <b>Cooperation:</b> Contact support to buy traffic!", 'tech_sup_btn': "👨‍💻 Support",
        'all_tasks': "<blockquote>📋 <b>Available Tasks:</b></blockquote>",
        'withdraw_menu': "<blockquote>💸 <b>WITHDRAW</b></blockquote>\n💎 <i>Available:</i> <code>{bal} USDT</code>\nSelect method:", 'with_max_btn': "💰 Max Withdraw", 'with_man_btn': "✍️ Manual Amount",
        'withdraw_req': "<blockquote>💰 <i>Enter amount (Min. 0.33 USDT):</i></blockquote>", 'with_err_num': "❌ Invalid number!", 'with_err_min': "❌ Minimum is 0.33 USDT", 'with_err_bal': "❌ Insufficient funds!", 'with_ok': "✅ Request created!",
        'ref_text': "<blockquote>🤝 <b>REFERRAL PROGRAM</b></blockquote>\nInvite friends and get <b>0.03 USDT</b>!\n\n🔗 <b>Your link:</b>\n<code>{link}</code>\n👥 <i>Invited:</i> <b>{count} users</b>",
        'rev_ask': "🎁 Receipt: {link}\n<i>Leave a review?</i>", 'rev_yes': "✅ Yes", 'rev_no': "❌ No", 'rev_write': "✍️ Write review:", 'rev_thanks': "✅ Sent!"
    },
    'uk': {
        'btn_profile': "👤 Мій профіль", 'btn_tasks': "🎯 Завдання", 'btn_withdraw': "💸 Виведення", 'btn_ref': "🤝 Партнерам", 'btn_rules': "📜 Правила", 'btn_info': "ℹ️ Про нас", 'btn_lang': "🌍 Мова", 'btn_admin': "⚙️ Адмін-панель",
        'btn_details': "📄 Детальніше",
        'welcome': "<blockquote>🌴 <b>Ласкаво просимо до NiksMany!</b></blockquote>\n<i>Оберіть дію в меню нижче 👇</i>",
        'sub_task': "<blockquote>🚨 <b>Доступ обмежено!</b></blockquote>\n<i>Підпишіться на наш канал.</i>\n\n🎁 За підписку ви отримаєте <code>0.01 USDT</code>.",
        'check_sub': "✅ Перевірити", 'sub_err': "❌ Ви не підписалися!", 'sub_ok': "🎉 Чудово! Нагороду зараховано.",
        'unsub_pen': "<blockquote>⚠️ <b>Штраф!</b></blockquote>\n<i>Ви відписалися.</i>\nСписано 0.01 USDT.",
        'profile': "<blockquote>🪪 <b>КАБІНЕТ КОРИСТУВАЧА</b></blockquote>\n👤 <i>Користувач:</i> @{username}\n🆔 <i>ID:</i> <code>{id}</code>\n📊 <i>Ранг:</i> <b>{status}</b>\n🎯 <i>Виконано:</i> <b>{tasks}</b>\n💎 <b>Баланс:</b> <code>{balance} USDT</code>",
        'rules': "<blockquote>📜 <b>ПРАВИЛА:</b></blockquote>\n1️⃣ <b>Мін. вивід:</b> 0.33 USDT.\n2️⃣ <b>Штрафи:</b> За відписку списується баланс!\n3️⃣ <b>Ранг:</b>\n  🥉 Бронза: 1\n  🥈 Сільвер: 2-3\n  🥇 Золото: 4-6\n  💠 Платина: 7+\n4️⃣ <b>Реферали:</b> 0.03 USDT за друга (Сільвер).",
        'info': "<blockquote>🏢 <b>ПРО КОМПАНІЮ ТА НАШ ТРАФІК:</b></blockquote>\nРозробка NM Global Technologies.\n\n🌐 <b>Джерела трафіку:</b>\n• Telegram, Instagram, TikTok, YouTube\n\n🎯 <b>Основні тематики:</b>\n🔹 Криптовалюта та NFT\n🔹 Ігрова індустрія\n🔹 Telegram Stars\n🔹 Спорт\n🔹 Гемблінг та беттінг\n🔹 Схеми легкого заробітку\n🔹 Розробка скриптів та ботів\n\n🤝 <b>Співпраця:</b> Звертайтесь у підтримку!", 'tech_sup_btn': "👨‍💻 Підтримка",
        'all_tasks': "<blockquote>📋 <b>Доступні завдання:</b></blockquote>",
        'withdraw_menu': "<blockquote>💸 <b>ВИВЕДЕННЯ</b></blockquote>\n💎 <i>Доступно:</i> <code>{bal} USDT</code>", 'with_max_btn': "💰 Вивести все", 'with_man_btn': "✍️ Ввести суму вручну",
        'withdraw_req': "<blockquote>💰 <i>Сума виводу (Мін 0.33 USDT):</i></blockquote>", 'with_err_num': "❌ Введіть число!", 'with_err_min': "❌ Мін 0.33 USDT", 'with_err_bal': "❌ Недостатньо коштів!", 'with_ok': "✅ Заявка створена!",
        'ref_text': "<blockquote>🤝 <b>ПАРТНЕРСЬКА ПРОГРАМА</b></blockquote>\nЗапрошуйте друзів!\n🔗 <b>Посилання:</b>\n<code>{link}</code>\n👥 <i>Запрошено:</i> <b>{count} чол.</b>",
        'rev_ask': "🎁 Ваш чек: {link}\n<i>Відгук?</i>", 'rev_yes': "✅ Так", 'rev_no': "❌ Ні", 'rev_write': "✍️ Відгук:", 'rev_thanks': "✅ Дякуємо!"
    },
    'de': {
        'btn_profile': "👤 Mein Profil", 'btn_tasks': "🎯 Aufgaben", 'btn_withdraw': "💸 Auszahlung", 'btn_ref': "🤝 Partner", 'btn_rules': "📜 Regeln", 'btn_info': "ℹ️ Über uns", 'btn_lang': "🌍 Sprache", 'btn_admin': "⚙️ Admin-panel",
        'btn_details': "📄 Details",
        'welcome': "<blockquote>🌴 <b>Willkommen bei NiksMany!</b></blockquote>\n<i>Aktion wählen 👇</i>",
        'sub_task': "<blockquote>🚨 <b>Zugang eingeschränkt!</b></blockquote>\n<i>Bitte abonnieren Sie unseren Kanal.</i>\n🎁 <code>0.01 USDT</code> Belohnung.",
        'check_sub': "✅ Prüfen", 'sub_err': "❌ Nicht abonniert!", 'sub_ok': "🎉 Belohnung erhalten.",
        'unsub_pen': "<blockquote>⚠️ <b>Strafe!</b></blockquote>\n0.01 USDT abgezogen.",
        'profile': "<blockquote>🪪 <b>PROFIL</b></blockquote>\n👤 <i>Benutzer:</i> @{username}\n🆔 <i>ID:</i> <code>{id}</code>\n📊 <i>Rang:</i> <b>{status}</b>\n🎯 <i>Aufgaben:</i> <b>{tasks}</b>\n💎 <b>Guthaben:</b> <code>{balance} USDT</code>",
        'rules': "<blockquote>📜 <b>REGELN:</b></blockquote>\n1️⃣ <b>Min Auszahlung:</b> 0.33 USDT.\n4️⃣ <b>Partner:</b> 0.03 USDT pro Freund (Silber).",
        'info': "<blockquote>🏢 <b>ÜBER UNS:</b></blockquote>\nNM Global Technologies. Traffic: Telegram, Instagram, TikTok. Nischen: Crypto, Gaming, Betting, NFT.", 'tech_sup_btn': "👨‍💻 Support",
        'all_tasks': "<blockquote>📋 <b>Aufgaben:</b></blockquote>",
        'withdraw_menu': "<blockquote>💸 <b>AUSZAHLUNG</b></blockquote>\n💎 <i>Verfügbar:</i> <code>{bal} USDT</code>", 'with_max_btn': "💰 Max Auszahlung", 'with_man_btn': "✍️ Manuell",
        'withdraw_req': "<blockquote>💰 <i>Betrag (Min 0.33):</i></blockquote>", 'with_err_num': "❌ Ungültig!", 'with_err_min': "❌ Min 0.33", 'with_err_bal': "❌ Zu wenig Geld!", 'with_ok': "✅ Gesendet!",
        'ref_text': "<blockquote>🤝 <b>PARTNER</b></blockquote>\n🔗 <b>Link:</b>\n<code>{link}</code>\n👥 <i>Eingeladen:</i> <b>{count}</b>",
        'rev_ask': "🎁 Beleg: {link}\n<i>Bewertung?</i>", 'rev_yes': "✅ Ja", 'rev_no': "❌ Nein", 'rev_write': "✍️ Text:", 'rev_thanks': "✅ Danke!"
    },
    'pl': {
        'btn_profile': "👤 Mój profil", 'btn_tasks': "🎯 Zadania", 'btn_withdraw': "💸 Wypłata", 'btn_ref': "🤝 Partnerzy", 'btn_rules': "📜 Zasady", 'btn_info': "ℹ️ O nas", 'btn_lang': "🌍 Język", 'btn_admin': "⚙️ Panel Admina",
        'btn_details': "📄 Szczegóły",
        'welcome': "<blockquote>🌴 <b>Witamy w NiksMany!</b></blockquote>\n<i>Wybierz akcję 👇</i>",
        'sub_task': "<blockquote>🚨 <b>Brak dostępu!</b></blockquote>\n<i>Zasubskrybuj kanał.</i>\n🎁 <code>0.01 USDT</code>.",
        'check_sub': "✅ Sprawdź", 'sub_err': "❌ Brak subskrypcji!", 'sub_ok': "🎉 Nagroda!",
        'unsub_pen': "<blockquote>⚠️ <b>Kara!</b></blockquote>\nOdjęto 0.01 USDT.",
        'profile': "<blockquote>🪪 <b>PROFIL</b></blockquote>\n👤 <i>User:</i> @{username}\n🆔 <i>ID:</i> <code>{id}</code>\n📊 <i>Ranga:</i> <b>{status}</b>\n🎯 <i>Zadania:</i> <b>{tasks}</b>\n💎 <b>Saldo:</b> <code>{balance} USDT</code>",
        'rules': "<blockquote>📜 <b>ZASADY:</b></blockquote>\n1️⃣ <b>Min wypłata:</b> 0.33 USDT.\n4️⃣ <b>Poleceni:</b> 0.03 USDT (Srebro).",
        'info': "<blockquote>🏢 <b>O NAS:</b></blockquote>\nNM Global Technologies. Ruch z Telegram, TikTok. Nisze: Crypto, NFT, Gaming.", 'tech_sup_btn': "👨‍💻 Wsparcie",
        'all_tasks': "<blockquote>📋 <b>Zadania:</b></blockquote>",
        'withdraw_menu': "<blockquote>💸 <b>WYPŁATA</b></blockquote>\n💎 <i>Dostępne:</i> <code>{bal} USDT</code>", 'with_max_btn': "💰 Max", 'with_man_btn': "✍️ Ręcznie",
        'withdraw_req': "<blockquote>💰 <i>Kwota (Min 0.33):</i></blockquote>", 'with_err_num': "❌ Błąd!", 'with_err_min': "❌ Min 0.33", 'with_err_bal': "❌ Brak środków!", 'with_ok': "✅ Wysłano!",
        'ref_text': "<blockquote>🤝 <b>PARTNERZY</b></blockquote>\n🔗 <b>Link:</b>\n<code>{link}</code>\n👥 <i>Poleceni:</i> <b>{count}</b>",
        'rev_ask': "🎁 Paragon: {link}\n<i>Opinia?</i>", 'rev_yes': "✅ Tak", 'rev_no': "❌ Nie", 'rev_write': "✍️ Napisz:", 'rev_thanks': "✅ Dzięki!"
    },
    'uz': {
        'btn_profile': "👤 Profilim", 'btn_tasks': "🎯 Vazifalar", 'btn_withdraw': "💸 Yechib olish", 'btn_ref': "🤝 Hamkorlar", 'btn_rules': "📜 Qoidalar", 'btn_info': "ℹ️ Biz haqimizda", 'btn_lang': "🌍 Til", 'btn_admin': "⚙️ Admin-panel",
        'btn_details': "📄 Batafsil",
        'welcome': "<blockquote>🌴 <b>NiksMany-ga xush kelibsiz!</b></blockquote>\n<i>Harakatni tanlang 👇</i>",
        'sub_task': "<blockquote>🚨 <b>Kirish cheklangan!</b></blockquote>\n<i>Kanalimizga obuna bo'ling.</i>\n🎁 <code>0.01 USDT</code> olasiz.",
        'check_sub': "✅ Tekshirish", 'sub_err': "❌ Obuna bo'lmadingiz!", 'sub_ok': "🎉 Mukofot!",
        'unsub_pen': "<blockquote>⚠️ <b>Jarima!</b></blockquote>\n0.01 USDT yechildi.",
        'profile': "<blockquote>🪪 <b>PROFIL</b></blockquote>\n👤 <i>Foydalanuvchi:</i> @{username}\n🆔 <i>ID:</i> <code>{id}</code>\n📊 <i>Daraja:</i> <b>{status}</b>\n🎯 <i>Vazifalar:</i> <b>{tasks}</b>\n💎 <b>Balans:</b> <code>{balance} USDT</code>",
        'rules': "<blockquote>📜 <b>QOIDALAR:</b></blockquote>\n1️⃣ <b>Min yechish:</b> 0.33 USDT.\n4️⃣ <b>Hamkorlar:</b> 0.03 USDT.",
        'info': "<blockquote>🏢 <b>BIZ HAQIMIZDA:</b></blockquote>\nNM Global Technologies. Trafik: Telegram, TikTok. Crypto, NFT.", 'tech_sup_btn': "👨‍💻 Yordam",
        'all_tasks': "<blockquote>📋 <b>Vazifalar:</b></blockquote>",
        'withdraw_menu': "<blockquote>💸 <b>YECHISH</b></blockquote>\n💎 <i>Mavjud:</i> <code>{bal} USDT</code>", 'with_max_btn': "💰 Hammasi", 'with_man_btn': "✍️ Qo'lda",
        'withdraw_req': "<blockquote>💰 <i>Summa (Min 0.33):</i></blockquote>", 'with_err_num': "❌ Xato!", 'with_err_min': "❌ Min 0.33", 'with_err_bal': "❌ Mablag' yetarli emas!", 'with_ok': "✅ Yuborildi!",
        'ref_text': "<blockquote>🤝 <b>HAMKORLAR</b></blockquote>\n🔗 <b>Havola:</b>\n<code>{link}</code>\n👥 <i>Taklif qilingan:</i> <b>{count}</b>",
        'rev_ask': "🎁 Chek: {link}\n<i>Fikr?</i>", 'rev_yes': "✅ Ha", 'rev_no': "❌ Yo'q", 'rev_write': "✍️ Yozing:", 'rev_thanks': "✅ Rahmat!"
    }
}

def get_txt(uid, key, **kwargs):
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id = ?", (uid,))
    res = c.fetchone()
    conn.close()
    lang = res[0] if res and res[0] in LANGS else 'ru'
    return LANGS[lang].get(key, LANGS['ru'].get(key, "")).format(**kwargs)

def get_action_by_text(text):
    if not text: return None
    for lang_code, phrases in LANGS.items():
        for key, phrase in phrases.items():
            if text == phrase: return key
    return None

def parse_channels(channels_str):
    result = []
    for raw in channels_str.split(','):
        raw = raw.strip()
        if not raw: continue
        if '|' in raw:
            target, link = raw.split('|', 1)
            result.append((target.strip(), link.strip()))
        else:
            link = raw
            if "t.me/+" in link: target = link
            elif "t.me/" in link: target = "@" + link.split("t.me/")[1].strip()
            else: target = link
            result.append((target, link))
    return result

async def is_admin(uid):
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM admins WHERE user_id = ?", (uid,))
    res = c.fetchone()
    conn.close()
    return res is not None

async def check_ban(uid):
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id = ?", (uid,))
    res = c.fetchone()
    conn.close()
    return res and res[0] == 1

async def enforce_mandatory_sub(uid):
    try:
        member = await bot.get_chat_member(MANDATORY_CHANNEL, uid)
        if member.status not in ['member', 'administrator', 'creator']:
            conn = sqlite3.connect('niksmany.db')
            c = conn.cursor()
            c.execute("SELECT mandatory_sub FROM users WHERE user_id = ?", (uid,))
            msub = c.fetchone()
            if msub and msub[0] == 1:
                c.execute("UPDATE users SET mandatory_sub = 0, balance = balance - 0.01 WHERE user_id = ?", (uid,))
                conn.commit()
                await bot.send_message(uid, get_txt(uid, 'unsub_pen'))
            conn.close()
            return False
        return True
    except:
        return False

async def verify_task_subscriptions(uid):
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT t.task_id, t.reward, t.channels FROM tasks t JOIN user_tasks ut ON t.task_id = ut.task_id WHERE ut.user_id = ?", (uid,))
    completed_tasks = c.fetchall()
    
    penalties = 0.0
    for tid, reward, channels_str in completed_tasks:
        all_subbed = True
        for target, _ in parse_channels(channels_str):
            try:
                m = await bot.get_chat_member(target, uid)
                if m.status not in ['member', 'administrator', 'creator']:
                    all_subbed = False
                    break
            except:
                all_subbed = False
                break
        
        if not all_subbed:
            c.execute("DELETE FROM user_tasks WHERE user_id = ? AND task_id = ?", (uid, tid))
            c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (reward, uid))
            penalties += reward
    
    conn.commit()
    conn.close()
    
    if penalties > 0:
        try:
            await bot.send_message(uid, f"<blockquote>⚠️ <b>Штраф за отписку!</b></blockquote>\n<i>Бот обнаружил, что вы отписались от каналов в выполненных заданиях.</i>\n\nЗадания сброшены. С баланса списано: <b>{round(penalties, 4)} USDT</b>.")
        except: pass

async def send_photo_safe(target_id, photo_id, caption, reply_markup=None):
    try:
        # Теперь бот отправляет фото по FILE_ID, не загружая файлы с диска!
        if photo_id:
            await bot.send_photo(chat_id=target_id, photo=photo_id, caption=caption, reply_markup=reply_markup)
        else:
            await bot.send_message(target_id, caption, reply_markup=reply_markup)
    except Exception as e:
        logging.error(f"Image error: {e}")
        await bot.send_message(target_id, caption, reply_markup=reply_markup)

# ИНСТРУМЕНТ ДЛЯ ПОЛУЧЕНИЯ FILE_ID КАРТИНОК
@dp.message_handler(content_types=['photo'], state='*')
async def get_photo_file_id(msg: types.Message):
    uid = msg.from_user.id
    if await is_admin(uid):
        await msg.answer(f"⚙️ <b>ID этого фото для кода:</b>\n\n<code>{msg.photo[-1].file_id}</code>\n\n<i>Скопируй это и вставь в нужную переменную IMG_ в самом верху кода.</i>")

async def main_menu(uid, msg=None):
    if not await enforce_mandatory_sub(uid):
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔗 Подписаться", url=f"https://t.me/{MANDATORY_CHANNEL.replace('@','')}"))
        kb.add(InlineKeyboardButton(get_txt(uid, 'check_sub'), callback_data="check_m_sub"))
        await bot.send_message(uid, get_txt(uid, 'sub_task'), reply_markup=kb)
        return

    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, input_field_placeholder="Money 💸")
    kb.add(
        KeyboardButton(get_txt(uid, 'btn_profile')), KeyboardButton(get_txt(uid, 'btn_tasks')),
        KeyboardButton(get_txt(uid, 'btn_withdraw')), KeyboardButton(get_txt(uid, 'btn_ref')),
        KeyboardButton(get_txt(uid, 'btn_rules')), KeyboardButton(get_txt(uid, 'btn_info')),
        KeyboardButton(get_txt(uid, 'btn_lang'))
    )
    if await is_admin(uid): kb.add(KeyboardButton(get_txt(uid, 'btn_admin')))
    
    caption = get_txt(uid, 'welcome')
    await send_photo_safe(uid, IMG_MAIN, caption, kb)

@dp.message_handler(commands=['start'], state='*')
async def cmd_start(msg: types.Message, state: FSMContext):
    await state.finish()
    uid = msg.from_user.id
    if await check_ban(uid): return

    args = msg.get_args()
    ref_id = int(args) if args.isdigit() and int(args) != uid else None
    
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT lang FROM users WHERE user_id = ?", (uid,))
    user_data = c.fetchone()
    
    if not user_data:
        c.execute("INSERT INTO users (user_id, ref_id) VALUES (?, ?)", (uid, ref_id))
        conn.commit()
        lang = None
    else:
        lang = user_data[0]
    conn.close()

    if lang:
        await main_menu(uid, msg)
        return

    welcome = "<blockquote>Hello, you are in the NiksMany bot!</blockquote>\nSelect your language below:"
    kb = InlineKeyboardMarkup(row_width=3).add(
        InlineKeyboardButton("🇷🇺 RU", callback_data="setlang_ru"), InlineKeyboardButton("🇬🇧 EN", callback_data="setlang_en"),
        InlineKeyboardButton("🇺🇦 UA", callback_data="setlang_uk"), InlineKeyboardButton("🇩🇪 DE", callback_data="setlang_de"),
        InlineKeyboardButton("🇵🇱 PL", callback_data="setlang_pl"), InlineKeyboardButton("🇺🇿 UZ", callback_data="setlang_uz")
    )
    await send_photo_safe(uid, IMG_LANG, welcome, kb)

@dp.callback_query_handler(lambda c: c.data.startswith('setlang_'), state='*')
async def set_lang(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    uid = cb.from_user.id
    lang = cb.data.split('_')[1]
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, uid))
    conn.commit(); conn.close()
    await cb.answer()
    await bot.delete_message(uid, cb.message.message_id)
    await main_menu(uid)

@dp.callback_query_handler(lambda c: c.data == 'check_m_sub', state='*')
async def check_m_sub(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    uid = cb.from_user.id
    try:
        member = await bot.get_chat_member(MANDATORY_CHANNEL, uid)
        if member.status in ['member', 'administrator', 'creator']:
            conn = sqlite3.connect('niksmany.db')
            c = conn.cursor()
            c.execute("UPDATE users SET mandatory_sub = 1, balance = balance + 0.01 WHERE user_id = ?", (uid,))
            conn.commit(); conn.close()
            await cb.answer(get_txt(uid, 'sub_ok'), show_alert=True)
            await bot.delete_message(uid, cb.message.message_id)
            await main_menu(uid)
        else: await cb.answer(get_txt(uid, 'sub_err'), show_alert=True)
    except: await cb.answer(get_txt(uid, 'sub_err'), show_alert=True)

@dp.message_handler(lambda msg: get_action_by_text(msg.text) is not None, state='*')
async def menu_router(msg: types.Message, state: FSMContext):
    uid = msg.from_user.id
    if await check_ban(uid): return
    if not await enforce_mandatory_sub(uid): return
    
    current_state = await state.get_state()
    if current_state: await state.finish()
        
    action = get_action_by_text(msg.text)

    if action == 'btn_admin' and await is_admin(uid):
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(InlineKeyboardButton("➕ Задание", callback_data="a_add_t"), InlineKeyboardButton("➖ Задание", callback_data="a_rem_t"))
        kb.add(InlineKeyboardButton("🔨 Бан", callback_data="a_ban_user"), InlineKeyboardButton("🕊 Разбан", callback_data="a_unban_user"))
        kb.add(InlineKeyboardButton("➕ Админ", callback_data="a_add_admin"), InlineKeyboardButton("➖ Админ", callback_data="a_rem_admin"))
        kb.add(InlineKeyboardButton("💰 Выдать USDT", callback_data="a_add_b"), InlineKeyboardButton("📉 Снять USDT", callback_data="a_rem_b"))
        kb.add(InlineKeyboardButton("📢 Рассылка", callback_data="a_broad"))
        caption = "<blockquote>⚙️ <b>АДМИН-ПАНЕЛЬ:</b></blockquote>\nВыберите необходимое действие в меню ниже 👇"
        await send_photo_safe(uid, IMG_ADMIN, caption, kb)
            
    elif action == 'btn_lang':
        kb = InlineKeyboardMarkup(row_width=3).add(
            InlineKeyboardButton("🇷🇺 RU", callback_data="setlang_ru"), InlineKeyboardButton("🇬🇧 EN", callback_data="setlang_en"),
            InlineKeyboardButton("🇺🇦 UA", callback_data="setlang_uk"), InlineKeyboardButton("🇩🇪 DE", callback_data="setlang_de"),
            InlineKeyboardButton("🇵🇱 PL", callback_data="setlang_pl"), InlineKeyboardButton("🇺🇿 UZ", callback_data="setlang_uz")
        )
        await send_photo_safe(uid, IMG_LANG, "🌍 Select language:", kb)
        
    elif action == 'btn_profile':
        await verify_task_subscriptions(uid)
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("SELECT balance, mandatory_sub FROM users WHERE user_id = ?", (uid,))
        res = c.fetchone()
        bal = res[0] if res else 0.0
        m_sub = res[1] if res else 0
        c.execute("SELECT COUNT(DISTINCT task_id) FROM user_tasks WHERE user_id = ?", (uid,))
        tasks_done = c.fetchone()[0] + m_sub
        conn.close()
        
        if tasks_done >= 7: user_status = "💠 Платина"
        elif tasks_done >= 4: user_status = "🥇 Золото"
        elif tasks_done >= 2: user_status = "🥈 Сильвер"
        else: user_status = "🥉 Бронза"

        uname = msg.from_user.username or "Hidden"
        # ДОБАВЛЕНО ФОТО ПРОФИЛЯ
        await send_photo_safe(uid, IMG_PROFILE, get_txt(uid, 'profile', username=uname, id=uid, balance=round(bal, 4), status=user_status, tasks=tasks_done))
        
    elif action == 'btn_ref':
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users WHERE ref_id = ?", (uid,))
        count = c.fetchone()[0]
        conn.close()
        link = f"https://t.me/{(await bot.get_me()).username}?start={uid}"
        await send_photo_safe(uid, IMG_REF, get_txt(uid, 'ref_text', link=link, count=count))
        
    elif action == 'btn_rules':
        # КНОПКА ПОДРОБНЕЙ ТЕПЕРЬ ПЕРЕВЕДЕНА ДЛЯ ВСЕХ ЯЗЫКОВ И ДОБАВЛЕНО ФОТО
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(get_txt(uid, 'btn_details'), url="https://telegra.ph/Polzovatelskoe-soglashenie-06-25-20"))
        await send_photo_safe(uid, IMG_RULES, get_txt(uid, 'rules'), kb)
        
    elif action == 'btn_info':
        kb = InlineKeyboardMarkup().add(InlineKeyboardButton(get_txt(uid, 'tech_sup_btn'), url=f"https://t.me/{TECH_SUPPORT.replace('@','')}"))
        await msg.answer(get_txt(uid, 'info'), reply_markup=kb)
        
    elif action == 'btn_withdraw':
        await verify_task_subscriptions(uid)
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        bal = c.fetchone()[0]
        conn.close()

        kb = InlineKeyboardMarkup(row_width=1).add(
            InlineKeyboardButton(get_txt(uid, 'with_max_btn'), callback_data="with_max"),
            InlineKeyboardButton(get_txt(uid, 'with_man_btn'), callback_data="with_manual")
        )
        await send_photo_safe(uid, IMG_WITHDRAW, get_txt(uid, 'withdraw_menu', bal=round(bal, 4)), kb)
        
    elif action == 'btn_tasks':
        await verify_task_subscriptions(uid)
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("SELECT task_id, reward, label FROM tasks")
        all_t = c.fetchall()
        c.execute("SELECT task_id FROM user_tasks WHERE user_id = ?", (uid,))
        done_t = [row[0] for row in c.fetchall()]
        conn.close()
        
        text = get_txt(uid, 'all_tasks') + f"\n\n🟢 Задание #1 | Награда: 0.01 USDT (✅ Выполнено)\n"
        await send_photo_safe(uid, IMG_TASKS, text)
        
        for idx, t in enumerate(all_t, start=2): 
            if t[0] in done_t:
                await msg.answer(f"🟢 Задание #{idx} {t[2]} | Награда: {t[1]} USDT (✅ Выполнено)")
            else:
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("👁 Начать выполнение", callback_data=f"captcha_{t[0]}"))
                await msg.answer(f"🔴 Задание #{idx} {t[2]} | Награда: {t[1]} USDT", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('captcha_'), state='*')
async def start_captcha(cb: types.CallbackQuery):
    tid = cb.data.split('_')[1]
    emojis = ['🍎', '🍌', '🍉', '🍇', '🍓']
    target = random.choice(emojis)
    options = random.sample(emojis, 3)
    if target not in options: options[0] = target
    random.shuffle(options)
    
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(*[InlineKeyboardButton(opt, callback_data=f"cap_pass_{tid}" if opt == target else "cap_fail") for opt in options])
    await cb.message.answer(f"🤖 <b>Анти-бот проверка!</b>\nВыберите стикер: {target}", reply_markup=kb)
    await cb.answer()

@dp.callback_query_handler(lambda c: c.data == 'cap_fail', state='*')
async def fail_captcha(cb: types.CallbackQuery):
    await cb.message.delete()
    await cb.answer("❌ Ошибка капчи!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith('cap_pass_'), state='*')
async def pass_captcha(cb: types.CallbackQuery):
    uid = cb.from_user.id
    tid = int(cb.data.split('_')[2])
    await cb.message.delete()
    
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT reward, channels FROM tasks WHERE task_id = ?", (tid,))
    task = c.fetchone()
    conn.close()
    if not task: return
    
    needed = []
    for target, link in parse_channels(task[1]):
        try:
            m = await bot.get_chat_member(target, uid)
            if m.status not in ['member', 'administrator', 'creator']: needed.append((target, link))
        except: needed.append((target, link))

    kb = InlineKeyboardMarkup(row_width=1)
    for idx, (_, link) in enumerate(needed, 1): kb.add(InlineKeyboardButton(f"🔗 Канал {idx}", url=link))
    kb.add(InlineKeyboardButton("✅ Проверить подписку", callback_data=f"checktask_{tid}"))
    await bot.send_message(uid, "👇 Подпишитесь и нажмите 'Проверить':", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith('checktask_'), state='*')
async def check_task(cb: types.CallbackQuery):
    uid = cb.from_user.id
    tid = int(cb.data.split('_')[1])
    
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT reward, channels FROM tasks WHERE task_id = ?", (tid,))
    task = c.fetchone()
    if not task: conn.close(); return
    
    needed_now = []
    for target, link in parse_channels(task[1]):
        try:
            m = await bot.get_chat_member(target, uid)
            if m.status not in ['member', 'administrator', 'creator']: needed_now.append(target)
        except: needed_now.append(target)
            
    if len(needed_now) == 0:
        c.execute("SELECT 1 FROM user_tasks WHERE user_id = ? AND task_id = ?", (uid, tid))
        if not c.fetchone():
            c.execute("INSERT INTO user_tasks (user_id, task_id) VALUES (?, ?)", (uid, tid))
            c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (task[0], uid))
            conn.commit()
            await cb.answer("🎉 Награда начислена!", show_alert=True)
            await bot.delete_message(uid, cb.message.message_id)
        else: await cb.answer("❌ Вы уже выполнили это задание!", show_alert=True)
    else: await cb.answer("❌ Вы не подписались на все каналы!", show_alert=True)
    conn.close()

@dp.callback_query_handler(lambda c: c.data in ['with_max', 'with_manual'], state='*')
async def withdraw_choice(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    await state.finish()
    await cb.answer()
    if cb.data == 'with_manual':
        await UserStates.withdraw_amount.set()
        await bot.send_message(uid, get_txt(uid, 'withdraw_req'))
    elif cb.data == 'with_max':
        await verify_task_subscriptions(uid)
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
        bal = c.fetchone()[0]
        if bal < MIN_WITHDRAW:
            await bot.send_message(uid, get_txt(uid, 'with_err_min'))
            conn.close(); return
        c.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (uid,))
        conn.commit(); conn.close()
        await bot.send_message(uid, get_txt(uid, 'with_ok'))
        await bot.send_message(ADMIN_PAYOUTS_CHANNEL, f"💰 <b>НОВАЯ ЗАЯВКА (MAX)!</b>\nID: <code>{uid}</code>\nСумма: <b>{bal} USDT</b>\nВыдать чек: <code>/pay {uid} ССЫЛКА</code>")

@dp.message_handler(state=UserStates.withdraw_amount)
async def withdraw_process(msg: types.Message, state: FSMContext):
    uid = msg.from_user.id
    try: amt = float(msg.text.replace(',', '.'))
    except ValueError: 
        await msg.answer(get_txt(uid, 'with_err_num')); await state.finish(); return
    
    if amt < MIN_WITHDRAW: 
        await msg.answer(get_txt(uid, 'with_err_min')); await state.finish(); return
    
    await verify_task_subscriptions(uid)
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (uid,))
    bal = c.fetchone()[0]
    
    if bal < amt:
        await msg.answer(get_txt(uid, 'with_err_bal')); conn.close(); await state.finish(); return
        
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, uid))
    conn.commit(); conn.close()
    await msg.answer(get_txt(uid, 'with_ok'))
    await bot.send_message(ADMIN_PAYOUTS_CHANNEL, f"💰 <b>НОВАЯ ЗАЯВКА НА ВЫВОД!</b>\nID: <code>{uid}</code>\nСумма: <b>{amt} USDT</b>\nВыдать чек: <code>/pay {uid} ССЫЛКА</code>")
    await state.finish()

@dp.message_handler(commands=['pay'], state='*')
async def admin_pay(msg: types.Message, state: FSMContext):
    await state.finish()
    uid = msg.from_user.id
    if not await is_admin(uid): return
    parts = msg.text.split(maxsplit=2)
    if len(parts) < 3: await msg.answer("Формат: /pay ID ССЫЛКА"); return
    
    t_id, link = int(parts[1]), parts[2]
    kb = InlineKeyboardMarkup(row_width=2).add(InlineKeyboardButton(get_txt(t_id, 'rev_yes'), callback_data="write_rev"), InlineKeyboardButton(get_txt(t_id, 'rev_no'), callback_data="no_rev"))
    await bot.send_message(t_id, get_txt(t_id, 'rev_ask', link=link), reply_markup=kb)
    await msg.answer("✅ Чек отправлен!")

@dp.callback_query_handler(lambda c: c.data in ['write_rev', 'no_rev'], state='*')
async def ask_rev(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    uid = cb.from_user.id
    await cb.answer()
    await bot.delete_message(uid, cb.message.message_id)
    if cb.data == 'write_rev':
        await UserStates.writing_review.set()
        await bot.send_message(uid, get_txt(uid, 'rev_write'))

@dp.message_handler(state=UserStates.writing_review, content_types=['text', 'photo', 'video'])
async def save_rev(msg: types.Message, state: FSMContext):
    uid = msg.from_user.id
    uname = msg.from_user.username or "Скрыт"
    await bot.send_message(ADMIN_REVIEWS_CHANNEL, f"🌟 <b>ОТЗЫВ ОТ ПОЛЬЗОВАТЕЛЯ</b> 🌟\n👤 Клиент: @{uname}\n🆔 ID: <code>{uid}</code>")
    await bot.forward_message(chat_id=ADMIN_REVIEWS_CHANNEL, from_chat_id=uid, message_id=msg.message_id)
    await msg.answer(get_txt(uid, 'rev_thanks'))
    await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith('a_'), state='*')
async def adm_clicks(cb: types.CallbackQuery, state: FSMContext):
    uid = cb.from_user.id
    if not await is_admin(uid): return
    await cb.answer()
    act = cb.data
    
    if act == "a_add_t":
        await AdminStates.task_reward.set()
        await bot.send_message(uid, "Введите сумму награды (например, 0.05):")
    elif act == "a_rem_t":
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("SELECT task_id, reward, label FROM tasks")
        tasks = c.fetchall()
        conn.close()
        t_list = "\n".join([f"ID: <code>{t[0]}</code> | {t[1]} USDT {t[2]}" for t in tasks]) or "Список пуст."
        await AdminStates.rem_task.set()
        await bot.send_message(uid, f"Введите ID задания для удаления:\n\n{t_list}")
    elif act == "a_add_admin":
        await AdminStates.add_admin.set()
        await bot.send_message(uid, "Введите Telegram ID нового администратора:")
    elif act == "a_rem_admin":
        await AdminStates.rem_admin.set()
        await bot.send_message(uid, "Введите Telegram ID администратора для удаления:")
    elif act == "a_ban_user":
        await AdminStates.ban_user.set()
        await bot.send_message(uid, "Введите Telegram ID пользователя для БАНА:")
    elif act == "a_unban_user":
        await AdminStates.unban_user.set()
        await bot.send_message(uid, "Введите Telegram ID пользователя для РАЗБАНА:")
    elif act == "a_add_b":
        await AdminStates.add_balance_id.set()
        await bot.send_message(uid, "Введите Telegram ID пользователя:")
    elif act == "a_rem_b":
        await AdminStates.rem_balance_id.set()
        await bot.send_message(uid, "Введите Telegram ID пользователя:")
    elif act == "a_broad":
        await AdminStates.broadcast.set()
        await bot.send_message(uid, "Отправьте текст или фото для рассылки всем пользователям:")

@dp.message_handler(state=AdminStates.rem_task)
async def process_rem_task(msg: types.Message, state: FSMContext):
    try:
        tid = int(msg.text)
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE task_id = ?", (tid,))
        c.execute("DELETE FROM user_tasks WHERE task_id = ?", (tid,))
        conn.commit(); conn.close()
        await msg.answer("✅ Задание успешно удалено.")
    except ValueError: await msg.answer("❌ Ошибка ввода (ID).")
    await state.finish()

@dp.message_handler(state=AdminStates.add_admin)
async def a_add_adm(msg: types.Message, state: FSMContext):
    try:
        new_id = int(msg.text.strip())
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (new_id,))
        conn.commit(); conn.close()
        await msg.answer(f"✅ Админ {new_id} добавлен.")
        try: await bot.send_message(new_id, "⭐️ Вам выданы права администратора бота.")
        except: pass
    except ValueError: await msg.answer("❌ Ошибка ввода. Нужно число.")
    await state.finish()

@dp.message_handler(state=AdminStates.rem_admin)
async def a_rem_adm(msg: types.Message, state: FSMContext):
    try:
        rem_id = int(msg.text.strip())
        if rem_id == MAIN_ADMIN_ID:
            await msg.answer("❌ Нельзя удалить главного админа!")
            await state.finish(); return
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE user_id = ?", (rem_id,))
        conn.commit(); conn.close()
        await msg.answer(f"✅ Админ {rem_id} удален.")
        try: await bot.send_message(rem_id, "⚠️ Вы были лишены прав администратора.")
        except: pass
    except ValueError: await msg.answer("❌ Ошибка ввода.")
    await state.finish()

@dp.message_handler(state=AdminStates.ban_user)
async def a_ban(msg: types.Message, state: FSMContext):
    try:
        uid = int(msg.text)
        if uid == MAIN_ADMIN_ID:
            await msg.answer("❌ Нельзя забанить главного админа!")
            await state.finish(); return
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (uid,))
        conn.commit(); conn.close()
        await msg.answer(f"🔨 Пользователь {uid} забанен.")
        try: await bot.send_message(uid, "🚫 Вы были заблокированы администратором бота.")
        except: pass
    except ValueError: await msg.answer("❌ Ошибка ввода.")
    await state.finish()

@dp.message_handler(state=AdminStates.unban_user)
async def a_unban(msg: types.Message, state: FSMContext):
    try:
        uid = int(msg.text)
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (uid,))
        conn.commit(); conn.close()
        await msg.answer(f"🕊 Пользователь {uid} разбанен.")
        try: await bot.send_message(uid, "✅ Ваш аккаунт был разблокирован.")
        except: pass
    except ValueError: await msg.answer("❌ Ошибка ввода.")
    await state.finish()

@dp.message_handler(state=AdminStates.add_balance_id)
async def process_add_bal_id(msg: types.Message, state: FSMContext):
    try:
        t_id = int(msg.text)
        await state.update_data(t_id=t_id)
        await AdminStates.add_balance_amount.set()
        await msg.answer("Введите сумму USDT:")
    except ValueError:
        await msg.answer("❌ Ошибка ввода. Нужен ID (число).")
        await state.finish()

@dp.message_handler(state=AdminStates.add_balance_amount)
async def process_add_bal_amt(msg: types.Message, state: FSMContext):
    try:
        amt = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, data['t_id']))
        conn.commit(); conn.close()
        await msg.answer("✅ Баланс пополнен.")
        try: await bot.send_message(data['t_id'], f"💰 <b>Ваш баланс пополнен на {amt} USDT!</b>")
        except: pass
    except ValueError: await msg.answer("❌ Ошибка ввода суммы.")
    await state.finish()

@dp.message_handler(state=AdminStates.rem_balance_id)
async def process_rem_bal_id(msg: types.Message, state: FSMContext):
    try:
        t_id = int(msg.text)
        await state.update_data(t_id=t_id)
        await AdminStates.rem_balance_amount.set()
        await msg.answer("Введите сумму USDT для снятия:")
    except ValueError:
        await msg.answer("❌ Ошибка ввода. Нужен ID (число).")
        await state.finish()

@dp.message_handler(state=AdminStates.rem_balance_amount)
async def process_rem_bal_amt(msg: types.Message, state: FSMContext):
    try:
        amt = float(msg.text.replace(',', '.'))
        data = await state.get_data()
        conn = sqlite3.connect('niksmany.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amt, data['t_id']))
        conn.commit(); conn.close()
        await msg.answer("✅ Средства сняты.")
        try: await bot.send_message(data['t_id'], f"📉 <b>С вашего баланса списано {amt} USDT администратором.</b>")
        except: pass
    except ValueError: await msg.answer("❌ Ошибка ввода суммы.")
    await state.finish()

@dp.message_handler(state=AdminStates.broadcast, content_types=['text', 'photo'])
async def process_broadcast(msg: types.Message, state: FSMContext):
    await state.finish()
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = c.fetchall()
    conn.close()
    
    count = 0
    await msg.answer("📢 Начинаю рассылку...")
    for u in users:
        try:
            if msg.content_type == 'text': await bot.send_message(u[0], msg.text)
            elif msg.content_type == 'photo': await bot.send_photo(u[0], photo=msg.photo[-1].file_id, caption=msg.caption)
            count += 1
            await asyncio.sleep(0.05)
        except: pass
    await msg.answer(f"✅ Рассылка завершена! Отправлено: {count}.")

@dp.message_handler(state=AdminStates.task_reward)
async def a_task_rew(msg: types.Message, state: FSMContext):
    try:
        reward = float(msg.text.replace(',','.'))
        await state.update_data(reward=reward)
        await AdminStates.task_label.set()
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add("Без метки")
        await msg.answer("Придумайте метку для задания (например: 💎 VIP) или нажмите 'Без метки':", reply_markup=kb)
    except ValueError:
        await msg.answer("❌ Ошибка ввода суммы."); await state.finish()

@dp.message_handler(state=AdminStates.task_label)
async def a_task_lbl(msg: types.Message, state: FSMContext):
    label = "" if msg.text == "Без метки" else f"[{msg.text}]"
    await state.update_data(label=label)
    await AdminStates.task_links.set()
    await msg.answer("Отправьте каналы.\n\n<b>ФОРМАТ ВВОДА:</b> ID_канала|Ссылка на канал\n<b>Пример:</b> <code>-10012345|https://t.me/+приватная_ссылка</code>\n<i>Для нескольких каналов вводите через запятую.</i>", reply_markup=ReplyKeyboardRemove())

@dp.message_handler(state=AdminStates.task_links)
async def a_task_lnks(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = sqlite3.connect('niksmany.db')
    c = conn.cursor()
    c.execute("INSERT INTO tasks (reward, channels, label) VALUES (?, ?, ?)", (data['reward'], msg.text, data['label']))
    conn.commit(); conn.close()
    await msg.answer("✅ Задание добавлено! Бот будет проверять по ID, а пользователям отдавать твою ссылку.")
    await state.finish()

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=set_default_commands, skip_updates=True)
