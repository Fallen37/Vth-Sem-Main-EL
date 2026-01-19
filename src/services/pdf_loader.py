"""Fast PDF text extraction and chunking."""

from pathlib import Path
from typing import Optional
import re

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class PDFLoader:
    """Extract text from PDFs efficiently."""
    
    def __init__(self, textbooks_dir: str = "textbooks"):
        self.textbooks_dir = Path(textbooks_dir)
        self._cache = {}  # Simple cache for extracted text
    
    def extract_text(self, filename: str) -> Optional[str]:
        """Extract text from a PDF file."""
        if filename in self._cache:
            return self._cache[filename]
        
        if not HAS_PDFPLUMBER:
            return None
        
        # Find the PDF file
        pdf_files = list(self.textbooks_dir.rglob(filename))
        if not pdf_files:
            return None
        
        pdf_path = pdf_files[0]
        
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
                    text += "\n"
            
            # Cache it
            self._cache[filename] = text
            return text
        except Exception as e:
            print(f"Error extracting text from {filename}: {e}")
            return None
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
        """Split text into overlapping chunks."""
        if not text:
            return []
        
        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += " " + sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
