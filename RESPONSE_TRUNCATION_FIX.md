# Response Truncation Fix

## Issue
AI responses were being cut off mid-sentence, resulting in incomplete explanations for students.

## Root Cause
The token limits for AI model responses were set too low:

1. **OpenAI API (rag_engine.py)**: `max_tokens=1000` 
2. **Google Gemini API (llm_service.py)**: No explicit limit set, using defaults

These limits were causing responses to be truncated before the AI could complete its explanation.

## Solution
Increased token limits to allow complete responses:

### 1. OpenAI API (`src/services/rag_engine.py`)
- Changed `max_tokens` from **1000** to **2048**
- This doubles the available space for responses

### 2. Google Gemini API (`src/services/llm_service.py`)
- Added explicit `generation_config` with `max_output_tokens: 2048`
- Applied to all main response generation calls
- Used `max_output_tokens: 512` for follow-up suggestions (shorter responses)

## Files Modified
- `src/services/rag_engine.py` - Line ~357
- `src/services/llm_service.py` - Lines ~96, ~114, ~208

## Testing
After these changes, AI responses should:
- Complete full sentences and paragraphs
- Provide comprehensive explanations without cutting off
- Still respect the instruction to explain ONE concept at a time

## Notes
- 2048 tokens is approximately 1500-2000 words, which is sufficient for a complete educational explanation
- The system prompt still instructs the AI to keep responses focused (2-3 paragraphs max)
- This balances completeness with the need for digestible, focused explanations for autistic students
