import asyncio
import logging
import random
import aiohttp
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from googletrans import Translator

from aiogram import Router

from TGBot.token_data import THEMEALDB_API

router = Router()
translator = Translator()


class RecipeStates(StatesGroup):
    waiting_for_category = State()
    waiting_for_recipes = State()
    showing_recipe_details = State()


@router.message(Command('category_search_random'))
async def category_search_random(message: Message, command: CommandObject, state: FSMContext):
    if command.args is None:
        await message.answer("Вы забыли указать количество рецептов!\n"
                             "Пожалуйста повторите команду и передайте число.\n"
                             "Пример: /category_search_random 2")

        return

    try:
        count_recipes = int(command.args)
    except ValueError:
        await message.answer(f"Не удалось распознать значение {command.args}\n"
                             f"Пример: /category_search_random 2")
        return

    await state.set_data({'count_recipes': count_recipes})

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{THEMEALDB_API}/categories.php") as response:
                response.raise_for_status()
                data = await response.json()

                if 'categories' not in data or not data['categories']:
                    await message.answer("Не удалось получить список категорий! Попробуйте еще раз.")
                    return

                categories = [category['strCategory'] for category in data['categories']]

                builder = ReplyKeyboardBuilder()
                for date_item in categories:
                    builder.add(KeyboardButton(text=date_item))
                builder.adjust(4)

                await message.answer("Выберите категорию блюда:",
                                     reply_markup=builder.as_markup(resize_keyboard=True))
                await state.set_state(RecipeStates.waiting_for_category.state)


        except aiohttp.ClientError as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await message.answer("Произошла ошибка при получении категорий. Попробуйте позже.")
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            await message.answer("Произошла неожиданная ошибка. Попробуйте позже.")


@router.message(RecipeStates.waiting_for_category)
async def category_choosing_handler(message: Message, state: FSMContext):
    category = message.text
    count_recipes = (await state.get_data()).get('count_recipes', 1)

    async with aiohttp.ClientSession as session:
        try:
            async with session.get(f"{THEMEALDB_API}/filter.php?c={category}") as response:
                response.raise_for_status()
                data = await response.json()

                if 'meals' not in data or not data['meals']:
                    await message.answer("Для этой категории не найдены рецепты!")
                    return

                meals = random.choices(data['meals'], k=count_recipes)
                meal_names = [meal['strMeal'] for meal in meals]
                meal_ids = [meal['idMeal'] for meal in meals]

                await state.set_data({'meal_ids': meal_ids, 'meals': meals})

                translated_names = [translator.translate(name, dest='ru').text for name in meal_names]

                builder = ReplyKeyboardBuilder()
                builder.add(KeyboardButton(text="Покажи рецепты."))
                await message.answer(f"Как вам такие варианты: {','.join(translated_names)}",
                                     reply_markup=builder.as_markup(resize_keyboard=True))


        except aiohttp.ClientError as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await message.answer("Произошла ошибка при получении рецептов. Попробуйте позже.")
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            await message.answer("Произошла неожиданная ошибка. Попробуйте позже.")
