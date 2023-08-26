import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import PhotoSize
#from config_reader import config
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text
from aiogram.utils import markdown
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token="6577349724:AAFhGJJVmqWvUVDsqlAOFwvSt29CiXYlvE8")
storage = MemoryStorage()
# Диспетчер
dp = Dispatcher(bot, storage=storage)


@dp.message_handler(commands=["answer"])
async def cmd_answer(message: types.Message):
    await message.answer("Это простой ответ")

# Хэндлер на команду /start
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

class Form(StatesGroup):
    book_name = State()
    book_description = State()
    book_photo = State()

@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.finish()
    await message.reply('ОК')

@dp.message_handler(Text(equals="Создать объявление"))
async def listing_start(message: types.Message):
    await Form.book_name.set()
    await message.reply("Введите название книги")

@dp.message_handler(state=Form.book_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['book_name'] = message.text
    await Form.next()
    await message.reply("Введите описание книги")

@dp.message_handler(state=Form.book_description)
async def process_desc(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['book_desc'] = message.text
    await Form.next()
    await message.reply("Пришлите фото книг")

@dp.message_handler(content_types=types.ContentTypes.PHOTO, state=Form.book_photo)
async def process_photos(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'book_photos' not in data:
            data['book_photos'] = []
        photo = message.photo[-1]
        data['book_photos'].append(photo.file_id)

    await message.reply('Пришлите еще фото или напишите /finish для завершения')
    #await state.finish()

@dp.message_handler(commands=['finish'], state=Form.book_photo)
async def finish_listing(message: types.Message, state: FSMContext):
    await message.answer("Итоговое объявление:")

    async with state.proxy() as data:
        book_name = data['book_name']
        book_desc = data['book_desc']
        book_photos = data.get('book_photos', [])

        # Отправляем текст информации
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


    #await state.finish()

@dp.callback_query_handler(lambda button: button.data in ["button1", "button2"], state=Form.book_photo)
async def process_callback_buttons(button: types.CallbackQuery, state: FSMContext):
    button_data = button.data
    user_id = button.from_user.id

    if button_data == "button1":
        await bot.send_message(user_id, "Объявление было добавлено")
    elif button_data == "button2":
        await bot.send_message(user_id, "Объявление не было добавлено")

    
    await state.finish()

# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
