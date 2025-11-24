import requests
import json
from typing import List, Dict
from math import radians, sin, cos, sqrt, atan2


class OSMPlacesFinder:
    def __init__(self):
        self.overpass_url = "http://overpass-api.de/api/interpreter"

    def get_top_5_places(self, latitude: float, longitude: float, radius: int = 1000) -> List[Dict]:
        """
        Получает 5 лучших ближайших заведений через OpenStreetMap

        Args:
            latitude: Широта
            longitude: Долгота
            radius: Радиус поиска в метрах (по умолчанию 1 км)

        Returns:
            List[Dict]: Список из 5 заведений с информацией
        """
        # Overpass QL запрос для поиска заведений
        overpass_query = f"""
        [out:json][timeout:25];
        (
          node["amenity"~"cafe|restaurant|bar|pub|fast_food|biergarten"]
            (around:{radius},{latitude},{longitude});
          way["amenity"~"cafe|restaurant|bar|pub|fast_food|biergarten"]
            (around:{radius},{latitude},{longitude});
          relation["amenity"~"cafe|restaurant|bar|pub|fast_food|biergarten"]
            (around:{radius},{latitude},{longitude});
        );
        out center;
        """

        try:
            # Отправляем запрос к OSM API
            response = requests.post(self.overpass_url, data=overpass_query)
            response.raise_for_status()

            data = response.json()
            places = self._parse_osm_data(data, latitude, longitude)

            # Берем топ-5 ближайших
            return sorted(places, key=lambda x: x['distance'])[:5]

        except Exception as e:
            print(f"Ошибка при запросе к OSM: {e}")
            return []

    def _parse_osm_data(self, data: Dict, user_lat: float, user_lon: float) -> List[Dict]:
        """Парсит данные из OSM response"""
        places = []

        for element in data['elements']:
            tags = element.get('tags', {})

            # Пропускаем если нет названия
            if 'name' not in tags:
                continue

            # Получаем координаты места
            place_lat, place_lon = self._get_coordinates(element)
            if not place_lat or not place_lon:
                continue

            # Рассчитываем расстояние
            distance = self._calculate_distance(user_lat, user_lon, place_lat, place_lon)

            # Формируем информацию о месте
            place_info = {
                'name': tags['name'],
                'type': tags.get('amenity', 'place'),
                'address': self._format_address(tags),
                'cuisine': tags.get('cuisine', ''),
                'website': tags.get('website', ''),
                'phone': tags.get('phone', ''),
                'opening_hours': tags.get('opening_hours', ''),
                'latitude': place_lat,
                'longitude': place_lon,
                'distance': distance
            }

            places.append(place_info)

        return places

    def _get_coordinates(self, element: Dict) -> tuple:
        """Извлекает координаты из OSM элемента"""
        if element['type'] == 'node':
            return element.get('lat'), element.get('lon')
        else:  # way or relation
            center = element.get('center', {})
            return center.get('lat'), center.get('lon')

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Рассчитывает расстояние между точками в метрах"""
        R = 6371000  # Радиус Земли в метрах

        # Конвертируем градусы в радианы
        lat1_rad = radians(lat1)
        lon1_rad = radians(lon1)
        lat2_rad = radians(lat2)
        lon2_rad = radians(lon2)

        # Разница координат
        dlon = lon2_rad - lon1_rad
        dlat = lat2_rad - lat1_rad

        # Формула гаверсинуса
        a = sin(dlat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))

        return R * c

    def _format_address(self, tags: Dict) -> str:
        """Форматирует адрес из OSM тегов"""
        address_parts = []

        if tags.get('addr:street'):
            street = tags['addr:street']
            house = tags.get('addr:housenumber', '')
            address_parts.append(f"{street} {house}".strip())

        return ', '.join(address_parts) if address_parts else 'Адрес не указан'

    def format_results(self, places: List[Dict]) -> str:
        """Форматирует результаты для красивого вывода"""
        if not places:
            return "❌ В радиусе 1 км не найдено заведений"

        result = ["📍 **Топ-5 ближайших заведений:**\n"]

        for i, place in enumerate(places, 1):
            # Определяем эмодзи для типа заведения
            emoji = self._get_place_emoji(place['type'])

            # Форматируем расстояние
            distance_str = f"🚶 {int(place['distance'])}м"

            # Дополнительная информация
            details = []
            if place.get('cuisine'):
                details.append(f"🍴 {place['cuisine']}")
            if place.get('opening_hours'):
                # Обрезаем длинные строки с часами работы
                hours = place['opening_hours']
                if len(hours) > 30:
                    hours = hours[:30] + "..."
                details.append(f"🕒 {hours}")

            details_str = " • ".join(details)
            if details_str:
                details_str = f"\n   {details_str}"

            # Формируем текст для каждого места
            place_text = f"""
{i}. {emoji} **{place['name']}**
   📍 {place['address']}
   {distance_str}{details_str}
            """.strip()

            result.append(place_text)

        return "\n".join(result)

    def _get_place_emoji(self, place_type: str) -> str:
        """Возвращает эмодзи в зависимости от типа заведения"""
        emoji_map = {
            'cafe': '☕',
            'restaurant': '🍽️',
            'bar': '🍺',
            'pub': '🍻',
            'fast_food': '🍔',
            'biergarten': '🌳',
        }
        return emoji_map.get(place_type, '🏢')


# Пример использования
def main():
    # Создаем экземпляр поисковика
    finder = OSMPlacesFinder()
    #54.844886950148606, 83.09631758224445
    latitude = 54.844886950148606
    longitude = 83.09631758224445

    print(f"🔍 Ищем заведения рядом с координатами: {latitude}, {longitude}")
    print("⏳ Запрос к OpenStreetMap...")

    # Получаем топ-5 заведений
    places = finder.get_top_5_places(latitude, longitude)

    # Выводим результаты
    if places:
        print(f"\n✅ Найдено {len(places)} заведений:")
        print(finder.format_results(places))
    else:
        print("❌ Заведения не найдены")


# Функция для использования в боте
async def find_places_handler(message, bot, latitude: float, longitude: float):
    """Обработчик для использования в Telegram боте"""
    try:
        finder = OSMPlacesFinder()
        places = finder.get_top_5_places(latitude, longitude)
        result_text = finder.format_results(places)

        await bot.send_message(message.chat.id, result_text, parse_mode='Markdown')

    except Exception as e:
        error_text = f"❌ Ошибка при поиске заведений: {str(e)}"
        await bot.send_message(message.chat.id, error_text)


if __name__ == "__main__":
    main()