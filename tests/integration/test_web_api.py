# -*- coding: utf-8 -*-
"""
Integration checks for HH Tool v4 Web API
- Вызывает ключевые эндпоинты веб-панели, проверяет корректность ответов
- Может запускаться как pytest (функции test_*) или как скрипт (python test_web_api.py)
- Логи добавляются в logs/union_test.log (UTF-8)
"""
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("[Integration] Требуется библиотека 'requests' (pip install requests)")
    sys.exit(2)

BASE_URL = os.environ.get("HH_BASE_URL", "http://127.0.0.1:5000").rstrip('/')
LOGS_DIR = Path("logs")
UNION_LOG = LOGS_DIR / "union_test.log"


def _log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    txt = f"[{ts}] [integration] {msg}"
    print(txt)
    try:
        with open(UNION_LOG, 'a', encoding='utf-8') as f:
            f.write(txt + "\n")
    except Exception:
        pass


def _get(path: str, timeout=10):
    return requests.get(f"{BASE_URL}{path}", timeout=timeout)


def _post(path: str, payload=None, timeout=60):
    return requests.post(f"{BASE_URL}{path}", json=payload or {}, timeout=timeout)


# ---- Tests ----

def test_stats():
    r = _get('/api/stats', timeout=5)
    assert r.ok, f"/api/stats http {r.status_code}"
    js = r.json()
    assert 'system_info' in js, "no system_info in stats"
    _log("/api/stats OK")


def test_filters():
    r = _get('/api/filters', timeout=5)
    assert r.ok, f"/api/filters http {r.status_code}"
    js = r.json()
    assert 'filters' in js, "no filters key"
    _log(f"/api/filters OK; count={len(js.get('filters') or [])}")


def test_smoke():
    r = _post('/api/tests/smoke', timeout=120)
    assert r.ok, f"/api/tests/smoke http {r.status_code}"
    js = r.json()
    assert js.get('status') == 'ok', f"smoke status={js}"
    _log(f"/api/tests/smoke OK; items={js.get('items_count')} saved={js.get('loaded_count')}")


def test_tasks_and_vacancies():
    r = _get('/api/tasks?status=completed,running,pending&limit=3', timeout=10)
    assert r.ok, f"/api/tasks http {r.status_code}"
    tasks = (r.json() or {}).get('tasks') or []
    _log(f"/api/tasks OK; total={len(tasks)}")

    r2 = _get('/api/vacancies/recent?limit=5', timeout=10)
    assert r2.ok, f"/api/vacancies/recent http {r2.status_code}"
    vac = (r2.json() or {}).get('vacancies') or []
    _log(f"/api/vacancies/recent OK; count={len(vac)}")


def test_history():
    r = _get('/api/tests/history?limit=10', timeout=10)
    assert r.ok, f"/api/tests/history http {r.status_code}"
    hist = (r.json() or {}).get('history') or []
    _log(f"/api/tests/history OK; total={len(hist)}")


def main():
    LOGS_DIR.mkdir(exist_ok=True)
    # Не очищаем файл здесь, это делает e2e_runner. Просто добавляем записи.

    # Мини-проверка доступности
    try:
        r = _get('/api/stats', timeout=3)
        if not r.ok:
            _log("Веб-сервер не отвечает: /api/stats http " + str(r.status_code))
            sys.exit(1)
    except Exception as e:
        _log("Веб-сервер не доступен: " + str(e))
        sys.exit(1)

    # Выполняем тесты последовательно
    try:
        test_stats()
        test_filters()
        test_smoke()
        test_tasks_and_vacancies()
        test_history()
        _log("Integration SUCCESS")
        sys.exit(0)
    except AssertionError as ae:
        _log("Integration FAILED: " + str(ae))
        sys.exit(1)
    except Exception as e:
        _log("Integration ERROR: " + str(e))
        sys.exit(2)


if __name__ == '__main__':
    main()
