import aiohttp
import asyncio
from typing import Optional, Tuple, Dict


class OSMGeocoder:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            'User-Agent': 'MeetingFinderBot/1.0 (https://t.me/ai_test_helper_nsu_bot; artem.rt2020@mail.ru)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
        }

    async def address_to_coordinates(self, address: str, city: str = "") -> Optional[Tuple[float, float]]:
        """АСИНХРОННАЯ версия с aiohttp"""
        full_address = address
        if city and city not in address:
            full_address += f", {city}"

        params = {
            'q': full_address,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'ru',
            'accept-language': 'ru'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        self.base_url,
                        params=params,
                        headers=self.headers,
                        timeout=aiohttp.ClientTimeout(total=10)
                ) as response:

                    if response.status == 200:
                        data = await response.json()
                        if data:
                            first_result = data[0]
                            lat = float(first_result['lat'])
                            lon = float(first_result['lon'])
                            return lat, lon
                    else:
                        print(f"❌ HTTP ошибка: {response.status}")
                        return None

        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return None


# async def test_async_geocoding():
#     geocoder = OSMGeocoder()
#     test_addresses = [
#         "Барнаул шумакова 58",
#         "Невский проспект, 28, Санкт-Петербург",
#         "Красная площадь, Москва",
#         "улица Ленина, 1, Новосибирск"
#     ]
#
#     print("🧭 Тестируем асинхронный геокодинг:\n")
#
#     for address in test_addresses:
#         print(f"🔍 Поиск: '{address}'")
#         coords = await geocoder.address_to_coordinates(address)  # ✅ С await!
#
#         if coords:
#             lat, lon = coords
#             print(f"   ✅ Успех: {lat:.6f}, {lon:.6f}")
#         else:
#             print("   ❌ Не найдено")
#         print("-" * 50)
#
#
# # Для запуска асинхронного теста
# if __name__ == "__main__":
#     asyncio.run(test_async_geocoding())