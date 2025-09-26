#!/usr/bin/env python3
"""
// Chg_TEST_PIPELINE_2409: единый пайплайн всех тестов с отчетами и скриншотами
"""
import asyncio
import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.consolidated_tests import TestRunner
from tests.integration_tests import IntegrationTestRunner


class TestPipeline:
    """Единый пайплайн всех тестов системы"""
    
    def __init__(self):
        self.results = {
            'unit_tests': {},
            'integration_tests': {},
            'pipeline_summary': {}
        }
        self.reports_dir = Path(__file__).parent.parent / 'reports'
        self.reports_dir.mkdir(exist_ok=True)
        
        # Логирование
        self.logger = logging.getLogger('test_pipeline')
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def run_unit_tests(self, priorities: List[int] = [1, 2]) -> Dict:
        """Запуск unit/functional тестов"""
        self.logger.info(f"Running unit tests for priorities: {priorities}")
        
        try:
            # Используем existing TestRunner
            runner = TestRunner(priorities)
            results = runner.run_all_tests()
            
            self.logger.info(f"Unit tests completed: {results['passed_tests']}/{results['total_tests']} passed")
            return results
            
        except Exception as e:
            self.logger.error(f"Unit tests failed: {e}")
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'overall_percentage': 0.0,
                'execution_time': 0.0,
                'error': str(e)
            }
    
    async def run_integration_tests(self) -> Dict:
        """Запуск интеграционных тестов с UI"""
        self.logger.info("Running integration tests with screenshots...")
        
        try:
            runner = IntegrationTestRunner()
            results = await runner.run_all_tests()
            
            self.logger.info(f"Integration tests completed: {results['passed_tests']}/{results['total_tests']} passed")
            return results
            
        except Exception as e:
            self.logger.error(f"Integration tests failed: {e}")
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'success_rate': 0.0,
                'execution_time': 0.0,
                'error': str(e)
            }
    
    def generate_html_report(self, timestamp: str) -> Path:
        """Генерация HTML отчета"""
        html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HH v4 Test Pipeline Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .summary-card.passed {{ border-left-color: #28a745; }}
        .summary-card.failed {{ border-left-color: #dc3545; }}
        .test-section {{ margin-bottom: 40px; }}
        .test-section h2 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 5px; }}
        .test-results {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin-bottom: 15px; }}
        .test-item {{ margin-bottom: 10px; padding: 10px; background: white; border-radius: 4px; }}
        .test-item.passed {{ border-left: 4px solid #28a745; }}
        .test-item.failed {{ border-left: 4px solid #dc3545; }}
        .screenshots {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .screenshot {{ text-align: center; }}
        .screenshot img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 4px; }}
        .details {{ background: #f1f3f4; padding: 10px; margin-top: 5px; border-radius: 4px; font-size: 12px; }}
        .error {{ color: #dc3545; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>HH v4 Test Pipeline Report</h1>
            <p>Generated: {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>Unit Tests</h3>
                <p><strong>{self.results['unit_tests'].get('passed_tests', 0)}</strong> / {self.results['unit_tests'].get('total_tests', 0)} passed</p>
                <p>{self.results['unit_tests'].get('overall_percentage', 0):.1f}% success rate</p>
            </div>
            <div class="summary-card">
                <h3>Integration Tests</h3>
                <p><strong>{self.results['integration_tests'].get('passed_tests', 0)}</strong> / {self.results['integration_tests'].get('total_tests', 0)} passed</p>
                <p>{self.results['integration_tests'].get('success_rate', 0):.1f}% success rate</p>
            </div>
            <div class="summary-card">
                <h3>Overall</h3>
                <p><strong>{self.results['pipeline_summary'].get('total_passed', 0)}</strong> / {self.results['pipeline_summary'].get('total_tests', 0)} passed</p>
                <p>{self.results['pipeline_summary'].get('overall_success_rate', 0):.1f}% success rate</p>
            </div>
        </div>
"""
        
        # Unit Tests Section
        if self.results['unit_tests']:
            html_content += """
        <div class="test-section">
            <h2>📋 Unit & Functional Tests</h2>
            <div class="test-results">
"""
            
            for test in self.results['unit_tests'].get('detailed_results', []):
                status_class = 'passed' if test['passed'] else 'failed'
                html_content += f"""
                <div class="test-item {status_class}">
                    <strong>{test['name']}</strong> (Priority {test['priority']})
                    <div class="details">
                        <p>Test ID: {test['test_id']}</p>
                        <p>Execution Time: {test['execution_time']:.2f}s</p>
                        {f'<p class="error">Error: {test["error_message"]}</p>' if test['error_message'] else ''}
                        {f'<pre>{json.dumps(test["details"], indent=2, ensure_ascii=False)}</pre>' if test['details'] else ''}
                    </div>
                </div>
"""
            
            html_content += """
            </div>
        </div>
"""
        
        # Integration Tests Section
        if self.results['integration_tests']:
            html_content += """
        <div class="test-section">
            <h2>🌐 Integration Tests with Screenshots</h2>
            <div class="test-results">
"""
            
            for test in self.results['integration_tests'].get('results', []):
                status_class = 'passed' if test['passed'] else 'failed'
                html_content += f"""
                <div class="test-item {status_class}">
                    <strong>{test['name']}</strong> (Priority {test['priority']})
                    <div class="details">
                        <p>Test ID: {test['test_id']}</p>
                        {f'<p class="error">Error: {test["error_message"]}</p>' if test['error_message'] else ''}
                        {f'<pre>{json.dumps(test["details"], indent=2, ensure_ascii=False)}</pre>' if test['details'] else ''}
                    </div>
                </div>
"""
            
            html_content += """
            </div>
        </div>
"""
            
            # Screenshots Section
            screenshots = []
            for test in self.results['integration_tests'].get('results', []):
                details = test.get('details', {})
                for key, value in details.items():
                    if 'screenshot' in key and isinstance(value, str) and value.endswith('.png'):
                        screenshots.append((test['name'], key, value))
            
            if screenshots:
                html_content += """
        <div class="test-section">
            <h2>📸 Screenshots</h2>
            <div class="screenshots">
"""
                
                for test_name, key, screenshot_path in screenshots:
                    # Конвертируем абсолютный путь в относительный для HTML
                    rel_path = Path(screenshot_path).name
                    html_content += f"""
                <div class="screenshot">
                    <h4>{test_name}</h4>
                    <p>{key}</p>
                    <img src="{rel_path}" alt="{test_name} - {key}">
                </div>
"""
                
                html_content += """
            </div>
        </div>
"""
        
        html_content += """
    </div>
</body>
</html>
"""
        
        # Сохранение HTML файла
        html_file = self.reports_dir / f'test_report_{timestamp}.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return html_file
    
    async def run_full_pipeline(self) -> Dict:
        """Запуск полного пайплайна тестов"""
        start_time = time.time()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        self.logger.info("="*60)
        self.logger.info("STARTING FULL TEST PIPELINE")
        self.logger.info("="*60)
        
        try:
            # 1. Unit/Functional Tests
            self.logger.info("Phase 1: Unit & Functional Tests")
            self.results['unit_tests'] = self.run_unit_tests([1, 2])
            
            # 2. Integration Tests с UI
            self.logger.info("Phase 2: Integration Tests with UI Screenshots")
            self.results['integration_tests'] = await self.run_integration_tests()
            
            # 3. Общая статистика
            total_tests = (
                self.results['unit_tests'].get('total_tests', 0) + 
                self.results['integration_tests'].get('total_tests', 0)
            )
            total_passed = (
                self.results['unit_tests'].get('passed_tests', 0) + 
                self.results['integration_tests'].get('passed_tests', 0)
            )
            
            overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
            total_time = time.time() - start_time
            
            self.results['pipeline_summary'] = {
                'total_tests': total_tests,
                'total_passed': total_passed,
                'total_failed': total_tests - total_passed,
                'overall_success_rate': overall_success_rate,
                'execution_time': total_time,
                'timestamp': timestamp
            }
            
            # 4. Генерация отчетов
            self.logger.info("Phase 3: Generating Reports")
            
            # JSON отчет
            json_file = self.reports_dir / f'pipeline_results_{timestamp}.json'
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            # HTML отчет
            html_file = self.generate_html_report(timestamp)
            
            # Копирование скриншотов в папку отчетов
            screenshots_src = Path(__file__).parent.parent / 'reports' / 'screenshots'
            if screenshots_src.exists():
                for screenshot in screenshots_src.glob('*.png'):
                    screenshot.rename(self.reports_dir / screenshot.name)
            
            self.logger.info("="*60)
            self.logger.info("TEST PIPELINE COMPLETED")
            self.logger.info("="*60)
            self.logger.info(f"Total Tests: {total_tests}")
            self.logger.info(f"Passed: {total_passed}")
            self.logger.info(f"Failed: {total_tests - total_passed}")
            self.logger.info(f"Success Rate: {overall_success_rate:.1f}%")
            self.logger.info(f"Execution Time: {total_time:.1f}s")
            self.logger.info(f"JSON Report: {json_file}")
            self.logger.info(f"HTML Report: {html_file}")
            
            return self.results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            raise


async def main():
    """Главная функция для CLI запуска"""
    import argparse
    
    parser = argparse.ArgumentParser(description='HH v4 Test Pipeline')
    parser.add_argument('--unit-only', action='store_true', help='Запустить только unit тесты')
    parser.add_argument('--integration-only', action='store_true', help='Запустить только интеграционные тесты')
    parser.add_argument('--priorities', type=str, default='1,2', help='Приоритеты для unit тестов')
    
    args = parser.parse_args()
    
    pipeline = TestPipeline()
    
    try:
        if args.unit_only:
            priorities = [int(p.strip()) for p in args.priorities.split(',')]
            results = pipeline.run_unit_tests(priorities)
            print(f"Unit tests: {results['passed_tests']}/{results['total_tests']} passed")
            
        elif args.integration_only:
            results = await pipeline.run_integration_tests()
            print(f"Integration tests: {results['passed_tests']}/{results['total_tests']} passed")
            
        else:
            # Полный пайплайн
            results = await pipeline.run_full_pipeline()
            summary = results['pipeline_summary']
            return 0 if summary['total_failed'] == 0 else 1
        
        return 0
        
    except Exception as e:
        print(f"Pipeline error: {e}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user")
        sys.exit(1)
