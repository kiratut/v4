# Модели данных для HH Tool v4
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import hashlib
import json
import psutil
import platform


@dataclass
class Vacancy:
    """Модель вакансии v3"""
    hh_id: str
    title: str
    employer_name: str
    employer_id: str
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    currency: Optional[str] = None
    experience: Optional[str] = None
    schedule: Optional[str] = None
    schedule_id: Optional[str] = None  # Для классификатора
    employment: Optional[str] = None
    description: Optional[str] = None
    snippet_description: Optional[str] = None  # // Chg_013_0909 Добавлено поле snippet_description для совместимости
    key_skills: Optional[List[str]] = None
    area: Optional[str] = None  # // Chg_012_0909 Добавлено поле area для совместимости
    area_name: Optional[str] = None
    published_at: Optional[str] = None
    url: Optional[str] = None
    
    # Поля для плагинов
    work_format_classified: Optional[str] = None  # REMOTE/ON_SITE/HYBRID
    relevance_score: Optional[float] = None       # 0-10 от анализатора
    analysis_summary: Optional[str] = None        # Краткий анализ
    match_status: Optional[str] = None            # matched/rejected/pending
    
    # Системные поля
    id: Optional[int] = None
    content_hash: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    # // Chg_VER_VAC_2009: Поля версионирования
    version: Optional[int] = None
    prev_version_id: Optional[int] = None
    
    def __post_init__(self):
        if self.content_hash is None:
            self.content_hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        Улучшенный хеш контента для дедупликации v4
        
        // Chg_HASH_1909: Enhanced content hashing with SHA256 and normalized fields
        """
        # Нормализованные ключевые поля для дедупликации
        content_parts = [
            # Основная информация
            (self.title or "").strip().lower(),
            (self.employer_name or "").strip().lower(),
            
            # Зарплатная вилка (нормализованная)
            str(self.salary_from or 0),
            str(self.salary_to or 0),
            (self.currency or "RUR").upper(),
            
            # Условия работы
            (self.experience or "").lower(),
            (self.schedule or "").lower(), 
            (self.employment or "").lower(),
            
            # Навыки (отсортированные)
            json.dumps(sorted([s.strip().lower() for s in (self.key_skills or [])]), ensure_ascii=False),
            
            # Описание (первые 500 символов для стабильности)
            (self.description or "")[:500].strip().lower(),
            
            # Локация
            (self.area or "").strip().lower()
        ]
        
        # Объединение с разделителем
        content = "|".join(content_parts)
        
        # SHA256 для лучшей безопасности и меньших коллизий
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:32]  # First 32 chars for compactness


@dataclass 
class PluginResult:
    """Результат выполнения плагина"""
    status: str  # completed, failed, skipped
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    execution_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginContext:
    """Контекст выполнения плагина с доступом к результатам других плагинов"""
    vacancy: Vacancy
    session_results: Dict[str, PluginResult]
    persistent_results: Dict[str, PluginResult]
    config: Dict[str, Any] = field(default_factory=dict)
    
    def get_result(self, plugin_name: str, fallback_to_db: bool = True) -> Optional[PluginResult]:
        """Получить результат другого плагина"""
        # Сначала ищем в памяти (текущая сессия)
        if plugin_name in self.session_results:
            return self.session_results[plugin_name]
        
        # Потом в БД (предыдущие запуски)
        if fallback_to_db and plugin_name in self.persistent_results:
            return self.persistent_results[plugin_name]
            
        return None
    
    def get_data(self, plugin_name: str, key: str, default=None):
        """Получить конкретное значение из результата плагина"""
        result = self.get_result(plugin_name)
        if result and result.status == 'completed':
            return result.data.get(key, default)
        return default


@dataclass
class ProcessStatus:
    """Статус выполнения процесса для веб-мониторинга"""
    process_id: str
    name: str
    status: str  # running, completed, failed, paused
    started_at: str
    progress: float  # 0-100
    total_items: int
    processed_items: int
    current_item: Optional[str] = None
    eta_minutes: Optional[int] = None
    speed_per_minute: Optional[float] = None
    errors_count: int = 0
    last_error: Optional[str] = None


@dataclass
class Employer:
    """Модель работодателя"""
    hh_id: str
    name: str
    description: Optional[str] = None
    site_url: Optional[str] = None
    logo_url: Optional[str] = None
    area_name: Optional[str] = None
    vacancies_url: Optional[str] = None
    
    # Поля версионирования
    id: Optional[int] = None
    version: int = 1
    content_hash: Optional[str] = None
    prev_version_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def calculate_hash(self) -> str:
        """Хеш контента для дедупликации"""
        content_parts = [
            self.name or "",
            self.description or "",
            self.site_url or "",
            self.area_name or ""
        ]
        content = "|".join(content_parts)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()


class PathManager:
    """Менеджер кроссплатформенных путей"""
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or Path.cwd()
        self.is_windows = platform.system() == "Windows"
    
    def get_data_path(self, filename: str) -> Path:
        """Получить путь к файлу данных"""
        return self.base_path / "data" / filename
    
    def get_config_path(self, filename: str) -> Path:
        """Получить путь к конфигурационному файлу"""
        return self.base_path / "config" / filename
    
    def get_logs_path(self, filename: str) -> Path:
        """Получить путь к лог-файлу"""
        return self.base_path / "logs" / filename
    
    def ensure_directory(self, path: Path) -> Path:
        """Создать директорию если не существует"""
        path.mkdir(parents=True, exist_ok=True)
        return path


class Host2Client:
    """Заглушка клиента для Хоста 2 (PostgreSQL)"""
    
    def __init__(self, enabled: bool = False, config: Optional[Dict] = None):
        self.enabled = enabled
        self.config = config or {}
    
    def sync_vacancies(self, vacancies: List[Dict]) -> Dict:
        """Синхронизация вакансий с PostgreSQL"""
        if not self.enabled:
            return {
                "status": "skipped", 
                "message": "Host 2 disabled",
                "synced": 0
            }
        
        # TODO: Реальная реализация для PostgreSQL
        return {
            "status": "success",
            "synced": len(vacancies),
            "message": f"Synced {len(vacancies)} vacancies"
        }
    
    def get_shared_stats(self) -> Dict:
        """Получить общую статистику из PostgreSQL"""
        if not self.enabled:
            return {"status": "disabled"}
        
        # TODO: Реальная реализация
        return {
            "status": "enabled",
            "total_vacancies": 0,
            "total_employers": 0
        }


class Host3Client:
    """Заглушка клиента для Хоста 3 (LLM)"""
    
    def __init__(self, enabled: bool = False, config: Optional[Dict] = None):
        self.enabled = enabled
        self.config = config or {}
    
    def classify_vacancy(self, vacancy: Dict) -> Dict:
        """Классификация вакансии через LLM"""
        if not self.enabled:
            return {
                "status": "skipped",
                "message": "Host 3 disabled",
                "work_format": "UNKNOWN",
                "relevance_score": 0.0
            }
        
        # TODO: Реальная реализация LLM классификации
        return {
            "status": "success",
            "work_format": "UNKNOWN",
            "relevance_score": 5.0,
            "analysis_summary": "Требует LLM обработки"
        }
    
    def generate_cover_letter(self, vacancy: Dict, profile: Dict) -> Dict:
        """Генерация сопроводительного письма"""
        if not self.enabled:
            return {
                "status": "skipped",
                "message": "Host 3 disabled"
            }
        
        # TODO: Реальная реализация генерации письма
        return {
            "status": "success",
            "cover_letter": "Уважаемый работодатель, я заинтересован в данной позиции.",
            "confidence": 0.7
        }


class SystemMonitor:
    """
    Расширенный монитор системных ресурсов и здоровья приложения v4
    
    // Chg_MONITOR_1909: Enhanced monitoring with detailed metrics and self-diagnostics
    """
    
    def __init__(self, project_root: Optional[Path] = None):
        self.start_time = datetime.now()
        self.project_root = project_root or Path.cwd()
        self.thresholds = {
            'cpu_high': 80.0,
            'memory_high': 85.0,
            'disk_high': 90.0,
            'response_time_high': 5.0,  # seconds
            'db_size_high': 1000,  # MB
        }
        self._load_averages = []  # For calculating load average on Windows
        
    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Получить полный набор системных метрик"""
        try:
            # Basic system metrics
            cpu_data = self._get_cpu_metrics()
            memory_data = self._get_memory_metrics()
            disk_data = self._get_disk_metrics()
            
            # Application-specific metrics
            process_data = self._get_process_metrics()
            database_data = self._get_database_metrics()
            network_data = self._get_network_metrics()
            
            # Health checks
            health_checks = self._perform_health_checks()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds(),
                'system': {
                    'cpu': cpu_data,
                    'memory': memory_data,
                    'disk': disk_data,
                    'network': network_data
                },
                'application': {
                    'process': process_data,
                    'database': database_data,
                    'health_checks': health_checks
                },
                'alerts': self._generate_alerts(cpu_data, memory_data, disk_data, database_data)
            }
            
        except Exception as e:
            return {
                'error': f"Failed to collect metrics: {e}",
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_cpu_metrics(self) -> Dict[str, Any]:
        """Детальная информация о CPU"""
        try:
            # Get per-CPU percentages
            cpu_percents = psutil.cpu_percent(interval=0.1, percpu=True)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            
            # Calculate load average (simulate on Windows)
            current_load = psutil.cpu_percent(interval=0.1)
            self._load_averages.append(current_load)
            if len(self._load_averages) > 15:  # Keep last 15 samples (15 minutes if called every minute)
                self._load_averages.pop(0)
            
            return {
                'percent_total': round(sum(cpu_percents) / len(cpu_percents), 2),
                'percent_per_cpu': [round(p, 1) for p in cpu_percents],
                'count_logical': cpu_count,
                'count_physical': psutil.cpu_count(logical=False),
                'frequency_current': round(cpu_freq.current, 1) if cpu_freq else None,
                'frequency_max': round(cpu_freq.max, 1) if cpu_freq else None,
                'load_average': {
                    '1min': round(sum(self._load_averages[-1:]) / max(1, len(self._load_averages[-1:])), 2),
                    '5min': round(sum(self._load_averages[-5:]) / max(1, len(self._load_averages[-5:])), 2),
                    '15min': round(sum(self._load_averages) / max(1, len(self._load_averages)), 2)
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_memory_metrics(self) -> Dict[str, Any]:
        """Детальная информация о памяти"""
        try:
            virtual_mem = psutil.virtual_memory()
            swap_mem = psutil.swap_memory()
            
            return {
                'virtual': {
                    'total_mb': round(virtual_mem.total / (1024**2), 1),
                    'available_mb': round(virtual_mem.available / (1024**2), 1),
                    'used_mb': round(virtual_mem.used / (1024**2), 1),
                    'percent': round(virtual_mem.percent, 1),
                    'cached_mb': round(getattr(virtual_mem, 'cached', 0) / (1024**2), 1),
                    'buffers_mb': round(getattr(virtual_mem, 'buffers', 0) / (1024**2), 1)
                },
                'swap': {
                    'total_mb': round(swap_mem.total / (1024**2), 1),
                    'used_mb': round(swap_mem.used / (1024**2), 1),
                    'percent': round(swap_mem.percent, 1)
                }
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """Детальная информация о дисках"""
        try:
            disk_partitions = psutil.disk_partitions()
            disk_data = {}
            
            for partition in disk_partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_data[partition.device] = {
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percent': round((usage.used / usage.total) * 100, 1)
                    }
                except (PermissionError, OSError):
                    continue  # Skip inaccessible partitions
            
            # Project-specific directories
            project_usage = self._get_project_disk_usage()
            
            return {
                'partitions': disk_data,
                'project': project_usage
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_project_disk_usage(self) -> Dict[str, Any]:
        """Размер файлов проекта по папкам"""
        try:
            folders_to_check = ['data', 'logs', 'config', 'docs']
            usage = {}
            
            for folder in folders_to_check:
                folder_path = self.project_root / folder
                if folder_path.exists():
                    total_size = sum(
                        f.stat().st_size for f in folder_path.rglob('*') 
                        if f.is_file()
                    )
                    file_count = sum(1 for f in folder_path.rglob('*') if f.is_file())
                    usage[folder] = {
                        'size_mb': round(total_size / (1024**2), 2),
                        'file_count': file_count
                    }
                else:
                    usage[folder] = {'size_mb': 0, 'file_count': 0}
            
            return usage
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """Сетевая статистика"""
        try:
            net_io = psutil.net_io_counters()
            net_connections = len(psutil.net_connections())
            
            return {
                'bytes_sent_mb': round(net_io.bytes_sent / (1024**2), 2),
                'bytes_recv_mb': round(net_io.bytes_recv / (1024**2), 2),
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errors_in': net_io.errin,
                'errors_out': net_io.errout,
                'connections_count': net_connections
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_process_metrics(self) -> Dict[str, Any]:
        """Детальная информация о процессах приложения"""
        try:
            current_process = psutil.Process()
            
            # Find related processes (dispatcher, web server)
            related_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'cli_v4.py' in cmdline or 'dispatcher' in cmdline.lower():
                        proc_info = psutil.Process(proc.info['pid'])
                        related_processes.append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'cpu_percent': proc_info.cpu_percent(),
                            'memory_mb': round(proc_info.memory_info().rss / (1024**2), 2),
                            'status': proc_info.status(),
                            'cmdline': ' '.join(proc.info['cmdline'][:3])  # First 3 args
                        })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'current': {
                    'pid': current_process.pid,
                    'name': current_process.name(),
                    'cpu_percent': current_process.cpu_percent(),
                    'memory_mb': round(current_process.memory_info().rss / (1024**2), 2),
                    'memory_percent': round(current_process.memory_percent(), 2),
                    'num_threads': current_process.num_threads(),
                    'status': current_process.status(),
                    'open_files': len(current_process.open_files()),
                    'connections': len(current_process.connections())
                },
                'related_processes': related_processes
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_database_metrics(self) -> Dict[str, Any]:
        """Метрики базы данных"""
        try:
            import sqlite3
            
            db_path = self.project_root / "data" / "hh_v4.sqlite3"
            if not db_path.exists():
                return {'status': 'missing', 'path': str(db_path)}
            
            # File size
            db_size_mb = round(db_path.stat().st_size / (1024**2), 2)
            
            # Connect and get table stats
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Table sizes
            tables_info = {}
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for (table_name,) in cursor.fetchall():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                tables_info[table_name] = {'record_count': count}
            
            # WAL mode check
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            
            # Page info
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'status': 'connected',
                'file_size_mb': db_size_mb,
                'journal_mode': journal_mode,
                'page_count': page_count,
                'page_size': page_size,
                'tables': tables_info,
                'last_modified': datetime.fromtimestamp(db_path.stat().st_mtime).isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def _perform_health_checks(self) -> Dict[str, Dict[str, Any]]:
        """Выполнить проверки здоровья системы"""
        checks = {}
        
        # Database connectivity
        checks['database'] = self._check_database_health()
        
        # Config files existence
        checks['config_files'] = self._check_config_files()
        
        # Log files status
        checks['log_files'] = self._check_log_files()
        
        # API connectivity (basic)
        checks['api_connectivity'] = self._check_api_connectivity()
        
        return checks
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Проверить здоровье базы данных"""
        try:
            import sqlite3
            db_path = self.project_root / "data" / "hh_v4.sqlite3"
            
            if not db_path.exists():
                return {'status': 'fail', 'message': 'Database file not found'}
            
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Quick integrity check
            cursor.execute("PRAGMA integrity_check")
            integrity = cursor.fetchone()[0]
            
            # Check critical tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['vacancies', 'tasks']
            missing_tables = [t for t in required_tables if t not in tables]
            
            conn.close()
            
            if missing_tables:
                return {
                    'status': 'warning',
                    'message': f'Missing tables: {missing_tables}',
                    'integrity': integrity
                }
            
            return {
                'status': 'pass',
                'message': 'Database healthy',
                'integrity': integrity,
                'tables_count': len(tables)
            }
            
        except Exception as e:
            return {'status': 'fail', 'message': f'Database check failed: {e}'}
    
    def _check_config_files(self) -> Dict[str, Any]:
        """Проверить наличие конфигурационных файлов"""
        try:
            config_files = [
                'config/config_v4.json',
                'config/filters.json'
            ]
            
            missing = []
            existing = []
            
            for config_file in config_files:
                file_path = self.project_root / config_file
                if file_path.exists():
                    existing.append(config_file)
                else:
                    missing.append(config_file)
            
            if missing:
                return {
                    'status': 'warning',
                    'message': f'Missing configs: {missing}',
                    'existing': existing
                }
            
            return {
                'status': 'pass',
                'message': 'All config files present',
                'existing': existing
            }
            
        except Exception as e:
            return {'status': 'fail', 'message': f'Config check failed: {e}'}
    
    def _check_log_files(self) -> Dict[str, Any]:
        """Проверить состояние лог файлов"""
        try:
            logs_dir = self.project_root / "logs"
            if not logs_dir.exists():
                return {'status': 'warning', 'message': 'Logs directory not found'}
            
            log_files = list(logs_dir.glob('*.log'))
            large_logs = []
            
            for log_file in log_files:
                size_mb = log_file.stat().st_size / (1024**2)
                if size_mb > 100:  # 100MB threshold
                    large_logs.append({
                        'file': log_file.name,
                        'size_mb': round(size_mb, 2)
                    })
            
            return {
                'status': 'pass' if not large_logs else 'warning',
                'message': f'Found {len(log_files)} log files',
                'log_files_count': len(log_files),
                'large_logs': large_logs
            }
            
        except Exception as e:
            return {'status': 'fail', 'message': f'Log check failed: {e}'}
    
    def _check_api_connectivity(self) -> Dict[str, Any]:
        """Базовая проверка доступности HH API"""
        try:
            import requests
            
            # Quick HEAD request to HH API
            response = requests.head('https://api.hh.ru/vacancies', timeout=5)
            
            if response.status_code in [200, 400]:  # 400 is expected for HEAD without params
                return {
                    'status': 'pass',
                    'message': 'HH API accessible',
                    'response_code': response.status_code,
                    'response_time_ms': round(response.elapsed.total_seconds() * 1000, 1)
                }
            else:
                return {
                    'status': 'warning',
                    'message': f'Unexpected response code: {response.status_code}',
                    'response_code': response.status_code
                }
                
        except Exception as e:
            return {
                'status': 'fail',
                'message': f'API connectivity failed: {e}'
            }
    
    def _generate_alerts(self, cpu_data: Dict, memory_data: Dict, disk_data: Dict, db_data: Dict) -> List[Dict[str, Any]]:
        """Генерировать алерты на основе пороговых значений"""
        alerts = []
        
        # CPU alerts
        if cpu_data.get('percent_total', 0) > self.thresholds['cpu_high']:
            alerts.append({
                'level': 'warning',
                'component': 'cpu',
                'message': f"High CPU usage: {cpu_data['percent_total']}%",
                'threshold': self.thresholds['cpu_high']
            })
        
        # Memory alerts
        memory_percent = memory_data.get('virtual', {}).get('percent', 0)
        if memory_percent > self.thresholds['memory_high']:
            alerts.append({
                'level': 'warning',
                'component': 'memory',
                'message': f"High memory usage: {memory_percent}%",
                'threshold': self.thresholds['memory_high']
            })
        
        # Disk alerts
        for device, disk_info in disk_data.get('partitions', {}).items():
            if disk_info.get('percent', 0) > self.thresholds['disk_high']:
                alerts.append({
                    'level': 'critical',
                    'component': 'disk',
                    'message': f"High disk usage on {device}: {disk_info['percent']}%",
                    'threshold': self.thresholds['disk_high']
                })
        
        # Database alerts  
        db_size = db_data.get('file_size_mb', 0)
        if db_size > self.thresholds['db_size_high']:
            alerts.append({
                'level': 'info',
                'component': 'database',
                'message': f"Large database file: {db_size}MB",
                'threshold': self.thresholds['db_size_high']
            })
        
        return alerts
    
    def get_quick_status(self) -> Dict[str, str]:
        """Быстрая проверка статуса системы"""
        try:
            cpu = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory().percent
            
            # Simple status determination
            if cpu > 90 or memory > 90:
                status = 'critical'
            elif cpu > 70 or memory > 70:
                status = 'warning'
            else:
                status = 'healthy'
            
            return {
                'overall_status': status,
                'cpu_percent': round(cpu, 1),
                'memory_percent': round(memory, 1),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'overall_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
