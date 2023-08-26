import asyncio
import logging
from aiogram import Bot, Dispatcher, types
#from config_reader import config
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.utils import markdown
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import sqlite3

logging.basicConfig(level=logging.INFO)
bot = Bot(token="6577349724:AAFhGJJVmqWvUVDsqlAOFwvSt29CiXYlvE8")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

@dp.message_handler(commands=['start'])
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

class Display_Listings(StatesGroup):
    all_listings = State()
    listing = State()

@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply('ОК')

@dp.message_handler(Text(equals="Посмотреть объявления"))
async def listing_start(message: types.Message):
    await Display_Listings.all_listings.set()

@dp.message_handler(state=Display_Listings.all_listings)
async def all_listings_display(message: types.Message, state: FSMContext):
    await message.answer("Все активные объявления:")
    connection = sqlite3.connect("books.db")
    cursor = connection.cursor()

    connection.commit()
    connection.close()

@dp.message_handler(Text(equals="Создать объявление"))
async def listing_start(message: types.Message):
    await Create_Listing.book_name.set()
    await message.reply("Введите название книги")

@dp.message_handler(state=Create_Listing.book_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['book_name'] = message.text
    await Create_Listing.next()
    await message.reply("Введите описание книги")

@dp.message_handler(state=Create_Listing.book_description)
async def process_desc(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['book_desc'] = message.text
    await Create_Listing.next()
    await message.reply("Пришлите фото книг")

@dp.message_handler(content_types=types.ContentTypes.PHOTO, state=Create_Listing.book_photo)
async def process_photos(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'book_photos' not in data:
            data['book_photos'] = []
        photo = message.photo[-1]
        data['book_photos'].append(photo.file_id)

    await message.reply('Пришлите еще фото или напишите /finish для завершения')

@dp.message_handler(commands=['finish'], state=Create_Listing.book_photo)
async def finish_listing(message: types.Message, state: FSMContext):
    await message.answer("Итоговое объявление:")

    async with state.proxy() as data:
        book_name = data['book_name']
        book_desc = data['book_desc']
        book_photos = data.get('book_photos', [])

        info_message = f"*Название книги:* {book_name}\n"
        info_message += f"*Описание книги:* {book_desc}"
        await message.answer(info_message, parse_mode=types.ParseMode.MARKDOWN)

        if book_photos:
            media = [types.InputMediaPhoto(media=photo) for photo in book_photos]
            await bot.send_media_group(message.from_user.id, media)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Добавить объявление ✅", callback_data="button1"))
    keyboard.add(InlineKeyboardButton("Отменить объявление ❌", callback_data="button2"))
    await message.answer("-----------Выберите действие-----------", reply_markup=keyboard)

@dp.callback_query_handler(lambda button: button.data in ["button1", "button2"], state=Create_Listing.book_photo)
async def process_callback_buttons(button: types.CallbackQuery, state: FSMContext):
    button_data = button.data
    user_id = button.from_user.id

    if button_data == "button1":
        connection = sqlite3.connect("books.db")
        cursor = connection.cursor()
        await bot.send_message(user_id, "Объявление было добавлено")
        async with state.proxy() as data:
            book_name = data['book_name']
            book_desc = data['book_desc']
            book_photos = data.get('book_photos', [])
            cursor.execute("INSERT INTO Users (user_id, name, nickname) VALUES(?, ?, ?)", (user_id, button.from_user.first_name, button.from_user.username))
            cursor.execute("INSERT INTO Books (user_id, book_name, description) VALUES(?, ?, ?)", (user_id, book_name, book_desc))
            book_id = cursor.lastrowid
            for photo_tg_id in book_photos:
                cursor.execute("INSERT INTO Photos (book_id, photo_tg_id) VALUES(?, ?)", (book_id, photo_tg_id))
            connection.commit()
            connection.close()
    elif button_data == "button2":
        await bot.send_message(user_id, "Объявление не было добавлено")

    
    await state.finish()

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
