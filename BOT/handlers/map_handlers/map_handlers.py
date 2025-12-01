from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from .utils_for_map_handlers import get_top_5_places, format_results, address_to_coordinates


class MapHandlers:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            'User-Agent': 'MeetingFinderBot/1.0 (https://t.me/ai_test_helper_nsu_bot; artem.rt2020@mail.ru)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
        }
        self.overpass_url = "http://overpass-api.de/api/interpreter"
        self.router = Router()
        self.register_handler()

    def register_handler(self):
        self.router.message.register(self.cmd_get_nearest_places, Command("get_nearest_places"))

    async def cmd_get_nearest_places(self, message: Message):
        address = message.text.replace("/find_places_near", "")
        coords = await address_to_coordinates(address)
        if not coords:
            await message.answer("Некорректный адрес")
            return
        lat, lng = coords
        places = await get_top_5_places(self.overpass_url,lat, lng)
        await format_results(places)
        return