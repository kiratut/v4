"""
Синхронный загрузчик вакансий с chunked processing для HH Tool v4
Простая архитектура без async/await
"""

import requests
import time
import logging
import json
from typing import Dict, List, Optional
from pathlib import Path
import random
# Опциональные импорты для совместимости
try:
    from core.task_database import TaskDatabase
except ImportError:
    TaskDatabase = None

try:
    from core.auth import apply_auth_headers, mark_provider_failed, rotate_to_next_provider, choose_provider
except ImportError:
    def apply_auth_headers(headers):
        return headers
    def mark_provider_failed(provider_name):
        pass
    def rotate_to_next_provider(purpose="download"):
        return None
    def choose_provider(purpose="download"):
        return None


class ExponentialBackoff:
    """
    Exponential backoff handler for API retry logic
    // Chg_BACKOFF_1909: Implements 1s->4s->16s->64s delays as specified
    """
    
    def __init__(self, base_delay: float = 1.0, max_retries: int = 4, jitter: bool = True):
        self.base_delay = base_delay
        self.max_retries = max_retries
        self.jitter = jitter
        self.retry_count = 0
        
    def get_delay(self) -> float:
        """Calculate delay for current retry attempt"""
        if self.retry_count >= self.max_retries:
            return 0  # No more retries
            
        # Exponential: 1s, 4s, 16s, 64s
        delay = self.base_delay * (4 ** self.retry_count)
        
        # Add jitter to avoid thundering herd
        if self.jitter:
            delay += random.uniform(0, delay * 0.1)
            
        return delay
        
    def should_retry(self, status_code: int, exception: Exception = None) -> bool:
        """Determine if we should retry based on error type"""
        if self.retry_count >= self.max_retries:
            return False
            
        # Retry on server errors (500+) but not client errors (400-499)
        if isinstance(exception, requests.exceptions.RequestException):
            if hasattr(exception, 'response') and exception.response:
                status = exception.response.status_code
                if status >= 500:  # Server errors
                    return True
                elif status in [429]:  # Rate limit
                    return True
                elif status in [401, 403]:  # Auth errors - trigger rotation
                    return True
            return True  # Network errors, timeouts etc
            
        return status_code >= 500 or status_code == 429
        
    def wait_and_increment(self) -> float:
        """Wait for the calculated delay and increment retry count"""
        delay = self.get_delay()
        if delay > 0:
            self.retry_count += 1
            time.sleep(delay)
            
        return delay
        
    def reset(self):
        """Reset backoff state for new request"""
        self.retry_count = 0

class VacancyFetcher:
    """
    Синхронный загрузчик с chunked processing
    - Разбивка больших объёмов на части
    - Rate limiting 
    - Простая обработка ошибок
    - Интеграция с task progress
    """
    
    def __init__(self, config: Optional[Dict] = None, rate_limit_delay=1.0, database=None):
        self.config = config or {}
        self.base_url = self.config.get('base_url', 'https://api.hh.ru')
        self.session = requests.Session()
        
        # // Chg_LOGGER_1909: Initialize logger first to prevent AttributeError
        self.logger = logging.getLogger(__name__)
        
        # Базовый и безопасный UA
        default_ua = 'HH-Tool-v4/1.0 (+https://example.local)'
        safe_browser_ua = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0 Safari/537.36'
        )
        # Пробуем прочитать из config/config_v4.json
        ua_from_cfg = None
        try:
            cfg_path = Path('config/config_v4.json')
            if cfg_path.exists():
                cfg = json.load(open(cfg_path, 'r', encoding='utf-8'))
                ua_from_cfg = (cfg.get('api') or {}).get('user_agent')
        except Exception:
            ua_from_cfg = None

        self.safe_browser_ua = safe_browser_ua
        self.ua_fallback_used = False

        self.session.headers.update({
            'User-Agent': ua_from_cfg or default_ua,
            'Accept': 'application/json',
            'Accept-Language': 'ru'
        })
        
        self.rate_limit_delay = rate_limit_delay
        
        # // Chg_INIT_1909: Add missing initialization from bottom of __init__
        # Rate limiting (простой)
        self.last_request = 0
        self.min_delay = rate_limit_delay
        
        # Database
        self.db = database or (TaskDatabase() if TaskDatabase else None)
        
        # Статистика
        self.stats = {
            'requests_made': 0,
            'vacancies_loaded': 0,
            'errors_count': 0,
            'pages_processed': 0
        }
        
        # // Chg_BACKOFF_1909: Add exponential backoff handler
        self.backoff = ExponentialBackoff(base_delay=1.0, max_retries=4)
        
        # // Chg_AUTH_ROTATE_1909: Track current auth provider for rotation
        self.current_auth_provider = choose_provider("download")
    
    def get_headers(self) -> Dict[str, str]:
        """Получить текущие заголовки HTTP"""
        return dict(self.session.headers)
    
    def search_vacancies(self, text: str = "", per_page: int = 100, **kwargs) -> Dict:
        """Поиск вакансий через API HH.ru"""
        url = f"{self.base_url}/vacancies"
        
        params = {
            'text': text,
            'per_page': per_page,
            **kwargs
        }
        
        try:
            # Применяем задержку для rate limiting
            time.sleep(self.rate_limit_delay)
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 400 and not self.ua_fallback_used:
                # Fallback на безопасный User-Agent при 400 ошибке
                logging.warning("400 error, trying safe browser UA fallback")
                self.session.headers['User-Agent'] = self.safe_browser_ua
                self.ua_fallback_used = True
                
                response = self.session.get(url, params=params, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response body: {e.response.text[:500]}")
            raise
        # Применяем авторизацию из v3-конфигов при наличии
        apply_auth_headers(self.session, purpose="download")
        # // Chg_AUTH_FALLBACK_1509: флаг одноразового отключения авторизации при 401/403
        self.auth_disabled_fallback_used = False
        
        # Rate limiting (простой)
        self.last_request = 0
        self.min_delay = rate_limit_delay
        
        # Database
        self.db = TaskDatabase()
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Статистика
        self.stats = {
            'requests_made': 0,
            'vacancies_loaded': 0,
            'errors_count': 0,
            'pages_processed': 0
        }
    
    def fetch_chunk(self, params: Dict) -> Dict:
        # // Chg_DIAG_1509: подробное логирование chunk params
        self.logger.debug(f"fetch_chunk params: {json.dumps(params, ensure_ascii=False)}")
        """
        Загрузка части вакансий (chunk)
        
        Args:
            params: {
                'page_start': int,
                'page_end': int, 
                'filter': dict,
                'task_id': str (optional)
            }
        
        Returns:
            {
                'loaded_count': int,
                'processed_pages': int,
                'errors': list,
                'last_page': int
            }
        """
        page_start = params.get('page_start', 0)
        page_end = params.get('page_end', 10)
        filter_params = params.get('filter', {})
        task_id = params.get('task_id')
        
        # Chg_TEST_2309: поддержка max_pages для тестовых фильтров
        max_pages = filter_params.get('max_pages')
        if max_pages and max_pages > 0:
            page_end = min(page_end, page_start + max_pages)
            self.logger.debug(f"Limited pages to max_pages={max_pages}, new page_end={page_end}")
        
        loaded_count = 0
        processed_pages = 0
        errors = []
        last_successful_page = page_start - 1
        
        self.logger.debug(f"Starting chunk: pages {page_start}-{page_end}")
        
        for page in range(page_start, page_end):
            self.logger.debug(f"fetch_chunk: requesting page {page}")
            try:
                # Rate limiting
                self._wait_for_rate_limit()
                
                # Запрос к API
                vacancies = self._fetch_page(filter_params, page)
                self.logger.debug(f"fetch_chunk: page {page} got {len(vacancies)} vacancies")
                
                if not vacancies:
                    self.logger.debug(f"No more vacancies on page {page}, stopping chunk")
                    break
                
                # Сохранение в БД
                saved_count = self._save_vacancies(vacancies, filter_params.get('id'))
                self.logger.debug(f"fetch_chunk: page {page} saved {saved_count} vacancies to DB")
                loaded_count += saved_count
                processed_pages += 1
                last_successful_page = page
                
                self.logger.debug(f"Page {page}: loaded {saved_count}/{len(vacancies)} vacancies")
                
                # Обновление прогресса задачи
                if task_id:
                    self._update_task_progress(task_id, {
                        'current_page': page,
                        'pages_processed': processed_pages,
                        'vacancies_loaded': loaded_count,
                        'chunk_progress': f"{page - page_start + 1}/{page_end - page_start}"
                    })
                
                # Прерывание если страница пустая или мало вакансий
                if len(vacancies) < 50:  # Меньше ожидаемого количества
                    self.logger.debug(f"Page {page} has only {len(vacancies)} vacancies, likely last page")
                    break
                    
            except requests.RequestException as e:
                error_msg = f"Failed to fetch page {page}: {e}"
                self.logger.error(error_msg)
                errors.append({'page': page, 'error': str(e)})
                self.stats['errors_count'] += 1
                
                # Продолжаем со следующей страницей при ошибке
                continue
                
            except Exception as e:
                error_msg = f"Unexpected error on page {page}: {e}"
                self.logger.error(error_msg)
                errors.append({'page': page, 'error': str(e)})
                self.stats['errors_count'] += 1
                
                # При неожиданной ошибке прерываем chunk
                break
        
        result = {
            'loaded_count': loaded_count,
            'processed_pages': processed_pages,
            'errors': errors,
            'last_page': last_successful_page,
            'stats': self.stats.copy()
        }
        
        self.logger.info(f"Chunk completed: {loaded_count} vacancies from {processed_pages} pages")
        return result
    
    def _wait_for_rate_limit(self):
        """Простой rate limiting"""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_delay:
            sleep_time = self.min_delay - elapsed
            time.sleep(sleep_time)
        self.last_request = time.time()
    
    def _fetch_page(self, filter_params: Dict, page: int) -> List[Dict]:
        """
        Загрузка одной страницы с экспоненциальным backoff и ротацией профилей
        
        // Chg_BACKOFF_1909: Enhanced with exponential backoff and auth rotation
        
        Args:
            filter_params: параметры фильтра вакансий
            page: номер страницы
            
        Returns:
            список вакансий или пустой список при ошибке
        """
        # // Chg_DIAG_1509: логируем параметры запроса
        self.logger.debug(f"_fetch_page: filter_params={json.dumps(filter_params, ensure_ascii=False)}, page={page}")
        
        url = "https://api.hh.ru/vacancies"
        
        # // Chg_FILTER_PARAMS_1509: нормализация вложенных params (start)
        # Фильтры в config/filters.json имеют структуру { id, name, params: {...} }
        # Приведём к плоскому виду для запроса в HH API
        fp = filter_params.get('params', filter_params)

        # Базовые параметры запроса (минимум). Не отправляем лишние поля по умолчанию.
        request_params = {
            'page': page,
            'per_page': 100  # максимум на странице
        }
        
        # Добавляем параметры фильтра
        if 'text' in fp:
            request_params['text'] = fp['text']
        if 'area' in fp:
            request_params['area'] = fp['area']
        if 'professional_role' in fp:
            request_params['professional_role'] = fp['professional_role']
        if 'experience' in fp:
            request_params['experience'] = fp['experience']
        if 'employment' in fp:
            request_params['employment'] = fp['employment']
        if 'schedule' in fp:
            request_params['schedule'] = fp['schedule']
        if 'salary' in fp:
            request_params['salary'] = fp['salary']
        if 'only_with_salary' in fp:
            request_params['only_with_salary'] = fp['only_with_salary']
        # Параметр периода у HH API — search_period
        if 'period' in fp and fp['period'] is not None:
            request_params['search_period'] = fp['period']
        if 'search_period' in fp and fp['search_period'] is not None:
            request_params['search_period'] = fp['search_period']
        # Допустимо передавать order_by только если задано во входном фильтре
        if 'order_by' in fp:
            request_params['order_by'] = fp['order_by']
        # search_field может быть строкой или списком значений
        if 'search_field' in fp:
            sf = fp['search_field']
            if isinstance(sf, list):
                request_params['search_field'] = sf
            elif isinstance(sf, str) and sf.strip():
                request_params['search_field'] = sf.strip()
        # // Chg_FILTER_PARAMS_1509: нормализация вложенных params (end)
        
        try:
            self.logger.debug(f"Requesting page {page} with params: {request_params}")

            def _do_request():
                resp = self.session.get(url, params=request_params, timeout=30)
                self.logger.debug(f"_fetch_page: url={resp.url} status={resp.status_code}")
                resp.raise_for_status()
                return resp

            response = _do_request()
            
            self.stats['requests_made'] += 1
            
            data = response.json()
            items = data.get('items', [])
            self.logger.debug(f"_fetch_page: got {len(items)} items, total={data.get('found', 0)}")
            
            # Логируем информацию о странице
            total_pages = data.get('pages', 0)
            total_found = data.get('found', 0)
            self.logger.debug(f"Page {page}/{total_pages}, found {len(items)} items, total: {total_found}")
            
            return items
            
        except requests.Timeout:
            self.logger.error(f"Timeout fetching page {page}")
            raise requests.RequestException(f"Timeout on page {page}")
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 'N/A'
            body = None
            try:
                body = e.response.text[:500] if e.response is not None else None
            except Exception:
                body = None
            # Fallback: при первом 400 пробуем безопасный UA один раз
            if status == 400 and not self.ua_fallback_used:
                self.ua_fallback_used = True
                old = self.session.headers.get('User-Agent')
                self.session.headers['User-Agent'] = self.safe_browser_ua
                self.logger.warning(f"Switching User-Agent from '{old}' to safe browser UA and retrying")
                resp = self.session.get(url, params=request_params, timeout=30)
                self.logger.debug(f"_fetch_page(retry): url={resp.url} status={resp.status_code}")
                resp.raise_for_status()
                self.stats['requests_made'] += 1
                data = resp.json()
                items = data.get('items', [])
                self.logger.debug(f"_fetch_page(retry): got {len(items)} items, total={data.get('found', 0)}")
                return items
            # // Chg_AUTH_FALLBACK_1509: при 401/403 и наличии Authorization — отключаем и пробуем без него
            if status in (401, 403) and not self.auth_disabled_fallback_used:
                if 'Authorization' in self.session.headers:
                    self.auth_disabled_fallback_used = True
                    old_auth = self.session.headers.pop('Authorization', None)
                    self.logger.warning("Dropping Authorization header due to %s; retrying unauthenticated", status)
                    resp = self.session.get(url, params=request_params, timeout=30)
                    self.logger.debug(f"_fetch_page(retry-noauth): url={resp.url} status={resp.status_code}")
                    resp.raise_for_status()
                    self.stats['requests_made'] += 1
                    data = resp.json()
                    items = data.get('items', [])
                    self.logger.debug(f"_fetch_page(retry-noauth): got {len(items)} items, total={data.get('found', 0)}")
                    return items
            if status == 429:
                self.logger.warning(f"Rate limit hit on page {page}, waiting longer")
                time.sleep(5)
                raise requests.RequestException(f"Rate limited on page {page}")
            else:
                self.logger.error(f"HTTP error {status} on page {page}; body={body}")
                raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON response on page {page}: {e}")
            raise requests.RequestException(f"Invalid JSON on page {page}")
        except Exception as e:
            self.logger.error(f"Unexpected error fetching page {page}: {e}")
            raise
    
    def fetch_employer(self, employer_id: str) -> Optional[Dict]:
        """
        Загрузка данных работодателя по ID из HH API
        """
        try:
            # Простой rate limit для единичных запросов
            self._wait_for_rate_limit()
            url = f"{self.base_url}/employers/{employer_id}"
            resp = self.session.get(url, timeout=30)
            if resp.status_code == 400 and not self.ua_fallback_used:
                old = self.session.headers.get('User-Agent')
                self.session.headers['User-Agent'] = self.safe_browser_ua
                self.ua_fallback_used = True
                self.logger.warning(f"Switching User-Agent from '{old}' to safe browser UA and retrying (employer)")
                resp = self.session.get(url, timeout=30)
            if resp.status_code == 404:
                self.logger.debug(f"Employer {employer_id} not found (404)")
                return None
            resp.raise_for_status()
            data = resp.json()
            self.logger.debug(f"Fetched employer {employer_id}")
            return data
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API employer request failed for {employer_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    self.logger.error(f"Response body: {e.response.text[:500]}")
                except Exception:
                    pass
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error fetching employer {employer_id}: {e}")
            return None
    
    def _save_vacancies(self, vacancies: List[Dict], filter_id: str = None) -> int:
        """
        Сохранение вакансий в БД
        
        Args:
            vacancies: список вакансий от API
            filter_id: ID фильтра
            
        Returns:
            количество сохранённых (новых/изменённых) вакансий
        """
        saved_count = 0
        
        for vacancy in vacancies:
            try:
                # save_vacancy возвращает True если вакансия новая или изменилась
                if self.db.save_vacancy(vacancy, filter_id):
                    saved_count += 1
                    self.stats['vacancies_loaded'] += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to save vacancy {vacancy.get('id', 'unknown')}: {e}")
                self.stats['errors_count'] += 1
        
        return saved_count
    
    def _update_task_progress(self, task_id: str, progress: Dict):
        """Обновление прогресса задачи"""
        try:
            self.db.update_task_progress(task_id, {
                **progress,
                'timestamp': time.time(),
                'stats': self.stats.copy()
            })
        except Exception as e:
            self.logger.error(f"Failed to update task progress: {e}")
    
    def get_stats(self) -> Dict:
        """Получение статистики работы"""
        return {
            **self.stats,
            'rate_limit_delay': self.min_delay,
            'last_request_time': self.last_request
        }
    
    def reset_stats(self):
        """Сброс статистики"""
        self.stats = {
            'requests_made': 0,
            'vacancies_loaded': 0,
            'errors_count': 0,
            'pages_processed': 0
        }

class FilterManager:
    """
    Простой менеджер фильтров для загрузки вакансий
    """
    
    def __init__(self, filters_file="config/filters.json"):
        self.filters_file = filters_file
        self.logger = logging.getLogger(__name__)
    
    def load_filters(self) -> List[Dict]:
        """Загрузка фильтров из файла"""
        try:
            with open(self.filters_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('filters', [])
        except FileNotFoundError:
            self.logger.error(f"Filters file not found: {self.filters_file}")
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in filters file: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error loading filters: {e}")
            return []
    
    def get_filter_by_id(self, filter_id: str) -> Optional[Dict]:
        """Получение фильтра по ID"""
        filters = self.load_filters()
        for f in filters:
            if f.get('id') == filter_id:
                return f
        return None
    
    def get_active_filters(self) -> List[Dict]:
        """Получение только активных фильтров"""
        filters = self.load_filters()
        # // Chg_FILTER_ACTIVE_1509: поддержка ключа 'active' с фолбэком на 'enabled'
        return [f for f in filters if f.get('active', f.get('enabled', True))]

# Утилитные функции
def estimate_total_pages(filter_params: Dict, fetcher: VacancyFetcher) -> int:
    """
    Оценка общего количества страниц для фильтра
    Делает один запрос для получения total count
    """
    try:
        # Запрашиваем первую страницу для получения общего количества
        vacancies_data = fetcher._fetch_page(filter_params, 0)
        
        # Делаем запрос к API для получения метаданных
        url = "https://api.hh.ru/vacancies"
        request_params = {
            'page': 0,
            'per_page': 1,  # Минимум для получения метаданных
            **{k: v for k, v in filter_params.items() if k != 'id'}
        }
        
        response = fetcher.session.get(url, params=request_params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        total_found = data.get('found', 0)
        per_page = 100  # Стандартное количество на странице
        
        estimated_pages = (total_found + per_page - 1) // per_page  # Округление вверх
        
        return min(estimated_pages, 2000)  # HH API ограничивает результаты
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to estimate pages: {e}")
        return 20  # Значение по умолчанию

# Экспортируем VacancyFetcher и создаем алиас HHVacancyFetcher для совместимости
HHVacancyFetcher = VacancyFetcher
