import psycopg2
import openai
import json
from fastapi import FastAPI, Header, HTTPException, Body
from pydantic import BaseModel
from typing import List, Dict, Optional
from config import api_key, db_credentials

# Создание клиента openai
client = openai.OpenAI(api_key=api_key)

# Конфигурация подключения к PostgreSQL
DB_CONFIG = db_credentials

def execute_sql(query: str):
    """
    Выполняет SQL-запрос к базе данных PostgreSQL.
    """
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(query)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception as e:
        return f"Ошибка SQL: {e}"

def chat_gpt_with_sql(question: str, extra_context: Optional[List[Dict[str, str]]] = None) -> str:
    """
    Обрабатывает запрос:
    1. Отправляет запрос в GPT для генерации SQL-запроса.
    2. Выполняет SQL-запрос к базе.
    3. Передаёт результат в GPT для генерации финального ответа.
    Параметр extra_context позволяет передать дополнительный контекст в виде истории сообщений.
    """
    # Первый вызов: генерируем SQL-запрос
    sql_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": (
                    "Ты AI, который строит SQL-запросы для поиска информации в базе данных postgresql. "
                    "Ты стараешься разбить вопрос на ключевое слово, если это возможно и ищешь по нему. "
                    "Например, чтобы найти 'Как создать блюдо', ты ищешь по слову 'блюдо'."
                )
            },
            {
                "role": "user", 
                "content": (
                    "Вот структура базы данных:\n"
                    "Таблица: public.materials_material\n"
                    " - content (TEXT) - содержит инструкции в формате HTML\n\n"
                    f"Вопрос пользователя: {question}\n"
                    "Разбей вопрос на ключевое слово, если возможно и сформируй только SQL-запрос для поиска информации, без дополнительных сообщений и без "
                    "```sql"
                )
            }
        ]
    )
    
    sql_query = sql_response.choices[0].message.content.strip()
    print(f"🛠 GPT сгенерировал SQL-запрос:\n{sql_query}")
    
    # Выполняем SQL-запрос
    db_results = execute_sql(sql_query)
    print(f"Результаты SQL-запроса: {db_results}")
    
    # Собираем сообщения для финального вызова GPT с sql запросом сгенерированным ранее
    messages = [
        {
            "role": "system", 
            "content": (
                "Ты помощник по приложению, который отвечает на вопросы, используя данные из базы. "
                "Если по найденным данным невозможно найти, создать или предположить ответ, пиши, что не смог найти ответ."
            )
        }
    ]
    
    # Если передан контекст, добавляем его
    if extra_context:
        messages.extend(extra_context)
    
    # Добавление найденных данных из sql в основной запрос
    messages.append({
        "role": "assistant",
        "content": f"Вот найденные данные из базы: {db_results}"
    })
    messages.append({
        "role": "user",
        "content": f"Вопрос: {question}\nСформулируй понятный ответ пользователю."
    })
    
    final_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages
    )
    
    return final_response.choices[0].message.content

# Создание экземпляра FastAPI
app = FastAPI(
    title="Jowi ChatSQL API",
    description="API для обработки вопросов с генерацией SQL-запросов и последующим ответом с использованием GPT и базы данных Jowi, PostgreSQL.",
    version="1.0.0"
)

class ChatRequest(BaseModel):
    question: str
    context: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    answer: str

@app.post("/ask", response_model=ChatResponse, summary="Получение ответа на вопрос",
          description=(
              "Принимает вопрос и опциональный контекст (историю сообщений), "
              "проверяет наличие обязательного заголовка AuthRestaurantId и возвращает ответ, сгенерированный на основе базы данных."
          ))
def ask(
    payload: ChatRequest,
    authrestaurantid: str = Header(..., description="Обязательный идентификатор ресторана для доступа к API")
):
    # Простейшая проверка наличия значения заголовка (можно расширить валидацию)
    if not authrestaurantid:
        raise HTTPException(status_code=401, detail="Отсутствует AuthRestaurantId")
    
    try:
        answer = chat_gpt_with_sql(payload.question, payload.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    return ChatResponse(answer=answer)

# Для локального запуска (например, командой uvicorn main:app --reload)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
