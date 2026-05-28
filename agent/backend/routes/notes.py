"""Routes for note-based review generation"""
import logging
import os
import glob as glob_mod
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.database import crud
from backend.utils.structured_review_generator import structured_review_generator

logger = logging.getLogger(__name__)

router = APIRouter()

# Encodings to try when reading markdown files, in priority order
_ENCODINGS = ("utf-8", "gbk", "gb2312", "gb18030", "latin-1")


def _read_markdown_file(path: str) -> str:
    """Read a markdown file, trying multiple encodings."""
    for enc in _ENCODINGS:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            if content.strip():
                if enc != "utf-8":
                    logger.info(f"Read {Path(path).name} as {enc}")
                return content
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Unable to decode file: {path}")


class NoteReviewRequest(BaseModel):
    mode: str  # "file" or "directory"
    path: str  # absolute path to a .md file or a directory containing .md files
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class NoteReviewResult(BaseModel):
    note_id: str
    session_id: str
    status: str
    total_groups: int
    total_knowledge_cards: int
    total_quiz_questions: int


@router.post("/notes/review", response_model=list[NoteReviewResult])
async def generate_note_review(request: NoteReviewRequest, db: Session = Depends(get_db)):
    """Generate review content from markdown learning notes.

    mode="file": path is a single .md file
    mode="directory": path is a directory, all .md files inside are processed
    """
    if request.mode not in ("file", "directory"):
        raise HTTPException(status_code=400, detail="mode must be 'file' or 'directory'")

    # Collect .md files
    md_files: list[str] = []
    if request.mode == "file":
        p = Path(request.path)
        if not p.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.path}")
        if p.suffix.lower() != ".md":
            raise HTTPException(status_code=400, detail="Only .md files are supported")
        md_files.append(str(p))
    else:
        dir_path = Path(request.path)
        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Directory not found: {request.path}")
        md_files = sorted(str(f) for f in dir_path.glob("*.md"))
        if not md_files:
            raise HTTPException(status_code=404, detail=f"No .md files found in {request.path}")

    results = []
    for md_path in md_files:
        try:
            # Read markdown content with encoding auto-detection
            content = _read_markdown_file(md_path)

            if not content.strip():
                logger.warning(f"Empty file skipped: {md_path}")
                continue

            # Generate note_id from filename without extension
            filename = Path(md_path).stem
            session_id = f"note:{filename}"

            logger.info(f"Generating review for note: {filename} ({len(content)} chars)")

            # Generate review via LLM
            review_data = structured_review_generator.generate_note_review(
                markdown_content=content,
                note_id=session_id,
                api_key=request.api_key,
                base_url=request.base_url,
                model=request.model,
            )

            review_groups = review_data.get("review_groups", [])
            aggregated_summary = review_data.get("aggregated_summary", "")

            # Save to database
            from datetime import datetime, timedelta
            crud.create_or_update_review_data(
                db=db,
                session_id=session_id,
                review_groups=review_groups,
                aggregated_summary=aggregated_summary,
                next_review_date=datetime.utcnow() + timedelta(days=1),
                generation_config={
                    "message_count": 0,
                    "generation_type": "note",
                    "note_path": md_path,
                    "note_content_length": len(content),
                },
                generation_status="completed",
            )

            total_cards = sum(len(g.get("knowledge_cards", [])) for g in review_groups)
            total_questions = sum(len(g.get("quiz_questions", [])) for g in review_groups)

            results.append(NoteReviewResult(
                note_id=filename,
                session_id=session_id,
                status="completed",
                total_groups=len(review_groups),
                total_knowledge_cards=total_cards,
                total_quiz_questions=total_questions,
            ))

            logger.info(f"Note review saved: {filename} -> {len(review_groups)} groups")

        except Exception as e:
            logger.error(f"Failed to process {md_path}: {e}")
            results.append(NoteReviewResult(
                note_id=Path(md_path).stem,
                session_id=f"note:{Path(md_path).stem}",
                status="failed",
                total_groups=0,
                total_knowledge_cards=0,
                total_quiz_questions=0,
            ))

    return results
