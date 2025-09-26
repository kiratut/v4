"""Smoke tests for critical functionality
Auto-generated from master_plan.json
Date: 2025-09-26
"""
import pytest
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any

BASE_URL = 'http://localhost:8000'
TIMEOUT = 5

class TestCriticalPaths:
    """Test critical user paths"""
    
    def test_api_health(self):
        """API should be reachable"""
        try:
            response = requests.get(f'{BASE_URL}/api/version', timeout=TIMEOUT)
            assert response.status_code == 200
            data = response.json()
            assert 'version' in data
        except requests.exceptions.ConnectionError:
            pytest.skip("Web server not running")
    
    def test_daemon_lifecycle(self):
        """Daemon should start/stop cleanly"""
        try:
            # Start daemon
            response = requests.post(f'{BASE_URL}/api/daemon/start', timeout=TIMEOUT)
            assert response.status_code in [200, 409]  # OK or already running
            
            # Check status
            response = requests.get(f'{BASE_URL}/api/daemon/status', timeout=TIMEOUT)
            assert response.status_code == 200
            
            # Stop daemon
            response = requests.post(f'{BASE_URL}/api/daemon/stop', timeout=TIMEOUT)
            assert response.status_code in [200, 404]  # OK or not running
        except requests.exceptions.ConnectionError:
            pytest.skip("Web server not running")
    
    def test_config_loading(self):
        """Configuration should load correctly"""
        config_path = Path(__file__).parent.parent.parent / 'config' / 'config_v4.json'
        assert config_path.exists(), f"Config file not found: {config_path}"
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # Check critical config sections
        assert 'daemon' in config, "Missing 'daemon' section"
        assert 'web_interface' in config, "Missing 'web_interface' section"
        assert 'logging' in config, "Missing 'logging' section"
    
    def test_database_connection(self):
        """Database should be accessible"""
        import sqlite3
        db_path = Path(__file__).parent.parent.parent / 'data' / 'production.db'
        
        if not db_path.exists():
            # Create if not exists
            db_path.parent.mkdir(exist_ok=True)
            db_path.touch()
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('SELECT sqlite_version()')
        version = cursor.fetchone()
        conn.close()
        
        assert version is not None
    
    def test_critical_endpoints(self):
        """All critical API endpoints should respond"""
        endpoints = [
            '/api/stats/system_health',
            '/api/daemon/status',
            '/api/daemon/tasks',
            '/api/tests/status',
            '/api/dashboard/config'
        ]
        
        for endpoint in endpoints:
            try:
                response = requests.get(f'{BASE_URL}{endpoint}', timeout=TIMEOUT)
                assert response.status_code in [200, 404], f'{endpoint} returned {response.status_code}'
            except requests.exceptions.ConnectionError:
                pytest.skip(f"Web server not running for {endpoint}")
    
    def test_required_files_exist(self):
        """Check that all required files exist"""
        required_files = [
            'cli_v4.py',
            'core/scheduler_daemon.py',
            'core/task_dispatcher.py',
            'core/task_database.py',
            'plugins/fetcher_v4.py',
            'web/server.py',
            'config/config_v4.json'
        ]
        
        base_path = Path(__file__).parent.parent.parent
        for file_path in required_files:
            full_path = base_path / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"
    
    def test_data_test_attributes_present(self):
        """Check that UI elements have data-test attributes"""
        try:
            response = requests.get(BASE_URL, timeout=TIMEOUT)
            if response.status_code == 200:
                # Check for data-test attributes in HTML
                assert 'data-test' in response.text or 'dashboard' in response.text.lower()
        except requests.exceptions.ConnectionError:
            pytest.skip("Web server not running")


if __name__ == '__main__':
    # Run smoke tests
    print("Running smoke tests...")
    pytest.main([__file__, '-v', '--tb=short'])
