# PassiveAgent Project Report

Дата отчета: 2026-06-08

## 1. Краткое описание проекта

PassiveAgent - это прототип системы пассивного мониторинга Telegram-сообщений для OSINT/anti-fraud задач. Проект собирает сообщения из Telegram, анализирует текст и ссылки, оценивает риск, сохраняет данные в PostgreSQL, строит граф связей в Neo4j и показывает результаты в web-dashboard.

Основная идея проекта: автоматически обнаруживать подозрительные сообщения, фишинг, спам, мошеннические паттерны, повторяющиеся рассылки и связи между пользователями, каналами и ссылками.

## 2. Текущая структура проекта

```text
PassiveAgent/
  backend/              Python backend и pipeline обработки
    api/                FastAPI endpoints
    collector/          Telegram listener на Telethon
    analysis/           NLP, ML classifier, risk scoring, analytics
    processing/         Очистка текста и извлечение ссылок
    storage/            SQLAlchemy модели и подключение к PostgreSQL
    graph/              Neo4j graph builder
    alerts/             Создание alert-записей
    spiderfoot_service/ Интеграция со SpiderFoot
    spiderfoot/         Локальная копия SpiderFoot
    ai/                 Локальная ML-модель
    main.py             Общий запуск backend + collector + frontend
    requirements.txt    Python зависимости

  frontend/             React/Vite dashboard
    src/components/     UI панели статистики, сообщений, alert-ов, графа и пользователей
    src/api/client.js   Клиент для FastAPI

  docker-compose.yml    PostgreSQL + pgvector и Neo4j
  install.bat           Установка зависимостей
  start.bat             Запуск проекта
```

## 3. Основные возможности, которые уже реализованы

1. Telegram collector:
   - подключение к Telegram через Telethon;
   - прием новых сообщений;
   - определение типа сообщения: text, link, image, video, voice, sticker, file, gif;
   - извлечение sender/user/chat данных.

2. Предобработка:
   - нормализация текста;
   - извлечение URL из сообщений.

3. Аналитический pipeline:
   - NLP-анализ;
   - pattern detection;
   - генерация embedding через sentence-transformers;
   - semantic matching через pgvector;
   - zero-shot классификация сообщений на scam/phishing/spam/normal;
   - behavioral scoring по частоте сообщений, числу чатов и доле ссылок;
   - risk scoring v2.

4. Хранилище:
   - PostgreSQL async SQLAlchemy;
   - pgvector для embedding;
   - таблицы users, user_names_history, user_stats, messages, alerts.

5. Graph intelligence:
   - запись связей User -> Channel, User -> Link, Link -> Channel в Neo4j;
   - API для просмотра графовых данных.

6. Alerts:
   - создание alert при HIGH risk;
   - сохранение alert в PostgreSQL;
   - endpoint для просмотра и закрытия alert.

7. API:
   - `/messages`;
   - `/alerts`;
   - `/alerts/{id}/resolve`;
   - `/similar`;
   - `/stats`;
   - `/users`;
   - `/user/{user_id}`;
   - `/user/{user_id}/messages`;
   - `/user/{user_id}/analytics`;
   - `/graph`.

8. Frontend dashboard:
   - общая статистика;
   - таблица сообщений;
   - управление alert-ами;
   - поиск пользователей;
   - профиль пользователя;
   - семантический поиск похожих сообщений;
   - просмотр графа.

9. Запуск:
   - добавлены `install.bat` и `start.bat`;
   - проект разложен на `backend` и `frontend`;
   - Docker Compose поднимает PostgreSQL + Neo4j.

## 4. В какой стадии находится проект

Проект находится в стадии MVP / working prototype.

Это уже не просто концепт: есть backend, frontend, база данных, ML pipeline, Telegram collector и dashboard. Однако проект еще не выглядит production-ready. Его можно запускать локально и использовать для демонстрации, тестирования гипотез и дальнейшей разработки, но перед реальным использованием нужна стабилизация.

Оценка стадии:

- Архитектура: MVP готова.
- Backend API: базово реализован.
- Collector: реализован, но требует проверки на реальных Telegram credentials.
- ML/NLP: реализовано, но требует исправления путей и качества модели.
- Frontend: реализован dashboard, но есть проблемы кодировки текста/иконок.
- База данных: схема создается автоматически, но миграций нет.
- DevOps: локальный запуск упрощен через bat-файлы, production deployment не готов.
- Тесты: отсутствуют или не обнаружены.

## 5. Обнаруженные проблемы и технический долг

1. Старый абсолютный путь к ML-модели:
   - файл: `backend/analysis/classifier.py`;
   - сейчас модель загружается из `D:/Projects/PassiveAgent/ai`;
   - после переноса правильный путь должен быть `backend/ai`.

2. `graph_score` считается, но не участвует в итоговом `risk_score`:
   - файл: `backend/collector/telegram_listener.py`;
   - `graph_score = await graph_builder.get_graph_score(...)` вычисляется;
   - затем не передается в `risk_engine_v2.calculate_score`.

3. Есть проблемы кодировки:
   - в некоторых Python/JS файлах видны поврежденные символы вроде `в”Ђ`, `рџ`;
   - это влияет на читаемость комментариев, логов и UI-иконок.

4. Нет миграций базы данных:
   - таблицы создаются через `Base.metadata.create_all`;
   - для серьезной эксплуатации лучше добавить Alembic.

5. Нет автоматических тестов:
   - нужны хотя бы smoke-тесты API и unit-тесты risk engine / preprocessor.

6. Telegram session и `.env` лежат внутри backend:
   - для локальной разработки нормально;
   - для репозитория и production лучше хранить secrets отдельно.

7. Старый корневой `venv` остался в проекте:
   - он не используется новым запуском;
   - новый путь окружения: `backend/.venv`;
   - старый `venv/` можно удалить вручную, если он больше не нужен.

8. Frontend использует фиксированный API URL:
   - `frontend/src/api/client.js` содержит `http://localhost:8000`;
   - лучше вынести в `.env` Vite-переменную.

## 6. Что нужно сделать дальше

Приоритет 1:

1. Исправить путь к локальной ML-модели в classifier.
2. Добавить `graph_score` в формулу риска или удалить неиспользуемый расчет.
3. Исправить кодировку файлов, где сломаны комментарии, логи и UI-иконки.
4. Проверить полный запуск через `install.bat` и `start.bat` на чистой машине.

Приоритет 2:

1. Добавить `.env.example`.
2. Добавить Alembic миграции.
3. Добавить smoke-тесты API.
4. Добавить обработку конфликтов duplicate `telegram_id`.
5. Вынести frontend API URL в переменные окружения.

Приоритет 3:

1. Улучшить качество ML-классификации на реальных данных.
2. Добавить роли/авторизацию для dashboard.
3. Добавить экспорт отчетов по alert-ам.
4. Добавить очередь задач для тяжелых ML/SpiderFoot операций.
5. Подготовить Dockerfile для backend и frontend.

## 7. Итоговая оценка

PassiveAgent сейчас представляет собой рабочий MVP интеллектуальной системы мониторинга Telegram. В проекте уже есть основные блоки: сбор данных, анализ, риск-скоринг, граф связей, alert-ы и web-интерфейс.

Текущая стадия: локальный демонстрационный прототип / MVP.

До production-стадии проекту не хватает тестов, миграций, исправления путей после реструктуризации, нормализации кодировки, настройки secrets и более надежного deployment-процесса.
