"""Dynamic Text Analyzer - Filters AI responses into educational and meta content."""

import re
from datetime import datetime
from typing import Optional, Dict, Tuple
from uuid import UUID
import json


class TextAnalyzer:
    """Analyzes and filters AI responses into educational and conversational content."""
    
    # First-person indicators that mark conversational/meta text
    META_INDICATORS = [
        r'\bI\s+(?:think|believe|understand|realize|see|notice|found|discovered)',
        r'\bLet\s+me\s+(?:explain|break|show|help|clarify)',
        r'\bI\s+(?:will|can|should|would|could|must)',
        r'\bI\s+(?:am|\'m|have|\'ve|had)',
        r'\bI\s+(?:don\'t|don\'t|didn\'t|won\'t|can\'t|shouldn\'t)',
        r'\bAs\s+(?:I|you)\s+(?:can|may|might)',
        r'\bYou\s+(?:might|may|could|should|will)',
        r'\bI\s+apologize',
        r'\bI\s+understand\s+that\s+you',
        r'\bSorry',
        r'\bThank\s+you',
        r'\bGreat\s+(?:job|work|question)',
        r'\bWonderful',
        r'\bExcellent',
        r'\bPerfect',
        r'\bNice',
        r'\bCool',
        r'\bAwesome',
        r'\bHello',
        r'\bHi\s+there',
        r'\bWelcome',
        r'\bReady\s+to',
        r'\bLet\'s\s+(?:start|begin|explore)',
        r'\bNow\s+(?:let\'s|let\'s)',
        r'\bSo\s+(?:here\'s|here\'s)',
        r'\bBased\s+on\s+(?:the\s+)?textbook',
        r'\bFrom\s+(?:the\s+)?textbook',
        r'\bAccording\s+to\s+(?:the\s+)?textbook',
        r'\bThe\s+textbook\s+(?:states|says|mentions|explains)',
        r'\bYour\s+textbook',
        r'\bWould\s+you\s+like',
        r'\bDo\s+you\s+(?:want|need|have)',
        r'\bCan\s+I\s+(?:help|assist)',
        r'\bIs\s+there\s+anything',
        r'\bLet\s+me\s+know',
        r'\bFeel\s+free',
        r'\bDon\'t\s+hesitate',
    ]
    
    # Compile regex patterns for performance
    META_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in META_INDICATORS]
    
    # Educational markers that should stay in content
    EDUCATIONAL_MARKERS = [
        r'\b(?:definition|concept|principle|law|theory|formula|equation)',
        r'\b(?:example|instance|case|illustration)',
        r'\b(?:therefore|thus|hence|consequently|as\s+a\s+result)',
        r'\b(?:because|since|due\s+to|caused\s+by)',
        r'\b(?:however|but|although|despite|whereas)',
        r'\b(?:furthermore|moreover|additionally|also)',
        r'\b(?:first|second|third|finally|next|then)',
        r'\b(?:in\s+conclusion|to\s+summarize|in\s+summary)',
        r'\*\*.*?\*\*',  # Bold text (section titles)
        r'•\s+',  # Bullet points
        r'\d+\.',  # Numbered lists
    ]
    
    EDUCATIONAL_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in EDUCATIONAL_MARKERS]
    
    def __init__(self):
        """Initialize the text analyzer."""
        self.nlp_available = False
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            self.nlp_available = True
            print("✓ spaCy NLP model loaded for advanced text analysis")
        except Exception as e:
            print(f"⚠ spaCy not available, using rule-based filtering only: {e}")
            self.nlp = None
    
    def analyze(
        self,
        response_text: str,
        session_id: Optional[UUID] = None,
        topic: Optional[str] = None,
    ) -> Dict:
        """
        Analyze AI response and separate meta and educational content.
        
        Args:
            response_text: Raw AI response text
            session_id: Session ID for tracking
            topic: Topic being discussed
        
        Returns:
            Dict with meta_text, content_text, and metadata
        """
        if not response_text or not response_text.strip():
            return {
                "meta_text": "",
                "content_text": "",
                "timestamp": datetime.now().isoformat(),
                "session_id": str(session_id) if session_id else None,
                "topic": topic,
                "analysis_method": "empty",
            }
        
        # Stage 1: Rule-based filtering
        meta_text, content_text = self._stage1_rule_based_filter(response_text)
        
        # Stage 2: NLP-based refinement (if available)
        if self.nlp_available:
            meta_text, content_text = self._stage2_nlp_refinement(meta_text, content_text)
        
        return {
            "meta_text": meta_text.strip(),
            "content_text": content_text.strip(),
            "timestamp": datetime.now().isoformat(),
            "session_id": str(session_id) if session_id else None,
            "topic": topic,
            "analysis_method": "nlp" if self.nlp_available else "rule-based",
            "meta_sentence_count": len([s for s in meta_text.split('.') if s.strip()]),
            "content_sentence_count": len([s for s in content_text.split('.') if s.strip()]),
        }
    
    def _stage1_rule_based_filter(self, text: str) -> Tuple[str, str]:
        """
        Stage 1: Rule-based filtering using regex patterns.
        
        Returns:
            Tuple of (meta_text, content_text)
        """
        sentences = self._split_sentences(text)
        meta_sentences = []
        content_sentences = []
        
        for sentence in sentences:
            if self._is_meta_sentence(sentence):
                meta_sentences.append(sentence)
            else:
                content_sentences.append(sentence)
        
        meta_text = " ".join(meta_sentences)
        content_text = " ".join(content_sentences)
        
        return meta_text, content_text
    
    def _stage2_nlp_refinement(self, meta_text: str, content_text: str) -> Tuple[str, str]:
        """
        Stage 2: NLP-based refinement for improved accuracy.
        
        Uses spaCy to analyze sentence structure and tone.
        """
        if not self.nlp:
            return meta_text, content_text
        
        try:
            # Analyze content text for any missed meta sentences
            doc = self.nlp(content_text)
            refined_meta = []
            refined_content = []
            
            for sent in doc.sents:
                sent_text = sent.text.strip()
                if not sent_text:
                    continue
                
                # Check for first-person pronouns and conversational patterns
                has_first_person = any(token.text.lower() in ['i', 'me', 'my', 'mine'] for token in sent)
                has_question = sent_text.endswith('?')
                has_imperative = any(token.pos_ == 'VERB' and token.dep_ == 'ROOT' for token in sent if token.idx == 0)
                
                # Conversational patterns
                is_conversational = (
                    has_first_person or
                    has_question or
                    any(self._is_meta_sentence(sent_text) for _ in [1])
                )
                
                if is_conversational:
                    refined_meta.append(sent_text)
                else:
                    refined_content.append(sent_text)
            
            refined_meta_text = meta_text + " " + " ".join(refined_meta)
            refined_content_text = " ".join(refined_content)
            
            return refined_meta_text.strip(), refined_content_text.strip()
        except Exception as e:
            print(f"Error in NLP refinement: {e}")
            return meta_text, content_text
    
    def _is_meta_sentence(self, sentence: str) -> bool:
        """Check if a sentence is meta/conversational."""
        if not sentence or len(sentence.strip()) < 3:
            return False
        
        # Check against meta patterns
        for pattern in self.META_PATTERNS:
            if pattern.search(sentence):
                return True
        
        # Check if it's purely educational
        has_educational = any(pattern.search(sentence) for pattern in self.EDUCATIONAL_PATTERNS)
        if has_educational and not any(pattern.search(sentence) for pattern in self.META_PATTERNS):
            return False
        
        return False
    
    def _split_sentences(self, text: str) -> list:
        """Split text into sentences."""
        # Handle common sentence endings
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        # Also split on newlines with content
        sentences = [s for sent in sentences for s in sent.split('\n') if s.strip()]
        return [s.strip() for s in sentences if s.strip()]


# Global instance
_text_analyzer: Optional[TextAnalyzer] = None


def get_text_analyzer() -> TextAnalyzer:
    """Get or create the global text analyzer."""
    global _text_analyzer
    if _text_analyzer is None:
        _text_analyzer = TextAnalyzer()
    return _text_analyzer
