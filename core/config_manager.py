#!/usr/bin/env python3
"""
HH v4 CONFIG MANAGER MODULE
Единое управление настройками системы

Соответствует требованиям: 2.6.* (настройки)
Автор: AI Assistant
Дата: 23.09.2025
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union


class ConfigValidationError(Exception):
    """Ошибка валидации конфигурации"""
    pass


class ConfigManager:
    """Менеджер конфигурации для HH v4"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent.parent / "config"
        self.logger = logging.getLogger(__name__)
        self._config_cache = {}
        self._validators = self._setup_validators()
    
    def load_config(self, config_name: str = 'config_v4.json') -> Dict[str, Any]:
        """2.6.4 - Загрузка основной конфигурации"""
        config_path = self.config_dir / config_name
        
        if not config_path.exists():
            raise ConfigValidationError(f"Файл конфигурации не найден: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Валидация конфигурации
            self._validate_config(config, config_name)
            
            # Кэширование
            self._config_cache[config_name] = config
            
            self.logger.info(f"Конфигурация {config_name} успешно загружена")
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Некорректный JSON в {config_path}: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Ошибка загрузки конфигурации {config_path}: {e}")
    
    def get_auth_settings(self) -> Dict[str, Any]:
        """2.6.5 - Настройки авторизации HH"""
        try:
            auth_config_path = self.config_dir / "auth_roles.json"
            
            if not auth_config_path.exists():
                self.logger.warning("Файл auth_roles.json не найден, возвращаем настройки по умолчанию")
                return self._get_default_auth_settings()
            
            with open(auth_config_path, 'r', encoding='utf-8') as f:
                auth_config = json.load(f)
            
            # Валидация структуры auth_roles.json
            required_sections = ['config', 'profiles']
            missing_sections = [s for s in required_sections if s not in auth_config]
            
            if missing_sections:
                raise ConfigValidationError(f"Отсутствуют секции в auth_roles.json: {missing_sections}")
            
            config_section = auth_config.get('config', {})
            profiles = auth_config.get('profiles', [])
            
            # Подсчет активных профилей
            enabled_profiles = [p for p in profiles if p.get('enabled', False)]
            
            result = {
                'profiles_enabled': config_section.get('profiles_enabled', True),
                'rotation_strategy': config_section.get('rotation_strategy', 'round_robin'),
                'profile_cooldown_minutes': config_section.get('profile_cooldown_minutes', 30),
                'fallback_user_agent': config_section.get('fallback_user_agent', 'Mozilla/5.0 (compatible; HHBot/1.0)'),
                'health_check_interval_minutes': config_section.get('health_check_interval_minutes', 15),
                'ban_detection_keywords': config_section.get('ban_detection_keywords', ['blocked', 'banned', 'rate limit']),
                'captcha_detection_keywords': config_section.get('captcha_detection_keywords', ['captcha', 'verification']),
                'max_consecutive_failures': config_section.get('max_consecutive_failures', 5),
                'recovery_check_interval_minutes': config_section.get('recovery_check_interval_minutes', 60),
                'profile_timeout_sec': config_section.get('profile_timeout_sec', 30),
                'total_profiles': len(profiles),
                'enabled_profiles': len(enabled_profiles),
                'profiles': profiles
            }
            
            self.logger.debug(f"Загружены настройки авторизации: {len(enabled_profiles)} активных профилей")
            return result
            
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Некорректный JSON в auth_roles.json: {e}")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки настроек авторизации: {e}")
            return self._get_default_auth_settings()
    
    def get_dispatcher_settings(self) -> Dict[str, Any]:
        """2.6.6 - Параметры диспетчера задач"""
        main_config = self._get_cached_config()
        dispatcher_config = main_config.get('task_dispatcher', {})
        
        return {
            'enabled': dispatcher_config.get('enabled', True),
            'worker_pool_size': dispatcher_config.get('max_workers', 3),  # совместимость со старым названием
            'max_workers': dispatcher_config.get('max_workers', 3),
            'dynamic_scaling_enabled': dispatcher_config.get('dynamic_scaling_enabled', False),
            'min_workers': dispatcher_config.get('min_workers', 1),
            'queue_max_size': dispatcher_config.get('queue_max_size', 10000),
            'chunk_size': dispatcher_config.get('chunk_size', 500),
            'monitor_interval_sec': dispatcher_config.get('monitor_interval_sec', 10),
            'task_timeout_sec': dispatcher_config.get('default_timeout_sec', 3600),
            'health_check_interval_sec': dispatcher_config.get('health_check_interval_sec', 30),
            'failed_task_retry_limit': dispatcher_config.get('failed_task_retry_limit', 3),
            'retry_delay_multiplier': dispatcher_config.get('retry_delay_multiplier', 2.0),
            'metrics_collection_enabled': dispatcher_config.get('metrics_collection_enabled', True),
            'metrics_retention_hours': dispatcher_config.get('metrics_retention_hours', 168),
            'priority_queue_enabled': dispatcher_config.get('priority_queue_enabled', True),
            'deadlock_detection_enabled': dispatcher_config.get('deadlock_detection_enabled', True),
            'worker_memory_limit_mb': dispatcher_config.get('worker_memory_limit_mb', 512)
        }
    
    def get_logging_settings(self) -> Dict[str, Any]:
        """2.6.7 - Настройки логирования"""
        main_config = self._get_cached_config()
        logging_config = main_config.get('logging', {})
        
        return {
            'level': logging_config.get('level', 'INFO'),
            'file_enabled': logging_config.get('file_enabled', True),
            'file_path': logging_config.get('file', 'logs/app.log'),  # совместимость
            'max_size_mb': logging_config.get('max_size_mb', 100),
            'backup_count': logging_config.get('backup_count', 5),
            'rotation_enabled': logging_config.get('rotation_enabled', True),
            'format': logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            'date_format': logging_config.get('date_format', '%Y-%m-%d %H:%M:%S'),
            'db_enabled': logging_config.get('db_enabled', False),
            'db_table': logging_config.get('db_table', 'system_logs'),
            'db_retention_days': logging_config.get('db_retention_days', 30),
            'db_level_filter': logging_config.get('db_level_filter', 'WARNING'),
            'console_enabled': logging_config.get('console_enabled', True),
            'console_level': logging_config.get('console_level', 'INFO'),
            'structured_format': logging_config.get('structured_format', False),
            'module_filters': logging_config.get('module_filters', {})
        }
    
    def get_monitoring_settings(self) -> Dict[str, Any]:
        """2.6.8 - Настройки самодиагностики"""
        main_config = self._get_cached_config()
        monitoring_config = main_config.get('system_monitoring', {})
        
        return {
            'enabled': monitoring_config.get('enabled', True),
            'interval_minutes': monitoring_config.get('interval_minutes', 5),
            'cpu_threshold_percent': monitoring_config.get('cpu_threshold_percent', 80),
            'cpu_critical_percent': monitoring_config.get('cpu_critical_percent', 95),
            'memory_threshold_percent': monitoring_config.get('memory_threshold_percent', 85),
            'memory_critical_percent': monitoring_config.get('memory_critical_percent', 95),
            'disk_threshold_percent': monitoring_config.get('disk_threshold_percent', 85),
            'disk_critical_percent': monitoring_config.get('disk_critical_percent', 95),
            'load_average_threshold': monitoring_config.get('load_average_threshold', 4.0),
            'process_count_threshold': monitoring_config.get('process_count_threshold', 1000),
            'log_error_keywords': monitoring_config.get('log_error_keywords', ['ERROR', 'CRITICAL', 'EXCEPTION']),
            'log_scan_lines': monitoring_config.get('log_scan_lines', 1000),
            'health_report_format': monitoring_config.get('health_report_format', 'telegram'),
            'alert_cooldown_minutes': monitoring_config.get('alert_cooldown_minutes', 30),
            'system_info_cache_minutes': monitoring_config.get('system_info_cache_minutes', 2),
            'network_check_enabled': monitoring_config.get('network_check_enabled', True),
            'network_test_hosts': monitoring_config.get('network_test_hosts', ['8.8.8.8', 'api.hh.ru']),
            'service_dependencies': monitoring_config.get('service_dependencies', [])
        }
    
    def get_telegram_settings(self) -> Dict[str, Any]:
        """2.6.2 - Настройки Telegram"""
        main_config = self._get_cached_config()
        telegram_config = main_config.get('telegram', {})
        
        return {
            'token': telegram_config.get('token', ''),
            'chat_id': telegram_config.get('chat_id', ''),
            'enabled': telegram_config.get('enabled', False),
            'alerts_enabled': telegram_config.get('alerts_enabled', True),
            'daily_summary_enabled': telegram_config.get('daily_summary_enabled', True),
            'daily_summary_time': telegram_config.get('daily_summary_time', '09:00'),
            'retry_delay_minutes': telegram_config.get('retry_delay_minutes', 5),
            'message_max_length': telegram_config.get('message_max_length', 4096),
            'test_message': telegram_config.get('test_message', 'HH Bot v4 test message'),
            'error_threshold': telegram_config.get('error_threshold', 5),
            'queue_max_size': telegram_config.get('queue_max_size', 100)
        }
    
    def get_database_settings(self) -> Dict[str, Any]:
        """Настройки базы данных"""
        main_config = self._get_cached_config()
        db_config = main_config.get('database', {})
        
        return {
            'path': db_config.get('path', 'data/hh_v4.sqlite3'),
            'timeout_sec': db_config.get('timeout_sec', 30),
            'wal_mode': db_config.get('wal_mode', True),
            'backup_enabled': db_config.get('backup_enabled', True),
            'backup_interval_hours': db_config.get('backup_interval_hours', 24),
            'vacuum_enabled': db_config.get('vacuum_enabled', True)
        }
    
    def get_api_settings(self) -> Dict[str, Any]:
        """Настройки API"""
        main_config = self._get_cached_config()
        api_config = main_config.get('api', {})
        
        return {
            'base_url': api_config.get('base_url', 'https://api.hh.ru'),
            'user_agent': api_config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'max_retries': api_config.get('max_retries', 3)
        }
    
    def get_cleanup_settings(self) -> Dict[str, Any]:
        """Настройки очистки"""
        main_config = self._get_cached_config()
        cleanup_config = main_config.get('cleanup', {})
        
        return {
            'auto_cleanup_enabled': cleanup_config.get('auto_cleanup_enabled', True),
            'interval_hours': cleanup_config.get('cleanup_interval_hours', 24),
            'keep_tasks_days': cleanup_config.get('keep_tasks_days', 7),
            'keep_logs_days': cleanup_config.get('keep_logs_days', 30)
        }
    
    def update_setting(self, section: str, key: str, value: Any, config_name: str = 'config_v4.json') -> bool:
        """Обновление отдельного параметра конфигурации"""
        try:
            config = self.load_config(config_name)
            
            if section not in config:
                config[section] = {}
            
            old_value = config[section].get(key)
            config[section][key] = value
            
            # Сохранение обновленной конфигурации
            config_path = self.config_dir / config_name
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # Обновление кэша
            self._config_cache[config_name] = config
            
            self.logger.info(f"Обновлен параметр {section}.{key}: {old_value} -> {value}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка обновления параметра {section}.{key}: {e}")
            return False
    
    def validate_all_configs(self) -> Dict[str, List[str]]:
        """Валидация всех конфигурационных файлов"""
        validation_results = {}
        
        # Основная конфигурация
        try:
            self.load_config('config_v4.json')
            validation_results['config_v4.json'] = []
        except ConfigValidationError as e:
            validation_results['config_v4.json'] = [str(e)]
        
        # Авторизация
        try:
            self.get_auth_settings()
            validation_results['auth_roles.json'] = []
        except ConfigValidationError as e:
            validation_results['auth_roles.json'] = [str(e)]
        
        # Фильтры
        try:
            filters_path = self.config_dir / "filters.json"
            if filters_path.exists():
                with open(filters_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                validation_results['filters.json'] = []
            else:
                validation_results['filters.json'] = ['Файл не найден (опционально)']
        except Exception as e:
            validation_results['filters.json'] = [str(e)]
        
        return validation_results
    
    def _get_cached_config(self, config_name: str = 'config_v4.json') -> Dict[str, Any]:
        """Получение конфигурации из кэша или загрузка"""
        if config_name not in self._config_cache:
            return self.load_config(config_name)
        return self._config_cache[config_name]
    
    def _get_default_auth_settings(self) -> Dict[str, Any]:
        """Настройки авторизации по умолчанию"""
        return {
            'profiles_enabled': False,
            'rotation_strategy': 'round_robin',
            'profile_cooldown_minutes': 30,
            'fallback_user_agent': 'Mozilla/5.0 (compatible; HHBot/1.0)',
            'health_check_interval_minutes': 15,
            'ban_detection_keywords': ['blocked', 'banned', 'rate limit', 'captcha'],
            'captcha_detection_keywords': ['captcha', 'verification', 'robot'],
            'max_consecutive_failures': 5,
            'recovery_check_interval_minutes': 60,
            'profile_timeout_sec': 30,
            'total_profiles': 0,
            'enabled_profiles': 0,
            'profiles': []
        }
    
    def _setup_validators(self) -> Dict[str, callable]:
        """Настройка валидаторов конфигурации"""
        return {
            'config_v4.json': self._validate_main_config,
            'auth_roles.json': self._validate_auth_config
        }
    
    def _validate_config(self, config: Dict[str, Any], config_name: str):
        """Валидация конфигурации"""
        if config_name in self._validators:
            self._validators[config_name](config)
    
    def _validate_main_config(self, config: Dict[str, Any]):
        """Валидация основной конфигурации"""
        required_sections = ['database', 'task_dispatcher', 'logging']
        missing_sections = [s for s in required_sections if s not in config]
        
        if missing_sections:
            raise ConfigValidationError(f"Отсутствуют обязательные секции: {missing_sections}")
        
        # Валидация типов данных
        db_config = config.get('database', {})
        if 'timeout_sec' in db_config and not isinstance(db_config['timeout_sec'], (int, float)):
            raise ConfigValidationError("database.timeout_sec должен быть числом")
        
        dispatcher_config = config.get('task_dispatcher', {})
        if 'max_workers' in dispatcher_config and not isinstance(dispatcher_config['max_workers'], int):
            raise ConfigValidationError("task_dispatcher.max_workers должен быть целым числом")
    
    def _validate_auth_config(self, config: Dict[str, Any]):
        """Валидация конфигурации авторизации"""
        if 'profiles' not in config:
            raise ConfigValidationError("Отсутствует секция profiles в auth_roles.json")
        
        profiles = config.get('profiles', [])
        if not isinstance(profiles, list):
            raise ConfigValidationError("profiles должен быть массивом")
        
        for i, profile in enumerate(profiles):
            if not isinstance(profile, dict):
                raise ConfigValidationError(f"profile[{i}] должен быть объектом")
            
            if 'id' not in profile:
                raise ConfigValidationError(f"profile[{i}] должен содержать поле id")


# Глобальный экземпляр менеджера конфигурации
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Получение глобального экземпляра менеджера конфигурации"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
