"""
HH Tool v4 - Enhanced Web Interface with FastAPI
Улучшенная веб-панель на основе v3 с WebSocket поддержкой, системными метриками и расширенной функциональностью
"""

import json
import asyncio
import time
import glob
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import psutil
import uvicorn
import threading
from logging.handlers import RotatingFileHandler
from core.db_log_handler import DbLogHandler
from core.config_manager import get_config_manager

# Импорты модулей v4
from core.task_database import TaskDatabase

app = FastAPI(title="HH Tool v4 Dashboard", version="4.0.0")

# Настройка статических файлов и шаблонов
templates = Jinja2Templates(directory="web/templates")
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# // Chg_WEB_LOG_INIT_2109 + Chg_LOG_CFG_2509: инициализация логирования по ConfigManager
try:
    Path('logs').mkdir(exist_ok=True)
    cfgm = get_config_manager()
    logging_cfg = cfgm.get_logging_settings()
    log_file = logging_cfg.get('file_path', 'logs/app.log')
    max_bytes = int(logging_cfg.get('max_size_mb', 100)) * 1024 * 1024
    backup_count = int(logging_cfg.get('backup_count', 3))
    level = getattr(logging, str(logging_cfg.get('level', 'INFO')).upper(), logging.INFO)
    console_enabled = bool(logging_cfg.get('console_enabled', True))
    db_enabled = bool(logging_cfg.get('db_enabled', False))

    root = logging.getLogger()
    # Добавляем файловый обработчик, если его ещё нет на тот же путь
    has_file = any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '') == str(Path(log_file)) for h in root.handlers)
    if not has_file:
        fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        fmt = logging.Formatter(logging_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        fh.setFormatter(fmt)
        root.addHandler(fh)
    if console_enabled and not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(logging_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))
        root.addHandler(sh)
    if db_enabled and not any(isinstance(h, DbLogHandler) for h in root.handlers):
        dbh = DbLogHandler()
        dbh.setFormatter(logging.Formatter(logging_cfg.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')))
        root.addHandler(dbh)
    root.setLevel(level)
except Exception:
    pass

# // Chg_STATS_CACHE_1509: cache last good stats/system info to avoid UI flicker (start)
_LAST_GOOD_SYSTEM_INFO: Dict[str, Any] = {}
_LAST_GOOD_DB_SIZE_BYTES: Optional[int] = None
# // Chg_STATS_CACHE_1509: cache last good stats/system info (end)

# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                disconnected.append(connection)
        # Удаляем неактивные соединения
        for conn in disconnected:
            try:
                self.active_connections.remove(conn)
            except ValueError:
                pass

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def control_panel(request: Request):
    """Главная страница (новая панель-пульт)"""
    # // Chg_PANEL_ROUTE_2409: новая главная -> control_panel.html + server-side unix_time
    return templates.TemplateResponse("control_panel.html", {"request": request, "unix_time": int(time.time())})

@app.get("/dashboard-old", response_class=HTMLResponse)
async def dashboard_legacy(request: Request):
    """Старая главная страница дашборда (legacy)"""
    # // Chg_PANEL_ROUTE_2409: сохранили доступ к старому шаблону
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/version")
async def get_version():
    """API: Версия API"""
    return {"version": app.version}

@app.get("/api/stats")
async def get_stats():
    """API получения статистики БД"""
    try:
        task_db = TaskDatabase()
        # Получаем агрегированную статистику в формате v4 БД
        stats = task_db.get_stats()
        
        # Надёжное вычисление размера БД: PRAGMA -> os.path.getsize -> сумма файлов data/*.sqlite*
        db_size_bytes: int = 0
        try:
            with task_db.get_connection() as conn:
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size_bytes = int(page_count) * int(page_size)
        except Exception:
            try:
                # Фолбэк: размер основного файла
                main_db = Path(task_db.db_path)
                if main_db.exists():
                    db_size_bytes = os.path.getsize(main_db)
                else:
                    raise FileNotFoundError
            except Exception:
                # Фолбэк: сумма по маске
                try:
                    db_files = glob.glob("data/*.sqlite*")
                    db_size_bytes = sum(os.path.getsize(f) for f in db_files if os.path.exists(f))
                except Exception:
                    db_size_bytes = 0

        sys_info = _get_system_info()
        # // Chg_WORKERS_1509: считаем активных воркеров и читаем конфигурацию
        active_workers = 0
        try:
            with task_db.get_connection() as conn:
                roww = conn.execute(
                    "SELECT COUNT(DISTINCT worker_id) AS cnt FROM tasks WHERE status='running' AND worker_id IS NOT NULL"
                ).fetchone()
                active_workers = roww['cnt'] if roww else 0
        except Exception:
            active_workers = 0
        workers_configured = None
        try:
            cfg_path = Path('config/config_v4.json')
            if cfg_path.exists():
                cfg = json.load(open(cfg_path, 'r', encoding='utf-8'))
                workers_configured = ((cfg.get('task_dispatcher') or {}).get('max_workers'))
        except Exception:
            workers_configured = None
        # Объединяем метрики системы с размером БД и информацией о воркерах
        sys_info_merged = {**sys_info, "db_size": db_size_bytes, "active_workers": active_workers, "workers_configured": workers_configured}

        # Обновляем кэш только если данные валидны
        global _LAST_GOOD_SYSTEM_INFO, _LAST_GOOD_DB_SIZE_BYTES
        if sys_info_merged:
            _LAST_GOOD_SYSTEM_INFO = sys_info_merged
        if isinstance(db_size_bytes, int) and db_size_bytes >= 0:
            _LAST_GOOD_DB_SIZE_BYTES = db_size_bytes

        stats["system_info"] = sys_info_merged
        stats["status"] = "ok"
        return stats
    except Exception as e:
        print(f"Ошибка получения статистики: {e}")
        # Фолбэк: возвращаем последние валидные метрики вместо нулей
        fallback_sys = _LAST_GOOD_SYSTEM_INFO or {"db_size": _LAST_GOOD_DB_SIZE_BYTES or 0}
        return {
            "tasks": {},
            "vacancies": {"total_vacancies": 0, "processed_vacancies": 0, "today_vacancies": 0},
            "timestamp": datetime.now().isoformat(),
            "system_info": fallback_sys,
            "status": "degraded",
            "error": str(e)
        }

@app.get("/api/stats/system_health")
async def stats_system_health():
    """API: Системное здоровье (CPU/Mem/Disk)"""
    info = _get_system_info()
    return {
        "cpu_percent": info.get("cpu_percent", 0),
        "memory_percent": info.get("memory_percent", 0),
        "disk_percent": info.get("disk_percent", 0),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/stats/api_status")
async def stats_api_status():
    """API: Статус доступности внешнего HH API (демо)"""
    return {"status": "200 OK", "bans": 0, "last_check": datetime.now().isoformat()}

@app.get("/api/tasks")
async def get_tasks(
    status: Optional[str] = None, 
    limit: int = 50,
    offset: int = 0
):
    """API получения списка задач"""
    task_db = TaskDatabase()
    # // Chg_TASKS_API_1509: поддержка CSV статусов (напр. running,pending)
    status_param: Optional[object] = None
    if status:
        status_param = [s.strip() for s in status.split(',') if s.strip()]
        if len(status_param) == 1:
            status_param = status_param[0]
    tasks = task_db.get_tasks(status=status_param, limit=limit, offset=offset)
    
    # Форматирование времени
    for task in tasks:
        if task.get('created_at'):
            try:
                if task['created_at'] > 1000000000:
                    task['created_at_formatted'] = datetime.fromtimestamp(task['created_at']).isoformat()
                else:
                    unix_time = (task['created_at'] - 2440587.5) * 86400
                    task['created_at_formatted'] = datetime.fromtimestamp(unix_time).isoformat()
            except:
                task['created_at_formatted'] = 'Invalid'
    
    return {"tasks": tasks, "total": len(tasks)}

@app.get("/api/task/{task_id}")
async def get_task_detail(task_id: str):
    """API получения детальной информации о задаче"""
    task_db = TaskDatabase()
    task = task_db.get_task(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

@app.get("/api/vacancies/recent")
async def get_recent_vacancies(limit: int = 20):
    """API получения последних вакансий"""
    # // Chg_API_1509: используем v4 TaskDatabase и маппим поля под UI
    db = TaskDatabase()
    items = db.get_recent_vacancies(limit=limit)
    # Маппинг к ожидаемым ключам UI (dashboard.js)
    mapped = []
    for v in items:
        mapped.append({
            "id": v.get("id"),
            "hh_id": v.get("hh_id"),
            "name": v.get("title"),
            "employer_name": v.get("company"),
            "area_name": v.get("area"),
            "published_at": v.get("published_at"),
            "url": v.get("url"),
            "salary_text": None
        })
    return {"vacancies": mapped}

@app.get("/api/filters")
async def get_filters():
    """API: Список фильтров из config/filters.json"""
    try:
        filters_path = Path("config/filters.json")
        if filters_path.exists():
            with open(filters_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            # // Chg_API_1509: нормализуем структуру и признак активности под UI
            if isinstance(raw, dict) and "filters" in raw:
                items = raw["filters"]
            elif isinstance(raw, dict):
                items = list(raw.values())
            else:
                items = raw
            for item in items:
                if "active" not in item:
                    item["active"] = item.get("enabled", True)
            return {"filters": items}
        return {"filters": []}
    except Exception as e:
        return {"error": str(e), "filters": []}

@app.get("/api/system")
async def get_system():
    """API: Системные метрики (память/CPU/диск) как в v3"""
    return _get_system_info()

@app.get("/api/processes")
async def get_processes():
    """API: Активные процессы (аналог process_status v3)"""
    return {"active_processes": _get_active_processes()}

@app.get("/api/enhanced")
async def get_enhanced_metrics():
    """API: Расширенные метрики из логов (как в v3)"""
    return _load_enhanced_metrics()

@app.post("/api/tests/functional")
async def run_functional_tests():
    """API: Запуск функциональных тестов"""
    import subprocess
    import sys
    from pathlib import Path
    
    try:
        logging.info("web_api_test_start: functional")
        # Запускаем functional_test_runner.py
        result = subprocess.run([
            sys.executable, 'tests/functional_test_runner.py', '--json'
        ], capture_output=True, text=True, timeout=300, cwd=Path.cwd())
        
        if result.returncode == 0:
            # Пытаемся найти JSON отчет
            import glob
            json_files = glob.glob('reports/functional_test_report_*.json')
            if json_files:
                latest_report = max(json_files, key=os.path.getctime)
                with open(latest_report, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                try:
                    sr = report_data.get('success_rate', 0)
                    total = (report_data.get('statistics') or {}).get('total', 0)
                    passed = (report_data.get('statistics') or {}).get('passed', 0)
                    logging.info(f"web_api_test_finish: functional success_rate={sr} passed={passed}/{total}")
                except Exception:
                    pass
                return report_data
            else:
                # Если JSON файла нет, возвращаем базовый результат
                res = {
                    "success_rate": 100 if result.returncode == 0 else 0,
                    "statistics": {"total": 1, "passed": 1, "failed": 0},
                    "results": []
                }
                logging.info("web_api_test_finish: functional success_rate=100 passed=1/1 (fallback)")
                return res
        else:
            res = {
                "success_rate": 0,
                "statistics": {"total": 1, "passed": 0, "failed": 1},
                "results": [{"status": "FAIL", "id": "RUN", "name": "Test Execution", "message": result.stderr or "Unknown error"}],
                "error": result.stderr
            }
            logging.info("web_api_test_finish: functional success_rate=0 passed=0/1 (returncode!=0)")
            return res
            
    except subprocess.TimeoutExpired:
        logging.info("web_api_test_finish: functional timeout")
        return {"error": "Test execution timeout", "success_rate": 0, "statistics": {"total": 1, "passed": 0, "failed": 1}}
    except Exception as e:
        logging.info(f"web_api_test_finish: functional error={e}")
        return {"error": str(e), "success_rate": 0, "statistics": {"total": 1, "passed": 0, "failed": 1}}

    

@app.post("/api/tests/system")
async def run_system_tests():
    """API: Запуск системных тестов"""
    import subprocess
    import sys
    from pathlib import Path
    
    try:
        logging.info("web_api_test_start: system")
        # Запускаем system_test_runner.py
        result = subprocess.run([
            sys.executable, 'tests/system_test_runner.py'
        ], capture_output=True, text=True, timeout=300, cwd=Path.cwd())
        
        # Пытаемся найти JSON отчет системных тестов
        import glob
        json_files = glob.glob('reports/system_test_report_*.json')
        
        if json_files:
            latest_report = max(json_files, key=os.path.getctime)
            with open(latest_report, 'r', encoding='utf-8') as f:
                report_data = json.load(f)
            
            # Преобразуем формат для совместимости с frontend
            res = {
                "summary": {
                    "total": report_data.get("summary", {}).get("total_tests", 0),
                    "passed": report_data.get("summary", {}).get("passed", 0),
                    "failed": report_data.get("summary", {}).get("failed", 0),
                    "success_rate": report_data.get("summary", {}).get("success_rate", 0)
                },
                "results": [
                    {
                        "id": k,
                        "name": v.get("name", "Unknown"),
                        "status": "passed" if v.get("passed", False) else "failed",
                        "error": v.get("error"),
                        "time": v.get("time", 0)
                    }
                    for k, v in report_data.get("details", {}).items()
                ]
            }
            try:
                sr = res["summary"].get("success_rate", 0)
                total = res["summary"].get("total", 0)
                passed = res["summary"].get("passed", 0)
                logging.info(f"web_api_test_finish: system success_rate={sr} passed={passed}/{total}")
            except Exception:
                pass
            return res
        else:
            # Если JSON файла нет, возвращаем результат на основе returncode
            success = result.returncode == 0
            res = {
                "summary": {
                    "total": 1,
                    "passed": 1 if success else 0,
                    "failed": 0 if success else 1,
                    "success_rate": 100 if success else 0
                },
                "results": [] if success else [
                    {"id": "SYS", "name": "System Test", "status": "failed", "error": result.stderr or "Unknown error"}
                ]
            }
            logging.info(f"web_api_test_finish: system success_rate={'100' if success else '0'} passed={'1' if success else '0'}/1 (no report)")
            return res
            
    except subprocess.TimeoutExpired:
        logging.info("web_api_test_finish: system timeout")
        return {
            "summary": {"total": 1, "passed": 0, "failed": 1, "success_rate": 0},
            "results": [{"id": "TIMEOUT", "name": "Test Timeout", "status": "failed", "error": "Test execution timeout"}]
        }
    except Exception as e:
        logging.info(f"web_api_test_finish: system error={e}")
        return {
            "summary": {"total": 1, "passed": 0, "failed": 1, "success_rate": 0},
            "results": [{"id": "ERROR", "name": "Test Error", "status": "failed", "error": str(e)}]
        }

@app.post("/api/tests/smoke")
async def run_smoke_test():
    """API: Быстрый smoke-тест загрузки 1 страницы вакансий по первому активному фильтру"""
    try:
        logging.info("web_api_test_start: smoke")
        # Загружаем первый активный фильтр
        filters_path = Path("config/filters.json")
        if not filters_path.exists():
            return {"status": "error", "message": "filters.json not found"}
        raw = json.load(open(filters_path, 'r', encoding='utf-8'))
        if isinstance(raw, dict) and "filters" in raw:
            items = raw["filters"]
        elif isinstance(raw, dict):
            items = list(raw.values())
        else:
            items = raw
        active = [f for f in items if f.get('active', f.get('enabled', True))]
        if not active:
            return {"status": "error", "message": "no active filters"}
        flt = active[0]
        from plugins.fetcher_v4 import VacancyFetcher
        fetcher = VacancyFetcher(rate_limit_delay=0.2)
        # Загрузка первой страницы
        items = fetcher._fetch_page(flt, page=0)
        # Сохранение в БД v4
        saved = fetcher._save_vacancies(items, flt.get('id'))
        result = {
            "status": "ok",
            "items_count": len(items),
            "loaded_count": saved,
            "filter_id": flt.get('id'),
            "filter_name": flt.get('name'),
            "sample": [
                {"id": it.get('id'), "name": it.get('name')} for it in items[:3]
            ]
        }
        logging.info(f"web_api_test_finish: smoke items={len(items)} saved={saved}")
        return result
    except Exception as e:
        logging.info(f"web_api_test_finish: smoke error={e}")
        return {"status": "error", "message": str(e)}

# // Chg_SCHEDULE_NEXT_2509: время следующей запланированной загрузки (HH:MM)
@app.get("/api/schedule/next")
async def schedule_next():
    """Возвращает время следующей запланированной загрузки в формате HH:MM"""
    try:
        fp = Path('config/config_v4.json')
        freq_h = 1
        if fp.exists():
            try:
                cfg = json.load(open(fp, 'r', encoding='utf-8'))
                td = cfg.get('task_dispatcher') or {}
                # В конфиге уже используется ключ frequency_hours
                freq_h = int(td.get('frequency_hours', 1))
            except Exception:
                freq_h = 1
        now = datetime.now()
        # следующее кратное часу + freq_h часов
        base = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=freq_h)
        return {"next": base.strftime("%H:%M")}
    except Exception as e:
        logging.exception("schedule_next failed")
        # Fallback: текущее время HH:MM
        return {"next": datetime.now().strftime("%H:%M"), "error": str(e)}
# // Chg_WORKERS_FREEZE_2409: заморозка/разморозка воркеров через конфиг
@app.post("/api/workers/freeze")
async def workers_freeze(request: Request):
    try:
        body = await request.json()
        frozen = bool(body.get('frozen', True))
        cfg_path = Path('config/config_v4.json')
        cfg = {}
        if cfg_path.exists():
            cfg = json.load(open(cfg_path, 'r', encoding='utf-8'))
        td = cfg.get('task_dispatcher') or {}
        td['frozen'] = frozen
        cfg['task_dispatcher'] = td
        with open(cfg_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "frozen": frozen}
    except Exception as e:
        logging.exception("workers_freeze failed")
        return {"status": "error", "message": str(e)}

# // Chg_QUEUE_CLEAR_2409: очистка очереди задач (pending)
@app.post("/api/queue/clear")
async def queue_clear(request: Request):
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            body = {}
        status = (body.get('status') or 'pending').strip().lower()
        db = TaskDatabase()
        deleted = 0
        with db.get_connection() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE status=?", (status,))
            deleted = cur.rowcount if hasattr(cur, 'rowcount') else 0
            conn.commit()
        return {"status": "ok", "deleted": deleted, "cleared_status": status}
    except Exception as e:
        logging.exception("queue_clear failed")
        return {"status": "error", "message": str(e)}

@app.get("/api/tests/history")
async def get_tests_history(limit: int = 10):
    """API: История последних тестов (functional/system) из папки reports/
    Возвращает список последних отчетов с унифицированными полями
    """
    try:
        Path('reports').mkdir(exist_ok=True)
        files = []
        # Собираем отчеты функциональных и системных тестов
        files.extend(glob.glob('reports/functional_test_report_*.json'))
        files.extend(glob.glob('reports/system_test_report_*.json'))
        files = sorted(files, key=os.path.getmtime, reverse=True)[:max(1, min(limit, 50))]
        history: List[Dict[str, Any]] = []
        for fp in files:
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                mtime = datetime.fromtimestamp(os.path.getmtime(fp)).isoformat()
                if os.path.basename(fp).startswith('functional_test_report_'):
                    stats = data.get('statistics') or {}
                    history.append({
                        'type': 'functional',
                        'file': os.path.basename(fp),
                        'timestamp': data.get('timestamp') or mtime,
                        'success_rate': data.get('success_rate', 0),
                        'total': stats.get('total', 0),
                        'passed': stats.get('passed', 0),
                        'failed': stats.get('failed', 0)
                    })
                elif os.path.basename(fp).startswith('system_test_report_'):
                    summary = data.get('summary') or {}
                    history.append({
                        'type': 'system',
                        'file': os.path.basename(fp),
                        'timestamp': data.get('timestamp') or mtime,
                        'success_rate': summary.get('success_rate', 0),
                        'total': summary.get('total_tests', 0),
                        'passed': summary.get('passed', 0),
                        'failed': summary.get('failed', 0)
                    })
            except Exception:
                continue
        logging.info(f"web_api_test_history: returned={len(history)}")
        return {'history': history}
    except Exception as e:
        logging.info(f"web_api_test_history_error: {e}")
        return {'history': [], 'error': str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для real-time обновлений"""
    await manager.connect(websocket)
    try:
        while True:
            # Отправляем обновления каждые 5 секунд
            await asyncio.sleep(5)
            
            task_db = TaskDatabase()
            stats = task_db.get_stats()
            
            await websocket.send_text(json.dumps({
                "type": "stats_update",
                "data": stats,
                "timestamp": datetime.now().isoformat()
            }))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/system/health")
async def health_check():
    """Проверка работоспособности системы"""
    try:
        task_db = TaskDatabase()
        stats = task_db.get_stats()
        
        return {
            "status": "healthy",
            "database": "connected",
            "tasks_processed": stats.get("tasks", {}).get("completed", 0),
            "uptime": "running",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/api/daemon/status")
async def get_daemon_status():
    """API: Статус демона планировщика"""
    import psutil 
    from pathlib import Path
    
    pid_file = Path('data/scheduler_daemon.pid')
    now_unix = int(time.time())
    
    if not pid_file.exists():
        return {
            "status": "stopped",
            "running": False,
            "pid": None,
            "message": "PID файл не найден",
            "unix_time": now_unix
        }
    
    try:
        pid = int(pid_file.read_text().strip())
        
        if psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                return {
                    "status": "running", 
                    "running": True,
                    "pid": pid,
                    "cpu_percent": round(process.cpu_percent(), 1),
                    "memory_mb": round(process.memory_info().rss / 1024 / 1024, 1),
                    "started": datetime.fromtimestamp(process.create_time()).isoformat(),
                    "message": "Демон активен",
                    "unix_time": now_unix
                }
            except psutil.NoSuchProcess:
                pid_file.unlink()  # Удаляем устаревший PID
                return {
                    "status": "stopped",
                    "running": False, 
                    "pid": None,
                    "message": "Процесс не найден",
                    "unix_time": now_unix
                }
        else:
            pid_file.unlink()  # Удаляем устаревший PID
            return {
                "status": "stopped",
                "running": False,
                "pid": None, 
                "message": "Процесс не существует",
                "unix_time": now_unix
            }
            
    except Exception as e:
        return {
            "status": "error",
            "running": False,
            "pid": None,
            "message": f"Ошибка проверки: {str(e)}",
            "unix_time": now_unix
        }

@app.get("/api/dashboard/config")
async def dashboard_config():
    """Конфигурация панели для динамической генерации"""
    try:
        config_path = Path(__file__).parent.parent / "config" / "dashboard_layout.json"
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Возвращаем базовую конфигурацию
            return {
                "dashboard_config": {
                    "header": {"title": "HH Tool v4", "version": "v4.0"},
                    "refresh_interval_ms": 30000,
                    "status_row": {"cards": []},
                    "main_grid": {"cards": []}
                }
            }
    except Exception as e:
        logging.exception("config_read failed")
        return {"error": str(e)}

@app.get("/api/filters/list")
async def filters_list():
    """Список фильтров для управления"""
    try:
        filters_path = Path(__file__).parent.parent / "config" / "filters.json"
        if filters_path.exists():
            with open(filters_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"filters": []}
    except Exception as e:
        return {"error": str(e), "filters": []}

@app.get("/api/daemon/tasks")
async def get_daemon_tasks():
    """API: Последние задачи демона планировщика"""
    # Попытка получить статус демона через его API (если доступен)
    # Поскольку демон работает независимо, читаем логи
    from pathlib import Path
    import re
    
    log_file = Path('logs/app.log')
    if not log_file.exists():
        return {"tasks": [], "message": "Лог файл не найден"}
    
    try:
        # Читаем последние строки лога
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Ищем записи планировщика
        scheduler_logs = []
        for line in reversed(lines[-200:]):  # Последние 200 строк
            if 'scheduler_daemon' in line and ('задача' in line.lower() or 'task' in line.lower()):
                # Парсим лог: время, уровень, сообщение
                match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - .* - (\w+) - (.+)', line.strip())
                if match:
                    timestamp, level, message = match.groups()
                    scheduler_logs.append({
                        "timestamp": timestamp,
                        "level": level,
                        "message": message.strip()
                    })
                    
                if len(scheduler_logs) >= 10:  # Ограничиваем количество
                    break
        
        return {
            "tasks": scheduler_logs,
            "message": f"Найдено {len(scheduler_logs)} записей планировщика"
        }
        
    except Exception as e:
        return {
            "tasks": [],
            "message": f"Ошибка чтения логов: {str(e)}"
        }

# // Chg_ACTIVE_TASKS_2409: активные задачи и сводка
@app.get("/api/daemon/tasks/active")
async def get_active_tasks():
    """API: Активные задачи и сводка по очереди"""
    db = TaskDatabase()
    now_unix = int(time.time())
    try:
        running = db.get_tasks(status='running', limit=200, offset=0)
    except Exception:
        running = []
    try:
        pending = db.get_tasks(status='pending', limit=200, offset=0)
    except Exception:
        pending = []
    tasks_table = []
    for idx, t in enumerate(running, start=1):
        tasks_table.append({
            "num": idx,
            "worker": t.get('worker_id') or '-',
            "task_type": t.get('type') or t.get('task_type') or '-',
            "status": t.get('status') or 'running'
        })
    summary = {
        "total": len(running) + len(pending),
        "running": len(running),
        "pending": len(pending),
        "queue_eta": "~0min",
        "unix_time": now_unix
    }
    return {"summary": summary, "tasks": tasks_table}

# // Chg_WORKERS_STATUS_2409: статус воркеров
@app.get("/api/workers/status")
async def workers_status():
    """API: Агрегированный статус по worker_id"""
    db = TaskDatabase()
    workers = []
    active_workers = 0
    total_workers = 5
    try:
        cfg_path = Path('config/config_v4.json')
        if cfg_path.exists():
            cfg = json.load(open(cfg_path, 'r', encoding='utf-8'))
            total_workers = int(((cfg.get('task_dispatcher') or {}).get('max_workers')) or total_workers)
    except Exception:
        pass
    try:
        with db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT worker_id,
                       SUM(CASE WHEN status='running' THEN 1 ELSE 0 END) AS running,
                       SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) AS pending,
                       COUNT(*) AS total
                FROM tasks
                WHERE worker_id IS NOT NULL
                GROUP BY worker_id
                ORDER BY worker_id
                """
            )
            rows = cursor.fetchall()
            for r in rows:
                workers.append({
                    "worker_id": r[0],
                    "running": r[1],
                    "pending": r[2],
                    "total": r[3]
                })
                if r[1] and r[1] > 0:
                    active_workers += 1
    except Exception:
        pass
    return {"workers": workers, "active_workers": active_workers, "total_workers": total_workers}

# // Chg_FILTERS_CTRL_2409: управление фильтрами
@app.post("/api/filters/toggle-all")
async def filters_toggle_all(request: Request):
    body = await request.json()
    enable = bool(body.get('enable', True))
    fp = Path(__file__).parent.parent / "config" / "filters.json"
    if not fp.exists():
        return {"status": "error", "message": "filters.json not found"}
    try:
        data = json.load(open(fp, 'r', encoding='utf-8'))
        items = data.get('filters') if isinstance(data, dict) else data
        for it in items:
            it['active'] = enable
        json.dump({"filters": items}, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return {"status": "ok", "active": enable, "count": len(items)}
    except Exception as e:
        logging.exception("filters_toggle_all failed")
        return {"status": "error", "message": str(e)}

@app.post("/api/filters/invert")
async def filters_invert():
    fp = Path(__file__).parent.parent / "config" / "filters.json"
    if not fp.exists():
        return {"status": "error", "message": "filters.json not found"}
    try:
        data = json.load(open(fp, 'r', encoding='utf-8'))
        items = data.get('filters') if isinstance(data, dict) else data
        for it in items:
            it['active'] = not it.get('active', False)
        json.dump({"filters": items}, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
        return {"status": "ok", "count": len(items)}
    except Exception as e:
        logging.exception("filters_invert failed")
        return {"status": "error", "message": str(e)}

# // Chg_FILTERS_CTRL_2609: установка активности одного фильтра по id
@app.post("/api/filters/set-active")
async def filters_set_active(request: Request):
    """Установить active для конкретного фильтра по его id"""
    try:
        body = await request.json()
        filter_id = body.get('filter_id') or body.get('id')
        active = bool(body.get('active', True))
        if not filter_id:
            return {"status": "error", "message": "filter_id is required"}

        fp = Path(__file__).parent.parent / "config" / "filters.json"
        if not fp.exists():
            return {"status": "error", "message": "filters.json not found"}

        data = json.load(open(fp, 'r', encoding='utf-8'))
        items = data.get('filters') if isinstance(data, dict) else data

        updated = False
        for it in items:
            if str(it.get('id')) == str(filter_id):
                it['active'] = active
                updated = True
                break

        if not updated:
            return {"status": "error", "message": f"filter {filter_id} not found"}

        with open(fp, 'w', encoding='utf-8') as f:
            json.dump({"filters": items}, f, ensure_ascii=False, indent=2)

        return {"status": "ok", "filter_id": filter_id, "active": active}
    except Exception as e:
        logging.exception("filters_set_active failed")
        return {"status": "error", "message": str(e)}

# // Chg_FILTERS_LOAD_NOW_2609: немедленный запуск загрузки для выбранных фильтров
@app.post("/api/filters/load-now")
async def filters_load_now(request: Request):
    """Создает задачи load_vacancies для указанных filter_ids (или для всех active)."""
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}
        filter_ids = body.get('filter_ids') or []

        fp = Path(__file__).parent.parent / "config" / "filters.json"
        if not fp.exists():
            return {"status": "error", "message": "filters.json not found"}
        raw = json.load(open(fp, 'r', encoding='utf-8'))
        items = (raw.get('filters') if isinstance(raw, dict) else raw) or []

        selected = []
        if filter_ids:
            want = {str(x) for x in filter_ids}
            for it in items:
                if str(it.get('id')) in want:
                    selected.append(it)
        else:
            selected = [it for it in items if it.get('active', False)]

        if not selected:
            return {"status": "error", "message": "no filters selected"}

        db = TaskDatabase()
        created = []
        import uuid as _uuid
        for f in selected:
            try:
                tid = str(_uuid.uuid4())
                params = {"filter": f, "max_pages": f.get('max_pages'), "chunk_size": 500}
                db.create_task(tid, 'load_vacancies', params, schedule_at=None, timeout_sec=3600)
                created.append({"task_id": tid, "filter_id": f.get('id'), "name": f.get('name')})
            except Exception:
                continue

        return {"status": "ok", "count": len(created), "created": created}
    except Exception as e:
        logging.exception("filters_load_now failed")
        return {"status": "error", "message": str(e)}

# // Chg_CONFIG_CTRL_2409: управление config_v4.json
@app.get("/api/config/read")
async def config_read():
    fp = Path('config/config_v4.json')
    if not fp.exists():
        return {}
    try:
        return json.load(open(fp, 'r', encoding='utf-8'))
    except Exception as e:
        logging.exception("config_read failed")
        return {"error": str(e)}

@app.post("/api/config/write")
async def config_write(request: Request):
    body = await request.json()
    fp = Path('config/config_v4.json')
    try:
        fp.parent.mkdir(exist_ok=True)
        # backup
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        bak = fp.with_suffix('.json.bak.' + ts)
        if fp.exists():
            with open(fp, 'r', encoding='utf-8') as src, open(bak, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "backup": str(bak.name)}
    except Exception as e:
        logging.exception("config_write failed")
        return {"status": "error", "message": str(e)}

# // Chg_SCHEDULE_CTRL_2409: частота расписания
@app.post("/api/schedule/frequency")
async def schedule_frequency(request: Request):
    body = await request.json()
    freq = int(body.get('frequency_hours', 0))
    fp = Path('config/config_v4.json')
    try:
        cfg = {}
        if fp.exists():
            cfg = json.load(open(fp, 'r', encoding='utf-8'))
        td = cfg.get('task_dispatcher') or {}
        td['frequency_hours'] = freq
        cfg['task_dispatcher'] = td
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "frequency_hours": freq}
    except Exception as e:
        logging.exception("schedule_frequency failed")
        return {"status": "error", "message": str(e)}

# // Chg_DAEMON_CTRL_2409: управление демоном через CLI
@app.post("/api/daemon/start")
async def daemon_start():
    try:
        import subprocess, sys, os
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        env['CALLED_FROM_WEB'] = '1'
        result = subprocess.run([sys.executable, 'cli_v4.py', 'daemon', 'start', '--background'], capture_output=True, text=True, timeout=60, env=env)
        return {"status": "ok" if result.returncode == 0 else "error", "returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}
    except Exception as e:
        logging.exception("daemon_start failed")
        return {"status": "error", "message": str(e)}

@app.post("/api/daemon/stop")
async def daemon_stop():
    try:
        import subprocess, sys
        result = subprocess.run([sys.executable, 'cli_v4.py', 'daemon', 'stop'], capture_output=True, text=True, timeout=60)
        return {"status": "ok" if result.returncode == 0 else "error", "returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}
    except Exception as e:
        logging.exception("daemon_stop failed")
        return {"status": "error", "message": str(e)}

# // Chg_DAEMON_API_2509: перезапуск демона через CLI
@app.post("/api/daemon/restart")
async def daemon_restart():
    try:
        import subprocess, sys, os
        env = os.environ.copy()
        env["CALLED_FROM_WEB"] = "1"
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        result = subprocess.run([sys.executable, 'cli_v4.py', 'daemon', 'restart'], capture_output=True, text=True, timeout=90, env=env)
        return {"status": "ok" if result.returncode == 0 else "error", "returncode": result.returncode, "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}
    except Exception as e:
        logging.exception("daemon_restart failed")
        return {"status": "error", "message": str(e)}

# Background task для broadcast обновлений
async def broadcast_updates():
    """Фоновая задача для отправки обновлений всем подключенным клиентам"""
    while True:
        try:
            # Получаем актуальные данные безопасно
            try:
                stats_data = await get_stats()
            except Exception as e:
                print(f"Ошибка получения статистики: {e}")
                stats_data = {"status": "error", "error": str(e)}
            
            try:
                system_info = _get_system_info()
            except Exception as e:
                print(f"Ошибка получения системной информации: {e}")
                system_info = {"status": "error", "error": str(e)}
            
            # Отправляем всем подключенным клиентам
            if manager.active_connections:
                await manager.broadcast({
                    "type": "stats_update",
                    "data": stats_data,
                    "timestamp": time.time()
                })
                
                await manager.broadcast({
                    "type": "system_update", 
                    "data": system_info,
                    "timestamp": time.time()
                })
            
            await asyncio.sleep(5)  # Обновляем каждые 5 секунд
            
        except Exception as e:
            print(f"Broadcast error: {e}")
            await asyncio.sleep(10)  # При ошибке ждем дольше

@app.on_event("startup")
async def startup_event():
    """Событие запуска - запускаем фоновые задачи"""
    asyncio.create_task(broadcast_updates())

def _read_web_bind_from_config() -> tuple[str, int, str]:
    """Читает host/port и уровень логирования из config/config_v4.json"""
    try:
        cfg = json.load(open('config/config_v4.json', 'r', encoding='utf-8'))
        wi = cfg.get('web_interface') or {}
        host = wi.get('host', 'localhost')
        port = int(wi.get('port', 8000))
        lvl = ((cfg.get('logging') or {}).get('level') or 'INFO').lower()
        return host, port, lvl
    except Exception:
        return 'localhost', 8000, 'info'

def run_web_server(host: str = None, port: int = None, debug: bool = False):
    """Запуск веб-сервера (совместимость)"""
    h, p, lvl = _read_web_bind_from_config()
    host = host or h
    port = int(port or p)
    if debug:
        uvicorn.run("web.server:app", host=host, port=port, reload=True, log_level=lvl)
    else:
        uvicorn.run(app, host=host, port=port, log_level=lvl)

def _get_system_info() -> Dict[str, Any]:
    """Получение системных метрик: память%/диск%/CPU/нагрузка + метрики из БД"""
    try:
        vm = psutil.virtual_memory()
        total_mb = round(vm.total / 1024 / 1024, 2)
        memory_percent = round(vm.percent, 1)
        
        # Диск: процент использования
        try:
            if os.name == 'nt':  # Windows
                disk = psutil.disk_usage('C:\\')
            else:
                disk = psutil.disk_usage('/')
            disk_percent = round((disk.used / disk.total) * 100, 1)
        except Exception:
            disk_percent = 0.0
        
        # // Chg_STATS_CACHE_1509: неблокирующее измерение CPU (interval=0)
        cpu_percent = round(psutil.cpu_percent(interval=0), 1)
        
        load_avg = None
        try:
            la1, la5, la15 = psutil.getloadavg()  # Не работает на Windows
            load_avg = {"1m": round(la1, 2), "5m": round(la5, 2), "15m": round(la15, 2)}
        except (AttributeError, OSError):
            load_avg = {"1m": None, "5m": None, "15m": None}
        
        # Размер всех файлов *.sqlite* в рабочей папке
        try:
            db_files = glob.glob("data/*.sqlite*", recursive=False)
            db_total_size = sum(os.path.getsize(f) for f in db_files if os.path.exists(f))
            db_total_mb = round(db_total_size / 1024 / 1024, 2)
        except Exception:
            db_total_mb = 0.0
        
        # Расширенные метрики
        enhanced_metrics = _load_enhanced_metrics()
        
        return {
            "memory_total_mb": total_mb,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "cpu_percent": cpu_percent,
            "load_avg": load_avg,
            "db_files_total_mb": db_total_mb,
            **enhanced_metrics
        }
    except Exception as e:
        print(f"Ошибка получения системных метрик: {e}")
        return {
            "memory_total_mb": 0,
            "memory_percent": 0,
            "disk_percent": 0,
            "cpu_percent": 0,
            "load_avg": {"1m": None, "5m": None, "15m": None},
            "db_files_total_mb": 0
        }

def _load_enhanced_metrics() -> Dict[str, Any]:
    """Загрузка расширенных метрик из logs/dashboard_metrics.json или logs/local_metrics.txt"""
    try:
        logs_dir = Path("logs")
        json_file = logs_dir / "dashboard_metrics.json"
        txt_file = logs_dir / "local_metrics.txt"

        if json_file.exists():
            try:
                with open(json_file, 'r', encoding='utf-8') as jf:
                    data = json.load(jf)
                def _norm_dt(v):
                    try:
                        if isinstance(v, str):
                            return v.replace('T', ' ')
                    except Exception:
                        pass
                    return v
                return {
                    "db_last_update": _norm_dt(data.get("db_last_update", "unknown")),
                    "max_published_at": _norm_dt(data.get("max_published_at", "unknown")),
                    "unique_publish_dates": int(data.get("unique_publish_dates", 0) or 0),
                    "captcha_detected": int(data.get("captcha_detected", 0) or 0),
                    "captcha_solved": int(data.get("captcha_solved", 0) or 0),
                    "last_captcha": _norm_dt(data.get("last_captcha", "none")),
                    "unique_companies": int(data.get("unique_companies", 0) or 0)
                }
            except Exception:
                pass

        # Фоллбэк: TXT
        if txt_file.exists():
            with open(txt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            metrics = {}
            for line in content.split('\n'):
                if '=' in line and not line.startswith('['):
                    key, value = line.split('=', 1)
                    value = value.strip()
                    try:
                        if value.replace('.', '', 1).isdigit():
                            if '.' in value:
                                metrics[key.lower()] = float(value)
                            else:
                                metrics[key.lower()] = int(value)
                        else:
                            metrics[key.lower()] = value
                    except Exception:
                        metrics[key.lower()] = value

            def _norm_dt(v):
                try:
                    if isinstance(v, str):
                        return v.replace('T', ' ')
                except Exception:
                    pass
                return v

            return {
                "db_last_update": _norm_dt(metrics.get("db_last_update", "unknown")),
                "max_published_at": _norm_dt(metrics.get("max_published_at", "unknown")),
                "unique_publish_dates": metrics.get("unique_publish_dates", 0),
                "captcha_detected": metrics.get("captcha_detected", 0),
                "captcha_solved": metrics.get("captcha_solved", 0),
                "last_captcha": _norm_dt(metrics.get("last_captcha", "none")),
                "unique_companies": metrics.get("unique_companies", 0)
            }
        
        return {
            "db_last_update": "unknown",
            "max_published_at": "unknown",
            "unique_publish_dates": 0,
            "captcha_detected": 0,
            "captcha_solved": 0,
            "last_captcha": "none",
            "unique_companies": 0
        }

    except Exception:
        return {
            "db_last_update": "error",
            "max_published_at": "error",
            "unique_publish_dates": 0,
            "captcha_detected": 0,
            "captcha_solved": 0,
            "last_captcha": "error",
            "unique_companies": 0
        }

def _get_active_processes() -> List[Dict[str, Any]]:
    """Получение списка активных процессов (для v4 - из tasks с status='running')"""
    try:
        task_db = TaskDatabase()
        
        # В v4 нет process_status таблицы, используем tasks
        with task_db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, type, status, created_at, started_at, progress_json 
                FROM tasks 
                WHERE status = 'running' 
                ORDER BY created_at DESC
            """)
            
            processes = []
            for row in cursor.fetchall():
                task_id, task_type, status, created_at, started_at, progress_json = row
                
                # Парсим прогресс
                progress_data = {}
                if progress_json:
                    try:
                        progress_data = json.loads(progress_json)
                    except:
                        pass
                
                total_items = progress_data.get('total', 0)
                processed_items = progress_data.get('processed', 0)
                progress = 0.0
                eta_minutes = None
                
                if total_items and total_items > 0:
                    progress = (processed_items / total_items) * 100
                    # Примерная оценка времени
                    if started_at and processed_items > 0:
                        elapsed = time.time() - started_at
                        speed_per_second = processed_items / elapsed if elapsed > 0 else 0
                        remaining = total_items - processed_items
                        if speed_per_second > 0:
                            eta_minutes = round((remaining / speed_per_second) / 60)
                
                processes.append({
                    "id": task_id,
                    "name": f"{task_type} Task",
                    "status": status,
                    "progress": round(progress, 1),
                    "eta_minutes": eta_minutes,
                    "speed_per_minute": progress_data.get('speed_per_minute', 0.0),
                    "total_items": total_items,
                    "processed_items": processed_items
                })
            
            return processes
            
    except Exception as e:
        print(f"Ошибка чтения активных процессов: {e}")
        return []

# // Chg_TEST_API_2409: API endpoints for testing system
@app.post("/api/tests/run")
async def run_tests():
    """Неблокирующий запуск тестов: стартуем подпроцесс, сразу возвращаем status=started.
    Статус и результаты читаются через /api/tests/status и /api/tests/details.
    """
    try:
        import subprocess, sys, os
        from pathlib import Path

        logging.info("Starting test run via API (non-blocking)")

        logs_dir = Path(__file__).parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        running_flag = logs_dir / '.tests_running'
        try:
            running_flag.write_text(str(time.time()), encoding='utf-8')
        except Exception:
            pass

        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'

        proc = subprocess.Popen([sys.executable, '-m', 'tests.consolidated_tests'], cwd=Path.cwd(),
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

        def _wait_and_clear():
            try:
                proc.wait(timeout=900)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
            # снимаем флаг выполнения
            try:
                if running_flag.exists():
                    running_flag.unlink()
            except Exception:
                pass

        threading.Thread(target=_wait_and_clear, daemon=True).start()

        return JSONResponse({"status": "started", "pid": proc.pid})
    except Exception as e:
        logging.exception("Error starting tests")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/tests/status") 
async def get_test_status():
    """Получение статуса последних тестов"""
    try:
        from pathlib import Path
        import os
        
        union_log_path = Path(__file__).parent.parent / 'logs' / 'union_test.log'
        running_flag = Path(__file__).parent.parent / 'logs' / '.tests_running'
        
        if not union_log_path.exists():
            return JSONResponse({
                "success_rate": 0,
                "last_run": None,
                "status": "running" if running_flag.exists() else "no_tests_run",
                "running": running_flag.exists()
            })
        
        # Время модификации файла
        last_modified = os.path.getmtime(union_log_path)
        last_run = datetime.fromtimestamp(last_modified).isoformat()
        
        # Читаем и парсим лог
        with open(union_log_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        success_rate = 0
        for line in content.split('\n'):
            if 'Overall:' in line and '%' in line:
                try:
                    success_rate = float(line.split('Overall:')[1].split('%')[0].strip())
                    break
                except (ValueError, IndexError):
                    pass
        
        return JSONResponse({
            "success_rate": success_rate,
            "last_run": last_run,
            "status": "running" if running_flag.exists() else "available",
            "running": running_flag.exists()
        })
        
    except Exception as e:
        logging.exception("Error getting test status")
        return JSONResponse({"success_rate": 0, "last_run": None, "error": str(e)})

@app.get("/api/tests/details")
async def get_test_details():
    """Детальные результаты тестов с union_test.log"""
    try:
        from pathlib import Path
        
        union_log_path = Path(__file__).parent.parent / 'logs' / 'union_test.log'
        
        if not union_log_path.exists():
            return JSONResponse({"error": "No test results available"}, status_code=404)
        
        with open(union_log_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        # Парсим результаты
        lines = log_content.split('\n')
        total_tests = 0
        passed_tests = 0
        success_rate = 0
        failed_tests = []
        
        in_failed_section = False
        for line in lines:
            line = line.strip()
            if 'Total:' in line and 'Passed:' in line:
                parts = line.split(',')
                if len(parts) >= 3:
                    try:
                        total_tests = int(parts[0].split(':')[1].strip())
                        passed_tests = int(parts[1].split(':')[1].strip())
                        success_rate = float(parts[2].split(':')[1].strip().replace('%', ''))
                    except (ValueError, IndexError):
                        pass
            elif 'FAILED TESTS:' in line:
                in_failed_section = True
            elif in_failed_section and line.startswith('- '):
                # Парсим неуспешные тесты
                test_info = line[2:]  # убираем "- "
                if ':' in test_info:
                    parts = test_info.split(':', 1)
                    failed_tests.append({
                        "name": parts[0].strip(),
                        "error": parts[1].strip()
                    })
        
        return JSONResponse({
            "total_tests": total_tests,
            "passed_tests": passed_tests, 
            "success_rate": success_rate,
            "failed_tests": failed_tests,
            "union_test_log": log_content
        })
        
    except Exception as e:
        logging.exception("Error getting test details")
        return JSONResponse({"error": str(e)}, status_code=500)

# // Chg_STATS_API_2609: системные метрики для панели
@app.get("/api/stats/system_health")
async def get_system_health():
    """API: Системные метрики для индикатора здоровья"""
    try:
        system_info = _get_system_info()

        # Определяем статус на основе метрик
        memory_percent = system_info.get('memory_percent', 0)
        cpu_percent = system_info.get('cpu_percent', 0)
        disk_percent = system_info.get('disk_percent', 0)

        # Логика определения статуса
        if memory_percent > 90 or cpu_percent > 90 or disk_percent > 95:
            status = "critical"
            color = "#dc3545"
        elif memory_percent > 75 or cpu_percent > 75 or disk_percent > 80:
            status = "warning"
            color = "#ffc107"
        else:
            status = "good"
            color = "#28a745"

        return {
            "status": status,
            "color": color,
            "memory_percent": memory_percent,
            "cpu_percent": cpu_percent,
            "disk_percent": disk_percent,
            "details": f"RAM: {memory_percent}%, CPU: {cpu_percent}%, Disk: {disk_percent}%"
        }
    except Exception as e:
        logging.exception("get_system_health failed")
        return {
            "status": "error",
            "color": "#6c757d",
            "memory_percent": 0,
            "cpu_percent": 0,
            "disk_percent": 0,
            "details": f"Error: {str(e)}"
        }

@app.get("/api/stats/api_status")
async def get_api_status():
    """API: Статус HH API для индикатора"""
    try:
        # Проверяем доступность HH API через тестовый запрос
        import requests

        # Используем базовый URL из конфига
        try:
            cfg = json.load(open('config/config_v4.json', 'r', encoding='utf-8'))
            hh_config = cfg.get('hh_api', {})
            test_url = hh_config.get('base_url', 'https://api.hh.ru/vacancies')
        except Exception:
            test_url = 'https://api.hh.ru/vacancies'

        try:
            # Делаем тестовый запрос к HH API
            response = requests.get(
                test_url,
                params={'per_page': 1, 'page': 0},
                timeout=5,
                headers={'User-Agent': 'HH-Bot/4.0'}
            )

            if response.status_code == 200:
                status = "good"
                color = "#28a745"
                details = f"API доступен (200)"
            elif response.status_code >= 400:
                status = "critical"
                color = "#dc3545"
                details = f"API ошибка ({response.status_code})"
            else:
                status = "warning"
                color = "#ffc107"
                details = f"API предупреждение ({response.status_code})"

        except requests.RequestException as e:
            status = "critical"
            color = "#dc3545"
            details = f"API недоступен: {str(e)}"

        return {
            "status": status,
            "color": color,
            "http_code": response.status_code if 'response' in locals() else 0,
            "details": details
        }

    except Exception as e:
        logging.exception("get_api_status failed")
        return {
            "status": "error",
            "color": "#6c757d",
            "http_code": 0,
            "details": f"Error: {str(e)}"
        }

@app.get("/api/logs/app")
async def get_app_log(limit: int = 100):
    """Получение последних строк из app.log"""
    try:
        from pathlib import Path
        
        app_log_path = Path(__file__).parent.parent / 'logs' / 'app.log'
        
        if not app_log_path.exists():
            return JSONResponse({"error": "app.log not found"}, status_code=404)
        
        # Ограничение количества строк 20..100
        try:
            limit = int(limit)
        except Exception:
            limit = 100
        limit = max(20, min(100, limit))
        
        # Читаем последние N строк
        with open(app_log_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
        return JSONResponse({
            "lines": [line.strip() for line in recent_lines],
            "total_lines": len(lines),
            "showing_last": len(recent_lines)
        })
        
    except Exception as e:
        logging.exception("Error reading app.log")
        return JSONResponse({"error": str(e)}, status_code=500)

def run_server(host: str = None, port: int = None, log_level: str = None):
    """Запуск FastAPI сервера с параметрами из конфига по умолчанию"""
    h, p, lvl = _read_web_bind_from_config()
    host = host or h
    port = int(port or p)
    log_level = (log_level or lvl).lower()
    uvicorn.run(app, host=host, port=port, log_level=log_level)

if __name__ == "__main__":
    # Запускаем сервер с настройками из config/config_v4.json
    run_server()
