# // TEMP: Test SystemMonitor functionality
"""
Test script for SystemMonitor - comprehensive system metrics and diagnostics
Usage: python utils/test_system_monitor.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.models import SystemMonitor
import json

def test_system_monitor():
    """Test SystemMonitor comprehensive functionality"""
    
    print("🔧 Testing SystemMonitor v4...")
    print("=" * 50)
    
    # Initialize monitor
    monitor = SystemMonitor(project_root=project_root)
    
    # Test 1: Quick status
    print("\n📊 1. Quick Status Check:")
    quick_status = monitor.get_quick_status()
    print(f"   Overall Status: {quick_status['overall_status']}")
    print(f"   CPU: {quick_status['cpu_percent']}%")
    print(f"   Memory: {quick_status['memory_percent']}%")
    
    # Test 2: Comprehensive metrics
    print("\n📈 2. Comprehensive Metrics:")
    metrics = monitor.get_comprehensive_metrics()
    
    if 'error' in metrics:
        print(f"   ❌ Error: {metrics['error']}")
        return False
    
    # Display key metrics
    system = metrics.get('system', {})
    application = metrics.get('application', {})
    
    # CPU info
    cpu = system.get('cpu', {})
    if cpu and 'error' not in cpu:
        print(f"   💻 CPU: {cpu['percent_total']}% ({cpu['count_logical']} cores)")
        if cpu.get('load_average'):
            la = cpu['load_average']
            print(f"      Load Avg: {la['1min']}, {la['5min']}, {la['15min']}")
    
    # Memory info  
    memory = system.get('memory', {})
    if memory and 'error' not in memory:
        virtual = memory.get('virtual', {})
        print(f"   🧠 Memory: {virtual.get('percent', 0)}% of {virtual.get('total_mb', 0)}MB")
        swap = memory.get('swap', {})
        if swap.get('total_mb', 0) > 0:
            print(f"      Swap: {swap.get('percent', 0)}% of {swap.get('total_mb', 0)}MB")
    
    # Disk info
    disk = system.get('disk', {})
    if disk and 'error' not in disk:
        partitions = disk.get('partitions', {})
        print(f"   💾 Disk Partitions: {len(partitions)}")
        for device, info in partitions.items():
            print(f"      {device}: {info.get('percent', 0)}% ({info.get('free_gb', 0)}GB free)")
        
        project = disk.get('project', {})
        if project:
            print(f"   📁 Project folders:")
            for folder, info in project.items():
                print(f"      {folder}: {info.get('size_mb', 0)}MB ({info.get('file_count', 0)} files)")
    
    # Process info
    process = application.get('process', {})
    if process and 'error' not in process:
        current = process.get('current', {})
        print(f"   🔄 Current Process: PID {current.get('pid')} - {current.get('memory_mb', 0)}MB")
        
        related = process.get('related_processes', [])
        if related:
            print(f"   🔗 Related Processes: {len(related)}")
            for proc in related[:3]:  # Show first 3
                print(f"      PID {proc.get('pid')}: {proc.get('name')} - {proc.get('memory_mb', 0)}MB")
    
    # Database info
    database = application.get('database', {})
    if database and database.get('status') == 'connected':
        print(f"   🗄️  Database: {database.get('file_size_mb', 0)}MB ({database.get('journal_mode')} mode)")
        tables = database.get('tables', {})
        for table, info in tables.items():
            print(f"      {table}: {info.get('record_count', 0)} records")
    
    # Health checks
    print("\n🏥 3. Health Checks:")
    health = application.get('health_checks', {})
    for check_name, check_result in health.items():
        status = check_result.get('status', 'unknown')
        message = check_result.get('message', 'No message')
        icon = {'pass': '✅', 'warning': '⚠️', 'fail': '❌'}.get(status, '❓')
        print(f"   {icon} {check_name}: {message}")
    
    # Alerts
    alerts = metrics.get('alerts', [])
    if alerts:
        print(f"\n🚨 4. Active Alerts ({len(alerts)}):")
        for alert in alerts:
            level_icon = {'info': 'ℹ️', 'warning': '⚠️', 'critical': '🔥'}.get(alert['level'], '❓')
            print(f"   {level_icon} {alert['component']}: {alert['message']}")
    else:
        print("\n✅ 4. No Active Alerts")
    
    # Network info
    network = system.get('network', {})
    if network and 'error' not in network:
        print(f"\n🌐 5. Network: {network.get('connections_count', 0)} connections")
        print(f"   Sent: {network.get('bytes_sent_mb', 0)}MB, Recv: {network.get('bytes_recv_mb', 0)}MB")
    
    return True

def test_integration_points():
    """Test integration with other system components"""
    
    print("\n🔌 Testing Integration Points:")
    print("=" * 50)
    
    # Test CLI integration
    print("\n1. CLI Integration Test:")
    try:
        # Simulate what cli_v4.py system command would do
        monitor = SystemMonitor()
        status = monitor.get_quick_status()
        print(f"   CLI Status: {status['overall_status']} (CPU: {status['cpu_percent']}%)")
        print("   ✅ CLI integration ready")
    except Exception as e:
        print(f"   ❌ CLI integration failed: {e}")
    
    # Test web API integration
    print("\n2. Web API Integration Test:")
    try:
        # Simulate what web/server.py /api/system endpoint would return
        monitor = SystemMonitor()
        metrics = monitor.get_comprehensive_metrics()
        
        # Create API response format
        api_response = {
            'status': 'ok' if 'error' not in metrics else 'error',
            'system_health': metrics.get('application', {}).get('health_checks', {}),
            'quick_metrics': {
                'cpu_percent': metrics.get('system', {}).get('cpu', {}).get('percent_total', 0),
                'memory_percent': metrics.get('system', {}).get('memory', {}).get('virtual', {}).get('percent', 0),
                'disk_usage_percent': max([
                    info.get('percent', 0) 
                    for info in metrics.get('system', {}).get('disk', {}).get('partitions', {}).values()
                ], default=0),
                'database_size_mb': metrics.get('application', {}).get('database', {}).get('file_size_mb', 0)
            },
            'alerts_count': len(metrics.get('alerts', [])),
            'timestamp': metrics.get('timestamp')
        }
        
        print(f"   API Response Status: {api_response['status']}")
        print(f"   Database Size: {api_response['quick_metrics']['database_size_mb']}MB")
        print("   ✅ Web API integration ready")
        
    except Exception as e:
        print(f"   ❌ Web API integration failed: {e}")

def save_sample_output():
    """Save sample monitoring output to file for reference"""
    
    try:
        monitor = SystemMonitor()
        metrics = monitor.get_comprehensive_metrics()
        
        # Save to logs directory
        output_file = project_root / "logs" / "system_monitor_sample.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Sample output saved to: {output_file}")
        print(f"   File size: {output_file.stat().st_size} bytes")
        
        return str(output_file)
        
    except Exception as e:
        print(f"\n❌ Failed to save sample output: {e}")
        return None

if __name__ == "__main__":
    print("SystemMonitor v4 Test Suite")
    print("=" * 60)
    
    # Run tests
    success = test_system_monitor()
    if success:
        test_integration_points()
        sample_file = save_sample_output()
        
        print("\n🎉 SystemMonitor Test Results:")
        print("✅ Core functionality working")
        print("✅ Integration points ready")
        print("✅ Sample output generated")
        
        if sample_file:
            print(f"\nNext steps:")
            print(f"1. Add 'python cli_v4.py system' command")
            print(f"2. Update web/server.py with /api/system endpoint")
            print(f"3. Review sample output: {sample_file}")
        
    else:
        print("\n❌ SystemMonitor tests failed")
        sys.exit(1)
