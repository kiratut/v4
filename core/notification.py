#!/usr/bin/env python3
"""
HH v4 NOTIFICATION MODULE
Telegram интеграция для уведомлений и алертов

Соответствует требованиям: 2.6.2 (настройки Telegram)
Автор: AI Assistant  
Дата: 23.09.2025
"""

import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from queue import Queue, Empty
import threading
import requests


class TelegramNotificationError(Exception):
    """Ошибка отправки Telegram уведомления"""
    pass


class NotificationMessage:
    """Структура сообщения для отправки"""
    def __init__(self, text: str, priority: str = 'INFO', parse_mode: str = 'HTML'):
        self.text = text
        self.priority = priority  # INFO, WARNING, CRITICAL
        self.parse_mode = parse_mode
        self.timestamp = datetime.now()
        self.attempts = 0
        self.max_attempts = 3


class TelegramNotifier:
    """Менеджер Telegram уведомлений"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(Path(__file__).parent.parent / "config" / "config_v4.json")
        self.logger = logging.getLogger(__name__)
        
        # Конфигурация
        self.config = self._load_config()
        self.telegram_config = self.config.get('telegram', {})
        
        # Состояние
        self.enabled = self.telegram_config.get('enabled', False)
        self.token = self.telegram_config.get('token', '')
        self.chat_id = self.telegram_config.get('chat_id', '')
        
        # Очередь сообщений и обработка ошибок
        self.message_queue = Queue(maxsize=self.telegram_config.get('queue_max_size', 100))
        self.error_count = 0
        self.error_threshold = self.telegram_config.get('error_threshold', 5)
        self.last_error_time = 0
        self.retry_delay_minutes = self.telegram_config.get('retry_delay_minutes', 5)
        
        # Поток обработки сообщений
        self.worker_thread = None
        self.stop_event = threading.Event()
        
        if self.enabled and self._validate_credentials():
            self._start_worker()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить конфигурацию: {e}")
            return {}
    
    def _validate_credentials(self) -> bool:
        """Проверка наличия необходимых данных для Telegram"""
        if not self.token.strip():
            self.logger.warning("Telegram token не настроен")
            return False
        
        if not self.chat_id.strip():
            self.logger.warning("Telegram chat_id не настроен")
            return False
        
        return True
    
    def _start_worker(self):
        """Запуск потока обработки сообщений"""
        if self.worker_thread and self.worker_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.worker_thread = threading.Thread(target=self._message_worker, daemon=True)
        self.worker_thread.start()
        self.logger.info("Telegram worker thread запущен")
    
    def _stop_worker(self):
        """Остановка потока обработки сообщений"""
        if self.worker_thread and self.worker_thread.is_alive():
            self.stop_event.set()
            self.worker_thread.join(timeout=5)
            self.logger.info("Telegram worker thread остановлен")
    
    def send_alert(self, message: str, severity: str = 'WARNING') -> bool:
        """Отправка критического уведомления"""
        if not self.enabled:
            self.logger.debug(f"Telegram отключен, пропускаем alert: {message}")
            return False
        
        if not self.telegram_config.get('alerts_enabled', True):
            self.logger.debug("Telegram алерты отключены в конфигурации")
            return False
        
        # Форматирование алерта
        severity_emoji = {
            'INFO': 'ℹ️',
            'WARNING': '⚠️',
            'CRITICAL': '🔴',
            'ERROR': '❌'
        }
        
        emoji = severity_emoji.get(severity, '📢')
        timestamp = datetime.now().strftime('%H:%M:%S %d.%m.%Y')
        
        formatted_message = f"{emoji} <b>HH v4 Alert</b>\n\n" \
                          f"<b>Уровень:</b> {severity}\n" \
                          f"<b>Время:</b> {timestamp}\n\n" \
                          f"{message}"
        
        return self._queue_message(formatted_message, severity)
    
    def send_daily_summary(self, summary_data: Dict[str, Any]) -> bool:
        """Отправка ежедневной сводки"""
        if not self.enabled:
            return False
        
        if not self.telegram_config.get('daily_summary_enabled', True):
            return False
        
        # Проверяем время отправки
        summary_time = self.telegram_config.get('daily_summary_time', '09:00')
        current_time = datetime.now().strftime('%H:%M')
        
        # Для тестирования можно отправлять в любое время
        # В продакшене добавить проверку времени
        
        try:
            message = self._format_daily_summary(summary_data)
            return self._queue_message(message, 'INFO')
        except Exception as e:
            self.logger.error(f"Ошибка формирования ежедневной сводки: {e}")
            return False
    
    def send_system_health(self, health_report: Dict[str, Any]) -> bool:
        """Отправка отчета о здоровье системы"""
        if not self.enabled:
            return False
        
        try:
            # Используем готовое сообщение из отчета если есть
            if 'telegram_message' in health_report:
                message = health_report['telegram_message']
            else:
                # Формируем сообщение из данных отчета
                message = self._format_health_report(health_report)
            
            # Определяем приоритет по статусу
            overall_status = health_report.get('overall_status', 'UNKNOWN')
            priority = 'CRITICAL' if overall_status == 'CRITICAL' else 'WARNING' if overall_status in ['WARNING', 'ERROR'] else 'INFO'
            
            return self._queue_message(message, priority)
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки отчета здоровья: {e}")
            return False
    
    def test_connection(self) -> Dict[str, Any]:
        """Тестирование соединения с Telegram API"""
        if not self._validate_credentials():
            return {
                'success': False,
                'error': 'Telegram credentials не настроены'
            }
        
        test_message = self.telegram_config.get('test_message', 'HH Bot v4 test message')
        
        try:
            success = self._send_message_direct(f"🧪 {test_message}\n⏰ {datetime.now().strftime('%H:%M:%S %d.%m.%Y')}")
            
            if success:
                return {
                    'success': True,
                    'message': 'Тестовое сообщение отправлено успешно'
                }
            else:
                return {
                    'success': False,
                    'error': 'Не удалось отправить тестовое сообщение'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка тестирования: {e}'
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Статус очереди сообщений"""
        return {
            'queue_size': self.message_queue.qsize(),
            'max_size': self.message_queue.maxsize,
            'worker_alive': self.worker_thread.is_alive() if self.worker_thread else False,
            'error_count': self.error_count,
            'error_threshold': self.error_threshold,
            'last_error_time': self.last_error_time,
            'enabled': self.enabled
        }
    
    def _queue_message(self, text: str, priority: str = 'INFO') -> bool:
        """Добавление сообщения в очередь"""
        try:
            # Проверка на блокировку из-за ошибок
            if self._is_temporarily_disabled():
                self.logger.warning("Telegram временно отключен из-за ошибок API")
                return False
            
            # Ограничение длины сообщения
            max_length = self.telegram_config.get('message_max_length', 4096)
            if len(text) > max_length:
                text = text[:max_length-50] + "\n\n... (сообщение обрезано)"
            
            message = NotificationMessage(text, priority)
            
            # Проверка заполнения очереди
            if self.message_queue.full():
                self.logger.warning("Очередь Telegram сообщений переполнена, пропускаем сообщение")
                return False
            
            self.message_queue.put_nowait(message)
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления сообщения в очередь: {e}")
            return False
    
    def _message_worker(self):
        """Рабочий поток для обработки очереди сообщений"""
        self.logger.info("Telegram message worker запущен")
        
        while not self.stop_event.is_set():
            try:
                # Получаем сообщение с таймаутом
                message = self.message_queue.get(timeout=1.0)
                
                # Проверяем блокировку
                if self._is_temporarily_disabled():
                    # Возвращаем сообщение в очередь для повторной попытки позже
                    if message.attempts < message.max_attempts:
                        message.attempts += 1
                        self.message_queue.put_nowait(message)
                    time.sleep(5)
                    continue
                
                # Отправляем сообщение
                success = self._send_message_direct(message.text, message.parse_mode)
                
                if success:
                    self.logger.debug(f"Telegram сообщение отправлено: {message.priority}")
                    # Сбрасываем счетчик ошибок при успешной отправке
                    self.error_count = max(0, self.error_count - 1)
                else:
                    # Повторная попытка для важных сообщений
                    message.attempts += 1
                    if message.attempts < message.max_attempts and message.priority in ['CRITICAL', 'WARNING']:
                        self.message_queue.put_nowait(message)
                        self.logger.warning(f"Повторная попытка отправки сообщения {message.attempts}/{message.max_attempts}")
                
                # Пауза между сообщениями
                time.sleep(1)
                
            except Empty:
                # Таймаут ожидания сообщения - это нормально
                continue
            except Exception as e:
                self.logger.error(f"Ошибка в Telegram worker: {e}")
                time.sleep(5)
        
        self.logger.info("Telegram message worker остановлен")
    
    def _send_message_direct(self, text: str, parse_mode: str = 'HTML') -> bool:
        """Прямая отправка сообщения в Telegram"""
        if not self._validate_credentials():
            return False
        
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 429:  # Rate limit
                self.logger.warning("Telegram rate limit превышен")
                self._handle_api_error()
                return False
            else:
                self.logger.error(f"Telegram API error {response.status_code}: {response.text}")
                self._handle_api_error()
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка сетевого запроса к Telegram: {e}")
            self._handle_api_error()
            return False
    
    def _handle_api_error(self):
        """Обработка ошибки API"""
        self.error_count += 1
        self.last_error_time = time.time()
        
        if self.error_count >= self.error_threshold:
            self.logger.warning(f"Достигнут порог ошибок Telegram API ({self.error_count}), временное отключение")
    
    def _is_temporarily_disabled(self) -> bool:
        """Проверка временной блокировки из-за ошибок"""
        if self.error_count < self.error_threshold:
            return False
        
        # Проверяем прошло ли достаточно времени для повторной попытки
        retry_delay_seconds = self.retry_delay_minutes * 60
        time_since_error = time.time() - self.last_error_time
        
        if time_since_error >= retry_delay_seconds:
            # Сбрасываем счетчик ошибок для новой попытки
            self.error_count = 0
            self.logger.info("Telegram API разблокирован после таймаута")
            return False
        
        return True
    
    def _format_daily_summary(self, summary_data: Dict[str, Any]) -> str:
        """Форматирование ежедневной сводки"""
        date_str = datetime.now().strftime('%d.%m.%Y')
        
        message_parts = [
            f"📊 <b>HH v4 Daily Summary - {date_str}</b>\n"
        ]
        
        # Статистика загрузок
        if 'vacancies' in summary_data:
            vacancies = summary_data['vacancies']
            message_parts.append(
                f"🔍 <b>Вакансии:</b>\n"
                f"  • Загружено: {vacancies.get('loaded', 0)}\n"
                f"  • Дубликаты: {vacancies.get('duplicates', 0)}\n"
                f"  • Обновлено: {vacancies.get('updated', 0)}\n"
            )
        
        # Статистика системы
        if 'system' in summary_data:
            system = summary_data['system']
            message_parts.append(
                f"💻 <b>Система:</b>\n"
                f"  • Время работы: {system.get('uptime_hours', 0):.1f}ч\n"
                f"  • Задач выполнено: {system.get('tasks_completed', 0)}\n"
                f"  • Ошибки: {system.get('errors', 0)}\n"
            )
        
        # Здоровье системы
        if 'health' in summary_data:
            health = summary_data['health']
            health_emoji = '✅' if health.get('score', 0) >= 90 else '⚠️' if health.get('score', 0) >= 70 else '🔴'
            message_parts.append(
                f"{health_emoji} <b>Здоровье системы:</b> {health.get('score', 0):.0f}%\n"
            )
        
        message_parts.append(f"\n⏰ Сформировано: {datetime.now().strftime('%H:%M:%S')}")
        
        return "\n".join(message_parts)
    
    def _format_health_report(self, health_report: Dict[str, Any]) -> str:
        """Форматирование отчета здоровья системы"""
        overall_status = health_report.get('overall_status', 'UNKNOWN')
        health_score = health_report.get('health_score', 0)
        
        status_emoji = {
            'OK': '✅',
            'WARNING': '⚠️',
            'CRITICAL': '🔴',
            'ERROR': '❌'
        }
        
        emoji = status_emoji.get(overall_status, '❓')
        
        message = f"{emoji} <b>HH v4 System Health</b>\n\n"
        message += f"<b>Статус:</b> {overall_status} ({health_score:.0f}%)\n"
        
        # Критические проблемы
        critical_issues = health_report.get('critical_issues', [])
        if critical_issues:
            message += f"\n🔴 <b>КРИТИЧНО:</b>\n"
            for issue in critical_issues[:3]:  # Показываем только первые 3
                message += f"  • {issue}\n"
        
        # Предупреждения
        warning_issues = health_report.get('warning_issues', [])
        if warning_issues:
            message += f"\n⚠️ <b>ПРЕДУПРЕЖДЕНИЯ:</b>\n"
            for issue in warning_issues[:3]:  # Показываем только первые 3
                message += f"  • {issue}\n"
        
        # Статистика
        status_counts = health_report.get('status_counts', {})
        message += f"\n📊 Проверок: ✅{status_counts.get('OK', 0)} ⚠️{status_counts.get('WARNING', 0)} 🔴{status_counts.get('CRITICAL', 0)}"
        
        message += f"\n⏰ {datetime.now().strftime('%H:%M %d.%m.%Y')}"
        
        return message
    
    def __del__(self):
        """Деструктор для корректной остановки потока"""
        self._stop_worker()


# Глобальный экземпляр нотификатора
_notifier = None

def get_notifier() -> TelegramNotifier:
    """Получение глобального экземпляра нотификатора"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier
