#!/usr/bin/env python
"""Ingest documents into the vector store."""

import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from config.settings import get_settings
from src.models.database import Base
from src.models.document import DocumentORM
from src.services.rag_service import RAGService


async def ingest_all_documents():
    """Ingest all documents from the database into the vector store."""
    
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get all documents
        result = await session.execute(select(DocumentORM))
        documents = result.scalars().all()
        
        print(f"Found {len(documents)} documents to ingest\n")
        
        # Prepare documents for ingestion
        docs_to_ingest = []
        for doc in documents:
            docs_to_ingest.append({
                'filename': doc.filename,
                'metadata': {
                    'grade': doc.grade,
                    'syllabus': doc.syllabus,
                    'subject': doc.subject,
                    'chapter': doc.chapter,
                    'topic': doc.topic,
                }
            })
        
        # Ingest into vector store
        rag_service = RAGService(db_session=session)
        
        print("Ingesting documents into vector store...")
        print("This may take a few minutes...\n")
        
        stats = await rag_service.ingest_documents(docs_to_ingest)
        
        print(f"\n{'='*70}")
        print(f"✅ Ingestion Complete!")
        print(f"   Documents: {stats['total_documents']}")
        print(f"   Chunks: {stats['total_chunks']}")
        print(f"{'='*70}\n")


if __name__ == '__main__':
    asyncio.run(ingest_all_documents())
