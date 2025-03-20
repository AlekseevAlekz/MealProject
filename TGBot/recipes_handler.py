import aiohttp
import logging
from aiogram.fsm.state import StatesGroup, State

# Настройка логирования.
logging.basicConfig(level=logging.INFO)

URL = "https://www.themealdb.com/api/json/v1/1/"

async def fetch_json(url):
    """Получает JSON данные по указанному URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status() # Поднимаем исключение для ошибок HTTP
                return await response.json()

    except aiohttp.ClientError as e:
        logging.error(f"Ошибка при запросе к API: {e}")
        return None
    except Exception as e:
        logging.error(f"Неожиданная ошибка: {e}")
        return None


async def get_categories():
    """Получает список категорий блюд."""
    url = f"{URL}list.php?c=list"
    data = await fetch_json(url)
    if data and data.get('meals'):
        return data['meals']
    return None


async def get_meals_by_category(category):
    """Получает список блюд по категории."""
    url = f"{URL}filter.php?c={category}"
    data = await fetch_json(url)
    if data and data.get('meals'):
        return data['meals']
    return None

async def get_meal_details(meal_id):
    """Получает детали блюда по ID"""
    url = f"{URL}lookup.php?i={meal_id}"
    data = await fetch_json(url)
    if data and data.get('meals') and data['meals'][0]:
        return data['meals'][0]
    return None


async def get_random_meals_by_ids(meal_ids):
    """Получает детали блюд по списку ID."""
    import asyncio
    results = await asyncio.gather(*[get_meal_details(meal_id) for meal_id in meal_ids])
    return results


class CategorySearchStates(StatesGroup):
    choosing_category = State()
    showing_recipes = State()