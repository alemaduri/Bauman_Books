import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from config_reader import config
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiogram.utils.markdown as md
from aiogram.types import ParseMode

import sqlite3

STARTING_COINS = 1
ONLIST = 1
ONWAIT = 2
NOLIST = 3

BANNED = 1
NOT_BANNED = 0

ADMIN_IDS = [430814010, 810121389, 673698210]

DB_PATH = "/data/books.db"


class Create_Listing(StatesGroup):
    book_name = State()
    book_description = State()
    book_photo = State()
    book_accept = State()
    book_photos_done = State()


class Delete_book(StatesGroup):
    accept = State()


class Admin_delete_book(StatesGroup):
    accept = State()


class Mailing(StatesGroup):
    next_state = State()


class User_ban(StatesGroup):
    next_state = State()


# Эти фотки получены с помощью магии
MENU_PHOTO = "AgACAgIAAxkBAAIPhmTwat0uDPzGy8GzGuRslrxS53KeAAL_zjEbkieAS7w17GJ78so6AQADAgADeQADMAQ"
INFO_PHOTO = "AgACAgIAAxkBAAIUR2T3RSCD6yT8rm7BZN6uWco9Mne4AAJQ0TEbUJzBS015Qrlz_gABkAEAAwIAA3kAAzAE"

main_keyboard = types.ReplyKeyboardMarkup(
    resize_keyboard=True, input_field_placeholder="Что вы хотите сделать?"
)

main_keyboard.row(
    types.KeyboardButton(text="Выбрать книгу"),
    types.KeyboardButton(text="Поделиться книгой"),
).row(
    types.KeyboardButton(text="Мои книги"), types.KeyboardButton(text="Мои Book Coin")
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.bot_token.get_secret_value())
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(state="*", commands="cancel")
@dp.message_handler(Text(equals="отмена", ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply("Отмена")


@dp.message_handler(commands=["admin_all_books"])
async def admin_listing_all(message: types.Message, page=0):
    user_id = message.from_user.id
    if user_id not in ADMIN_IDS:
        await bot.send_message(user_id, "Вы не админ :)")
        return
    command = "ADMIN_GOTOPAGE"
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM Books WHERE book_status={ONLIST}")

    max_page = cursor.fetchone()[0]
    if page < 0:
        page = max_page - 1
    if page >= max_page:
        page = 0
    # print(f"LOG:listing_all:page:{page}")
    cursor.execute(
        f"SELECT * FROM Books WHERE book_status={ONLIST} LIMIT 1 OFFSET {page}"
    )

    book_info = cursor.fetchone()
    if not book_info:
        await message.answer(
            "Нет активных объявлений, скорее поделись книжкой с товарищами!"
        )
        connection.close()
        return

    (
        book_id,
        owner_user_id,
        book_name,
        book_desc,
        book_status,
    ) = book_info
    cursor.execute(f"SELECT * FROM Users WHERE user_id={owner_user_id}")
    owner_data = cursor.fetchone()
    (
        db_user_id,
        owner_user_id,
        owner_name,
        owner_nickname,
        owner_coins,
        isbanned,
    ) = owner_data
    catalogue_keyboard = types.InlineKeyboardMarkup()
    catalogue_keyboard.add(
        InlineKeyboardButton(f"Забанить перса", callback_data=f"ADMIN_DELETE|{book_id}")
    )

    cursor.execute(f"SELECT photo_tg_id FROM Photos WHERE book_id={book_id}")
    photo_tg_id = cursor.fetchone()[0]
    connection.close()
    caption_variable = md.text(f"Каталог книг: страница __{page+1}/{max_page}__\n")
    caption = md.text(
        md.text(f"ВЛАДЕЛЕЦ:{owner_name}\n"),
        md.text(f"TG: @{owner_nickname}\n"),
        md.text(f"id: @{owner_user_id}\n"),
        md.text(f"*{book_name}*\n"),
        md.text(f"{book_desc}\n"),
        caption_variable,
        sep="",
    )

    catalogue_keyboard.row(
        InlineKeyboardButton("⬅️", callback_data=f"{command}|{page-1}"),
        InlineKeyboardButton("➡️", callback_data=f"{command}|{page+1}"),
    )
    await bot.send_photo(
        photo=photo_tg_id,
        chat_id=message.from_user.id,
        caption=caption,
        reply_markup=catalogue_keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.callback_query_handler(
    lambda callback: callback.data.split("|")[0] in ["ADMIN_GOTOPAGE"]
)
async def admin_go_to_page(callback: types.CallbackQuery):
    command = callback.data.split("|")[0]
    page = int(callback.data.split("|")[1])
    user_id = callback.from_user.id
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM Books WHERE book_status={ONLIST}")

    max_page = cursor.fetchone()[0]
    if page < 0:
        page = max_page - 1
    if page >= max_page:
        page = 0
    # print(f"LOG:listing_all:page:{page}")
    cursor.execute(
        f"SELECT * FROM Books WHERE book_status={ONLIST} LIMIT 1 OFFSET {page}"
    )

    book_info = cursor.fetchone()

    (
        book_id,
        owner_user_id,
        book_name,
        book_desc,
        book_status,
    ) = book_info
    cursor.execute(f"SELECT * FROM Users WHERE user_id={owner_user_id}")
    owner_data = cursor.fetchone()
    (
        db_user_id,
        owner_user_id,
        owner_name,
        owner_nickname,
        owner_coins,
        isbanned,
    ) = owner_data
    catalogue_keyboard = types.InlineKeyboardMarkup()
    catalogue_keyboard.add(
        InlineKeyboardButton(f"Забанить перса", callback_data=f"ADMIN_DELETE|{book_id}")
    )

    cursor.execute(f"SELECT photo_tg_id FROM Photos WHERE book_id={book_id}")
    photo_tg_id = cursor.fetchone()[0]
    connection.close()
    caption_variable = md.text(f"Каталог книг: страница _{page+1}/{max_page}_\n")
    caption = md.text(
        md.text(f"ВЛАДЕЛЕЦ:{owner_name}\n"),
        md.text(f"TG: @{owner_nickname}\n"),
        md.text(f"*{book_name} *\n"),
        md.text(f"{book_desc}\n"),
        caption_variable,
        sep="",
    )

    catalogue_keyboard.row(
        InlineKeyboardButton("⬅️", callback_data=f"{command}|{page-1}"),
        InlineKeyboardButton("➡️", callback_data=f"{command}|{page+1}"),
    )
    media = types.InputMediaPhoto(photo_tg_id)
    await bot.edit_message_media(
        media=media,
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
    )

    await bot.edit_message_caption(
        chat_id=callback.from_user.id,
        caption=caption,
        message_id=callback.message.message_id,
    )

    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=catalogue_keyboard,
    )


@dp.callback_query_handler(
    lambda callback: callback.data.split("|")[0] in ["ADMIN_DELETE"]
)
async def delete_book(callback: types.CallbackQuery):
    book_id = callback.data.split("|")[1]
    message_text = md.text(md.text("Подтверди удаление книги"))
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Отмена", callback_data="ADMIN_CANCEL_DELETION"))
    kb.add(
        InlineKeyboardButton(
            "Подтвердить", callback_data=f"ADMIN_ACCEPT_DELETION|{book_id}"
        )
    )
    await bot.send_message(
        chat_id=callback.from_user.id, text=message_text, reply_markup=kb
    )
    await Admin_delete_book.accept.set()


@dp.callback_query_handler(state=Admin_delete_book.accept)
async def admin_delete_book_accept(callback: types.CallbackQuery, state: FSMContext):
    command = callback.data.split("|")[0]

    if command == "ADMIN_ACCEPT_DELETION":
        book_id = callback.data.split("|")[1]
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.execute(f"SELECT book_name FROM Books WHERE book_id={book_id}")
        book_name = cursor.fetchone()[0]
        cursor.execute(
            "UPDATE Books SET book_status=? WHERE book_id=?", (NOLIST, book_id)
        )
        cursor.execute(f"SELECT user_id FROM Books WHERE book_id={book_id}")
        owner_id = cursor.fetchone()[0]
        connection.commit()
        connection.close()
        admin_message_text = md.text(
            md.text("Теперь эта книга больше не будет показываться другими читателям."),
            sep="\n",
        )
        owner_message_text = md.text(
            md.text(
                f"Твоя книга *{book_name}* не соответствовала правилам сообщества Bauman Books и была удалена из каталога"
            )
        )

        await bot.send_message(
            chat_id=callback.from_user.id,
            text=admin_message_text,
            parse_mode=ParseMode.MARKDOWN,
        )
        await bot.send_message(
            chat_id=owner_id, text=owner_message_text, parse_mode=ParseMode.MARKDOWN
        )

    if command == "ADMIN_CANCEL_DELETION":
        message_text = md.text(
            md.text("Эта книга по-прежнему будет показываться другим читателям"),
        )
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    await state.finish()


@dp.message_handler(commands=["info"])
async def info_message(message: types.Message):
    caption = md.text(
        md.text("*Как работает обмен книгами?*\n"),
        md.text(
            "_Концепция очень проста, каждому участнику сообщества доступен каталог литературы, куда попадают книги, выложенные другими участниками._"
        ),
        md.text(
            "_Наверняка у тебя возникает вопрос, а вдруг кто-то просто будет собирать все книги и не делиться?_"
        ),
        md.text(
            "_Мы все просчитали!_ *Book Coin*_ - валюта внутри сообщества, позволяющая получать столько же книг, сколькими ты поделился._"
        ),
        md.text(
            "_Со старта мы дарим тебе 1 единицу_ *Book Coin*_, потому что видим в тебе потенциал читателя._"
        ),
        md.text(
            "_Это позволит попробовать Bauman Books абсолютно безвозмездно, но потом тоже нужно будет делиться, чтобы система не рухнула!_\n"
        ),
        md.text(
            "Мы стремимся сделать бота лучше. Если у тебя возникли ошибки или предложения по улучшению, ты можешь написать разработчикам:\n@maleyungthug\n@TeaWithMilkAndSugar"
        ),
        sep="\n",
    )
    await bot.send_photo(
        chat_id=message.chat.id,
        caption=caption,
        photo=INFO_PHOTO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard,
    )


@dp.message_handler(commands=["help"])
async def info_message(message: types.Message):
    caption = md.text(
        md.text("Список доступных комманд:"),
        md.text("/help - отобразить это меню"),
        md.text("/info - узнать больше о том, как устроен обмен"),
        md.text("/coins - посмотреть количество Book Coin"),
        md.text("/mine - посмотреть свои обьявления"),
        # md.text("/finish - заверешение отправки сообщений в режиме создания объявлений"),
        sep="\n",
    )
    await bot.send_photo(
        chat_id=message.chat.id,
        caption=caption,
        photo=MENU_PHOTO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard,
    )


@dp.message_handler(commands=["coins"])
async def display_coins_command(message: types.Message):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    user_id = message.from_user.id
    cursor.execute("SELECT coins FROM Users WHERE user_id=?", (user_id,))
    coins = cursor.fetchone()[0]
    cursor.execute(
        f"SELECT COUNT(*) FROM Books WHERE user_id={user_id} AND (book_status={ONLIST} OR book_status={ONWAIT})"
    )
    my_books_count = int(cursor.fetchone()[0])
    connection.close()

    message_text = md.text(
        md.text(f"Cейчас у тебя: *{coins}* Book Coin"),
        md.text("Поделись книжками чтобы получить больше Book Coin"),
        sep="\n",
    )
    await message.answer(message_text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands=["mine"])
async def my_books_command(message: types.Message, page=0):
    command = "MY_GOTOPAGE"
    user_id = message.from_user.id
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        f"SELECT COUNT(*) FROM Books WHERE user_id={user_id} AND book_status={ONLIST}"
    )

    max_page = cursor.fetchone()[0]
    if page < 0:
        page = max_page - 1
    if page >= max_page:
        page = 0
    # print(f"LOG:listing_all:page:{page}")
    cursor.execute(
        f"SELECT * FROM Books WHERE book_status={ONLIST} AND user_id={user_id} LIMIT 1 OFFSET {page}"
    )

    book_info = cursor.fetchone()
    if not book_info:
        await message.answer(
            'Пока что, у вас нет активных объявлений\nВы можете поделиться книгой с другими читателями, нажав кнопку "Поделиться книгой"'
        )
        connection.close()
        return

    (
        book_id,
        user_id,
        book_name,
        book_desc,
        book_status,
    ) = book_info

    catalogue_keyboard = types.InlineKeyboardMarkup()
    catalogue_keyboard.add(
        InlineKeyboardButton(f"Удалить", callback_data=f"DELETE|{book_id}")
    )

    cursor.execute(f"SELECT photo_tg_id FROM Photos WHERE book_id={book_id}")
    photo_tg_id = cursor.fetchone()[0]
    connection.close()
    if command == "ALL_GOTOPAGE":
        caption_variable = md.text(f"Каталог книг: страница __{page+1}/{max_page}__\n")
    if command == "MY_GOTOPAGE":
        caption_variable = md.text(f"Мои книги: страница __{page+1}/{max_page}__\n")

    caption = md.text(
        md.text(f"*{book_name}*\n"), md.text(f"{book_desc}\n"), caption_variable, sep=""
    )

    catalogue_keyboard.row(
        InlineKeyboardButton("⬅️", callback_data=f"{command}|{page-1}"),
        InlineKeyboardButton("➡️", callback_data=f"{command}|{page+1}"),
    )
    await bot.send_photo(
        photo=photo_tg_id,
        chat_id=message.from_user.id,
        caption=caption,
        reply_markup=catalogue_keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message_handler(commands=["start"])
async def start_message(message: types.Message):
    # Отправка стартового сообщения
    caption = md.text(
        md.text(f"Привет, {message.from_user.first_name}!"),
        md.text("Это *Bauman Books* - революционный сервис обмена книгами."),
        md.text("Список доступных команд:"),
        md.text("/help - отобразить это меню"),
        md.text("/info - узнать больше о том, как устроен обмен"),
        md.text("/coins - посмотреть количество Book Coin"),
        md.text("/mine - посмотреть свои обьявления"),
        md.text(
            "Мы стремимся сделать бота лучше. Если у тебя возникли ошибки или предложения по улучшению, ты можешь написать разработчикам:\n@maleyungthug\n@TeaWithMilkAndSugar"
        ),
        # md.text("/finish - заверешение отправки сообщений в режиме создания объявлений"),
        sep="\n",
    )

    await bot.send_photo(
        chat_id=message.chat.id,
        caption=caption,
        photo=MENU_PHOTO,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_keyboard,
    )

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM Users WHERE user_id=?)", (message.from_user.id,)
    )
    user_in_system = cursor.fetchone()[0]
    if not user_in_system:
        caption = None
        caption = md.text(
            md.text(
                f"Чтобы ты сразу мог начать пользоваться сервисом *Bauman Books* дарит тебе один Book Coin."
            ),
            md.italic("Зачем?"),
            md.text(
                "Book Coin'ы нужны для того, чтобы брать книги. Одна взятая тобой книга - один Book Coin"
            ),
            md.italic("Как их получить?"),
            md.text(
                "Чтобы получить Book Coin ты должен поделиться какой-нибдуь книгой с другими читателями. Так мы сохраняем баланс книг в сервисе"
            ),
            md.text("Чтобы узнать больше - пиши /info"),
            sep="\n",
        )
        await bot.send_message(
            chat_id=message.from_user.id,
            text=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard,
        )
        cursor.execute(
            "INSERT INTO Users (user_id, name, nickname, coins, isbanned) VALUES(?, ?, ?, ?, ?)",
            (
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username,
                STARTING_COINS,
                NOT_BANNED,
            ),
        )
        connection.commit()
        print(f"LOG: new user ({message.from_user.id})")
    connection.close()
    # Добавление пользователя в базу данных


@dp.message_handler(Text(equals="Мои Book Coin"))
async def display_coins(message: types.Message):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    user_id = message.from_user.id

    cursor.execute(
        "SELECT isbanned FROM Users WHERE user_id=?", (message.from_user.id,)
    )
    isbanned = cursor.fetchone()[0]

    if isbanned:
        await message.answer("Вы забанены")
        connection.close()
        return

    cursor.execute("SELECT coins FROM Users WHERE user_id=?", (user_id,))
    coins = cursor.fetchone()[0]
    cursor.execute(
        f"SELECT COUNT(*) FROM Books WHERE user_id={user_id} AND (book_status={ONLIST} OR book_status={ONWAIT})"
    )
    my_books_count = int(cursor.fetchone()[0])
    connection.close()

    message_text = md.text(
        md.text(f"Cейчас у тебя: *{coins}* Book Coin"),
        md.text("Поделись книжками чтобы получить больше Book Coin"),
        sep="\n",
    )
    await message.answer(message_text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(commands="admin_send_message")
async def all_users_mailing_1(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await bot.send_message(message.from_user.id, "Вы не админ :)")
        return
    await Mailing.next_state.set()


@dp.message_handler(state=Mailing.next_state)
async def all_users_mailing_2(message: types.Message, state: FSMContext):
    print("LOG:admin_send_message")
    mailing = message.text
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM Users")
    user_ids = cursor.fetchall()
    for user_id in user_ids:
        await bot.send_message(
            chat_id=user_id[0], text=message.text, entities=message.entities
        )
        print(f"LOG:admin_send_message:to_dest:{user_id}")
    connection.close()
    await state.finish()


@dp.message_handler(Text(equals=["Выбрать книгу", "Мои книги"]))
async def listing_all(message: types.Message, page=0):
    if message.text == "Выбрать книгу":
        command = "ALL_GOTOPAGE"
    if message.text == "Мои книги":
        command = "MY_GOTOPAGE"
    user_id = message.from_user.id
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT isbanned FROM Users WHERE user_id=?", (message.from_user.id,)
    )
    isbanned = cursor.fetchone()[0]

    if isbanned:
        await message.answer("Вы забанены")
        connection.close()
        return

    if command == "ALL_GOTOPAGE":
        cursor.execute(f"SELECT COUNT(*) FROM Books WHERE book_status={ONLIST}")
    if command == "MY_GOTOPAGE":
        cursor.execute(
            f"SELECT COUNT(*) FROM Books WHERE user_id={user_id} AND book_status={ONLIST}"
        )

    max_page = cursor.fetchone()[0]
    if page < 0:
        page = max_page - 1
    if page >= max_page:
        page = 0
    # print(f"LOG:listing_all:page:{page}")
    if command == "ALL_GOTOPAGE":
        cursor.execute(
            f"SELECT * FROM Books WHERE book_status={ONLIST} LIMIT 1 OFFSET {page}"
        )
    if command == "MY_GOTOPAGE":
        cursor.execute(
            f"SELECT * FROM Books WHERE book_status={ONLIST} AND user_id={user_id} LIMIT 1 OFFSET {page}"
        )

    book_info = cursor.fetchone()
    if not book_info:
        await message.answer(
            "Нет активных объявлений, скорее поделись книжкой с товарищами!"
        )
        connection.close()
        return

    (
        book_id,
        user_id,
        book_name,
        book_desc,
        book_status,
    ) = book_info

    catalogue_keyboard = types.InlineKeyboardMarkup()
    if command == "ALL_GOTOPAGE":
        catalogue_keyboard.add(
            InlineKeyboardButton(f"Хочу взять", callback_data=f"ALL_BOOK|{book_id}")
        )
    if command == "MY_GOTOPAGE":
        catalogue_keyboard.add(
            InlineKeyboardButton(f"Удалить", callback_data=f"DELETE|{book_id}")
        )

    cursor.execute(f"SELECT photo_tg_id FROM Photos WHERE book_id={book_id}")
    photo_tg_id = cursor.fetchone()[0]
    connection.close()
    if command == "ALL_GOTOPAGE":
        caption_variable = md.text(f"Каталог книг: страница __{page+1}/{max_page}__\n")
    if command == "MY_GOTOPAGE":
        caption_variable = md.text(f"Мои книги: страница __{page+1}/{max_page}__\n")

    caption = md.text(
        md.text(f"*{book_name}*\n"), md.text(f"{book_desc}\n"), caption_variable, sep=""
    )

    catalogue_keyboard.row(
        InlineKeyboardButton("⬅️", callback_data=f"{command}|{page-1}"),
        InlineKeyboardButton("➡️", callback_data=f"{command}|{page+1}"),
    )
    await bot.send_photo(
        photo=photo_tg_id,
        chat_id=message.from_user.id,
        caption=caption,
        reply_markup=catalogue_keyboard,
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.callback_query_handler(
    lambda callback: callback.data.split("|")[0] in ["ALL_GOTOPAGE", "MY_GOTOPAGE"],
)
async def go_to_page(callback: types.CallbackQuery):
    command = callback.data.split("|")[0]
    page = int(callback.data.split("|")[1])
    user_id = callback.from_user.id
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    if command == "ALL_GOTOPAGE":
        cursor.execute(f"SELECT COUNT(*) FROM Books WHERE book_status={ONLIST}")
    if command == "MY_GOTOPAGE":
        cursor.execute(
            f"SELECT COUNT(*) FROM Books WHERE user_id={user_id} AND book_status={ONLIST}"
        )

    max_page = cursor.fetchone()[0]
    if page < 0:
        page = max_page - 1
    if page >= max_page:
        page = 0
    # print(f"LOG:listing_all:page:{page}")
    if command == "ALL_GOTOPAGE":
        cursor.execute(
            f"SELECT * FROM Books WHERE book_status={ONLIST} LIMIT 1 OFFSET {page}"
        )
    if command == "MY_GOTOPAGE":
        cursor.execute(
            f"SELECT * FROM Books WHERE book_status={ONLIST} AND user_id={user_id} LIMIT 1 OFFSET {page}"
        )

    book_info = cursor.fetchone()
    book_id, user_id, book_name, book_desc, book_status = book_info

    catalogue_keyboard = types.InlineKeyboardMarkup()
    if command == "ALL_GOTOPAGE":
        catalogue_keyboard.add(
            InlineKeyboardButton(f"Хочу взять", callback_data=f"ALL_BOOK|{book_id}")
        )
    if command == "MY_GOTOPAGE":
        catalogue_keyboard.add(
            InlineKeyboardButton(f"Удалить", callback_data=f"DELETE|{book_id}")
        )

    cursor.execute(f"SELECT photo_tg_id FROM Photos WHERE book_id={book_id}")
    photo_tg_id = cursor.fetchone()[0]
    connection.close()
    if command == "ALL_GOTOPAGE":
        caption_variable = md.text(f"Каталог книг: страница __{page+1}/{max_page}__\n")
    if command == "MY_GOTOPAGE":
        caption_variable = md.text(f"Мои книги: страница __{page+1}/{max_page}__\n")

    caption = md.text(
        md.text(f"*{book_name}*\n"), md.text(f"{book_desc}\n"), caption_variable, sep=""
    )

    catalogue_keyboard.row(
        InlineKeyboardButton("⬅️", callback_data=f"{command}|{page-1}"),
        InlineKeyboardButton("➡️", callback_data=f"{command}|{page+1}"),
    )
    media = types.InputMediaPhoto(photo_tg_id)

    await bot.edit_message_media(
        media=media,
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
    )

    await bot.edit_message_caption(
        chat_id=callback.from_user.id,
        caption=caption,
        message_id=callback.message.message_id,
        parse_mode=ParseMode.MARKDOWN,
    )

    await bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=catalogue_keyboard,
    )


@dp.message_handler(Text(equals="Поделиться книгой"))
async def listing_start(message: types.Message):
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT isbanned FROM Users WHERE user_id=?", (message.from_user.id,)
    )
    isbanned = cursor.fetchone()[0]

    connection.close()
    if isbanned:
        await message.answer("Вы забанены")
    else:
        message_text = md.text(
            md.text("Введите название книги"),
            md.text("Если вы хотите отменить создание объявления - напишите /cancel"),
            sep="\n",
        )
        await Create_Listing.book_name.set()
        await message.reply(message_text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(state=Create_Listing.book_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["book_name"] = message.text
    await Create_Listing.next()
    message_text = md.text(
        md.text("Введите описание книги"),
        md.text("Если вы хотите отменить создание объявления - напишите /cancel"),
        sep="\n",
    )
    await message.reply(message_text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(state=Create_Listing.book_description)
async def process_desc(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["book_desc"] = message.text
    await Create_Listing.next()
    message_text = md.text(
        md.text("Пришлите фото книг"),
        md.text("Если вы хотите отменить создание объявления - напишите /cancel"),
        sep="\n",
    )
    await message.reply(message_text, parse_mode=ParseMode.MARKDOWN)


@dp.message_handler(
    content_types=types.ContentTypes.PHOTO, state=Create_Listing.book_photo
)
async def process_photos(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if "book_photos" not in data:
            data["book_photos"] = []
        photo = message.photo[-1]
        data["book_photos"].append(photo.file_id)
    await message.answer(
        "Отличное фото! В библиотеке твоя книга будет выглядеть вот так:"
    )
    async with state.proxy() as data:
        book_name = data["book_name"]
        book_desc = data["book_desc"]
        book_photos = data.get("book_photos", [])

        info_message = f"*Название книги:* {book_name}\n"
        info_message += f"*Описание книги:* {book_desc}"
        await message.answer(info_message, parse_mode=ParseMode.MARKDOWN)

        if book_photos:
            media = [types.InputMediaPhoto(media=photo) for photo in book_photos]
            await bot.send_media_group(message.from_user.id, media)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("Да! Добавить книгу в библиотеку", callback_data="button1")
    )
    keyboard.add(InlineKeyboardButton("Нет, хочу переделать", callback_data="button2"))
    await message.answer("Тебе нравится?", reply_markup=keyboard)

    await Create_Listing.book_accept.set()


@dp.callback_query_handler(
    lambda button: button.data in ["button1", "button2"],
    state=Create_Listing.book_accept,
)
async def process_callback_buttons(button: types.CallbackQuery, state: FSMContext):
    button_data = button.data
    user_id = button.from_user.id

    if button_data == "button1":
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        await bot.send_message(user_id, "Объявление было добавлено")
        async with state.proxy() as data:
            book_name = data["book_name"]
            book_desc = data["book_desc"]
            book_photos = data.get("book_photos", [])
            cursor.execute(
                "INSERT INTO Books (user_id, book_name, description, book_status) VALUES(?, ?, ?, ?)",
                (user_id, book_name, book_desc, ONLIST),
            )
            book_id = cursor.lastrowid
            for photo_tg_id in book_photos:
                cursor.execute(
                    "INSERT INTO Photos (book_id, photo_tg_id) VALUES(?, ?)",
                    (book_id, photo_tg_id),
                )
        connection.commit()
        connection.close()
    elif button_data == "button2":
        await bot.send_message(
            user_id, "Публикация отменена. Попробуй снова через «Поделиться книгой»"
        )

    await state.finish()


@dp.callback_query_handler(
    lambda button: button.data in ["button1", "button2"],
    state=Create_Listing.book_photo,
)
@dp.callback_query_handler(lambda callback: callback.data.split("|")[0] in ["ALL_BOOK"])
async def take_book(callback: types.CallbackQuery):
    command = callback.data.split("|")[0]
    book_id = callback.data.split("|")[1]
    user_id = callback.from_user.id
    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()
    cursor.execute(f"SELECT * FROM Books WHERE book_id={book_id}")
    book_info = cursor.fetchone()
    book_id, book_owner_id, book_name, book_desc, book_status = book_info
    cursor.execute(f"SELECT * from Users Where user_id={book_owner_id}")
    book_owner_info = cursor.fetchone()
    (
        book_owner_dbid,
        book_owner_id,
        book_owner_name,
        book_owner_nickname,
        book_owner_coins,
        book_owner_isbanned,
    ) = book_owner_info
    cursor.execute(f"SELECT * from Users WHERE user_id={user_id}")
    user_info = cursor.fetchone()
    user_dbid, user_id, user_name, user_nickname, user_coins, isbanned = user_info

    if book_owner_id == user_id:
        user_message_text = md.text(
            md.text("*Эта книга уже твоя*"),
            md.text(
                f"Если ты хочешь, чтобы другие читатели ее больше не видели, нажми кнопку"
            ),
            sep="\n",
        )
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton(f"Удалить", callback_data=f"DELETE|{book_id}"))
        await bot.send_message(
            chat_id=user_id,
            text=user_message_text,
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN,
        )
        connection.close()
        return

    if int(user_coins) > 0:
        cursor.execute(f"UPDATE Users SET coins=coins-1 WHERE user_id={user_id}")
        cursor.execute(
            "UPDATE Books SET book_status=? WHERE book_id=?", (ONWAIT, book_id)
        )
        connection.commit()
        connection.close()
        user_message_text = md.text(
            md.text("*Отличный выбор!*"),
            md.text(f"Пока что, владелец книги - {book_owner_name}"),
            md.text(
                f"Напиши ему, чтобы договориться о встрече: @{book_owner_nickname}"
            ),
            md.text(
                f"Сейчас на твоем счету {user_coins - 1} Book Coin, если владелец книги не подтвердит обмен, то Book Coin вернется обратно на счет"
            ),
            md.text(
                f"\nЧтобы заработать больше Book Coin'ов ты можешь поделиться книгой с другими читателями!"
            ),
            md.text("Чтобы это сделать просто нажми кнопку \"Поделиться книгой\""),
            sep="\n",
        )
        owner_message_text = md.text(
            md.text("Привет!"),
            md.text(f'{user_name} хочет взять твою книгу "{book_name}".'),
            md.text(
                f"Скоро он напишет тебе, но ты, конечно, можешь написать первым: @{user_nickname}"
            ),
            md.text(
                "Когда вы договоритесь - нажми эту кнопку, и твоя книжка исчезнет из библиотеки, а тебе начислятся Book Coin"
            ),
            sep="\n",
        )
        await bot.send_message(
            chat_id=user_id, text=user_message_text, parse_mode=ParseMode.MARKDOWN
        )
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton(
                text="Мы договорились",
                callback_data=f"SUCCESS_TRANSFER|{book_id}|{user_id}",
            )
        )
        kb.add(
            InlineKeyboardButton(
                text="Мы не договорились",
                callback_data=f"CANCEL_TRANSFER|{book_id}|{user_id}",
            )
        )
        await bot.send_message(
            chat_id=book_owner_id,
            text=owner_message_text,
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN,
        )

    else:
        message_text = md.text(
            md.text("У тебя не хватает *Book Coins*"),
            md.text(
                f"\nЧтобы их заработать, делись своими книгами с другими читателями!"
            ),
            md.text('Чтобы это сделать просто нажми кнопку _"Поделиться книгой"_'),
            sep="\n",
        )
        await bot.send_message(
            chat_id=user_id,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN,
        )


@dp.callback_query_handler(
    lambda callback: callback.data.split("|")[0]
    in ["SUCCESS_TRANSFER", "CANCEL_TRANSFER"]
)
async def handle_transfer_response(callback: types.CallbackQuery):
    callback_data = callback.data.split("|")
    command = callback_data[0]
    book_id = callback_data[1]
    user_that_recieves_id = callback_data[2]
    

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(f"SELECT book_name FROM Books WHERE book_id={book_id}")
    book_name = cursor.fetchone()[0]

    curr_user_id = callback.from_user.id
    cursor.execute(f"SELECT book_status FROM Books WHERE book_id={book_id}")
    book_status = cursor.fetchone()[0]
    if int(book_status) != ONWAIT:
        connection.close()
        return

    if command == "SUCCESS_TRANSFER":
        cursor.execute("SELECT coins FROM Users WHERE user_id=?", (curr_user_id,))
        coins_curr_user = cursor.fetchone()[0]
        cursor.execute(
            "SELECT coins FROM Users WHERE user_id=?", (user_that_recieves_id,)
        )
        coins_user_that_recieves = cursor.fetchone()[0]
        cursor.execute(
            "UPDATE Books SET book_status=? WHERE book_id=?", (NOLIST, book_id)
        )
        cursor.execute(
            "UPDATE Users SET coins=? WHERE user_id=?",
            (coins_curr_user + 1, curr_user_id),
        )

        await bot.send_message(
            curr_user_id,
            f"Поздравляем! Вы отдали книгу *{book_name}*!",
            parse_mode=ParseMode.MARKDOWN,
        )
        await bot.send_message(
            user_that_recieves_id,
            f"Поздравляем! Вы получили книгу *{book_name}*!",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif command == "CANCEL_TRANSFER":
        cursor.execute(
            "UPDATE Books SET book_status=? WHERE book_id=?", (ONLIST, book_id)
        )
        cursor.execute(
            f"UPDATE Users SET coins = coins + 1 WHERE user_id={user_that_recieves_id}"
        )
        await bot.send_message(curr_user_id, "Книга вернулась в каталог!")
        await bot.send_message(
            user_that_recieves_id,
            f"Вы не смогли договориться по поводу книги *{book_name}* \nBook Coin вернулся обратно на счёт",
            parse_mode=ParseMode.MARKDOWN,
        )

    connection.commit()
    connection.close()


@dp.callback_query_handler(lambda callback: callback.data.split("|")[0] in ["DELETE"])
async def delete_book(callback: types.CallbackQuery):
    book_id = callback.data.split("|")[1]
    message_text = md.text(md.text("Подтверди удаление книги"))
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Отмена", callback_data="CANCEL_DELETION"))
    kb.add(
        InlineKeyboardButton("Подтвердить", callback_data=f"ACCEPT_DELETION|{book_id}")
    )
    await bot.send_message(
        chat_id=callback.from_user.id, text=message_text, reply_markup=kb
    )
    await Delete_book.accept.set()


@dp.callback_query_handler(state=Delete_book.accept)
async def delete_book_accept(callback: types.CallbackQuery, state: FSMContext):
    command = callback.data.split("|")[0]

    if command == "ACCEPT_DELETION":
        book_id = callback.data.split("|")[1]
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE Books SET book_status=? WHERE book_id=?", (NOLIST, book_id)
        )
        connection.commit()
        connection.close()
        message_text = md.text(
            md.text("Теперь эта книга больше не будет показываться другими читателям."),
            md.text(
                'Ты по-прежнему можешь делиться книжной мудростью с помощью кнопки _"Поделиться книгой"_'
            ),
            sep="\n",
        )
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    if command == "CANCEL_DELETION":
        message_text = md.text(
            md.text("Эта книга по-прежнему будет показываться другим читателям"),
        )
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=message_text,
            parse_mode=ParseMode.MARKDOWN,
        )
    await state.finish()


@dp.message_handler(commands=["admin_ban", "admin_unban"])
async def ban_user(message: types.Message):
    command_type = ""
    if "/admin_ban" in message.text:
        command_type = "bam"
    elif "admin_unban" in message.text:
        command_type = "unban"
    banned_user_id = message.get_args()
    await ban_user_handle(message.from_user.id, banned_user_id, command_type)


async def ban_user_handle(user_id, banned_user_id, command_type):
    if user_id not in ADMIN_IDS:
        await bot.send_message(user_id, "Вы не админ :)")
    elif banned_user_id in ADMIN_IDS:
        await bot.send_message(user_id, "охуел???")
    else:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()

        if command_type == "ban":
            cursor.execute(
                "UPDATE Users SET isbanned=? WHERE user_id=?", (BANNED, banned_user_id)
            )
            cursor.execute(
                "UPDATE Books SET book_status=? WHERE user_id=?",
                (NOLIST, banned_user_id),
            )

            await bot.send_message(user_id, f"User {banned_user_id} был забанен")
            await bot.send_message(
                banned_user_id, "К сожалению, мы были вынуждены вас забанить"
            )
        elif command_type == "unban":
            cursor.execute(
                "UPDATE Users SET isbanned=? WHERE user_id=?",
                (NOT_BANNED, banned_user_id),
            )
            cursor.execute(
                "UPDATE Books SET book_status=? WHERE user_id=?",
                (ONLIST, banned_user_id),
            )

            await bot.send_message(user_id, f"User {banned_user_id} был разбанен")
            await bot.send_message(banned_user_id, "Вы были разбанены")
        connection.commit()
        connection.close()


# Начало поллинга
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    # try:
    #     connection = sqlite3.connect(DB_PATH)
    #     cursor = connection.cursor()
    #     cursor.execute("UPDATE Users SET coins=10 WHERE (nickname=\"maleyungthug\" OR nickname=\"dpilipp\" OR nickname=\"TeaWithMilkAndSugar\")")
    #     cursor.execute(f"SELECT * FROM Users")
    #     connection.commit()
    #     connection.close()
    # except:
    #     connection = sqlite3.connect(DB_PATH)
    #     cursor = connection.cursor()
    #     cursor.execute(f"CREATE TABLE Photos (photo_id INTEGER PRIMARY KEY AUTOINCREMENT,book_id INTEGER,photo_tg_id TEXT,FOREIGN KEY (book_id) REFERENCES Books (book_id) ON DELETE CASCADE)")
    #     cursor.execute(f"CREATE TABLE Users (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,name TEXT,nickname TEXT,coins INTEGER, isbanned INTEGER)")
    #     cursor.execute(f"CREATE TABLE Books (book_id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,book_name TEXT,description TEXT,book_status INTEGER,FOREIGN KEY (user_id) REFERENCES Users (user_id) ON DELETE CASCADE)")
    #     connection.commit()
    #     connection.close()

    asyncio.run(main())
