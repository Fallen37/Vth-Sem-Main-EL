# API Rate Limit Issue - Raw Textbook Content

## Problem
Users are seeing raw, unprocessed textbook chunks instead of coherent AI-generated explanations. Example:

```
"From Electric Current and its Effects: an electric circuit can be represented by a circuit diagram. When an electric current flows through a wire, the wire gets heated. It is the heating effect of current. This effect has many applications. ELECTRIC CURRENT AND ITS EFFECTS 169 Wires made from some special materials melt quickly and break Key Points: • when large electric currents are passed through them..."
```

## Root Cause
All three Google Gemini API keys are currently rate-limited and won't reset until **January 21, 2026 at ~1:28 PM**.

Current API key status (from `data/api_key_state.json`):
- Key 0: Rate limited until 2026-01-21 13:28:32
- Key 1: Rate limited until 2026-01-21 13:28:43
- Key 2: Rate limited until 2026-01-21 13:29:11

When all API keys are exhausted, the system falls back to `_generate_from_context_formatted()` which just returns raw textbook chunks without AI synthesis.

## What Happens When a User Starts a Chapter

1. **Frontend** (`InteractiveLearnPage.tsx`) sends initial prompt:
   ```
   Please explain the chapter "${chapter}" in a way suitable for a Grade ${user?.grade} student. Start with the basics and build up. Use examples from the textbook if possible.
   ```

2. **RAG Service** retrieves relevant textbook chunks from vector store

3. **LLM Service** attempts to synthesize chunks into coherent explanation:
   - Tries to call Gemini API
   - If rate limited → Falls back to raw textbook chunks
   - Returns unprocessed content to user

## Solutions

### Immediate (Applied)
✅ **Improved fallback formatting** - Better cleanup of raw textbook content:
- Removes "From [chapter]:" prefixes
- Cleans up special characters
- Formats as readable paragraphs with bullet points
- Adds note that this is simplified view

✅ **Early detection** - Check if all keys are rate-limited before attempting API call

### Short-term
1. **Add more API keys** to the rotation in `src/services/api_key_manager.py`
2. **Increase rate limit handling** - Better error messages to users
3. **Cache responses** - Store common chapter introductions to reduce API calls

### Long-term
1. **Use a paid API tier** with higher rate limits
2. **Implement response caching** at the chapter level
3. **Add alternative LLM providers** (OpenAI, Anthropic) as fallbacks
4. **Pre-generate chapter introductions** during ingestion

## Files Modified
- `src/services/llm_service.py` - Improved fallback formatting and early rate limit detection

## Testing After API Reset
Once API keys reset tomorrow (Jan 21 at 1:28 PM), test:
1. Start a new chapter
2. Verify you get a coherent, synthesized explanation
3. Check that it follows the format:
   ```
   **[Section Title]**
   [Detailed explanation with examples]
   
   • Key point 1
   • Key point 2
   • Key point 3
   ```

## Adding More API Keys
To add more Gemini API keys:

1. Get new keys from: https://makersuite.google.com/app/apikey
2. Add to `src/services/api_key_manager.py`:
   ```python
   self.api_keys = [
       "AIzaSyAz4jwDFwxrVCmU4SVOAMIRLrxtF2oFvQA",  # Original
       "AIzaSyCulZGm1P382VhSACxJs94qrRxIZXyZj3c",  # Key 1
       "AIzaSyDGKMTlJRpdV1zyfFe-JF87oP7BXQ9nqaQ",  # Key 2
       "YOUR_NEW_KEY_HERE",  # Key 3
       "YOUR_NEW_KEY_HERE",  # Key 4
   ]
   ```
3. Restart the backend server

## Monitoring API Usage
Check API key status via endpoint:
```
GET http://localhost:8080/chat/api-status
```

Returns:
```json
{
  "current_key_index": 0,
  "keys": [
    {
      "index": 0,
      "usage_count": 1,
      "is_current": true,
      "is_available": false,
      "reset_time": "2026-01-21T13:28:32.102604"
    },
    ...
  ]
}
```
