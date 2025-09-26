#!/usr/bin/env python3
"""
КОНСОЛИДИРОВАННЫЙ ВИЗУАЛЬНЫЙ ТЕСТ HH v4 WEB ПАНЕЛИ
Объединяет функционал из simple_visual_test.py, visual_panel_test.py и final_visual_test.py
Автоматически определяет порт из конфигурации и проводит полный анализ
"""

import asyncio
import logging
from logging.handlers import RotatingFileHandler
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Installing Playwright...")
    import subprocess
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    from playwright.async_api import async_playwright, Browser, Page

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))


class ConsolidatedVisualTest:
    """Консолидированный визуальный тест веб-панели"""
    
    def __init__(self):
        # Логирование в общий app.log
        try:
            (Path(__file__).parent.parent / 'logs').mkdir(parents=True, exist_ok=True)
            logger = logging.getLogger('visual_test')
            logger.setLevel(logging.INFO)
            if not any(isinstance(h, RotatingFileHandler) and getattr(h, 'baseFilename', '').endswith('app.log') for h in logger.handlers):
                handler = RotatingFileHandler(str(Path(__file__).parent.parent / 'logs' / 'app.log'), maxBytes=100*1024*1024, backupCount=3, encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                logger.addHandler(handler)
            self.logger = logger
            self.logger.info('Consolidated visual test initialized')
        except Exception:
            # В случае ошибок логирования — не падаем, продолжаем
            self.logger = logging.getLogger('visual_test_fallback')

        self.config = self._load_config()
        self.host = self.config.get('web_interface', {}).get('host', 'localhost')
        self.port = self.config.get('web_interface', {}).get('port', 8000)
        self.base_url = f"http://{self.host}:{self.port}"
        
        self.report_dir = Path(__file__).parent.parent / 'reports' / 'consolidated_visual'
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'test_config': {
                'base_url': self.base_url,
                'host': self.host,
                'port': self.port
            },
            'screenshots': [],
            'elements_analysis': {},
            'functionality_tests': {},
            'api_checks': {},
            'issues_found': [],
            'summary': {}
        }
        
    def _load_config(self) -> Dict:
        """Загрузка конфигурации"""
        try:
            config_path = Path(__file__).parent.parent / 'config' / 'config_v4.json'
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load config: {e}")
            return {}
    
    async def setup_browser(self):
        """Настройка браузера"""
        self.logger.info(f"Setting up browser for {self.base_url}")
        print(f"🌐 Setting up browser for {self.base_url}")
        playwright = await async_playwright().start()
        
        # Headless для стабильности, но можно переключить на False для отладки
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
        )
        
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await context.new_page()
        
        # Увеличиваем таймауты
        self.page.set_default_timeout(30000)
        # Подписка на события консоли/ошибок браузера -> в общий лог
        try:
            self.page.on("console", lambda msg: self.logger.warning(f"Browser console [{msg.type}]: {msg.text()}") )
            self.page.on("pageerror", lambda exc: self.logger.error(f"Browser page error: {exc}") )
        except Exception as e:
            self.logger.exception(f"Failed to attach page event handlers: {e}")
        
    async def take_screenshot(self, name: str, description: str) -> str:
        """Создание скриншота"""
        filename = f"{name}_{self.timestamp}.png"
        filepath = self.report_dir / filename
        
        await self.page.screenshot(path=str(filepath), full_page=True)
        
        screenshot_info = {
            'name': name,
            'description': description,
            'filepath': str(filepath),
            'timestamp': self.timestamp
        }
        self.results['screenshots'].append(screenshot_info)
        
        self.logger.info(f"Screenshot saved: {filename} - {description}")
        print(f"📸 Screenshot saved: {filename} - {description}")
        return str(filepath)
        
    async def analyze_page_elements(self) -> Dict:
        """Анализ элементов страницы"""
        self.logger.info("Analyzing page elements...")
        print("🔍 Analyzing page elements...")
        
        elements = {}
        
        # Системные индикаторы
        try:
            system_health = await self.page.locator('[data-metric="system-health"]').inner_text()
            elements['system_health'] = {
                'found': True,
                'text': system_health,
                'visible': await self.page.locator('[data-metric="system-health"]').is_visible()
            }
        except:
            elements['system_health'] = {'found': False}
            
        # Статус демона
        try:
            daemon_status = await self.page.locator('[data-metric="daemon-status"]').inner_text()
            elements['daemon_status'] = {
                'found': True,
                'text': daemon_status,
                'visible': await self.page.locator('[data-metric="daemon-status"]').is_visible()
            }
        except:
            elements['daemon_status'] = {'found': False}
            
        # API Health
        try:
            api_health = await self.page.locator('[data-metric="api-health"]').inner_text()
            elements['api_health'] = {
                'found': True,
                'text': api_health,
                'visible': await self.page.locator('[data-metric="api-health"]').is_visible()
            }
        except:
            elements['api_health'] = {'found': False}
            
        # Кнопки
        buttons = {}
        button_selectors = [
            ('test_button', '//button[contains(text(), "🧪") or contains(text(), "Run Tests")]'),
            ('details_button', '//button[contains(text(), "📋") or contains(text(), "Test Details")]'),
            ('freeze_button', '//button[contains(text(), "❄️") or contains(text(), "Freeze")]'),
            ('clear_button', '//button[contains(text(), "🗑️") or contains(text(), "Clear")]')
        ]
        
        for button_name, selector in button_selectors:
            try:
                button = self.page.locator(selector).first
                buttons[button_name] = {
                    'found': True,
                    'text': await button.inner_text(),
                    'enabled': await button.is_enabled(),
                    'visible': await button.is_visible()
                }
            except:
                buttons[button_name] = {'found': False}
                
        elements['buttons'] = buttons
        
        # Таблицы
        try:
            filters_rows = await self.page.locator('#filtersTable tbody tr').count()
            elements['filters_table'] = {
                'found': True,
                'rows': filters_rows,
                'has_content': filters_rows > 0
            }
        except:
            elements['filters_table'] = {'found': False}
            
        try:
            tasks_rows = await self.page.locator('#tasksTable tbody tr').count()
            elements['tasks_table'] = {
                'found': True,
                'rows': tasks_rows,
                'has_content': tasks_rows > 0
            }
        except:
            elements['tasks_table'] = {'found': False}
            
        return elements
        
    async def test_functionality(self) -> Dict:
        """Тестирование функциональности кнопок"""
        self.logger.info("Testing button functionality...")
        print("🔧 Testing button functionality...")
        
        functionality = {}
        
        # Тест кнопки "Run Tests"
        try:
            test_button = self.page.locator('//button[contains(text(), "🧪") or contains(text(), "Run Tests")]').first
            if await test_button.is_visible():
                await test_button.click()
                await self.page.wait_for_timeout(2000)  # Ждем реакцию
                
                functionality['test_button_click'] = {
                    'success': True,
                    'message': 'Button clicked successfully'
                }
            else:
                functionality['test_button_click'] = {
                    'success': False,
                    'message': 'Button not visible'
                }
        except Exception as e:
            functionality['test_button_click'] = {
                'success': False,
                'message': f'Click failed: {str(e)}'
            }
            
        return functionality
        
    def check_api_endpoints(self) -> Dict:
        """Проверка API эндпоинтов"""
        self.logger.info("Checking API endpoints...")
        print("🔌 Checking API endpoints...")
        
        api_checks = {}
        endpoints = [
            ('version', '/api/version'),
            ('stats', '/api/stats'),
            ('daemon_status', '/api/daemon/status'),
            ('tests_status', '/api/tests/status'),
            ('app_logs', '/api/logs/app?limit=10')
        ]
        
        for name, endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, timeout=5)
                api_checks[name] = {
                    'success': True,
                    'status_code': response.status_code,
                    'response_size': len(response.text)
                }
                self.logger.info(f"API {name} OK: {response.status_code}, size={len(response.text)}")
            except Exception as e:
                api_checks[name] = {
                    'success': False,
                    'error': str(e)
                }
                self.logger.error(f"API {name} FAILED: {e}")
                
        return api_checks
        
    def analyze_issues(self):
        """Анализ найденных проблем"""
        issues = []
        
        # Проверка критических элементов
        elements = self.results.get('elements_analysis', {})
        
        if not elements.get('system_health', {}).get('found'):
            issues.append("❌ Missing system health indicator")
            
        if not elements.get('daemon_status', {}).get('found'):
            issues.append("❌ Missing daemon status indicator")
            
        # Проверка кнопок
        buttons = elements.get('buttons', {})
        if not buttons.get('test_button', {}).get('found'):
            issues.append("❌ Missing test button")
            
        # Проверка API
        api_checks = self.results.get('api_checks', {})
        failed_apis = [name for name, check in api_checks.items() if not check.get('success')]
        if failed_apis:
            issues.append(f"❌ Failed API endpoints: {', '.join(failed_apis)}")
            
        # Проверка таблиц
        if not elements.get('filters_table', {}).get('has_content'):
            issues.append("⚠️ Filters table is empty")
            
        self.results['issues_found'] = issues
        
    def generate_summary(self):
        """Генерация сводки результатов"""
        elements = self.results.get('elements_analysis', {})
        api_checks = self.results.get('api_checks', {})
        
        total_elements = len(elements)
        found_elements = sum(1 for elem in elements.values() if isinstance(elem, dict) and elem.get('found'))
        
        total_apis = len(api_checks)
        working_apis = sum(1 for api in api_checks.values() if api.get('success'))
        
        self.results['summary'] = {
            'elements_found': f"{found_elements}/{total_elements}",
            'apis_working': f"{working_apis}/{total_apis}",
            'issues_count': len(self.results.get('issues_found', [])),
            'screenshots_taken': len(self.results.get('screenshots', [])),
            'overall_status': 'PASS' if len(self.results.get('issues_found', [])) == 0 else 'ISSUES_FOUND'
        }
        
    async def run_full_analysis(self) -> Dict:
        """Запуск полного анализа"""
        try:
            self.logger.info("Starting full analysis run")
            await self.setup_browser()
            
            print(f"🌐 Loading panel at {self.base_url}")
            await self.page.goto(self.base_url, wait_until='networkidle')
            await asyncio.sleep(3)  # Дополнительное время для загрузки
            
            # Основной скриншот
            await self.take_screenshot('main_panel', 'Main dashboard view')
            
            # Анализ элементов
            self.results['elements_analysis'] = await self.analyze_page_elements()
            
            # Скриншот после анализа
            await self.take_screenshot('after_analysis', 'Panel state after element analysis')
            
            # Тестирование функциональности
            self.results['functionality_tests'] = await self.test_functionality()
            
            # Финальный скриншот
            await self.take_screenshot('final_state', 'Final panel state after tests')
            
            # Проверка API
            self.results['api_checks'] = self.check_api_endpoints()
            
            # Анализ проблем
            self.analyze_issues()
            
            # Генерация сводки
            self.generate_summary()
            
        except Exception as e:
            self.logger.exception(f"Analysis failed: {e}")
            print(f"❌ Analysis failed: {e}")
            self.results['fatal_error'] = str(e)
        
        finally:
            if self.browser:
                await self.browser.close()
                
        return self.results
        
    def save_results(self):
        """Сохранение результатов"""
        results_file = self.report_dir / f'analysis_{self.timestamp}.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Results saved: {results_file}")
        print(f"💾 Results saved: {results_file}")
        
        # Печать сводки
        summary = self.results.get('summary', {})
        summary_lines = [
            "",
            "="*60,
            "📊 VISUAL TEST SUMMARY",
            "="*60,
            f"🌐 Panel URL: {self.base_url}",
            f"🎯 Elements found: {summary.get('elements_found', 'N/A')}",
            f"🔌 APIs working: {summary.get('apis_working', 'N/A')}",
            f"📸 Screenshots: {summary.get('screenshots_taken', 0)}",
            f"⚠️  Issues: {summary.get('issues_count', 0)}",
            f"📊 Overall status: {summary.get('overall_status', 'UNKNOWN')}",
        ]
        for line in summary_lines:
            if line:
                self.logger.info(line)
            print(line)
        
        if self.results.get('issues_found'):
            self.logger.warning("ISSUES FOUND:")
            print("\n🔍 ISSUES FOUND:")
            for issue in self.results['issues_found']:
                self.logger.warning(issue)
                print(f"  {issue}")
                
        print("="*60)


async def main():
    """Главная функция"""
    print("🚀 Starting consolidated visual panel analysis...")
    
    analyzer = ConsolidatedVisualTest()
    results = await analyzer.run_full_analysis()
    analyzer.save_results()
    
    return results


if __name__ == "__main__":
    asyncio.run(main())
