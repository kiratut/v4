"""
Синхронный диспетчер задач для HH Tool v4
Простая архитектура без async/await

// Chg_TASK_DISPATCHER_2009: Интеграция с Host2 и Host3 клиентами
"""

import threading
import time
import logging
from logging.handlers import RotatingFileHandler
import json
import queue
import signal
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .task_database import TaskDatabase

# Импорты новых хостов
try:
    from .host2_client import create_host2_client, PostgreSQLClient
    from .host3_client import create_host3_client, LLMClient
except ImportError:
    # Для backward compatibility
    PostgreSQLClient = None
    LLMClient = None

@dataclass
class Task:
    id: str
    type: str
    params: Dict
    timeout_sec: int = 300
    chunk_size: int = 500

class TaskDispatcher:
    """
    Синхронный диспетчер задач с threading
    - Chunked processing для больших объёмов
    - Timeout monitoring
    - Graceful shutdown
    """
    
    def __init__(self, max_workers=3, chunk_size=500, config: Dict[str, Any] = None):
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.task_queue = queue.Queue()
        self.workers: List[threading.Thread] = []
        self.running = False
        self.current_tasks: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        
        # Configuration
        self.config = config or {}
        
        # Database
        self.db = TaskDatabase()
        
        # // Chg_HOST_CLIENTS_2009: Инициализация клиентов для Host2 и Host3
        self.host2_client: Optional[PostgreSQLClient] = None
        self.host3_client: Optional[LLMClient] = None
        
        # // Chg_LOG_ROTATE_1509: Logging с ротацией и без повторной базовой настройки
        root = logging.getLogger()
        if not root.handlers:
            handlers = [
                RotatingFileHandler('logs/app.log', maxBytes=100*1024*1024, backupCount=3, encoding='utf-8'),
                logging.StreamHandler()
            ]
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=handlers
            )
        # // Chg_UNIFIED_LOG_2109: убран отдельный dispatcher.log, используем общий app.log
        self.logger = logging.getLogger(__name__)
        
        # Обработчики сигналов для graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        
        # Инициализируем клиенты хостов после logger
        self._init_host_clients()
    
    def _init_host_clients(self):
        """Инициализация клиентов для Host2 и Host3"""
        hosts_config = self.config.get('hosts', {})
        
        # Инициализация Host2 (PostgreSQL)
        host2_config = hosts_config.get('host2', {})
        if host2_config.get('enabled', False) and PostgreSQLClient:
            try:
                self.host2_client = create_host2_client(host2_config.get('connection', {}))
                self.logger.info("Host2 (PostgreSQL) client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Host2 client: {e}")
        
        # Инициализация Host3 (LLM)
        host3_config = hosts_config.get('host3', {})
        if host3_config.get('enabled', False) and LLMClient:
            try:
                self.host3_client = create_host3_client(host3_config.get('connection', {}))
                self.logger.info("Host3 (LLM) client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize Host3 client: {e}")
    
    def sync_to_host2(self, vacancy_ids: List[int]) -> Dict[str, Any]:
        """Синхронизация данных с Host2 (PostgreSQL)"""
        if not self.host2_client:
            return {'status': 'disabled', 'message': 'Host2 client not available'}
        
        try:
            result = self.host2_client.sync_vacancy_data(vacancy_ids)
            self.logger.info(f"Synced {len(vacancy_ids)} vacancies to Host2")
            return result
        except Exception as e:
            self.logger.error(f"Host2 sync failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def analyze_with_host3(self, vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ вакансии через Host3 (LLM)"""
        if not self.host3_client:
            return {'status': 'disabled', 'message': 'Host3 client not available'}
        
        try:
            result = self.host3_client.analyze_vacancy(vacancy_data)
            self.logger.info(f"Analyzed vacancy {vacancy_data.get('id', 'unknown')} with Host3")
            return result
        except Exception as e:
            self.logger.error(f"Host3 analysis failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_host_status(self) -> Dict[str, Any]:
        """Получение статуса всех хостов"""
        status = {
            'host1': {'status': 'active', 'type': 'sqlite', 'description': 'Primary storage'},
            'host2': {'status': 'disabled', 'type': 'postgresql', 'description': 'Analytics'},
            'host3': {'status': 'disabled', 'type': 'llm', 'description': 'AI analysis'}
        }
        
        if self.host2_client:
            try:
                host2_health = self.host2_client.health_check()
                status['host2'] = host2_health
            except Exception as e:
                status['host2']['status'] = 'error'
                status['host2']['error'] = str(e)
        
        if self.host3_client:
            try:
                host3_health = self.host3_client.health_check()
                status['host3'] = host3_health
            except Exception as e:
                status['host3']['status'] = 'error'
                status['host3']['error'] = str(e)
        
        return status
    
    def start(self):
        """Запуск диспетчера"""
        self.running = True
        
        # Загружаем существующие pending задачи из БД
        self._load_pending_tasks()
        
        # Запуск worker threads
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop, 
                args=(f"worker-{i}",),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
        
        self.logger.info(f"Task dispatcher started with {self.max_workers} workers")
        
        # Основной цикл мониторинга
        self._monitor_loop()
    
    def _load_pending_tasks(self):
        """Загрузка pending задач из БД при старте"""
        try:
            pending_tasks = self.db.get_pending_tasks(limit=100)
            for task_data in pending_tasks:
                task = Task(
                    id=task_data['id'],
                    type=task_data['type'],
                    params=json.loads(task_data.get('params_json', '{}')),
                    timeout_sec=task_data.get('timeout_sec', 3600)
                )
                self.task_queue.put(task)
                self.logger.info(f"Loaded pending task {task.id} ({task.type})")
            
            if pending_tasks:
                self.logger.info(f"Loaded {len(pending_tasks)} pending tasks from database")
        except Exception as e:
            self.logger.error(f"Error loading pending tasks: {e}")
    
    def _worker_loop(self, worker_id: str):
        """Цикл обработки задач worker'ом"""
        while self.running:
            try:
                # Получение задачи (блокирующее, с таймаутом)
                task = self.task_queue.get(timeout=1.0)
                
                # Регистрация текущей задачи
                with self.lock:
                    self.current_tasks[worker_id] = {
                        'task_id': task.id,
                        'started_at': time.time(),
                        'timeout': task.timeout_sec
                    }
                
                self.logger.info(f"Worker {worker_id} started task {task.id} ({task.type})")
                
                # Выполнение задачи
                self._execute_task(worker_id, task)
                
            except queue.Empty:
                continue  # Нет задач, ждём
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
            finally:
                # Очистка текущей задачи
                with self.lock:
                    self.current_tasks.pop(worker_id, None)
                
                try:
                    self.task_queue.task_done()
                except:
                    pass
    
    def _execute_task(self, worker_id: str, task: Task):
        """Выполнение конкретной задачи"""
        try:
            # // Chg_TASK_WORKER_1509: сохраняем worker_id при переходе в running
            self.db.update_task_status(task.id, 'running', worker_id=worker_id)
            
            if task.type == 'load_vacancies':
                result = self._handle_load_vacancies(worker_id, task)
            elif task.type == 'process_pipeline':
                result = self._handle_process_pipeline(worker_id, task)
            elif task.type == 'cleanup':
                result = self._handle_cleanup(worker_id, task)
            else:
                raise ValueError(f"Unknown task type: {task.type}")
            
            self.db.update_task_status(task.id, 'completed', result)
            self.logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Task {task.id} failed: {e}")
            self.db.update_task_status(task.id, 'failed', {'error': str(e)})
    
    def _handle_load_vacancies(self, worker_id: str, task: Task) -> Dict:
        """
        Загрузка вакансий с chunked processing
        """
        from plugins.fetcher_v4 import VacancyFetcher
        
        filter_params = task.params
        total_expected = filter_params.get('max_pages', 20) * 100  # ~100 вакансий на страницу
        
        # Разбиваем на части для контроля прогресса
        chunk_count = max(1, total_expected // task.chunk_size)
        
        fetcher = VacancyFetcher()
        loaded_total = 0
        
        for chunk_idx in range(chunk_count):
            # Проверка на прерывание
            if not self.running:
                self.logger.info(f"Task {task.id} interrupted during chunk {chunk_idx}")
                break
                
            # Проверка таймаута
            if self._is_task_timeout(worker_id):
                self.logger.warning(f"Task {task.id} timed out at chunk {chunk_idx}")
                break
            
            # Загрузка части данных
            chunk_params = filter_params.copy()
            chunk_params['page_start'] = chunk_idx * (task.chunk_size // 100)
            chunk_params['page_end'] = chunk_params['page_start'] + (task.chunk_size // 100)
            
            chunk_result = fetcher.fetch_chunk(chunk_params)
            loaded_total += chunk_result['loaded_count']
            
            self.logger.info(f"Worker {worker_id}: chunk {chunk_idx+1}/{chunk_count}, "
                           f"loaded {loaded_total} vacancies")
            
            # Прерывание если страница пустая
            if chunk_result['loaded_count'] == 0:
                break
        
        return {
            'loaded_count': loaded_total,
            'chunks_processed': chunk_idx + 1 if 'chunk_idx' in locals() else 0
        }
    
    def _handle_process_pipeline(self, worker_id: str, task: Task) -> Dict:
        """Обработка pipeline задач - TODO: реализовать в будущих версиях"""
        # TODO: Создать plugins.pipeline для v4
        self.logger.warning("Pipeline processing не реализован в v4")
        return {'status': 'skipped', 'reason': 'Pipeline не реализован в v4'}
    
    def _handle_cleanup(self, worker_id: str, task: Task) -> Dict:
        """Очистка старых данных"""
        cleanup_result = self.db.cleanup_old_tasks(days_to_keep=7)
        
        return {
            'cleaned_tasks': cleanup_result['cleaned_count'],
            'cleaned_bytes': cleanup_result.get('cleaned_bytes', 0)
        }
    
    def _is_task_timeout(self, worker_id: str) -> bool:
        """Проверка таймаута задачи"""
        with self.lock:
            task_info = self.current_tasks.get(worker_id)
            
        if not task_info:
            return False
        
        elapsed = time.time() - task_info['started_at']
        return elapsed > task_info['timeout']
    
    def _monitor_loop(self):
        """Цикл мониторинга для прерывания зависших задач"""
        while self.running:
            try:
                self._check_timeouts()
                self._check_schedule()
                time.sleep(10)  # Проверка каждые 10 секунд
            except KeyboardInterrupt:
                self._handle_shutdown()
                break
            except Exception as e:
                self.logger.error(f"Monitor loop error: {e}")
                time.sleep(5)
    
    def _check_timeouts(self):
        """Проверка и прерывание зависших задач"""
        current_time = time.time()
        
        with self.lock:
            timeout_tasks = []
            for worker_id, task_info in self.current_tasks.items():
                elapsed = current_time - task_info['started_at']
                
                if elapsed > task_info['timeout']:
                    timeout_tasks.append((worker_id, task_info))
        
        for worker_id, task_info in timeout_tasks:
            self.logger.warning(f"TIMEOUT: Task {task_info['task_id']} "
                              f"on worker {worker_id} (elapsed: {elapsed:.1f}s)")
            
            # Помечаем задачу как failed
            self.db.update_task_status(
                task_info['task_id'], 
                'failed', 
                {'error': f'Timeout after {elapsed:.1f}s'}
            )
    
    def _check_schedule(self):
        """Проверка и запуск запланированных задач"""
        due_tasks = self.db.get_due_tasks()
        
        for task_data in due_tasks:
            # Проверяем конфликты: если такой тип задач уже выполняется
            if self._has_running_task_type(task_data['type']):
                self.logger.info(f"Skipping scheduled task {task_data['id']}: "
                               f"task type {task_data['type']} already running")
                continue
            
            # Создаём объект задачи
            task = Task(
                id=task_data['id'],
                type=task_data['type'],
                params=task_data.get('params', {}),
                timeout_sec=task_data.get('timeout_sec', 300)
            )
            
            # Добавляем в очередь
            self.task_queue.put(task)
            # // Chg_STATUS_1509: normalize 'queued' -> 'pending' (start)
            self.db.update_task_status(task.id, 'pending')
            self.logger.info(f"Pending scheduled task: {task.id} ({task.type})")
            # // Chg_STATUS_1509: normalize 'queued' -> 'pending' (end)
    
    def _has_running_task_type(self, task_type: str) -> bool:
        """Проверка выполнения задач данного типа"""
        with self.lock:
            for worker_id, task_info in self.current_tasks.items():
                # Получаем тип текущей задачи из БД
                current_task = self.db.get_task(task_info['task_id'])
                if current_task and current_task['type'] == task_type:
                    return True
        return False
    
    def add_task(self, task_type: str, params: Dict, 
                 schedule_at: Optional[float] = None,
                 timeout_sec: int = 300,
                 chunk_size: int = None) -> str:
        """Добавление задачи в очередь"""
        import uuid
        
        task_id = str(uuid.uuid4())
        chunk_size = chunk_size or self.chunk_size
        
        # Сохранение в БД
        self.db.create_task(
            task_id=task_id,
            task_type=task_type,
            params=params,
            schedule_at=schedule_at,
            timeout_sec=timeout_sec
        )
        
        # Если задача не запланирована, добавляем сразу в очередь
        if schedule_at is None or schedule_at <= time.time():
            task = Task(
                id=task_id,
                type=task_type,
                params=params,
                timeout_sec=timeout_sec,
                chunk_size=chunk_size
            )
            
            self.task_queue.put(task)
            # // Chg_STATUS_1509: normalize 'queued' -> 'pending' (start)
            self.db.update_task_status(task_id, 'pending')
            self.logger.info(f"Added immediate task (pending): {task_id} ({task_type})")
            # // Chg_STATUS_1509: normalize 'queued' -> 'pending' (end)
        else:
            self.logger.info(f"Scheduled task: {task_id} ({task_type}) "
                           f"for {time.ctime(schedule_at)}")
        
        return task_id
    
    def get_progress(self, task_id: str) -> Dict:
        """Получение прогресса выполнения задачи"""
        task_info = self.db.get_task(task_id)
        if not task_info:
            return {'status': 'not_found', 'progress': 0}
        
        return {
            'task_id': task_id,
            'status': task_info.get('status', 'unknown'),
            'progress': task_info.get('progress', 0),
            'result': task_info.get('result', {}),
            'error': task_info.get('error'),
            'created_at': task_info.get('created_at'),
            'updated_at': task_info.get('updated_at')
        }
    
    def calculate_eta(self, queue_size: int, avg_processing_time: float) -> float:
        """Расчёт ожидаемого времени завершения очереди"""
        if queue_size == 0:
            return 0.0
        
        # Учитываем количество воркеров
        effective_time = (queue_size * avg_processing_time) / max(len(self.workers), 1)
        return time.time() + effective_time
    
    def get_status(self) -> Dict:
        """Получение статуса диспетчера"""
        with self.lock:
            current_tasks_info = dict(self.current_tasks)
        
        return {
            'running': self.running,
            'workers_count': len(self.workers),
            'queue_size': self.task_queue.qsize(),
            'current_tasks': current_tasks_info,
            'stats': self.db.get_stats()
        }
    
    def _handle_shutdown(self, signum=None, frame=None):
        """Graceful shutdown"""
        self.logger.info("Shutting down task dispatcher...")
        self.running = False
        
        # Ждём завершения текущих задач
        for worker in self.workers:
            worker.join(timeout=30)  # Ждём максимум 30 секунд
        
        self.logger.info("Task dispatcher stopped")

# Точка входа
if __name__ == "__main__":
    dispatcher = TaskDispatcher(max_workers=3, chunk_size=500)
    try:
        dispatcher.start()
    except KeyboardInterrupt:
        print("Interrupted by user")
