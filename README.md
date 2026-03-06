## Как запустить проект

1. Поднять все сервисы (API + Postgres + Kafka + Redis + Prometheus + Grafana):

```
docker compose up -d
```

После этого:
- API на `http://localhost:8003`
- Kafka на `localhost:9092`
- Вэб-консоль для просмотра топиков и сообщений на `http://localhost:8080`
- Prometheus на `http://localhost:9090`
- Grafana на `http://localhost:3000` (`admin` / `admin`)

2. Запуск воркера (локально):

```
pip install -r requirements.txt
python -m workers.moderation_worker
```

Или как контейнер:

```
docker compose run --rm app python -m workers.moderation_worker
```

Что делает воркер:
- читает сообщения из топика `moderation`
- обрабатывает объявление (извлекает item_id, получает данные из БД, вызывает ML-сервис, получает предсказание)
- сохраняет результат в таблицу `moderation_results`
- если ошибка, отправляет сообщение в `moderation_dlq`

## Мониторинг (Prometheus + Grafana)

Проверить метрики:

```
curl http://127.0.0.1:8003/metrics
```

Доступы:
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000` (`admin` / `admin`)

Примеры PromQL для дашборда:

- RPS по endpoint:
```
sum by (endpoint) (rate(http_requests_total[1m]))
```

- Латентность p50/p95/p99:
```
histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

- Error rate (4xx/5xx):
```
sum(rate(http_requests_total{status=~"4..|5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100
```

- Кол-во предсказаний по результату:
```
sum by (result) (rate(predictions_total[5m]))
```

- Время инференса p50/p95:
```
histogram_quantile(0.50, sum(rate(prediction_duration_seconds_bucket[5m])) by (le))
histogram_quantile(0.95, sum(rate(prediction_duration_seconds_bucket[5m])) by (le))
```

- Время запросов к БД по типу:
```
sum by (query_type) (rate(db_query_duration_seconds_sum[5m])) / sum by (query_type) (rate(db_query_duration_seconds_count[5m]))
```
