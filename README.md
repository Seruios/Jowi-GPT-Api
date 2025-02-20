# Jowi-GPT-Api
Jowi GPT api for chat

# Установите зависимости из requirements.txt
`pip install -r requirements.txt`

# Запустите приложение
Используйте Uvicorn для запуска сервера. Например, чтобы слушать на всех IP-адресах на порту 8000, выполните:

`uvicorn main:app --host 0.0.0.0 --port 8000`

# Api-эндпоинт
`http://<IP-адрес>:8000/ask`

# Документация Swagger
`http://<IP-адрес>:8000/docs`
