"""
Auth helper for HH Tool v4 - Enhanced profile rotation and error handling
- Loads prioritized auth providers from config/auth_roles.json (v3-compatible)
- Provides headers for requests.Session (Bearer tokens)
- Supports profile rotation on auth failures
- Falls back gracefully if config is missing

// Chg_AUTH_ROTATE_1909: Enhanced auth with profile rotation and failure tracking
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, List

LOGGER = logging.getLogger(__name__)

AUTH_FILE = Path("config/auth_roles.json")
CREDENTIALS_FILE = Path("config/credentials.json")


def _load_json(path: Path) -> Optional[Dict]:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        LOGGER.error("Failed to read %s: %s", path, e)
    return None


# Global auth state for profile rotation
_auth_state = {
    'current_provider_index': 0,
    'failed_providers': set(),
    'last_rotation': 0,
    'rotation_cooldown': 60  # seconds between rotations
}


def get_all_providers(purpose: str = "download") -> List[Dict]:
    """Get all available providers for the given purpose, sorted by priority"""
    data = _load_json(AUTH_FILE)
    if not data or "auth_providers" not in data:
        return []
    
    providers = []
    for name, p in data["auth_providers"].items():
        allowed = p.get("allowed_for", ["download"]) or ["download"]
        if purpose in allowed:
            providers.append({"name": name, **p})
    
    if not providers:
        return []
    
    # // Chg_AUTH_PREF_1509: для purpose='download' предпочитаем access_token над oauth
    def _pref(p: Dict) -> int:
        t = (p.get("type") or "").lower()
        if t == "access_token":
            return 0
        if t == "oauth":
            return 1
        return 2
    
    providers.sort(key=lambda x: (_pref(x), int(x.get("priority", 100))))
    return providers


def choose_provider(purpose: str = "download") -> Optional[Dict]:
    """Choose the current auth provider, with rotation support"""
    providers = get_all_providers(purpose)
    if not providers:
        return None
    
    # Return the current provider based on rotation state
    current_index = _auth_state['current_provider_index']
    if current_index < len(providers):
        return providers[current_index]
    
    # Reset if index is out of bounds
    _auth_state['current_provider_index'] = 0
    return providers[0]


def mark_provider_failed(provider_name: str) -> None:
    """Mark a provider as failed and trigger rotation if needed"""
    if not provider_name:
        return
    
    _auth_state['failed_providers'].add(provider_name)
    LOGGER.warning(f"Auth provider '{provider_name}' marked as failed")
    
    # Trigger rotation if cooldown period has passed
    now = time.time()
    if now - _auth_state['last_rotation'] > _auth_state['rotation_cooldown']:
        rotate_to_next_provider()


def rotate_to_next_provider(purpose: str = "download") -> Optional[Dict]:
    """Rotate to the next available auth provider"""
    providers = get_all_providers(purpose)
    if len(providers) <= 1:
        LOGGER.info("Only one or no auth providers available, cannot rotate")
        return choose_provider(purpose)
    
    current_index = _auth_state['current_provider_index']
    failed_providers = _auth_state['failed_providers']
    
    # Try to find next working provider
    for i in range(1, len(providers)):
        next_index = (current_index + i) % len(providers)
        next_provider = providers[next_index]
        
        if next_provider['name'] not in failed_providers:
            _auth_state['current_provider_index'] = next_index
            _auth_state['last_rotation'] = time.time()
            LOGGER.info(f"Rotated to auth provider '{next_provider['name']}' (index {next_index})")
            return next_provider
    
    # All providers failed, reset failed set and use first
    LOGGER.warning("All auth providers failed, resetting failure state")
    _auth_state['failed_providers'].clear()
    _auth_state['current_provider_index'] = 0
    _auth_state['last_rotation'] = time.time()
    
    return providers[0] if providers else None


def reset_auth_state() -> None:
    """Reset auth rotation state (useful for testing or recovery)"""
    _auth_state['current_provider_index'] = 0
    _auth_state['failed_providers'].clear()
    _auth_state['last_rotation'] = 0
    LOGGER.info("Auth rotation state reset")


def get_auth_headers(purpose: str = "download") -> Dict[str, str]:
    """Return Authorization headers if configured, else empty dict."""
    prov = choose_provider(purpose)
    if not prov:
        return {}
    ptype = prov.get("type")
    if ptype == "access_token":
        token = prov.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}
    elif ptype == "oauth":
        # Minimal support: try direct access_token from credentials.json
        creds = _load_json(CREDENTIALS_FILE) or {}
        token = creds.get("access_token")
        if token:
            return {"Authorization": f"Bearer {token}"}
        LOGGER.warning("OAuth provider selected but no access_token found in credentials.json")
    return {}


def apply_auth_headers(session, purpose: str = "download") -> None:
    try:
        headers = get_auth_headers(purpose)
        if headers:
            session.headers.update(headers)
            # // Chg_AUTH_PREF_1509: логируем провайдера (тип)
            prov = choose_provider(purpose)
            LOGGER.info("Auth headers applied using provider '%s' (type=%s) for '%s'",
                        prov.get('name') if prov else 'unknown',
                        (prov.get('type') if prov else 'unknown'),
                        purpose)
        else:
            LOGGER.info("No auth headers applied (config missing or not required)")
    except Exception as e:
        LOGGER.error("Failed to apply auth headers: %s", e)
