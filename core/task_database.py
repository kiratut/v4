"""
Простая обёртка для SQLite без ORM для HH Tool v4
Управление очередью задач и данными вакансий
"""

import sqlite3
import json
import time
import hashlib
import logging
from typing import Dict, List, Optional, Any
import uuid
from contextlib import contextmanager
from datetime import datetime

class TaskDatabase:
    """
    Простая обёртка для SQLite без сложных миграций
    """
    
    def __init__(self, db_path="data/hh_v4.sqlite3"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._create_tables()
    
    def register_process(self, name: str, pid: int, command_line: str = "", 
                        host: str = "localhost", port: int = None):
        """Регистрация процесса в БД"""
        import time
        now = time.time()
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_processes 
                (name, pid, start_time, command_line, host, port, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'running', ?, ?)
            """, (name, pid, now, command_line, host, port, now, now))
            # // Chg_PROC_COMMIT_2509: фиксируем регистрацию процесса
            conn.commit()
    
    def get_process_pid(self, name: str) -> int:
        """Получение PID процесса по имени"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT pid FROM system_processes 
                WHERE name = ? AND status = 'running'
            """, (name,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def kill_process(self, name: str) -> bool:
        """Убить процесс по имени и обновить статус"""
        import os
        import psutil
        
        pid = self.get_process_pid(name)
        if not pid:
            return False
        
        try:
            if psutil.pid_exists(pid):
                os.kill(pid, 15)  # SIGTERM
                import time
                time.sleep(1)
                if psutil.pid_exists(pid):
                    os.kill(pid, 9)  # SIGKILL
            
            # Обновляем статус в БД
            with self.get_connection() as conn:
                conn.execute("""
                    UPDATE system_processes 
                    SET status = 'stopped', updated_at = ?
                    WHERE name = ?
                """, (time.time(), name))
                # // Chg_PROC_COMMIT_2509: коммитим смену статуса процесса
                conn.commit()
            
            return True
        except Exception:
            return False
    
    def cleanup_dead_processes(self):
        """Очистка мертвых процессов из БД"""
        import psutil
        import time
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT name, pid FROM system_processes 
                WHERE status = 'running'
            """)
            
            for name, pid in cursor.fetchall():
                if not psutil.pid_exists(pid):
                    conn.execute("""
                        UPDATE system_processes 
                        SET status = 'dead', updated_at = ?
                        WHERE name = ?
                    """, (time.time(), name))
            # // Chg_PROC_COMMIT_2509: сохраняем результаты очистки
            conn.commit()
    
    def _create_tables(self):
        """Инициализация схемы БД"""
        with self.get_connection() as conn:
            # Таблица задач (простая, без сложностей Alembic)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    params_json TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at REAL NOT NULL,
                    schedule_at REAL,
                    started_at REAL,
                    finished_at REAL,
                    timeout_sec INTEGER DEFAULT 3600,
                    worker_id TEXT,
                    result_json TEXT,
                    progress_json TEXT
                )
            """)
            
            # // Chg_EMPLOYERS_2509: таблица работодателей (v4)
            # Создание таблицы employers (не изменяет существующую схему)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS employers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hh_id INTEGER UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    url TEXT,
                    raw_json TEXT,
                    created_at REAL,
                    updated_at REAL
                )
            """)

            # Миграции для существующей таблицы employers: добавляем недостающие колонки
            try:
                cur = conn.execute("PRAGMA table_info(employers)")
                existing_cols = {row[1] for row in cur.fetchall()}
                if 'url' not in existing_cols:
                    conn.execute("ALTER TABLE employers ADD COLUMN url TEXT")
                if 'raw_json' not in existing_cols:
                    conn.execute("ALTER TABLE employers ADD COLUMN raw_json TEXT")
            except sqlite3.OperationalError:
                # ALTER TABLE может быть недоступен в некоторых окружениях
                pass

            # Метрики здоровья системы
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS system_health (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_percent REAL,
                    database_size_mb REAL,
                    active_tasks INTEGER,
                    host_status_json TEXT
                )
                """
            )
            
            # Таблица процессов для управления PID
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_processes (
                    name TEXT PRIMARY KEY,
                    pid INTEGER NOT NULL,
                    start_time REAL NOT NULL,
                    command_line TEXT,
                    host TEXT DEFAULT 'localhost',
                    port INTEGER,
                    status TEXT DEFAULT 'running',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            
            # Таблица вакансий (адаптируем из v3)
            conn.execute("""
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
                    raw_json TEXT,
                    created_at REAL,
                    updated_at REAL,
                    is_processed INTEGER DEFAULT 0
                )
            """)
            # // Chg_DB_MIGRATE_1509: миграция недостающих колонок в vacancies
            try:
                cursor = conn.execute("PRAGMA table_info(vacancies)")
                existing_cols = {row[1] for row in cursor.fetchall()}
                if 'created_at' not in existing_cols:
                    conn.execute("ALTER TABLE vacancies ADD COLUMN created_at REAL")
                if 'updated_at' not in existing_cols:
                    conn.execute("ALTER TABLE vacancies ADD COLUMN updated_at REAL")
                if 'is_processed' not in existing_cols:
                    conn.execute("ALTER TABLE vacancies ADD COLUMN is_processed INTEGER DEFAULT 0")
                # // Chg_V4HOST2_2509: флаг синхронизации с Host2
                if 'synced_host2' not in existing_cols:
                    conn.execute("ALTER TABLE vacancies ADD COLUMN synced_host2 INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                # Если ALTER TABLE не поддерживается в текущем контексте — игнорируем
                pass
            
            # Таблица результатов плагинов
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plugin_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vacancy_id TEXT NOT NULL,
                    plugin_name TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at REAL DEFAULT (julianday('now')),
                    FOREIGN KEY (vacancy_id) REFERENCES vacancies (id)
                )
            """)
            
            # Индексы для производительности
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_schedule ON tasks(schedule_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_type ON tasks(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_hh_id ON vacancies(hh_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_filter ON vacancies(filter_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_processed ON vacancies(processed_at)")
            # // Chg_DB_INDEX_1509: индексы для новых колонок
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_created ON vacancies(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_is_processed ON vacancies(is_processed)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vacancies_synced_host2 ON vacancies(synced_host2)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plugin_results_vacancy ON plugin_results(vacancy_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_system_health_ts ON system_health(ts)")

            # // Chg_DB_LOGS_2409: таблица логов централизованного логирования
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    level TEXT NOT NULL,
                    module TEXT,
                    func TEXT,
                    message TEXT NOT NULL,
                    context_json TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts)")
            # // Chg_COMMIT_DDL_2509: фиксируем все DDL/ALTER изменения
            try:
                conn.commit()
            except Exception:
                pass
    
    @contextmanager
    def get_connection(self):
        """Context manager для соединения с БД"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row  # Доступ к колонкам по имени
        
        # Настройки производительности
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        
        try:
            yield conn
        finally:
            conn.close()
    
    # === МЕТОДЫ ДЛЯ ЗАДАЧ ===
    
    def create_task(self, task_id: str, task_type: str, params: Dict,
                   schedule_at: Optional[float] = None, timeout_sec: int = 300):
        """Создание новой задачи"""
        current_time = time.time()
        with self.get_connection() as conn:
            # // Chg_TASK_UPSERT_2509: защищаемся от редких коллизий id (повторные регистрации)
            conn.execute("""
                INSERT OR IGNORE INTO tasks (id, type, params_json, created_at, schedule_at, timeout_sec)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (task_id, task_type, json.dumps(params), current_time, schedule_at, timeout_sec))
            conn.commit()
            
        self.logger.info(f"Created task {task_id} ({task_type})")
    
    def update_task_status(self, task_id: str, status: str, result: Dict = None, worker_id: Optional[str] = None):
        """Обновление статуса задачи"""
        with self.get_connection() as conn:
            if status == 'running':
                # // Chg_TASK_WORKER_1509: сохраняем worker_id при старте
                if worker_id:
                    conn.execute("""
                        UPDATE tasks 
                        SET status = ?, started_at = julianday('now'), worker_id = ?
                        WHERE id = ?
                    """, (status, worker_id, task_id))
                else:
                    conn.execute("""
                        UPDATE tasks 
                        SET status = ?, started_at = julianday('now')
                        WHERE id = ?
                    """, (status, task_id))
            elif status in ('completed', 'failed'):
                conn.execute("""
                    UPDATE tasks 
                    SET status = ?, finished_at = julianday('now'), result_json = ?
                    WHERE id = ?
                """, (status, json.dumps(result or {}), task_id))
            else:
                conn.execute("""
                    UPDATE tasks SET status = ? WHERE id = ?
                """, (status, task_id))
            
            conn.commit()
    
    def update_task_progress(self, task_id: str, progress: Dict):
        """Обновление прогресса задачи"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE tasks SET progress_json = ? WHERE id = ?
            """, (json.dumps(progress), task_id))
            conn.commit()
    
    def get_due_tasks(self) -> List[Dict]:
        """Получение задач готовых к выполнению"""
        current_time = time.time()
        
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM tasks
                WHERE status = 'pending'
                  AND (schedule_at IS NULL OR schedule_at <= ?)
                ORDER BY schedule_at ASC, created_at ASC
                LIMIT 50
            """, (current_time,))
            
            tasks = []
            for row in cursor.fetchall():
                task = dict(row)
                if task['params_json']:
                    task['params'] = json.loads(task['params_json'])
                tasks.append(task)
            
            return tasks
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Получение задачи по ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            
            if row:
                task = dict(row)
                if task['params_json']:
                    task['params'] = json.loads(task['params_json'])
                if task['result_json']:
                    task['result'] = json.loads(task['result_json'])
                if task['progress_json']:
                    task['progress'] = json.loads(task['progress_json'])
                return task
            
            return None
    
    def get_pending_tasks(self, limit: int = 100) -> List[Dict]:
        """Получение pending задач из БД"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, type, params_json, timeout_sec, created_at
                FROM tasks 
                -- // Chg_STATUS_1509: normalize 'queued' -> 'pending' (start)
                WHERE status = 'pending'
                -- // Chg_STATUS_1509: normalize 'queued' -> 'pending' (end)
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict:
        """Получение статистики по задачам и вакансиям"""
        with self.get_connection() as conn:
            # Статистика задач за последний день
            # // Chg_STATS_TIME_1509: сравнение по unix timestamp (created_at хранится как seconds)
            cursor = conn.execute("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM tasks 
                WHERE created_at > strftime('%s','now','-1 day')
                GROUP BY status
            """)
            
            task_stats = {}
            for row in cursor.fetchall():
                task_stats[row['status']] = row['count']
            
            # Статистика вакансий
            # // Chg_STATS_TIME_1509: используем created_at и unix timestamp для "сегодня"
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_vacancies,
                    COUNT(CASE WHEN is_processed = 1 THEN 1 END) as processed_vacancies,
                    COUNT(CASE WHEN created_at > strftime('%s','now','-1 day') THEN 1 END) as today_vacancies
                FROM vacancies
            """)
            
            vacancy_stats = dict(cursor.fetchone())
            
            # // Chg_VAC_ADDED_1509: метрика добавленных за последний запуск (окно 10 минут)
            try:
                last_row = conn.execute(
                    """
                    SELECT created_at, started_at, finished_at
                    FROM tasks
                    WHERE type = 'load_vacancies'
                    ORDER BY COALESCE(finished_at, started_at, created_at) DESC
                    LIMIT 1
                    """
                ).fetchone()
                added_last_run = 0
                last_run_at_iso = None
                if last_row:
                    created_at = last_row['created_at']  # seconds
                    started_at = last_row['started_at']  # julian day
                    finished_at = last_row['finished_at']  # julian day
                    candidates = []
                    if created_at:
                        candidates.append(created_at)
                    def _jd_to_sec(v):
                        return (v - 2440587.5) * 86400.0 if v else None
                    if started_at:
                        st = _jd_to_sec(started_at)
                        if st: candidates.append(st)
                    if finished_at:
                        ft = _jd_to_sec(finished_at)
                        if ft: candidates.append(ft)
                    candidates = [t for t in candidates if t]
                    if candidates:
                        last_ts = max(candidates)
                        window_start = last_ts - 600.0
                        # // Chg_VAC_ADDED_WINDOW_1509: жёсткое окно [last_ts-600, last_ts]
                        row2 = conn.execute(
                            "SELECT COUNT(*) AS cnt FROM vacancies WHERE created_at BETWEEN ? AND ?",
                            (window_start, last_ts)
                        ).fetchone()
                        added_last_run = row2['cnt'] if row2 else 0
                        try:
                            last_run_at_iso = datetime.fromtimestamp(last_ts).isoformat()
                        except Exception:
                            last_run_at_iso = None
                vacancy_stats['added_last_run_10m_window'] = added_last_run
                vacancy_stats['last_run_at'] = last_run_at_iso
            except Exception:
                vacancy_stats['added_last_run_10m_window'] = 0
                vacancy_stats['last_run_at'] = None
            # // Chg_VAC_ADDED_1509 end
            
            return {
                'tasks': task_stats,
                'vacancies': vacancy_stats,
                'timestamp': datetime.now().isoformat()
            }

    # // Chg_DB_LOGS_2409: внутренний метод записи строки лога в БД
    def _write_log_record(self, ts: float, level: str, module: str, func: str, message: str, context_json: Optional[str] = None) -> None:
        try:
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO logs (ts, level, module, func, message, context_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (ts, level, module, func, message, context_json)
                )
                conn.commit()
        except Exception:
            # не выбрасываем наружу, чтобы не мешать основному потоку
            pass
    
    def cleanup_old_tasks(self, days_to_keep=7) -> Dict:
        """Очистка старых задач"""
        cutoff_time = time.time() - (days_to_keep * 24 * 3600)
        
        with self.get_connection() as conn:
            # Подсчитываем что будем удалять
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM tasks 
                WHERE status IN ('completed', 'failed') 
                  AND finished_at < ?
            """, (cutoff_time,))
            
            count_to_delete = cursor.fetchone()['count']
            
            # Удаляем старые задачи
            cursor = conn.execute("""
                DELETE FROM tasks 
                WHERE status IN ('completed', 'failed') 
                  AND finished_at < ?
            """, (cutoff_time,))
            
            deleted_count = cursor.rowcount
            conn.commit()
            
            # VACUUM для освобождения места
            conn.execute("VACUUM")
        
        self.logger.info(f"Cleaned up {deleted_count} old tasks")
        
        return {
            'cleaned_count': deleted_count,
            'days_kept': days_to_keep
        }
    
    # === МЕТОДЫ ДЛЯ ВАКАНСИЙ ===
    
    def save_vacancy(self, vacancy_data: Dict, filter_id: str = None) -> bool:
        """
        Сохранение вакансии с дедупликацией по content_hash
        Обновлено для схемы Database_Schema_v4.md: hh_id, processed_at
        """
        try:
            # // Chg_VAC_SAVE_1509: подробное логирование входящих данных
            # // Chg_LOGVERB_2509: понижаем уровень детализации до DEBUG
            self.logger.debug(f"save_vacancy: input={json.dumps(vacancy_data, ensure_ascii=False)[:800]}, filter_id={filter_id}")
            self.logger.debug(f"save_vacancy: received id={vacancy_data.get('id')} filter_id={filter_id}")
            # Создаем контент для хеширования (исключаем изменяемые поля)
            content_for_hash = {
                'id': vacancy_data.get('id'),
                'name': vacancy_data.get('name'),
                'employer': vacancy_data.get('employer', {}).get('name', ''),
                'snippet': vacancy_data.get('snippet', {}),
                'salary': vacancy_data.get('salary'),
                'area': vacancy_data.get('area', {}),
                'published_at': vacancy_data.get('published_at')
            }
            content_hash = hashlib.md5(json.dumps(content_for_hash, sort_keys=True).encode()).hexdigest()
            
            # Извлекаем данные
            hh_id = str(vacancy_data.get('id'))  # Chg_22_1509: external_id → hh_id
            title = vacancy_data.get('name', '')
            employer = vacancy_data.get('employer', {})
            company = employer.get('name', '') if employer else ''
            employer_id = str(employer.get('id', '')) if employer and employer.get('id') else None
            
            salary = vacancy_data.get('salary') or {}
            salary_from = salary.get('from') if salary else None
            salary_to = salary.get('to') if salary else None
            currency = salary.get('currency') if salary else None
            
            experience = vacancy_data.get('experience', {})
            experience_name = experience.get('name', '') if experience else ''
            
            schedule = vacancy_data.get('schedule', {})
            schedule_name = schedule.get('name', '') if schedule else ''
            
            employment = vacancy_data.get('employment', {})
            employment_name = employment.get('name', '') if employment else ''
            
            snippet = vacancy_data.get('snippet', {})
            description = snippet.get('responsibility', '') if snippet else ''
            key_skills = snippet.get('requirement', '') if snippet else ''
            
            area = vacancy_data.get('area', {})
            area_name = area.get('name', '') if area else ''
            
            published_at = vacancy_data.get('published_at', '')
            url = vacancy_data.get('alternate_url', '')
            
            raw_json = json.dumps(vacancy_data, ensure_ascii=False)
            
            with self.get_connection() as conn:
                # Проверяем существование по hh_id (исправлено!)
                cursor = conn.execute(
                    "SELECT content_hash FROM vacancies WHERE hh_id = ?", 
                    (hh_id,)
                )
                existing = cursor.fetchone()
                
                if existing and existing['content_hash'] == content_hash:
                    # Контент не изменился
                    # // Chg_VAC_SAVE_1509: логируем пропуск без изменений
                    # // Chg_LOGVERB_2509: переводим в DEBUG
                    self.logger.debug(f"save_vacancy: skip unchanged hh_id={hh_id}")
                    return False
                
                current_time = time.time()
                
                if existing:
                    # Обновляем существующую запись
                    # // Chg_VAC_SAVE_1509: не трогаем processed_at при апдейте; обновляем updated_at
                    conn.execute("""
                        UPDATE vacancies SET
                            title = ?, company = ?, employer_id = ?,
                            salary_from = ?, salary_to = ?, currency = ?,
                            experience = ?, schedule = ?, employment = ?,
                            description = ?, key_skills = ?, area = ?,
                            published_at = ?, url = ?, updated_at = ?,
                            filter_id = ?, content_hash = ?, raw_json = ?
                        WHERE hh_id = ?
                    """, (
                        title, company, employer_id,
                        salary_from, salary_to, currency,
                        experience_name, schedule_name, employment_name,
                        description, key_skills, area_name,
                        published_at, url, current_time,
                        filter_id, content_hash, raw_json,
                        hh_id
                    ))
                    # // Chg_LOGVERB_2509: понижаем уровень до DEBUG, чтобы INFO не засорялся
                    self.logger.debug(f"save_vacancy: updated hh_id={hh_id}")
                else:
                    # Вставляем новую запись
                    # // Chg_VAC_SAVE_1509: processed_at по умолчанию NULL; добавляем created_at/updated_at/is_processed
                    conn.execute("""
                        INSERT INTO vacancies (
                            hh_id, title, company, employer_id,
                            salary_from, salary_to, currency,
                            experience, schedule, employment,
                            description, key_skills, area,
                            published_at, url, processed_at,
                            filter_id, content_hash, raw_json,
                            created_at, updated_at, is_processed
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        hh_id, title, company, employer_id,
                        salary_from, salary_to, currency,
                        experience_name, schedule_name, employment_name,
                        description, key_skills, area_name,
                        published_at, url, None,
                        filter_id, content_hash, raw_json,
                        current_time, current_time, 0
                    ))
                    # // Chg_LOGVERB_2509: понижаем уровень до DEBUG
                    self.logger.debug(f"save_vacancy: inserted hh_id={hh_id}")
                
                conn.commit()
                return True
                
        except Exception as e:
            # // Chg_VAC_SAVE_1509: подробное логирование ошибок
            self.logger.exception(f"save_vacancy error for hh_id={vacancy_data.get('id')}: {e}")
            print(f"Ошибка сохранения вакансии: {e}")
            return False
    
    def get_unprocessed_vacancies(self, limit: int = 100) -> List[Dict]:
        """Получение необработанных вакансий для pipeline"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM vacancies 
                WHERE processed_at IS NULL 
                ORDER BY published_at DESC 
                LIMIT ?
            """, (limit,))
        
            vacancies = []
            for row in cursor.fetchall():
                vacancy = dict(row)
                if vacancy['raw_json']:
                    vacancy['raw_data'] = json.loads(vacancy['raw_json'])
                if vacancy['key_skills']:
                    vacancy['key_skills_list'] = json.loads(vacancy['key_skills'])
                vacancies.append(vacancy)
        
            return vacancies

    # // Chg_VAC_RECENT_1509: быстрый доступ к последним вакансиям для веб-панели
    def get_recent_vacancies(self, limit: int = 20) -> List[Dict]:
        """Получение последних вакансий из БД v4"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, hh_id, title, company, area, published_at, url, filter_id, created_at
                FROM vacancies
                ORDER BY COALESCE(created_at, 0) DESC, published_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_vacancy_processed(self, vacancy_id: str):
        """Отметить вакансию как обработанную"""
        with self.get_connection() as conn:
            # // Chg_VAC_PROCESS_1509: устанавливаем processed_at и updated_at в unix timestamp
            now_ts = time.time()
            conn.execute("""
                UPDATE vacancies 
                SET is_processed = 1, processed_at = ?, updated_at = ?
                WHERE id = ?
            """, (now_ts, now_ts, vacancy_id))
            conn.commit()

    # // Chg_TASKS_API_1509: метод для получения задач (для web/api)
    def get_tasks(self, status: Optional[object] = None, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Получить список задач с пагинацией"""
        with self.get_connection() as conn:
            query = "SELECT * FROM tasks"
            params: List = []
            if status:
                # // Chg_TASKS_API_1509: поддержка нескольких статусов (IN (...))
                if isinstance(status, (list, tuple, set)):
                    placeholders = ",".join(["?"] * len(status))
                    query += f" WHERE status IN ({placeholders})"
                    params.extend(list(status))
                else:
                    query += " WHERE status = ?"
                    params.append(status)
            query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def save_plugin_result(self, vacancy_id: str, plugin_name: str, result: Dict):
        """Сохранение результата работы плагина"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO plugin_results (vacancy_id, plugin_name, result_json)
                VALUES (?, ?, ?)
            """, (vacancy_id, plugin_name, json.dumps(result, ensure_ascii=False)))
            conn.commit()
    
    def get_vacancy_count_by_filter(self) -> Dict[str, int]:
        """Статистика вакансий по фильтрам"""
        with self.get_connection() as conn:
            # // Chg_STATS_TIME_1509: корректное окно по unix timestamp
            cursor = conn.execute("""
                SELECT 
                    COALESCE(filter_id, 'unknown') as filter_id,
                    COUNT(*) as count
                FROM vacancies 
                WHERE created_at > strftime('%s','now','-7 day')
                GROUP BY filter_id
                ORDER BY count DESC
            """)
            
            return {row['filter_id']: row['count'] for row in cursor.fetchall()}

    # // Chg_V3_COMPAT_2509: методы-замены для функционала из v3 (VacancyDatabase)
    def vacuum(self) -> None:
        """VACUUM БД"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")

    def cleanup_old_records(self, cutoff_date: datetime) -> int:
        """Удаление старых записей задач, завершённых до cutoff_date"""
        try:
            cutoff_ts = cutoff_date.timestamp()
        except Exception:
            cutoff_ts = time.time() - 7*24*3600
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                DELETE FROM tasks
                WHERE status IN ('completed','failed')
                  AND COALESCE(finished_at, 0) < ?
                """,
                (cutoff_ts,)
            )
            deleted = cur.rowcount
            conn.commit()
        return deleted or 0

    def get_missing_employer_ids(self, limit: int = 1000) -> List[str]:
        """Список employer_id из vacancies, отсутствующих в employers"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT v.employer_id
                FROM vacancies v
                WHERE v.employer_id IS NOT NULL AND v.employer_id != ''
                  AND NOT EXISTS (
                    SELECT 1 FROM employers e WHERE e.hh_id = v.employer_id
                  )
                LIMIT ?
                """,
                (limit,)
            )
            return [row[0] for row in cursor.fetchall()]

    def save_employer(self, employer_data: Dict) -> Optional[int]:
        """Upsert работодателя по hh_id"""
        try:
            hh_id = str(employer_data.get('id')) if employer_data.get('id') is not None else None
            name = employer_data.get('name') or employer_data.get('alternate_url') or ''
            url = employer_data.get('alternate_url') or employer_data.get('site_url') or ''
            raw_json = json.dumps(employer_data, ensure_ascii=False)
            now_ts = time.time()
            with self.get_connection() as conn:
                # Проверка на существование
                row = conn.execute("SELECT id FROM employers WHERE hh_id = ?", (hh_id,)).fetchone()
                if row:
                    conn.execute(
                        "UPDATE employers SET name=?, url=?, raw_json=?, updated_at=? WHERE hh_id=?",
                        (name, url, raw_json, now_ts, hh_id)
                    )
                    conn.commit()
                    return row['id'] if isinstance(row, sqlite3.Row) else row[0]
                else:
                    cur = conn.execute(
                        "INSERT INTO employers (hh_id, name, url, raw_json, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                        (hh_id, name, url, raw_json, now_ts, now_ts)
                    )
                    conn.commit()
                    return cur.lastrowid
        except Exception:
            self.logger.exception("save_employer failed")
            return None

    def get_unsynced_vacancy_ids(self, limit: int = 1000) -> List[int]:
        """ID вакансий, не синхронизированных с Host2"""
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT id FROM vacancies WHERE COALESCE(synced_host2,0)=0 ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [row[0] for row in cur.fetchall()]

    def mark_vacancies_synced(self, vacancy_ids: List[int]) -> int:
        """Пометить вакансии как синхронизированные с Host2"""
        if not vacancy_ids:
            return 0
        placeholders = ",".join(["?"]*len(vacancy_ids))
        with self.get_connection() as conn:
            cur = conn.execute(
                f"UPDATE vacancies SET synced_host2=1, updated_at=strftime('%s','now') WHERE id IN ({placeholders})",
                vacancy_ids
            )
            conn.commit()
            return cur.rowcount or 0

    def get_unanalyzed_vacancies(self, limit: int = 50, new_only: bool = True) -> List[Dict]:
        """Вакансии без результата анализа host3_analysis"""
        with self.get_connection() as conn:
            where = ""
            params: List[Any] = []  # type: ignore
            if new_only:
                where = "WHERE v.created_at > strftime('%s','now','-7 day')"
            sql = f"""
                SELECT v.* FROM vacancies v
                LEFT JOIN plugin_results p ON p.vacancy_id = v.id AND p.plugin_name = 'host3_analysis'
                {where}
                AND p.id IS NULL
                ORDER BY v.created_at DESC
                LIMIT ?
            """
            params.append(limit)
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def save_analysis_result(self, vacancy_id: int, analysis: Dict) -> None:
        """Сохранить результат анализа как plugin_result"""
        try:
            self.save_plugin_result(str(vacancy_id), 'host3_analysis', analysis)
        except Exception:
            self.logger.exception("save_analysis_result failed")

    def save_system_health(self, health_data: Dict) -> None:
        """Сохранить метрики здоровья системы"""
        try:
            ts = health_data.get('timestamp')
            if isinstance(ts, str):
                try:
                    # Пытаемся распарсить ISO и перевести в UNIX
                    ts_val = datetime.fromisoformat(ts).timestamp()
                except Exception:
                    ts_val = time.time()
            else:
                ts_val = time.time()
            host_status_json = json.dumps(health_data.get('host_status', {}), ensure_ascii=False)
            with self.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO system_health (ts, cpu_percent, memory_percent, disk_percent, database_size_mb, active_tasks, host_status_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ts_val,
                        float(health_data.get('cpu_percent', 0.0)),
                        float(health_data.get('memory_percent', 0.0)),
                        float(health_data.get('disk_percent', 0.0)),
                        float(health_data.get('database_size_mb', 0.0)),
                        int(health_data.get('active_tasks', 0)),
                        host_status_json
                    )
                )
                conn.commit()
        except Exception:
            self.logger.exception("save_system_health failed")

    def get_vacancy_stats(self) -> Dict:
        """Возвращает блок статистики вакансий (удобно для CLI)"""
        try:
            return self.get_stats().get('vacancies', {})
        except Exception:
            return {}

    def get_combined_changes_stats(self, days: int = 7) -> Dict:
        """Сводная статистика изменений (упрощённая версия v3)"""
        days = max(1, int(days))
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM vacancies WHERE created_at > strftime('%s','now', ?)",
                (f'-{days} day',)
            ).fetchone()
            new_vacancies = row['cnt'] if row else 0
            # В v4 нет версионирования — считаем новые версии = 0
            result = {
                'vacancies': {
                    'new_vacancies': new_vacancies,
                    'new_versions': 0,
                    'duplicates_skipped': 0,
                    'efficiency_percentage': 100 if new_vacancies else 0,
                    'total_changes': new_vacancies
                },
                'employers': {
                    'total_changes': conn.execute("SELECT COUNT(*) FROM employers WHERE created_at > strftime('%s','now', ?)", (f'-{days} day',)).fetchone()[0] if True else 0
                },
                'summary': {
                    'total_operations': new_vacancies
                }
            }
            return result
