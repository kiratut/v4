#!/usr/bin/env python3
"""
// Chg_VISUAL_PANEL_TEST_2409: автоматическая проверка веб-панели через скриншоты
"""
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("Playwright not available, installing...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'playwright'], check=True)
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
    from playwright.async_api import async_playwright, Browser, Page

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))


class VisualPanelAnalyzer:
    """Автоматический анализ веб-панели через скриншоты и DOM инспекцию"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.screenshot_dir = Path(__file__).parent.parent / 'reports' / 'visual_analysis'
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.analysis_results = {
            'timestamp': datetime.now().isoformat(),
            'screenshots': [],
            'elements_found': {},
            'values_analysis': {},
            'functional_tests': {},
            'issues_found': []
        }
    
    async def setup_browser(self):
        """Настройка браузера"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=False, args=['--start-maximized'])
        context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = await context.new_page()
        
        # Ждем загрузки панели
        await self.page.goto('http://127.0.0.1:8000', wait_until='networkidle')
        await asyncio.sleep(3)  # Дополнительное время для JavaScript
    
    async def take_screenshot(self, name: str, description: str) -> str:
        """Создание скриншота"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = self.screenshot_dir / filename
        
        await self.page.screenshot(path=str(filepath), full_page=True)
        
        self.analysis_results['screenshots'].append({
            'name': name,
            'description': description,
            'filepath': str(filepath),
            'timestamp': timestamp
        })
        
        print(f"📸 Screenshot saved: {filename} - {description}")
        return str(filepath)
    
    async def analyze_status_indicators(self) -> Dict:
        """Анализ статусных индикаторов"""
        print("🔍 Analyzing status indicators...")
        
        indicators = {}
        
        # System Health
        try:
            health_elem = await self.page.query_selector('#system_health, [id*="health"]')
            if health_elem:
                health_text = await health_elem.text_content()
                indicators['system_health'] = {
                    'found': True,
                    'value': health_text.strip() if health_text else 'Empty',
                    'valid': health_text and ('OK' in health_text or '%' in health_text)
                }
            else:
                indicators['system_health'] = {'found': False, 'issue': 'System health indicator not found'}
        except Exception as e:
            indicators['system_health'] = {'found': False, 'error': str(e)}
        
        # Daemon Status
        try:
            daemon_elem = await self.page.query_selector('#daemonStatus, [id*="daemon"]')
            if daemon_elem:
                daemon_text = await daemon_elem.text_content()
                indicators['daemon_status'] = {
                    'found': True,
                    'value': daemon_text.strip() if daemon_text else 'Empty',
                    'has_pid': 'PID:' in daemon_text if daemon_text else False,
                    'has_time': 'Started:' in daemon_text if daemon_text else False,
                    'no_microseconds': ',' not in daemon_text if daemon_text else True
                }
            else:
                indicators['daemon_status'] = {'found': False, 'issue': 'Daemon status not found'}
        except Exception as e:
            indicators['daemon_status'] = {'found': False, 'error': str(e)}
        
        # API Health (with timestamp)
        try:
            api_elem = await self.page.query_selector('#apiHealth, [id*="api"]')
            if api_elem:
                api_text = await api_elem.text_content()
                indicators['api_health'] = {
                    'found': True,
                    'value': api_text.strip() if api_text else 'Empty',
                    'has_timestamp': '(' in api_text and ')' in api_text if api_text else False,
                    'status_ok': '200' in api_text or 'OK' in api_text if api_text else False
                }
            else:
                indicators['api_health'] = {'found': False, 'issue': 'API health indicator not found'}
        except Exception as e:
            indicators['api_health'] = {'found': False, 'error': str(e)}
        
        # Test Success Rate
        try:
            test_elem = await self.page.query_selector('#testSuccessRate')
            if test_elem:
                test_text = await test_elem.text_content()
                indicators['test_success_rate'] = {
                    'found': True,
                    'value': test_text.strip() if test_text else 'Empty',
                    'is_percentage': '%' in test_text if test_text else False,
                    'valid_range': self._check_percentage_range(test_text) if test_text else False
                }
            else:
                indicators['test_success_rate'] = {'found': False, 'issue': 'Test success rate not found'}
        except Exception as e:
            indicators['test_success_rate'] = {'found': False, 'error': str(e)}
        
        return indicators
    
    async def analyze_control_buttons(self) -> Dict:
        """Анализ контрольных кнопок"""
        print("🔍 Analyzing control buttons...")
        
        buttons = {}
        
        # Ищем все кнопки
        button_selectors = [
            ('start_button', 'button:has-text("Start"), [onclick*="startSystem"]'),
            ('stop_button', 'button:has-text("Stop"), [onclick*="stopSystem"]'), 
            ('test_button', 'button:has-text("Test"), [onclick*="runTests"]'),
            ('test_details_button', 'button:has-text("Details"), [onclick*="showTestDetails"]'),
            ('freeze_button', 'button:has-text("Freeze")'),
            ('clear_button', 'button:has-text("Clear")')
        ]
        
        for btn_name, selector in button_selectors:
            try:
                btn_elem = await self.page.query_selector(selector)
                if btn_elem:
                    btn_text = await btn_elem.text_content()
                    is_enabled = await btn_elem.is_enabled()
                    is_visible = await btn_elem.is_visible()
                    
                    buttons[btn_name] = {
                        'found': True,
                        'text': btn_text.strip() if btn_text else 'No text',
                        'enabled': is_enabled,
                        'visible': is_visible,
                        'functional': is_enabled and is_visible
                    }
                else:
                    buttons[btn_name] = {'found': False, 'issue': f'Button not found: {selector}'}
            except Exception as e:
                buttons[btn_name] = {'found': False, 'error': str(e)}
        
        return buttons
    
    async def analyze_data_tables(self) -> Dict:
        """Анализ таблиц с данными"""
        print("🔍 Analyzing data tables...")
        
        tables = {}
        
        # Filters Table
        try:
            filters_table = await self.page.query_selector('#filtersTableBody, table tbody')
            if filters_table:
                rows = await filters_table.query_selector_all('tr')
                tables['filters_table'] = {
                    'found': True,
                    'rows_count': len(rows),
                    'has_data': len(rows) > 0
                }
                
                # Анализ содержимого первой строки
                if rows:
                    cells = await rows[0].query_selector_all('td')
                    if len(cells) >= 4:
                        query_text = await cells[3].text_content()
                        tables['filters_table']['first_row_query'] = query_text.strip() if query_text else 'Empty'
                        tables['filters_table']['has_json_content'] = len(query_text.strip()) > 5 if query_text else False
            else:
                tables['filters_table'] = {'found': False, 'issue': 'Filters table not found'}
        except Exception as e:
            tables['filters_table'] = {'found': False, 'error': str(e)}
        
        # Tasks Table
        try:
            tasks_table = await self.page.query_selector('#tasksTableBody')
            if tasks_table:
                rows = await tasks_table.query_selector_all('tr')
                tables['tasks_table'] = {
                    'found': True,
                    'rows_count': len(rows),
                    'has_active_tasks': len(rows) > 0
                }
            else:
                tables['tasks_table'] = {'found': False, 'issue': 'Tasks table not found'}
        except Exception as e:
            tables['tasks_table'] = {'found': False, 'error': str(e)}
        
        return tables
    
    async def analyze_app_log_display(self) -> Dict:
        """Анализ отображения app.log"""
        print("🔍 Analyzing app.log display...")
        
        log_analysis = {}
        
        try:
            # Ищем контейнер лога
            log_container = await self.page.query_selector('#appLogContainer, #appLogDisplay, pre')
            if log_container:
                log_content = await log_container.text_content()
                lines = log_content.split('\n') if log_content else []
                
                log_analysis = {
                    'found': True,
                    'has_content': len(lines) > 0,
                    'lines_count': len(lines),
                    'recent_entries': len(lines) <= 100,  # Должно быть не больше 100 строк
                    'has_timestamps': any('2025' in line for line in lines[:5]) if lines else False,
                    'sample_lines': lines[-3:] if lines else []
                }
            else:
                log_analysis = {'found': False, 'issue': 'App log display not found'}
        except Exception as e:
            log_analysis = {'found': False, 'error': str(e)}
        
        return log_analysis
    
    async def test_button_functionality(self) -> Dict:
        """Тестирование функциональности кнопок"""
        print("🔍 Testing button functionality...")
        
        func_tests = {}
        
        # Тест кнопки Test
        try:
            test_btn = await self.page.query_selector('button:has-text("Test"), [onclick*="runTests"]')
            if test_btn and await test_btn.is_enabled():
                # Кликаем на кнопку Test
                await test_btn.click()
                await asyncio.sleep(2)  # Ждем начала выполнения
                
                # Проверяем изменилось ли состояние кнопки
                btn_text = await test_btn.text_content()
                func_tests['test_button_click'] = {
                    'clickable': True,
                    'state_changed': 'Running' in btn_text if btn_text else False,
                    'response': 'Button responded to click'
                }
                
                # Ждем завершения тестов
                await asyncio.sleep(10)
                
                # Проверяем обновился ли индикатор
                success_elem = await self.page.query_selector('#testSuccessRate')
                if success_elem:
                    success_text = await success_elem.text_content()
                    func_tests['test_execution'] = {
                        'completed': True,
                        'success_rate_updated': '%' in success_text if success_text else False,
                        'final_rate': success_text.strip() if success_text else 'Not found'
                    }
            else:
                func_tests['test_button_click'] = {'clickable': False, 'issue': 'Test button not clickable'}
        except Exception as e:
            func_tests['test_button_click'] = {'clickable': False, 'error': str(e)}
        
        return func_tests
    
    def _check_percentage_range(self, text: str) -> bool:
        """Проверка что процент в допустимом диапазоне 0-100%"""
        try:
            if '%' not in text:
                return False
            percentage = float(text.replace('%', '').strip())
            return 0 <= percentage <= 100
        except:
            return False
    
    async def run_full_analysis(self) -> Dict:
        """Запуск полного анализа панели"""
        print("🚀 Starting visual panel analysis...")
        
        try:
            await self.setup_browser()
            
            # Основной скриншот панели
            await self.take_screenshot('main_panel', 'Main dashboard view')
            
            # Анализ компонентов
            self.analysis_results['elements_found'] = await self.analyze_status_indicators()
            self.analysis_results['control_buttons'] = await self.analyze_control_buttons()
            self.analysis_results['data_tables'] = await self.analyze_data_tables()
            self.analysis_results['app_log'] = await self.analyze_app_log_display()
            
            # Скриншот после анализа элементов
            await self.take_screenshot('after_analysis', 'Panel state after element analysis')
            
            # Функциональные тесты
            self.analysis_results['functional_tests'] = await self.test_button_functionality()
            
            # Финальный скриншот
            await self.take_screenshot('final_state', 'Final panel state after functional tests')
            
            # Анализ проблем
            self._analyze_issues()
            
            return self.analysis_results
            
        finally:
            if self.browser:
                await self.browser.close()
    
    def _analyze_issues(self):
        """Анализ найденных проблем"""
        issues = []
        
        # Проверка статусных индикаторов
        for indicator, data in self.analysis_results.get('elements_found', {}).items():
            if not data.get('found', False):
                issues.append(f"❌ {indicator}: {data.get('issue', data.get('error', 'Not found'))}")
            elif indicator == 'daemon_status':
                if not data.get('has_pid', False):
                    issues.append(f"⚠️ Daemon status missing PID information")
                if not data.get('no_microseconds', True):
                    issues.append(f"⚠️ Daemon time contains microseconds (should be removed)")
            elif indicator == 'api_health':
                if not data.get('has_timestamp', False):
                    issues.append(f"⚠️ API health missing timestamp in format (HH:mm:ss)")
            elif indicator == 'test_success_rate':
                if not data.get('is_percentage', False):
                    issues.append(f"⚠️ Test success rate not in percentage format")
                if not data.get('valid_range', False):
                    issues.append(f"⚠️ Test success rate outside valid range (0-100%)")
        
        # Проверка кнопок
        required_buttons = ['test_button', 'start_button', 'stop_button']
        for btn in required_buttons:
            btn_data = self.analysis_results.get('control_buttons', {}).get(btn, {})
            if not btn_data.get('found', False):
                issues.append(f"❌ Required button missing: {btn}")
            elif not btn_data.get('functional', False):
                issues.append(f"⚠️ Button not functional: {btn} (enabled: {btn_data.get('enabled')}, visible: {btn_data.get('visible')})")
        
        # Проверка таблиц
        tables_data = self.analysis_results.get('data_tables', {})
        if not tables_data.get('filters_table', {}).get('found', False):
            issues.append(f"❌ Filters table not found")
        elif not tables_data.get('filters_table', {}).get('has_json_content', False):
            issues.append(f"⚠️ Filters table missing JSON content in query column")
        
        # Проверка app.log
        log_data = self.analysis_results.get('app_log', {})
        if not log_data.get('found', False):
            issues.append(f"❌ App.log display not found")
        elif not log_data.get('has_content', False):
            issues.append(f"⚠️ App.log display has no content")
        
        self.analysis_results['issues_found'] = issues
    
    def print_analysis_report(self):
        """Вывод детального отчета анализа"""
        print("\n" + "="*80)
        print("📊 VISUAL PANEL ANALYSIS REPORT")
        print("="*80)
        
        # Статус индикаторы
        print("\n🎯 STATUS INDICATORS:")
        for name, data in self.analysis_results.get('elements_found', {}).items():
            status = "✅" if data.get('found') else "❌"
            value = data.get('value', 'N/A')
            print(f"  {status} {name}: {value}")
        
        # Кнопки управления  
        print("\n🎮 CONTROL BUTTONS:")
        for name, data in self.analysis_results.get('control_buttons', {}).items():
            status = "✅" if data.get('functional') else "❌"
            text = data.get('text', 'N/A')
            print(f"  {status} {name}: {text}")
        
        # Таблицы данных
        print("\n📋 DATA TABLES:")
        for name, data in self.analysis_results.get('data_tables', {}).items():
            status = "✅" if data.get('found') else "❌"
            rows = data.get('rows_count', 0)
            print(f"  {status} {name}: {rows} rows")
        
        # App.log отображение
        print("\n📄 APP.LOG DISPLAY:")
        log_data = self.analysis_results.get('app_log', {})
        status = "✅" if log_data.get('found') else "❌"
        lines = log_data.get('lines_count', 0)
        print(f"  {status} app_log: {lines} lines shown")
        
        # Функциональные тесты
        print("\n🧪 FUNCTIONAL TESTS:")
        for name, data in self.analysis_results.get('functional_tests', {}).items():
            status = "✅" if data.get('clickable') or data.get('completed') else "❌"
            result = data.get('response', data.get('final_rate', 'Failed'))
            print(f"  {status} {name}: {result}")
        
        # Найденные проблемы
        issues = self.analysis_results.get('issues_found', [])
        print(f"\n🚨 ISSUES FOUND: {len(issues)}")
        for issue in issues:
            print(f"  {issue}")
        
        # Скриншоты
        screenshots = self.analysis_results.get('screenshots', [])
        print(f"\n📸 SCREENSHOTS: {len(screenshots)}")
        for shot in screenshots:
            print(f"  📷 {shot['name']}: {shot['description']}")
        
        # Общий статус
        total_issues = len(issues)
        overall_status = "🎉 EXCELLENT" if total_issues == 0 else "⚠️ NEEDS ATTENTION" if total_issues < 3 else "❌ CRITICAL ISSUES"
        print(f"\n🏆 OVERALL STATUS: {overall_status} ({total_issues} issues)")
        
        return total_issues == 0


async def main():
    """Главная функция"""
    analyzer = VisualPanelAnalyzer()
    
    try:
        results = await analyzer.run_full_analysis()
        
        # Сохранение результатов
        results_file = analyzer.screenshot_dir / f'analysis_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Вывод отчета
        success = analyzer.print_analysis_report()
        
        print(f"\n📁 Results saved to: {results_file}")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Analysis interrupted by user")
        sys.exit(1)
