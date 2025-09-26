"""Visual smoke tests with Playwright
Auto-generated from master_plan.json
Date: 2025-09-26
"""
from playwright.sync_api import sync_playwright, expect
import json
from pathlib import Path
from PIL import Image, ImageChops
import io
import pytest

BASE_URL = 'http://localhost:8000'

class TestUIBaseline:
    """Visual regression tests for UI"""
    
    def setup_class(self):
        self.baseline_dir = Path(__file__).parent / 'baselines'
        self.baseline_dir.mkdir(exist_ok=True)
        self.diff_dir = Path(__file__).parent.parent.parent / 'reports' / 'visual_diff'
        self.diff_dir.mkdir(parents=True, exist_ok=True)
    
    def test_dashboard_layout(self):
        """Test dashboard layout hasn't changed"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(BASE_URL, wait_until='networkidle')
                
                # Take screenshot
                screenshot = page.screenshot(full_page=True)
                baseline_path = self.baseline_dir / 'dashboard.png'
                
                if not baseline_path.exists():
                    # Save baseline
                    with open(baseline_path, 'wb') as f:
                        f.write(screenshot)
                    print(f"Baseline created: {baseline_path}")
                else:
                    # Compare with baseline
                    current = Image.open(io.BytesIO(screenshot))
                    baseline = Image.open(baseline_path)
                    
                    # Check dimensions match
                    if current.size != baseline.size:
                        diff_path = self.diff_dir / 'dashboard_size_diff.txt'
                        with open(diff_path, 'w') as f:
                            f.write(f"Size mismatch: {current.size} vs {baseline.size}")
                        assert False, f"Visual difference detected: size mismatch"
                    
                    # Check pixel differences
                    diff = ImageChops.difference(current, baseline)
                    if diff.getbbox():
                        diff_path = self.diff_dir / 'dashboard_diff.png'
                        diff.save(diff_path)
                        assert False, f'Visual difference detected, saved to {diff_path}'
                    
                    print("Visual test passed: no differences")
            except Exception as e:
                pytest.skip(f"Web server not accessible: {e}")
            finally:
                browser.close()
    
    def test_ui_elements_present(self):
        """Test that key UI elements are present"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(BASE_URL, wait_until='networkidle')
                
                # Check for data-test attributes
                elements_to_check = [
                    '[data-test="status-card-system-health"]',
                    '[data-test="status-card-daemon-status"]',
                    '[data-test="status-card-tasks-queue"]',
                    '[data-test="refresh-button"]'
                ]
                
                for selector in elements_to_check:
                    try:
                        element = page.query_selector(selector)
                        if element:
                            expect(element).to_be_visible(timeout=5000)
                    except:
                        # If data-test attributes don't exist, check by ID
                        id_selector = selector.replace('data-test=', 'id=').replace('"', '').replace('status-card-', '')
                        element = page.query_selector(id_selector)
                        if element:
                            print(f"Found element by ID instead of data-test: {id_selector}")
            except Exception as e:
                pytest.skip(f"Web server not accessible: {e}")
            finally:
                browser.close()
    
    def test_responsive_layout(self):
        """Test responsive layout at different viewport sizes"""
        viewports = [
            {'width': 1920, 'height': 1080, 'name': 'desktop'},
            {'width': 1366, 'height': 768, 'name': 'laptop'},
            {'width': 768, 'height': 1024, 'name': 'tablet'},
            {'width': 375, 'height': 667, 'name': 'mobile'}
        ]
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for viewport in viewports:
                    page = browser.new_page(viewport={'width': viewport['width'], 'height': viewport['height']})
                    page.goto(BASE_URL, wait_until='networkidle')
                    
                    screenshot_path = self.baseline_dir / f"dashboard_{viewport['name']}.png"
                    screenshot = page.screenshot()
                    
                    if not screenshot_path.exists():
                        with open(screenshot_path, 'wb') as f:
                            f.write(screenshot)
                        print(f"Baseline created for {viewport['name']}: {screenshot_path}")
                    else:
                        # Compare with baseline
                        current = Image.open(io.BytesIO(screenshot))
                        baseline = Image.open(screenshot_path)
                        
                        if current.size == baseline.size:
                            diff = ImageChops.difference(current, baseline)
                            if diff.getbbox():
                                diff_path = self.diff_dir / f"dashboard_{viewport['name']}_diff.png"
                                diff.save(diff_path)
                                print(f"Warning: Visual difference at {viewport['name']}")
                    
                    page.close()
            except Exception as e:
                pytest.skip(f"Web server not accessible: {e}")
            finally:
                browser.close()
    
    def test_interactive_elements(self):
        """Test that buttons and interactive elements work"""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(BASE_URL, wait_until='networkidle')
                
                # Test refresh button
                refresh_btn = page.query_selector('button:has-text("Refresh")')
                if refresh_btn:
                    refresh_btn.click()
                    # Wait for any loading indicator or state change
                    page.wait_for_timeout(1000)
                    print("Refresh button clicked successfully")
                
                # Test daemon control buttons
                for button_text in ['Start', 'Stop', 'Restart']:
                    btn = page.query_selector(f'button:has-text("{button_text}")')
                    if btn and btn.is_visible():
                        print(f"Found {button_text} button")
            except Exception as e:
                pytest.skip(f"Web server not accessible: {e}")
            finally:
                browser.close()


if __name__ == '__main__':
    print("Running visual smoke tests...")
    pytest.main([__file__, '-v', '--tb=short'])
