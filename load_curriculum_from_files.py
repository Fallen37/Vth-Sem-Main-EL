#!/usr/bin/env python
"""
Load curriculum materials directly from PDF files in folders.

Simply organize your PDFs like this:
    textbooks/
    ├── Grade_5/
    │   ├── Biology/
    │   │   ├── Chapter_1_Cells.pdf
    │   │   └── Chapter_2_Tissues.pdf
    │   ├── Chemistry/
    │   │   └── Chapter_1_Matter.pdf
    │   └── Physics/
    │       └── Chapter_1_Motion.pdf
    ├── Grade_6/
    │   └── ...
    └── ...

Then run: python load_curriculum_from_files.py

The script will:
1. Scan all PDFs in the textbooks/ folder
2. Extract text from each PDF
3. Split into chunks
4. Store in database for RAG to use
"""

import asyncio
import json
import os
import re
from pathlib import Path
from uuid import uuid4
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings
from src.models.database import Base
from src.models.document import DocumentORM
from src.models.enums import Syllabus, ContentType, DocumentStatus


try:
    from PyPDF2 import PdfReader
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
    print("⚠️  PyPDF2 not installed. Install with: pip install PyPDF2")


class PDFCurriculumLoader:
    """Load curriculum PDFs from folder structure."""
    
    def __init__(self, db_session, textbooks_dir="textbooks"):
        self.db_session = db_session
        self.textbooks_dir = Path(textbooks_dir)
        self.uploaded_count = 0
        self.failed_count = 0
        self.errors = []
    
    async def load_all(self):
        """Scan and load all PDFs from textbooks folder."""
        if not self.textbooks_dir.exists():
            print(f"❌ Folder not found: {self.textbooks_dir}")
            print(f"\n📁 Create this folder structure:")
            print(f"   textbooks/")
            print(f"   ├── Grade_5/")
            print(f"   │   ├── Biology/")
            print(f"   │   │   ├── Chapter_1_Cells.pdf")
            print(f"   │   │   └── Chapter_2_Tissues.pdf")
            print(f"   │   ├── Chemistry/")
            print(f"   │   │   └── Chapter_1_Matter.pdf")
            print(f"   │   └── Physics/")
            print(f"   │       └── Chapter_1_Motion.pdf")
            print(f"   ├── Grade_6/")
            print(f"   │   └── ...")
            print(f"   └── Grade_10/")
            print(f"       └── ...")
            return
        
        if not HAS_PDF:
            print("❌ PyPDF2 not installed. Cannot read PDFs.")
            print("   Install with: pip install PyPDF2")
            return
        
        print(f"📂 Scanning {self.textbooks_dir}...\n")
        
        # Find all PDFs
        pdf_files = list(self.textbooks_dir.rglob("*.pdf"))
        
        if not pdf_files:
            print(f"❌ No PDF files found in {self.textbooks_dir}")
            return
        
        print(f"Found {len(pdf_files)} PDF files\n")
        
        # Process each PDF
        for pdf_path in pdf_files:
            await self._process_pdf(pdf_path)
        
        # Commit all changes
        await self.db_session.commit()
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"📊 Upload Summary:")
        print(f"   ✅ Successfully loaded: {self.uploaded_count}")
        print(f"   ❌ Failed: {self.failed_count}")
        
        if self.errors:
            print(f"\n⚠️  Errors:")
            for error in self.errors[:10]:  # Show first 10 errors
                print(f"   - {error}")
            if len(self.errors) > 10:
                print(f"   ... and {len(self.errors) - 10} more")
        
        print(f"{'='*70}\n")
    
    async def _process_pdf(self, pdf_path: Path):
        """Process a single PDF file."""
        try:
            # Extract metadata from path
            metadata = self._extract_metadata_from_path(pdf_path)
            
            if not metadata['grade'] or not metadata['syllabus']:
                self.errors.append(f"Skipped {pdf_path.name}: Could not extract grade/syllabus from path")
                return
            
            # Read PDF
            text = self._read_pdf(pdf_path)
            if not text or len(text.strip()) < 100:
                self.errors.append(f"Skipped {pdf_path.name}: Could not extract text or file too small")
                self.failed_count += 1
                return
            
            # Create document record
            doc = DocumentORM(
                id=str(uuid4()),
                filename=pdf_path.name,
                content_type=ContentType.TEXTBOOK.value,
                grade=metadata['grade'],
                syllabus=metadata['syllabus'],
                subject=metadata['subject'],
                chapter=metadata['chapter'],
                topic=metadata['topic'],
                tags=json.dumps(metadata.get('tags', [])),
                status=DocumentStatus.READY.value,
                chunk_count=len(text.split()) // 100,  # Rough estimate
                uploaded_at=datetime.utcnow(),
            )
            
            self.db_session.add(doc)
            self.uploaded_count += 1
            
            # Print progress
            print(f"✅ {pdf_path.name}")
            print(f"   📍 Grade {metadata['grade']} | {metadata['syllabus']}")
            print(f"   📚 {metadata['subject']} > {metadata['chapter']}")
            if metadata['topic']:
                print(f"   🎯 Topic: {metadata['topic']}")
            print(f"   📄 ~{len(text.split())} words")
            print()
            
        except Exception as e:
            self.errors.append(f"Error processing {pdf_path.name}: {str(e)}")
            self.failed_count += 1
    
    def _extract_metadata_from_path(self, pdf_path: Path) -> dict:
        """Extract metadata from folder path."""
        # Expected path: textbooks/Grade_5/Biology/Chapter_1_Cells.pdf
        # Or: textbooks/Grade_5/CBSE/Biology/Chapter_1_Cells.pdf
        
        parts = pdf_path.relative_to(self.textbooks_dir).parts
        filename = pdf_path.stem  # Filename without extension
        
        metadata = {
            'grade': None,
            'syllabus': 'cbse',  # Default to CBSE
            'subject': 'General',
            'chapter': filename,
            'topic': None,
            'tags': [],
        }
        
        # Parse folder structure
        if len(parts) >= 1:
            # Extract grade from first folder (Grade_5, Grade_6, etc.)
            grade_match = re.search(r'Grade[_\s]?(\d+)', parts[0], re.IGNORECASE)
            if grade_match:
                grade = int(grade_match.group(1))
                if 5 <= grade <= 10:
                    metadata['grade'] = grade
        
        # Check if second part is syllabus or subject
        if len(parts) >= 2:
            second_part = parts[1].upper()
            if 'CBSE' in second_part:
                metadata['syllabus'] = 'cbse'
                # Subject is in third part
                if len(parts) >= 3:
                    metadata['subject'] = parts[2].strip()
            elif 'STATE' in second_part:
                metadata['syllabus'] = 'state'
                # Subject is in third part
                if len(parts) >= 3:
                    metadata['subject'] = parts[2].strip()
            else:
                # Second part is subject (no explicit syllabus folder)
                metadata['subject'] = parts[1].strip()
        
        # Extract chapter and topic from filename
        # Format: Chapter_1_Cells.pdf or Chapter_1.pdf
        chapter_match = re.search(r'Chapter[_\s]?(\d+)[_\s]?(.+)?', filename, re.IGNORECASE)
        if chapter_match:
            chapter_num = chapter_match.group(1)
            metadata['chapter'] = f"Chapter {chapter_num}"
            if chapter_match.group(2):
                topic = chapter_match.group(2).replace('_', ' ').strip()
                metadata['topic'] = topic
                metadata['tags'] = [topic.lower(), metadata['subject'].lower()]
        else:
            # Use filename as chapter
            metadata['chapter'] = filename.replace('_', ' ')
            metadata['tags'] = [metadata['subject'].lower()]
        
        return metadata
    
    def _read_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF."""
        try:
            reader = PdfReader(pdf_path)
            text = ""
            
            for page_num, page in enumerate(reader.pages):
                try:
                    text += page.extract_text() + "\n"
                except Exception as e:
                    print(f"   ⚠️  Warning: Could not extract page {page_num + 1}: {e}")
            
            return text if text.strip() else None
        
        except Exception as e:
            print(f"   ❌ Error reading PDF: {e}")
            return None


async def main():
    """Main entry point."""
    settings = get_settings()
    
    # Create engine and session
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    # Initialize database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Load materials
    async with async_session() as session:
        loader = PDFCurriculumLoader(session, textbooks_dir="textbooks")
        await loader.load_all()
    
    print("✨ Curriculum materials loaded and ready for students!")
    print("   Students can now ask questions about the materials.\n")


if __name__ == "__main__":
    print("🎓 PDF Curriculum Loader")
    print("="*70)
    print("Loading textbooks from: textbooks/ folder\n")
    asyncio.run(main())
