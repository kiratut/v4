# ПОЛНЫЙ СПРАВОЧНИК ПАРАМЕТРОВ КОНФИГУРАЦИИ HH v4

## Дозаполнение раздела 2.6 "Настройка"

**Дата обновления**: 23.09.2025  
**На основе**: req_16572309.md и анализа кодовой базы v4  

---

## 2.6.1 Ведение фильтров поиска вакансий

**Приоритет**: 3 (исключено из текущего релиза)
**Статус**: Отложено до следующей версии

---

## 2.6.2 Настройки отправки в Telegram

**Приоритет**: 2  
**Расширенное описание**: Полная интеграция с Telegram Bot API для отправки уведомлений, алертов и ежедневных сводок.

**Параметры конфигурации**:
- `telegram_token`: токен бота Telegram для авторизации API, получается через @BotFather
- `telegram_chat_id`: уникальный ID чата для получения сообщений, можно получить через @userinfobot  
- `telegram_enabled`: глобальное включение/отключение всех Telegram уведомлений (true/false)
- `telegram_alerts_enabled`: включение/отключение критических алертов (true/false)
- `telegram_daily_summary_enabled`: включение ежедневных сводок в указанное время (true/false)
- `telegram_daily_summary_time`: время отправки ежедневной сводки в формате HH:MM
- `telegram_retry_delay_minutes`: задержка при превышении лимитов API в минутах (по умолчанию 5)
- `telegram_message_max_length`: максимальная длина сообщения в символах (по умолчанию 4096)
- `telegram_test_message`: текст тестового сообщения для проверки настроек
- `telegram_error_threshold`: количество ошибок API для временного отключения (по умолчанию 5)
- `telegram_queue_max_size`: максимальный размер очереди неотправленных сообщений

**Секция config_v4.json**:
```json
{
  "telegram": {
    "token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID_HERE", 
    "enabled": true,
    "alerts_enabled": true,
    "daily_summary_enabled": true,
    "daily_summary_time": "09:00",
    "retry_delay_minutes": 5,
    "message_max_length": 4096,
    "test_message": "HH Bot v4 test message",
    "error_threshold": 5,
    "queue_max_size": 100
  }
}
```

---

## 2.6.3 Настройки отображения панели

**Приоритет**: 3 (исключено из текущего релиза)
**Статус**: Базовая панель реализована, расширенные настройки отложены

---

## 2.6.4 Настройки сервиса

**Приоритет**: 1  
**Расширенное описание**: Основные параметры работы демона, диспетчера задач, базы данных и системных компонентов.

**Параметры конфигурации**:
- `database_path`: относительный или абсолютный путь к файлу SQLite базы данных
- `database_timeout_sec`: таймаут подключения к БД в секундах для предотвращения блокировок
- `database_wal_mode`: включение WAL режима SQLite для конкурентного доступа (true/false)
- `database_backup_enabled`: автоматическое резервное копирование БД (true/false)
- `database_backup_interval_hours`: интервал создания бэкапов в часах
- `database_vacuum_enabled`: автоматическая оптимизация БД командой VACUUM (true/false)
- `task_dispatcher_max_workers`: количество рабочих потоков диспетчера задач
- `task_dispatcher_chunk_size`: размер чанка задач для параллельной обработки
- `task_dispatcher_monitor_interval_sec`: интервал мониторинга состояния задач в секундах
- `task_dispatcher_default_timeout_sec`: таймаут выполнения задачи по умолчанию
- `task_dispatcher_queue_max_size`: максимальный размер очереди задач
- `vacancy_fetcher_rate_limit_delay`: обязательная задержка между запросами к HH API в секундах
- `vacancy_fetcher_request_timeout_sec`: таймаут HTTP запроса к внешним API
- `vacancy_fetcher_retry_attempts`: количество повторных попыток при ошибках
- `vacancy_fetcher_retry_backoff_sec`: экспоненциальная задержка между повторами
- `vacancy_fetcher_max_pages_per_filter`: ограничение страниц на фильтр для предотвращения зацикливания
- `cleanup_auto_cleanup_enabled`: включение автоматической очистки старых данных
- `cleanup_interval_hours`: интервал запуска процедур автоочистки в часах
- `cleanup_keep_tasks_days`: срок хранения записей задач в днях
- `cleanup_keep_logs_days`: срок хранения файлов логов в днях
- `api_base_url`: базовый URL HH API (по умолчанию https://api.hh.ru)
- `api_user_agent`: User-Agent строка для HTTP запросов, важна для обхода блокировок
- `api_max_retries`: максимальное количество повторных попыток к API при ошибках

**Секция config_v4.json**:
```json
{
  "database": {
    "path": "data/hh_v4.sqlite3",
    "timeout_sec": 30,
    "wal_mode": true,
    "backup_enabled": true,
    "backup_interval_hours": 24,
    "vacuum_enabled": true
  },
  "task_dispatcher": {
    "max_workers": 3,
    "chunk_size": 500,
    "monitor_interval_sec": 10,
    "default_timeout_sec": 3600,
    "queue_max_size": 10000
  },
  "vacancy_fetcher": {
    "rate_limit_delay": 1.0,
    "request_timeout_sec": 30,
    "retry_attempts": 3,
    "retry_backoff_sec": 2,
    "max_pages_per_filter": 200
  },
  "cleanup": {
    "auto_cleanup_enabled": true,
    "interval_hours": 24,
    "keep_tasks_days": 7,
    "keep_logs_days": 30
  },
  "api": {
    "base_url": "https://api.hh.ru",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "max_retries": 3
  }
}
```

---

## 2.6.5 Авторизация HH

**Приоритет**: 1  
**Расширенное описание**: Система профилей авторизации для HH API с автоматической ротацией, обработкой банов и восстановлением после ошибок.

**Параметры конфигурации**:
- `auth_profiles_enabled`: глобальное включение системы профилей авторизации (true/false)
- `auth_rotation_strategy`: стратегия выбора профилей (round_robin, priority, random, load_balancing)
- `auth_profile_cooldown_minutes`: время ожидания после бана профиля перед повторным использованием
- `auth_fallback_user_agent`: запасной User-Agent при получении ошибки 400 Bad Request
- `auth_profile_health_check_interval_minutes`: интервал проверки работоспособности всех профилей
- `auth_ban_detection_keywords`: список ключевых слов в ответе API для определения бана
- `auth_captcha_detection_keywords`: список ключевых слов для определения требования капчи
- `auth_profile_priority_weights`: веса приоритетов профилей для стратегии priority
- `auth_max_consecutive_failures`: максимум подряд идущих ошибок профиля до исключения
- `auth_recovery_check_interval_minutes`: интервал проверки восстановления забаненных профилей
- `auth_default_headers`: базовые HTTP заголовки для всех профилей
- `auth_profile_timeout_sec`: таймаут запросов для проверки профилей

**Структура auth_roles.json**:
```json
{
  "config": {
    "profiles_enabled": true,
    "rotation_strategy": "round_robin",
    "profile_cooldown_minutes": 30,
    "fallback_user_agent": "Mozilla/5.0 (compatible; HHBot/1.0)",
    "health_check_interval_minutes": 15,
    "ban_detection_keywords": ["blocked", "banned", "rate limit", "captcha"],
    "captcha_detection_keywords": ["captcha", "verification", "robot"],
    "max_consecutive_failures": 5,
    "recovery_check_interval_minutes": 60,
    "profile_timeout_sec": 30
  },
  "profiles": [
    {
      "id": "profile_1",
      "name": "Primary Profile",
      "enabled": true,
      "priority": 1,
      "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0",
        "Authorization": "Bearer TOKEN_HERE"
      },
      "rate_limit": {
        "requests_per_minute": 60,
        "burst_limit": 10
      }
    }
  ]
}
```

---

## 2.6.6 Настройки диспетчера

**Приоритет**: 1  
**Расширенное описание**: Конфигурация диспетчера задач для управления очередью обработки, пулом воркеров и мониторингом производительности.

**Параметры конфигурации**:
- `dispatcher_enabled`: глобальное включение диспетчера задач (true/false)
- `dispatcher_worker_pool_size`: размер пула постоянных рабочих потоков
- `dispatcher_dynamic_scaling_enabled`: включение динамического масштабирования воркеров
- `dispatcher_min_workers`: минимальное количество воркеров при динамическом масштабировании
- `dispatcher_max_workers`: максимальное количество воркеров при высокой нагрузке
- `dispatcher_queue_max_size`: максимальный размер очереди задач до блокировки новых
- `dispatcher_task_timeout_sec`: глобальный таймаут выполнения любой задачи
- `dispatcher_health_check_interval_sec`: интервал проверки здоровья диспетчера и воркеров
- `dispatcher_failed_task_retry_limit`: максимальное количество повторов неудачных задач
- `dispatcher_retry_delay_multiplier`: множитель задержки между повторами (1.5, 2.0, и т.д.)
- `dispatcher_metrics_collection_enabled`: включение сбора детальных метрик производительности
- `dispatcher_metrics_retention_hours`: время хранения метрик в часах
- `dispatcher_priority_queue_enabled`: включение приоритизации задач в очереди
- `dispatcher_deadlock_detection_enabled`: включение детекции взаимных блокировок
- `dispatcher_worker_memory_limit_mb`: лимит памяти на воркер в мегабайтах

**Секция config_v4.json**:
```json
{
  "task_dispatcher": {
    "enabled": true,
    "worker_pool_size": 3,
    "dynamic_scaling_enabled": false,
    "min_workers": 1,
    "max_workers": 6,
    "queue_max_size": 10000,
    "task_timeout_sec": 3600,
    "health_check_interval_sec": 30,
    "failed_task_retry_limit": 3,
    "retry_delay_multiplier": 2.0,
    "metrics_collection_enabled": true,
    "metrics_retention_hours": 168,
    "priority_queue_enabled": true,
    "deadlock_detection_enabled": true,
    "worker_memory_limit_mb": 512
  }
}
```

---

## 2.6.7 Настройки логирования

**Приоритет**: 1  
**Расширенное описание**: Централизованная система логирования с поддержкой файлов, базы данных, ротации и различных уровней детализации.

**Параметры конфигурации**:
- `logging_level`: глобальный уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `logging_file_enabled`: включение записи логов в файлы (true/false)
- `logging_file_path`: относительный или абсолютный путь к основному файлу логов
- `logging_max_size_mb`: максимальный размер одного файла лога в мегабайтах
- `logging_backup_count`: количество архивных файлов логов для ротации
- `logging_rotation_enabled`: включение автоматической ротации при достижении размера
- `logging_format`: шаблон формата записей лога с поддержкой переменных Python logging
- `logging_date_format`: формат временных меток в логах
- `logging_db_enabled`: включение дублирования логов в таблицы БД (true/false)
- `logging_db_table`: имя таблицы для хранения логов в SQLite
- `logging_db_retention_days`: автоматическое удаление логов старше указанных дней
- `logging_db_level_filter`: минимальный уровень для записи в БД (может отличаться от файлового)
- `logging_console_enabled`: дублирование логов в консоль/stdout (true/false)
- `logging_console_level`: уровень логов для вывода в консоль
- `logging_structured_format`: использование JSON формата для машинной обработки
- `logging_module_filters`: настройка уровней логирования для отдельных модулей

**Секция config_v4.json**:
```json
{
  "logging": {
    "level": "INFO",
    "file_enabled": true,
    "file_path": "logs/app.log",
    "max_size_mb": 100,
    "backup_count": 5,
    "rotation_enabled": true,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "db_enabled": true,
    "db_table": "system_logs",
    "db_retention_days": 30,
    "db_level_filter": "WARNING",
    "console_enabled": true,
    "console_level": "INFO",
    "structured_format": false,
    "module_filters": {
      "requests": "WARNING",
      "urllib3": "ERROR",
      "core.database_v3": "DEBUG"
    }
  }
}
```

 Примечание: параметр `logging.file` поддерживается как алиас для `logging.file_path`.
 В `ConfigManager.get_logging_settings()` путь к файлу логов читается из `logging.file` (для совместимости);
 при отсутствии параметра используется значение по умолчанию `logs/app.log`.

---

## 2.6.8 Настройки самодиагностики

**Приоритет**: 1  
**Расширенное описание**: Система непрерывного мониторинга состояния системы с настраиваемыми порогами, алертами и автоматическими проверками.

**Параметры конфигурации**:
- `monitoring_enabled`: глобальное включение системы мониторинга (true/false)
- `monitoring_interval_minutes`: основной интервал выполнения проверок в минутах
- `monitoring_cpu_threshold_percent`: порог загрузки CPU для генерации предупреждения
- `monitoring_cpu_critical_percent`: критический порог CPU для экстренных мер
- `monitoring_memory_threshold_percent`: порог использования RAM для предупреждения  
- `monitoring_memory_critical_percent`: критический порог памяти
- `monitoring_disk_threshold_percent`: порог заполнения диска для алерта
- `monitoring_disk_critical_percent`: критический порог дискового пространства
- `monitoring_load_average_threshold`: максимальная средняя нагрузка системы (Linux/Mac)
- `monitoring_process_count_threshold`: максимальное количество процессов системы
- `monitoring_log_error_keywords`: список ключевых слов для поиска ошибок в логах
- `monitoring_log_scan_lines`: количество последних строк лога для анализа
- `monitoring_health_report_format`: формат генерируемых отчетов (json, text, html, telegram)
- `monitoring_alert_cooldown_minutes`: минимальное время между повторными алертами одного типа
- `monitoring_system_info_cache_minutes`: время кэширования системной информации для производительности
- `monitoring_network_check_enabled`: включение проверки сетевого соединения
- `monitoring_network_test_hosts`: список хостов для проверки доступности сети
- `monitoring_service_dependencies`: список внешних сервисов для проверки доступности

**Секция config_v4.json**:
```json
{
  "system_monitoring": {
    "enabled": true,
    "interval_minutes": 5,
    "cpu_threshold_percent": 80,
    "cpu_critical_percent": 95,
    "memory_threshold_percent": 85,
    "memory_critical_percent": 95,
    "disk_threshold_percent": 85,
    "disk_critical_percent": 95,
    "load_average_threshold": 4.0,
    "process_count_threshold": 1000,
    "log_error_keywords": ["ERROR", "CRITICAL", "EXCEPTION", "FAILED", "TIMEOUT"],
    "log_scan_lines": 1000,
    "health_report_format": "telegram",
    "alert_cooldown_minutes": 30,
    "system_info_cache_minutes": 2,
    "network_check_enabled": true,
    "network_test_hosts": ["8.8.8.8", "api.hh.ru", "google.com"],
    "service_dependencies": [
      {
        "name": "HH API",
        "url": "https://api.hh.ru/vacancies",
        "timeout_sec": 10,
        "expected_status": 200
      }
    ]
  }
}
```

---

## 2.6.9 Настройки запросов к LLM

**Приоритет**: 3 (исключено из текущего релиза)  
**Статус**: Базовые заглушки реализованы в mock режиме, полная интеграция отложена

**Параметры конфигурации** (для будущих версий):
- `llm_provider`: провайдер LLM API (openai, anthropic, local, custom)
- `llm_model`: модель для использования (gpt-3.5-turbo, gpt-4, claude-3, и т.д.)
- `llm_api_key`: ключ API для авторизации
- `llm_api_endpoint`: URL эндпоинта API
- `llm_max_tokens`: максимальное количество токенов в ответе
- `llm_temperature`: параметр креативности модели (0.0-1.0)
- `llm_timeout_sec`: таймаут запросов к LLM API
- `llm_retry_attempts`: количество повторных попыток при ошибках
- `llm_batch_size`: размер батча для массовой обработки
- `llm_rate_limit_requests_per_minute`: лимит запросов в минуту
- `llm_cost_tracking_enabled`: отслеживание стоимости запросов
- `llm_fallback_provider`: резервный провайдер при недоступности основного

---

## ИТОГОВАЯ СТРУКТУРА config_v4.json

```json
{
  "database": {
    "path": "data/hh_v4.sqlite3",
    "timeout_sec": 30,
    "wal_mode": true,
    "backup_enabled": true,
    "backup_interval_hours": 24,
    "vacuum_enabled": true
  },
  "task_dispatcher": {
    "enabled": true,
    "worker_pool_size": 3,
    "dynamic_scaling_enabled": false,
    "min_workers": 1,
    "max_workers": 6,
    "queue_max_size": 10000,
    "task_timeout_sec": 3600,
    "health_check_interval_sec": 30,
    "failed_task_retry_limit": 3,
    "retry_delay_multiplier": 2.0,
    "metrics_collection_enabled": true,
    "metrics_retention_hours": 168,
    "priority_queue_enabled": true,
    "deadlock_detection_enabled": true,
    "worker_memory_limit_mb": 512
  },
  "vacancy_fetcher": {
    "rate_limit_delay": 1.0,
    "request_timeout_sec": 30,
    "retry_attempts": 3,
    "retry_backoff_sec": 2,
    "max_pages_per_filter": 200
  },
  "logging": {
    "level": "INFO",
    "file_enabled": true,
    "file_path": "logs/app.log",
    "max_size_mb": 100,
    "backup_count": 5,
    "rotation_enabled": true,
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S",
    "db_enabled": true,
    "db_table": "system_logs",
    "db_retention_days": 30,
    "db_level_filter": "WARNING",
    "console_enabled": true,
    "console_level": "INFO",
    "structured_format": false,
    "module_filters": {
      "requests": "WARNING",
      "urllib3": "ERROR",
      "core.database_v3": "DEBUG"
    }
  },
  "cleanup": {
    "auto_cleanup_enabled": true,
    "interval_hours": 24,
    "keep_tasks_days": 7,
    "keep_logs_days": 30
  },
  "api": {
    "base_url": "https://api.hh.ru",
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "max_retries": 3
  },
  "system_monitoring": {
    "enabled": true,
    "interval_minutes": 5,
    "cpu_threshold_percent": 80,
    "cpu_critical_percent": 95,
    "memory_threshold_percent": 85,
    "memory_critical_percent": 95,
    "disk_threshold_percent": 85,
    "disk_critical_percent": 95,
    "log_error_keywords": ["ERROR", "CRITICAL", "EXCEPTION", "FAILED", "TIMEOUT"],
    "log_scan_lines": 1000,
    "health_report_format": "telegram",
    "alert_cooldown_minutes": 30,
    "system_info_cache_minutes": 2,
    "network_check_enabled": true,
    "network_test_hosts": ["8.8.8.8", "api.hh.ru", "google.com"]
  },
  "telegram": {
    "token": "YOUR_BOT_TOKEN_HERE",
    "chat_id": "YOUR_CHAT_ID_HERE",
    "enabled": false,
    "alerts_enabled": true,
    "daily_summary_enabled": true,
    "daily_summary_time": "09:00",
    "retry_delay_minutes": 5,
    "message_max_length": 4096,
    "test_message": "HH Bot v4 test message",
    "error_threshold": 5,
    "queue_max_size": 100
  },
  "web_interface": {
    "enabled": true,
    "host": "localhost",
    "port": 8000,
    "auto_start": true,
    "auto_refresh_sec": 30
  },
  "hosts": {
    "host1": {
      "name": "Primary Data Storage",
      "description": "SQLite database for vacancy storage and versioning",
      "enabled": true,
      "type": "sqlite"
    },
    "host2": {
      "name": "Analytics PostgreSQL",
      "description": "PostgreSQL analytics and aggregation service",
      "enabled": true,
      "mock_mode": true,
      "type": "postgresql"
    },
    "host3": {
      "name": "LLM Analysis Service", 
      "description": "AI-powered vacancy analysis and matching",
      "enabled": true,
      "mock_mode": true,
      "type": "llm"
    }
  }
}
```

---

**Документ подготовлен**: AI Assistant  
**Дата**: 23.09.2025 17:45  
**Статус**: ГОТОВО К ИСПОЛЬЗОВАНИЮ
