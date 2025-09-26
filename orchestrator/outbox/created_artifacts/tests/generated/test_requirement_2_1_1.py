"""Generated test for requirement 2.1.1: Resource monitoring"""
import pytest
import psutil
from pathlib import Path
import json

class TestRequirement_2_1_1:
    """Test resource monitoring thresholds"""
    
    def setup_method(self):
        """Load configuration"""
        config_path = Path(__file__).parent.parent.parent.parent.parent / 'config' / 'config_v4.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        self.thresholds = self.config.get('system_monitoring', {})
    
    def test_cpu_threshold(self):
        """Test CPU usage is below threshold"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_threshold = self.thresholds.get('cpu_critical_percent', 90)
        
        assert cpu_percent < cpu_threshold, f"CPU usage {cpu_percent}% exceeds threshold {cpu_threshold}%"
    
    def test_memory_threshold(self):
        """Test memory usage is below threshold"""
        memory = psutil.virtual_memory()
        memory_threshold = self.thresholds.get('memory_critical_percent', 80)
        
        assert memory.percent < memory_threshold, f"Memory usage {memory.percent}% exceeds threshold {memory_threshold}%"
    
    def test_disk_threshold(self):
        """Test disk usage is below threshold"""
        disk = psutil.disk_usage('/')
        disk_threshold = self.thresholds.get('disk_critical_percent', 80)
        
        assert disk.percent < disk_threshold, f"Disk usage {disk.percent}% exceeds threshold {disk_threshold}%"
    
    def test_monitoring_service_running(self):
        """Test that monitoring service is accessible"""
        from core.system_monitor import SystemMonitor
        
        monitor = SystemMonitor()
        status = monitor.get_status()
        
        assert status is not None, "System monitor not responding"
        assert 'cpu' in status, "CPU metrics missing"
        assert 'memory' in status, "Memory metrics missing"
        assert 'disk' in status, "Disk metrics missing"
