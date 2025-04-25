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
                await state.set_state(RecipeStates.waiting_for_category)


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

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{THEMEALDB_API}/filter.php?c={category}") as response:
                response.raise_for_status()
                data = await response.json()

                if 'meals' not in data or not data['meals']:
                    await message.answer("Для этой категории не найдены рецепты!")
                    return

                meals = random.sample(data['meals'], min(count_recipes, len(data['meals'])))
                meal_names = [meal['strMeal'] for meal in meals]
                meal_ids = [meal['idMeal'] for meal in meals]

                # translated_names = [await asyncio.to_thread(translator.translate(name, dest='ru').text) for name in meal_names]
                # translated_texts = [item.text for item in translated_names]
                translated_texts = await asyncio.gather(
                    *[asyncio.to_thread(lambda text: translator.translate(text, dest='ru').text, name) for name in
                      meal_names])

                # await state.set_data({'meal_ids': meal_ids, 'meals': meals, 'translated_names': translated_texts})
                await state.update_data(meal_ids=meal_ids, meals=meals, translated_names=translated_texts)


                builder = ReplyKeyboardBuilder()
                builder.add(KeyboardButton(text="Покажи рецепты."))
                await message.answer(f"Как вам такие варианты: {','.join(translated_texts)}",
                                     reply_markup=builder.as_markup(resize_keyboard=True))
                await state.set_state(RecipeStates.waiting_for_recipes)

        except aiohttp.ClientError as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await message.answer("Произошла ошибка при получении рецептов. Попробуйте позже.")
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {e}")
            await message.answer("Произошла неожиданная ошибка. Попробуйте позже.")


@router.message(RecipeStates.waiting_for_recipes)
async def recipe_choosing_handler(message: Message, state: FSMContext):
    # selected_recipe = message.text
    # logging.info(f"selected_recipe: {selected_recipe}")
    if message.text != "Покажи рецепты.":
        await message.answer("Сначала выберите один из предложенных рецептов.")
        return

    data = await state.get_data()
    meal_ids = data.get('meal_ids')
    meals = data.get('meals', [])
    translated_names = data.get('translated_names', [])

    if not meal_ids:
        await message.answer("Не удалось получить список рецептов")
        return

    # selected_id = None
    # for meal in meals:
    #     translated_name = translator.translate(meal['strMeal'], dest='ru').text
    #     if translated_name == selected_recipe:
    #         selected_id = meal['idMeal']
    #         break

    # if selected_id is None:
    #     await message.answer("Не удалось найти выбранный рецепт.")
    #     return

    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for idx, translated_name in enumerate(translated_names):
        keyboard.insert(KeyboardButton(text=f"{idx+1}, {translated_name}"))

    if message.text == "Покажи рецепты.":
        await message.answer("Выберите рецепт для просмотра подробностей.", reply_markup=keyboard)
        await state.set_state(RecipeStates.showing_recipe_details)

    # async with aiohttp.ClientSession() as session:
    #     try:
    #         async with session.get(f"{THEMEALDB_API}/lookup.php?i={selected_id}") as response:
    #             data = await response.json()
    #
    #             if meals not in data or not data['meals']:
    #                 await message.answer("Не удалось найти рецепт!")
    #                 return
    #
    #             meal = data['meals'][0]
    #
    #             translated_name = translator.translate(meal['strMeal'], dest='ru').text
    #             translated_instructions = translator.translate(meal['strInstructions'], dest='ru').text
    #
    #             ingredients = []
    #             for i in range(1, 21):
    #                 ingredient = meal.get(f"strIngredient{i}")
    #                 measure = meal.get(f"strMeasure{i}")
    #                 if ingredient and ingredient.strip():
    #                     translated_ingredient = translator.translate(ingredient, dest='ru').text
    #                     translated_measure = translator.translate(measure, dest='ru').text
    #                     ingredients.append(f"- {await translated_measure} {await translated_ingredient}")
    #             ingredients_text = "\n".join(ingredients)
    #
    #             #instructions_ru = await translate_text(meal['strInstructions'])
    #
    #             message_text = (
    #                 f"<b>{await translated_name}</b>\n"
    #                 f"<b>Рецепт:</b>\n{translated_instructions}\n"
    #                 f"<b>Ингредиенты:</b>\n{ingredients_text}"
    #             )
    #             await message.answer(message_text)
    #
    #     except Exception as e:
    #         logging.error(f"Error while fetching details for recipe {selected_recipe}: {e}")
    #         await message.answer("Произошла ошибка")



@router.message(RecipeStates.showing_recipe_details)
async def recipe_detail_handler(message: Message, state: FSMContext):
    data = await state.get_data()
    meal_ids = data.get('meal_ids')
    meals = data.get('meals', [])

    if not meal_ids or not meals:
        await message.answer("Не удалось получить данные о рецептах.")
        return

    # Извлекаем номер рецепта
    try:
        selected_index = int(message.text.split('.')[0]) - 1  # Убираем текст после точки и переводим в индекс
        if selected_index < 0 or selected_index >= len(meal_ids):
            raise IndexError
    except (ValueError, IndexError):
        await message.answer("Пожалуйста, выберите корректный рецепт.")
        return

    meal_id = meal_ids[selected_index]

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{THEMEALDB_API}/lookup.php?i={meal_id}") as response:
                response.raise_for_status()
                data = await response.json()

                if 'meals' not in data or not data['meals']:
                    await message.answer("Не удалось получить информацию о выбранном рецепте.")
                    return

                meal_detail = data['meals'][0]
                details = (
                    f"Название: {meal_detail['strMeal']}\n"
                    f"Категория: {meal_detail['strCategory']}\n"
                    f"Ингредиенты:\n"
                )

                ingredients = []
                for i in range(1, 21):  # Поиск до 20 ингредиентов
                    ingredient = meal_detail.get(f'strIngredient{i}')
                    measure = meal_detail.get(f'strMeasure{i}')
                    if ingredient:
                        ingredients.append(f"{ingredient} - {measure}")

                details += "\n".join(ingredients) if ingredients else "Нет доступных ингредиентов."

                await message.answer(details)

        except aiohttp.ClientError as e:
            logging.error(f"Ошибка при запросе к API для получения детали рецепта: {e}")
            await message.answer("Произошла ошибка при получении подробной информации о рецепте. Попробуйте позже.")
        except Exception as e:
            logging.error(f"Неожиданная ошибка при получении детали рецепта: {e}")
            await message.answer("Произошла неожиданная ошибка. Попробуйте позже.")


