from math import radians, sin, cos, sqrt, atan2
from typing import List, Dict, Optional, Tuple

import aiohttp
import requests


async def address_to_coordinates(base_url,headers,address: str, city: str = "") -> Optional[Tuple[float, float]]:
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
                    base_url,
                    params=params,
                    headers=headers,
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


async def format_address(tags: Dict) -> str:
    """Форматирует адрес из OSM тегов"""
    address_parts = []

    if tags.get('addr:street'):
        street = tags['addr:street']
        house = tags.get('addr:housenumber', '')
        address_parts.append(f"{street} {house}".strip())

    return ', '.join(address_parts) if address_parts else 'Адрес не указан'

async def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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

async def get_coordinates(element: Dict) -> tuple:
    """Извлекает координаты из OSM элемента"""
    if element['type'] == 'node':
        return element.get('lat'), element.get('lon')
    else:  # way or relation
        center = element.get('center', {})
        return center.get('lat'), center.get('lon')

async def parse_osm_data(data: Dict, user_lat: float, user_lon: float) -> List[Dict]:
    """Парсит данные из OSM response"""
    places = []

    for element in data['elements']:
        tags = element.get('tags', {})

        # Пропускаем если нет названия
        if 'name' not in tags:
            continue

        # Получаем координаты места
        place_lat, place_lon = await get_coordinates(element)
        if not place_lat or not place_lon:
            continue

        # Рассчитываем расстояние
        distance = await calculate_distance(user_lat, user_lon, place_lat, place_lon)

        # Формируем информацию о месте
        place_info = {
            'name': tags['name'],
            'type': tags.get('amenity', 'place'),
            'address': await format_address(tags),
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

async def get_top_5_places(overpass_url,latitude: float, longitude: float, radius: int = 1000) -> List[Dict]:
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
        response = requests.post(overpass_url, data=overpass_query)
        response.raise_for_status()

        data = response.json()
        places = await parse_osm_data(data, latitude, longitude)

        # Берем топ-5 ближайших
        return sorted(places, key=lambda x: x['distance'])[:5]

    except Exception as e:
        print(f"Ошибка при запросе к OSM: {e}")
        return []

async def get_place_emoji(place_type: str) -> str:
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

async def format_results(places: List[Dict]) -> str:
    """Форматирует результаты для красивого вывода"""
    if not places:
        return "❌ В радиусе 1 км не найдено заведений"

    result = ["📍 **Топ-5 ближайших заведений:**\n"]

    for i, place in enumerate(places, 1):
        # Определяем эмодзи для типа заведения
        emoji = await get_place_emoji(place['type'])

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