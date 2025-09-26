#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-панель мониторинга HH-бота v4

// Chg_DASHBOARD_2009: Современная веб-панель с real-time мониторингом
Включает статистику БД, профили данных, статус системы, логи
"""

from flask import Flask, render_template, jsonify, request
import json
import os
import time
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
from typing import Dict, List, Any

# Настройка путей
PROJECT_ROOT = Path(__file__).parent.parent
TEMPLATES_DIR = PROJECT_ROOT / 'web' / 'templates'
STATIC_DIR = PROJECT_ROOT / 'web' / 'static'

app = Flask(__name__, 
           template_folder=str(TEMPLATES_DIR),
           static_folder=str(STATIC_DIR))

# Добавляем путь к проекту для импортов
import sys
sys.path.insert(0, str(PROJECT_ROOT))


class MonitoringService:
    """Сервис для сбора данных мониторинга"""
    
    def __init__(self):
        self.db_path = PROJECT_ROOT / 'data' / 'hh_v4.sqlite3'
        
    def get_database_stats(self) -> Dict[str, Any]:
        """Статистика базы данных (v4)"""
        try:
            from core.task_database import TaskDatabase
            db = TaskDatabase(str(self.db_path))
            
            # Основная статистика
            stats = db.get_stats()
            
            # Статистика изменений
            changes_stats = db.get_combined_changes_stats(days=7)
            
            # Системная информация (упрощённо)
            system_info = {}
            try:
                if os.path.exists(self.db_path):
                    system_info['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024*1024), 2)
                with db.get_connection() as conn:
                    cur = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                    system_info['tables_count'] = cur.fetchone()[0]
            except Exception:
                system_info = {'tables_count': 0}
            
            return {
                'basic_stats': stats,
                'changes_stats': changes_stats,
                'system_info': system_info,
                'status': 'connected',
                'last_updated': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'status': 'error',
                'last_updated': datetime.now().isoformat()
            }
    
    def get_data_profile(self) -> Dict[str, Any]:
        """Профиль данных в БД"""
        try:
            if not os.path.exists(self.db_path):
                return {'error': 'База данных не найдена'}
                
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                
                # Профиль вакансий
                vacancy_profile = self._get_vacancy_profile(cursor)
                
                # Профиль работодателей  
                employer_profile = self._get_employer_profile(cursor)
                
                # Статистика по времени
                time_stats = self._get_time_statistics(cursor)
                
                return {
                    'vacancies': vacancy_profile,
                    'employers': employer_profile,
                    'time_analysis': time_stats,
                    'status': 'success'
                }
                
        except Exception as e:
            return {'error': str(e), 'status': 'error'}
    
    def _get_vacancy_profile(self, cursor) -> Dict[str, Any]:
        """Профиль данных по вакансиям"""
        profile = {}
        
        # Общие метрики
        cursor.execute("SELECT COUNT(*) FROM vacancies")
        profile['total_count'] = cursor.fetchone()[0]
        
        # Распределение по зарплатам
        cursor.execute("""
            SELECT 
                CASE 
                    WHEN salary_from IS NULL THEN 'Не указана'
                    WHEN salary_from < 50000 THEN '< 50к'
                    WHEN salary_from < 100000 THEN '50к - 100к'
                    WHEN salary_from < 200000 THEN '100к - 200к'
                    WHEN salary_from < 300000 THEN '200к - 300к'
                    ELSE '> 300к'
                END as salary_range,
                COUNT(*) as count
            FROM vacancies
            GROUP BY salary_range
            ORDER BY count DESC
        """)
        profile['salary_distribution'] = dict(cursor.fetchall())
        
        # Топ работодателей
        cursor.execute("""
            SELECT employer_name, COUNT(*) as count
            FROM vacancies 
            WHERE employer_name IS NOT NULL
            GROUP BY employer_name
            ORDER BY count DESC
            LIMIT 10
        """)
        profile['top_employers'] = dict(cursor.fetchall())
        
        # Распределение по опыту
        cursor.execute("""
            SELECT experience, COUNT(*) as count
            FROM vacancies
            GROUP BY experience
            ORDER BY count DESC
        """)
        profile['experience_distribution'] = dict(cursor.fetchall())
        
        # Последние обновления
        cursor.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM vacancies
            WHERE created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        """)
        profile['recent_activity'] = dict(cursor.fetchall())
        
        return profile
    
    def _get_employer_profile(self, cursor) -> Dict[str, Any]:
        """Профиль данных по работодателям"""
        profile = {}
        
        # Проверяем наличие таблицы employers
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employers'")
        if not cursor.fetchone():
            return {'error': 'Таблица employers не найдена'}
        
        # Общие метрики
        cursor.execute("SELECT COUNT(*) FROM employers")
        profile['total_count'] = cursor.fetchone()[0]
        
        # Активные работодатели (у которых есть вакансии)
        cursor.execute("""
            SELECT COUNT(DISTINCT e.id)
            FROM employers e
            JOIN vacancies v ON e.hh_id = v.employer_id
        """)
        result = cursor.fetchone()
        profile['active_count'] = result[0] if result else 0
        
        return profile
    
    def _get_time_statistics(self, cursor) -> Dict[str, Any]:
        """Статистика по времени"""
        stats = {}
        
        # Активность по дням недели
        cursor.execute("""
            SELECT 
                CASE strftime('%w', created_at)
                    WHEN '0' THEN 'Воскресенье'
                    WHEN '1' THEN 'Понедельник'
                    WHEN '2' THEN 'Вторник'
                    WHEN '3' THEN 'Среда'
                    WHEN '4' THEN 'Четверг'
                    WHEN '5' THEN 'Пятница'
                    WHEN '6' THEN 'Суббота'
                END as day_name,
                COUNT(*) as count
            FROM vacancies
            WHERE created_at >= date('now', '-30 days')
            GROUP BY strftime('%w', created_at)
            ORDER BY strftime('%w', created_at)
        """)
        stats['by_weekday'] = dict(cursor.fetchall())
        
        # Активность по часам
        cursor.execute("""
            SELECT strftime('%H', created_at) as hour, COUNT(*) as count
            FROM vacancies
            WHERE created_at >= date('now', '-7 days')
            GROUP BY strftime('%H', created_at)
            ORDER BY hour
        """)
        stats['by_hour'] = dict(cursor.fetchall())
        
        return stats
    
    def get_system_health(self) -> Dict[str, Any]:
        """Состояние системы"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'status': 'healthy'
        }
        
        # Проверка БД
        if os.path.exists(self.db_path):
            db_size = os.path.getsize(self.db_path)
            health['database'] = {
                'status': 'online',
                'size_mb': round(db_size / 1024 / 1024, 2),
                'path': str(self.db_path)
            }
        else:
            health['database'] = {'status': 'missing'}
            health['status'] = 'warning'
        
        # Проверка конфигурации
        config_path = PROJECT_ROOT / 'config' / 'config_v4.json'
        if os.path.exists(config_path):
            health['config'] = {'status': 'found'}
        else:
            health['config'] = {'status': 'missing'}
            health['status'] = 'warning'
        
        # Проверка логов
        logs_dir = PROJECT_ROOT / 'logs'
        if logs_dir.exists():
            log_files = list(logs_dir.glob('*.log'))
            health['logs'] = {
                'status': 'available',
                'count': len(log_files)
            }
        else:
            health['logs'] = {'status': 'no_logs'}
        
        return health
    
    def run_functional_tests(self) -> Dict[str, Any]:
        """Запуск функциональных тестов"""
        try:
            # Импортируем наш test runner
            from tests.functional_test_runner import FunctionalTestRunner
            
            runner = FunctionalTestRunner()
            report = runner.run_all_tests(verbose=False)
            
            return {
                'status': 'completed',
                'report': report
            }
            
        except Exception as e:
            return {
                'status': 'error', 
                'error': str(e)
            }


# Создаем сервис мониторинга
monitoring = MonitoringService()


@app.route('/')
def dashboard():
    """Главная страница дашборда"""
    return render_template('monitoring_dashboard.html')


@app.route('/api/stats')
def api_stats():
    """API: Основная статистика"""
    try:
        return jsonify(monitoring.get_database_stats())
    except Exception as e:
        print(f"❌ API stats error: {e}")  # // Chg_FIX_API_2009: добавлено логирование
        return jsonify({
            'error': str(e),
            'basic_stats': {
                'total_vacancies': 0,
                'db_size_mb': 0
            },
            'changes_stats': {
                'vacancies': {
                    'new_vacancies': 0,
                    'new_versions': 0, 
                    'duplicates_skipped': 0,
                    'efficiency_percentage': 0,
                    'total_changes': 0
                },
                'employers': {'total_changes': 0},
                'summary': {
                    'total_operations': 0,
                    'overall_efficiency': 0
                }
            },
            'system_info': {'tables_count': 0},
            'status': 'error'
        }), 500


@app.route('/api/data-profile')
def api_data_profile():
    """API: Профиль данных"""
    try:
        return jsonify(monitoring.get_data_profile())
    except Exception as e:
        print(f"❌ API data-profile error: {e}")  # // Chg_FIX_API_2009
        return jsonify({
            'error': str(e),
            'vacancies': {
                'total_count': 0,
                'salary_distribution': {},
                'top_employers': {},
                'experience_distribution': {},
                'recent_activity': {}
            },
            'employers': {'total_count': 0},
            'time_analysis': {},
            'status': 'error'
        }), 500


@app.route('/api/health')
def api_health():
    """API: Состояние системы"""
    return jsonify(monitoring.get_system_health())


@app.route('/api/run-tests', methods=['POST'])
def api_run_tests():
    """API: Запуск функциональных тестов"""
    return jsonify(monitoring.run_functional_tests())


@app.route('/api/version')
def api_version():
    """API: Информация о версии"""
    return jsonify({
        'version': 'HH-бот v4',
        'build_date': '2025-09-20',
        'status': 'development'
    })


if __name__ == '__main__':
    print("🚀 Запуск веб-панели мониторинга HH-бота v4")
    print("📊 Доступна по адресу: http://localhost:5000")
    print("🔄 Автообновление каждые 30 секунд")
    print()
    
    app.run(host='0.0.0.0', port=5000, debug=True)
