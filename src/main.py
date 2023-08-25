import asyncio
import logging
from aiogram import Bot, Dispatcher, types

#from config_reader import config
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text

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

@dp.message_handler(Text(equals="Создать объявление"))
async def listing_start(message: types.Message):
    await Form.book_name.set()
    await message.reply("Введите название книги")

@dp.message_handler(state=Form.book_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['book_name'] = message.text
    await message.answer(data['book_name'])
    #await state.finish()
    await Form.next()


# Запуск процесса поллинга новых апдейтов
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
