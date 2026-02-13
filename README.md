## Как запустить проект


1. Зависимости:

```
pip install -r requirements.txt
```

2. Докер сервисы:

```
docker compose up -d
```

После этого:
- Kafka на `localhost:9092`
- Вэб-консоль для просмотра топиков и сообщений на `http://localhost:8080`

3. FastAPI:

```
uvicorn main:app --reload --port 8003
```

4. Запуск воркерв

```
python -m workers.moderation_worker
```

Что делает воркер:
- читает сообщения из топика `moderation`
- обрабатывает объявление (извлекает item_id, получает данные из БД, вызывает ML-сервис, получает предсказание)
- сохраняет результат в таблицу `moderation_results`
- если ошибка, отправляет сообщение в `moderation_dlq`
