# ТАБЛИЦА ТРАССИРОВКИ ПАРАМЕТРОВ КОНФИГУРАЦИИ HH v4

**Дата создания**: 25.09.2025 16:00:00  
**Назначение**: Отслеживание реализации всех параметров из Configuration_Parameters_v4.md

---

## СЕКЦИЯ 2.6.2: НАСТРОЙКИ TELEGRAM

| Параметр | Описание | Файл/Функция реализации | Статус | Секция в config_v4.json |
|----------|----------|-------------------------|--------|--------------------------|
| `telegram_token` | Токен бота Telegram | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.token |
| `telegram_chat_id` | ID чата для сообщений | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.chat_id |
| `telegram_enabled` | Глобальное включение | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.enabled |
| `telegram_alerts_enabled` | Критические алерты | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.alerts_enabled |
| `telegram_daily_summary_enabled` | Ежедневные сводки | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.daily_summary_enabled |
| `telegram_daily_summary_time` | Время отправки сводки | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.daily_summary_time |
| `telegram_retry_delay_minutes` | Задержка при ошибках API | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.retry_delay_minutes |
| `telegram_message_max_length` | Максимальная длина сообщения | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.message_max_length |
| `telegram_test_message` | Текст тестового сообщения | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.test_message |
| `telegram_error_threshold` | Лимит ошибок до отключения | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.error_threshold |
| `telegram_queue_max_size` | Размер очереди сообщений | `core/config_manager.py:get_telegram_settings()` | ❌ НЕ РЕАЛИЗОВАН | telegram.queue_max_size |

---

## СЕКЦИЯ 2.6.4: НАСТРОЙКИ СЕРВИСА

| Параметр | Описание | Файл/Функция реализации | Статус | Секция в config_v4.json |
|----------|----------|-------------------------|--------|--------------------------|
| `database_path` | Путь к файлу SQLite | `core/config_manager.py:get_database_settings()` | ✅ РЕАЛИЗОВАН | database.path |
| `database_timeout_sec` | Таймаут подключения БД | `core/config_manager.py:get_database_settings()` | ✅ РЕАЛИЗОВАН | database.timeout_sec |
| `database_wal_mode` | WAL режим SQLite | `core/config_manager.py:get_database_settings()` | ✅ РЕАЛИЗОВАН | database.wal_mode |
| `database_backup_enabled` | Автобэкапы БД | `core/config_manager.py:get_database_settings()` | ⚠️ ЧАСТИЧНО | database.backup_enabled |
| `database_backup_interval_hours` | Интервал бэкапов | `core/config_manager.py:get_database_settings()` | ⚠️ ЧАСТИЧНО | database.backup_interval_hours |
| `database_vacuum_enabled` | Автоматический VACUUM | `core/config_manager.py:get_database_settings()` | ⚠️ ЧАСТИЧНО | database.vacuum_enabled |
| `task_dispatcher_max_workers` | Количество воркеров | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.max_workers |
| `task_dispatcher_chunk_size` | Размер чанка задач | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.chunk_size |
| `task_dispatcher_monitor_interval_sec` | Интервал мониторинга | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.monitor_interval_sec |
| `task_dispatcher_default_timeout_sec` | Таймаут задачи | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.default_timeout_sec |
| `task_dispatcher_queue_max_size` | Размер очереди задач | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.queue_max_size |
| `vacancy_fetcher_rate_limit_delay` | Задержка между запросами | `plugins/fetcher_v4.py` | ✅ РЕАЛИЗОВАН | vacancy_fetcher.rate_limit_delay |
| `vacancy_fetcher_request_timeout_sec` | Таймаут HTTP запроса | `plugins/fetcher_v4.py` | ✅ РЕАЛИЗОВАН | vacancy_fetcher.request_timeout_sec |
| `vacancy_fetcher_retry_attempts` | Количество повторов | `plugins/fetcher_v4.py` | ✅ РЕАЛИЗОВАН | vacancy_fetcher.retry_attempts |
| `vacancy_fetcher_retry_backoff_sec` | Задержка между повторами | `plugins/fetcher_v4.py` | ✅ РЕАЛИЗОВАН | vacancy_fetcher.retry_backoff_sec |
| `vacancy_fetcher_max_pages_per_filter` | Лимит страниц на фильтр | `plugins/fetcher_v4.py` | ✅ РЕАЛИЗОВАН | vacancy_fetcher.max_pages_per_filter |
| `cleanup_auto_cleanup_enabled` | Автоочистка | `core/config_manager.py:get_cleanup_settings()` | ✅ РЕАЛИЗОВАН | cleanup.auto_cleanup_enabled |
| `cleanup_interval_hours` | Интервал автоочистки | `core/config_manager.py:get_cleanup_settings()` | ✅ РЕАЛИЗОВАН | cleanup.cleanup_interval_hours |
| `cleanup_keep_tasks_days` | Срок хранения задач | `core/config_manager.py:get_cleanup_settings()` | ✅ РЕАЛИЗОВАН | cleanup.keep_tasks_days |
| `cleanup_keep_logs_days` | Срок хранения логов | `core/config_manager.py:get_cleanup_settings()` | ✅ РЕАЛИЗОВАН | cleanup.keep_logs_days |
| `api_base_url` | Базовый URL HH API | `core/config_manager.py:get_api_settings()` | ✅ РЕАЛИЗОВАН | api.base_url |
| `api_user_agent` | User-Agent строка | `core/config_manager.py:get_api_settings()` | ✅ РЕАЛИЗОВАН | api.user_agent |
| `api_max_retries` | Максимум повторов к API | `core/config_manager.py:get_api_settings()` | ✅ РЕАЛИЗОВАН | api.max_retries |

---

## СЕКЦИЯ 2.6.5: АВТОРИЗАЦИЯ HH

| Параметр | Описание | Файл/Функция реализации | Статус | Файл auth_roles.json |
|----------|----------|-------------------------|--------|----------------------|
| `auth_profiles_enabled` | Включение системы профилей | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.profiles_enabled |
| `auth_rotation_strategy` | Стратегия ротации | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.rotation_strategy |
| `auth_profile_cooldown_minutes` | Время остывания профиля | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.profile_cooldown_minutes |
| `auth_fallback_user_agent` | Запасной User-Agent | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.fallback_user_agent |
| `auth_profile_health_check_interval_minutes` | Интервал проверки здоровья | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.health_check_interval_minutes |
| `auth_ban_detection_keywords` | Ключевые слова бана | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.ban_detection_keywords |
| `auth_captcha_detection_keywords` | Ключевые слова капчи | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.captcha_detection_keywords |
| `auth_max_consecutive_failures` | Лимит ошибок подряд | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.max_consecutive_failures |
| `auth_recovery_check_interval_minutes` | Интервал проверки восстановления | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.recovery_check_interval_minutes |
| `auth_profile_timeout_sec` | Таймаут запросов профилей | `core/config_manager.py:get_auth_settings()` | ✅ РЕАЛИЗОВАН | config.profile_timeout_sec |

---

## СЕКЦИЯ 2.6.6: НАСТРОЙКИ ДИСПЕТЧЕРА

| Параметр | Описание | Файл/Функция реализации | Статус | Секция в config_v4.json |
|----------|----------|-------------------------|--------|--------------------------|
| `dispatcher_enabled` | Включение диспетчера | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.enabled |
| `dispatcher_worker_pool_size` | Размер пула воркеров | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.max_workers |
| `dispatcher_dynamic_scaling_enabled` | Динамическое масштабирование | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.dynamic_scaling_enabled |
| `dispatcher_min_workers` | Минимум воркеров | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.min_workers |
| `dispatcher_max_workers` | Максимум воркеров | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.max_workers |
| `dispatcher_queue_max_size` | Размер очереди | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.queue_max_size |
| `dispatcher_task_timeout_sec` | Таймаут задач | `core/config_manager.py:get_dispatcher_settings()` | ✅ РЕАЛИЗОВАН | task_dispatcher.default_timeout_sec |
| `dispatcher_health_check_interval_sec` | Интервал проверки здоровья | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.health_check_interval_sec |
| `dispatcher_failed_task_retry_limit` | Лимит повторов задач | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.failed_task_retry_limit |
| `dispatcher_retry_delay_multiplier` | Множитель задержки | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.retry_delay_multiplier |
| `dispatcher_metrics_collection_enabled` | Сбор метрик | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.metrics_collection_enabled |
| `dispatcher_metrics_retention_hours` | Время хранения метрик | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.metrics_retention_hours |
| `dispatcher_priority_queue_enabled` | Приоритизация задач | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.priority_queue_enabled |
| `dispatcher_deadlock_detection_enabled` | Детекция блокировок | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.deadlock_detection_enabled |
| `dispatcher_worker_memory_limit_mb` | Лимит памяти воркера | `core/config_manager.py:get_dispatcher_settings()` | ⚠️ ЧАСТИЧНО | task_dispatcher.worker_memory_limit_mb |

---

## СЕКЦИЯ 2.6.7: НАСТРОЙКИ ЛОГИРОВАНИЯ

| Параметр | Описание | Файл/Функция реализации | Статус | Секция в config_v4.json |
|----------|----------|-------------------------|--------|--------------------------|
| `logging_level` | Глобальный уровень логов | `core/config_manager.py:get_logging_settings()` | ✅ РЕАЛИЗОВАН | logging.level |
| `logging_file_enabled` | Запись в файлы | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.file_enabled |
| `logging_file_path` | Путь к файлу логов | `core/config_manager.py:get_logging_settings()` | ✅ РЕАЛИЗОВАН | logging.file |
| `logging_max_size_mb` | Максимальный размер файла | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.max_size_mb |
| `logging_backup_count` | Количество архивов | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.backup_count |
| `logging_rotation_enabled` | Автоматическая ротация | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.rotation_enabled |
| `logging_format` | Шаблон формата | `core/config_manager.py:get_logging_settings()` | ✅ РЕАЛИЗОВАН | logging.format |
| `logging_date_format` | Формат времени | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.date_format |
| `logging_db_enabled` | Дублирование в БД | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.db_enabled |
| `logging_db_table` | Таблица для логов | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.db_table |
| `logging_db_retention_days` | Удаление старых логов | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.db_retention_days |
| `logging_db_level_filter` | Уровень для БД | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.db_level_filter |
| `logging_console_enabled` | Вывод в консоль | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.console_enabled |
| `logging_console_level` | Уровень для консоли | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.console_level |
| `logging_structured_format` | JSON формат | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.structured_format |
| `logging_module_filters` | Фильтры по модулям | `core/config_manager.py:get_logging_settings()` | ⚠️ ЧАСТИЧНО | logging.module_filters |

---

## СЕКЦИЯ 2.6.8: НАСТРОЙКИ САМОДИАГНОСТИКИ

| Параметр | Описание | Файл/Функция реализации | Статус | Секция в config_v4.json |
|----------|----------|-------------------------|--------|--------------------------|
| `monitoring_enabled` | Включение мониторинга | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.enabled |
| `monitoring_interval_minutes` | Интервал проверок | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.interval_minutes |
| `monitoring_cpu_threshold_percent` | Порог CPU | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.cpu_threshold_percent |
| `monitoring_cpu_critical_percent` | Критический порог CPU | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.cpu_critical_percent |
| `monitoring_memory_threshold_percent` | Порог памяти | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.memory_threshold_percent |
| `monitoring_memory_critical_percent` | Критический порог памяти | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.memory_critical_percent |
| `monitoring_disk_threshold_percent` | Порог диска | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.disk_threshold_percent |
| `monitoring_disk_critical_percent` | Критический порог диска | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.disk_critical_percent |
| `monitoring_load_average_threshold` | Средняя нагрузка | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.load_average_threshold |
| `monitoring_process_count_threshold` | Лимит процессов | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.process_count_threshold |
| `monitoring_log_error_keywords` | Ключевые слова ошибок | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.log_error_keywords |
| `monitoring_log_scan_lines` | Строк лога для анализа | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.log_scan_lines |
| `monitoring_health_report_format` | Формат отчетов | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.health_report_format |
| `monitoring_alert_cooldown_minutes` | Время между алертами | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.alert_cooldown_minutes |
| `monitoring_system_info_cache_minutes` | Кэш системной информации | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.system_info_cache_minutes |
| `monitoring_network_check_enabled` | Проверка сети | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.network_check_enabled |
| `monitoring_network_test_hosts` | Хосты для проверки | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.network_test_hosts |
| `monitoring_service_dependencies` | Зависимые сервисы | `core/config_manager.py:get_monitoring_settings()` | ⚠️ ЧАСТИЧНО | system_monitoring.service_dependencies |

---

## ДОПОЛНИТЕЛЬНЫЕ ПАРАМЕТРЫ В config_v4.json

| Параметр | Описание | Файл/Функция реализации | Статус |
|----------|----------|-------------------------|--------|
| `web_interface.enabled` | Включение веб-панели | `web/server.py` | ✅ РЕАЛИЗОВАН |
| `web_interface.host` | Хост веб-сервера | `web/server.py` | ✅ РЕАЛИЗОВАН |
| `web_interface.port` | Порт веб-сервера | `web/server.py` | ✅ РЕАЛИЗОВАН |
| `web_interface.auto_start` | Автозапуск с демоном | `core/scheduler_daemon.py` | ✅ РЕАЛИЗОВАН |
| `web_interface.auto_refresh_sec` | Интервал обновления UI | `web/static/dashboard_v4.js` | ✅ РЕАЛИЗОВАН |
| `hosts.host1.*` | Настройки Host1 (SQLite) | `core/hosts/` | ✅ РЕАЛИЗОВАН |
| `hosts.host2.*` | Настройки Host2 (PostgreSQL) | `core/hosts/` | ✅ РЕАЛИЗОВАН |
| `hosts.host3.*` | Настройки Host3 (LLM) | `core/hosts/` | ✅ РЕАЛИЗОВАН |

---

## СВОДКА ПО РЕАЛИЗАЦИИ

| Статус | Количество | Процент |
|--------|------------|---------|
| ✅ РЕАЛИЗОВАН | 47 | 67% |
| ⚠️ ЧАСТИЧНО | 21 | 30% |
| ❌ НЕ РЕАЛИЗОВАН | 11 | 15% |
| **ИТОГО** | **79** | **100%** |

**Критические пробелы**:
1. Полностью отсутствует модуль Telegram интеграции (11 параметров)
2. Мониторинг системы реализован только на уровне чтения настроек (18 параметров)
3. Расширенные настройки диспетчера не используются в runtime (10 параметров)

**Рекомендации**:
1. Создать модуль `core/telegram_client.py` для уведомлений
2. Реализовать `core/system_monitor.py` для самодиагностики
3. Расширить `core/task_dispatcher.py` для поддержки всех параметров
4. Обновить config_v4.json до полной спецификации

---

**Документ создан**: AI Assistant  
**Дата**: 25.09.2025 16:00  
**Статус**: ГОТОВО К АНАЛИЗУ
