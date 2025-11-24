import requests
from typing import Optional, Tuple, Dict
import time


class OSMGeocoder:
    def __init__(self):
        self.base_url = "https://nominatim.openstreetmap.org/search"
        self.delay = 1  # секунда между запросами

        # Важно: добавляем правильные заголовки
        self.headers = {
            'User-Agent': 'MeetingFinderBot/1.0 (https://t.me/ai_test_helper_nsu_bot; artem.rt2020@mail.ru)',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'
        }

    def address_to_coordinates(self, address: str, city: str = "") -> Optional[Tuple[float, float]]:
        """
        Преобразует адрес в координаты с правильными заголовками
        """
        # Формируем полный адрес
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
            time.sleep(self.delay)

            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,  # Добавляем заголовки!
                timeout=10
            )

            # print(f"Status Code: {response.status_code}")

            # if response.status_code == 403:
            #     print("❌ Доступ запрещен. Проверьте User-Agent")
            #     return None

            response.raise_for_status()

            data = response.json()

            if data:
                first_result = data[0]
                lat = float(first_result['lat'])
                lon = float(first_result['lon'])

                # print(f"✅ Найдены координаты для '{full_address}': {lat}, {lon}")
                return lat, lon
            else:
                # print(f"❌ Адрес не найден: {full_address}")
                return None

        except requests.exceptions.HTTPError as e:
            print(f"❌ HTTP ошибка: {e}")
            return None
        except Exception as e:
            print(f"❌ Общая ошибка: {e}")
            return None

    # def address_to_coordinates_simple(self, address: str) -> Optional[Tuple[float, float]]:
    #     """
    #     Упрощенный метод с меньшим количеством параметров
    #     """
    #     params = {
    #         'q': address,
    #         'format': 'json',
    #         'limit': 1
    #     }
    #
    #     try:
    #         time.sleep(self.delay)
    #
    #         response = requests.get(
    #             self.base_url,
    #             params=params,
    #             headers=self.headers,
    #             timeout=10
    #         )
    #
    #         print(f"Simple method - Status: {response.status_code}")
    #
    #         if response.status_code == 200:
    #             data = response.json()
    #             if data:
    #                 lat = float(data[0]['lat'])
    #                 lon = float(data[0]['lon'])
    #                 print(f"✅ Координаты: {lat}, {lon}")
    #                 return lat, lon
    #
    #         return None
    #
    #     except Exception as e:
    #         print(f"Ошибка упрощенного метода: {e}")
    #         return None


# Тестируем исправленный код
def test_fixed_geocoding():
    geocoder = OSMGeocoder()

    test_addresses = [
        "Барнаул, Шумакова, 58",
        "Невский проспект, 28, Санкт-Петербург",
        "Красная площадь, Москва",
        "улица Ленина, 1, Новосибирск"  # Без города
    ]

    print("🧭 Тестируем исправленный геокодинг:\n")

    for address in test_addresses:
        print(f"🔍 Поиск: '{address}'")

        # Пробуем оба метода
        coords = geocoder.address_to_coordinates(address)
        if not coords:
            print("   ⚠️ Пробуем упрощенный метод...")
            coords = geocoder.address_to_coordinates_simple(address)

        if coords:
            lat, lon = coords
            print(f"   ✅ Успех: {lat:.6f}, {lon:.6f}")
        else:
            print("   ❌ Все методы не сработали")

        print("-" * 50)


if __name__ == "__main__":
    test_fixed_geocoding()