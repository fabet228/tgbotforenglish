from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = os.getenv("Id")
# Временное хранилище данных
user_data = {}
sc_data = {}

# Состояния для обработки ввода пользователя
WAITING_FOR_NAME, WAITING_FOR_CONTACT, WAITING_FOR_AGE, WAITING_FOR_LEVEL = range(4)

WT_NM, WT_TXT, WT_PHOTO = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("📅 Оставить заявку", callback_data="request")],
        [InlineKeyboardButton("📊 Ближайший speaking club", callback_data="check_file")],
        [InlineKeyboardButton("ℹ️ Информация о боте", callback_data="info")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет, я бот [Имя]! С моей помощью ты можешь узнать всё о speaking club'ах и подать заявку на участие",
        reply_markup=reply_markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()  # Убираем "часики" на кнопке

    data = query.data

    if data == "request":
        await new_request_check(query)
    elif data == "info":
        await query.edit_message_text(

            "  Тут будет доп информация",
            reply_markup=create_back_keyboard()
        )
    elif data == "back_to_main":
        # Обычная кнопка - редактирует сообщение
        await main_menu_from_callback(query)
    elif data == "back_to_main_delete":
        # Кнопка для удаления сообщения с фото
        await back_to_main_delete_handler(query)
    elif data == "confirm_request":
        await start_new_request(query, context)
    elif data == "check_file":
        await show_speaker_club_info(query)
    elif data == "skip_photo":
        await skip_photo_handler(query, context)
    elif data == "add_photo":
        await add_photo_handler(query, context)


async def back_to_main_delete_handler(query):
    """Обработчик кнопки 'Главное меню' которая удаляет сообщение"""
    # Удаляем текущее сообщение
    try:
        await query.message.delete()
    except:
        pass  # Игнорируем ошибку если нельзя удалить сообщение

    # Отправляем новое сообщение с главным меню
    keyboard = [
        [InlineKeyboardButton("📅 Оставить заявку", callback_data="request")],
        [InlineKeyboardButton("📊 Ближайший speaking club", callback_data="check_file")],
        [InlineKeyboardButton("ℹ️ Информация о боте", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        'Привет, я бот [Имя]! С моей помощью ты можешь узнать всё о speaking club\'ах и подать заявку на участие',
        reply_markup=reply_markup
    )


async def add_photo_handler(query, context):
    """Обработчик кнопки добавления фото"""
    user_id = query.from_user.id
    if user_id in sc_data:
        # Изменяем текст сообщения на "Можете отправлять фото"
        await query.edit_message_text(
            "📷 Можете отправлять фото",
            reply_markup=create_back_keyboard()
        )


async def skip_photo_handler(query, context):
    """Обработчик пропуска добавления фото"""
    user_id = query.from_user.id
    if user_id in sc_data:
        # Сохраняем speaking club без фото
        await save_speaker_club_to_excel(
            sc_data[user_id]['name_sc'],
            sc_data[user_id]['txt_sc'],
            None
        )

        await query.edit_message_text(
            f"✅ Speaking club создан!\n\nНазвание: {sc_data[user_id]['name_sc']}\nОписание: {sc_data[user_id]['txt_sc']}",
            reply_markup=create_back_keyboard()
        )

        # Очищаем данные
        del sc_data[user_id]


async def show_speaker_club_info(query):
    """Показывает информацию о текущем speaking club"""
    try:
        file_path = "SpeakerClubs.xlsx"

        if not os.path.exists(file_path):
            await query.edit_message_text(
                "❌ Информация о speaking club пока не добавлена",
                reply_markup=create_back_keyboard()
            )
            return

        df = pd.read_excel(file_path)
        if df.empty:
            await query.edit_message_text(
                "❌ Информация о speaking club пока не добавлена",
                reply_markup=create_back_keyboard()
            )
            return

        name = df.iloc[0]['Название']
        description = df.iloc[0]['Описание']
        photo_path = df.iloc[0]['Фото'] if 'Фото' in df.columns else None

        # Проверяем, есть ли фото и существует ли файл
        has_photo = False
        if photo_path and isinstance(photo_path, str) and photo_path != 'None':
            if os.path.exists(photo_path):
                has_photo = True

        if has_photo:
            delete_keyboard = [
                [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main_delete")]
            ]
            delete_reply_markup = InlineKeyboardMarkup(delete_keyboard)

            # Отправляем фото с описанием как новое сообщение
            with open(photo_path, 'rb') as photo:
                await query.message.reply_photo(
                    photo=photo,
                    caption=f"📅 **Ближайший Speaking Club**\n\n{name}\n\n{description}",
                    reply_markup=delete_reply_markup
                )
            # Удаляем предыдущее сообщение с кнопкой
            try:
                await query.message.delete()
            except:
                pass  # Игнорируем ошибку если нельзя удалить сообщение
        else:
            # Отправляем только текст с обычной кнопкой
            await query.edit_message_text(
                f"📅 **Ближайший Speaking Club**\n\n{name}\n\n{description}",
                reply_markup=create_back_keyboard()
            )

    except Exception as e:
        print(f"Ошибка при чтении информации о speaking club: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при загрузке информации",
            reply_markup=create_back_keyboard()
        )


async def start_new_request(query, context):
    """Начинает процесс подачи заявки"""
    user_id = query.from_user.id
    user_data[user_id] = {'state': WAITING_FOR_NAME}

    await query.edit_message_text(
        "Чтобы оставить заявку, напишите сначала ваше имя и фамилию:",
        reply_markup=create_back_keyboard()
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений для сбора данных заявки"""
    user_id = update.message.from_user.id
    text = update.message.text

    # Проверяем, находится ли пользователь в процессе заявки
    if user_id in user_data:
        await process_user_request(update, context, user_id, text)
    elif user_id in sc_data:
        await process_sc_request(update, context, user_id, text)
    else:
        # Если пользователь не в процессе заявки, игнорируем сообщение
        return


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фотографий для speaking club"""
    user_id = update.message.from_user.id

    if user_id in sc_data and sc_data[user_id].get('state') == WT_PHOTO:
        # Получаем фото с наилучшим качеством
        photo = update.message.photo[-1]
        photo_file = await photo.get_file()

        # Создаем папку для фото если её нет
        os.makedirs("speaker_club_photos", exist_ok=True)

        # Сохраняем фото
        photo_path = f"speaker_club_photos/speaker_club_{user_id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        await photo_file.download_to_drive(photo_path)

        # Сохраняем путь к фото в данных
        sc_data[user_id]['photo_path'] = photo_path

        # Сохраняем данные в Excel
        await save_speaker_club_to_excel(
            sc_data[user_id]['name_sc'],
            sc_data[user_id]['txt_sc'],
            photo_path
        )

        await update.message.reply_text(
            f"✅ Speaking club создан с фото!\n\nНазвание: {sc_data[user_id]['name_sc']}\nОписание: {sc_data[user_id]['txt_sc']}",
            reply_markup=create_back_keyboard()
        )

        # Очищаем данные
        del sc_data[user_id]


async def process_user_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обрабатывает заявку пользователя"""
    user_state = user_data[user_id].get('state')

    if user_state == WAITING_FOR_NAME:
        # Сохраняем имя и запрашиваем контакт
        user_data[user_id]['name'] = text
        user_data[user_id]['state'] = WAITING_FOR_AGE

        await update.message.reply_text(
            f"Спасибо, {text}! Теперь напишите ваш возраст",
            reply_markup=create_back_keyboard()
        )

    elif user_state == WAITING_FOR_AGE:
        user_data[user_id]['age'] = text
        user_data[user_id]['state'] = WAITING_FOR_LEVEL

        await update.message.reply_text(
            "Спасибо! Теперь понадобиться ваш уровень",
            reply_markup=create_back_keyboard()
        )

    elif user_state == WAITING_FOR_LEVEL:
        user_data[user_id]['lv'] = text
        user_data[user_id]['state'] = WAITING_FOR_CONTACT

        await update.message.reply_text(
            "Последнее что осталось добавить - ваш контак(мобильный телефон)",
            reply_markup=create_back_keyboard()
        )

    elif user_state == WAITING_FOR_CONTACT:
        # Сохраняем контакт и завершаем заявку
        if len(text) == 11 or len(text) == 12:
            user_data[user_id]['contact'] = text
            await save_to_excel(user_id, update, context)

            # Очищаем данные пользователя
            del user_data[user_id]

            await update.message.reply_text(
                "✅ Ваша заявка успешно отправлена! Спасибо за обращение.",
                reply_markup=main_menu_keyboard()
            )
        else:
            await update.message.reply_text(
                "Неверно написан номер телефона, провертье пожалуйста и отправьте занаво",
                reply_markup=create_back_keyboard()
            )


async def process_sc_request(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, text: str):
    """Обрабатывает создание speaking club"""
    user_state = sc_data[user_id].get('state')

    if user_state == WT_NM:
        # Сохраняем имя и запрашиваем описание
        sc_data[user_id]['name_sc'] = text
        sc_data[user_id]['state'] = WT_TXT

        await update.message.reply_text(
            "Теперь введите описание",
            reply_markup=create_back_keyboard()
        )

    elif user_state == WT_TXT:
        sc_data[user_id]['txt_sc'] = text
        sc_data[user_id]['state'] = WT_PHOTO

        # Предлагаем добавить фото или пропустить
        keyboard = [
            [InlineKeyboardButton("📷 Добавить фото", callback_data="add_photo")],
            [InlineKeyboardButton("⏭ Пропустить", callback_data="skip_photo")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Хотите добавить фото для speaking club?",
            reply_markup=reply_markup
        )


async def save_to_excel(user_id, update, context):
    """Сохраняет данные пользователя в Excel файл"""
    try:
        file_path = "Zapisi.xlsx"

        # Получаем данные пользователя
        name = user_data[user_id].get('name')
        contact = user_data[user_id].get('contact')
        age = user_data[user_id].get('age')
        lv = user_data[user_id].get('lv')
        username = f"@{update.message.from_user.username}" if update.message.from_user.username else "Не указан"

        # Создаем новую запись
        new_data = {
            'Имя Фамилия': [name],
            'Возраст': [age],
            'Уровень': [lv],
            'Контакт': [contact],
            'Username': [username],
            'User ID': [user_id],
            'Дата': [pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')]
        }

        df_new = pd.DataFrame(new_data)

        # Если файл существует, добавляем к существующим данным
        if os.path.exists(file_path):
            df_existing = pd.read_excel(file_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        # Сохраняем файл
        df_combined.to_excel(file_path, index=False)

    except Exception as e:
        print(f"Ошибка при сохранении в Excel: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при сохранении заявки. Пожалуйста, попробуйте позже."
        )


async def save_speaker_club_to_excel(name, description, photo_path):
    """Сохраняет или заменяет информацию о speaking club в Excel файл"""
    try:
        file_path = "SpeakerClubs.xlsx"

        # Создаем новую запись (всегда одна запись - заменяем существующую)
        new_data = {
            'Название': [name],
            'Описание': [description],
            'Фото': [photo_path],
            'Дата создания': [pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')]
        }

        df_new = pd.DataFrame(new_data)

        # Сохраняем файл (перезаписываем полностью)
        df_new.to_excel(file_path, index=False)

    except Exception as e:
        print(f"Ошибка при сохранении speaking club в Excel: {e}")
        raise e


async def check_old_request(update: Update, context: ContextTypes):
    # Проверяем ID пользователя
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет прав для использования этой команды!")
        return

    # Логика команды для администратора
    response = ""
    file_path = "Zapisi.xlsx"
    df = pd.read_excel(file_path)
    k = len(df)
    response += f"Кол-во заявок: {k}\n\n"

    for i in range(0, k):
        response += f"Заявка {i + 1}:\n"
        n = df.iat[i, 0]
        response += f"  Имя: {n}\n"
        n = df.iat[i, 1]
        response += f"  Возраст: {n}\n"
        n = df.iat[i, 2]
        response += f"  Уровень: {n}\n"
        n = df.iat[i, 3]
        response += f"  Контактный телефон: {n}\n"
        n = df.iat[i, 4]
        response += f"  Username тг: {n}\n"
        n = df.iat[i, 6]
        response += f"  Дата и время подачи заявки: {n}\n\n"

    await update.message.reply_text(
        response,
        reply_markup=create_back_keyboard()
    )


async def new_sc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс создания speaking club"""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ У вас нет прав для использования этой команды!")
        return

    user_id = update.effective_user.id
    sc_data[user_id] = {'state': WT_NM}

    await update.message.reply_text(
        "Напишите название нового speaking club:",
        reply_markup=create_back_keyboard()
    )


async def new_request_check(query):
    """Начало процесса подачи заявки"""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_request")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "Подтвердите начало подачи заявки",
        reply_markup=reply_markup
    )


def create_back_keyboard():
    """Создает клавиатуру с обычной кнопкой 'Главное меню' (редактирует сообщение)"""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_delete_back_keyboard():
    """Создает клавиатуру с кнопкой 'Главное меню' которая удаляет сообщение"""
    keyboard = [
        [InlineKeyboardButton("🏠 Главное меню", callback_data="back_to_main_delete")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def main_menu_from_callback(query):
    """Возврат в главное меню из callback (редактирует сообщение)"""
    keyboard = [
        [InlineKeyboardButton("📅 Оставить заявку", callback_data="request")],
        [InlineKeyboardButton("📊 Ближайший speaking club", callback_data="check_file")],
        [InlineKeyboardButton("ℹ️ Информация о боте", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        'Привет, я бот Кати! С моей помощью ты можешь узнать всё о speaking club\'ах и подать заявку на участие',
        reply_markup=reply_markup
    )


async def main_menu_from_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню из сообщения"""
    keyboard = [
        [InlineKeyboardButton("📅 Оставить заявку", callback_data="request")],
        [InlineKeyboardButton("📊 Ближайший speaking club", callback_data="check_file")],
        [InlineKeyboardButton("ℹ️ Информация о боте", callback_data="info")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        'Привет, я бот Кати! С моей помощью ты можешь узнать всё о speaking club\'ах и подать заявку на участие',
        reply_markup=reply_markup
    )


def main_menu_keyboard():
    """Главное меню с кнопками"""
    keyboard = [
        [InlineKeyboardButton("📅 Оставить заявку", callback_data="request")],
        [InlineKeyboardButton("📊 Ближайший speaking club", callback_data="check_file")],
        [InlineKeyboardButton("ℹ️ Информация о боте", callback_data="info")]
    ]
    return InlineKeyboardMarkup(keyboard)


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(CommandHandler("request", check_old_request))
    application.add_handler(CommandHandler("new_sc", new_sc))
    application.add_handler(CommandHandler("menu", main_menu_from_message))

    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()