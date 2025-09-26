# Архитектура HH-бота v4 - Хост 1 (Основной)

*Создано: 19.09.2025 17:08:16*

## 1. Общая концепция

### 1.1. Роль Хоста 1 в системе
- **Основная функция**: Сбор, первичная обработка и буферизация данных
- **БД1**: SQLite как локальный буфер и основное хранилище для автономной работы
- **Заглушки**: Подготовка интерфейсов для будущей интеграции с Хост 2 (PostgreSQL) и Хост 3 (LLM)
- **Кроссплатформенность**: Единый код для Windows и Linux

### 1.2. Принципы архитектуры
- **Модульность**: Четкое разделение компонентов с возможностью замены
- **Автономность**: Полная функциональность без внешних зависимостей
- **Расширяемость**: Готовность к добавлению новых хостов
- **Отказоустойчивость**: Graceful degradation при сбоях компонентов

## 2. Структура компонентов

### 2.1. Текущая реализация v4
```
/hh_v4/
├── core/                          # Ядро системы
│   ├── __init__.py
│   ├── auth.py                    # Авторизация HH.ru (auth_roles.json)
│   ├── database_v3.py             # БД1 - SQLite операции
│   ├── models.py                  # Модели данных
│   ├── task_database.py           # Система задач
│   └── task_dispatcher.py         # Диспетчер задач
├── plugins/                       # Плагины обработки
│   ├── base.py                    # Базовый класс плагина
│   └── fetcher_v4.py             # Загрузка с HH.ru + UA fallback
├── config/                        # Конфигурация
│   ├── auth_roles.json           # Роли авторизации для задач
│   ├── config_v4.json            # Основная конфигурация
│   └── filters.json              # Фильтры поиска
├── web/                          # Веб-панель мониторинга
│   ├── server.py                 # FastAPI сервер
│   ├── templates/dashboard.html  # UI панели
│   └── static/                   # CSS/JS ресурсы
├── scripts/                      # Вспомогательные скрипты
├── tests/                        # Тесты
├── docs/                         # Документация
├── cli_v4.py                     # CLI интерфейс
└── run_v4.py                     # Основной запуск
```

### 2.2. Заглушки для будущих хостов

#### 2.2.1. Хост 2 - БД2 заглушка
```python
# core/host2_client.py
class PostgreSQLClient:
    """Заглушка для подключения к БД2 (PostgreSQL)"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        
    def sync_vacancies(self, vacancy_ids: List[str]) -> bool:
        """Синхронизация вакансий с БД2"""
        if not self.enabled:
            return True  # Имитация успеха
        # TODO: Реализация подключения к PostgreSQL
        
    def check_connection(self) -> bool:
        """Проверка подключения к БД2"""
        if not self.enabled:
            return False
        # TODO: Реализация ping БД2
```

#### 2.2.2. Хост 3 - LLM заглушка  
```python
# core/host3_client.py
class LLMClient:
    """Заглушка для LLM обработки (Хост 3)"""
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        
    def classify_vacancy(self, vacancy_data: dict) -> dict:
        """Классификация вакансии через LLM"""
        if not self.enabled:
            return {"status": "skipped", "reason": "llm_disabled"}
        # TODO: Интеграция с облачными LLM API
        
    def generate_cover_letter(self, vacancy_data: dict) -> str:
        """Генерация сопроводительного письма"""
        if not self.enabled:
            return "Template cover letter"  # Шаблон
        # TODO: LLM генерация письма
```

### 2.3. Кроссплатформенные пути

#### 2.3.1. Менеджер путей
```python
# core/platform_paths.py
import os
import platform
from pathlib import Path

class PlatformPaths:
    """Кроссплатформенное управление путями"""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.base_dir = Path(__file__).parent.parent
        
    def get_data_path(self) -> Path:
        """Путь к данным"""
        if self.is_windows:
            return self.base_dir / "data"
        else:
            return Path("/var/lib/hh-tool/data")
            
    def get_log_path(self) -> Path:
        """Путь к логам"""
        if self.is_windows:
            return self.base_dir / "logs"
        else:
            return Path("/var/log/hh-tool")
            
    def get_config_path(self) -> Path:
        """Путь к конфигурации"""
        if self.is_windows:
            return self.base_dir / "config"
        else:
            return Path("/etc/hh-tool")
```

## 3. Схема БД1 с версионированием

### 3.1. Принципы версионирования
- **Контент-хэш**: Проверка изменений по набору ключевых полей
- **Инкрементальные версии**: version=1 для новых, version++ при изменениях
- **Очистка дублей**: Удаление идентичных версий по content_hash

### 3.2. Основные таблицы

#### 3.2.1. Вакансии с версионированием
```sql
-- Основная таблица вакансий
CREATE TABLE vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hh_id TEXT NOT NULL,                    -- ID с HH.ru
    version INTEGER NOT NULL DEFAULT 1,     -- Версия записи
    content_hash TEXT NOT NULL,             -- Хэш для дедупликации
    
    -- Основные поля вакансии
    title TEXT NOT NULL,
    company_name TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    currency TEXT,
    experience TEXT,
    employment TEXT,
    description TEXT,
    requirements TEXT,
    
    -- Метаданные
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_filter_id TEXT,                  -- Какой фильтр нашел
    
    -- Флаги синхронизации
    synced_to_host2 BOOLEAN DEFAULT FALSE,  -- Синхронизировано с БД2
    processed_by_host3 BOOLEAN DEFAULT FALSE, -- Обработано LLM
    
    -- Индексы
    UNIQUE(hh_id, version),
    INDEX(content_hash),
    INDEX(synced_to_host2),
    INDEX(processed_by_host3)
);
```

#### 3.2.2. Работодатели с версионированием
```sql
CREATE TABLE employers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hh_employer_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    content_hash TEXT NOT NULL,
    
    -- Данные работодателя
    name TEXT NOT NULL,
    description TEXT,
    site_url TEXT,
    logo_url TEXT,
    
    -- Метаданные
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Флаги синхронизации  
    synced_to_host2 BOOLEAN DEFAULT FALSE,
    
    UNIQUE(hh_employer_id, version),
    INDEX(content_hash),
    INDEX(synced_to_host2)
);
```

#### 3.2.3. Очередь задач
```sql
CREATE TABLE task_queue (
    id TEXT PRIMARY KEY,                    -- UUID задачи
    type TEXT NOT NULL,                     -- load_vacancies, classify, etc
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    params TEXT,                            -- JSON параметры
    result TEXT,                            -- JSON результат
    error TEXT,                             -- Текст ошибки
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    timeout_sec INTEGER DEFAULT 3600,
    
    INDEX(status),
    INDEX(type),
    INDEX(created_at)
);
```

### 3.3. Алгоритм версионирования

#### 3.3.1. Функция вычисления content_hash
```python
def calculate_content_hash(vacancy_data: dict) -> str:
    """Вычисление хэша для версионирования вакансий"""
    # Ключевые поля для определения изменений
    key_fields = [
        'title', 'company_name', 'salary_min', 'salary_max',
        'experience', 'employment', 'description', 'requirements'
    ]
    
    content_parts = []
    for field in key_fields:
        value = vacancy_data.get(field, '')
        if value:
            content_parts.append(f"{field}:{str(value).strip()}")
    
    content_string = '|'.join(content_parts)
    return hashlib.sha256(content_string.encode('utf-8')).hexdigest()[:16]
```

#### 3.3.2. Логика сохранения с версионированием
```python
def save_vacancy_with_versioning(self, vacancy_data: dict) -> dict:
    """Сохранение вакансии с автоматическим версионированием"""
    hh_id = vacancy_data['hh_id']
    new_hash = calculate_content_hash(vacancy_data)
    
    with self._connect() as conn:
        cursor = conn.cursor()
        
        # Проверяем существующие версии
        cursor.execute("""
            SELECT version, content_hash FROM vacancies 
            WHERE hh_id = ? ORDER BY version DESC LIMIT 1
        """, (hh_id,))
        
        existing = cursor.fetchone()
        
        if existing:
            last_version, last_hash = existing
            if last_hash == new_hash:
                return {"action": "duplicate", "version": last_version}
            else:
                new_version = last_version + 1
        else:
            new_version = 1
            
        # Вставляем новую версию
        vacancy_data['version'] = new_version
        vacancy_data['content_hash'] = new_hash
        
        # SQL INSERT здесь...
        
        return {"action": "created", "version": new_version}
```

## 4. Интеграция компонентов

### 4.1. Диспетчер с заглушками
```python
# core/integrated_dispatcher.py
class IntegratedDispatcher:
    """Диспетчер с поддержкой всех хостов"""
    
    def __init__(self, config: dict):
        self.host2_client = PostgreSQLClient(config.get('host2_enabled', False))
        self.host3_client = LLMClient(config.get('host3_enabled', False))
        self.platform_paths = PlatformPaths()
        
    async def process_vacancy_pipeline(self, vacancy_data: dict):
        """Полный pipeline обработки вакансии"""
        # 1. Сохранение в БД1 с версионированием
        save_result = self.db.save_vacancy_with_versioning(vacancy_data)
        
        # 2. Синхронизация с БД2 (заглушка)
        if self.host2_client.enabled:
            sync_success = await self.host2_client.sync_vacancies([vacancy_data['hh_id']])
            # Обновление флага synced_to_host2
            
        # 3. LLM обработка (заглушка)
        if self.host3_client.enabled:
            llm_result = await self.host3_client.classify_vacancy(vacancy_data)
            # Сохранение результатов классификации
            
        return save_result
```

### 4.2. Конфигурационный файл
```json
{
    "version": "4.0",
    "host1": {
        "database": {
            "path": "data/hh_v4.sqlite3",
            "backup_interval_hours": 24
        },
        "web": {
            "host": "localhost",
            "port": 8080
        }
    },
    "host2": {
        "enabled": false,
        "postgresql": {
            "host": "localhost",
            "port": 5432,
            "database": "hh_shared",
            "user": "hh_user"
        }
    },
    "host3": {
        "enabled": false,
        "llm": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "max_tokens": 1000
        }
    },
    "platform": {
        "auto_detect": true,
        "force_windows_paths": false
    }
}
```

## 5. Стратегия миграции

### 5.1. Этапы развертывания
1. **Этап 1**: Хост 1 автономно (текущее состояние + версионирование)
2. **Этап 2**: Подключение БД2 (замена заглушки Host2Client)
3. **Этап 3**: Интеграция LLM (замена заглушки Host3Client)
4. **Этап 4**: Полная распределенная система

### 5.2. Принципы обратной совместимости
- Все API остаются неизменными
- Заглушки обеспечивают корректную работу без внешних зависимостей
- Конфигурация позволяет постепенное включение компонентов

*Chg_ARCH_HOST1_1909: Создана архитектура Хоста 1 с заглушками и версионированием*

*Обновлено: 19.09.2025 17:08:16*
