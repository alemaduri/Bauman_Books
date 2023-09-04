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

STARTING_COINS = 3
ONLIST = 1
ONWAIT = 2
NOLIST = 3


class Create_Listing(StatesGroup):
    book_name = State()
    book_description = State()
    book_photo = State()
    book_photos_done = State()


class Mailing(StatesGroup):
    next_state = State()


# Эти фотки получены с помощью магии
MENU_PHOTO = "AgACAgIAAxkBAAIPhmTwat0uDPzGy8GzGuRslrxS53KeAAL_zjEbkieAS7w17GJ78so6AQADAgADeQADMAQ"

main_keyboard = types.ReplyKeyboardMarkup(
    resize_keyboard=True, input_field_placeholder="Что вы хотите сделать?"
)

main_keyboard.row(
    types.KeyboardButton(text="Выбрать книгу"),
    types.KeyboardButton(text="Поделиться книгой"),
).row(
    types.KeyboardButton(text="Мои книги"), types.KeyboardButton(text="Мои BookCoins")
)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.bot_token.get_secret_value())
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=["start"])
async def start_message(message: types.Message):
    # Отправка стартового сообщения
    caption = md.text(
        md.text(f"Привет, {message.from_user.first_name}!"),
        md.text("Это *Bauman Books* - революционный сервис обмена книгами."),
        md.text("Список доступных комманд:"),
        md.text("/info - узнать больше о том, как устроен обмен"),
        md.text("/coins - посмотреть количество BookCoins"),
        md.text("/mine - посмотреть свои обьявления"),
        md.text("/cancel - отмена какого-либо действия"),
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

    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM Users WHERE user_id=?)", (message.from_user.id,)
    )
    user_in_system = cursor.fetchone()[0]

    if not user_in_system:
        caption = None
        caption = md.text(
            md.text(
                f"Чтобы ты сразу мог начать пользоваться сервисом *Bauman Books* дарит тебе три Book Coin'a."
            ),
            md.italic("Зачем?"),
            md.text(
                "Book Coin'ы нужны для того, чтобы брать книги. Одна взятая тобой книга - один Book Coin"
            ),
            md.italic("Как их получить?"),
            md.text(
                "Чтобы получить Book Coin ты должен поделиться какой-нибдуь книгой с другими читателями. Так мы сохраняем баланс книг в сервисе"
            ),
            md.text("Чтобы узанть больше пиши /info"),
            sep="\n",
        )
        await bot.send_message(
            chat_id=message.from_user.id,
            text=caption,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_keyboard,
        )
        cursor.execute(
            "INSERT INTO Users (user_id, name, nickname, coins) VALUES(?, ?, ?, ?)",
            (
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.username,
                STARTING_COINS,
            ),
        )
        connection.commit()
        connection.close()
        print(f"LOG: new user ({message.from_user.id})")
    # Добавление пользователя в базу данных


# @dp.message_handler(commands=["end"])
# async def end_run(message: types.Message):
#     if message.from_user.id == 810121389:
#         print("LOG: Bot ended")
#         dp.stop_polling()


@dp.message_handler(Text(equals="Мои BookCoins"))
async def display_coins(message: types.Message):
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()

    cursor.execute("SELECT coins FROM Users WHERE user_id=?", (message.from_user.id,))
    coins = cursor.fetchone()[0]
    postfix = ""
    match_coins = coins % 10
    if match_coins in [0, 5, 6, 7, 8, 9]:
        postfix = "монет"
    elif match_coins == 1:
        postfix = "монета"
    else:
        postfix = "монеты"
    connection.close()
    await message.answer(
        f"У вас: *{coins}* {postfix}", parse_mode=types.ParseMode.MARKDOWN
    )


@dp.message_handler(commands="admin_send_message")
async def all_users_mailing_1(message: types.Message):
    await Mailing.next_state.set()


@dp.message_handler(state=Mailing.next_state)
async def all_users_mailing_2(message: types.Message, state: FSMContext):
    mailing = message.text
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM Users")
    user_ids = cursor.fetchall()
    for user_id in user_ids:
        print(f"user_id: {user_id[0]}")
        await bot.send_message(chat_id=user_id[0], text=mailing)
    connection.close()
    await state.finish()


@dp.message_handler(Text(equals=["Выбрать книгу", "Мои книги"]))
async def listing_all(message: types.Message, page=0):
    if message.text == "Выбрать книгу":
        command = "ALL_GOTOPAGE"
    if message.text == "Мои книги":
        command = "MY_GOTOPAGE"
    user_id = message.from_user.id
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    if command == "ALL_GOTOPAGE":
        cursor.execute("SELECT COUNT(*) FROM Books")
    if command == "MY_GOTOPAGE":
        cursor.execute(f"SELECT COUNT(*) FROM Books WHERE user_id={user_id}")

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
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    if command == "ALL_GOTOPAGE":
        cursor.execute("SELECT COUNT(*) FROM Books")
    if command == "MY_GOTOPAGE":
        cursor.execute(f"SELECT COUNT(*) FROM Books WHERE user_id={user_id}")

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
    await Create_Listing.book_name.set()
    await message.reply("Введите название книги")


@dp.message_handler(state=Create_Listing.book_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["book_name"] = message.text
    await Create_Listing.next()
    await message.reply("Введите описание книги")


@dp.message_handler(state=Create_Listing.book_description)
async def process_desc(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["book_desc"] = message.text
    await Create_Listing.next()
    await message.reply("Пришлите фото книг")
    await message.answer(
        "После отправки всех необходимых фото напишите /finish для завершения"
    )


@dp.message_handler(
    content_types=types.ContentTypes.PHOTO, state=Create_Listing.book_photo
)
async def process_photos(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if "book_photos" not in data:
            data["book_photos"] = []
        photo = message.photo[-1]
        data["book_photos"].append(photo.file_id)


@dp.message_handler(commands=["finish"], state=Create_Listing.book_photo)
async def finish_listing(message: types.Message, state: FSMContext):
    await message.answer("Итоговое объявление:")

    async with state.proxy() as data:
        book_name = data["book_name"]
        book_desc = data["book_desc"]
        book_photos = data.get("book_photos", [])

        info_message = f"*Название книги:* {book_name}\n"
        info_message += f"*Описание книги:* {book_desc}"
        await message.answer(info_message, parse_mode=types.ParseMode.MARKDOWN)

        if book_photos:
            media = [types.InputMediaPhoto(media=photo) for photo in book_photos]
            await bot.send_media_group(message.from_user.id, media)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Добавить объявление ✅", callback_data="button1"))
    keyboard.add(InlineKeyboardButton("Отменить объявление ❌", callback_data="button2"))
    await message.answer(
        "-----------Выберите действие-----------", reply_markup=keyboard
    )


@dp.callback_query_handler(
    lambda button: button.data in ["button1", "button2"],
    state=Create_Listing.book_photo,
)
async def process_callback_buttons(button: types.CallbackQuery, state: FSMContext):
    button_data = button.data
    user_id = button.from_user.id

    if button_data == "button1":
        connection = sqlite3.connect("books.db")
        cursor = connection.cursor()
        await bot.send_message(user_id, "Объявление было добавлено")
        async with state.proxy() as data:
            book_name = data["book_name"]
            book_desc = data["book_desc"]
            book_photos = data.get("book_photos", [])
            cursor.execute("SELECT coins FROM Users WHERE user_id=?", (user_id,))
            coins = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE Users SET coins=? WHERE user_id=?", (coins + 1, user_id)
            )
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
        await bot.send_message(user_id, "Объявление не было добавлено")

    await state.finish()


# Начало поллинга
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
