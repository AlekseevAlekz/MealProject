import asyncio
import logging
import sys

from aiogram import Dispatcher, Bot, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.utils.formatting import as_list, as_marked_section, Bold
from aiogram.utils.markdown import hbold

from TGBot.recipes_handler import router
from TGBot.token_data import BOT_TOKEN

dp = Dispatcher()
dp.include_router(router)


@dp.message(CommandStart())
async def cmd_start_handler(message=Message):
    """ Обработчик команды /start"""
    kb = [
        [
            KeyboardButton(text='Команды'),
            KeyboardButton(text='Описание бота')
        ],
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )
    await message.answer(
        f"Привет, {hbold(message.from_user.full_name)}! С чего начнем?",
        reply_markup=keyboard
    )


@dp.message(F.text.lower() == "команды")
async def commands(message: Message):
    response = as_list(
        as_marked_section(
            Bold("Команды"),
            "/category_search_random - для указания количества рецептов",
            marker="✅ "
        )
    )
    await message.answer(**response.as_kwargs())


@dp.message(F.text.lower() == "описание бота")
async def description(message: Message):
    await message.answer("Этот бот предоставляет информацию о рецептах с сайта https://www.themealdb.com")


async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
