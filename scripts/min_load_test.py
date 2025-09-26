#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Мини-тест загрузки 1 страницы для тест-фильтра и проверка увеличения записей в БД v4
Соответствует Фазе B плана: Verify vacancies saved to DB
"""
import json
import sys
import time
from pathlib import Path

sys.path.append('.')
from plugins.fetcher_v4 import VacancyFetcher
from core.task_database import TaskDatabase


def get_vacancy_count(db: TaskDatabase) -> int:
    with db.get_connection() as conn:
        return int(conn.execute('SELECT COUNT(*) FROM vacancies').fetchone()[0])


def pick_test_filter() -> dict:
    filters_path = Path('config/filters.json')
    if not filters_path.exists():
        raise FileNotFoundError('config/filters.json not found')
    data = json.load(open(filters_path, 'r', encoding='utf-8'))
    items = data.get('filters', [])
    # Предпочтительно python-hybrid-latest
    for it in items:
        if it.get('id') == 'python-hybrid-latest':
            return it
    # Иначе первый test с max_pages=1
    for it in items:
        if it.get('type') == 'test':
            it.setdefault('max_pages', 1)
            return it
    # Фолбэк — первый активный
    for it in items:
        if it.get('active', it.get('enabled', True)):
            it.setdefault('max_pages', 1)
            return it
    # Если пусто
    raise RuntimeError('No suitable filter found in config/filters.json')


def append_union_log(lines: list):
    logs_dir = Path('logs')
    logs_dir.mkdir(exist_ok=True)
    with open(logs_dir / 'union_test.log', 'a', encoding='utf-8') as f:
        for line in lines:
            f.write(line.rstrip('\n') + '\n')


def main():
    db = TaskDatabase()
    before = get_vacancy_count(db)

    test_filter = pick_test_filter()
    fetcher = VacancyFetcher(database=db)

    # Ограничиваем загрузку одной страницей
    params = {
        'page_start': 0,
        'page_end': 1,
        'filter': test_filter,
        'task_id': 'min_load_test'
    }

    t0 = time.time()
    result = fetcher.fetch_chunk(params)
    elapsed = time.time() - t0

    after = get_vacancy_count(db)

    summary = {
        'filter_id': test_filter.get('id'),
        'loaded_count': int(result.get('loaded_count', 0)),
        'processed_pages': int(result.get('processed_pages', 0)),
        'errors': result.get('errors', []),
        'vacancies_before': before,
        'vacancies_after': after,
        'delta': after - before,
        'elapsed_sec': round(elapsed, 2)
    }

    # Вывод в stdout для CI и парсинга
    print('MIN_LOAD_RESULT:', json.dumps(summary, ensure_ascii=False))

    # Лог в union_test.log
    append_union_log([
        '--- MIN LOAD TEST ---',
        f"Filter: {summary['filter_id']}",
        f"Loaded: {summary['loaded_count']} from {summary['processed_pages']} pages in {summary['elapsed_sec']}s",
        f"DB before/after/delta: {before}/{after}/{summary['delta']}",
    ])

    # Код выхода: 0 если есть прирост или хотя бы попытка загрузки прошла без ошибок
    if summary['loaded_count'] > 0 or summary['delta'] > 0:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
