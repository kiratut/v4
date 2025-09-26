#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Host3 Client - LLM сервис анализа вакансий

// Chg_HOST3_CLIENT_2009: Заглушка для будущего LLM хоста
Согласно Architecture_v4_Host1.md - Host3 отвечает за LLM анализ и генерацию контента
"""

import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import json
import random

logger = logging.getLogger(__name__)


class LLMTaskType(Enum):
    """Типы задач для LLM"""
    VACANCY_ANALYSIS = "vacancy_analysis"
    SKILL_EXTRACTION = "skill_extraction" 
    SALARY_PREDICTION = "salary_prediction"
    TEXT_CLASSIFICATION = "text_classification"
    SUMMARY_GENERATION = "summary_generation"
    MATCHING_SCORE = "matching_score"


@dataclass
class LLMRequest:
    """Запрос к LLM сервису"""
    task_type: LLMTaskType
    input_data: Dict[str, Any]
    model: str = "gpt-3.5-turbo"
    temperature: float = 0.3
    max_tokens: int = 1000
    system_prompt: Optional[str] = None


@dataclass
class LLMResponse:
    """Ответ от LLM сервиса"""
    request_id: str
    task_type: LLMTaskType
    result: Dict[str, Any]
    confidence: float
    processing_time_ms: int
    model_used: str
    timestamp: datetime
    status: str  # 'success', 'error', 'partial'
    error_message: Optional[str] = None


class LLMClient:
    """
    Клиент для подключения к LLM сервису (Host3)
    
    В MVP работает как заглушка с предопределенными ответами.
    В будущем будет подключаться к реальному LLM API (OpenAI, Anthropic, локальная модель).
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация LLM клиента
        
        Args:
            config: Конфигурация подключения
        """
        self.config = config
        self.api_endpoint = config.get('api_endpoint', 'http://localhost:8000/v1')
        self.api_key = config.get('api_key', 'mock_api_key')
        self.default_model = config.get('default_model', 'gpt-3.5-turbo')
        self.mock_mode = config.get('mock_mode', True)  # В MVP всегда True
        self.timeout = config.get('timeout', 30)
        
        self._request_count = 0
        self._last_request = None
        
        logger.info(f"LLMClient initialized: {self.api_endpoint}")
        if self.mock_mode:
            logger.info("LLM client running in MOCK MODE")
    
    def is_available(self) -> bool:
        """Проверка доступности LLM сервиса"""
        if self.mock_mode:
            return True
        
        # В будущем: реальная проверка API
        # response = requests.get(f"{self.api_endpoint}/health")
        # return response.status_code == 200
        return False
    
    def process_request(self, request: LLMRequest) -> LLMResponse:
        """
        Обработка запроса к LLM
        
        Args:
            request: Параметры запроса
            
        Returns:
            LLMResponse: Результат обработки
        """
        self._request_count += 1
        self._last_request = datetime.now()
        
        if self.mock_mode:
            return self._generate_mock_response(request)
        
        # В будущем: реальный API запрос
        # response = requests.post(f"{self.api_endpoint}/completions", ...)
        raise NotImplementedError("Real LLM API not implemented")
    
    def _generate_mock_response(self, request: LLMRequest) -> LLMResponse:
        """Генерация mock ответа от LLM"""
        request_id = f"mock_{self._request_count}_{datetime.now().strftime('%H%M%S')}"
        
        # Генерируем результат в зависимости от типа задачи
        if request.task_type == LLMTaskType.VACANCY_ANALYSIS:
            result = self._mock_vacancy_analysis(request.input_data)
        elif request.task_type == LLMTaskType.SKILL_EXTRACTION:
            result = self._mock_skill_extraction(request.input_data)
        elif request.task_type == LLMTaskType.SALARY_PREDICTION:
            result = self._mock_salary_prediction(request.input_data)
        elif request.task_type == LLMTaskType.TEXT_CLASSIFICATION:
            result = self._mock_text_classification(request.input_data)
        elif request.task_type == LLMTaskType.SUMMARY_GENERATION:
            result = self._mock_summary_generation(request.input_data)
        elif request.task_type == LLMTaskType.MATCHING_SCORE:
            result = self._mock_matching_score(request.input_data)
        else:
            result = {'error': f'Unknown task type: {request.task_type}'}
        
        return LLMResponse(
            request_id=request_id,
            task_type=request.task_type,
            result=result,
            confidence=random.uniform(0.7, 0.95),
            processing_time_ms=random.randint(500, 2000),
            model_used=request.model,
            timestamp=datetime.now(),
            status='success'
        )
    
    def _mock_vacancy_analysis(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock анализ вакансии"""
        vacancy_title = input_data.get('title', 'Unknown Position')
        
        return {
            'analysis': f"Вакансия '{vacancy_title}' требует опыта в Python разработке. "
                       f"Компания предлагает конкурентную зарплату и возможности роста.",
            'key_requirements': ['Python', 'Django/Flask', 'PostgreSQL', 'Docker'],
            'experience_level': random.choice(['Junior', 'Middle', 'Senior']),
            'remote_work': random.choice([True, False]),
            'complexity_score': random.uniform(0.3, 0.9),
            'market_attractiveness': random.uniform(0.5, 0.95)
        }
    
    def _mock_skill_extraction(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock извлечение навыков"""
        description = input_data.get('description', '')
        
        # Предопределенные навыки для демонстрации
        all_skills = [
            'Python', 'JavaScript', 'Java', 'C++', 'Django', 'Flask', 
            'React', 'Vue.js', 'PostgreSQL', 'MySQL', 'Redis', 'Docker',
            'Kubernetes', 'Git', 'Linux', 'AWS', 'Machine Learning'
        ]
        
        # Возвращаем случайные навыки
        extracted_skills = random.sample(all_skills, random.randint(3, 8))
        
        return {
            'technical_skills': extracted_skills[:5],
            'soft_skills': ['Командная работа', 'Аналитическое мышление', 'Коммуникация'],
            'required_experience': f"{random.randint(1, 5)} лет",
            'skill_confidence': {skill: random.uniform(0.6, 0.95) for skill in extracted_skills}
        }
    
    def _mock_salary_prediction(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock предсказание зарплаты"""
        base_salary = random.randint(80000, 300000)
        
        return {
            'predicted_salary_min': base_salary,
            'predicted_salary_max': int(base_salary * 1.4),
            'currency': 'RUR',
            'confidence': random.uniform(0.7, 0.9),
            'factors': {
                'experience': 0.4,
                'skills': 0.3,
                'location': 0.2,
                'company_size': 0.1
            },
            'market_comparison': 'above_average'
        }
    
    def _mock_text_classification(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock классификация текста"""
        categories = ['Web Development', 'Data Science', 'DevOps', 'Mobile', 'QA']
        
        return {
            'primary_category': random.choice(categories),
            'secondary_categories': random.sample(categories, 2),
            'category_scores': {cat: random.uniform(0.1, 0.9) for cat in categories},
            'confidence': random.uniform(0.75, 0.95)
        }
    
    def _mock_summary_generation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock генерация резюме"""
        return {
            'summary': "Интересная позиция Python разработчика с возможностями роста. "
                      "Компания предлагает работу с современными технологиями и конкурентную зарплату.",
            'highlights': [
                "Работа с Python и Django",
                "Удаленная работа доступна",
                "Конкурентная зарплата",
                "Возможности профессионального роста"
            ],
            'word_count': 156,
            'readability_score': random.uniform(0.7, 0.9)
        }
    
    def _mock_matching_score(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock оценка соответствия"""
        return {
            'overall_match': random.uniform(0.5, 0.95),
            'skill_match': random.uniform(0.6, 0.9),
            'experience_match': random.uniform(0.4, 0.8),
            'location_match': random.uniform(0.8, 1.0),
            'salary_match': random.uniform(0.5, 0.9),
            'recommendation': random.choice(['strongly_recommend', 'recommend', 'consider', 'skip']),
            'match_explanation': "Высокое соответствие по техническим навыкам и опыту работы."
        }
    
    def analyze_vacancy(self, vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Анализ вакансии через LLM"""
        request = LLMRequest(
            task_type=LLMTaskType.VACANCY_ANALYSIS,
            input_data=vacancy_data
        )
        response = self.process_request(request)
        return response.result
    
    def extract_skills(self, description: str) -> Dict[str, Any]:
        """Извлечение навыков из описания"""
        request = LLMRequest(
            task_type=LLMTaskType.SKILL_EXTRACTION,
            input_data={'description': description}
        )
        response = self.process_request(request)
        return response.result
    
    def predict_salary(self, vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Предсказание зарплаты"""
        request = LLMRequest(
            task_type=LLMTaskType.SALARY_PREDICTION,
            input_data=vacancy_data
        )
        response = self.process_request(request)
        return response.result
    
    def generate_summary(self, vacancy_data: Dict[str, Any]) -> str:
        """Генерация краткого описания"""
        request = LLMRequest(
            task_type=LLMTaskType.SUMMARY_GENERATION,
            input_data=vacancy_data
        )
        response = self.process_request(request)
        return response.result.get('summary', 'Summary not available')
    
    def calculate_matching_score(self, vacancy_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Расчет соответствия вакансии профилю пользователя"""
        request = LLMRequest(
            task_type=LLMTaskType.MATCHING_SCORE,
            input_data={
                'vacancy': vacancy_data,
                'user_profile': user_profile
            }
        )
        response = self.process_request(request)
        return response.result
    
    def batch_process(self, requests: List[LLMRequest]) -> List[LLMResponse]:
        """Пакетная обработка запросов"""
        results = []
        for request in requests:
            results.append(self.process_request(request))
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Статистика использования LLM"""
        return {
            'total_requests': self._request_count,
            'last_request': self._last_request.isoformat() if self._last_request else None,
            'mock_mode': self.mock_mode,
            'model': self.default_model,
            'endpoint': self.api_endpoint,
            'status': 'available' if self.is_available() else 'unavailable'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Проверка состояния LLM сервиса"""
        return {
            'service': 'llm_client',
            'status': 'healthy' if self.is_available() else 'unavailable',
            'mock_mode': self.mock_mode,
            'endpoint': self.api_endpoint,
            'model': self.default_model,
            'requests_processed': self._request_count,
            'timestamp': datetime.now().isoformat()
        }


def create_host3_client(config: Dict[str, Any]) -> LLMClient:
    """
    Factory функция для создания LLM клиента
    
    Args:
        config: Конфигурация подключения
        
    Returns:
        LLMClient: Настроенный клиент
    """
    client = LLMClient(config)
    
    if not client.is_available() and not client.mock_mode:
        logger.warning("LLM service unavailable, switching to mock mode")
        client.mock_mode = True
    
    return client


# Convenience функции для быстрого использования
def quick_analyze_vacancy(client: LLMClient, title: str, description: str, company: str = None) -> Dict[str, Any]:
    """Быстрый анализ вакансии"""
    vacancy_data = {
        'title': title,
        'description': description,
        'company': company or 'Unknown Company'
    }
    return client.analyze_vacancy(vacancy_data)


def quick_extract_skills(client: LLMClient, description: str) -> List[str]:
    """Быстрое извлечение навыков"""
    result = client.extract_skills(description)
    return result.get('technical_skills', []) + result.get('soft_skills', [])
