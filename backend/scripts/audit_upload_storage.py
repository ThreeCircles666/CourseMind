"""Read-only audit of upload storage directories.

This script reports storage state only. It does not delete or modify files.
It classifies top-level UUID directories under the configured upload root and
compares them with database records.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, text

from app.core.config import settings


@dataclass(frozen=True)
class FileEntry:
    name: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class DirectoryAudit:
    directory: str
    is_valid_uuid: bool
    file_count: int
    files: list[FileEntry]
    db_document_exists: bool
    db_sha256_exists: bool
    matches_protected_document: bool
    modified_at: str | None
    category: str


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _db_lookup(conn, document_id: str | None, sha256: str | None) -> tuple[bool, bool, bool]:
    doc_exists = False
    sha_exists = False
    protected_match = False
    if document_id:
        row = conn.execute(
            text(
                "select id::text, sha256 from documents where id = :document_id"
            ),
            {"document_id": document_id},
        ).mappings().first()
        doc_exists = row is not None
        if row is not None:
            sha_exists = row["sha256"] == sha256 if sha256 else False
    if sha256:
        row = conn.execute(
            text("select 1 from documents where sha256 = :sha256 limit 1"),
            {"sha256": sha256},
        ).first()
        sha_exists = sha_exists or row is not None
        protected = conn.execute(
            text(
                "select 1 from documents where id = 'd42818a8-089c-404f-a3a0-aca970098f11' and sha256 = :sha256 limit 1"
            ),
            {"sha256": sha256},
        ).first()
        protected_match = protected is not None
    return doc_exists, sha_exists, protected_match


def audit_upload_root(upload_root: Path) -> list[DirectoryAudit]:
    engine = create_engine(settings.database_url)
    audits: list[DirectoryAudit] = []
    with engine.connect() as conn:
        for entry in sorted(upload_root.iterdir(), key=lambda p: p.name):
            if entry.name == ".staging":
                continue
            if not entry.is_dir():
                audits.append(
                    DirectoryAudit(
                        directory=entry.name,
                        is_valid_uuid=False,
                        file_count=0,
                        files=[],
                        db_document_exists=False,
                        db_sha256_exists=False,
                        matches_protected_document=False,
                        modified_at=entry.stat().st_mtime_ns and str(entry.stat().st_mtime_ns),
                        category="UUID非法或目录结构异常",
                    )
                )
                continue
            try:
                UUID(entry.name)
                is_valid_uuid = True
            except ValueError:
                is_valid_uuid = False
            files: list[FileEntry] = []
            for file_path in sorted(p for p in entry.iterdir() if p.is_file()):
                files.append(
                    FileEntry(
                        name=file_path.name,
                        size_bytes=file_path.stat().st_size,
                        sha256=_sha256(file_path),
                    )
                )
            sha256 = files[0].sha256 if len(files) == 1 else None
            doc_exists, sha_exists, protected_match = _db_lookup(conn, entry.name if is_valid_uuid else None, sha256)
            if not is_valid_uuid:
                category = "UUID非法或目录结构异常"
            elif doc_exists and len(files) == 1 and sha_exists:
                category = "数据库记录与文件完全对应"
            elif doc_exists and not files:
                category = "数据库存在但文件缺失"
            elif files and not doc_exists:
                category = "文件存在但数据库无记录"
            elif not doc_exists and not files:
                category = "无法判断归属"
            else:
                category = "无法判断归属"
            audits.append(
                DirectoryAudit(
                    directory=entry.name,
                    is_valid_uuid=is_valid_uuid,
                    file_count=len(files),
                    files=files,
                    db_document_exists=doc_exists,
                    db_sha256_exists=sha_exists,
                    matches_protected_document=protected_match,
                    modified_at=str(entry.stat().st_mtime_ns),
                    category=category,
                )
            )
    return audits


def main() -> int:
    upload_root = settings.get_upload_root_path()
    audits = audit_upload_root(upload_root)
    print(json.dumps([asdict(item) for item in audits], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
