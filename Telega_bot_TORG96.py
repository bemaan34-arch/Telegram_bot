import os
from dotenv import load_dotenv
import logging
import asyncio
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram import BotCommand
import requests

# ⚠️ Загружаем переменные из .env файла
load_dotenv()

# ⚠️ Включим логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ⚠️Ваш токен от BotFather
API_TOKEN = os.getenv('TOKEN')

# ⚠️ Настройки времени уведомлений
NOTIFICATION_TIME_WEEKDAYS = time(18, 30)  # Пн-Чт в 18:30
# ⚠️ Настройки времени отслеживания фотоотчетов
MONITORING_START_TIME_WEEKDAYS = time(18, 30)  # Пн-Чт НАЧАЛО МОНИТОРИНГА
MONITORING_END_TIME_WEEKDAYS = time(19, 50)  # Пн-Чт КОНЕЦ МОНИТОРИНГА

NOTIFICATION_TIME_FRIDAY = time(16, 30)  # Пт в 16:30
# ⚠️ Настройки времени отслеживания фотоотчетов
MONITORING_START_TIME_FRIDAY = time(16, 30)  # Пт НАЧАЛО МОНИТОРИНГА
MONITORING_END_TIME_FRIDAY = time(19, 50)  # Пт КОНЕЦ МОНИТОРИНГА

# ⚠️ Настройки времени отправки уведомлений о невыполнении (после мониторинга)
NOTIFICATION_AFTER_MONITORING_TIME = time(19, 50)  # Время отправки уведомлений после мониторинга

# ⚠️ Настройки времени уведомлений для мастеров (по вторникам)
MASTER_NOTIFICATION_TIME = time(14, 30)  # ВТ в 14:30

# ⚠️ ИНФОКИОСКИ кнопки настройка
BUTTONS_CONFIG = [
    {"name": "1 ПР", "url": "https://tsoserver.ru/zadpodr.php?podr=3"},
    {"name": "2 СВ", "url": "https://tsoserver.ru/zadpodr.php?podr=6"},
    {"name": "3 УП", "url": "https://tsoserver.ru/zadpodr.php?podr=11"},
    {"name": "4 ДСП", "url": "https://tsoserver.ru/zadpodr.php?podr=9"},
    {"name": "5 ГЛ", "url": "https://tsoserver.ru/zadpodr.php?podr=7"},
    {"name": "6 СТ", "url": "https://tsoserver.ru/zadpodr.php?podr=4"},
    {"name": "7 ЛЗ", "url": "https://tsoserver.ru/zadpodr.php?podr=5"},
    {"name": "8 ТР", "url": "https://tsoserver.ru/zadpodr.php?podr=2"},
    {"name": "9 ПК", "url": "https://tsoserver.ru/zadpodr.php?podr=8"}
]

# ⚠️ НАСТРОЙКИ ГРУПП ДЛЯ ФОТООТЧЕТОВ
PHOTO_GROUPS = {
    "проволока": "https://t.me/+hh1Ib7u0kkgxYTYy",
    "сварка": "https://t.me/+uO_ga9I2tnwxZWFi",
    "упаковка": "https://t.me/+VXwRHTX8DvxlYmVi",
    "гальваника": "https://t.me/+1-Rgla-P-V8xMzAy",
    "стеллажи": "https://t.me/+1BBzeHAN0z0zYWMy",
    "лазер": "https://t.me/+clIuAEXiHj1hMzg6",
    "лдсп": "https://t.me/+clIuAEXiHj1hMzg", # Не используется
    "покраска": "https://t.me/+clIuAEXiHj1hM", # Не используется
}

# ⚠️ ID ГРУППЫ в телеге для мониторинга хештегов
GROUP_IDS = {
    "проволока": -1002906695193,
    "гальваника": -1002600152486,
    "сварка": -1003021224475,
    "упаковка": -1003017933861,
    "лазер": -1002923783616,
    "стеллажи": -1002948162835,
    "лдсп": -100, #не используется
    "покраска": -100, #не используется
}


def is_valid_group_id(group_id):
    """Проверяет, является ли ID валидным ID группы"""
    # ID групп обычно отрицательные
    if not isinstance(group_id, int):
        return False
    if group_id > 0:
        return False
    return True


# ⚠️ ХРАНИЛИЩЕ ВЫПОЛНЕННЫХ ЗАДАНИЙ
completed_tasks = {}

# ⚠️ ХРАНИЛИЩЕ ОЖИДАЮЩИХ ЗАДАНИЙ (для автоматического отслеживания)
pending_auto_tasks = {}

# ⚠️ СЛОВАРЬ ДЛЯ СВЯЗИ ПОЛЬЗОВАТЕЛЕЙ -сотрудников С ИХ ЦЕХАМИ
USER_DEPARTMENTS = {
    5334760125: "упаковка",  # Кочев упаковка
    6955081799: "проволока",  # Елфимов проволока
    8445311572: "стеллажи",  # Гусев стелажи
    385485636: "сварка",  # Торговкин сварка
    624545305: "лазер",  # Супиченко лазер
}

# ⚠️ Словарь имен пользователей для более информативных уведомлений
USER_NAMES = {
    5334760125: "Кочев Д.",
    6955081799: "Елфимов П.",
    8445311572: "Гусев С.",
    385485636: "Торговкин С.",
    624545305: "Супиченко К.",
    5047921635: "Солдатова Е.",
    1798364305: "Кобыленко Д.",
    6106047700: "Рахманов С.",
    6456577245: "Першин М.",
    6532862503: "Морозов Я.",
    928749882: "Березин М.",
    6493380518: "Пивоварова Е.",
}

# ⚠️ Раздельные сообщения для будних дней и пятницы
INDIVIDUAL_MESSAGES_WEEKDAYS = {
    6955081799: f"""‼️ НАПОМИНАНИЕ (ПН-ЧТ) ‼️\n 
Фото-отчеты в группу цеха ПРОВОЛОКА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Стеллаж заготовок проволоки
- Инструментальный стенд

{PHOTO_GROUPS['проволока']}
""",
    385485636: f"""‼️ НАПОМИНАНИЕ (ПН-ЧТ) ‼️\n
Фото-отчеты в группу цеха СВАРКА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Стеллаж расходников
- Инструментальный стенд

{PHOTO_GROUPS['сварка']}
""",
    5334760125: f"""‼️ НАПОМИНАНИЕ (ПН-ЧТ) ‼️\n
Фото-отчеты в группу цеха УПАКОВКА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Шкаф метизов

{PHOTO_GROUPS['упаковка']}
""",
    8445311572: f"""‼️ НАПОМИНАНИЕ (ПН-ЧТ) ‼️\n
Фото-отчеты в группу цеха СТЕЛЛАЖИ\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Инструментальные стенды в цеху

{PHOTO_GROUPS['стеллажи']}
""",
    624545305: f"""‼️ НАПОМИНАНИЕ (ПН-ЧТ) ‼️\n
Фото-отчеты в группу цеха ЛАЗЕР и ТРУБА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Стеллаж трубы
- Инструментальный стенд

{PHOTO_GROUPS['лазер']}
""",
}

INDIVIDUAL_MESSAGES_FRIDAY = {
    6955081799: f"""‼️ НАПОМИНАНИЕ (ПТ) ‼️\n
Фото-отчеты в группу цеха ПРОВОЛОКА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Стеллаж заготовок проволоки
- Инструментальный стенд
- Болгарки
- Уборка цеха

{PHOTO_GROUPS['проволока']}
""",
    385485636: f"""‼️ НАПОМИНАНИЕ (ПТ) ‼️\n
Фото-отчеты в группу цеха СВАРКА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Стеллаж расходников
- Инструментальный стенд
- Болгарки
- Уборка цеха

{PHOTO_GROUPS['сварка']}
""",
    5334760125: f"""‼️ НАПОМИНАНИЕ (ПТ) ‼️\n
Фото-отчеты в группу цеха УПАКОВКА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Шкаф метизов
- Уборка цеха

{PHOTO_GROUPS['упаковка']}
""",
    8445311572: f"""‼️ НАПОМИНАНИЕ (ПТ) ‼️\n
Фото-отчеты в группу цеха СТЕЛЛАЖИ\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Инструментальные стенды в цеху
- Болгарки
- Уборка цеха

{PHOTO_GROUPS['стеллажи']}
""",
    624545305: f"""‼️ НАПОМИНАНИЕ (ПТ) ‼️\n
Фото-отчеты в группу цеха ЛАЗЕР и ТРУБА\nс хештегом #Фотоотчет (скопируй и вставь в подпись фото)\n
- Стеллаж трубы
- Болгарки
- Инструментальный стенд
- Уборка цеха

{PHOTO_GROUPS['лазер']}
""",
}

# ⚠️ Индивидуальные сообщения для мастеров
MASTER_MESSAGES = {
    6106047700: "‼️ Напоминание для мастера сварки ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!",
    # Рахманов
    6532862503: "‼️ Напоминание для мастера лазера и трубы ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!",
    # Morozov
    6456577245: "‼️ Напоминание для мастера стеллажей ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!",
    # Першин
    1135613534: "‼️ Напоминание для мастера проволоки ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!",
    # Пахомов
    5334760125: "‼️ Напоминание для мастера упаковки ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!",
    # Kochev
    6493380518: "‼️ Напоминание для мастера проволоки ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!",
    # Пивоварова
    1798364305: "‼️ Напоминание для мастера проволоки ‼️\n\nОбновить реестр остатков изделий и заготовок в гугл таблице цеха !!!"
    # кобыленко
}

# ⚠️ Список пользователей для уведомлений все - сотрудники и мастера
TARGET_USER_IDS = [
    5047921635, # солдатова
    1798364305, #кобыленко
    6106047700,  # Рахманов
    6456577245,  # Першин
    1135613534,  # Пахомов
    6532862503,  # Morozov
    5334760125,  # Kochev
    6955081799,  # Елфимов - проволока
    8445311572,  # гусев - стеллажи
    385485636,  # торговкин - сварка
    624545305,  # супиченко - лазер
]

YOUR_ADMIN_ID = 928749882  # berezin
MASTER_ID = [
    5047921635, # солдатова
    1798364305, #кобыленко
    YOUR_ADMIN_ID,
    6106047700,  # Рахманов
    6532862503,  # Morozov
    6456577245,  # Першин
    6493380518,  # Пивоварова
    1135613534,  # Пахомов
    5334760125,  # Kochev
    5787593238,  # ТВ
]

# ⚠️ Настройки времени для табелей
TABEL_NOTIFICATION_TIME = time(7, 30)  # Пн-Пт в 7:40
TABEL_MONITORING_START_TIME = time(7, 30)  # Пн-Пт НАЧАЛО МОНИТОРИНГА
TABEL_MONITORING_END_TIME = time(9, 1)    # Пн-Пт КОНЕЦ МОНИТОРИНГА

# ⚠️ Хранилища
completed_tabels = {}  # {master_id: данные}
pending_tabels = {}    # {master_id: данные}
is_tabel_monitoring_active = False

TABEL_MESSAGE = """‼️ НАПОМИНАНИЕ О СДАЧЕ ТАБЕЛЯ СВОЕГО ЦЕХА ‼️

⚠️ С подписью фотографии "Табель" ⚠️

Необходимо сдать табель в группу: "Табеля Торг96" до 09:00!
За невыполнение фото отчета табеля до 09:00, будет выставлен штраф в размере 1000 рублей.
"""

GROUP_IDS_TABEL = {
    "табель завод": -876417763,
}

PHOTO_GROUPS_TABEL = {
    "табель завод": "https://t.me/+BeBzZIvsQyNiOWRi",
}

# ⚠️ Словарь для связи цехов с ID мастеров
MASTER_BY_DEPARTMENT = {
    "покраска": [5047921635], # Солдатова
    "лдсп": [1798364305],  # кобыленко
    "проволока": [6493380518],  # Пивоварова
    "гальваника": [6493380518],  # Пивоварова
    "сварка": [6106047700],  # Рахманов
    "стеллажи": [6456577245],  # Першин
    "лазер": [6532862503],  # Morozov
    "упаковка": [5334760125],  # Kochev
    "администратор": [928749882],  # berezin
}

# Глобальная переменная для хранения application
application_instance = None

# Флаг для отслеживания активного мониторинга
is_monitoring_active = False

# Словарь для отслеживания отправленных уведомлений
sent_notifications = set()


# ⚠️ Функция для проверки хештега с учетом опечаток
def check_photo_report_hashtag(text):
    if not text:
        return False

    text_lower = text.lower()
    hashtag_variants = [
        'фотоотчет',
        'фотоотчёт',
        'фотоотчет',
        'фотоотчёт',
        'photoотчет',
        'photoотчёт',
        'фоттоотчет',
        'фоттоотчёт',
        ' фотоотчет',
        ' фотоотчёт',
        ' Фотоотчет',
        ' Фотоотчёт',
        'фототчет',
        'Фототчет',
        '  фото отчет',
        ' фото отчет',
        ' Фото-отчет',
        ' фото-отчет',
        'Фото-отчет',
        'фото-отчет',
    ]
    # Проверяем все варианты
    for variant in hashtag_variants:
        if variant in text_lower:
            return True

    return False


# ⚠️ Функция для запуска мониторинга фотоотчетов
async def start_photo_monitoring():
    global is_monitoring_active

    now = datetime.now()
    current_weekday = now.weekday()

    # Определяем время мониторинга в зависимости от дня недели
    if current_weekday == 4:  # Пятница
        start_time = MONITORING_START_TIME_FRIDAY
        end_time = MONITORING_END_TIME_FRIDAY
        day_type = "пятница"
    else:  # Пн-Чт
        start_time = MONITORING_START_TIME_WEEKDAYS
        end_time = MONITORING_END_TIME_WEEKDAYS
        day_type = "будний день"

    start_datetime = datetime.combine(now.date(), start_time)
    end_datetime = datetime.combine(now.date(), end_time)

    # Если текущее время в пределах периода мониторинга
    if start_datetime <= now <= end_datetime:
        is_monitoring_active = True
        logger.info(f"🚀 Начинаем мониторинг фотоотчетов для {day_type} с {start_time} до {end_time}")

        # Добавляем всех сотрудников в ожидание автоматического отслеживания
        for user_id in TARGET_USER_IDS:
            if user_id in USER_DEPARTMENTS:
                department = USER_DEPARTMENTS[user_id]
                user_name = USER_NAMES.get(user_id, "Сотрудник")

                pending_auto_tasks[user_id] = {
                    'user_name': user_name,
                    'department': department,
                    'start_time': datetime.now().strftime('%H:%M:%S'),
                    'status': 'ожидает фото с хештегом',
                    'notification_sent': False  # Флаг для отслеживания отправки уведомления о невыполнении
                }

        logger.info(f"📋 Добавлено {len(pending_auto_tasks)} задач для автоматического отслеживания")

        # Останавливаем мониторинг в указанное время
        monitoring_duration = (end_datetime - now).total_seconds()
        if monitoring_duration > 0:
            await asyncio.sleep(monitoring_duration)
            is_monitoring_active = False
            logger.info(f"⏹️ Мониторинг фотоотчетов завершен ({day_type})")

            # Запускаем отправку уведомлений о невыполненных заданиях
            asyncio.create_task(send_failure_notifications_after_monitoring(day_type))


# ⚠️ Функция для отправки уведомлений о невыполнении после завершения мониторинга
async def send_failure_notifications_after_monitoring(day_type):
    logger.info(f"⏰ Запуск отправки уведомлений о невыполнении после мониторинга ({day_type})")
    # Ждем до установленного времени отправки
    now = datetime.now()
    target_time = NOTIFICATION_AFTER_MONITORING_TIME
    target_datetime = datetime.combine(now.date(), target_time)

    if now < target_datetime:
        wait_seconds = (target_datetime - now).total_seconds()
        logger.info(f"⏳ Ждем {wait_seconds} секунд до времени отправки уведомлений")
        await asyncio.sleep(wait_seconds)

    # Отправляем уведомления
    await send_unfinished_tasks_notifications(day_type)

    # Очищаем ожидающие задания после отправки уведомлений
    pending_auto_tasks.clear()
    logger.info("🧹 Очищены ожидающие задания после отправки уведомлений")


# ⚠️ Функция для отправки уведомлений о невыполненных заданиях
async def send_unfinished_tasks_notifications(day_type):
    if not pending_auto_tasks:
        logger.info("📭 Нет невыполненных заданий для отправки уведомлений")
        return

    logger.info(f"📤 Начинаем отправку уведомлений о {len(pending_auto_tasks)} невыполненных заданиях")

    unfinished_tasks_list = []
    failed_notifications = []  # Для хранения информации о невыполненных заданиях

    for user_id, task_data in pending_auto_tasks.items():
        if not task_data.get('notification_sent', False):
            department = task_data['department']
            user_name = task_data['user_name']
            unfinished_tasks_list.append(f"• {user_name} ({department})")
            failed_notifications.append((user_id, task_data))

            logger.info(f"📨 Отправляем уведомление для {user_name} ({department})")

            # Помечаем, что уведомление отправлено
            task_data['notification_sent'] = True

    if unfinished_tasks_list:
        unfinished_tasks = "\n".join(unfinished_tasks_list)

        # 1. Отправляем уведомление администратору
        admin_message = f"""
⚠️ *Admin - Мониторинг завершен! Невыполненные задания ({day_type}):*

{unfinished_tasks}

*Всего не выполнено: {len(unfinished_tasks_list)} заданий*
*Будут наложены штрафы за невыполнение 100 руб.!*
        """

        try:
            await application_instance.bot.send_message(
                chat_id=YOUR_ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Администратор уведомлен о {len(unfinished_tasks_list)} невыполненных заданиях")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления администратору: {e}")

        # 2. Отправляем уведомления мастерам и в группы
        for user_id, task_data in failed_notifications:
            logger.info(f"📨 Отправка уведомления для {task_data['user_name']} ({task_data['department']})")
            await send_task_failed_notification(user_id, task_data, day_type)

    else:
        logger.info("✅ Все задания выполнены, уведомления не требуются")


# ⚠️ Функция для отправки уведомления о невыполнении задания мастеру и в группу цеха
async def send_task_failed_notification(user_id, task_data, day_type):
    department = task_data['department']
    user_name = task_data['user_name']

    logger.info(f"🔍 Отправка уведомления для {user_name} ({department})")

    # Сообщение для мастера
    master_message = f"""
⚠️ Master - ЗАДАНИЕ НЕ ВЫПОЛНЕНО!

Сотрудник: {user_name}
Цех: {department}
День: {day_type}
Время мониторинга: завершено

Задание не выполнено в установленный срок!
Свяжитесь с сотрудником! И проверьте фотоотчет!
Если фотоотчета не будет, требуется наложение штрафа 100 руб. за невыполнение обязанностей!
    """

    # Сообщение для группы цеха
    group_message = f"""
🚨 ЗАДАНИЕ НЕ ВЫПОЛНЕНО! {department.upper()} 🚨

⚠️ Сотрудник {user_name} не выполнил задание по фотоотчету!

День: {day_type}
Время мониторинга завершено

Требуется срочно предоставить фотоотчет или будут применены штрафные санкции!
    """

    # Отправляем уведомление мастерам цеха
    if department in MASTER_BY_DEPARTMENT:
        master_ids = MASTER_BY_DEPARTMENT[department]
        logger.info(f"👨‍🏭 Мастера для цеха {department}: {master_ids}")

        for master_id in master_ids:
            try:
                logger.info(f"📨 Отправка уведомления мастеру {master_id}")
                await application_instance.bot.send_message(
                    chat_id=master_id,
                    text=master_message
                )
                logger.info(f"✅ Мастер {master_id} уведомлен о невыполнении задания в цехе {department}")
            except Exception as e:
                logger.error(f"❌ Ошибка уведомления мастера {master_id}: {e}")

    # Отправляем уведомление в группу цеха
    if department in GROUP_IDS:
        group_id = GROUP_IDS[department]

        # Проверяем валидность ID группы
        if not is_valid_group_id(group_id):
            logger.error(f"❌ Невалидный ID группы для цеха {department}: {group_id}")
            return

        logger.info(f"📨 Отправка уведомления в группу {group_id} для цеха {department}")

        try:
            await application_instance.bot.send_message(
                chat_id=group_id,
                text=group_message
            )
            logger.info(f"✅ Уведомление отправлено в группу цеха {department} о невыполнении задания")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления в группу цеха {department}: {e}")
            # Добавим дополнительную диагностику
            if "Chat not found" in str(e):
                logger.error(f"❌ Группа с ID {group_id} не найдена. Проверьте ID группы и права бота.")
            elif "bot was blocked" in str(e).lower():
                logger.error(f"❌ Бот заблокирован в группе {group_id}")
            elif "not enough rights" in str(e).lower():
                logger.error(f"❌ У бота недостаточно прав для отправки сообщений в группу {group_id}")
    else:
        logger.warning(f"⚠️ Для цеха {department} не найдена группа для уведомлений в GROUP_IDS")


# ⚠️ Модифицированная функция отправки уведомлений
async def send_notifications_to_all():
    global application_instance

    if application_instance is None:
        logger.error("Application instance not set!")
        return

    success_count = 0
    error_count = 0

    now = datetime.now()
    if now.weekday() == 4:  # Пятница
        messages_to_send = INDIVIDUAL_MESSAGES_FRIDAY
        day_type = "пятница"
    else:
        messages_to_send = INDIVIDUAL_MESSAGES_WEEKDAYS
        day_type = "будний день"

    logger.info(f"📅 Отправка уведомлений для {day_type}")

    # Создаем уникальный ключ для сегодняшних уведомлений
    notification_key = f"notify_{now.date().isoformat()}_{day_type}"

    # Проверяем, не отправляли ли уже уведомления сегодня
    if notification_key in sent_notifications:
        logger.info(f"⚠️ Уведомления для {day_type} уже отправлены сегодня")
        return

    for user_id in TARGET_USER_IDS:
        message_text = messages_to_send.get(user_id)

        if not message_text:
            logger.warning(f"❌ Для пользователя {user_id} не настроено сообщение на {day_type}")
            error_count += 1
            continue

        try:
            # Отправляем уведомление БЕЗ КНОПКИ
            await application_instance.bot.send_message(
                chat_id=user_id,
                text=message_text
            )
            logger.info(f"✅ Уведомление отправлено пользователю {user_id} ({day_type})")
            success_count += 1

        except Exception as e:
            logger.error(f"❌ Ошибка отправки пользователю {user_id}: {e}")
            error_count += 1
            if "bot was blocked" in str(e).lower():
                if user_id in TARGET_USER_IDS:
                    TARGET_USER_IDS.remove(user_id)
                logger.warning(f"🗑️ Пользователь {user_id} удален из списков (заблокировал бота)")

    # Помечаем уведомления как отправленные сегодня
    sent_notifications.add(notification_key)

    # Запускаем автоматический мониторинг после отправки уведомлений
    asyncio.create_task(start_photo_monitoring())

    logger.info(f"📊 Итог отправки: ✅ {success_count} успешно, ❌ {error_count} с ошибками")


# ⚠️ Модифицированный обработчик сообщений из групп
async def handle_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        return

    # Проверяем, активен ли мониторинг
    if not is_monitoring_active:
        return

    user_id = update.message.from_user.id
    message_text = update.message.caption or update.message.text or ""

    # Проверяем хештег с учетом опечаток
    has_photo_report_hashtag = check_photo_report_hashtag(message_text)

    if has_photo_report_hashtag and update.message.photo:
        if user_id in pending_auto_tasks:
            task_data = pending_auto_tasks[user_id]
            department = task_data['department']
            user_name = task_data['user_name']

            task_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Сохраняем выполненное задание
            completed_tasks[task_id] = {
                'user_id': user_id,
                'user_name': user_name,
                'department': department,
                'start_time': task_data['start_time'],
                'completion_time': datetime.now().strftime('%H:%M:%S'),
                'photo_count': len(update.message.photo),
                'message': message_text,
                'status': 'выполнено'
            }

            # Уведомление администратору
            admin_message = f"""
✅ Admin - Задание выполнено!

Сотрудник: {user_name}
Цех: {department}
Время выполнения: {datetime.now().strftime('%H:%M:%S')}

Фото: {len(update.message.photo)} шт.
Сообщение: {message_text or 'без текста'}

Перейди по ссылке сообщения и проверь фотоотчет!
Ссылка на сообщение: https://t.me/c/{str(update.effective_chat.id).replace('-100', '')}/{update.message.message_id}
"""

            try:
                await context.bot.send_message(
                    chat_id=YOUR_ADMIN_ID,
                    text=admin_message,
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Администратор уведомлен о выполнении задания пользователем {user_id}")
            except Exception as e:
                logger.error(f"❌ Ошибка уведомления администратора: {e}")

            # Уведомление мастерам цеха
            if department in MASTER_BY_DEPARTMENT:
                master_ids = MASTER_BY_DEPARTMENT[department]
                master_message = f"""
✅ Master - Фотоотчет выполнен в вашем цехе!
⚠️ Требуется проверка фотоотчета! ⚠️

Сотрудник: {user_name}
Цех: {department}
Время выполнения: {datetime.now().strftime('%H:%M:%S')}

Фото: {len(update.message.photo)} шт.
Сообщение: {message_text or 'без текста'}

Ссылка на сообщение: https://t.me/c/{str(update.effective_chat.id).replace('-100', '')}/{update.message.message_id}
"""

                for master_id in master_ids:
                    try:
                        await context.bot.send_message(
                            chat_id=master_id,
                            text=master_message,
                            parse_mode='Markdown'
                        )
                        logger.info(f"✅ Мастер {master_id} уведомлен о выполнении задания в цехе {department}")
                    except Exception as e:
                        logger.error(f"❌ Ошибка уведомления мастера {master_id}: {e}")

            # Удаляем из ожидающих заданий
            if user_id in pending_auto_tasks:
                del pending_auto_tasks[user_id]

            # Подтверждение в группе
            try:
                await update.message.reply_text(
                    f"✅ *Фотоотчет принят!*\n\nЗадание выполнено. Уведомление отправлено мастеру цеха.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"❌ Ошибка отправки подтверждения пользователю: {e}")

    elif has_photo_report_hashtag and not update.message.photo:
        try:
            await update.message.reply_text(
                f"❌ *Сообщение не засчитано как фотоотчет!*\n\n"
                f"Для выполнения задания необходимо отправить ФОТО с хештегом #Фотоотчет",
                parse_mode='Markdown'
            )
            logger.info(f"⚠️ Пользователь {user_id} отправил хештег без фото в группе")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки предупреждения пользователю: {e}")


# Добавьте эту функцию для проверки прав бота
async def check_bot_permissions(group_id):
    """Проверяет права бота в группе"""
    try:
        chat = await application_instance.bot.get_chat(group_id)
        member = await application_instance.bot.get_chat_member(group_id, application_instance.bot.id)

        logger.info(f"👥 Бот в группе {group_id}: {chat.title}")
        logger.info(
            f"🔧 Права бота: can_send_messages={member.can_send_messages}, can_send_media_messages={member.can_send_media_messages}")

        return member.can_send_messages
    except Exception as e:
        logger.error(f"❌ Ошибка проверки прав бота в группе {group_id}: {e}")
        return False


# ⚠️ ФУНКЦИЯ ОТПРАВКИ ЕЖЕНЕДЕЛЬНЫХ УВЕДОМЛЕНИЙ МАСТЕРАМ
async def send_master_notifications():
    global application_instance

    if application_instance is None:
        logger.error("Application instance not set!")
        return

    success_count = 0
    error_count = 0

    logger.info("📅 Отправка еженедельных уведомлений мастерам")

    # Создаем уникальный ключ для еженедельных уведомлений
    weekly_key = f"weekly_{datetime.now().isocalendar()[1]}"  # Номер недели в году

    if weekly_key in sent_notifications:
        logger.info("⚠️ Еженедельные уведомления уже отправлены на этой неделе")
        return

    for user_id in MASTER_ID:
        message_text = MASTER_MESSAGES.get(user_id)

        if not message_text:
            logger.warning(f"❌ Для мастера {user_id} не настроено еженедельное сообщение")
            error_count += 1
            continue

        try:
            await application_instance.bot.send_message(
                chat_id=user_id,
                text=message_text
            )
            logger.info(f"✅ Еженедельное уведомление отправлено мастеру {user_id}")
            success_count += 1

        except Exception as e:
            logger.error(f"❌ Ошибка отправки мастеру {user_id}: {e}")
            error_count += 1
            if "bot was blocked" in str(e).lower():
                logger.warning(f"⚠️ Мастер {user_id} заблокировал бота")

    # Помечаем еженедельные уведомления как отправленные
    sent_notifications.add(weekly_key)

    logger.info(f"📊 Итог отправки мастерам: ✅ {success_count} успешно, ❌ {error_count} с ошибками")

# ⚠️ Функция для проверки и отправки ежедневных уведомлений
async def check_and_send_daily_notifications():
    # Переменная для отслеживания отправленных еженедельных уведомлений
    weekly_notification_sent = False

    while True:
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()
        current_date_str = now.date().isoformat()  # Уникальный идентификатор дня

        # Проверяем будний день (0-4 = пн-пт)
        if current_weekday < 5:
            # Определяем правильное время для текущего дня
            if current_weekday == 4:  # Пятница
                target_time = NOTIFICATION_TIME_FRIDAY
                monitoring_start = MONITORING_START_TIME_FRIDAY
                monitoring_end = MONITORING_END_TIME_FRIDAY
            else:
                target_time = NOTIFICATION_TIME_WEEKDAYS
                monitoring_start = MONITORING_START_TIME_WEEKDAYS
                monitoring_end = MONITORING_END_TIME_WEEKDAYS

            # Проверяем время для еженедельных уведомлений мастеров (вторник)
            if (current_weekday == 1 and
                    current_time.hour == MASTER_NOTIFICATION_TIME.hour and
                    current_time.minute == MASTER_NOTIFICATION_TIME.minute and
                    current_time.second == 0 and
                    not weekly_notification_sent):
                logger.info("⏰ Время отправки еженедельных уведомлений мастерам")
                await send_master_notifications()
                weekly_notification_sent = True
                await asyncio.sleep(60)

            # Проверяем совпадение времени для ежедневных уведомлений
            notification_key = f"notify_{current_date_str}_{target_time.hour}_{target_time.minute}"
            if (current_time.hour == target_time.hour and
                    current_time.minute == target_time.minute and
                    current_time.second == 0 and
                    notification_key not in sent_notifications):
                day_name = ["понедельник", "вторник", "среду", "четверг", "пятницу"][current_weekday]
                logger.info(f"⏰ Время отправки уведомлений: {current_time.strftime('%H:%M:%S')} ({day_name})")

                await send_notifications_to_all()
                sent_notifications.add(notification_key)
                await asyncio.sleep(60)

            # Проверяем время для запуска мониторинга
            monitoring_key = f"monitor_{current_date_str}_{monitoring_start.hour}_{monitoring_start.minute}"
            if (current_time.hour == monitoring_start.hour and
                    current_time.minute == monitoring_start.minute and
                    current_time.second == 0 and
                    monitoring_key not in sent_notifications):
                logger.info(f"⏰ Время начала мониторинга: {current_time.strftime('%H:%M:%S')}")
                asyncio.create_task(start_photo_monitoring())
                sent_notifications.add(monitoring_key)
                await asyncio.sleep(60)

        # Сбрасываем флаги отправленных уведомлений в начале нового дня
        if current_time.hour == 0 and current_time.minute == 0 and current_time.second == 0:
            # Удаляем только ежедневные уведомления, оставляя еженедельные
            keys_to_remove = [key for key in sent_notifications if key.startswith(('notify_', 'monitor_'))]
            for key in keys_to_remove:
                sent_notifications.discard(key)
            weekly_notification_sent = False
            logger.info("🔄 Сброс флагов отправленных уведомлений для нового дня")

        # Ждем 1 секунду перед следующей проверкой
        await asyncio.sleep(1)

# ⚠️Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    user_id = update.message.from_user.id
    # ⚠️ Создаем клавиатуру с 9 кнопками (3x3 grid)
    keyboard = []
    for i in range(0, 9, 3):
        row = [
            InlineKeyboardButton(BUTTONS_CONFIG[i]["name"], url=BUTTONS_CONFIG[i]["url"]),
            InlineKeyboardButton(BUTTONS_CONFIG[i + 1]["name"], url=BUTTONS_CONFIG[i + 1]["url"]),
            InlineKeyboardButton(BUTTONS_CONFIG[i + 2]["name"], url=BUTTONS_CONFIG[i + 2]["url"])
        ]
        keyboard.append(row)

    # ⚠️ Добавляем кнопки управления общедоступные
    keyboard.append([InlineKeyboardButton("🕐  График работы завода", callback_data='info_grafik')])
    keyboard.append([InlineKeyboardButton("☎️  Номера руководителей завода", callback_data='info_number_master')])
    keyboard.append([InlineKeyboardButton("☎️  Номера отдела кадров", callback_data='info_number_kadry')])
    keyboard.append([InlineKeyboardButton("🧮  Справка о КТУ", callback_data='info_kty')])
    keyboard.append([InlineKeyboardButton("⚖️  Категории и ставки", callback_data='info_katigorya')])
    keyboard.append([InlineKeyboardButton("ℹ️  Информация", callback_data='info')])
    keyboard.append([InlineKeyboardButton("🆔  Мой ID", callback_data='my_id')])

    # ⚠️ Кнопка для админа
    if user_id == YOUR_ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🧠  Menu - Admin", callback_data='admin_menu')])

    if user_id in MASTER_ID:
        keyboard.append(
            [InlineKeyboardButton("👤  Menu - Master", callback_data='master_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = f"""
Привет, {user_name} !!! 👋      

Я заводской чат-бот, БЕНДЕР ТОРЖИКОВИЧ !!! 
Для напоминаний и быстрого доступа к информационным сервисам завода.

🔔 *Напоминания:*
Автоматические напоминания:
• Пн-Чт: {NOTIFICATION_TIME_WEEKDAYS.strftime('%H:%M')}
• Пт: {NOTIFICATION_TIME_FRIDAY.strftime('%H:%M')}
о фото-отчетах в своих цехах!

↗️ *Кнопки с сылками для перехода в инфокисок цеха:*

*1 ПР* - Инфокисок ПРОВОЛОКИ
*2 СВ* - Инфокисок СВАРКИ
*3 УП* - Инфокисок УПАКОВКИ
*4 ДСП* - Инфокисок ЛДСП
*5 ГЛ* - Инфокисок ГАЛЬВАНИКИ
*6 СТ* - Инфокисок СТЕЛЛАЖЕЙ
*7 ЛЗ* - Инфокисок ЛАЗЕРА
*8 ТР* - Инфокисок ТРУБЫ
*9 ПК* - Инфокисок ПОКРАСКИ

*Выбери и нажми необходимию кнопку* ⬇️
    """
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# ⚠️ Обработчик команды /id
async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"👤 Ваш профиль:\n"
        f"• Имя: {user_name}\n"
        f"• ID: `{user_id}`\n"
        f"⬆️ Этот ID нужно передать администратору для добавления в список уведомлений @MBer89"
        f"\n"
        f"Для перехода на начальную страницу нажми: /start",
        parse_mode='Markdown'
    )

# ⚠️Обработчик команды /admin_stats
async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    stats_text = "📊 Статистика уведомлений:\n\n"
    stats_text += f"• Время уведомлений (Пн-Чт): {NOTIFICATION_TIME_WEEKDAYS.strftime('%H:%M')}\n"
    stats_text += f"• Время уведомлений (Пт): {NOTIFICATION_TIME_FRIDAY.strftime('%H:%M')}\n"
    stats_text += f"• Дни: Пн-Пт (будние)\n\n"
    stats_text += "🎯 Получатели уведомлений:\n\n"

    for i, user_id in enumerate(TARGET_USER_IDS, 1):
        department = USER_DEPARTMENTS.get(user_id, "неизвестный цех")
        weekday_msg = INDIVIDUAL_MESSAGES_WEEKDAYS.get(user_id, "❌ Сообщение не настроено")
        friday_msg = INDIVIDUAL_MESSAGES_FRIDAY.get(user_id, "❌ Сообщение не настроено")
        stats_text += f"{i}. ID: {user_id} - {department}\n"
        stats_text += f"   Пн-Чт: {weekday_msg[:50]}...\n"
        stats_text += f"   Пт: {friday_msg[:50]}...\n"

    stats_text += f"\nВсего получателей: {len(TARGET_USER_IDS)}"
    await update.message.reply_text(stats_text)

# ⚠️Обработчик команды /send_now
async def send_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in [YOUR_ADMIN_ID]:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    await update.message.reply_text("🔄 Начинаю отправку уведомлений...")
    await send_notifications_to_all()
    await update.message.reply_text("✅ Уведомления отправлены!")

# ⚠️ Обработчик команды /set_message
async def set_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in [YOUR_ADMIN_ID]:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Используйте: /set_message user_id текст_сообщения\n"
            "Пример: /set_message 123456789 ⏰ Напоминание"
        )
        return

    try:
        target_user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        INDIVIDUAL_MESSAGES_WEEKDAYS[target_user_id] = message_text
        INDIVIDUAL_MESSAGES_FRIDAY[target_user_id] = message_text

        if target_user_id not in TARGET_USER_IDS:
            TARGET_USER_IDS.append(target_user_id)

        await update.message.reply_text(
            f"✅ Сообщение для пользователя {target_user_id} установлено:\n"
            f"\"{message_text}\""
        )
    except ValueError:
        await update.message.reply_text("❌ user_id должен быть числом")

# ⚠️ Обработчик команды /set_weekday
async def set_weekday_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Используйте: /set_weekday user_id текст_сообщения\n"
            "Пример: /set_weekday 123456789 ⏰ Напоминание для будних дней"
        )
        return

    try:
        target_user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        INDIVIDUAL_MESSAGES_WEEKDAYS[target_user_id] = message_text

        await update.message.reply_text(
            f"✅ Сообщение для будних дней пользователю {target_user_id} установлено:\n"
            f"\"{message_text}\""
        )
    except ValueError:
        await update.message.reply_text("❌ user_id должен быть числом")

# ⚠️ Обработчик команды /set_friday
async def set_friday_message_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Используйте: /set_friday user_id текст_сообщения\n"
            "Пример: /set_friday 123456789 ⏰ Пятничное напоминание"
        )
        return

    try:
        target_user_id = int(context.args[0])
        message_text = " ".join(context.args[1:])
        INDIVIDUAL_MESSAGES_FRIDAY[target_user_id] = message_text

        await update.message.reply_text(
            f"✅ Сообщение для пятницы пользователю {target_user_id} установлено:\n"
            f"\"{message_text}\""
        )
    except ValueError:
        await update.message.reply_text("❌ user_id должен быть числом")

# ⚠️ Обработчик команды /check_tasks
async def check_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    if not completed_tasks:
        await update.message.reply_text("📊 Выполненных заданий пока нет")
        return

    tasks_text = "📊 Все задания:\n\n"
    for task_id, task_data in completed_tasks.items():
        status_icon = "✅" if task_data.get('status') == 'выполнено' else "🟡"
        tasks_text += f"{status_icon} {task_data['user_name']} ({task_data['department']})\n"
        tasks_text += f"  ⏰ Начало: {task_data['start_time']}\n"
        if task_data.get('completion_time'):
            tasks_text += f"  ⏰ Завершение: {task_data['completion_time']}\n"
        tasks_text += f"  📊 Статус: {task_data.get('status', 'неизвестно')}\n"
        tasks_text += f"  📸 Фото: {task_data.get('photo_count', 0)} шт.\n"
        tasks_text += f"  💬 Сообщение: {task_data.get('message', 'без текста')}\n\n"

    await update.message.reply_text(tasks_text)

# ⚠️ Обработчик команды /menu
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.from_user.first_name
    user_id = update.message.from_user.id
    keyboard = []
    for i in range(0, 9, 3):
        row = [
            InlineKeyboardButton(BUTTONS_CONFIG[i]["name"], url=BUTTONS_CONFIG[i]["url"]),
            InlineKeyboardButton(BUTTONS_CONFIG[i + 1]["name"], url=BUTTONS_CONFIG[i + 1]["url"]),
            InlineKeyboardButton(BUTTONS_CONFIG[i + 2]["name"], url=BUTTONS_CONFIG[i + 2]["url"])
        ]
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🕐  График работы завода", callback_data='info_grafik')])
    keyboard.append([InlineKeyboardButton("☎️  Номера руководителей завода", callback_data='info_number_master')])
    keyboard.append([InlineKeyboardButton("☎️  Номера отдела кадров", callback_data='info_number_kadry')])
    keyboard.append([InlineKeyboardButton("🧮  Справка о КТУ", callback_data='info_kty')])
    keyboard.append([InlineKeyboardButton("🚫  Штрафы завод",
                                          url='https://docs.google.com/spreadsheets/d/1VQia-_BOpVbh5nH6FNRUhi43XxMZjtP9wYINQchy5Tg/edit?gid=0#gid=0')])
    keyboard.append([InlineKeyboardButton("⚖️  Категории и ставки", callback_data='info_katigorya')])
    keyboard.append([InlineKeyboardButton("ℹ️  Информация", callback_data='info')])
    keyboard.append([InlineKeyboardButton("🆔  Мой ID", callback_data='my_id')])

    # ⚠️ Кнопка для админа
    if user_id == YOUR_ADMIN_ID:
        keyboard.append([InlineKeyboardButton("🧠  Menu - Admin", callback_data='admin_menu')])

    if user_id in MASTER_ID:
        keyboard.append(
            [InlineKeyboardButton("👤  Menu - Master", callback_data='master_menu')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📋  Основное меню:", reply_markup=reply_markup)

# ⚠️Обработчик нажатий на inline-кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == 'info':
        text = f"""
ℹ️ Информация о боте:

⚠️ ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ
    
    Данное программное обеспечение является собственностью [Berezin Maksim / MBer89 - TORG96].
    Любое копирование, модификация или распространение без письменного разрешения
    запрещено и преследуется по закону.
    
    © [2025] [Berezin Maksim / MBer89 - TORG96]. Все права защищены.
        """
        keyboard = [[InlineKeyboardButton("📋 В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup)

    elif data == 'info_grafik':
        text = """
*🕐  График работы завода:*

☀️  *ДНЕВНАЯ СМЕНА*
*Сотрудники находящиеся на 5/2:*
    ПН --- Рабочий день
    ВТ --- Рабочий день
    СР --- Рабочий день
    ЧТ --- Рабочий день
    ПТ --- Рабочий день
    СБ --- Выходной / Рабоч. день при произв. необх.
    ВС --- Выходной

*Расписание перекуров и обедов:*
    1-й перекур --- 10:00 - 10:10
    Обед для 5/2 -- 12:00 - 13:00
    Обед Вахты ---- 12:00 - 12:30  
    2-й перекур --- 15:00 - 15:10
    3-й перекур --- 17:00 - 17:10
    Ужин Вахта --- 19:00 - 19:30

⚠️ Опаздания на смену, с перекуров и обедов ЗАПРЕЩЕНЫ ⚠️
            """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'info_grafik_master':
        text = """
    *🕐  График работы завода:*

☀️  *ДНЕВНАЯ СМЕНА* (10 часов)
*Сотрудники находящиеся на 5/2:*
        ПН --- 08:00 - 19:00
        ВТ --- 08:00 - 19:00   
        СР --- 08:00 - 19:00
        ЧТ --- 08:00 - 19:00
        ПТ --- 08:00 - 17:00
        СБ --- Выходной / 08:00 - 17:00 Рабоч. день при произв. необх.
        ВС --- Выходной

    *Сотрудники находящиеся на ВАХТЕ:* (11 часов)
        ПН --- 08:00 - 20:00
        ВТ --- 08:00 - 20:00   
        СР --- 08:00 - 20:00
        ЧТ --- 08:00 - 20:00
        ПТ --- 08:00 - 20:00
        СБ --- 08:00 - 20:00
        ВС --- Выходной
        
    *Сотрудники находящиеся на ВАХТЕ 5/2:* (10 часов)
        ПН --- 08:00 - 19:00
        ВТ --- 08:00 - 19:00   
        СР --- 08:00 - 19:00
        ЧТ --- 08:00 - 19:00
        ПТ --- 08:00 - 17:00
        СБ --- Выходной / 08:00 - 17:00 Рабоч. день при произв. необх.
        ВС --- Выходной

    *Расписание перекуров и обедов:*
        1-й перекур --- 10:00 - 10:10
        Обед для 5/2 -- 12:00 - 13:00
        Обед Вахты ---- 12:00 - 12:30
        Обед Вахты 5/2 - 12:00 - 12:30   
        2-й перекур --- 15:00 - 15:10
        3-й перекур --- 17:00 - 17:10
        Ужин Вахта --- 19:00 - 19:30


🌙  *НОЧНАЯ СМЕНА* (11 часов)
*График работы завода в НОЧНУЮ СМЕНУ:*

        ПН --- 19:00 - 07:00
        ВТ --- 19:00 - 07:00   
        СР --- 19:00 - 07:00
        ЧТ --- 19:00 - 07:00
        ПТ --- Выходной / Рабоч. день при произв. необх.
        СБ --- Выходной / Рабоч. день при произв. необх.
        ВС --- Выходной

         *Сотрудники находящиеся на ВАХТЕ:*
        ПН --- 19:00 - 07:00
        ВТ --- 19:00 - 07:00
        СР --- 19:00 - 07:00
        ЧТ --- 19:00 - 07:00
        ПТ --- 19:00 - 07:00
        СБ --- Выходной / Рабоч. день при произв. необх.
        ВС --- Выходной

    *Расписание перекуров и обедов в ночную смену:*
        1-й перекур --- 21:00 - 21:10
        Обед для всех -- 00:00 - 01:00 
        2-й перекур --- 03:00 - 03:10
        3-й перекур --- 05:00 - 05:10
        
В ночную смену обед для вахты и для остальных сотрудников 1 час!
В табеле должно стоять 11 часов!

⚠️ Опаздания на смену, с перекуров и обедов ЗАПРЕЩЕНЫ ⚠️
                """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='master_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'info_kty':
        text = """
🕐  Информация о КТУ:

КТУ по каждому сотруднику - считается ежедневно!

Каждую неделю скидывается информация КТУ смены, по каждому сотруднику!

КТУ:
0,850 - 85 % эффективности      (плохо)
1,000 - 100 % эффективности     (выполнил норму)
1,010 - 101 % эффективности     (перевыполнил норму на 1 %)
1,100 - 110 % эффективности     (отлично)

*Пример расчета ЗП за смену:*
    Формула:
        Часы отраб. х Ставку/ч х КТУ смены
        """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'info_number_master':
        text = """
☎️ *Номера руководителей завода:*

● *Цех проволоки и гальваники:* 
        Мастер цеха - Пивоварова Елена
        +79041721095
        Мастер цеха - Пахомов Владимир
        +79623185657

● *Цех упаковки:*
        Мастер цеха - Кочев Дмитрий
        +79221736163

● *Цех сварки:*
        Мастер цеха - Рахманов Сыймык
        +79533843238

● *Цех стеллажей:*
        Мастер цеха (заготовочный) - Морозов Яков
        +79090206725
        Мастер цеха - Першин Максим
        +79505459828

● *Цех лазер и труба:*
        Мастер цеха - Морозов Яков
        +79090206725

● *Цех покраски:*
        Мастер цеха - Солдатова Евгения 
        +79045441523

● *Цех лдсп:*    
        Мастер цеха - Кобыленко Денис 
        +79321210456

● *Начальник производства*
        Березин Максим 
        +79122114550

🚫 Звонки в алкогольном и наркотическом состоянии ЗАПРЕЩЕНЫ ‼️
🚫 Звонки в ночное время НЕ РЕКОМЕНДОВАНЫ, только в случае ЧП и непредвиденых обстоятельств ‼️
            """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'info_number_kadry':
        text = """
☎️ *Номера отдела кадров:*   

● *Офис/завод отдел кадров:* 
        Фадеева Анна
        +79667016524

● *График работы отдел кадров:* 
    С понедельника по пятницу --- 09:00 - 18:00

🚫 Звонки в алкогольном и наркотическом состоянии ЗАПРЕЩЕНЫ ‼️
🚫 Звонки в ночное время НЕ РЕКОМЕНДОВАНЫ, только в случае ЧП и непредвиденых обстоятельств ‼️
            """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'info_katigorya':
        text = """
*Категории и ставка/час:*

Категория - далее "кат."

Стажер 2 нед. 
1 кат. 
2 кат. 
3 кат. 
Ночная смена 

1 кат. ВАХТА 
2 кат. ВАХТА 
        """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'info_katigorya_master':
        text = """
    *Категории и ставка/час:*

    Категория - далее "кат."

    Стажер 2 нед. --- 200 руб./час
    1 кат. ---------- 242 руб./час
    2 кат. ---------- 275 руб./час
    3 кат. ---------- 300 руб./час
    Ночная смена ---- 290 руб./час

    1 кат. ВАХТА ---- 242 руб./час
    2 кат. ВАХТА ---- 275 руб./час
            """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='master_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'my_id':
        text = f"""
🆔 Ваш ID: `{user_id}`

Скопируй и передай, этот ID администратору для добавления в список получателей уведомлений @MBer89.

👤 Ваш профиль:
• Имя: {query.from_user.first_name}
• Username: @{query.from_user.username or 'не указан'}
        """
        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'test_notification':
        if user_id not in [YOUR_ADMIN_ID]:
            await query.answer("❌ Только для администратора", show_alert=True)
            return
        await query.answer("🔄 Отправляю тестовые уведомления...")
        await send_notifications_to_all()
        await query.edit_message_text(text="✅ Тестовые уведомления отправлены!\n/start")

    elif data == 'check_tasks':
        if user_id != YOUR_ADMIN_ID:
            await query.answer("❌ Только для администратора", show_alert=True)
            return
        if not completed_tasks:
            await query.edit_message_text("📊 Выполненных заданий пока нет\n/menu")
            return

        tasks_text = "📊 *Все задания:*\n\n"
        for task_id, task_data in completed_tasks.items():
            status_icon = "✅" if task_data.get('status') == 'выполнено' else "🟡"
            tasks_text += f"{status_icon} *{task_data['user_name']}* ({task_data['department']})\n"
            tasks_text += f"⏰ Начало: {task_data['start_time']}\n"
            if task_data.get('completion_time'):
                tasks_text += f"⏰ Завершение: {task_data['completion_time']}\n"
            tasks_text += f"📊 Статус: {task_data.get('status', 'неизвестно')}\n"
            tasks_text += f"📸 Фото: {task_data.get('photo_count', 0)} шт.\n"
            tasks_text += f"💬 {task_data.get('message', 'без текста')[:50]}...\n\n/menu"

        await query.edit_message_text(tasks_text, parse_mode='Markdown')

    elif data == 'master_settings':
        if user_id != YOUR_ADMIN_ID:
            await query.answer("❌ Только для администратора", show_alert=True)
            return
        settings_text = "👨‍🏭 Настройки мастеров по цехам:\n\n"
        for department, master_ids in MASTER_BY_DEPARTMENT.items():
            settings_text += f"• {department.upper()}: {', '.join(map(str, master_ids))}\n"
        settings_text += f"\nИспользуйте команду /set_master [цех] [id_мастера] для добавления мастера"

        keyboard = [[InlineKeyboardButton("📋  В меню", callback_data='menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=settings_text, reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'test_groups':
        if user_id != YOUR_ADMIN_ID:
            await query.answer("❌ Только для администратора", show_alert=True)
            return

        await query.answer("🔧 Тестирую отправку в группы...")

        test_message = "🔧 *Тестовое сообщение от бота*\n\nЭто тест отправки сообщений в группы цехов!"
        success_count = 0
        error_count = 0

        for department, group_id in GROUP_IDS.items():
            if not is_valid_group_id(group_id):
                logger.error(f"❌ Невалидный ID группы для цеха {department}: {group_id}")
                error_count += 1
                continue

            try:
                await application_instance.bot.send_message(
                    chat_id=group_id,
                    text=test_message,
                    parse_mode='Markdown'
                )
                logger.info(f"✅ Тестовое сообщение отправлено в группу {department}")
                success_count += 1
            except Exception as e:
                logger.error(f"❌ Ошибка отправки тестового сообщения в группу {department}: {e}")
                error_count += 1

        result_text = f"""
📊 *Результат теста отправки в группы:*

✅ Успешно: {success_count}
❌ Ошибок: {error_count}

Всего групп: {len(GROUP_IDS)}
        """
        await query.edit_message_text(result_text, parse_mode='Markdown')

    elif data == 'menu':
        user_name = query.from_user.first_name
        user_id = query.from_user.id
        keyboard = []
        for i in range(0, 9, 3):
            row = [
                InlineKeyboardButton(BUTTONS_CONFIG[i]["name"], url=BUTTONS_CONFIG[i]["url"]),
                InlineKeyboardButton(BUTTONS_CONFIG[i + 1]["name"], url=BUTTONS_CONFIG[i + 1]["url"]),
                InlineKeyboardButton(BUTTONS_CONFIG[i + 2]["name"], url=BUTTONS_CONFIG[i + 2]["url"])
            ]
            keyboard.append(row)

        keyboard.append([InlineKeyboardButton("🕐  График работы завода", callback_data='info_grafik')])
        keyboard.append([InlineKeyboardButton("☎️  Номера руководителей завода", callback_data='info_number_master')])
        keyboard.append([InlineKeyboardButton("☎️  Номера отдела кадров", callback_data='info_number_kadry')])
        keyboard.append([InlineKeyboardButton("🧮  Справка о КТУ", callback_data='info_kty')])
        keyboard.append([InlineKeyboardButton("⚖️  Категории и ставки", callback_data='info_katigorya')])
        keyboard.append([InlineKeyboardButton("ℹ️  Информация", callback_data='info')])
        keyboard.append([InlineKeyboardButton("🆔  Мой ID", callback_data='my_id')])

        # ⚠️ Кнопка для админа
        if user_id == YOUR_ADMIN_ID:
            keyboard.append([InlineKeyboardButton("🧠  Menu - Admin", callback_data='admin_menu')])

        if user_id in MASTER_ID:
            keyboard.append(
                [InlineKeyboardButton("👤  Menu - Master", callback_data='master_menu')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text=f"""
📋 Основное меню:\n
↗️ *Кнопки с сылками для перехода в инфокисок цеха:*

*1 ПР* - Инфокисок ПРОВОЛОКИ
*2 СВ* - Инфокисок СВАРКИ
*3 УП* - Инфокисок УПАКОВКИ
*4 ДСП* - Инфокисок ЛДСП
*5 ГЛ* - Инфокисок ГАЛЬВАНИКИ
*6 СТ* - Инфокисок СТЕЛЛАЖЕЙ
*7 ЛЗ* - Инфокисок ЛАЗЕРА
*8 ТР* - Инфокисок ТРУБЫ
*9 ПК* - Инфокисок ПОКРАСКИ

*Выбери и нажми необходимию кнопку* ⬇️
""", reply_markup=reply_markup, parse_mode='Markdown')

    elif data == 'master_menu':
        if user_id not in MASTER_ID:
            await query.answer("❌ Доступно только для мастеров", show_alert=True)
            return

        # Создаем меню для мастеров
        keyboard = [
            [InlineKeyboardButton("📐  Чертежи завод", url='https://torg96.bitrix24.ru/~FNyd2')],
            [InlineKeyboardButton("⚖️  Категории и ставки", callback_data='info_katigorya_master')],
            [InlineKeyboardButton("🕐  График работы завода", callback_data='info_grafik_master')],
            [InlineKeyboardButton("⚒️  Отчет заказов завод", url='https://tsoserver.ru/stanok2.php')],
            [InlineKeyboardButton("🖥️  Bitrix24", url='https://torg96.bitrix24.ru/online/')],
            [InlineKeyboardButton("📒  Остатки изделий",
                                  url='https://docs.google.com/spreadsheets/d/1mUiQFjk0Ux3KkiZraY7O3JLqmIDlpxKbCcCda6ckAI/edit?gid=1769002277#gid=1769002277')],
            [InlineKeyboardButton("🗄️  Хол.склад / Склад краски",
                                  url='https://docs.google.com/spreadsheets/d/1-oEaFj8GjU4W3BVw7dZO4vnoqab0IjR2vgFupWOwIHw/edit?gid=0#gid=0')],
            [InlineKeyboardButton("🧻  Реестр катушек СТ",
                                  url='https://docs.google.com/spreadsheets/d/19i5hQrFUEHWFKwAp0p9jQhoPMaRA71y_nANiz0wHq-A/edit?gid=0#gid=0')],
            [InlineKeyboardButton("⛓️  Реестр проволоки ПР",
                                  url='https://docs.google.com/spreadsheets/d/1ZpdVGfPpIUP7IVDxNq3kUAoB4ic4Oi8CM3qeTg_zEw0/edit?gid=71449538#gid=71449538')],
            [InlineKeyboardButton("📆  График дежурств",
                                  url='https://docs.google.com/spreadsheets/d/1KqxSmkn13UsXc3s5cjHCnmBuE7v7uEaIRpOCAE-bbzY/edit?gid=0#gid=0')],
            [InlineKeyboardButton("⚙️  Инструкции станков", url='https://torg96.bitrix24.ru/~XxNHM')],
            [InlineKeyboardButton("🚫  Штрафы завод",
                                                  url='https://docs.google.com/spreadsheets/d/1VQia-_BOpVbh5nH6FNRUhi43XxMZjtP9wYINQchy5Tg/edit?gid=0#gid=0')],
            [InlineKeyboardButton("⬅️  Назад в главное меню", callback_data='menu')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="👨‍🏭 *Меню мастера*\n\nВыберите нужный раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif data == 'admin_menu':

        if user_id != YOUR_ADMIN_ID:
            await query.answer("❌ Доступно только для Admin", show_alert=True)

            return

        keyboard = [

            [InlineKeyboardButton("📩 Тест уведомления - Admin", callback_data='test_notification')],

            [InlineKeyboardButton("📢 Рассылка в группы - Admin", callback_data='broadcast_menu')],  # Новая кнопка

            [InlineKeyboardButton("👤 Сотрудники в Месе - Admin", url='https://tsoserver.ru/sprab.php')],

            [InlineKeyboardButton("📊 Проверка заданий - Admin", callback_data='check_tasks')],

            [InlineKeyboardButton("👨‍🏭 Настройки мастеров - Admin", callback_data='master_settings')],

            [InlineKeyboardButton("🔧 Тест групп - Admin", callback_data='test_groups')],

            [InlineKeyboardButton("⬅️ Назад в главное меню", callback_data='menu')]

        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(

            text="👨‍🏭 *Меню Admin*\n\nВыберите нужный раздел:",

            reply_markup=reply_markup,

            parse_mode='Markdown'

        )
    # ⚠️ Добавим обработчик для новой кнопки рассылки
    elif data == 'broadcast_menu':
        if user_id != YOUR_ADMIN_ID:
            await query.answer("❌ Только для администратора", show_alert=True)
            return

        keyboard = [
            [InlineKeyboardButton("📝 Ввести сообщение", callback_data='broadcast_input')],
            [InlineKeyboardButton("🔙 Назад", callback_data='admin_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📢 *Рассылка сообщений в группы*\n\n"
                 "Вы можете отправить сообщение во все группы цехов.\n\n"
                 "*Группы для рассылки:*\n" +
                 "\n".join([f"• {dept.capitalize()}" for dept in GROUP_IDS.keys()]),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    elif data == 'broadcast_input':
        if user_id != YOUR_ADMIN_ID:
            await query.answer("❌ Только для администратора", show_alert=True)
            return

        # Сообщение с инструкцией
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data='broadcast_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            text="📝 *Ввод сообщения для рассылки*\n\n"
                 "Чтобы отправить сообщение во все группы, используйте команду:\n\n"
                 "`/broadcast Ваш текст сообщения`\n\n"
                 "*Пример:*\n"
                 "`/broadcast Всем цехам! Завтра проверка оборудования. Подготовьте рабочие места.`\n\n"
                 "Сообщение будет отправлено от имени бота с пометкой 'Сообщение от администратора'.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


# ⚠️ Обработчик команды /send_master_now
async def send_master_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in [YOUR_ADMIN_ID]:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    await update.message.reply_text("🔄 Начинаю отправку еженедельных уведомлений мастерам...")
    await send_master_notifications()
    await update.message.reply_text("✅ Еженедельные уведомления мастерам отправлены!")

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка при обработке update {update}: {context.error}")

# Команда для получения ID чата
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    chat_title = update.effective_chat.title or "личный чат"

    await update.message.reply_text(
        f"📋 ID этого чата:\n"
        f"• Название: {chat_title}\n"
        f"• ID: `{chat_id}`\n"
        f"• Тип: {chat_type}",
        parse_mode='Markdown'
    )

# Обработчик личных сообщений
async def handle_private_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "Используйте команды из меню 📋\nНажми кнопку: /start"
        )

# Команда для настройки мастеров
async def master_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    settings_text = "👨‍🏭 Настройки мастеров по цехам:\n\n"
    for department, master_ids in MASTER_BY_DEPARTMENT.items():
        settings_text += f"• {department.upper()}: {', '.join(map(str, master_ids))}\n"
    settings_text += f"\nИспользуйте /set_master [цех] [id_мастера] для добавления мастера"

    await update.message.reply_text(settings_text)

# Команда для установки мастеров
async def set_master_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Используйте: /set_master цех id_мастера\n"
            "Пример: /set_master проволока 123456789"
        )
        return

    department = context.args[0].lower()
    try:
        master_id = int(context.args[1])
        if department not in MASTER_BY_DEPARTMENT:
            MASTER_BY_DEPARTMENT[department] = []
        if master_id not in MASTER_BY_DEPARTMENT[department]:
            MASTER_BY_DEPARTMENT[department].append(master_id)
            await update.message.reply_text(f"✅ Мастер {master_id} добавлен в цех {department}")
        else:
            await update.message.reply_text(f"⚠️ Мастер {master_id} уже есть в цехе {department}")
    except ValueError:
        await update.message.reply_text("❌ ID мастера должен быть числом")

# ⚠️ Обработчик команды /test_failure
async def test_failure_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    # Создаем тестовое задание
    test_task = {
        'user_name': 'Тестовый Сотрудник',
        'department': 'лазер',
        'start_time': datetime.now().strftime('%H:%M:%S'),
        'notification_sent': False
    }

    pending_auto_tasks[999999999] = test_task  # Добавляем тестовый ID

    await update.message.reply_text("🔄 Тестирую отправку уведомлений о невыполнении...")
    await send_unfinished_tasks_notifications("тестовый день")
    await update.message.reply_text("✅ Тестовые уведомления отправлены!")

# В начале main() добавьте проверку прав
async def check_all_group_permissions():
    """Проверяет права бота во всех группах"""
    for department, group_id in GROUP_IDS.items():
        logger.info(f"🔍 Проверка прав бота в группе {department} (ID: {group_id})")
        has_permissions = await check_bot_permissions(group_id)
        if has_permissions:
            logger.info(f"✅ Бот имеет права для отправки сообщений в группу {department}")
        else:
            logger.error(f"❌ Бот НЕ имеет прав для отправки сообщений в группу {department}")

# ⚠️ Обработчик команды /check_groups
async def check_groups_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    await update.message.reply_text("🔍 Проверяю права бота в группах...")

    for department, group_id in GROUP_IDS.items():
        has_permissions = await check_bot_permissions(group_id)
        status = "✅" if has_permissions else "❌"
        await update.message.reply_text(
            f"{status} Группа {department} (ID: {group_id}): {'Доступ есть' if has_permissions else 'Нет доступа'}"
        )


# ⚠️ Обработчик команды /status
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    current_weekday = now.weekday()

    if current_weekday == 4:  # Пятница
        day_type = "пятница"
        start_time = MONITORING_START_TIME_FRIDAY
        end_time = MONITORING_END_TIME_FRIDAY
    else:
        day_type = "будний день (Пн-Чт)"
        start_time = MONITORING_START_TIME_WEEKDAYS
        end_time = MONITORING_END_TIME_WEEKDAYS

    status_message = f"""
📊 *Статус мониторинга*

• *День недели:* {day_type}
• *Мониторинг активен:* {'✅ Да' if is_monitoring_active else '❌ Нет'}
• *Время мониторинга:* {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}
• *Ожидающих заданий:* {len(pending_auto_tasks)}
• *Выполненных заданий:* {len(completed_tasks)}

*Текущее время:* {now.strftime('%H:%M:%S')}
"""

    await update.message.reply_text(status_message, parse_mode='Markdown')


# ⚠️ Обработчик команды /pending
async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not pending_auto_tasks:
        await update.message.reply_text("📭 Нет ожидающих заданий")
        return

    tasks_list = []
    for user_id, task_data in pending_auto_tasks.items():
        tasks_list.append(
            f"• {task_data['user_name']} ({task_data['department']}) - {task_data['status']} с {task_data['start_time']}"
        )

    message = f"📋 *Ожидающие задания:*\n\n" + "\n".join(tasks_list)
    await update.message.reply_text(message, parse_mode='Markdown')


# ⚠️ Обработчик команды /completed
async def completed_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not completed_tasks:
        await update.message.reply_text("✅ Нет выполненных заданий")
        return

    tasks_list = []
    for task_id, task_data in list(completed_tasks.items())[-10:]:  # Последние 10 заданий
        tasks_list.append(
            f"• {task_data['user_name']} ({task_data['department']}) - выполнено в {task_data['completion_time']}"
        )

    message = f"✅ *Последние выполненные задания ({len(completed_tasks)} всего):*\n\n" + "\n".join(tasks_list)
    await update.message.reply_text(message, parse_mode='Markdown')


# ⚠️ Обработчик команды /force_notify
async def force_notify_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительная отправка уведомлений о невыполнении"""
    user_id = update.effective_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Эта команда только для администратора")
        return

    now = datetime.now()
    current_weekday = now.weekday()
    day_type = "пятница" if current_weekday == 4 else "будний день"

    await update.message.reply_text(f"🔧 Принудительная отправка уведомлений о невыполнении ({day_type})...")

    # Запускаем отправку уведомлений
    await send_unfinished_tasks_notifications(day_type)

    await update.message.reply_text("✅ Уведомления о невыполнении отправлены!")


# ⚠️ Функция для установки меню бота
async def setup_bot_menu():
    """Устанавливает меню бота рядом с полем ввода сообщения"""
    try:
        # Базовые команды для всех пользователей
        commands = [
            BotCommand("start", "Запустить бота"),
            BotCommand("menu", "Главное меню"),
            BotCommand("id", "Узнать свой ID"),
            BotCommand("master", "Меню мастера"),
        ]

        # Устанавливаем команды для всех пользователей
        await application_instance.bot.set_my_commands(commands)

        logger.info("✅ Меню бота настроено")

    except Exception as e:
        logger.error(f"❌ Ошибка настройки меню бота: {e}")


# ⚠️ Обработчик команды /master для меню бота
async def master_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /master из меню бота"""
    user_id = update.message.from_user.id

    if user_id not in MASTER_ID:
        await update.message.reply_text("❌ Эта команда доступна только для мастеров")
        return

    # Создаем меню для мастеров
    keyboard = [
        [InlineKeyboardButton("📐  Чертежи завод", url='https://torg96.bitrix24.ru/~FNyd2')],
        [InlineKeyboardButton("⚖️  Категории и ставки", callback_data='info_katigorya_master')],
        [InlineKeyboardButton("🕐  График работы завода", callback_data='info_grafik_master')],
        [InlineKeyboardButton("⚒️  Отчет заказов завод", url='https://tsoserver.ru/stanok2.php')],
        [InlineKeyboardButton("🖥️  Bitrix24", url='https://torg96.bitrix24.ru/online/')],
        [InlineKeyboardButton("📒  Остатки изделий",
                              url='https://docs.google.com/spreadsheets/d/1mUiQFjk0Ux3KkiZraY7O3JLqmIDlpxKbCcCda6ckAI/edit?gid=1769002277#gid=1769002277')],
        [InlineKeyboardButton("🗄️  Хол.склад / Склад краски",
                              url='https://docs.google.com/spreadsheets/d/1-oEaFj8GjU4W3BVw7dZO4vnoqab0IjR2vgFupWOwIHw/edit?gid=0#gid=0')],
        [InlineKeyboardButton("🧻  Реестр катушек СТ",
                              url='https://docs.google.com/spreadsheets/d/19i5hQrFUEHWFKwAp0p9jQhoPMaRA71y_nANiz0wHq-A/edit?gid=0#gid=0')],
        [InlineKeyboardButton("⛓️  Реестр проволоки ПР",
                              url='https://docs.google.com/spreadsheets/d/1ZpdVGfPpIUP7IVDxNq3kUAoB4ic4Oi8CM3qeTg_zEw0/edit?gid=71449538#gid=71449538')],
        [InlineKeyboardButton("📆  График дежурств",
                              url='https://docs.google.com/spreadsheets/d/1KqxSmkn13UsXc3s5cjHCnmBuE7v7uEaIRpOCAE-bbzY/edit?gid=0#gid=0')],
        [InlineKeyboardButton("⚙️  Инструкции станков", url='https://torg96.bitrix24.ru/~XxNHM')],
        [InlineKeyboardButton("🚫  Штрафы завод",
                                              url='https://docs.google.com/spreadsheets/d/1VQia-_BOpVbh5nH6FNRUhi43XxMZjtP9wYINQchy5Tg/edit?gid=0#gid=0')],
        [InlineKeyboardButton("📋  Главное меню", callback_data='menu')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        text="👨‍🏭 *Меню мастера*\n\nВыберите нужный раздел:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ⚠️ Обработчик команды /broadcast
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id != YOUR_ADMIN_ID:
        await update.message.reply_text("❌ Команда только для администратора")
        return

    if not context.args:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n"
            "Используйте: /broadcast текст_сообщения\n"
            "Пример: /broadcast Важное сообщение для всех цехов!"
        )
        return

    message_text = " ".join(context.args)

    await update.message.reply_text("🔄 Начинаю рассылку сообщения в группы...")

    success_count = 0
    error_count = 0
    results = []

    for department, group_id in GROUP_IDS.items():
        if not is_valid_group_id(group_id):
            results.append(f"❌ {department}: невалидный ID группы")
            error_count += 1
            continue

        try:
            await application_instance.bot.send_message(
                chat_id=group_id,
                text=f"📢 *Сообщение от администратора:*\n\n{message_text}",
                parse_mode='Markdown'
            )
            results.append(f"✅ {department}: сообщение отправлено")
            success_count += 1
        except Exception as e:
            error_msg = f"❌ {department}: ошибка отправки"
            if "Chat not found" in str(e):
                error_msg += " (чат не найден)"
            elif "bot was blocked" in str(e).lower():
                error_msg += " (бот заблокирован)"
            elif "not enough rights" in str(e).lower():
                error_msg += " (недостаточно прав)"
            else:
                error_msg += f" ({str(e)})"

            results.append(error_msg)
            error_count += 1

    # Формируем итоговый отчет
    result_text = f"""
📊 *Результат рассылки:*

✅ Успешно: {success_count}
❌ Ошибок: {error_count}

*Детали:*
""" + "\n".join(results)

    await update.message.reply_text(result_text, parse_mode='Markdown')


# ⚠️ Обработчик кнопки рассылки в меню админа
async def broadcast_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != YOUR_ADMIN_ID:
        await query.answer("❌ Только для администратора", show_alert=True)
        return

    # Создаем форму для ввода сообщения
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data='admin_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="📢 *Рассылка сообщения в группы*\n\n"
             "Введите сообщение для рассылки в формате:\n"
             "`/broadcast Ваш текст сообщения`\n\n"
             "Сообщение будет отправлено во все группы цехов.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

#⚠️ Функция отправки уведомлений мастерам
async def send_tabel_notifications():
    """Отправляет уведомления мастерам"""
    global application_instance

    if application_instance is None:
        logger.error("Application instance not set!")
        return

    # Проверяем, не отправляли ли сегодня
    today_key = f"tabel_notify_{datetime.now().date().isoformat()}"
    if today_key in sent_notifications:
        logger.info("⚠️ Уведомления о табелях уже отправлены сегодня")
        return

    logger.info("📅 Отправка уведомлений о табелях")

    # Собираем всех мастеров
    all_masters = set()
    for masters in MASTER_BY_DEPARTMENT.values():
        all_masters.update(masters)

    success_count = 0
    error_count = 0

    for master_id in all_masters:
        try:
            await application_instance.bot.send_message(
                chat_id=master_id,
                text=TABEL_MESSAGE
            )
            success_count += 1

            # Добавляем в ожидание
            master_department = next(
                (dept for dept, masters in MASTER_BY_DEPARTMENT.items()
                 if master_id in masters), "неизвестный цех"
            )

            pending_tabels[master_id] = {
                'master_name': USER_NAMES.get(master_id, f"Мастер {master_id}"),
                'department': master_department
            }

            logger.info(f"✅ Уведомление отправлено мастеру {master_id}")

        except Exception as e:
            error_count += 1
            logger.error(f"❌ Ошибка отправки мастеру {master_id}: {e}")

    sent_notifications.add(today_key)
    logger.info(f"✅ Уведомления отправлены: {success_count} успешно, {error_count} с ошибками")

def check_tabel_hashtag(text):
    """Проверяет хештег табеля с учетом опечаток"""
    if not text:
        return False

    text_lower = text.lower()
    tabel_variants = [
        'табель',
        'табиль',
        'табел',
        'табил',
        'tabel',
        'table',
        '#табель',
        '#табиль',
        ' #табель',
        ' #табиль',
        'Табель',
    ]

    return any(variant in text_lower for variant in tabel_variants)

async def handle_tabel_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает фото табелей от мастеров"""
    if not is_tabel_monitoring_active:
        return

    # Проверяем, что это группа табелей
    if update.effective_chat.id not in GROUP_IDS_TABEL.values():
        return

    user_id = update.message.from_user.id

    # ДОБАВЬТЕ проверку текста/подписи с хештегом табеля
    message_text = update.message.caption or ""
    if not check_tabel_hashtag(message_text):  # Нужно создать эту функцию
        return

    # ЛЮБОЕ ФОТО от мастера = табель
    if update.message.photo:
        # Находим цех мастера
        master_department = next(
            (dept for dept, masters in MASTER_BY_DEPARTMENT.items()
             if user_id in masters), "неизвестный цех"
        )

        # Регистрируем табель
        completed_tabels[user_id] = {
            'master_name': USER_NAMES.get(user_id, f"Мастер {user_id}"),
            'department': master_department,
            'time': datetime.now().strftime('%H:%M')
        }

        # Удаляем из ожидающих
        if user_id in pending_tabels:
            del pending_tabels[user_id]

        logger.info(f"✅ Табель принят от {user_id}")

async def send_tabel_summary():
    """Отправляет сводку по табелям админу и в группу"""
    global application_instance

    if application_instance is None:
        logger.error("Application instance not set!")
        return

    # Формируем списки
    submitted = list(completed_tabels.values())
    not_submitted = list(pending_tabels.values())

    # 📊 СВОДКА ДЛЯ АДМИНА
    admin_message = f"""📊 СВОДКА ПО ТАБЕЛЯМ {datetime.now().strftime('%d.%m.%Y')}

✅ СДАЛИ ТАБЕЛЬ:
{chr(10).join([f"• {tabel['master_name']} ({tabel['department']}) - {tabel.get('time', 'время не указано')}" for tabel in submitted]) if submitted else "• Нет"}

❌ НЕ СДАЛИ ТАБЕЛЬ:
{chr(10).join([f"• {tabel['master_name']} ({tabel['department']})" for tabel in not_submitted]) if not_submitted else "• Все сдали!"}

Всего: {len(submitted)} сдали, {len(not_submitted)} не сдали"""

    try:
        await application_instance.bot.send_message(
            chat_id=YOUR_ADMIN_ID,
            text=admin_message
        )
        logger.info("✅ Сводка отправлена админу")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки админу: {e}")

    # 📊 СВОДКА В ГРУППУ ТАБЕЛЕЙ
    group_message = f"""📋 СВОДКА ПО ТАБЕЛЯМ {datetime.now().strftime('%d.%m.%Y')}

✅ СДАЛИ ТАБЕЛЬ:
{chr(10).join([f"• {tabel['master_name']} ({tabel['department']}) - {tabel.get('time', 'время не указано')}" for tabel in submitted]) if submitted else "• Нет"}

❌ НЕ СДАЛИ ТАБЕЛЬ:
{chr(10).join([f"• {tabel['master_name']} ({tabel['department']})" for tabel in not_submitted]) if not_submitted else "• Все сдали!"}

Период сдачи: {TABEL_MONITORING_START_TIME.strftime('%H:%M')} - {TABEL_MONITORING_END_TIME.strftime('%H:%M')}

Всего: {len(submitted)} сдали, {len(not_submitted)} не сдали"""

    # Отправляем в группу табелей
    for group_id in GROUP_IDS_TABEL.values():
        try:
            await application_instance.bot.send_message(
                chat_id=group_id,
                text=group_message
            )
            logger.info(f"✅ Сводка отправлена в группу табелей {group_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в группу табелей {group_id}: {e}")

    logger.info(f"📤 Сводки отправлены: {len(submitted)} сдали, {len(not_submitted)} не сдали")

async def start_tabel_monitoring():
    """Запускает мониторинг табелей"""
    global is_tabel_monitoring_active

    now = datetime.now()

    # Только пн-пт
    if now.weekday() >= 5:
        return

    start_time = datetime.combine(now.date(), TABEL_MONITORING_START_TIME)
    end_time = datetime.combine(now.date(), TABEL_MONITORING_END_TIME)

    if start_time <= now <= end_time:
        is_tabel_monitoring_active = True
        logger.info("🚀 Мониторинг табелей запущен")

        # Ждем до 10:00
        wait_seconds = (end_time - now).total_seconds()
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        is_tabel_monitoring_active = False
        logger.info("⏹️ Мониторинг табелей завершен")

        # Отправляем сводки
        await send_tabel_summary()

async def check_and_send_daily_notifications_tabel():
    while True:
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()

        # Будние дни
        if current_weekday < 5:
            # Уведомления о табелях в 7:40
            tabel_key = f"tabel_{now.date().isoformat()}"
            if (current_time.hour == TABEL_NOTIFICATION_TIME.hour and
                    current_time.minute == TABEL_NOTIFICATION_TIME.minute and
                    current_time.second == 0 and
                    tabel_key not in sent_notifications):
                logger.info("⏰ Время уведомлений о табелях")
                await send_tabel_notifications()
                asyncio.create_task(start_tabel_monitoring())
                sent_notifications.add(tabel_key)
                await asyncio.sleep(60)

        # Сброс в полночь
        if current_time.hour == 0 and current_time.minute == 0 and current_time.second == 0:
            completed_tabels.clear()
            pending_tabels.clear()
            # Чистим флаги
            keys_to_remove = [key for key in sent_notifications if key.startswith('tabel_')]
            for key in keys_to_remove:
                sent_notifications.discard(key)
            logger.info("🔄 Данные табелей очищены")

        await asyncio.sleep(1)

# Статус табелей
async def tabel_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ADMIN_ID:
        return

    status = "активен" if is_tabel_monitoring_active else "не активен"
    message = f"""📊 Текущий статус табелей:

Мониторинг: {status}
Сдали: {len(completed_tabels)}
Ожидают: {len(pending_tabels)}"""

    await update.message.reply_text(message)

# Принудительная сводка
async def force_tabel_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != YOUR_ADMIN_ID:
        return

    await update.message.reply_text("🔄 Отправляю сводку...")
    await send_tabel_summary()
    await update.message.reply_text("✅ Сводка отправлена!")


def display_license():
    license_text = """
    ⚠️ ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ

    Данное программное обеспечение является собственностью [Berezin Maksim / MBer89 - TORG96].
    Любое копирование, модификация или распространение без письменного разрешения
    запрещено и преследуется по закону.
    
    © [2025] [Berezin Maksim / MBer89 - TORG96]. Все права защищены.
    """
    print(license_text)


# Главная функция для запуска бота
def main():
    display_license()
    global application_instance
    application = Application.builder().token(API_TOKEN).build()
    application_instance = application

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("menu", menu_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("master", master_menu_command))  # Новая команда для мастеров
    application.add_handler(CommandHandler("admin_stats", admin_stats_command))
    application.add_handler(CommandHandler("send_now", send_now_command))
    application.add_handler(CommandHandler("set_message", set_message_command))
    application.add_handler(CommandHandler("set_weekday", set_weekday_message_command))
    application.add_handler(CommandHandler("set_friday", set_friday_message_command))
    application.add_handler(CommandHandler("check_tasks", check_tasks_command))
    application.add_handler(CommandHandler("master_settings", master_settings_command))
    application.add_handler(CommandHandler("set_master", set_master_command))
    application.add_handler(CommandHandler("getid", get_chat_id))
    application.add_handler(CommandHandler("send_master_now", send_master_now_command))
    application.add_handler(CommandHandler("test_failure", test_failure_command))
    application.add_handler(CommandHandler("check_groups", check_groups_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("completed", completed_command))
    application.add_handler(CommandHandler("force_notify", force_notify_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("tabel_status", tabel_status_command))
    application.add_handler(CommandHandler("tabel_summary", force_tabel_summary_command))


    async def startup_check():
        await check_all_group_permissions()
        await setup_bot_menu()  # Настраиваем меню при запуске

    asyncio.get_event_loop().run_until_complete(startup_check())

    asyncio.get_event_loop().create_task(check_and_send_daily_notifications())
    asyncio.get_event_loop().create_task(check_and_send_daily_notifications_tabel())

    # Добавляем обработчик inline-кнопок
    application.add_handler(CallbackQueryHandler(button_handler))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_private_messages))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, handle_group_messages))
    application.add_handler(MessageHandler(filters.PHOTO, handle_tabel_photos), group=1)
    application.add_handler(MessageHandler(
        filters.PHOTO & filters.Chat(chat_id=list(GROUP_IDS_TABEL.values())),
        handle_tabel_photos
    ), group=1)

    # Добавляем обработчик ошибок
    application.add_error_handler(error_handler)

    # Запускаем проверку уведомлений в фоне

    # Запускаем бота
    print("🤖 Бот запущен...")
    print(f"⏰ Уведомления Пн-Чт: {NOTIFICATION_TIME_WEEKDAYS.strftime('%H:%M')}")
    print(f"⏰ Уведомления Пт: {NOTIFICATION_TIME_FRIDAY.strftime('%H:%M')}")
    print(
        f"📊 Мониторинг Пн-Чт: {MONITORING_START_TIME_WEEKDAYS.strftime('%H:%M')}-{MONITORING_END_TIME_WEEKDAYS.strftime('%H:%M')}")
    print(
        f"📊 Мониторинг Пт: {MONITORING_START_TIME_FRIDAY.strftime('%H:%M')}-{MONITORING_END_TIME_FRIDAY.strftime('%H:%M')}")
    print(f"⏰ Время отправки уведомлений после мониторинга: {NOTIFICATION_AFTER_MONITORING_TIME.strftime('%H:%M')}")
    print(f"🎯 Получателей: {len(TARGET_USER_IDS)}")
    print("✅ Автоматическая система отслеживания фотоотчетов активирована")
    print("⚠️  Уведомления о невыполненных заданиях включены")
    print("🏷️ Расширенный контроль хештегов с учетом опечаток")
    print("⏹️ Для остановки нажмите Ctrl+C")

    application.run_polling()


if __name__ == '__main__':
    main()