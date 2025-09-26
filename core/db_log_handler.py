"""
// Chg_DB_LOG_HANDLER_2409: logging.Handler for writing logs into SQLite via TaskDatabase
"""
import logging
import json
import time
from typing import Optional
from .task_database import TaskDatabase

class DbLogHandler(logging.Handler):
    def __init__(self, db_path: Optional[str] = None, level=logging.INFO):
        super().__init__(level)
        self.db = TaskDatabase(db_path or "data/hh_v4.sqlite3")
        # avoid recursion: don't let this handler write its own logs
        self._logger_name = self.__class__.__name__

    def emit(self, record: logging.LogRecord) -> None:
        try:
            # Filter out noisy modules if needed
            if getattr(record, 'name', '').endswith('sqlite3') or record.name == self._logger_name:
                return
            msg = self.format(record) if self.formatter else record.getMessage()
            ctx = {
                'process': record.process,
                'thread': record.thread,
                'lineno': record.lineno,
                'pathname': record.pathname,
                'funcName': record.funcName,
            }
            # // Chg_DB_LOG_FIX_2409: добавляем debug при ошибках записи
            self.db._write_log_record(
                ts=time.time(),
                level=record.levelname,
                module=record.name,
                func=record.funcName or '',
                message=msg,
                context_json=json.dumps(ctx, ensure_ascii=False)
            )
        except Exception as e:
            # Never raise from logging, but try to debug
            try:
                import sys
                print(f"DbLogHandler error: {e}", file=sys.stderr)
            except:
                pass
