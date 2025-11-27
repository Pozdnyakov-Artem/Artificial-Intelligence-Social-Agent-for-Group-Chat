import asyncio
import time
import os
from pathlib import Path
from sentence_transformers import SentenceTransformer
import requests
from tqdm import tqdm
import threading


class AdvancedModelLoader:
    def __init__(self):
        self.model = None
        self.loaded = False
        self.cache_dir = Path.home() / '.cache' / 'torch' / 'sentence_transformers'
        self.model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self.download_progress = 0
        self.download_speed = 0
        self.estimated_time = 0

    def background_download(self):
        """Фоновая загрузка модели"""
        try:
            self.model = SentenceTransformer(self.model_name, device='cpu')
            self.loaded = True
        except Exception as e:
            print(f"\n❌ Ошибка загрузки: {e}")

    async def load_with_live_progress(self):
        """Загрузка с живым прогрессом"""
        if self.loaded:
            return self.model

        print("🚀 Запуск загрузки нейросети...")
        print("📦 Модель: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        print("💾 Размер: ~420 MB")
        print()

        # Запускаем загрузку в отдельном потоке
        download_thread = threading.Thread(target=self.background_download)
        download_thread.daemon = True
        download_thread.start()

        # Мониторим прогресс
        await self.show_live_progress()

        # Ждем завершения
        download_thread.join()

        if self.loaded:
            print("\n🎉 Модель успешно загружена!")
            return self.model
        else:
            raise Exception("Не удалось загрузить модель")

    async def show_live_progress(self):
        """Показывает живой прогресс"""
        start_time = time.time()
        expected_size = 440000000  # ~420 MB

        # Анимация загрузки
        animations = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        anim_index = 0

        while not self.loaded:
            current_size = self.get_current_download_size()
            progress = min((current_size / expected_size) * 100, 99.9)  # Макс 99.9% пока не загружено

            # Расчет скорости и времени
            elapsed = time.time() - start_time
            speed = current_size / elapsed if elapsed > 0 else 0

            if speed > 0 and progress < 100:
                remaining = (expected_size - current_size) / speed
            else:
                remaining = 0

            # Отображение прогресса
            self.display_animated_progress(progress, current_size, expected_size,
                                           speed, remaining, animations[anim_index % len(animations)])

            anim_index += 1
            await asyncio.sleep(0.3)

    def get_current_download_size(self):
        """Получает текущий размер скачанных файлов"""
        model_path = self.cache_dir / 'sentence-transformers_paraphrase-multilingual-MiniLM-L12-v2'
        if model_path.exists():
            return sum(f.stat().st_size for f in model_path.rglob('*') if f.is_file())
        return 0

    def display_animated_progress(self, progress, current, total, speed, remaining, animation):
        """Отображает анимированный прогресс"""
        bar_length = 25
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)

        # Форматирование
        def format_size(size):
            for unit in ['B', 'KB', 'MB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} GB"

        def format_time(seconds):
            if seconds < 60:
                return f"{seconds:.0f}с"
            else:
                return f"{seconds / 60:.1f}м"

        progress_text = (
            f"\r{animation} Загрузка: [{bar}] {progress:.1f}% "
            f"| {format_size(current)}/{format_size(total)} "
            f"| {format_size(speed)}/с "
            f"| ⏳ {format_time(remaining)}"
        )

        print(progress_text, end='', flush=True)


# Использование
async def main():
    loader = AdvancedModelLoader()

    try:
        model = await loader.load_with_live_progress()
        print("🤖 Модель готова к использованию!")

        # Тестируем
        embeddings = model.encode(["Тестовый текст"])
        print(f"📐 Размерность эмбеддингов: {embeddings.shape}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    asyncio.run(main())