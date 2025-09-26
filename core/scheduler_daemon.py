#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демон-планировщик для HH-бота v4
Реализация требований 2.7 (Диспетчер задач) и 3.2 (Основной процесс)

// Chg_SCHEDULER_DAEMON_2009: Автоматический диспетчер задач с планировщиком
"""

import asyncio
import logging
import time
import json
import signal
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum
import threading

# Импорт компонентов системы
from .task_dispatcher import TaskDispatcher
from .task_database import TaskDatabase
from plugins.fetcher_v4 import VacancyFetcher, estimate_total_pages
from logging.handlers import RotatingFileHandler
from core.config_manager import get_config_manager


class TaskType(Enum):
    """Типы задач планировщика"""
    FETCH_VACANCIES = "fetch_vacancies"
    FETCH_EMPLOYERS = "fetch_employers" 
    CLEANUP_DATA = "cleanup_data"
    SYNC_HOST2 = "sync_host2"
    ANALYZE_HOST3 = "analyze_host3"
    SYSTEM_HEALTH = "system_health"


class TaskStatus(Enum):
    """Статусы выполнения задач"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Запланированная задача"""
    task_type: TaskType
    name: str
    schedule_pattern: str  # "hourly", "daily", "weekly", "0 */2 * * *" (cron-like)
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    max_failures: int = 3
    timeout_minutes: int = 60
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class TaskExecution:
    """Результат выполнения задачи"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)


class SchedulerDaemon:
    """
    Демон-планировщик для автоматического выполнения задач
    
    Реализует требования:
    - 2.7. Диспетчер задач
    - 3.2. Основной процесс - Хост 1 (Сбор данных)
    """
    
    def __init__(self, config_path: str = "config/config_v4.json"):
        """
        Инициализация планировщика
        
        Args:
            config_path: Путь к конфигурационному файлу
        """
        self.config_path = config_path
        self.config = self._load_config()
        
        # Основные компоненты (v4)
        # // Chg_V4_DB_2109: добавляем v4 БД задач/вакансий для веб-панели и загрузок
        self.db_v4 = TaskDatabase()
        self.dispatcher = TaskDispatcher(config=self.config)
        self.fetcher = VacancyFetcher(
            config=self.config.get('vacancy_fetcher', {}),
            rate_limit_delay=self.config.get('rate_limit_delay', 1.0),
            database=self.db_v4  # сохраняем вакансии в v4 БД
        )
        
        # Состояние демона
        self.running = False
        self.shutdown_requested = False
        
        # Планировщик и задачи
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.active_executions: Dict[str, TaskExecution] = {}
        self.execution_history: List[TaskExecution] = []
        
        # Настройки
        self.check_interval = 60  # Проверять каждую минуту
        self.max_concurrent_tasks = 3
        self.history_limit = 1000
        
        # Логирование
        self.logger = logging.getLogger(__name__)
        
        # Обработчики сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Веб-панель процесс
        self.web_process = None
        
        # Инициализация задач по умолчанию
        self._initialize_default_tasks()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Не удалось загрузить конфигурацию: {e}")
            return {}
    
    def _initialize_default_tasks(self):
        """Инициализация задач по умолчанию согласно требованиям 3.2"""
        
        # 3.2.1. Запуск загрузки вакансий каждый час
        self.add_task(ScheduledTask(
            task_type=TaskType.FETCH_VACANCIES,
            name="Hourly Vacancy Fetch",
            schedule_pattern="hourly",
            enabled=True,
            timeout_minutes=45,
            params={
                "max_pages": 200,
                "filters_source": "config/filters.json",
                "first_run_delay_sec": 0
            }
        ))
        
        # 3.2.8-3.2.11. Загрузка работодателей (после вакансий)
        self.add_task(ScheduledTask(
            task_type=TaskType.FETCH_EMPLOYERS,
            name="Daily Employer Fetch", 
            schedule_pattern="daily",
            enabled=True,
            timeout_minutes=30,
            params={
                "first_run_delay_sec": 15
            }
        ))
        
        # Очистка данных каждые 6 часов
        self.add_task(ScheduledTask(
            task_type=TaskType.CLEANUP_DATA,
            name="System Cleanup",
            schedule_pattern="0 */6 * * *",  # Каждые 6 часов
            enabled=True,
            timeout_minutes=15,
            params={
                "keep_days": 30,
                "vacuum_db": True,
                "first_run_delay_sec": 20
            }
        ))
        
        # // Chg_TASKS_ALWAYS_2009: Всегда добавляем задачи, проверяем включение при выполнении
        # Синхронизация с Host2 (в mock режиме)
        self.add_task(ScheduledTask(
            task_type=TaskType.SYNC_HOST2,
            name="Host2 Sync",
            schedule_pattern="0 */4 * * *",  # Каждые 4 часа
            enabled=True,  # Всегда включено, mock режим безопасен
            timeout_minutes=20,
            params={
                "first_run_delay_sec": 25
            }
        ))
        
        # Анализ через Host3 (в mock режиме)
        self.add_task(ScheduledTask(
            task_type=TaskType.ANALYZE_HOST3,
            name="Host3 Analysis",
            schedule_pattern="daily",
            enabled=True,  # Всегда включено, mock режим безопасен
            timeout_minutes=60,
            params={
                "batch_size": 50,
                "analyze_new_only": True,
                "first_run_delay_sec": 30
            }
        ))
        
        # Проверка состояния системы каждые 5 минут
        self.add_task(ScheduledTask(
            task_type=TaskType.SYSTEM_HEALTH,
            name="System Health Check",
            schedule_pattern="*/5 * * * *",  # Каждые 5 минут
            enabled=True,
            timeout_minutes=2,
            params={
                "first_run_delay_sec": 5
            }
        ))
    
    def add_task(self, task: ScheduledTask):
        """Добавление задачи в планировщик"""
        import uuid
        # Добавляем микросекунды для уникальности
        timestamp = time.time()
        task_id = f"{task.task_type.value}_{int(timestamp)}_{int((timestamp % 1) * 1000000)}_{str(uuid.uuid4())[:8]}"
        self.scheduled_tasks[task_id] = task
        
        # Рассчитываем следующий запуск
        first_delay = None
        try:
            first_delay = int(task.params.get('first_run_delay_sec')) if task.params else None
        except Exception:
            first_delay = None
        if first_delay and first_delay > 0:
            task.next_run = datetime.now() + timedelta(seconds=first_delay)
        else:
            task.next_run = self._calculate_next_run(task.schedule_pattern)
        
        self.logger.info(f"Добавлена задача: {task.name} (запуск: {task.next_run})")
    
    def _calculate_next_run(self, pattern: str) -> datetime:
        """Расчет времени следующего запуска"""
        now = datetime.now()
        
        if pattern == "hourly":
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        elif pattern == "daily":
            return now.replace(hour=2, minute=0, second=0, microsecond=0) + timedelta(days=1)
        elif pattern == "weekly":
            days_ahead = 6 - now.weekday()  # Воскресенье
            if days_ahead <= 0:
                days_ahead += 7
            return now.replace(hour=3, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
        elif pattern.startswith("*/"):
            # Простой парсинг для */N минут
            minutes = int(pattern.split()[0][2:])
            return now + timedelta(minutes=minutes)
        elif pattern.startswith("0 */"):
            # Парсинг для 0 */N часов
            hours = int(pattern.split()[1][2:])
            next_hour = (now.hour // hours + 1) * hours
            return now.replace(hour=next_hour % 24, minute=0, second=0, microsecond=0)
        else:
            # По умолчанию - через час
            return now + timedelta(hours=1)
    
    async def _execute_task(self, task_id: str, task: ScheduledTask) -> TaskExecution:
        """Выполнение конкретной задачи"""
        execution = TaskExecution(
            task_id=task_id,
            task_type=task.task_type,
            status=TaskStatus.RUNNING,
            start_time=datetime.now()
        )
        
        self.active_executions[task_id] = execution
        
        try:
            # // Chg_V4_TASKS_2109: регистрируем задачу в v4 таблице tasks для веб-панели
            try:
                v4_type_map = {
                    TaskType.FETCH_VACANCIES: 'load_vacancies',
                    TaskType.FETCH_EMPLOYERS: 'load_vacancies',  # Используем разрешенный тип
                    TaskType.CLEANUP_DATA: 'cleanup',
                    TaskType.SYNC_HOST2: 'process_pipeline',     # Используем разрешенный тип
                    TaskType.ANALYZE_HOST3: 'process_pipeline',  # Используем разрешенный тип
                    TaskType.SYSTEM_HEALTH: 'test',             # Используем разрешенный тип
                }
                v4_type = v4_type_map.get(task.task_type, task.task_type.value)
                self.db_v4.create_task(
                    task_id=task_id,
                    task_type=v4_type,
                    params=task.params or {},
                    timeout_sec=int(task.timeout_minutes) * 60
                )
                self.db_v4.update_task_status(task_id, 'running')
            except Exception as reg_err:
                self.logger.error(f"Ошибка регистрации v4-задачи {task_id}: {reg_err}")
            self.logger.info(f"Начало выполнения задачи: {task.name}")
            execution.logs.append(f"Задача запущена: {task.name}")
            
            # Выполняем задачу в зависимости от типа
            if task.task_type == TaskType.FETCH_VACANCIES:
                result = await self._execute_fetch_vacancies(task_id, task)
            elif task.task_type == TaskType.FETCH_EMPLOYERS:
                result = await self._execute_fetch_employers(task)
            elif task.task_type == TaskType.CLEANUP_DATA:
                result = await self._execute_cleanup_data(task)
            elif task.task_type == TaskType.SYNC_HOST2:
                result = await self._execute_sync_host2(task)
            elif task.task_type == TaskType.ANALYZE_HOST3:
                result = await self._execute_analyze_host3(task)
            elif task.task_type == TaskType.SYSTEM_HEALTH:
                result = await self._execute_system_health(task)
            else:
                raise Exception(f"Неизвестный тип задачи: {task.task_type}")
            
            # Успешное завершение
            execution.status = TaskStatus.COMPLETED
            execution.result = result
            execution.logs.append("Задача выполнена успешно")
            
            task.last_run = execution.start_time
            task.run_count += 1
            task.failure_count = 0  # Сбрасываем счетчик ошибок
            
            # Обновляем статус v4-задачи
            try:
                self.db_v4.update_task_status(task_id, 'completed', result)
            except Exception:
                pass
            self.logger.info(f"Задача завершена успешно: {task.name}")
            
        except Exception as e:
            # Ошибка выполнения
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
            execution.logs.append(f"Ошибка: {e}")
            
            task.failure_count += 1
            
            self.logger.error(f"Ошибка выполнения задачи {task.name}: {e}")
            # Обновляем статус v4-задачи
            try:
                self.db_v4.update_task_status(task_id, 'failed', {'error': str(e)})
            except Exception:
                pass
            
            # Отключаем задачу при превышении лимита ошибок
            if task.failure_count >= task.max_failures:
                task.enabled = False
                self.logger.warning(f"Задача отключена из-за множественных ошибок: {task.name}")
        
        finally:
            # Завершение выполнения
            execution.end_time = datetime.now()
            execution.duration_seconds = (execution.end_time - execution.start_time).total_seconds()
            
            # Перемещаем из активных в историю
            if task_id in self.active_executions:
                del self.active_executions[task_id]
            
            self.execution_history.append(execution)
            
            # Ограничиваем размер истории
            if len(self.execution_history) > self.history_limit:
                self.execution_history = self.execution_history[-self.history_limit:]
            
            # Рассчитываем следующий запуск
            if task.enabled:
                task.next_run = self._calculate_next_run(task.schedule_pattern)
            else:
                task.next_run = None
        
        return execution
    
    async def _execute_fetch_vacancies(self, task_id: str, task: ScheduledTask) -> Dict[str, Any]:
        """Выполнение загрузки вакансий (3.2.1 - 3.2.7)"""
        
        # 3.2.2. Поиск через API hh.ru всех запросов в filters.json
        filters_path = task.params.get('filters_source', 'config/filters.json')
        max_pages = task.params.get('max_pages', 200)
        
        try:
            with open(filters_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception as e:
            raise Exception(f"Не удалось загрузить фильтры из {filters_path}: {e}")
        
        # Статистика выполнения
        stats = {
            'filters_processed': 0,
            'pages_fetched': 0,
            'vacancies_found': 0,
            'vacancies_new': 0,
            'vacancies_duplicates': 0,
            'employers_found': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # Нормализуем структуру фильтров: dict->list, поддержка ключа "filters"
        if isinstance(raw, dict) and 'filters' in raw:
            items = raw['filters']
        elif isinstance(raw, dict):
            items = list(raw.values())
        else:
            items = raw

        active_filters = [flt for flt in items if flt.get('active', flt.get('enabled', True))]

        # Обрабатываем каждый активный фильтр
        for flt in active_filters:
            filter_id = flt.get('id', 'unknown')
            filter_name = flt.get('name', filter_id)
            flt_params = flt.get('params', flt)
            self.logger.info(f"Обработка фильтра: {filter_name} ({filter_id})")

            try:
                # 3.2.3. Оценка числа страниц
                try:
                    est_pages = estimate_total_pages(flt_params, self.fetcher)
                except Exception:
                    est_pages = 10
                page_end = max(1, min(int(max_pages), int(est_pages)))

                # 3.2.4-3.2.7. Постраничная загрузка и сохранение (через v4 БД)
                chunk_result = await asyncio.to_thread(self.fetcher.fetch_chunk, {
                    'page_start': 0,
                    'page_end': page_end,
                    'filter': flt,
                    'task_id': task_id
                })

                stats['filters_processed'] += 1
                stats['pages_fetched'] += int(chunk_result.get('processed_pages', 0))
                loaded = int(chunk_result.get('loaded_count', 0))
                stats['vacancies_found'] += loaded
                stats['vacancies_new'] += loaded

            except Exception as e:
                self.logger.error(f"Ошибка обработки фильтра {filter_name}: {e}")
                continue
        
        stats['end_time'] = datetime.now().isoformat()
        stats['duration_minutes'] = (datetime.fromisoformat(stats['end_time']) - 
                                   datetime.fromisoformat(stats['start_time'])).total_seconds() / 60
        
        return stats
    
    async def _execute_fetch_employers(self, task: ScheduledTask) -> Dict[str, Any]:
        """Выполнение загрузки работодателей (3.2.8 - 3.2.11)"""
        
        # 3.2.8. Составление списка ID работодателей
        employer_ids = self.db_v4.get_missing_employer_ids()
        
        stats = {
            'employer_ids_found': len(employer_ids),
            'employers_processed': 0,
            'employers_new': 0,
            'errors': 0
        }
        
        # 3.2.10-3.2.11. Запрос и сохранение работодателей
        for employer_id in employer_ids[:100]:  # Ограничиваем пакет
            try:
                # VacancyFetcher.fetch_employer — синхронная функция; выполняем в пуле
                employer_data = await asyncio.to_thread(self.fetcher.fetch_employer, employer_id)
                if employer_data:
                    saved_id = self.db_v4.save_employer(employer_data)
                    if saved_id:
                        stats['employers_new'] += 1
                
                stats['employers_processed'] += 1
                
            except Exception as e:
                self.logger.error(f"Ошибка загрузки работодателя {employer_id}: {e}")
                stats['errors'] += 1
        
        return stats
    
    async def _execute_cleanup_data(self, task: ScheduledTask) -> Dict[str, Any]:
        """Выполнение очистки данных"""
        keep_days = task.params.get('keep_days', 30)
        vacuum_db = task.params.get('vacuum_db', True)
        
        stats = {
            'old_records_deleted': 0,
            'temp_files_deleted': 0,
            'database_vacuumed': False
        }
        
        # Очистка старых записей
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        deleted_count = self.db_v4.cleanup_old_records(cutoff_date)
        stats['old_records_deleted'] = deleted_count
        
        # Вакуум БД
        if vacuum_db:
            self.db_v4.vacuum()
            stats['database_vacuumed'] = True
        
        # Очистка временных файлов
        temp_files = list(Path('data').glob('temp_*.sqlite3'))
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                stats['temp_files_deleted'] += 1
            except:
                pass
        
        return stats
    
    async def _execute_sync_host2(self, task: ScheduledTask) -> Dict[str, Any]:
        """Синхронизация с Host2"""
        if not self.dispatcher.host2_client:
            raise Exception("Host2 client не инициализирован")
        
        # Получаем ID вакансий для синхронизации
        vacancy_ids = self.db_v4.get_unsynced_vacancy_ids(limit=1000)
        
        # Синхронизируем
        result = self.dispatcher.sync_to_host2(vacancy_ids)
        # Помечаем как синхронизированные при успешном статусе
        try:
            status = (result or {}).get('status', 'ok') if isinstance(result, dict) else 'ok'
            marked = 0
            if status in ('ok', 'success', 'synced'):
                marked = self.db_v4.mark_vacancies_synced(vacancy_ids)
        except Exception:
            marked = 0
        
        return {
            'vacancy_ids_synced': len(vacancy_ids),
            'synced_marked': marked,
            'sync_result': result
        }
    
    async def _execute_analyze_host3(self, task: ScheduledTask) -> Dict[str, Any]:
        """Анализ через Host3"""
        if not self.dispatcher.host3_client:
            raise Exception("Host3 client не инициализирован")
        
        batch_size = task.params.get('batch_size', 50)
        analyze_new_only = task.params.get('analyze_new_only', True)
        
        # Получаем вакансии для анализа
        vacancies = self.db_v4.get_unanalyzed_vacancies(
            limit=batch_size, 
            new_only=analyze_new_only
        )
        
        analyzed_count = 0
        for vacancy in vacancies:
            try:
                analysis = self.dispatcher.analyze_with_host3(vacancy)
                # Сохраняем результат анализа
                self.db_v4.save_analysis_result(vacancy['id'], analysis)
                analyzed_count += 1
            except Exception as e:
                self.logger.error(f"Ошибка анализа вакансии {vacancy['id']}: {e}")
        
        return {
            'vacancies_analyzed': analyzed_count,
            'batch_size': batch_size
        }
    
    async def _execute_system_health(self, task: ScheduledTask) -> Dict[str, Any]:
        """Проверка состояния системы"""
        import psutil
        
        # Системные метрики
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
            'database_size_mb': os.path.getsize('data/hh_v4.sqlite3') / (1024*1024) if os.path.exists('data/hh_v4.sqlite3') else 0,
            'active_tasks': len(self.active_executions),
            'host_status': self.dispatcher.get_host_status()
        }
        
        # Проверяем критические значения
        alerts = []
        if health_data['cpu_percent'] > 80:
            alerts.append(f"Высокая загрузка CPU: {health_data['cpu_percent']:.1f}%")
        if health_data['memory_percent'] > 85:
            alerts.append(f"Высокое использование памяти: {health_data['memory_percent']:.1f}%")
        if health_data['disk_percent'] > 90:
            alerts.append(f"Заканчивается место на диске: {health_data['disk_percent']:.1f}%")
        
        health_data['alerts'] = alerts
        health_data['status'] = 'critical' if alerts else 'healthy'
        
        # Сохраняем в БД
        self.db_v4.save_system_health(health_data)
        
        return health_data
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов завершения"""
        self.logger.info(f"Получен сигнал {signum}, завершение работы...")
        self.shutdown_requested = True
    
    def _start_web_panel(self):
        """Автозапуск веб-панели согласно 2.4.2 с проверкой занятого порта"""
        import subprocess
        import socket
        
        web_config = self.config.get('web_interface', {})
        if not web_config.get('auto_start', True):
            self.logger.info("Автозапуск веб-панели отключен в конфигурации")
            return
        
        host = web_config.get('host', 'localhost')
        port = int(web_config.get('port', 8000))
        
        # Проверяем, не занят ли порт (и, возможно, сервер уже запущен)
        try:
            with socket.create_connection((host, port), timeout=1):
                self.logger.info(f"🌐 Веб-панель уже активна на http://{host}:{port}/ — запуск пропущен")
                return
        except Exception:
            pass
        
        try:
            # Запускаем веб-сервер как отдельный процесс
            # web/server.py считывает конфиг при запуске (__main__) и использует host/port
            self.web_process = subprocess.Popen([
                sys.executable, "-m", "web.server"
            ], 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.getcwd())
            
            # Регистрируем веб-панель в БД
            try:
                self.db_v4.register_process(
                    name="web_server", 
                    pid=self.web_process.pid,
                    command_line="web.server",
                    port=port
                )
            except Exception:
                pass
            
            self.logger.info(f"🌐 Веб-панель запущена: http://{host}:{port}/ (PID: {self.web_process.pid})")
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска веб-панели: {e}")
    
    def _stop_web_panel(self):
        """Остановка веб-панели"""
        if self.web_process:
            try:
                self.web_process.terminate()
                self.web_process.wait(timeout=10)
                self.logger.info("Веб-панель остановлена")
            except Exception as e:
                self.logger.error(f"Ошибка остановки веб-панели: {e}")
            finally:
                self.web_process = None
    
    async def start(self):
        """Запуск демона"""
        self.logger.info("Запуск планировщика задач HH-бота v4")
        self.running = True
        
        # Регистрируем демон в БД
        self.db_v4.register_process(
            name="scheduler_daemon", 
            pid=os.getpid(),
            command_line="scheduler_daemon.py"
        )
        
        # Автостарт веб-панели
        self._start_web_panel()
        
        while self.running and not self.shutdown_requested:
            try:
                # Проверяем задачи для выполнения
                await self._check_and_execute_tasks()
                
                # Ожидаем следующую проверку
                await asyncio.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Ошибка в основном цикле планировщика: {e}")
                await asyncio.sleep(10)  # Короткая пауза при ошибках
        
        # Завершение работы
        await self._shutdown()
    
    async def _check_and_execute_tasks(self):
        """Проверка и выполнение задач"""
        now = datetime.now()
        
        # Проверяем каждую задачу
        for task_id, task in list(self.scheduled_tasks.items()):
            if not task.enabled or not task.next_run:
                continue
            
            # Время выполнения наступило?
            if now >= task.next_run:
                # Проверяем лимит одновременных задач
                if len(self.active_executions) >= self.max_concurrent_tasks:
                    self.logger.warning(f"Достигнут лимит одновременных задач ({self.max_concurrent_tasks}), откладываем {task.name}")
                    continue
                
                # Запускаем задачу
                asyncio.create_task(self._execute_task(task_id, task))
    
    async def _shutdown(self):
        """Корректное завершение работы"""
        self.logger.info("Завершение планировщика...")
        
        # Ожидаем завершения активных задач (максимум 5 минут)
        timeout = 300
        start_time = time.time()
        
        while self.active_executions and (time.time() - start_time) < timeout:
            self.logger.info(f"Ожидание завершения {len(self.active_executions)} активных задач...")
            await asyncio.sleep(5)
        
        # Принудительно останавливаем незавершенные задачи
        for task_id, execution in self.active_executions.items():
            execution.status = TaskStatus.CANCELLED
            execution.end_time = datetime.now()
            execution.error = "Cancelled due to daemon shutdown"
        
        # Останавливаем веб-панель
        self._stop_web_panel()
        
        self.running = False
        self.logger.info("Планировщик остановлен")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса планировщика"""
        return {
            'running': self.running,
            'active_tasks': len(self.active_executions),
            'scheduled_tasks': len([t for t in self.scheduled_tasks.values() if t.enabled]),
            'total_executions': len(self.execution_history),
            'last_executions': [
                {
                    'task_type': ex.task_type.value,
                    'status': ex.status.value,
                    'start_time': ex.start_time.isoformat(),
                    'duration': ex.duration_seconds
                }
                for ex in self.execution_history[-10:]
            ]
        }


def main():
    """Точка входа для демона"""
    os.makedirs("logs", exist_ok=True)
    
    # // Chg_UNIFIED_LOG_2009 + Chg_LOG_CFG_2509: централизованное логирование через ConfigManager
    try:
        cfgm = get_config_manager()
        logging_cfg = cfgm.get_logging_settings()
        log_file = logging_cfg.get('file_path', 'logs/app.log')
        max_bytes = int(logging_cfg.get('max_size_mb', 100)) * 1024 * 1024
        backup_count = int(logging_cfg.get('backup_count', 3))
        level = getattr(logging, str(logging_cfg.get('level', 'INFO')).upper(), logging.INFO)
        console_enabled = bool(logging_cfg.get('console_enabled', True))
        db_enabled = bool(logging_cfg.get('db_enabled', False))

        root = logging.getLogger()
        # Файловый обработчик (с ротацией)
        if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '') == str(Path(log_file)) for h in root.handlers):
            fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
            fmt = logging.Formatter(logging_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            fh.setFormatter(fmt)
            root.addHandler(fh)
        # Консольный обработчик
        if console_enabled and not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
            sh = logging.StreamHandler()
            sh.setFormatter(logging.Formatter(logging_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))
            root.addHandler(sh)
        # Уровень
        root.setLevel(level)
    except Exception:
        # Фолбэк на базовую конфигурацию
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/app.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
    logger = logging.getLogger(__name__)
    logger.info("Инициализация планировщика HH-бота v4")
    
    try:
        # Создаем PID файл
        pid_file = Path("data/scheduler_daemon.pid")
        pid_file.parent.mkdir(exist_ok=True)
        pid_file.write_text(str(os.getpid()))
        logger.info(f"PID файл создан: {pid_file} (PID: {os.getpid()})")
        
        daemon = SchedulerDaemon()
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка планировщика: {e}")
        sys.exit(1)
    finally:
        # Удаляем PID файл при завершении
        try:
            pid_file = Path("data/scheduler_daemon.pid")
            if pid_file.exists():
                pid_file.unlink()
                logger.info("PID файл удален")
        except:
            pass


if __name__ == "__main__":
    main()
