from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


class TopicSimilarityChecker:
    def __init__(self):
        # Загрузка модели
        self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

        # Предопределенные темы
        self.topic_candidates = [
            "программирование и технологии",
            "искусственный интеллект и машинное обучение",
            "наука и исследования",
            "образование и учеба",
            "бизнес и стартапы",
            # ... остальные темы
        ]

        self.topic_embeddings = self.model.encode(self.topic_candidates)

    def get_text_embedding(self, text: str) -> np.ndarray:
        """Создание векторного представления текста"""
        return self.model.encode([text])[0]

    def analyze_conversation_topic(self, conversation_history: list) -> tuple:
        """Определение основной темы из истории сообщений"""

        # Объединяем последние сообщения
        recent_text = " ".join([msg['text'] for msg in conversation_history[-10:]])

        # Создаем эмбеддинг для всей беседы
        conversation_embedding = self.get_text_embedding(recent_text)

        # Вычисляем схожесть со всеми темами
        similarities = cosine_similarity(
            [conversation_embedding],
            self.topic_embeddings
        )[0]

        # Находим наиболее подходящую тему
        best_topic_idx = np.argmax(similarities)
        best_topic = self.topic_candidates[best_topic_idx]
        confidence = similarities[best_topic_idx]

        return best_topic, confidence

    def check_message_relevance(self, message: str, current_topic: str) -> tuple:
        """Проверка соответствия сообщения текущей теме"""

        # Находим индекс текущей темы
        topic_idx = self.topic_candidates.index(current_topic)
        topic_embedding = self.topic_embeddings[topic_idx]

        # Создаем эмбеддинг для сообщения
        message_embedding = self.get_text_embedding(message)

        # Вычисляем схожесть
        similarity = cosine_similarity(
            [message_embedding],
            [topic_embedding]
        )[0][0]

        threshold = 0.6  # Порог релевантности

        if similarity >= threshold:
            return True, f"Сообщение соответствует теме (схожесть: {similarity:.2f})"
        else:
            return False, f"Сообщение не соответствует теме (схожесть: {similarity:.2f})"


mod = TopicSimilarityChecker()
print(mod.check_message_relevance("Я люблю питон", "программирование и технологии"))