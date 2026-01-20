# Dynamic Response Analyzer

## Overview

The Dynamic Response Analyzer is a middleware layer that automatically filters AI API responses to separate educational content from conversational meta-text. This ensures students see only the relevant learning material while meta-text is stored for behavioral analysis.

## Architecture

### Components

1. **TextAnalyzer** (`src/services/text_analyzer.py`)
   - Core analysis engine
   - Two-stage filtering system
   - Rule-based and NLP-based analysis

2. **ResponseAnalyzerService** (`src/services/response_analyzer_service.py`)
   - Service layer for analysis and storage
   - Database integration
   - Analytics generation

3. **AnalyzedResponseORM** (`src/models/analyzed_response.py`)
   - Database model for storing analysis results
   - Tracks meta and content text separately

4. **Chat API Integration** (`src/api/chat.py`)
   - Middleware integration in `/chat/message` endpoint
   - Analysis endpoints for viewing results

## How It Works

### Stage 1: Rule-Based Filtering

The analyzer uses regex patterns to identify meta-text indicators:

**Meta Indicators Detected:**
- First-person pronouns: "I think", "I understand", "I will"
- Conversational framing: "Let me explain", "Let me show"
- Empathetic responses: "I apologize", "Sorry", "Thank you"
- Engagement phrases: "Great job", "Wonderful", "Perfect"
- Textbook references: "Based on the textbook", "Your textbook"
- Questions: "Would you like", "Do you want", "Can I help"
- Directives: "Let me know", "Feel free", "Don't hesitate"

**Educational Markers Preserved:**
- Definitions and concepts
- Examples and illustrations
- Logical connectors: "therefore", "because", "however"
- Structural markers: "first", "second", "finally"
- Formatted text: **bold**, bullet points, numbered lists

### Stage 2: NLP Refinement (Optional)

When spaCy is available, the analyzer performs:
- Sentence structure analysis
- Tone detection
- First-person pronoun identification
- Question and imperative detection
- Conversational pattern recognition

## Data Flow

```
AI Response
    ↓
TextAnalyzer.analyze()
    ├─ Stage 1: Rule-based filtering
    │   ├─ Split into sentences
    │   ├─ Check against meta patterns
    │   └─ Classify as meta or content
    │
    └─ Stage 2: NLP refinement (if available)
        ├─ Parse with spaCy
        ├─ Analyze sentence structure
        └─ Refine classification
    ↓
ResponseAnalyzerService.analyze_and_store()
    ├─ Store in database
    └─ Return analysis results
    ↓
Chat API
    ├─ Send content_text to frontend
    └─ Store meta_text for analytics
```

## Output Format

The analyzer returns a JSON object:

```json
{
  "meta_text": "Hello! I'm here to help you understand this. Let me explain further. Would you like me to continue?",
  "content_text": "**Section 1: What is Force?** A force is a push or pull. For example, when you pull a rope, you apply force.",
  "timestamp": "2026-01-19T20:50:00.000000",
  "session_id": "abc123...",
  "topic": "Force and Pressure",
  "analysis_method": "rule-based",
  "meta_sentence_count": 4,
  "content_sentence_count": 3
}
```

## API Endpoints

### 1. Send Message (with automatic analysis)

```bash
POST /chat/message
Authorization: Bearer {user_id}
Content-Type: application/json

{
  "session_id": "abc123...",
  "content": "Please explain force and pressure",
  "input_type": "TEXT"
}
```

**Response:**
- Only `content_text` is sent to frontend
- Meta and content are stored in database

### 2. Get Analysis History

```bash
GET /chat/analysis-history/{session_id}
Authorization: Bearer {user_id}
```

**Response:**
```json
{
  "session_id": "abc123...",
  "analysis_count": 5,
  "analyses": [
    {
      "id": "analysis_1",
      "meta_text": "...",
      "content_text": "...",
      "analysis_method": "rule-based",
      "meta_sentence_count": 3,
      "content_sentence_count": 5,
      "created_at": "2026-01-19T20:50:00"
    }
  ]
}
```

### 3. Get User Analytics

```bash
GET /chat/analytics
Authorization: Bearer {user_id}
```

**Response:**
```json
{
  "user_id": "user_123",
  "analytics": {
    "total_responses": 42,
    "analysis_method_distribution": {
      "rule-based": 42,
      "nlp": 0
    },
    "average_meta_sentences": 3.2,
    "average_content_sentences": 5.8
  }
}
```

## Database Schema

### analyzed_responses Table

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR(36) | Primary key |
| session_id | VARCHAR(36) | Session reference |
| user_id | VARCHAR(36) | User reference |
| topic | VARCHAR(255) | Topic being discussed |
| original_response | TEXT | Raw AI response |
| meta_text | TEXT | Conversational content |
| content_text | TEXT | Educational content |
| analysis_method | VARCHAR(50) | 'rule-based' or 'nlp' |
| meta_sentence_count | INTEGER | Number of meta sentences |
| content_sentence_count | INTEGER | Number of content sentences |
| created_at | DATETIME | Response timestamp |
| analyzed_at | DATETIME | Analysis timestamp |

## Configuration

### Adding Meta Indicators

Edit `src/services/text_analyzer.py` and add patterns to `META_INDICATORS`:

```python
META_INDICATORS = [
    r'\bI\s+(?:think|believe|understand)',
    r'\bLet\s+me\s+(?:explain|show)',
    # Add your patterns here
]
```

### Enabling NLP Analysis

Install spaCy:
```bash
pip install spacy
python -m spacy download en_core_web_sm
```

The analyzer will automatically detect and use spaCy if available.

## Performance

- **Rule-based analysis**: ~1-2ms per response
- **NLP analysis**: ~10-20ms per response
- **Database storage**: ~5-10ms per response
- **Total overhead**: <50ms per request

## Examples

### Example 1: Simple Explanation

**Raw Response:**
```
Hello! I'm here to help you understand force. Let me explain this concept.

**What is Force?**

A force is a push or pull that can change the motion of an object. For example, when you push a ball, you apply force to it.

Would you like me to explain more?
```

**After Analysis:**

Meta Text:
```
Hello! I'm here to help you understand force. Let me explain this concept. Would you like me to explain more?
```

Content Text (Sent to Frontend):
```
**What is Force?**

A force is a push or pull that can change the motion of an object. For example, when you push a ball, you apply force to it.
```

### Example 2: Complex Explanation

**Raw Response:**
```
I understand you want to learn about pressure. Let me break this down for you.

**Pressure Definition**

Pressure is force per unit area. Your textbook states: "pressure = force / area"

For example, a sharp knife cuts better than a dull one because it applies force over a smaller area, creating higher pressure.

I hope this helps! Let me know if you need clarification.
```

**After Analysis:**

Meta Text:
```
I understand you want to learn about pressure. Let me break this down for you. I hope this helps! Let me know if you need clarification.
```

Content Text (Sent to Frontend):
```
**Pressure Definition**

Pressure is force per unit area. Your textbook states: "pressure = force / area"

For example, a sharp knife cuts better than a dull one because it applies force over a smaller area, creating higher pressure.
```

## Analytics Use Cases

### 1. Conversational Patterns
Track how much meta-text the AI generates:
- High meta-text: AI is being very conversational
- Low meta-text: AI is being direct and educational

### 2. Student Engagement
Analyze meta-text to understand:
- How often AI uses empathetic language
- How often AI asks clarifying questions
- How often AI provides encouragement

### 3. Content Quality
Analyze content-text to understand:
- Average explanation length
- Complexity of explanations
- Use of examples and illustrations

### 4. Behavioral Analysis
Store meta-text for later analysis:
- AI personality traits
- Engagement strategies
- Effectiveness of conversational approaches

## Troubleshooting

### All text classified as meta
- Check regex patterns for false positives
- Verify educational markers are included
- Consider enabling NLP analysis

### spaCy not loading
- Install: `pip install spacy`
- Download model: `python -m spacy download en_core_web_sm`
- Check Python version compatibility

### Database storage failing
- Verify `analyzed_responses` table exists
- Check database permissions
- Review error logs

## Future Enhancements

- [ ] Machine learning classifier for improved accuracy
- [ ] Sentiment analysis on meta-text
- [ ] Automatic tone adjustment based on student feedback
- [ ] Multi-language support
- [ ] Real-time analytics dashboard
- [ ] A/B testing different conversational styles
- [ ] Integration with student engagement metrics
