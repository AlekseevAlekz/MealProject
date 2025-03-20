import asyncio
import logging
import sys
import random
import aiohttp

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.markdown import hbold

from googletrans import Translator

from TGBot.token_data import token

from recipes_handler import CategorySearchStates
from recipes_handler import (
get_categories,
get_meals_by_category,
get_meal_details,
get_random_meals_by_ids,
)


# Настройка логирования.
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера.
dp = Dispatcher()
storage = MemoryStorage()
bot = Bot(token=token)

# Инициализация переводчика.
translator = Translator()

async def translate_text(text, dest='ru'):
    """Переводит текст на указанный язык."""
    try:
        translation = translator.translate(text, dest=dest)
        return translation
    except Exception as e:
        logging.error(f"Ошибка перевода: {e}")
        return text


@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    """Обработчик команды /start."""
    await message.answer(
        "Привет! Я бот-рецептов.  \n"
        "Вы можете использовать следующие команды: \n"
        "/category_search_random <количество_рецептов>\n"
        "/help - помощь",
    )


@dp.message(Command('help'))
async def command_help_handler(message: types.Message):
    """Обработчик команды /help."""
    await message.answer(
        "Я предоставляю информацию о рецептах. \n "
        "Доступные команды: \n"
        "/category_search_random <количество_рецептов> - поиск случайных рецептов"
    )


@dp.message(Command('category_search_random'))
async def category_search_random_command_handler(message:types.Message, state: FSMContext):
    """Обработчик команды /category_search_random."""
    try:
        args = message.text.split()
        if len(args) != 2 or not args[1].isdigit():
            await message.answer("Пожалуйста укажите корректное количество рецептов"
                                 "(например: /category_search_random 3)")
            return

        count = int(args[1])
        if count <=0:
            await message.answer("Количество рецептов должно быть больше чем 0")
            return

        await state.update_data(recipe_count=count)

        categories = await get_categories()
        if categories:
            keyboard = InlineKeyboardMarkup(row_width=2)
            for category in categories:
                keyboard.add(InlineKeyboardButton(text=category['strCategory'],
                                                  callback_data=f"category: {category['strCategory']}"))
            await message.answer("Выберите категорию: ", reply_markup=keyboard)
            await state.set_state(CategorySearchStates.choosing_category)
        else:
            await message.answer("Не удалось получить список категорий.")

    except:
        await  message.answer("Пожалуйста укажите корректное количество рецептов (например: /category_search_random 3)")

                             
@dp.callback_query(CategorySearchStates.choosing_category, F.data.startwith("category:"))
async def category_choosing_handler (callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора категории."""
    category_name = callback_query.data.split(":")[1]
    await callback_query.answer()

    meals = await get_meals_by_category(category_name)
    if meals:
        count = (await state.get_data()).get('recipe_count', 1)
        meal_ids = [meal['idMeal'] for meal in meals]
        random_meal_ids = random.choices(meal_ids, k=min(count, len(meal_ids)))

        await state.update_data(meal_ids=random_meal_ids)

        meal_names_ru = []
        for meal_id in random_meal_ids:
            meal_details = await get_meal_details(meal_id)
            if meal_details:
                meal_names_ru.append(await translate_text(meal_details['strMeal']))

        await callback_query.message.edit_text(f"Выбрано {count} рецептов из категории {category_name}: \n"
                                               f"{','.join(meal_names_ru)}")
        await state.set_state(CategorySearchStates.showing_recipes)
    else:
        await callback_query.message.edit_text(f"Не удалось найти блюда в категории {category_name}.")
        await state.clear()


@dp.message(CategorySearchStates.showing_recipes)
async def show_recipes_handler(message: types.Message, state: FSMContext):
    """Обработчик отображения рецептов."""
    data = await state.get_data()
    meal_ids = data.get('meal_ids')

    if not meal_ids:
        await message.answer("Не удалось найти рецепты.")
        await state.clear()
        return

    meals = await get_random_meals_by_ids(meal_ids)

    if meals:
        for meal in meals:
            if meal:
                ingredients = []
                for i in range(1, 21):
                    ingredient = meal.get(f"strIngredient{i}")
                    measure = meal.get(f"strMeasure{i}")
                    if ingredient and ingredient.strip():
                        ingredients.append(f"- {measure} {await translate_text(ingredient)}")
                ingredients_text = "\n".join(ingredients)

                message_text = (
                    f"<b>{await translate_text(meal['strMeal'])}</b>\n\n"
                    f"<b>Рецепт:</b>\n{await translate_text(meal['strInstructions'])}\n\n"
                    f"<b>Ингридиенты:</b>\n{ingredients_text}"
                )
                await message.answer(message_text, parse_mode='HTML')
            else:
                await message.answer("Не удалось получить детали рецептов.")
            await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
#recipe = translator.translate('Some recipe', dest='ru')


