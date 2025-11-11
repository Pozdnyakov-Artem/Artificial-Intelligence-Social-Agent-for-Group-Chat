from transformers import pipeline

# Загрузка модели (первый раз может занять время)
def load_chat_model():
    return pipeline("text-generation", model="mistralai/Mistral-7B-Instruct-v0.1")

def chat_with_huggingface(prompt, chat_pipeline):
    try:
        response = chat_pipeline(
            prompt,
            max_length=500,
            temperature=0.7,
            do_sample=True
        )
        return response[0]['generated_text']
    except Exception as e:
        return f"Ошибка: {e}"

# Использование
model = load_chat_model()  # Раскомментируйте для загрузки модели
prompt = "Напиши рецепт пасты карбонара"
result = chat_with_huggingface(prompt, model)
print(result)