import asyncio
import logging
from aiogram import Bot, Dispatcher, types

#from config_reader import config

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
# Объект бота
bot = Bot(token="6577349724:AAFhGJJVmqWvUVDsqlAOFwvSt29CiXYlvE8")
# Диспетчер
dp = Dispatcher(bot)


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


# from aiogram import F


# @dp.message(F.text.lower() == "посмотреть объявления")
# async def list_everything(message: types.Message):
#     await message.answer("Отличный выбор!")


class Form(StatesGroup):
    book_name = State()


# @dp.message(F.text.lower() == "создать объявление")
# async def make_listing(message: types.Message):
#     await Form.book_name.set()
#     await message.reply("Введите название книги")
#     user_text = message.text
#     # await message.reply(user_text)
#     # await State.finish()

# @dp.message_handler(state=Form.book_name)
# async def process_name(message: types.Message, state: FSMContext):
#     async with state.proxy() as data:
#         data['name'] = message.text

#     await Form.next()
#     await message.reply("Введите название книги")

@dp.message_handler(Text(equals="Создать объявление"))
async def listing_start(message: types.Message):
    await Form.book_name.set()
    await message.reply("Введите название книги")


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
