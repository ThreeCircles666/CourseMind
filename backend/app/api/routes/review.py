"""Owner-scoped persistent review artifacts, progress and original-page images."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.api.routes.documents import get_upload_root
from app.core.config import settings
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.review import ReviewRequest, ReviewStatePatch
from app.services.review import STATE_LOCK, generate_review, read_json, write_json
from app.services.review_media import render_page

router = APIRouter(tags=["courseware-review"])
CREATE_LOCK = threading.Lock()


def artifact_path(root: Path, user_id: int, review_id: UUID) -> Path:
    return root / ".reviews" / str(user_id) / str(review_id) / "review.json"


def owned_documents(db: Session, user_id: int, ids: list[UUID]) -> list[Document]:
    found = db.execute(select(Document).where(Document.user_id == user_id, Document.id.in_(ids))).scalars().all()
    mapping = {d.id: d for d in found}
    if any(i not in mapping for i in ids):
        raise HTTPException(404, "Document not found")
    return [mapping[i] for i in ids]


def source_path(root: Path, document: Document) -> Path:
    path = root / str(document.id) / document.safe_name
    if not path.resolve().is_relative_to((root / str(document.id)).resolve()):
        raise HTTPException(404, "Document file not found")
    if not path.is_file():
        raise HTTPException(404, "Document file not found")
    return path


def load_owned(root: Path, user_id: int, review_id: UUID, db: Session) -> tuple[Path, dict, list[Document]]:
    path = artifact_path(root, user_id, review_id)
    if not path.is_file():
        raise HTTPException(404, "Review not found")
    state = read_json(path)
    documents = owned_documents(db, user_id, [UUID(i) for i in state["document_ids"]])
    return path, state, documents


@router.post("/reviews", status_code=202)
async def create_review(request: ReviewRequest, background_tasks: BackgroundTasks,
                        user: User = Depends(get_current_user), db: Session = Depends(get_db),
                        root: Path = Depends(get_upload_root)) -> dict:
    ids = list(dict.fromkeys(request.document_ids))
    documents = owned_documents(db, user.id, ids)
    sources = [{"id": str(d.id), "name": d.original_name, "path": str(source_path(root, d))} for d in documents]
    if not settings.is_dashscope_configured():
        raise HTTPException(503, "Configure DASHSCOPE_API_KEY before generating a courseware review")
    if request.use_vision and not settings.review_vision_model:
        raise HTTPException(503, "Configure REVIEW_VISION_MODEL before enabling visual reading")
    review_id = uuid4()
    state = {"id": str(review_id), "document_ids": [str(i) for i in ids], "language": request.response_language,
             "use_vision": request.use_vision, "status": "queued", "created_at": datetime.now(timezone.utc).isoformat(),
             "completed_pages": 0, "documents": [], "sections": [], "duplicates": [], "reviewed_sections": [], "error": None}
    # Limit pending work before starting any paid model calls. Artifacts remain readable after restarts.
    with CREATE_LOCK:
        directory = root / ".reviews" / str(user.id)
        active = [read_json(p) for p in directory.glob("*/review.json") if read_json(p).get("status") in {"queued", "processing"}]
        for existing in active:
            if (existing.get("document_ids") == state["document_ids"]
                    and existing.get("language") == state["language"]
                    and existing.get("use_vision") == state["use_vision"]):
                return existing  # A double click must not start the same paid work twice.
        if len(active) >= 2:
            raise HTTPException(429, "Two review jobs are already active; wait for completion or remove an interrupted record")
        path = artifact_path(root, user.id, review_id)
        write_json(path, state)
    background_tasks.add_task(generate_review, path, sources)
    return state


@router.get("/reviews")
def list_reviews(user: User = Depends(get_current_user), db: Session = Depends(get_db),
                 root: Path = Depends(get_upload_root), limit: int = Query(50, ge=1, le=100)) -> list[dict]:
    directory = root / ".reviews" / str(user.id)
    result = []
    for path in sorted(directory.glob("*/review.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        state = read_json(path)
        try:
            owned_documents(db, user.id, [UUID(i) for i in state["document_ids"]])
        except HTTPException:
            continue
        result.append({k: state[k] for k in ("id", "document_ids", "language", "status", "created_at", "completed_pages")})
        if len(result) == limit:
            break
    return result


@router.get("/reviews/{review_id}")
def get_review(review_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db),
               root: Path = Depends(get_upload_root)) -> dict:
    return load_owned(root, user.id, review_id, db)[1]


@router.patch("/reviews/{review_id}/state")
def update_state(review_id: UUID, patch: ReviewStatePatch, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db), root: Path = Depends(get_upload_root)) -> dict:
    with STATE_LOCK:
        path, state, _ = load_owned(root, user.id, review_id, db)
        if state["status"] != "ready":
            raise HTTPException(409, "Review is not ready")
        if patch.reviewed_sections is not None:
            ids = {s["id"] for s in state["sections"]}
            if not set(patch.reviewed_sections) <= ids:
                raise HTTPException(422, "Unknown section")
            state["reviewed_sections"] = list(dict.fromkeys(patch.reviewed_sections))
        if patch.erratum_id is not None or patch.decision is not None:
            candidate = next((e for s in state["sections"] for e in s["errata"] if e["id"] == patch.erratum_id), None)
            if candidate is None or patch.decision is None:
                raise HTTPException(422, "Invalid erratum decision")
            candidate["status"] = patch.decision
        write_json(path, state)
        return state


@router.delete("/reviews/{review_id}", status_code=204)
def delete_review(review_id: UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db),
                  root: Path = Depends(get_upload_root)) -> Response:
    import shutil
    with STATE_LOCK:
        path, state, _ = load_owned(root, user.id, review_id, db)
        # Background tasks cannot be cancelled safely through a filesystem flag in a multiworker setup.
        if state["status"] in {"queued", "processing"}:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(state["created_at"])).total_seconds()
            if age < 3660:
                raise HTTPException(409, "Job is active. Interrupted jobs can be removed after one hour")
        shutil.rmtree(path.parent)
    return Response(status_code=204)


@router.get("/reviews/{review_id}/documents/{document_id}/pages/{page_number}/image")
def page_image(review_id: UUID, document_id: UUID, page_number: int,
               user: User = Depends(get_current_user), db: Session = Depends(get_db),
               root: Path = Depends(get_upload_root)) -> Response:
    path, state, documents = load_owned(root, user.id, review_id, db)
    document = next((d for d in documents if d.id == document_id), None)
    page = next((p for d in state["documents"] if d["id"] == str(document_id)
                 for p in d["pages"] if p["number"] == page_number), None)
    if document is None or page is None or not page["has_image"]:
        raise HTTPException(404, "Original page image not found")
    try:
        image = render_page(source_path(root, document), path.parent / str(document_id), page_number)
    except (ValueError, RuntimeError) as error:
        raise HTTPException(422, "Original page could not be rendered") from error
    return Response(image, media_type="image/jpeg", headers={"Cache-Control": "private, no-store"})
