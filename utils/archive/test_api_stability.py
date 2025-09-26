# // TEMP: Test API stability improvements
"""
Test script for enhanced API stability features:
- Exponential backoff (1s->4s->16s->64s)
- Auth provider rotation
- Improved error handling
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from plugins.fetcher_v4 import VacancyFetcher, ExponentialBackoff
from core.auth import choose_provider, rotate_to_next_provider, mark_provider_failed, get_all_providers, reset_auth_state
import time

def test_exponential_backoff():
    """Test ExponentialBackoff class"""
    print("🔧 Testing ExponentialBackoff...")
    
    backoff = ExponentialBackoff(base_delay=1.0, max_retries=4)
    
    print(f"Max retries: {backoff.max_retries}")
    
    for i in range(5):
        delay = backoff.get_delay()
        should_retry = backoff.should_retry(500)
        print(f"  Attempt {i+1}: delay={delay:.2f}s, should_retry={should_retry}")
        if delay > 0:
            backoff.retry_count += 1
    
    print("✅ ExponentialBackoff test completed")

def test_auth_rotation():
    """Test auth provider rotation"""
    print("\n🔧 Testing Auth Provider Rotation...")
    
    # Reset state
    reset_auth_state()
    
    # Get all providers
    providers = get_all_providers("download")
    print(f"Available providers: {len(providers)}")
    
    for provider in providers:
        print(f"  - {provider.get('name', 'unnamed')} (type: {provider.get('type', 'unknown')})")
    
    if not providers:
        print("⚠️  No auth providers configured - create config/auth_roles.json for testing")
        return
    
    # Test current selection
    current = choose_provider("download")
    print(f"Current provider: {current.get('name', 'unknown') if current else 'None'}")
    
    # Test rotation
    if len(providers) > 1:
        next_provider = rotate_to_next_provider("download")
        print(f"Rotated to: {next_provider.get('name', 'unknown') if next_provider else 'None'}")
    
    # Test failure marking
    if current:
        mark_provider_failed(current['name'])
        print(f"Marked '{current['name']}' as failed")
    
    print("✅ Auth rotation test completed")

def test_fetcher_integration():
    """Test VacancyFetcher with new stability features"""
    print("\n🔧 Testing VacancyFetcher Integration...")
    
    try:
        fetcher = VacancyFetcher()
        
        # Check backoff initialization
        print(f"Backoff initialized: {hasattr(fetcher, 'backoff')}")
        if hasattr(fetcher, 'backoff'):
            print(f"  Max retries: {fetcher.backoff.max_retries}")
            print(f"  Base delay: {fetcher.backoff.base_delay}s")
        
        # Check auth provider tracking
        print(f"Auth provider tracking: {hasattr(fetcher, 'current_auth_provider')}")
        if hasattr(fetcher, 'current_auth_provider'):
            current = fetcher.current_auth_provider
            provider_name = current.get('name', 'unknown') if current else 'None'
            print(f"  Current provider: {provider_name}")
        
        print("✅ VacancyFetcher integration test completed")
        
    except Exception as e:
        print(f"❌ VacancyFetcher test failed: {e}")

def test_error_scenarios():
    """Test different error scenarios"""
    print("\n🔧 Testing Error Scenarios...")
    
    backoff = ExponentialBackoff()
    
    # Test different status codes
    test_cases = [
        (400, "Bad Request - should not retry"),
        (401, "Unauthorized - should retry (auth rotation)"),
        (403, "Forbidden - should retry (auth rotation)"),
        (429, "Rate Limited - should retry"),
        (500, "Server Error - should retry"),
        (502, "Bad Gateway - should retry"),
        (503, "Service Unavailable - should retry")
    ]
    
    for status_code, description in test_cases:
        backoff.reset()
        should_retry = backoff.should_retry(status_code)
        print(f"  {status_code}: {description} -> {should_retry}")
    
    print("✅ Error scenarios test completed")

def simulate_api_failure_recovery():
    """Simulate API failure and recovery pattern"""
    print("\n🔧 Simulating API Failure Recovery...")
    
    backoff = ExponentialBackoff(base_delay=0.1, max_retries=3)  # Faster for testing
    
    # Simulate server errors with eventual success
    for attempt in range(5):
        if attempt < 3:
            # Simulate failures
            status_code = 503  # Service Unavailable
            should_retry = backoff.should_retry(status_code)
            
            if should_retry:
                delay = backoff.wait_and_increment()
                print(f"  Attempt {attempt + 1}: Failed (503), waiting {delay:.2f}s...")
            else:
                print(f"  Attempt {attempt + 1}: Max retries reached, giving up")
                break
        else:
            # Simulate success
            print(f"  Attempt {attempt + 1}: Success (200)")
            break
    
    print("✅ API failure recovery simulation completed")

if __name__ == "__main__":
    print("API Stability Features Test Suite")
    print("=" * 50)
    
    test_exponential_backoff()
    test_auth_rotation()
    test_fetcher_integration()
    test_error_scenarios()
    simulate_api_failure_recovery()
    
    print("\n🎉 All API stability tests completed!")
    print("\nNext steps:")
    print("1. Integrate backoff into _fetch_page method")
    print("2. Add auth rotation on 401/403 errors")  
    print("3. Test with real API calls")
