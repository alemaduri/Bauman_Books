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

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.bot_token.get_secret_value())
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=["info"])
async def display_info(message: types.Message):
    await bot.send_message(
        message.chat.id,
        md.text(
            md.text(f"Привет, {message.from_user.first_name}! Это *Bauman Books*"),
            md.text("Доступны следующие *команды:*"),
            md.text("/cancel - отмена какого-либо действия"),
            md.text(
                "/finish - заверешение отправки сообщений в режиме создания объявлений"
            ),
            md.text("/info - отображение информации"),
            md.text("/coins - отображение количества Book Coins"),
            sep="\n",
        ),
        parse_mode=ParseMode.MARKDOWN,
    )


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    kb = [
        [
            types.KeyboardButton(text="Посмотреть объявления"),
            types.KeyboardButton(text="Создать объявление"),
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="Что вы хотите сделать?",
    )
    await message.answer("Что вы хотите сделать?", reply_markup=keyboard)


class Create_Listing(StatesGroup):
    book_name = State()
    book_description = State()
    book_photo = State()
    book_photos_done = State()


class Display_Listings(StatesGroup):
    all_listings = State()
    listing = State()


@dp.message_handler(commands="coins")
async def display_coins(message: types.Message):
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    cursor.execute("SELECT coins FROM Users WHERE user_id=?", (message.from_user.id,))
    coins = cursor.fetchone()[0]
    await message.answer(
        f"Ваше количество монет: *{coins}*", parse_mode=types.ParseMode.MARKDOWN
    )


@dp.message_handler(state="*", commands="cancel")
@dp.message_handler(Text(equals="отмена", ignore_case=True), state="*")
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply("Отмена")


@dp.message_handler(Text(equals="Посмотреть объявления"))
async def listing_display(message: types.Message):
    await Display_Listings.all_listings.set()
    await message.answer("Все активные объявления:")

    await all_listings_display(message, state=Display_Listings.all_listings)


@dp.message_handler(state=Display_Listings.all_listings)
async def all_listings_display(message: types.Message, state: FSMContext):
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM Books")
    books_data = cursor.fetchall()

    info_message = f"----------------------------------\n"
    for book in books_data:
        book_id, user_id, book_name, description = book
        info_message += f"ID книги: {book_id}, Название книги: {book_name}\n"

    await message.answer(info_message, parse_mode=types.ParseMode.MARKDOWN)

    connection.close()

    await message.answer("Напишите ID интересующей книги")
    await Display_Listings.next()


@dp.message_handler(
    lambda message: not message.text.isdigit(), state=Display_Listings.listing
)
async def invalid_id(message: types.Message):
    await message.answer("Напишите ID или напиши /cancel")


@dp.message_handler(
    lambda message: message.text.isdigit(), state=Display_Listings.listing
)
async def listing_handle(message: types.Message, state: FSMContext):
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()
    book_id_message = message.text
    cursor.execute("SELECT * FROM Books WHERE book_id=?", (book_id_message,))
    book_info = cursor.fetchone()
    if not book_info:
        await message.answer("Напиши существующий или напиши /cancel")
    else:
        book_id, user_id, book_name, book_desc = book_info

        cursor.execute(
            "SELECT photo_tg_id FROM Photos WHERE book_id=?", (book_id_message,)
        )
        book_photos = cursor.fetchall()

        info_message = f"----------------------------------\n"
        info_message += f"ID книги: {book_id}, Название книги: {book_name}\n"
        info_message += f"Описание: {book_desc}\n"

        await message.answer(info_message, parse_mode=types.ParseMode.MARKDOWN)

        if book_photos:
            media = [types.InputMediaPhoto(media=photo[0]) for photo in book_photos]
            await bot.send_media_group(message.from_user.id, media)

        async with state.proxy() as data:
            data["user_id"] = user_id
            data["book_id"] = book_id

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("Написать владельцу ✅", callback_data="dm_owner")
        )
        keyboard.add(InlineKeyboardButton("Назад в каталог ❌", callback_data="go_back"))
        await message.answer(
            "-----------Выберите действие-----------", reply_markup=keyboard
        )

    connection.close()


@dp.callback_query_handler(
    lambda button: button.data in ["dm_owner", "go_back"],
    state=Display_Listings.listing,
)
async def go_back_to_listing_start(button: types.CallbackQuery, state: FSMContext):
    button_data = button.data

    if button_data == "dm_owner":
        async with state.proxy() as data:
            user_id = data.get("user_id")
        connection = sqlite3.connect("books.db")
        cursor = connection.cursor()
        cursor.execute("SELECT coins FROM Users WHERE user_id=?", (user_id,))
        coins = cursor.fetchone()[0]
        if coins > 0:
            coins -= 1
            cursor.execute("UPDATE Users SET coins=? WHERE user_id=?", (coins, user_id))
            connection.commit()
            await enough_coins(state, cursor, connection)
        else:
            connection.close()
            await bot.send_message(user_id, "У вас не хватает монет :(")
            await state.finish()
    elif button_data == "go_back":
        await state.finish()
        await listing_display(button.message)


async def enough_coins(state: FSMContext, cursor, connection):
    async with state.proxy() as data:
        user_id = data.get("user_id")
        book_id = data.get("book_id")
    cursor.execute("SELECT nickname FROM Users WHERE user_id=?", (user_id,))
    username = cursor.fetchone()[0]

    await bot.send_message(user_id, f"Напишите владельцу! @{username}")

    cursor.execute("DELETE FROM Books WHERE book_id=?", (book_id,))
    cursor.execute(
        "DELETE FROM Photos WHERE book_id=?", (book_id,)
    )  # Я НЕ ЕБУ ПОЧЕМУ ON CASCADE НЕ РАБОТАЕТ
    connection.commit()

    connection.close()
    await state.finish()


@dp.message_handler(Text(equals="Создать объявление"))
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

    # await message.reply('Пришлите еще фото или напишите /finish для завершения')


# @dp.message_handler(state=Create_Listing.book_photos_done)
# async def process_photos_after(message: types.Message):
#     await message.reply('Пришлите еще фото или напишите /finish для завершения')


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
            cursor.execute(
                "SELECT EXISTS(SELECT 1 FROM Users WHERE user_id=?)", (user_id,)
            )
            username_check = cursor.fetchone()[0]
            if not username_check:
                cursor.execute(
                    "INSERT INTO Users (user_id, name, nickname, coins) VALUES(?, ?, ?, ?)",
                    (
                        user_id,
                        button.from_user.first_name,
                        button.from_user.username,
                        STARTING_COINS,
                    ),
                )
            cursor.execute(
                "INSERT INTO Books (user_id, book_name, description) VALUES(?, ?, ?)",
                (user_id, book_name, book_desc),
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


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
