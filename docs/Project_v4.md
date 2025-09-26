# HH Tool v4 - Описание проекта

**Обновлено: 20.09.2025 - система полностью функциональна и работает в автоматическом режиме**


Автоматизация поиска работы на HH.ru через:
- 🤖 **Демон планировщика** с автоматическими загрузками каждый час
- 📊 **SQLite база данных** с версионированием и дедупликацией
- 🎯 **Умная загрузка** с обработкой дубликатов и мониторингом изменений
 - 🌐 **Веб-панель управления** на FastAPI (порт 8000)
- 🔌 **Host2/Host3 интеграция** (PostgreSQL и LLM анализ в mock режиме)

 ## Основные компоненты v4
 
 ### 1. Core (Ядро) - АКТУАЛИЗИРОВАНО
 
 - `scheduler_daemon.py` - ✅ Демон планировщика с 6 автоматическими задачами
 - `task_database.py` - ✅ Хранилище v4 (SQLite) с методами для задач, вакансий, работодателей и логов
- `task_dispatcher.py` - ✅ Диспетчер задач с интеграцией Host2/Host3
- `host2_client.py` - ✅ PostgreSQL клиент (mock режим)
- `host3_client.py` - ✅ LLM клиент для анализа вакансий (mock режим)
- `models.py` - ✅ Модели данных с поддержкой версионирования
### 2. Plugins (Плагины) - ИСПРАВЛЕНО
- `fetcher_v4.py` - ✅ Загрузчик вакансий с исправленным User-Agent и fallback логикой
- `base.py` - ✅ Базовые классы для плагинов

### 3. CLI (Интерфейс командной строки) - РАСШИРЕН
- `cli_v4.py` - ✅ 10+ команд: daemon, load-vacancies, status, tasks, export, stats, test, cleanup, system
- Удалён устаревший `run_v4.py` - заменён на `python cli_v4.py test readiness`

### 4. Configuration (Конфигурация)
- `config/config_v4.json` - Основные настройки системы
- `config/filters.json` - Фильтры поиска вакансий (из v3)

## Архитектура диспетчера задач

### Схема обработки задач
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Commands  │───▶│  Task Dispatcher │───▶│  Worker Pool    │
│                 │    │                  │    │  (3 threads)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │   SQLite Queue   │    │  Chunked Tasks  │
                       │  - tasks table   │    │  500 per chunk  │
                       │  - progress      │    │  timeout ctrl   │
                       └──────────────────┘    └─────────────────┘
```

### Пример обработки больших задач
```
50k вакансий → 100 chunks по 500 вакансий
│
├── Chunk 1: pages 0-5 (500 vacancies) → Worker 1
├── Chunk 2: pages 5-10 (500 vacancies) → Worker 2  
├── Chunk 3: pages 10-15 (500 vacancies) → Worker 3
│   ...
└── Chunk 100: pages 495-500 (500 vacancies) → Worker 1
```

## Упрощения по сравнению с v3

### Исключены из v4:
❌ **Async/await** - только синхронная архитектура
❌ **FastAPI/WebSockets** - простой HTTP сервер в CLI  
❌ **Сложные плагины** - пока только fetcher, планируется расширение
❌ **SSH операции** - только локальная работа
❌ **Docker** - нативное Python приложение
❌ **Redis** - SQLite для всего

### Сохранены из v3:
✅ **Модели данных** - полная совместимость
✅ **Фильтры поиска** - те же 4 активных фильтра
✅ **SQLite storage** - улучшенная схема для задач
✅ **Базовые классы плагинов** - для будущего расширения
✅ **Логирование** - структурированные логи

## Производительность

### Нагрузочные характеристики
- **Целевая нагрузка**: 50k вакансий/день
- **Chunk size**: 500 вакансий на задачу
- **Worker pool**: 3 потока по умолчанию
- **Rate limiting**: 1 сек между запросами к API
- **Timeout**: 3600 сек на задачу по умолчанию

### SQLite производительность
- **Вставки**: 1000+ INSERT/сек (достаточно для нашей нагрузки ~0.6/сек)
- **WAL mode**: включен для concurrent access
- **ACID транзакции**: гарантия консистентности
- **Backup**: простое копирование одного файла БД

## Конфигурация

### config_v4.json - основные настройки
```json
{
  "task_dispatcher": {
    "max_workers": 3,           // threading pool size
    "chunk_size": 500,          // vacancies per chunk  
    "default_timeout_sec": 3600 // task timeout
  },
  "vacancy_fetcher": {
    "rate_limit_delay": 1.0,    // delay between API calls
    "max_pages_per_filter": 200 // safety limit
  },
  "database": {
    "path": "data/hh_v4.sqlite3",
    "wal_mode": true            // concurrent access
  }
}
```

### filters.json - фильтры поиска (из v3)
```json
{
  "filters": [
    {
      "id": "python-remote",
      "name": "Python разработчик (удаленка)",  
      "params": {
        "text": "python",
        "area": 1,
        "schedule": "remote",
        "experience": "between1And3"
      },
      "active": true
    }
    // ... еще 3 фильтра
  ]
}
```

## База данных

### Схема SQLite v4
```sql
-- Очередь задач
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,           -- load_vacancies, process_pipeline, cleanup
    status TEXT NOT NULL,         -- pending, running, completed, failed
    params_json TEXT,             -- параметры задачи
    progress_json TEXT,           -- прогресс выполнения
    result_json TEXT,             -- результат выполнения
    error TEXT,                   -- текст ошибки
    created_at REAL,
    started_at REAL,
    finished_at REAL,
    schedule_at REAL,             -- отложенный запуск
    timeout_sec INTEGER,          -- таймаут задачи
    worker_id TEXT                -- какой worker обрабатывает
);

-- Вакансии (совместимо с v3)
CREATE TABLE vacancies (
    id INTEGER PRIMARY KEY,
    title TEXT,
    company TEXT,
    url TEXT,
    salary_from INTEGER,
    salary_to INTEGER,
    currency TEXT,
    area TEXT,
    published_at TEXT,
    description TEXT,
    key_skills TEXT,
    employment TEXT,
    schedule TEXT,
    experience TEXT,
    raw_json TEXT,
    processed_at REAL,
    filter_id TEXT,               -- какой фильтр нашел
    content_hash TEXT
);
```

## Использование

### Типичный workflow
```bash
# 1. Запуск демона планировщика (поднимет веб‑панель)
python -m core.scheduler_daemon

# 2. Тестовая загрузка (1 страница)
python cli_v4.py load_vacancies -f "python-remote" -p 1

# 3. Мониторинг
python cli_v4.py status
python cli_v4.py tasks

# 4. Боевая загрузка всех фильтров
python cli_v4.py load_vacancies

# 5. Очистка старых данных
python cli_v4.py cleanup
```

### Мониторинг и отладка
```bash
# Детали задачи
python cli_v4.py task-info <task_id>

# Последние задачи
python cli_v4.py tasks --limit 20

# Только failed задачи  
python cli_v4.py tasks --status failed

# Статистика фильтров
python cli_v4.py filters
```

## Логирование

### Структура логов
- `logs/app.log` - единый файл логов системы (ротация 100 МБ, 3 архива)
- Console - краткие сообщения о статусе

### Уровни логирования
```python
# В config_v4.json
"logging": {
  "level": "INFO",    // DEBUG, INFO, WARNING, ERROR
  "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
}
```

## Roadmap

### Ближайшие улучшения (в порядке приоритета)
1. **Тесты** - unit и integration тесты для компонентов
2. **Scripts** - утилиты для backup, migration, monitoring
3. **Analyzer plugin** - LLM анализ релевантности вакансий
4. **Classifier plugin** - автоматическая классификация
5. **Web dashboard** - улучшенный веб-интерфейс
6. **Docker** - контейнеризация для deployment

### Возможные масштабирования
1. **Redis queue** - если SQLite станет узким местом
2. **Horizontal scaling** - множественные workers через Redis
3. **FastAPI** - если нужен полноценный REST API
4. **Prometheus** - если нужны детальные метрики

## Миграция данных

### Совместимость с v3
- ✅ **Модели данных**: полная совместимость
- ✅ **Фильтры**: используются те же самые
- ✅ **SQLite схема вакансий**: совместима с v3
- ⚠️ **Плагины**: нужна адаптация под синхронную архитектуру

### Перенос данных из v3
```bash
# TODO: создать скрипт миграции
# python scripts/migrate_v3_to_v4.py
```

## Отличия от v3

| Аспект | v3 | v4 |
|--------|----|----|
| **Архитектура** | Async/await + FastAPI | Sync + threading |
| **Очередь задач** | Нет | SQLite-based |  
| **Chunked processing** | Нет | ✅ 500 per chunk |
| **Timeout control** | Нет | ✅ Настраиваемый |
| **SSH операции** | ✅ | ❌ Убраны |
| **Веб-интерфейс** | FastAPI + WebSocket | Простой HTTP |
| **Плагины** | Async pipeline | Sync (планируется) |
| **Deployment** | Docker | Native Python |
| **Dependencies** | Много | Минимум |

## Заключение

HH Tool v4 представляет эволюцию архитектуры v3 с фокусом на:
- **Автоматизацию** - полностью автономный демон планировщика
- **Надёжность** - система версионирования и дедупликации данных
- **Мониторинг** - веб-панель управления с real-time обновлениями
- **Расширяемость** - готовая интеграция с Host2 (PostgreSQL) и Host3 (LLM)

## 🎯 ТЕКУЩИЙ СТАТУС (20.09.2025 22:30)

**✅ СИСТЕМА В PRODUCTION:**
- Демон планировщика запущен и работает автономно
- Веб-панель доступна на http://localhost:8000  
- Автоматические загрузки вакансий каждый час
- Все тесты проходят успешно
- Проект очищен и документация обновлена

**Система полностью готова к производственному использованию!**
