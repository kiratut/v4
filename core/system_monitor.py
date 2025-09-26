#!/usr/bin/env python3
"""
HH v4 SYSTEM MONITOR MODULE
Модуль системного мониторинга и самодиагностики

Соответствует требованиям: 2.1.* (самодиагностика)
Автор: AI Assistant
Дата: 23.09.2025
"""

import os
import sys
import time
import json
import psutil
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


class SystemHealthAlert:
    """Структура для системных алертов"""
    def __init__(self, alert_type: str, severity: str, message: str, metrics: Dict = None):
        self.alert_type = alert_type
        self.severity = severity  # INFO, WARNING, CRITICAL
        self.message = message
        self.metrics = metrics or {}
        self.timestamp = datetime.now()


class SystemMonitor:
    """Основной класс системного мониторинга"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "config_v4.json")
        self.config = self._load_config()
        self.monitoring_config = self.config.get('system_monitoring', {})
        self.logger = logging.getLogger(__name__)
        self._last_check_time = 0
        self._cached_info = {}
        
    def _load_config(self) -> Dict:
        """Загрузка конфигурации мониторинга"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить конфигурацию: {e}")
            return {}
    
    def check_system_resources(self) -> Dict[str, Any]:
        """2.1.1 - Проверка CPU/RAM/Disk мониторинга"""
        try:
            # CPU метрики
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory метрики
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk метрики (для текущего диска проекта)
            project_path = Path(__file__).parent.parent
            disk_usage = psutil.disk_usage(str(project_path))
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            # Дополнительные системные метрики
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cpu': {
                    'percent': cpu_percent,
                    'count': cpu_count,
                    'load_avg': getattr(os, 'getloadavg', lambda: [0, 0, 0])()[:3] if hasattr(os, 'getloadavg') else [0, 0, 0]
                },
                'memory': {
                    'percent': memory.percent,
                    'total_gb': memory.total / (1024**3),
                    'available_gb': memory.available / (1024**3),
                    'used_gb': memory.used / (1024**3)
                },
                'swap': {
                    'percent': swap.percent,
                    'total_gb': swap.total / (1024**3) if swap.total > 0 else 0
                },
                'disk': {
                    'percent': disk_percent,
                    'total_gb': disk_usage.total / (1024**3),
                    'free_gb': disk_usage.free / (1024**3),
                    'used_gb': disk_usage.used / (1024**3)
                },
                'system': {
                    'uptime_hours': uptime_seconds / 3600,
                    'process_count': len(psutil.pids())
                }
            }
            
            # Проверка пороговых значений и генерация алертов
            alerts = self._check_resource_thresholds(metrics)
            
            return {
                'status': 'OK',
                'metrics': metrics,
                'alerts': alerts
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка мониторинга ресурсов: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'metrics': {},
                'alerts': []
            }
    
    def check_daemon_status(self) -> Dict[str, Any]:
        """2.1.2 - Проверка статуса демона и времени запуска"""
        try:
            daemon_info = {
                'daemon_found': False,
                'daemon_count': 0,
                'processes': [],
                'state_file_exists': False,
                'pid_file_exists': False
            }
            
            # Поиск процессов демона
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'memory_info', 'status']):
                try:
                    cmdline = proc.info['cmdline'] or []
                    if any('scheduler_daemon' in str(cmd) or 'daemon' in str(cmd) for cmd in cmdline):
                        daemon_info['daemon_found'] = True
                        daemon_info['daemon_count'] += 1
                        
                        uptime_seconds = time.time() - proc.info['create_time']
                        daemon_info['processes'].append({
                            'pid': proc.info['pid'],
                            'name': proc.info['name'],
                            'status': proc.info['status'],
                            'memory_mb': proc.info['memory_info'].rss / (1024*1024),
                            'uptime_seconds': uptime_seconds,
                            'uptime_hours': uptime_seconds / 3600,
                            'cmdline': ' '.join(cmdline)
                        })
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # Проверка файлов состояния
            state_file = Path(__file__).parent.parent / "data" / "daemon.state"
            pid_file = Path(__file__).parent.parent / "data" / "daemon.pid"
            
            daemon_info['state_file_exists'] = state_file.exists()
            daemon_info['pid_file_exists'] = pid_file.exists()
            
            # Чтение информации из файлов состояния
            if daemon_info['state_file_exists']:
                try:
                    with open(state_file, 'r') as f:
                        daemon_info['state_file_content'] = f.read().strip()
                except Exception as e:
                    daemon_info['state_file_error'] = str(e)
            
            if daemon_info['pid_file_exists']:
                try:
                    with open(pid_file, 'r') as f:
                        stored_pid = int(f.read().strip())
                        daemon_info['stored_pid'] = stored_pid
                        
                        # Проверяем что процесс с таким PID действительно существует
                        if psutil.pid_exists(stored_pid):
                            daemon_info['stored_pid_exists'] = True
                        else:
                            daemon_info['stored_pid_exists'] = False
                            daemon_info['pid_file_stale'] = True
                            
                except (ValueError, FileNotFoundError) as e:
                    daemon_info['pid_file_error'] = str(e)
            
            # Определение общего статуса
            if daemon_info['daemon_count'] == 1:
                status = 'OK'
                message = f"Демон активен (PID: {daemon_info['processes'][0]['pid']})"
            elif daemon_info['daemon_count'] > 1:
                status = 'WARNING'
                message = f"Обнаружено {daemon_info['daemon_count']} процессов демона"
            elif daemon_info['state_file_exists'] or daemon_info['pid_file_exists']:
                status = 'WARNING'
                message = "Демон не найден в процессах, но есть файлы состояния"
            else:
                status = 'CRITICAL'
                message = "Демон не обнаружен"
            
            return {
                'status': status,
                'message': message,
                'daemon_info': daemon_info
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки демона: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'daemon_info': {}
            }
    
    def check_hh_authorization(self) -> Dict[str, Any]:
        """2.1.3 - Проверка профилей авторизации HH"""
        try:
            auth_config_path = Path(__file__).parent.parent / "config" / "auth_roles.json"
            
            if not auth_config_path.exists():
                return {
                    'status': 'WARNING',
                    'message': 'Файл профилей авторизации не найден',
                    'auth_info': {
                        'config_exists': False,
                        'total_profiles': 0,
                        'enabled_profiles': 0
                    }
                }
            
            with open(auth_config_path, 'r', encoding='utf-8') as f:
                auth_config = json.load(f)
            
            profiles = auth_config.get('profiles', [])
            enabled_profiles = [p for p in profiles if p.get('enabled', False)]
            
            # Анализ профилей
            auth_info = {
                'config_exists': True,
                'total_profiles': len(profiles),
                'enabled_profiles': len(enabled_profiles),
                'profiles_health': []
            }
            
            # Простая проверка здоровья профилей
            for profile in enabled_profiles:
                profile_health = {
                    'id': profile.get('id', 'unknown'),
                    'name': profile.get('name', 'unnamed'),
                    'has_headers': bool(profile.get('headers', {})),
                    'has_user_agent': bool(profile.get('headers', {}).get('User-Agent')),
                    'has_auth': bool(profile.get('headers', {}).get('Authorization')),
                    'priority': profile.get('priority', 0)
                }
                auth_info['profiles_health'].append(profile_health)
            
            # Определение статуса
            if len(enabled_profiles) == 0:
                status = 'WARNING'
                message = f"Нет активных профилей авторизации ({len(profiles)} всего)"
            elif len(enabled_profiles) >= 3:
                status = 'OK'
                message = f"Достаточно профилей авторизации ({len(enabled_profiles)} активных)"
            else:
                status = 'WARNING'
                message = f"Мало профилей авторизации ({len(enabled_profiles)} активных, рекомендуется 3+)"
            
            return {
                'status': status,
                'message': message,
                'auth_info': auth_info
            }
            
        except json.JSONDecodeError as e:
            return {
                'status': 'ERROR',
                'error': f'Некорректный JSON в auth_roles.json: {e}',
                'auth_info': {}
            }
        except Exception as e:
            self.logger.error(f"Ошибка проверки авторизации: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'auth_info': {}
            }
    
    def check_log_health(self) -> Dict[str, Any]:
        """2.1.6 - Проверка логов на ошибки"""
        try:
            logging_config = self.config.get('logging', {})
            log_path = Path(__file__).parent.parent / logging_config.get('file_path', 'logs/app.log')
            
            log_info = {
                'log_exists': log_path.exists(),
                'log_path': str(log_path)
            }
            
            if not log_path.exists():
                return {
                    'status': 'WARNING',
                    'message': 'Основной файл логов не найден',
                    'log_info': log_info
                }
            
            # Анализ лог-файла
            stat = log_path.stat()
            log_size_mb = stat.st_size / (1024*1024)
            log_age_hours = (time.time() - stat.st_mtime) / 3600
            
            # Подсчет записей по уровням
            error_keywords = self.monitoring_config.get('log_error_keywords', ['ERROR', 'CRITICAL', 'EXCEPTION'])
            scan_lines = self.monitoring_config.get('log_scan_lines', 1000)
            
            error_count = 0
            warning_count = 0
            total_lines = 0
            recent_errors = []
            
            try:
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    total_lines = len(lines)
                    
                    # Анализируем последние N строк
                    for line in lines[-scan_lines:]:
                        line_upper = line.upper()
                        if any(keyword in line_upper for keyword in error_keywords):
                            error_count += 1
                            if len(recent_errors) < 5:
                                recent_errors.append(line.strip())
                        elif 'WARNING' in line_upper:
                            warning_count += 1
                            
            except Exception as e:
                log_info['read_error'] = str(e)
            
            log_info.update({
                'log_size_mb': log_size_mb,
                'log_age_hours': log_age_hours,
                'total_lines': total_lines,
                'error_count': error_count,
                'warning_count': warning_count,
                'recent_errors': recent_errors,
                'lines_analyzed': min(scan_lines, total_lines)
            })
            
            # Определение статуса
            max_size_mb = logging_config.get('max_size_mb', 100)
            
            if error_count > 20:
                status = 'CRITICAL'
                message = f"Критическое количество ошибок в логах ({error_count})"
            elif error_count > 5:
                status = 'WARNING' 
                message = f"Много ошибок в логах ({error_count} в последних {scan_lines} записях)"
            elif log_size_mb > max_size_mb * 1.5:
                status = 'WARNING'
                message = f"Лог-файл значительно превышает лимит ({log_size_mb:.1f} МБ)"
            elif log_age_hours > 48:
                status = 'WARNING'
                message = f"Лог не обновлялся {log_age_hours:.1f} часов"
            else:
                status = 'OK'
                message = f"Логи в норме ({total_lines} записей, {error_count} ошибок)"
            
            return {
                'status': status,
                'message': message,
                'log_info': log_info
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки логов: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'log_info': {}
            }
    
    def generate_health_report(self, format_type: str = 'telegram') -> Dict[str, Any]:
        """2.1.7 - Генерация сжатого отчета для Telegram"""
        try:
            # Сбор всех проверок
            resource_check = self.check_system_resources()
            daemon_check = self.check_daemon_status() 
            auth_check = self.check_hh_authorization()
            log_check = self.check_log_health()
            
            checks = [
                ('Ресурсы', resource_check),
                ('Демон', daemon_check),
                ('Авторизация', auth_check),
                ('Логи', log_check)
            ]
            
            # Подсчет статусов
            status_counts = {'OK': 0, 'WARNING': 0, 'CRITICAL': 0, 'ERROR': 0}
            critical_issues = []
            warning_issues = []
            
            for name, check in checks:
                status = check.get('status', 'UNKNOWN')
                if status in status_counts:
                    status_counts[status] += 1
                    
                if status == 'CRITICAL':
                    critical_issues.append(f"{name}: {check.get('message', 'Unknown issue')}")
                elif status in ['WARNING', 'ERROR']:
                    warning_issues.append(f"{name}: {check.get('message', 'Unknown issue')}")
            
            # Определение общего здоровья
            total_checks = len(checks)
            health_score = (status_counts['OK'] / total_checks * 100) if total_checks > 0 else 0
            
            if status_counts['CRITICAL'] > 0:
                overall_status = 'CRITICAL'
                overall_emoji = '🔴'
            elif status_counts['ERROR'] > 0:
                overall_status = 'ERROR'
                overall_emoji = '❌'
            elif status_counts['WARNING'] > 0:
                overall_status = 'WARNING'
                overall_emoji = '⚠️'
            else:
                overall_status = 'OK'
                overall_emoji = '✅'
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'overall_status': overall_status,
                'overall_emoji': overall_emoji,
                'health_score': health_score,
                'status_counts': status_counts,
                'critical_issues': critical_issues,
                'warning_issues': warning_issues,
                'detailed_checks': dict(checks)
            }
            
            # Форматирование для разных целей
            if format_type == 'telegram':
                report['telegram_message'] = self._format_telegram_message(report)
            elif format_type == 'json':
                # Уже в JSON формате
                pass
            elif format_type == 'text':
                report['text_message'] = self._format_text_message(report)
            
            return report
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации отчета: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_resource_thresholds(self, metrics: Dict) -> List[SystemHealthAlert]:
        """Проверка пороговых значений ресурсов"""
        alerts = []
        
        # CPU проверки
        cpu_percent = metrics['cpu']['percent']
        cpu_threshold = self.monitoring_config.get('cpu_threshold_percent', 80)
        cpu_critical = self.monitoring_config.get('cpu_critical_percent', 95)
        
        if cpu_percent >= cpu_critical:
            alerts.append(SystemHealthAlert(
                'cpu_usage', 'CRITICAL',
                f'CPU usage critical: {cpu_percent:.1f}% (threshold: {cpu_critical}%)',
                {'cpu_percent': cpu_percent, 'threshold': cpu_critical}
            ))
        elif cpu_percent >= cpu_threshold:
            alerts.append(SystemHealthAlert(
                'cpu_usage', 'WARNING',
                f'CPU usage high: {cpu_percent:.1f}% (threshold: {cpu_threshold}%)',
                {'cpu_percent': cpu_percent, 'threshold': cpu_threshold}
            ))
        
        # Memory проверки
        memory_percent = metrics['memory']['percent']
        memory_threshold = self.monitoring_config.get('memory_threshold_percent', 85)
        memory_critical = self.monitoring_config.get('memory_critical_percent', 95)
        
        if memory_percent >= memory_critical:
            alerts.append(SystemHealthAlert(
                'memory_usage', 'CRITICAL',
                f'Memory usage critical: {memory_percent:.1f}% (threshold: {memory_critical}%)',
                {'memory_percent': memory_percent, 'threshold': memory_critical}
            ))
        elif memory_percent >= memory_threshold:
            alerts.append(SystemHealthAlert(
                'memory_usage', 'WARNING',
                f'Memory usage high: {memory_percent:.1f}% (threshold: {memory_threshold}%)',
                {'memory_percent': memory_percent, 'threshold': memory_threshold}
            ))
        
        # Disk проверки
        disk_percent = metrics['disk']['percent']
        disk_threshold = self.monitoring_config.get('disk_threshold_percent', 85)
        disk_critical = self.monitoring_config.get('disk_critical_percent', 95)
        
        if disk_percent >= disk_critical:
            alerts.append(SystemHealthAlert(
                'disk_usage', 'CRITICAL',
                f'Disk usage critical: {disk_percent:.1f}% (threshold: {disk_critical}%)',
                {'disk_percent': disk_percent, 'threshold': disk_critical}
            ))
        elif disk_percent >= disk_threshold:
            alerts.append(SystemHealthAlert(
                'disk_usage', 'WARNING',
                f'Disk usage high: {disk_percent:.1f}% (threshold: {disk_threshold}%)',
                {'disk_percent': disk_percent, 'threshold': disk_threshold}
            ))
        
        return alerts
    
    def _format_telegram_message(self, report: Dict) -> str:
        """Форматирование сообщения для Telegram"""
        emoji = report['overall_emoji']
        status = report['overall_status']
        score = report['health_score']
        
        message = f"{emoji} HH v4 System Health: {status} ({score:.0f}%)\n\n"
        
        # Критические проблемы
        if report['critical_issues']:
            message += "🔴 КРИТИЧНО:\n"
            for issue in report['critical_issues']:
                message += f"  • {issue}\n"
            message += "\n"
        
        # Предупреждения
        if report['warning_issues']:
            message += "⚠️ ПРЕДУПРЕЖДЕНИЯ:\n"
            for issue in report['warning_issues']:
                message += f"  • {issue}\n"
            message += "\n"
        
        # Краткая статистика
        counts = report['status_counts']
        message += f"📊 Статус: ✅{counts['OK']} ⚠️{counts['WARNING']} 🔴{counts['CRITICAL']} ❌{counts['ERROR']}\n"
        message += f"⏰ {datetime.now().strftime('%H:%M %d.%m.%Y')}"
        
        return message
    
    def _format_text_message(self, report: Dict) -> str:
        """Форматирование текстового сообщения"""
        lines = [
            f"HH v4 System Health Report",
            f"Overall Status: {report['overall_status']} ({report['health_score']:.0f}%)",
            f"Timestamp: {report['timestamp']}",
            ""
        ]
        
        if report['critical_issues']:
            lines.append("CRITICAL ISSUES:")
            for issue in report['critical_issues']:
                lines.append(f"  - {issue}")
            lines.append("")
        
        if report['warning_issues']:
            lines.append("WARNINGS:")
            for issue in report['warning_issues']:
                lines.append(f"  - {issue}")
            lines.append("")
        
        counts = report['status_counts']
        lines.append(f"Summary: OK:{counts['OK']} WARNING:{counts['WARNING']} CRITICAL:{counts['CRITICAL']} ERROR:{counts['ERROR']}")
        
        return "\n".join(lines)
