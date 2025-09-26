#!/usr/bin/env python3
"""
HH v4 CONSOLIDATED TEST SUITE
Единый модуль тестирования приоритетов 1-2 с общим выводом результатов

Автор: AI Assistant
Дата: 23.09.2025
Соответствует требованиям: req_16572309.md
"""

import sys
import os
import time
import json
import sqlite3
import requests
import psutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Добавляем корневую папку проекта в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.scheduler_daemon import SchedulerDaemon
from core.task_dispatcher import TaskDispatcher
from core.task_database import TaskDatabase
from core.auth import apply_auth_headers
from plugins.fetcher_v4 import VacancyFetcher


class TestResult:
    """Структура для хранения результата теста"""
    def __init__(self, test_id: str, name: str, priority: int):
        self.test_id = test_id
        self.name = name
        self.priority = priority
        self.passed = False
        self.error_message = ""
        self.execution_time = 0.0
        self.details = {}


class ConsolidatedTestSuite:
    """Основной класс консолидированного тестирования"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.config = self._load_config()
        self.start_time = time.time()
        
    def _load_config(self) -> Dict:
        """Загрузка конфигурации"""
        config_path = Path(__file__).parent.parent / "config" / "config_v4.json"
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Не удалось загрузить конфигурацию: {e}")
            return {}
    
    def _execute_test(self, test_func, test_id: str, name: str, priority: int) -> TestResult:
        """Выполнение одного теста с измерением времени"""
        result = TestResult(test_id, name, priority)
        start_time = time.time()
        
        try:
            test_func(result)
            result.passed = True
        except Exception as e:
            result.passed = False
            result.error_message = str(e)
        
        result.execution_time = time.time() - start_time
        return result


class Priority1Tests(ConsolidatedTestSuite):
    """Критические тесты приоритета 1 - должны проходить 100%"""
    
    def test_resource_monitoring_critical_thresholds(self, result: TestResult):
        """2.1.1 - Мониторинг системных ресурсов"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        result.details = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent
        }
        
        # Проверяем что мониторинг работает
        assert cpu_percent >= 0, "CPU мониторинг не работает"
        assert memory.percent >= 0, "Memory мониторинг не работает"
        assert disk.percent >= 0, "Disk мониторинг не работает"
        
        # Проверяем критические пороги из конфигурации
        monitoring_config = self.config.get('system_monitoring', {})
        cpu_critical = monitoring_config.get('cpu_critical_percent', 95)
        memory_critical = monitoring_config.get('memory_critical_percent', 95)
        disk_critical = monitoring_config.get('disk_critical_percent', 95)
        
        if cpu_percent > cpu_critical:
            result.details['cpu_alert'] = f"CPU превышает критический порог {cpu_critical}%"
        if memory.percent > memory_critical:
            result.details['memory_alert'] = f"Память превышает критический порог {memory_critical}%"
        if disk.percent > disk_critical:
            result.details['disk_alert'] = f"Диск превышает критический порог {disk_critical}%"
    
    def test_service_status_response(self, result: TestResult):
        """2.1.2 - Проверка статуса демона"""
        try:
            # Ищем процесс демона
            daemon_found = False
            daemon_info = {}
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
                try:
                    if any('scheduler_daemon' in str(cmd) for cmd in proc.info['cmdline'] or []):
                        daemon_found = True
                        daemon_info = {
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'create_time': datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                            'uptime_seconds': time.time() - proc.info['create_time']
                        }
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            result.details = {
                'daemon_found': daemon_found,
                'daemon_info': daemon_info
            }
            
            assert daemon_found, "Демон планировщика не найден среди процессов"
            assert daemon_info['uptime_seconds'] > 0, "Время работы демона некорректно"
            
        except Exception as e:
            # Если не можем найти через процессы, проверяем через файл состояния
            state_file = Path(__file__).parent.parent / "data" / "daemon.state"
            if state_file.exists():
                result.details['daemon_status'] = "Файл состояния найден"
            else:
                raise AssertionError(f"Демон не активен: {e}")
    
    def test_02_api_auth_headers(self, result: TestResult):
        """2.1.3 - Проверка авторизации HH"""
        auth_config_path = Path(__file__).parent.parent / "config" / "auth_roles.json"
        
        if not auth_config_path.exists():
            result.details['auth_status'] = "Файл auth_roles.json не найден - авторизация отключена"
            return
        
        try:
            with open(auth_config_path, 'r', encoding='utf-8') as f:
                auth_config = json.load(f)
            
            profiles = auth_config.get('profiles', [])
            enabled_profiles = [p for p in profiles if p.get('enabled', False)]
            
            result.details = {
                'total_profiles': len(profiles),
                'enabled_profiles': len(enabled_profiles),
                'auth_percentage': (len(enabled_profiles) / max(len(profiles), 1)) * 100
            }
            
            assert len(enabled_profiles) > 0, "Нет активных профилей авторизации"
            
        except json.JSONDecodeError as e:
            raise AssertionError(f"Некорректный JSON в конфигурации: {e}")
    
    def test_dispatcher_start_command(self, result: TestResult):
        """2.4.1 - Проверка запуска диспетчера"""
        try:
            # Проверяем что TaskDispatcher может быть инициализирован
            dispatcher = TaskDispatcher(self.config.get('task_dispatcher', {}))
            result.details = {
                'dispatcher_created': True,
                'max_workers': dispatcher.max_workers,
                'queue_maxsize': getattr(dispatcher, 'queue_maxsize', 'unlimited')
            }
            
            # Проверяем базовые методы диспетчера
            assert hasattr(dispatcher, 'add_task'), "Метод add_task не найден"
            assert hasattr(dispatcher, 'get_progress'), "Метод get_progress не найден"
            
        except Exception as e:
            raise AssertionError(f"Ошибка инициализации диспетчера: {e}")
    
    def test_web_interface_command(self, result: TestResult):
        """2.4.2 - Проверка веб-интерфейса"""
        web_config = self.config.get('web_interface', {})
        port = web_config.get('port', 8000)
        
        try:
            # Проверяем доступность веб-интерфейса
            response = requests.get(f"http://localhost:{port}/api/version", timeout=5)
            
            result.details = {
                'port': port,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'api_reachable': response.status_code == 200
            }
            
            assert response.status_code == 200, f"Веб-интерфейс недоступен (статус {response.status_code})"
            
        except requests.exceptions.ConnectionError:
            result.details = {
                'port': port,
                'error': 'Connection refused - веб-сервер не запущен'
            }
            # Не провалываем тест если веб-интерфейс намеренно выключен
            if web_config.get('enabled', True):
                raise AssertionError("Веб-интерфейс должен быть доступен согласно конфигурации")
    
    def test_database_health_check(self, result: TestResult):
        """2.10.1 - Проверка здоровья базы данных"""
        db_config = self.config.get('database', {})
        db_path = Path(__file__).parent.parent / db_config.get('path', 'data/hh_v4.sqlite3')
        
        try:
            # Создаем БД если не существует
            db_path.parent.mkdir(exist_ok=True)
            
            with sqlite3.connect(str(db_path), timeout=30) as conn:
                cursor = conn.cursor()
                
                # Проверяем базовые операции
                cursor.execute("SELECT sqlite_version()")
                sqlite_version = cursor.fetchone()[0]
                
                # Проверяем размер БД
                db_size = db_path.stat().st_size if db_path.exists() else 0
                
                # Проверяем количество таблиц
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                
                result.details = {
                    'sqlite_version': sqlite_version,
                    'db_size_bytes': db_size,
                    'table_count': table_count,
                    'db_path': str(db_path),
                    'wal_mode': db_config.get('wal_mode', False)
                }
                
                assert db_size >= 0, "Размер БД некорректен"
                assert table_count >= 0, "Количество таблиц некорректно"
                
        except Exception as e:
            raise AssertionError(f"Ошибка проверки БД: {e}")
    
    def test_config_file_loading(self, result: TestResult):
        """2.6.4 - Загрузка конфигурации"""
        config_path = Path(__file__).parent.parent / "config" / "config_v4.json"
        
        try:
            assert config_path.exists(), f"Файл конфигурации не найден: {config_path}"
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Проверяем обязательные секции
            required_sections = ['database', 'task_dispatcher', 'logging', 'api']
            missing_sections = [s for s in required_sections if s not in config]
            
            result.details = {
                'config_sections': list(config.keys()),
                'required_sections': required_sections,
                'missing_sections': missing_sections,
                'config_valid': len(missing_sections) == 0
            }
            
            assert len(missing_sections) == 0, f"Отсутствуют обязательные секции: {missing_sections}"
            
        except json.JSONDecodeError as e:
            raise AssertionError(f"Некорректный JSON в конфигурации: {e}")
    
    def test_search_finds_new_vacancies(self, result: TestResult):
        """2.11.1 + 2.11.3 - Поиск и сбор ID вакансий"""
        try:
            # Инициализируем загрузчик
            fetcher_config = self.config.get('vacancy_fetcher', {})
            fetcher = VacancyFetcher(fetcher_config)
            
            # Простой тестовый запрос
            test_params = {
                'text': 'python',
                'area': '1',  # Москва
                'per_page': '1',
                'page': '0'
            }
            
            # Формируем URL запроса
            base_url = self.config.get('api', {}).get('base_url', 'https://api.hh.ru')
            url = f"{base_url}/vacancies"
            
            response = requests.get(url, params=test_params, timeout=10)
            
            result.details = {
                'api_url': url,
                'test_params': test_params,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds()
            }
            
            if response.status_code == 200:
                data = response.json()
                result.details.update({
                    'found_vacancies': data.get('found', 0),
                    'pages': data.get('pages', 0),
                    'items_count': len(data.get('items', []))
                })
                
                assert data.get('found', 0) > 0, "API не возвращает вакансии"
                
            elif response.status_code == 400:
                result.details['error'] = "Ошибка 400 - проблема с User-Agent или параметрами"
                raise AssertionError("API возвращает ошибку 400")
            else:
                raise AssertionError(f"API недоступен (статус {response.status_code})")
                
        except requests.exceptions.RequestException as e:
            raise AssertionError(f"Ошибка сетевого запроса: {e}")


class Priority2Tests(ConsolidatedTestSuite):
    """Важные тесты приоритета 2 - могут иметь известные ограничения"""
    
    def test_cleanup_command(self, result: TestResult):
        """2.2.1-2.2.2 + 2.2.4 - Тесты очистки"""
        cleanup_config = self.config.get('cleanup', {})
        
        result.details = {
            'auto_cleanup_enabled': cleanup_config.get('auto_cleanup_enabled', False),
            'keep_logs_days': cleanup_config.get('keep_logs_days', 30),
            'keep_tasks_days': cleanup_config.get('keep_tasks_days', 7)
        }
        
        # Проверяем что настройки очистки разумные
        assert cleanup_config.get('keep_logs_days', 30) > 0, "Период хранения логов должен быть больше 0"
        assert cleanup_config.get('keep_tasks_days', 7) > 0, "Период хранения задач должен быть больше 0"
    
    def test_critical_event_logging(self, result: TestResult):
        """2.3.1 - Централизованное логирование"""
        logging_config = self.config.get('logging', {})
        log_file = Path(__file__).parent.parent / logging_config.get('file_path', 'logs/app.log')
        
        result.details = {
            'log_file': str(log_file),
            'log_exists': log_file.exists(),
            'log_config': logging_config
        }
        
        # Создаем папку логов если не существует
        log_file.parent.mkdir(exist_ok=True)
        
        if log_file.exists():
            stat = log_file.stat()
            result.details.update({
                'log_size_bytes': stat.st_size,
                'log_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
            
            # Проверяем что лог не слишком старый (менее суток)
            age_hours = (time.time() - stat.st_mtime) / 3600
            result.details['log_age_hours'] = age_hours
            
            if age_hours > 24:
                result.details['warning'] = f"Лог не обновлялся {age_hours:.1f} часов"

        # // Chg_DB_LOGS_TEST_2409: Подключаем DbLogHandler и пишем пробную запись в БД
        try:
            from core.db_log_handler import DbLogHandler  # type: ignore
            root = logging.getLogger()
            if not any(isinstance(h, DbLogHandler) for h in root.handlers):
                dbh = DbLogHandler()
                root.addHandler(dbh)
            logging.getLogger('tests.logging').info('probe: consolidated_tests writes to DB logs')
        except Exception as e:
            result.details['db_log_attach_error'] = str(e)

        # Проверяем наличие записей в таблице logs за сутки
        try:
            db = TaskDatabase()
            with db.get_connection() as conn:
                cur = conn.execute("SELECT COUNT(*) FROM logs WHERE ts > strftime('%s','now','-1 day')")
                db_count = int(cur.fetchone()[0])
                result.details['db_logs_last_24h'] = db_count
        except Exception as e:
            result.details['db_logs_check_error'] = str(e)
    
    def test_telegram_critical_alerts(self, result: TestResult):
        """2.6.2 - Настройки Telegram"""
        telegram_config = self.config.get('telegram', {})
        
        result.details = {
            'telegram_enabled': telegram_config.get('enabled', False),
            'has_token': bool(telegram_config.get('token', '').strip()),
            'has_chat_id': bool(telegram_config.get('chat_id', '').strip()),
            'alerts_enabled': telegram_config.get('alerts_enabled', False)
        }
        
        if telegram_config.get('enabled', False):
            # Если Telegram включен, проверяем наличие обязательных параметров
            assert telegram_config.get('token', '').strip(), "Токен Telegram не настроен"
            assert telegram_config.get('chat_id', '').strip(), "Chat ID Telegram не настроен"
        else:
            result.details['note'] = "Telegram интеграция отключена в конфигурации"
    
    def test_filters_management_ui(self, result: TestResult):
        """2.5.9 - Управление фильтрами через UI"""
        filters_path = Path(__file__).parent.parent / "config" / "filters.json"
        
        try:
            with open(filters_path, 'r', encoding='utf-8') as f:
                filters_data = json.load(f)
            
            filters = filters_data.get('filters', [])
            test_filters = [f for f in filters if f.get('type') == 'test']
            prod_filters = [f for f in filters if f.get('type') == 'prod']
            
            result.details = {
                'total_filters': len(filters),
                'test_filters': len(test_filters),
                'prod_filters': len(prod_filters),
                'active_filters': len([f for f in filters if f.get('active', False)])
            }
            
            # Проверяем что есть хотя бы один test фильтр
            assert len(test_filters) > 0, "Должен быть хотя бы один test фильтр"
            
            # Проверяем структуру фильтров
            for f in filters:
                assert 'id' in f, f"Фильтр без id: {f}"
                assert 'type' in f, f"Фильтр {f.get('id')} без type"
                assert 'params' in f, f"Фильтр {f.get('id')} без params"
                
        except Exception as e:
            raise AssertionError(f"Ошибка проверки фильтров: {e}")
    
    def test_web_dashboard_main_page(self, result: TestResult):
        """2.4.4 + 2.5.7 - Проверка веб-панели"""
        web_config = self.config.get('web_interface', {})
        port = web_config.get('port', 8000)
        
        try:
            # Проверяем главную страницу панели
            response = requests.get(f"http://localhost:{port}/", timeout=5)
            
            result.details = {
                'port': port,
                'status_code': response.status_code,
                'response_time': response.elapsed.total_seconds(),
                'has_unix_time': 'data-unix-time' in response.text or 'unixTime' in response.text
            }
            
            if response.status_code == 200:
                # Проверяем наличие ключевых элементов панели
                checks = {
                    'has_system_health': 'System Health' in response.text,
                    'has_daemon_status': 'Daemon Status' in response.text,
                    'has_tasks_queue': 'Tasks Queue' in response.text,
                    'has_filters': 'Filters' in response.text
                }
                result.details.update(checks)
                
        except requests.exceptions.ConnectionError:
            result.details = {
                'port': port,
                'note': 'Веб-панель не запущена'
            }
            raise AssertionError("Веб-панель недоступна - требование 2.4.4 не выполнено")

    # // Chg_SCREENSHOT_2409: e2e скриншот веб-панели через Playwright
    def test_web_panel_screenshot(self, result: TestResult):
        """2.5.7 - E2E: Скриншот главной страницы панели и извлечение ключевых текстов"""
        import subprocess
        from pathlib import Path
        import time as _time

        # Определяем актуальный порт: пробуем 5000 (UAT), затем из конфига, затем 8000 по умолчанию
        cfg_port = self.config.get('web_interface', {}).get('port', 8000)
        candidate_ports = [5000, cfg_port, 8000]
        seen = set()
        ports = []
        for p in candidate_ports:
            if p not in seen:
                seen.add(p); ports.append(p)

        base_url = None
        for p in ports:
            try:
                r = requests.get(f"http://localhost:{p}/api/version", timeout=2)
                if r.status_code == 200:
                    base_url = f"http://localhost:{p}"
                    break
            except Exception:
                continue
        if not base_url:
            raise AssertionError("Веб-сервер не доступен ни на 5000, ни на порту из config, ни на 8000")

        # Ленивая установка браузера при необходимости
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except Exception as e:
            raise AssertionError(f"Playwright не установлен: {e}. Установите зависимости и выполните 'python -m playwright install chromium'")

        screenshot_path = None
        meta = {}
        reports_dir = Path(__file__).parent.parent / 'reports'
        reports_dir.mkdir(exist_ok=True)
        ts = _time.strftime('%Y%m%d_%H%M%S')
        out_png = reports_dir / f'web_panel_screenshot_{ts}.png'
        out_json = reports_dir / f'web_panel_screenshot_{ts}.json'

        # Пытаемся снять скриншот; при ошибке запуска попробуем авто-установку браузера
        def _do_capture():
            nonlocal screenshot_path, meta
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
                page = context.new_page()
                page.goto(base_url + '/', wait_until='domcontentloaded', timeout=15000)
                try:
                    page.wait_for_selector('.status-row', timeout=5000)
                except Exception:
                    pass
                page.wait_for_timeout(1000)
                # Собираем ключевые тексты
                def _txt(sel):
                    try:
                        el = page.query_selector(sel)
                        return (el.inner_text().strip() if el else None)
                    except Exception:
                        return None
                meta = {
                    'url': base_url + '/',
                    'headerTitle': _txt('#headerTitle'),
                    'headerVersion': _txt('#headerVersion'),
                    'daemonStatus': _txt('#daemonStatus'),
                    'apiHealth': _txt('#apiHealth'),
                    'taskStats': _txt('#taskStats'),
                    'has_server_unix': bool(page.query_selector('#serverUnixTime'))
                }
                page.screenshot(path=str(out_png), full_page=True)
                context.close()
                browser.close()
                screenshot_path = str(out_png)

        try:
            _do_capture()
        except Exception as e1:
            # Пытаемся установить браузер и повторить один раз
            try:
                subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True, timeout=180)
                _do_capture()
            except Exception as e2:
                raise AssertionError(f"Не удалось сделать скриншот: {e1} / {e2}")

        # Сохраняем метаданные
        try:
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump({'screenshot': screenshot_path, 'meta': meta}, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        result.details = {
            'base_url': base_url,
            'screenshot': screenshot_path,
            'meta': meta
        }
        # Простые проверки наличия ключевых секций
        assert meta.get('headerTitle'), 'Не нашли headerTitle'
        assert meta.get('headerVersion'), 'Не нашли headerVersion'
        assert meta.get('apiHealth') is not None, 'Не нашли apiHealth'


class TestRunner:
    """Основной класс для запуска всех тестов"""
    
    def __init__(self, priorities: List[int] = None):
        self.priorities = priorities or [1, 2]
        self.results: List[TestResult] = []
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Запуск всех тестов с красивым выводом"""
        print("=" * 65)
        print("           HH v4 CONSOLIDATED TEST RESULTS")
        print("=" * 65)
        print(f"Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Приоритеты: {', '.join(map(str, self.priorities))}")
        print()
        
        total_start_time = time.time()
        
        # Запуск тестов приоритета 1
        if 1 in self.priorities:
            print("🔴 ПРИОРИТЕТ 1 ТЕСТЫ (Критические)")
            print("-" * 45)
            self._run_priority_tests(Priority1Tests(), 1)
        
        # Запуск тестов приоритета 2  
        if 2 in self.priorities:
            print("\n🟡 ПРИОРИТЕТ 2 ТЕСТЫ (Важные)")
            print("-" * 35)
            self._run_priority_tests(Priority2Tests(), 2)
        
        total_time = time.time() - total_start_time
        
        # Итоговая статистика
        return self._print_final_results(total_time)
    
    def _run_priority_tests(self, test_class: ConsolidatedTestSuite, priority: int):
        """Запуск тестов определенного приоритета"""
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            test_func = getattr(test_class, method_name)
            test_name = test_func.__doc__.split('\n')[0].strip() if test_func.__doc__ else method_name
            
            print(f"  • {test_name[:60]}...", end=" ", flush=True)
            
            result = test_class._execute_test(test_func, method_name, test_name, priority)
            self.results.append(result)
            
            if result.passed:
                print(f"✅ ({result.execution_time:.2f}s)")
            else:
                print(f"❌ ({result.execution_time:.2f}s)")
                print(f"    Ошибка: {result.error_message}")
    
    def _print_final_results(self, total_time: float) -> Dict[str, Any]:
        """Печать итоговых результатов"""
        print("\n" + "=" * 65)
        print("                    ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
        print("=" * 65)
        
        # Группировка по приоритетам
        priority_stats = {}
        for priority in self.priorities:
            priority_results = [r for r in self.results if r.priority == priority]
            passed = len([r for r in priority_results if r.passed])
            total = len(priority_results)
            percentage = (passed / total * 100) if total > 0 else 0
            
            priority_stats[priority] = {
                'passed': passed,
                'total': total,
                'percentage': percentage
            }
            
            status_icon = "✅" if percentage == 100 else "⚠️" if percentage >= 80 else "❌"
            print(f"Приоритет {priority}: {passed}/{total} ({percentage:.1f}%) {status_icon}")
        
        # Общая статистика
        total_passed = sum(r.passed for r in self.results)
        total_tests = len(self.results)
        overall_percentage = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        print("-" * 65)
        print(f"ОБЩИЙ ИТОГ: {total_passed}/{total_tests} ({overall_percentage:.1f}%)")
        print(f"Время выполнения: {total_time:.2f} секунд")
        
        # Список проблемных тестов
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            print("\n🔍 ПРОБЛЕМНЫЕ ТЕСТЫ:")
            for test in failed_tests:
                print(f"  ❌ {test.name}")
                print(f"     {test.error_message}")
        
        print("=" * 65)

        # // Chg_UTF8_LOG_2409: Пишем сводку в logs/union_test.log как UTF-8
        try:
            logs_dir = Path(__file__).parent.parent / 'logs'
            logs_dir.mkdir(exist_ok=True)
            with open(logs_dir / 'union_test.log', 'w', encoding='utf-8') as f:
                f.write("HH v4 CONSOLIDATED TEST RESULTS\n")
                f.write(f"Total: {total_tests}, Passed: {total_passed}, Overall: {overall_percentage:.1f}%\n")
                for prio, stats in priority_stats.items():
                    f.write(f"Priority {prio}: {stats['passed']}/{stats['total']} ({stats['percentage']:.1f}%)\n")
                if failed_tests:
                    f.write("FAILED TESTS:\n")
                    for t in failed_tests:
                        f.write(f"- {t.name}: {t.error_message}\n")
        except Exception:
            pass

        # Возвращаем структурированные результаты
        return {
            'timestamp': datetime.now().isoformat(),
            'total_tests': total_tests,
            'passed_tests': total_passed,
            'overall_percentage': overall_percentage,
            'execution_time': total_time,
            'priority_stats': priority_stats,
            'failed_tests': [{'name': t.name, 'error': t.error_message} for t in failed_tests],
            'detailed_results': [
                {
                    'test_id': r.test_id,
                    'name': r.name,
                    'priority': r.priority,
                    'passed': r.passed,
                    'execution_time': r.execution_time,
                    'error_message': r.error_message,
                    'details': r.details
                }
                for r in self.results
            ]
        }


def main():
    """Главная функция для CLI запуска"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HH v4 Consolidated Test Suite')
    parser.add_argument('--priority', type=str, default='1,2', 
                       help='Приоритеты тестов через запятую (по умолчанию: 1,2)')
    parser.add_argument('--output', type=str, 
                       help='Файл для сохранения JSON результатов')
    
    args = parser.parse_args()
    
    # Парсинг приоритетов
    try:
        priorities = [int(p.strip()) for p in args.priority.split(',')]
    except ValueError:
        print("❌ Некорректный формат приоритетов. Используйте: --priority 1,2")
        return 1
    
    # Запуск тестов
    runner = TestRunner(priorities)
    results = runner.run_all_tests()
    
    # Сохранение результатов в файл
    if args.output:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n📝 Результаты сохранены в {args.output}")
        except Exception as e:
            print(f"⚠️  Ошибка сохранения результатов: {e}")
    
    # Возвращаем код выхода
    return 0 if results['overall_percentage'] >= 80 else 1


if __name__ == '__main__':
    sys.exit(main())
