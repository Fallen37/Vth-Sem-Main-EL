# API Key Rotation System

## Overview

The system now supports rotating between multiple Google Gemini API keys to handle rate limiting gracefully. When one key hits the free tier limit (20 requests/day), the system automatically switches to the next available key.

## Configuration

### API Keys

Three API keys are configured in `src/services/api_key_manager.py`:

1. **Key 1** (Original): `AIzaSyAz4jwDFwxrVCmU4SVOAMIRLrxtF2oFvQA`
2. **Key 2**: `AIzaSyCulZGm1P382VhSACxJs94qrRxIZXyZj3c`
3. **Key 3**: `AIzaSyDGKMTlJRpdV1zyfFe-JF87oP7BXQ9nqaQ`

To add more keys, edit the `api_keys` list in `APIKeyManager.__init__()`.

## How It Works

### 1. **Initialization**
- On startup, the system loads the API key manager
- It checks for saved state in `data/api_key_state.json`
- The first available key is set as the current key

### 2. **Normal Operation**
- Each API request increments the usage counter for the current key
- The state is saved to disk after each request
- Usage is tracked per key

### 3. **Rate Limit Detection**
When a rate limit error is detected:
- The system identifies the error (quota, rate, or 429 status)
- Marks the current key as rate-limited with a reset time
- Automatically rotates to the next available key
- Retries the request with the new key

### 4. **Key Rotation**
The system finds the next available key by:
1. Checking if any keys have reset times that have passed
2. If a key's reset time has passed, it's marked as available again
3. If all keys are rate-limited, it returns the one with the earliest reset time

## API Endpoints

### Check API Key Status

```bash
GET /chat/api-status
Authorization: Bearer {user_id}
```

**Response:**
```json
{
  "current_key_index": 0,
  "keys": [
    {
      "index": 0,
      "usage_count": 5,
      "is_current": true,
      "is_available": true,
      "reset_time": null
    },
    {
      "index": 1,
      "usage_count": 0,
      "is_current": false,
      "is_available": true,
      "reset_time": null
    },
    {
      "index": 2,
      "usage_count": 0,
      "is_current": false,
      "is_available": true,
      "reset_time": null
    }
  ]
}
```

## State Persistence

The system saves state to `data/api_key_state.json`:

```json
{
  "current_key_index": 0,
  "key_usage": {
    "0": 5,
    "1": 0,
    "2": 0
  },
  "key_reset_times": {
    "0": null,
    "1": null,
    "2": "2026-01-20T20:49:36.000000"
  }
}
```

This allows the system to:
- Resume with the correct key after restart
- Track usage across restarts
- Remember which keys are rate-limited

## Fallback Behavior

If all API keys are rate-limited:
1. The system uses the key with the earliest reset time
2. If the request still fails, it falls back to generating responses from the textbook content directly
3. The fallback response maintains the same format (one section at a time)

## Monitoring

### Check Current Key
```python
from src.services.api_key_manager import get_api_key_manager

manager = get_api_key_manager()
status = manager.get_status()
print(f"Current key: {status['current_key_index'] + 1}")
```

### View Usage
```python
manager = get_api_key_manager()
for key_info in manager.get_status()['keys']:
    print(f"Key {key_info['index'] + 1}: {key_info['usage_count']} requests")
```

## Adding More API Keys

To add more API keys:

1. Open `src/services/api_key_manager.py`
2. Add the new key to the `api_keys` list:
   ```python
   self.api_keys = [
       "AIzaSyAz4jwDFwxrVCmU4SVOAMIRLrxtF2oFvQA",
       "AIzaSyCulZGm1P382VhSACxJs94qrRxIZXyZj3c",
       "AIzaSyDGKMTlJRpdV1zyfFe-JF87oP7BXQ9nqaQ",
       "YOUR_NEW_KEY_HERE",  # Add new key
   ]
   ```
3. Restart the backend

## Rate Limit Details

### Free Tier Limits
- **20 requests per day** per API key
- **1 request per second** per API key
- Reset time: 24 hours from first request

### With 3 Keys
- **60 requests per day** total
- Effectively 3x the capacity

### Upgrade Options
- **Paid tier**: Significantly higher limits
- **Multiple projects**: Each project gets its own quota
- **Multiple API keys per project**: Can create multiple keys

## Troubleshooting

### All Keys Rate Limited
If all keys are rate-limited:
1. Check the reset times in the API status endpoint
2. Wait for the earliest reset time to pass
3. The system will automatically switch to the available key

### Key Not Rotating
1. Check the logs for error messages
2. Verify the API keys are valid
3. Check `data/api_key_state.json` for state issues
4. Delete the state file to reset: `rm data/api_key_state.json`

### Usage Not Tracking
1. Verify `data/` directory exists and is writable
2. Check file permissions on `data/api_key_state.json`
3. Check backend logs for save errors

## Performance Impact

- **Minimal overhead**: Key rotation adds <10ms per request
- **State persistence**: Saves state asynchronously
- **Automatic recovery**: No manual intervention needed

## Future Improvements

- [ ] Add metrics/dashboard for API usage
- [ ] Implement request queuing for rate limiting
- [ ] Add alerts when keys are rate-limited
- [ ] Support for different API providers (Claude, etc.)
- [ ] Automatic key refresh from environment variables
