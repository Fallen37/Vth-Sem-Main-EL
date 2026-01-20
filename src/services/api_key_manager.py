"""API Key Manager for rotating between multiple Google Gemini API keys."""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import google.generativeai as genai


class APIKeyManager:
    """Manages rotating API keys with rate limit tracking."""
    
    def __init__(self):
        """Initialize API key manager with available keys."""
        # API keys in order of preference
        self.api_keys = [
            "AIzaSyAz4jwDFwxrVCmU4SVOAMIRLrxtF2oFvQA",  # Original key
            "AIzaSyCulZGm1P382VhSACxJs94qrRxIZXyZj3c",  # New key 1
            "AIzaSyDGKMTlJRpdV1zyfFe-JF87oP7BXQ9nqaQ",  # New key 2
        ]
        
        # Track usage for each key
        self.key_usage = {}
        self.key_reset_times = {}
        self.current_key_index = 0
        
        # Initialize tracking
        for i, key in enumerate(self.api_keys):
            self.key_usage[i] = 0
            self.key_reset_times[i] = None
        
        # Load state from file if it exists
        self._load_state()
        
        # Set initial key
        self._set_current_key()
    
    def _load_state(self):
        """Load API key usage state from file."""
        state_file = Path("data/api_key_state.json")
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.key_usage = state.get('key_usage', self.key_usage)
                    self.current_key_index = state.get('current_key_index', 0)
                    
                    # Parse reset times
                    reset_times = state.get('key_reset_times', {})
                    for key_idx, reset_time_str in reset_times.items():
                        if reset_time_str:
                            self.key_reset_times[int(key_idx)] = datetime.fromisoformat(reset_time_str)
            except Exception as e:
                print(f"Error loading API key state: {e}")
    
    def _save_state(self):
        """Save API key usage state to file."""
        state_file = Path("data/api_key_state.json")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            state = {
                'key_usage': self.key_usage,
                'current_key_index': self.current_key_index,
                'key_reset_times': {
                    str(k): v.isoformat() if v else None 
                    for k, v in self.key_reset_times.items()
                }
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving API key state: {e}")
    
    def _set_current_key(self):
        """Set the current API key in genai."""
        key = self.api_keys[self.current_key_index]
        try:
            genai.configure(api_key=key)
            print(f"✓ Using API key {self.current_key_index + 1}/{len(self.api_keys)}")
        except Exception as e:
            print(f"Error configuring API key {self.current_key_index}: {e}")
    
    def _is_key_available(self, key_index: int) -> bool:
        """Check if a key is available (not rate limited)."""
        reset_time = self.key_reset_times.get(key_index)
        
        if reset_time is None:
            return True
        
        # Check if reset time has passed
        if datetime.now() >= reset_time:
            # Reset the key
            self.key_usage[key_index] = 0
            self.key_reset_times[key_index] = None
            return True
        
        return False
    
    def _find_available_key(self) -> Optional[int]:
        """Find the next available API key."""
        # First, try to find a key that's not rate limited
        for i in range(len(self.api_keys)):
            if self._is_key_available(i):
                return i
        
        # If all keys are rate limited, return the one with the earliest reset time
        earliest_reset = None
        earliest_index = None
        
        for i, reset_time in self.key_reset_times.items():
            if reset_time and (earliest_reset is None or reset_time < earliest_reset):
                earliest_reset = reset_time
                earliest_index = i
        
        return earliest_index
    
    def rotate_key(self):
        """Rotate to the next available API key."""
        available_index = self._find_available_key()
        
        if available_index is None:
            print("⚠ No API keys available!")
            return False
        
        if available_index != self.current_key_index:
            self.current_key_index = available_index
            self._set_current_key()
            self._save_state()
            return True
        
        return False
    
    def mark_rate_limited(self, retry_after_seconds: int = 86400):
        """Mark the current key as rate limited."""
        reset_time = datetime.now() + timedelta(seconds=retry_after_seconds)
        self.key_reset_times[self.current_key_index] = reset_time
        
        print(f"⚠ API key {self.current_key_index + 1} rate limited until {reset_time}")
        
        # Try to rotate to another key
        if self.rotate_key():
            print(f"✓ Rotated to API key {self.current_key_index + 1}")
        else:
            print("⚠ No other API keys available!")
        
        self._save_state()
    
    def record_request(self):
        """Record a successful API request."""
        self.key_usage[self.current_key_index] += 1
        self._save_state()
    
    def get_current_key(self) -> str:
        """Get the current API key."""
        return self.api_keys[self.current_key_index]
    
    def get_status(self) -> dict:
        """Get status of all API keys."""
        status = {
            'current_key_index': self.current_key_index,
            'keys': []
        }
        
        for i, key in enumerate(self.api_keys):
            key_status = {
                'index': i,
                'usage_count': self.key_usage.get(i, 0),
                'is_current': i == self.current_key_index,
                'is_available': self._is_key_available(i),
                'reset_time': self.key_reset_times.get(i).isoformat() if self.key_reset_times.get(i) else None,
            }
            status['keys'].append(key_status)
        
        return status


# Global instance
_api_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    """Get or create the global API key manager."""
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager
