# АРХИТЕКТУРНАЯ РЕВИЗИЯ HH v4 (23.09.2025)

## EXECUTIVE SUMMARY

**Цель**: Полный пересмотр архитектуры v4 на основе новых функциональных требований req_16572309.md  
**Статус**: ПЛАН РАБОТ  
**Приоритеты**: Только приоритеты 1-2 (приоритет 3 исключается из текущего релиза)  
**Дата**: 23.09.2025 17:30  

## 1. АНАЛИЗ НОВЫХ ТРЕБОВАНИЙ

### 1.1 Статистика приоритетов

**Приоритет 1 (Критические)**: 23 требования
- Самодиагностика: CPU/RAM/Disk мониторинг, статус демона, авторизация HH
- Сервис-демон: запуск/останов, веб-панель, диагностика, диспетчер задач
- Настройки: конфиг сервиса, авторизация, диспетчер, логирование
- Авторизация HH: профили, ротация, обработка ошибок
- База данных: health check, CRUD операции, экспорт
- Поиск/загрузка: API запросы, сбор ID, загрузка, дедупликация

**Приоритет 2 (Важные)**: 25 требований
- Обслуживание: очистка логов и архивов
- Логирование: централизованное в БД и файлы
- Панель-пульт: показатели, управление загрузками, фильтры
- Настройки Telegram: уведомления и алерты
- База данных: производительность, статистика, очистка
- Восстановление: обработка сбоев API, диска, БД

**Приоритет 3 (Исключены)**: 12 требований
- LLM классификация, работодатели, отклики, Telegram интеграция

### 1.2 Ключевые изменения архитектуры

**ДОБАВИТЬ**:
1. **Централизованная самодиагностика** - модуль мониторинга системных ресурсов
2. **Система настроек** - единый конфигурационный интерфейс
3. **Консолидированное тестирование** - 1-2 модуля с общим выводом
4. **Улучшенная веб-панель** - блочная структура с индикаторами
5. **Telegram интеграция** - уведомления и алерты (приоритет 2)

**ПЕРЕМЕСТИТЬ В ARCHIVE**:
- Устаревшие документы анализа и планирования
- Временные скрипты отладки
- Дубли архитектурных документов

**РЕФАКТОРИНГ**:
- Перекомпоновка функций по модулям согласно новым требованиям
- Оптимизация структуры тестов
- Унификация логирования

## 2. НОВАЯ МОДУЛЬНАЯ АРХИТЕКТУРА

### 2.1 Структура директорий

```
v4/
├── core/                    # Ядро системы
│   ├── scheduler_daemon.py  # Демон планировщика + самодиагностика
│   ├── database_v3.py       # БД с health check + статистика
│   ├── task_dispatcher.py   # Диспетчер + мониторинг задач
│   ├── auth.py              # Авторизация HH + ротация профилей
│   ├── system_monitor.py    # NEW: Системный мониторинг (2.1.*)
│   ├── config_manager.py    # NEW: Менеджер конфигурации (2.6.*)
│   └── notification.py      # NEW: Telegram уведомления (2.6.2)
├── plugins/
│   ├── fetcher_v4.py        # Загрузчик + обработка ошибок API
│   └── base.py              # Базовые классы
├── tests/
│   ├── consolidated_tests.py # NEW: Основные тесты приоритет 1-2
│   └── diagnostic_tests.py   # NEW: Самодиагностика и мониторинг
├── web/
│   ├── monitoring_dashboard.py # Обновленная панель
│   ├── static/
│   │   ├── dashboard.js     # NEW: Блочная структура
│   │   └── style.css        # NEW: Responsive design
│   └── templates/
│       └── dashboard.html   # NEW: Модульный дизайн
├── config/
│   ├── config_v4.json       # Расширенная конфигурация
│   ├── auth_roles.json      # Профили авторизации
│   └── filters.json         # Фильтры поиска
└── cli_v4.py                # Единая точка входа - все команды
```

### 2.2 Детализация модулей

#### 2.2.1 core/system_monitor.py (NEW)
**Назначение**: Самодиагностика системы (требования 2.1.*)
**Функции**:
- `check_system_resources()` - CPU/RAM/Disk мониторинг (2.1.1)
- `check_daemon_status()` - статус демона и время запуска (2.1.2)
- `check_hh_authorization()` - проверка профилей авторизации (2.1.3)
- `check_log_health()` - проверка логов на ошибки (2.1.6)
- `generate_health_report()` - сжатие отчета для Telegram (2.1.7)

#### 2.2.2 core/config_manager.py (NEW)
**Назначение**: Единое управление настройками (требования 2.6.*)
**Функции**:
- `load_config()` - загрузка всех конфигов (2.6.4)
- `get_auth_settings()` - настройки авторизации (2.6.5)
- `get_dispatcher_settings()` - параметры диспетчера (2.6.6)
- `get_logging_settings()` - настройки логирования (2.6.7)
- `get_monitoring_settings()` - пороги самодиагностики (2.6.8)
- `get_telegram_settings()` - параметры Telegram (2.6.2)

#### 2.2.3 core/notification.py (NEW)
**Назначение**: Telegram интеграция (приоритет 2)
**Функции**:
- `send_alert()` - отправка критических уведомлений
- `send_daily_summary()` - ежедневные сводки
- `manage_notification_queue()` - очередь сообщений
- `check_telegram_api()` - проверка доступности API

## 3. ПЛАН ОЧИСТКИ И АРХИВАЦИИ

### 3.1 Файлы для архивации в /docs/archive/

```bash
# Устаревшие аналитические документы
Architecture_v4_Host1.md → archive/Architecture_v4_Host1_archived_20250923.md
Requirements_Refinement_Analysis.md → archive/Requirements_Refinement_Analysis_archived_20250923.md
Requirements_Test_Catalog.md → archive/Requirements_Test_Catalog_archived_20250923.md

# Дубли и временные документы
Consolidated_Documentation.md (пустой) → удалить
Consolidated_Requirements_View.md → archive/
catalog_v3.md (слишком большой) → archive/

# Временные файлы Excel
~$req.xlsx → удалить
```

### 3.2 Скрипты для очистки в /utils, /scripts

```bash
# Отладочные скрипты старше 30 дней
utils/*debug*.py → data/.trash/
scripts/*temp*.py → data/.trash/

# Старые проверочные утилиты
utils/check_*.py → оценить актуальность, часть в archive/
```

## 4. КОНСОЛИДАЦИЯ ТЕСТОВ

### 4.1 Новая структура тестирования

**tests/consolidated_tests.py** - Основной модуль тестов
```python
class Priority1Tests:
    """Критические тесты - должны проходить 100%"""
    def test_system_resources(self)      # 2.1.1
    def test_daemon_status(self)         # 2.1.2
    def test_hh_authorization(self)      # 2.1.3
    def test_daemon_start_stop(self)     # 2.4.1
    def test_web_interface(self)         # 2.4.2
    def test_task_dispatcher(self)       # 2.4.5
    def test_config_loading(self)        # 2.6.4
    def test_database_health(self)       # 2.10.1
    def test_vacancy_crud(self)          # 2.10.3-2.10.5
    def test_api_requests(self)          # 2.11.1
    def test_vacancy_loading(self)       # 2.12.1-2.12.4

class Priority2Tests:
    """Важные тесты - могут иметь известные ограничения"""
    def test_log_cleanup(self)           # 2.2.1-2.2.2
    def test_centralized_logging(self)   # 2.3.1
    def test_dashboard_metrics(self)     # 2.5.1
    def test_telegram_notifications(self) # 2.6.2
    def test_api_recovery(self)          # 2.17.1-2.17.3
```

**tests/diagnostic_tests.py** - Самодиагностика и мониторинг
```python
class SystemDiagnosticTests:
    """Тесты самодиагностики - запуск по требованию"""
    def test_resource_thresholds(self)   # Пороговые значения
    def test_alert_generation(self)      # Генерация алертов
    def test_health_report_format(self)  # Формат отчетов
```

### 4.2 Команда запуска всех тестов

```bash
# Единая команда для всех тестов с общим выводом
python cli_v4.py test consolidated --priority 1,2

# Ожидаемый вывод:
# =====================================
# HH v4 CONSOLIDATED TEST RESULTS
# =====================================
# Priority 1 Tests: 11/11 passed (100%)
# Priority 2 Tests: 8/10 passed (80%)
# Total: 19/21 passed (90.5%)
# =====================================
# Failed tests:
# - test_telegram_notifications: API key not configured
# - test_dashboard_metrics: Port 5000 not accessible
# =====================================
```

## 5. ДОЗАПОЛНЕНИЕ РАЗДЕЛА "НАСТРОЙКА" (2.6)

### 5.1 Полный список параметров по модулям

**2.6.1 Фильтры поиска** (приоритет 3 - исключено)

**2.6.2 Настройки Telegram** (приоритет 2)
```
telegram_token: токен бота Telegram для отправки уведомлений
telegram_chat_id: ID чата для получения сообщений  
telegram_enabled: включение/отключение Telegram уведомлений
telegram_alerts_enabled: включение/отключение алертов
telegram_daily_summary: ежедневные сводки в указанное время
telegram_retry_delay: задержка при бане API в минутах (по умолчанию 5)
telegram_test_message: тестовое сообщение для проверки настроек
```

**2.6.3 Настройки панели** (приоритет 3 - исключено)

**2.6.4 Настройки сервиса** (приоритет 1)
```
database_path: путь к файлу SQLite базы данных
database_timeout_sec: таймаут подключения к БД в секундах  
database_wal_mode: включение WAL режима для конкурентного доступа
task_dispatcher_max_workers: количество рабочих потоков диспетчера
task_dispatcher_chunk_size: размер чанка задач для обработки
task_dispatcher_monitor_interval_sec: интервал мониторинга задач
task_dispatcher_default_timeout_sec: таймаут выполнения задачи по умолчанию
vacancy_fetcher_rate_limit_delay: задержка между запросами к HH API
vacancy_fetcher_request_timeout_sec: таймаут HTTP запроса
vacancy_fetcher_retry_attempts: количество повторных попыток
vacancy_fetcher_retry_backoff_sec: задержка между повторами
vacancy_fetcher_max_pages_per_filter: максимум страниц на фильтр
cleanup_auto_cleanup_enabled: включение автоматической очистки
cleanup_cleanup_interval_hours: интервал автоочистки в часах
cleanup_keep_tasks_days: срок хранения задач в днях
cleanup_keep_logs_days: срок хранения логов в днях
api_base_url: базовый URL HH API
api_user_agent: User-Agent для HTTP запросов
api_max_retries: максимум повторных попыток к API
```

**2.6.5 Авторизация HH** (приоритет 1)
```
auth_profiles_enabled: включение системы профилей авторизации
auth_rotation_strategy: стратегия ротации профилей (round_robin, priority, random)
auth_profile_cooldown_minutes: время ожидания после бана профиля
auth_fallback_user_agent: запасной User-Agent при ошибке 400
auth_profile_health_check_interval: интервал проверки работоспособности профилей
auth_ban_detection_keywords: ключевые слова для определения бана
auth_captcha_detection_keywords: ключевые слова для определения капчи
```

**2.6.6 Настройки диспетчера** (приоритет 1)
```
dispatcher_enabled: включение диспетчера задач
dispatcher_worker_pool_size: размер пула рабочих потоков
dispatcher_queue_max_size: максимальный размер очереди задач  
dispatcher_task_timeout_sec: таймаут выполнения задачи
dispatcher_health_check_interval: интервал проверки здоровья диспетчера
dispatcher_failed_task_retry_limit: лимит повторов неудачных задач
dispatcher_metrics_collection_enabled: сбор метрик производительности
```

**2.6.7 Настройки логирования** (приоритет 1)
```
logging_level: уровень логирования (DEBUG, INFO, WARNING, ERROR)
logging_file_path: путь к файлу логов
logging_max_size_mb: максимальный размер файла лога в МБ
logging_backup_count: количество архивных файлов логов
logging_format: формат записей лога
logging_db_enabled: включение логирования в БД
logging_db_table: таблица для логов в БД
logging_db_retention_days: срок хранения логов в БД
logging_console_enabled: вывод логов в консоль
logging_rotation_enabled: включение ротации логов
```

**2.6.8 Настройки самодиагностики** (приоритет 1)
```
monitoring_enabled: включение системного мониторинга
monitoring_interval_minutes: интервал проверок в минутах (по умолчанию 5)
monitoring_cpu_threshold_percent: порог загрузки CPU для алерта
monitoring_memory_threshold_percent: порог использования RAM для алерта  
monitoring_disk_threshold_percent: порог заполнения диска для алерта
monitoring_log_error_keywords: ключевые слова ошибок в логах
monitoring_health_report_format: формат отчета (json, text, telegram)
monitoring_alert_cooldown_minutes: время между повторными алертами
monitoring_system_info_cache_minutes: время кэширования системной информации
```

**2.6.9 Настройки LLM** (приоритет 3 - исключено)

## 6. ПРОЕКТИРОВАНИЕ WEB-ПАНЕЛИ

### 6.1 Блочная структура панели

```
┌─────────────────────────────────────────────────────────────┐
│                    HH v4 CONTROL PANEL                     │
├─────────────────────────────────────────────────────────────┤
│ [System Status] [Daemon Status] [Tasks Queue] [API Health] │
├─────────────────────────────────────────────────────────────┤
│ [Resource Monitor]              [Recent Activity]          │ 
│ CPU: ████░░ 67%                Activity Log:               │
│ RAM: ███░░░ 54%                15:30 Task completed        │
│ Disk: ██░░░░ 23%               15:25 API request OK        │
│                                15:20 System check         │
├─────────────────────────────────────────────────────────────┤
│ [Task Management]                                           │
│ ┌─────────┬──────────┬─────────┬─────────┬─────────────────┐│
│ │Filter   │Status    │Progress │Workers  │Actions          ││
│ ├─────────┼──────────┼─────────┼─────────┼─────────────────┤│
│ │python-rem│running  │67%      │2/3      │[Pause][Stop]    ││
│ │java-dev  │pending  │0%       │0/3      │[Start][Config]  ││
│ └─────────┴──────────┴─────────┴─────────┴─────────────────┘│
├─────────────────────────────────────────────────────────────┤
│ [Quick Actions]                 [Settings]                 │
│ [Manual Refresh] [Run Test]     [Edit Config] [View Logs]  │
│ [Emergency Stop] [Export Data]  [Telegram] [Auth Profiles] │  
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Индикаторы и контролы

**Системные индикаторы**:
- Статус демона: Зеленый/Красный + PID + Uptime
- Очередь задач: Количество pending/running/completed
- API здоровье: Последний успешный запрос + статистика ошибок
- Ресурсы: CPU/RAM/Disk с цветовой индикацией порогов

**Контролы управления**:
- Фильтры загрузки: чекбоксы активности + статус выполнения
- Управление задачами: кнопки Start/Pause/Stop для каждого фильтра
- Настройки: прямые ссылки на разделы конфигурации
- Экспорт: кнопки экспорта данных в разных форматах

**Лог активности**:
- Последние 10 записей с временными метками
- Фильтрация по уровням (INFO/WARNING/ERROR)
- Прямая ссылка на полные логи

### 6.3 Responsive адаптация

**Desktop (>1200px)**: Полная 4-колоночная раскладка
**Tablet (768-1200px)**: 2-колоночная раскладка с вертикальным стеком
**Mobile (<768px)**: Одноколоночная с коллапсирующими блоками

### 6.4 Технические возможности веб-дизайна

**Рекомендуемые инструменты для дизайна**:

1. **Figma** (https://figma.com)
   - Создание mockup'ов и интерактивных прототипов
   - Экспорт CSS кода и assets
   - Совместная работа над дизайном

2. **Webflow** (https://webflow.com)
   - Визуальный веб-дизайнер с экспортом HTML/CSS
   - Готовые responsive компоненты
   - Прямая интеграция с веб-проектами

3. **Bootstrap Studio** (https://bootstrapstudio.io)
   - Drag-and-drop интерфейс на базе Bootstrap
   - Экспорт готового HTML/CSS/JS кода
   - Встроенные компоненты для dashboard'ов  

4. **Tailwind UI** (https://tailwindui.com)
   - Готовые компоненты для admin панелей
   - Копирование готового кода компонентов
   - Responsive дизайн из коробки

**JSON конфигурация дизайна**:
```json
{
  "layout": {
    "grid": "4-column",
    "responsive_breakpoints": [768, 1200],
    "block_spacing": "1rem"
  },
  "colors": {
    "primary": "#2563eb",
    "success": "#059669", 
    "warning": "#d97706",
    "danger": "#dc2626",
    "background": "#f8fafc"
  },
  "blocks": [
    {
      "id": "system_status",
      "title": "System Status",
      "size": "col-1",
      "refresh_interval": 30,
      "indicators": ["daemon_pid", "uptime", "version"]
    },
    {
      "id": "resource_monitor", 
      "title": "Resource Monitor",
      "size": "col-2",
      "refresh_interval": 5,
      "charts": ["cpu_usage", "memory_usage", "disk_usage"]
    }
  ]
}
```

## 7. ПЛАН ВЫПОЛНЕНИЯ РАБОТ

### 7.1 Этап 1: Подготовка (1 день)
- ✅ Анализ требований по приоритетам 1-2
- ✅ Составление плана архитектурной ревизии
- ⏳ Архивация устаревших файлов
- ⏳ Подготовка новой структуры модулей

### 7.2 Этап 2: Модульный рефакторинг (2-3 дня)
- Создание новых модулей: system_monitor.py, config_manager.py, notification.py
- Перенос функций в соответствующие модули согласно требованиям
- Обновление импортов и зависимостей
- Тестирование совместимости

### 7.3 Этап 3: Консолидация тестов (1 день)
- Создание consolidated_tests.py и diagnostic_tests.py  
- Группировка существующих тестов по приоритетам
- Добавление недостающих тестов для новых требований
- Настройка единой команды запуска с общим выводом

### 7.4 Этап 4: Обновление конфигурации (1 день)
- Дозаполнение раздела 2.6 всеми параметрами из модулей
- Расширение config_v4.json новыми секциями
- Создание документации по всем параметрам
- Валидация конфигурации

### 7.5 Этап 5: Веб-панель (2 дня)
- Проектирование блочной структуры
- Создание responsive дизайна
- Реализация индикаторов и контролов
- Интеграция с backend API

### 7.6 Этап 6: Интеграционное тестирование (1 день)
- Полное тестирование архитектуры
- Проверка всех требований приоритетов 1-2
- Документирование изменений
- Создание migration guide

## 8. КРИТЕРИИ УСПЕХА

### 8.1 Количественные метрики
- **Покрытие требований**: 100% приоритет 1, 90%+ приоритет 2
- **Тестирование**: 95%+ тестов проходят успешно
- **Производительность**: время отклика веб-панели <2 сек
- **Архивация**: 80%+ неактуальных файлов в archive

### 8.2 Качественные критерии
- Все модули имеют четкое назначение согласно требованиям
- Тесты запускаются одной командой с понятным выводом
- Веб-панель адаптивна и интуитивна
- Документация актуальна и полна

## 9. РИСКИ И МИТИГАЦИЯ

### 9.1 Технические риски
- **Обратная совместимость**: детальное тестирование после рефакторинга
- **Производительность**: профилирование критических модулей
- **Зависимости**: версионирование всех внешних библиотек

### 9.2 Ресурсные риски  
- **Время**: поэтапное выполнение с промежуточными чекпойнтами
- **Тестирование**: автоматизация регрессионных тестов
- **Документация**: синхронное обновление с кодом

---

**Документ подготовлен**: AI Assistant  
**Дата**: 23.09.2025 17:30  
**Версия**: 1.0  
**Статус**: ПЛАН К ИСПОЛНЕНИЮ
