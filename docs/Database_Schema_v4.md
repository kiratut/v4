# Database Schema v4 Documentation

**Упрощенная схема для синхронного диспетчера задач v4**

## Основная таблица: `tasks` (новая в v4)

Центральная таблица для очереди задач диспетчера.

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| **id** | TEXT PK | UUID задачи | `"abc12345-6789-..."` |
| **type** | TEXT NOT NULL | Тип задачи | `"load_vacancies"`, `"cleanup"` |
| **status** | TEXT NOT NULL | Статус выполнения | `"pending"`, `"running"`, `"completed"`, `"failed"` |
| **params_json** | TEXT | Параметры задачи (JSON) | `{"filter": {...}, "max_pages": 20}` |
| **progress_json** | TEXT | Прогресс выполнения (JSON) | `{"chunk_progress": "3/4", "loaded": 1500}` |
| **result_json** | TEXT | Результат выполнения (JSON) | `{"loaded_count": 2000, "chunks": 4}` |
| **error** | TEXT | Текст ошибки | `"Rate limit exceeded"` |
| **created_at** | REAL | Unix timestamp создания | `1694712000.123` |
| **started_at** | REAL | Unix timestamp начала | `1694712010.456` |
| **finished_at** | REAL | Unix timestamp завершения | `1694712600.789` |
| **schedule_at** | REAL | Отложенный запуск | `1694720000.000` |
| **timeout_sec** | INTEGER | Таймаут задачи | `3600` |
| **worker_id** | TEXT | ID worker'а | `"worker_1"` |

### Индексы для tasks
```sql
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(type);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_schedule_at ON tasks(schedule_at);
```

## Основная таблица: `vacancies` (совместимая с v3)

Таблица вакансий сохраняет совместимость с v3 схемой.

| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| **id** | INTEGER PK | Внутренний ID (автоинкремент) | `1`, `2`, `3` |
| **hh_id** | TEXT | ID вакансии на HH.ru | `"98765432"` |
| **title** | TEXT | Название вакансии | `"Python Developer"` |
| **company** | TEXT | Компания | `"Яндекс"` |
| **employer_id** | TEXT | ID компании | `"1740"` |
| **salary_from** | INTEGER | Зарплата от (руб) | `150000` |
| **salary_to** | INTEGER | Зарплата до (руб) | `250000` |
| **currency** | TEXT | Валюта | `"RUR"`, `"USD"` |
| **experience** | TEXT | Опыт | `"between1And3"` |
| **schedule** | TEXT | График работы | `"remote"`, `"fullDay"` |
| **employment** | TEXT | Занятость | `"full"`, `"part"` |
| **description** | TEXT | Описание (без HTML) | `"Разработка веб-приложений..."` |
| **key_skills** | TEXT | Навыки (JSON string) | `["Python", "Django", "REST API"]` |
| **area** | TEXT | Город | `"Москва"` |
| **published_at** | TEXT | Дата публикации ISO | `"2025-01-09T10:30:00+03:00"` |
| **url** | TEXT | Ссылка на вакансию | `"https://hh.ru/vacancy/98765432"` |

### Поля специфичные для v4
| Поле | Тип | Описание | Пример |
|------|-----|----------|--------|
| **processed_at** | REAL | Unix timestamp обработки | `1694712000.123` |
| **filter_id** | TEXT | ID фильтра который нашел | `"python-remote"` |
| **content_hash** | TEXT | Хеш содержимого для дедупликации | `"sha256:abc123..."` |
| **raw_json** | TEXT | Полный JSON от HH API | `{"id": "98765432", ...}` |

### Индексы для vacancies
```sql
CREATE INDEX idx_vacancies_hh_id ON vacancies(hh_id);
CREATE INDEX idx_vacancies_filter_id ON vacancies(filter_id);
CREATE INDEX idx_vacancies_published_at ON vacancies(published_at);
CREATE INDEX idx_vacancies_processed_at ON vacancies(processed_at);
CREATE INDEX idx_vacancies_content_hash ON vacancies(content_hash);
```

## Упрощения по сравнению с v3

### Исключены из v4:
❌ **process_status** таблица - заменена на поле status в tasks
❌ **plugin_dependencies** - нет сложных зависимостей между плагинами
❌ **session_results** - нет in-memory кеширования

### Добавлены в v4:
✅ **tasks** таблица - центральная очередь задач
✅ **filter_id** в vacancies - какой фильтр нашел вакансию
✅ **content_hash** в vacancies - дедупликация по содержимому
✅ **processed_at** в vacancies - время обработки в v4
✅ **plugin_results** - хранение результатов анализов/плагинов (включая host3_analysis)

## DDL Создание схемы

```sql
-- Таблица задач диспетчера
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    params_json TEXT,
    progress_json TEXT,
    result_json TEXT,
    error TEXT,
    created_at REAL NOT NULL,
    started_at REAL,
    finished_at REAL,
    schedule_at REAL,
    timeout_sec INTEGER DEFAULT 3600,
    worker_id TEXT,
    
    CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    CHECK (type IN ('load_vacancies', 'process_pipeline', 'cleanup', 'test'))
);

-- Таблица вакансий (совместимая с v3)
CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hh_id TEXT,
    title TEXT,
    company TEXT,
    employer_id TEXT,
    salary_from INTEGER,
    salary_to INTEGER,
    currency TEXT,
    experience TEXT,
    schedule TEXT,
    employment TEXT,
    description TEXT,
    key_skills TEXT,
    area TEXT,
    published_at TEXT,
    url TEXT,
    processed_at REAL,
    filter_id TEXT,
    content_hash TEXT,
    raw_json TEXT
);

-- Индексы для производительности
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_tasks_schedule_at ON tasks(schedule_at) WHERE schedule_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_vacancies_hh_id ON vacancies(hh_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_filter_id ON vacancies(filter_id);
CREATE INDEX IF NOT EXISTS idx_vacancies_published_at ON vacancies(published_at);
CREATE INDEX IF NOT EXISTS idx_vacancies_processed_at ON vacancies(processed_at);
CREATE INDEX IF NOT EXISTS idx_vacancies_content_hash ON vacancies(content_hash) WHERE content_hash IS NOT NULL;

-- WAL режим для concurrent access
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=MEMORY;
```

## Примеры запросов v4

### Работа с задачами

```sql
-- Создание новой задачи загрузки
INSERT INTO tasks (id, type, status, params_json, created_at, timeout_sec)
VALUES (
  'abc12345-6789-...',
  'load_vacancies',
  'pending',
  '{"filter": {"id": "python-remote"}, "max_pages": 20, "chunk_size": 500}',
  1694712000.123,
  3600
);

-- Получение задач в очереди
SELECT * FROM tasks 
WHERE status = 'pending' 
ORDER BY created_at ASC 
LIMIT 10;

-- Обновление прогресса задачи
UPDATE tasks 
SET 
  status = 'running',
  started_at = 1694712010.456,
  progress_json = '{"chunk_progress": "2/4", "loaded_vacancies": 1000}',
  worker_id = 'worker_1'
WHERE id = 'abc12345-6789-...';

-- Завершение задачи
UPDATE tasks
SET
  status = 'completed',
  finished_at = 1694712600.789,
  result_json = '{"loaded_count": 2000, "chunks_processed": 4}'
WHERE id = 'abc12345-6789-...';

-- Статистика задач за последние 24 часа
SELECT 
  status,
  COUNT(*) as count,
  AVG(finished_at - started_at) as avg_duration_sec
FROM tasks 
WHERE created_at > (strftime('%s', 'now') - 86400)
GROUP BY status;
```

### Работа с вакансиями

```sql
-- Вставка новой вакансии
INSERT INTO vacancies (
  hh_id, title, company, salary_from, salary_to, currency,
  experience, schedule, employment, description, key_skills,
  area, published_at, url, processed_at, filter_id, content_hash, raw_json
) VALUES (
  '98765432',
  'Senior Python Developer',
  'Яндекс',
  200000, 300000, 'RUR',
  'between3And6', 'remote', 'full',
  'Разработка высоконагруженных веб-приложений...',
  '["Python", "Django", "PostgreSQL"]',
  'Москва',
  '2025-09-14T10:30:00+03:00',
  'https://hh.ru/vacancy/98765432',
  1694712000.123,
  'python-remote',
  'sha256:abc123...',
  '{"id": "98765432", "name": "Senior Python Developer", ...}'
);

-- Поиск дубликатов по content_hash
SELECT hh_id, title, company, COUNT(*) as duplicates
FROM vacancies 
WHERE content_hash IS NOT NULL
GROUP BY content_hash 
HAVING COUNT(*) > 1;

-- Статистика по фильтрам за последние 7 дней
SELECT 
  filter_id,
  COUNT(*) as vacancies_found,
  COUNT(DISTINCT company) as companies,
  AVG(salary_from) as avg_salary_from
FROM vacancies 
WHERE processed_at > (strftime('%s', 'now') - 604800)
  AND filter_id IS NOT NULL
GROUP BY filter_id 
ORDER BY vacancies_found DESC;

-- Топ компаний с удаленными Python вакансиями
SELECT 
  company,
  COUNT(*) as remote_python_vacancies,
  AVG(salary_from) as avg_salary
FROM vacancies 
WHERE filter_id LIKE '%python%'
  AND schedule = 'remote'
  AND salary_from IS NOT NULL
GROUP BY company 
ORDER BY remote_python_vacancies DESC 
LIMIT 10;
```

## Миграция данных

### Из v3 в v4

```sql
-- Копирование вакансий из v3 (если нужно)
INSERT INTO v4_vacancies (
  hh_id, title, company, salary_from, salary_to, currency,
  experience, schedule, employment, description, key_skills,
  area, published_at, url, processed_at, filter_id
)
SELECT 
  hh_id, title, employer_name, salary_from, salary_to, currency,
  experience, schedule, employment, description, key_skills,
  area_name, published_at, url, 
  strftime('%s', 'now'), 'migrated_from_v3'
FROM v3_vacancies 
WHERE hh_id NOT IN (SELECT hh_id FROM v4_vacancies WHERE hh_id IS NOT NULL);
```

## Производительность

### Ожидаемые объемы данных
- **tasks**: ~1000 задач/месяц, ~50MB/год
- **vacancies**: ~50k записей/день, ~100MB/день, ~35GB/год

### Оптимизация
- WAL режим для concurrent access (читаем во время записи)
- Индексы на часто используемые поля
- Регулярная очистка старых задач (7-30 дней)
- VACUUM раз в месяц для дефрагментации

### Мониторинг размера БД

```sql
-- Размер таблиц в KB
SELECT 
  name,
  (pgsize / 1024) as size_kb,
  (pgsize / 1024 / 1024) as size_mb
FROM (
  SELECT 'tasks' as name, SUM(pgsize) as pgsize FROM dbstat WHERE name='tasks'
  UNION ALL
  SELECT 'vacancies' as name, SUM(pgsize) as pgsize FROM dbstat WHERE name='vacancies'
);

-- Статистика БД
PRAGMA table_info(tasks);
PRAGMA table_info(vacancies);
SELECT COUNT(*) as total_tasks FROM tasks;
SELECT COUNT(*) as total_vacancies FROM vacancies;
```

## Backup и восстановление

### Backup
```bash
# Простой backup файла БД
cp data/hh_v4.sqlite3 backups/hh_v4_backup_$(date +%Y%m%d).sqlite3

# SQL dump
sqlite3 data/hh_v4.sqlite3 .dump > backups/hh_v4_dump_$(date +%Y%m%d).sql

# Backup только схемы
sqlite3 data/hh_v4.sqlite3 .schema > backups/hh_v4_schema.sql
```

### Восстановление
```bash
# Восстановление из файла
cp backups/hh_v4_backup_20250914.sqlite3 data/hh_v4.sqlite3

# Восстановление из SQL dump
sqlite3 data/hh_v4_new.sqlite3 < backups/hh_v4_dump_20250914.sql
```

## Заключение

Схема v4 упрощена по сравнению с v3, но сохраняет совместимость для вакансий. Основное нововведение - централизованная очередь задач `tasks`, которая обеспечивает надежный диспетчинг и мониторинг выполнения.

Производительности SQLite достаточно для планируемой нагрузки 50k+ вакансий/день.
