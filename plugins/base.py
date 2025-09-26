# Базовые классы плагинов для HH Tool v3
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import time
from core.models import Vacancy, PluginResult, PluginContext


class BasePlugin(ABC):
    """Базовый класс для всех плагинов обработки вакансий"""
    
    def __init__(self, config: Dict[str, Any]):
        self.name = self.__class__.__name__.replace('Plugin', '').lower()
        self.config = config
        self.should_persist = True  # По умолчанию сохраняем результаты в БД
        
    @abstractmethod
    async def process(self, context: PluginContext) -> PluginResult:
        """Обработка одной вакансии с контекстом других плагинов"""
        pass
    
    def should_process(self, vacancy: Vacancy, context: PluginContext) -> bool:
        """Проверка, нужно ли обрабатывать вакансию"""
        # Пропускаем если уже обработано и результат успешный
        result = context.get_result(self.name)
        if result and result.status == 'completed':
            return False
        return True
    
    def get_dependencies(self) -> List[str]:
        """Зависимости от других плагинов (выполняются ДО этого плагина)"""
        return []
    
    def validate_dependencies(self, context: PluginContext) -> bool:
        """Проверка выполнения всех зависимостей"""
        for dep_name in self.get_dependencies():
            result = context.get_result(dep_name)
            if not result or result.status != 'completed':
                return False
        return True


class SimplePlugin(BasePlugin):
    """Простой синхронный плагин (без async)"""
    
    def process_sync(self, context: PluginContext) -> PluginResult:
        """Синхронная обработка - переопределяется в наследниках"""
        return PluginResult(status='skipped', data={})
    
    async def process(self, context: PluginContext) -> PluginResult:
        """Обертка для синхронных плагинов"""
        start_time = time.time()
        try:
            result = self.process_sync(context)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return PluginResult(
                status='failed',
                error=str(e),
                execution_time=time.time() - start_time
            )


class AsyncPlugin(BasePlugin):
    """Асинхронный плагин (для API вызовов, LLM и т.д.)"""
    
    async def process_async(self, context: PluginContext) -> PluginResult:
        """Асинхронная обработка - переопределяется в наследниках"""
        return PluginResult(status='skipped', data={})
    
    async def process(self, context: PluginContext) -> PluginResult:
        """Обертка для асинхронных плагинов"""
        start_time = time.time()
        try:
            result = await self.process_async(context)
            result.execution_time = time.time() - start_time
            return result
        except Exception as e:
            return PluginResult(
                status='failed',
                error=str(e),
                execution_time=time.time() - start_time
            )
