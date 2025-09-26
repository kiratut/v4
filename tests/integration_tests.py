#!/usr/bin/env python3
"""
// Chg_INTEGRATION_TESTS_2409: интеграционные тесты с скриншотами веб-панели
"""
import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import psutil
from playwright.async_api import async_playwright, Browser, Page

# Добавляем путь к корню проекта
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.task_database import TaskDatabase
from tests.consolidated_tests import TestResult


class IntegrationTestRunner:
    """Интеграционное тестирование с автоматическими скриншотами"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.daemon_pid: Optional[int] = None
        self.web_pid: Optional[int] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.screenshots_dir = Path(__file__).parent.parent / 'reports' / 'screenshots'
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        
        # // Chg_UNION_LOG_2409: пишем в union_test.log вместо отдельного файла
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/union_test.log', encoding='utf-8', mode='a'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('integration_tests')
    
    async def setup_environment(self):
        """Настройка тестового окружения"""
        try:
            # Останавливаем процессы если есть
            self.cleanup_processes()
            
            # Запускаем демон
            self.logger.info("Starting daemon...")
            daemon_cmd = [sys.executable, 'cli_v4.py', 'daemon', 'start', '--background']
            daemon_proc = subprocess.run(daemon_cmd, capture_output=True, text=True, timeout=30)
            
            if daemon_proc.returncode != 0:
                self.logger.warning(f"Daemon start returned {daemon_proc.returncode}: {daemon_proc.stderr}")
            
            # Ждем запуска демона
            await asyncio.sleep(3)
            
            # Запускаем веб-сервер
            self.logger.info("Starting web server...")
            web_cmd = [sys.executable, '-m', 'uvicorn', 'web.server:app', '--host', '127.0.0.1', '--port', '5000']
            self.web_proc = subprocess.Popen(web_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.web_pid = self.web_proc.pid
            
            # Ждем запуска веб-сервера
            await asyncio.sleep(5)
            
            # Запускаем браузер
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            
            self.logger.info("Environment setup complete")
            return True
            
        except Exception as e:
            self.logger.error(f"Setup failed: {e}")
            return False
    
    def cleanup_processes(self):
        """Очистка процессов"""
        try:
            # Убиваем Python процессы
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python.exe':
                        cmdline = ' '.join(proc.info.get('cmdline', []))
                        if 'uvicorn' in cmdline or 'daemon' in cmdline or 'cli_v4' in cmdline:
                            proc.kill()
                            self.logger.info(f"Killed process {proc.pid}: {cmdline}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    async def test_web_panel_load(self) -> TestResult:
        """Тест загрузки веб-панели"""
        result = TestResult('integration_web_load', 'Загрузка веб-панели', 1)
        
        try:
            # Переходим на главную страницу
            await self.page.goto('http://127.0.0.1:5000', wait_until='networkidle')
            
            # Делаем скриншот главной страницы
            screenshot_path = self.screenshots_dir / f'main_page_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Проверяем наличие основных элементов
            title = await self.page.text_content('title')
            result.details['page_title'] = title
            result.details['screenshot'] = str(screenshot_path)
            
            # Проверяем заголовок панели
            header_title = await self.page.text_content('#headerTitle')
            if not header_title or 'HH v4' not in header_title:
                raise AssertionError(f"Header title not found or incorrect: {header_title}")
            
            result.details['header_title'] = header_title
            result.passed = True
            self.logger.info(f"Web panel loaded successfully: {title}")
            
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Web panel load test failed: {e}")
        
        return result
    
    async def test_status_indicators(self) -> TestResult:
        """Тест индикаторов статуса"""
        result = TestResult('integration_status_indicators', 'Индикаторы статуса на панели', 1)
        
        try:
            # Ждем загрузки данных
            await asyncio.sleep(2)
            
            # Проверяем статусные карточки
            status_cards = {}
            
            # System Health
            health_elem = await self.page.query_selector('#system_health')
            if health_elem:
                health_text = await health_elem.text_content()
                status_cards['system_health'] = health_text
            
            # Daemon Status  
            daemon_elem = await self.page.query_selector('#daemonStatus')
            if daemon_elem:
                daemon_text = await daemon_elem.text_content()
                status_cards['daemon_status'] = daemon_text
                
                # Проверяем формат времени (без микросекунд)
                if ',' in daemon_text:
                    raise AssertionError(f"Daemon time contains microseconds: {daemon_text}")
            
            # Unix Time
            unix_elem = await self.page.query_selector('#daemonUnixTime')
            if unix_elem:
                unix_text = await unix_elem.text_content()
                status_cards['daemon_unix'] = unix_text
                
                # Проверяем что это число
                try:
                    unix_val = int(unix_text)
                    if unix_val < 1000000000:  # Минимальная unix timestamp
                        raise ValueError("Invalid unix timestamp")
                except ValueError:
                    raise AssertionError(f"Invalid unix time format: {unix_text}")
            
            # Tasks Queue
            tasks_elem = await self.page.query_selector('#taskStats')
            if tasks_elem:
                tasks_text = await tasks_elem.text_content()
                status_cards['tasks_queue'] = tasks_text
            
            # API Health с временем
            api_elem = await self.page.query_selector('#apiHealth')
            if api_elem:
                api_text = await api_elem.text_content()
                status_cards['api_health'] = api_text
                
                # Проверяем формат времени в скобках
                if '(' not in api_text or ')' not in api_text:
                    raise AssertionError(f"API health missing time format: {api_text}")
            
            result.details['status_cards'] = status_cards
            result.details['cards_count'] = len(status_cards)
            
            # Делаем скриншот статус строки
            screenshot_path = self.screenshots_dir / f'status_indicators_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            status_row = await self.page.query_selector('.status-row')
            if status_row:
                await status_row.screenshot(path=str(screenshot_path))
                result.details['status_screenshot'] = str(screenshot_path)
            
            if len(status_cards) >= 4:
                result.passed = True
                self.logger.info(f"Status indicators test passed: {len(status_cards)} cards found")
            else:
                raise AssertionError(f"Expected at least 4 status cards, found {len(status_cards)}")
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Status indicators test failed: {e}")
        
        return result
    
    async def test_control_buttons(self) -> TestResult:
        """Тест контрольных кнопок"""
        result = TestResult('integration_control_buttons', 'Контрольные кнопки управления', 1)
        
        try:
            # Ищем кнопки
            buttons_found = {}
            
            # Start System button
            start_buttons = await self.page.query_selector_all('button:has-text("Start")')
            buttons_found['start_buttons'] = len(start_buttons)
            
            # Stop System button  
            stop_buttons = await self.page.query_selector_all('button:has-text("Stop")')
            buttons_found['stop_buttons'] = len(stop_buttons)
            
            # Freeze Workers button
            freeze_buttons = await self.page.query_selector_all('button:has-text("Freeze")')
            buttons_found['freeze_buttons'] = len(freeze_buttons)
            
            # Clear Queue button
            clear_buttons = await self.page.query_selector_all('button:has-text("Clear")')
            buttons_found['clear_buttons'] = len(clear_buttons)
            
            # Config Editor buttons
            read_buttons = await self.page.query_selector_all('button:has-text("Read")')
            write_buttons = await self.page.query_selector_all('button:has-text("Write")')
            buttons_found['read_buttons'] = len(read_buttons)
            buttons_found['write_buttons'] = len(write_buttons)
            
            # Filters buttons
            filters_buttons = await self.page.query_selector_all('button[title*="фильтр"]')
            buttons_found['filters_buttons'] = len(filters_buttons)
            
            result.details['buttons_found'] = buttons_found
            result.details['total_buttons'] = sum(buttons_found.values())
            
            # Делаем скриншот всех контролов
            screenshot_path = self.screenshots_dir / f'controls_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            result.details['controls_screenshot'] = str(screenshot_path)
            
            # Проверяем минимальное количество кнопок
            if sum(buttons_found.values()) >= 6:
                result.passed = True
                self.logger.info(f"Control buttons test passed: {sum(buttons_found.values())} buttons found")
            else:
                raise AssertionError(f"Expected at least 6 control buttons, found {sum(buttons_found.values())}")
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Control buttons test failed: {e}")
        
        return result
    
    async def test_data_tables(self) -> TestResult:
        """Тест таблиц с данными"""
        result = TestResult('integration_data_tables', 'Таблицы с данными', 2)
        
        try:
            tables_data = {}
            
            # Filters Table
            filters_table = await self.page.query_selector('#filtersTableBody')
            if filters_table:
                filters_rows = await filters_table.query_selector_all('tr')
                tables_data['filters_rows'] = len(filters_rows)
                
                # Проверяем содержимое первой строки фильтров
                if filters_rows:
                    first_row_cells = await filters_rows[0].query_selector_all('td')
                    if len(first_row_cells) >= 4:
                        query_cell = first_row_cells[3]
                        query_text = await query_cell.text_content()
                        tables_data['first_filter_query'] = query_text
                        
                        # Проверяем что текст не пустой
                        if not query_text or query_text.strip() == '-':
                            self.logger.warning("First filter query is empty or dash")
            
            # Tasks Table
            tasks_table = await self.page.query_selector('#tasksTableBody')
            if tasks_table:
                tasks_rows = await tasks_table.query_selector_all('tr')
                tables_data['tasks_rows'] = len(tasks_rows)
            
            # Workers List
            workers_list = await self.page.query_selector('#workerTasksList')
            if workers_list:
                workers_items = await workers_list.query_selector_all('li')
                tables_data['workers_items'] = len(workers_items)
            
            result.details['tables_data'] = tables_data
            
            # Делаем скриншот таблиц
            screenshot_path = self.screenshots_dir / f'tables_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            dashboard_grid = await self.page.query_selector('.dashboard-grid')
            if dashboard_grid:
                await dashboard_grid.screenshot(path=str(screenshot_path))
                result.details['tables_screenshot'] = str(screenshot_path)
            
            # Проверяем что таблицы найдены
            if len(tables_data) >= 2:
                result.passed = True
                self.logger.info(f"Data tables test passed: {len(tables_data)} tables found")
            else:
                raise AssertionError(f"Expected at least 2 data tables, found {len(tables_data)}")
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Data tables test failed: {e}")
        
        return result
    
    async def test_config_editor(self) -> TestResult:
        """Тест редактора конфигурации"""
        result = TestResult('integration_config_editor', 'Редактор конфигурации', 2)
        
        try:
            # Ищем текстовое поле редактора
            config_editor = await self.page.query_selector('#configEditor')
            if not config_editor:
                raise AssertionError("Config editor textarea not found")
            
            # Проверяем содержимое
            editor_content = await config_editor.input_value()
            result.details['editor_content_length'] = len(editor_content)
            result.details['editor_has_content'] = len(editor_content) > 0
            
            # Проверяем что это JSON или ошибка
            is_json = False
            is_error = False
            if editor_content.strip():
                if editor_content.startswith('{') or editor_content.startswith('['):
                    try:
                        json.loads(editor_content)
                        is_json = True
                    except json.JSONDecodeError:
                        pass
                elif 'Error loading config' in editor_content:
                    is_error = True
            
            result.details['is_json'] = is_json
            result.details['is_error_message'] = is_error
            result.details['content_preview'] = editor_content[:200] if editor_content else 'Empty'
            
            # Делаем скриншот области редактора
            screenshot_path = self.screenshots_dir / f'config_editor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
            editor_area = await self.page.query_selector('textarea#configEditor')
            if editor_area:
                await editor_area.screenshot(path=str(screenshot_path))
                result.details['editor_screenshot'] = str(screenshot_path)
            
            # Тест считается успешным если редактор найден и имеет содержимое (JSON или ошибку)
            if is_json or is_error:
                result.passed = True
                self.logger.info(f"Config editor test passed: JSON={is_json}, Error={is_error}")
            else:
                raise AssertionError(f"Config editor is empty or has invalid content")
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Config editor test failed: {e}")
        
        return result
    
    async def test_database_logging(self) -> TestResult:
        """Тест логирования в базу данных"""
        result = TestResult('integration_db_logging', 'Логирование в БД', 1)
        
        try:
            # Проверяем записи в БД
            db = TaskDatabase()
            with db.get_connection() as conn:
                # Общее количество логов
                cur = conn.execute("SELECT COUNT(*) FROM logs")
                total_logs = cur.fetchone()[0]
                
                # Логи за последний час
                cur = conn.execute("SELECT COUNT(*) FROM logs WHERE ts > ?", (time.time() - 3600,))
                recent_logs = cur.fetchone()[0]
                
                # Последние 5 записей
                cur = conn.execute("SELECT ts, level, module, message FROM logs ORDER BY ts DESC LIMIT 5")
                latest_logs = cur.fetchall()
            
            result.details['total_logs'] = total_logs
            result.details['recent_logs_1h'] = recent_logs
            result.details['latest_logs'] = [
                {'ts': ts, 'level': level, 'module': module, 'message': msg[:100]}
                for ts, level, module, msg in latest_logs
            ]
            
            # Тест успешен если есть логи в БД
            if total_logs > 0:
                result.passed = True
                self.logger.info(f"Database logging test passed: {total_logs} total logs, {recent_logs} recent")
            else:
                raise AssertionError("No logs found in database")
                
        except Exception as e:
            result.error_message = str(e)
            self.logger.error(f"Database logging test failed: {e}")
        
        return result
    
    async def run_all_tests(self) -> Dict:
        """Запуск всех интеграционных тестов"""
        start_time = time.time()
        
        try:
            self.logger.info("Starting integration tests...")
            
            # Настройка окружения
            if not await self.setup_environment():
                raise RuntimeError("Environment setup failed")
            
            # Запуск тестов
            test_methods = [
                self.test_web_panel_load,
                self.test_status_indicators, 
                self.test_control_buttons,
                self.test_data_tables,
                self.test_config_editor,
                self.test_database_logging
            ]
            
            for test_method in test_methods:
                try:
                    result = await test_method()
                    self.results.append(result)
                    self.logger.info(f"Test {result.test_id}: {'PASSED' if result.passed else 'FAILED'}")
                except Exception as e:
                    self.logger.error(f"Test method {test_method.__name__} crashed: {e}")
                    # Создаем failed результат
                    result = TestResult(test_method.__name__, f"Crashed: {test_method.__name__}", 1)
                    result.error_message = str(e)
                    self.results.append(result)
            
        finally:
            # Очистка
            if self.browser:
                await self.browser.close()
            self.cleanup_processes()
        
        # Статистика
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        total_time = time.time() - start_time
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'execution_time': total_time,
            'results': [
                {
                    'test_id': r.test_id,
                    'name': r.name,
                    'priority': r.priority,
                    'passed': r.passed,
                    'error_message': r.error_message,
                    'details': r.details
                }
                for r in self.results
            ]
        }


async def main():
    """Главная функция"""
    runner = IntegrationTestRunner()
    
    try:
        results = await runner.run_all_tests()
        
        # Сохранение результатов
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = Path('reports') / f'integration_tests_{timestamp}.json'
        results_file.parent.mkdir(exist_ok=True)
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Вывод сводки
        print(f"\n{'='*60}")
        print(f"INTEGRATION TESTS COMPLETED")
        print(f"{'='*60}")
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed_tests']}")
        print(f"Failed: {results['failed_tests']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Execution Time: {results['execution_time']:.1f}s")
        print(f"Results saved to: {results_file}")
        
        # Вывод неуспешных тестов
        failed_tests = [r for r in results['results'] if not r['passed']]
        if failed_tests:
            print(f"\nFAILED TESTS:")
            for test in failed_tests:
                print(f"- {test['name']}: {test['error_message']}")
        
        return 0 if results['failed_tests'] == 0 else 1
        
    except Exception as e:
        print(f"Integration tests crashed: {e}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
        sys.exit(1)
