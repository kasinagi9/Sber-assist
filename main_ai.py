from symbol import with_item
from aiogram.bot import BaseBot
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, WebAppInfo
from aiogram.types import ParseMode
from aiogram import Dispatcher, Bot, types
from aiogram.utils import executor
from langchain_community.vectorstores import AwaDB
from sqlalchemy.orm import defer

from config_ai import *

storage = MemoryStorage()
bot = Bot(token)
dp = Dispatcher(bot, storage = storage)


class BotStage(StatesGroup):
    FirstName = State()
    LastName = State()
    Polis = State()
    Chat = State()


@dp.message_handler(commands="start", state = "*")
async def cmd_start(message: types.Message):
    await message.answer("Здравствуйте, я ассистент в вопросах поликлиники!\nНужно пройти процедуру авторизации, пришли свое имя")
    await BotStage.FirstName.set()

@dp.message_handler(state=BotStage.FirstName)
async def FirstName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await message.answer("Отлично, теперь мне нужна твоя фамилия")
    await BotStage.LastName.set()


@dp.message_handler(state=BotStage.LastName)
async def LastName(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['surname'] = message.text
    await message.answer("Прекрасно, теперь мне нужен номер полиса")
    await BotStage.Polis.set()


@dp.message_handler(state=BotStage.Polis)
async def Polis(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['polis'] = message.text
    await message.answer("Спасибо за предоставленные данные, вы вошли в личный кабинет!")
    verif(data['name'], data["surname"], data["polis"])
    await BotStage.Chat.set()


@dp.message_handler(state=BotStage.Chat)
async def user_mes(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        test = get_context(message.text, dict=data)
        print(test)
        await message.answer(text=f'{generate_answer(message.text, test, user_dict=data)["generation"]}')


if __name__ == '__main__':
    executor.start_polling(dp)
