"""Real HTTP upload -> ingestion -> retrieval -> RAG acceptance check.

The script talks to an already-running FastAPI server. It never starts or
stops a process and it removes only the exact document UUID created here.

Usage:
    env -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
      .venv/bin/python scripts/check_document_http_pipeline.py \
      --base-url http://127.0.0.1:8000 --token "$COURSEMIND_ACCESS_TOKEN"
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from sqlalchemy import create_engine, text

from app.core.config import settings

PROTECTED_DOCUMENT_ID = UUID("d42818a8-089c-404f-a3a0-aca970098f11")
CONTENT_TEMPLATE = """# CourseMind HTTP acceptance {marker}

The CourseMind acceptance document says the internal project codename is {codename}.
The codename is used only for this exact HTTP pipeline test.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--token", default=os.getenv("COURSEMIND_ACCESS_TOKEN", ""))
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    return parser.parse_args()


def assert_no_proxy() -> None:
    proxy_names = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")
    present = [name for name in proxy_names if os.getenv(name)]
    if present:
        raise RuntimeError(f"Proxy variables must be cleared before this check: {', '.join(present)}")


def snapshot_protected(conn) -> dict:
    return dict(conn.execute(text(
        "select id::text, original_name, safe_name, mime_type, size_bytes, sha256, status, error_message, created_at, updated_at "
        "from documents where id = :id"
    ), {"id": str(PROTECTED_DOCUMENT_ID)}).mappings().one())


def main() -> int:
    args = parse_args()
    assert_no_proxy()
    marker = uuid4().hex
    username = args.username or f"cmhttp_{marker[:20]}"
    password = args.password or f"CM-http-{marker}-Pass"
    codename = f"CMHTTP-{marker[:12]}"
    content = CONTENT_TEMPLATE.format(marker=marker, codename=codename).encode()
    sha256 = hashlib.sha256(content).hexdigest()
    filename = f"coursemind_http_{marker}.md"
    duplicate_filename = f"coursemind_http_duplicate_{marker}.md"
    engine = create_engine(settings.database_url)

    print(f"rag_min_similarity_threshold={settings.rag_min_similarity:.4f}")

    session = httpx.Client(
        base_url=args.base_url.rstrip("/"),
        timeout=30.0,
    )
    document_id: UUID | None = None
    user_id: int | None = None
    before_protected: dict | None = None
    try:
        with engine.connect() as conn:
            before_protected = snapshot_protected(conn)
            print(f"protected_before={before_protected['id']}")

        if args.token:
            token = args.token
        else:
            registration = session.post(
                "/api/v1/auth/register",
                json={"username": username, "nickname": "CourseMind HTTP Acceptance", "password": password},
            )
            if registration.status_code != 201:
                raise RuntimeError(f"Acceptance user registration failed: HTTP {registration.status_code}")
            auth_payload = registration.json()
            token = auth_payload["access_token"]
            user_id = int(auth_payload["user"]["id"])
        session.headers.update({"Authorization": f"Bearer {token}"})
        upload = session.post(
            "/api/v1/documents",
            files={"file": (filename, content, "text/markdown")},
        )
        print(f"upload_status={upload.status_code}")
        if upload.status_code != 202:
            raise RuntimeError(f"Upload failed: HTTP {upload.status_code}")
        upload_payload = upload.json()
        document_id = UUID(upload_payload["id"])
        if upload_payload.get("duplicate") is not False:
            raise RuntimeError("Initial upload was unexpectedly marked duplicate")
        print(f"document_id={document_id}")
        print(f"sha256={sha256}")

        deadline = time.monotonic() + args.timeout
        final_status = None
        while time.monotonic() < deadline:
            status_response = session.get(f"/api/v1/documents/{document_id}")
            if status_response.status_code != 200:
                raise RuntimeError(f"Status query failed: HTTP {status_response.status_code}")
            final_status = status_response.json().get("status")
            print(f"status={final_status}")
            if final_status in {"succeeded", "failed"}:
                break
            time.sleep(2)
        if final_status != "succeeded":
            raise RuntimeError(f"Document did not succeed within timeout: {final_status}")

        with engine.connect() as conn:
            document = conn.execute(text(
                "select id::text, sha256, status from documents where id = :id"
            ), {"id": str(document_id)}).mappings().one()
            job = conn.execute(text(
                "select status from processing_jobs where document_id = :id order by created_at desc limit 1"
            ), {"id": str(document_id)}).mappings().one()
            chunks = conn.execute(text(
                "select chunk_index, content, start_char, end_char, embedding_dimension from document_chunks where document_id = :id order by chunk_index"
            ), {"id": str(document_id)}).mappings().all()
        if document["sha256"] != sha256 or document["status"] != "succeeded":
            raise RuntimeError("Database document verification failed")
        if job["status"] != "succeeded" or not chunks:
            raise RuntimeError("Processing job or chunks verification failed")
        if any(row["embedding_dimension"] != 1024 for row in chunks):
            raise RuntimeError("Chunk embedding dimension is not 1024")
        if any(not row["content"].strip() or row["end_char"] <= row["start_char"] for row in chunks):
            raise RuntimeError("Chunk content or offsets are invalid")
        print(f"job_status={job['status']}")
        print(f"chunk_count={len(chunks)}")
        print("embedding_dimension=1024")

        answer = session.post(
            "/api/v1/rag/ask",
            json={"question": "What is the internal project codename?", "document_ids": [str(document_id)], "top_k": 5},
        )
        if answer.status_code != 200:
            raise RuntimeError(f"RAG answer failed: HTTP {answer.status_code}")
        answer_payload = answer.json()
        if answer_payload.get("insufficient_context") is not False or not answer_payload.get("answer"):
            raise RuntimeError("RAG answer did not contain sufficient context")
        sources = answer_payload.get("sources") or []
        if not sources or any(str(source.get("document_id")) != str(document_id) for source in sources):
            raise RuntimeError("RAG sources do not belong exclusively to this document")
        citations = {int(number) for number in re.findall(r"\[S(\d+)\]", answer_payload["answer"])}
        if not citations or any(number < 1 or number > len(sources) for number in citations):
            raise RuntimeError("RAG citations do not match sources")
        in_doc_top_similarity = sources[0]["similarity"] if sources else 0.0
        print(f"rag_in_document_question=true")
        print(f"rag_in_document_top_similarity={in_doc_top_similarity:.4f}")
        print(f"rag_in_document_sources={len(sources)}")
        print(f"rag_in_document_citations={sorted(citations)}")
        print(f"rag_in_document_insufficient_context={answer_payload.get('insufficient_context')}")

        insufficient = session.post(
            "/api/v1/rag/ask",
            json={"question": "Which planet has rings made of cheese?", "document_ids": [str(document_id)], "top_k": 5},
        )
        if insufficient.status_code != 200:
            raise RuntimeError(f"Out-of-document question failed: HTTP {insufficient.status_code}")
        insufficient_payload = insufficient.json()
        if insufficient_payload.get("insufficient_context") is not True:
            raise RuntimeError("Out-of-document question was not marked insufficient")
        out_sources = insufficient_payload.get("sources") or []
        out_doc_top_similarity = out_sources[0]["similarity"] if out_sources else 0.0
        print(f"rag_out_document_question=true")
        print(f"rag_out_document_top_similarity={out_doc_top_similarity:.4f}")
        print(f"rag_out_document_sources={len(out_sources)}")
        print(f"rag_out_document_insufficient_context={insufficient_payload.get('insufficient_context')}")

        duplicate = session.post(
            "/api/v1/documents",
            files={"file": (duplicate_filename, content, "text/markdown")},
        )
        if duplicate.status_code != 202:
            raise RuntimeError(f"Duplicate upload failed: HTTP {duplicate.status_code}")
        duplicate_payload = duplicate.json()
        if UUID(duplicate_payload["id"]) != document_id or duplicate_payload.get("duplicate") is not True:
            raise RuntimeError("Duplicate upload did not reuse the original document")
        with engine.connect() as conn:
            chunk_count_after_duplicate = conn.execute(text(
                "select count(*) from document_chunks where document_id = :id"
            ), {"id": str(document_id)}).scalar_one()
        if chunk_count_after_duplicate != len(chunks):
            raise RuntimeError("Duplicate upload changed chunk count")
        print(f"duplicate_document_id={document_id}")
        print(f"chunk_count_after_duplicate={chunk_count_after_duplicate}")
    finally:
        session.close()
        if document_id is not None:
            with engine.begin() as cleanup:
                cleanup.execute(text("delete from documents where id = :id"), {"id": str(document_id)})
            upload_root = settings.get_upload_root_path()
            document_dir = upload_root / str(document_id)
            if document_dir.exists():
                import shutil
                shutil.rmtree(document_dir)
        if user_id is not None:
            with engine.begin() as cleanup:
                cleanup.execute(text("delete from users where id = :id"), {"id": user_id})
        if before_protected is not None:
            with engine.connect() as conn:
                after_protected = snapshot_protected(conn)
                if before_protected != after_protected:
                    raise RuntimeError("Protected document changed during HTTP pipeline")
                if document_id is not None:
                    remaining = conn.execute(text("select count(*) from documents where id = :id"), {"id": str(document_id)}).scalar_one()
                    jobs = conn.execute(text("select count(*) from processing_jobs where document_id = :id"), {"id": str(document_id)}).scalar_one()
                    chunks = conn.execute(text("select count(*) from document_chunks where document_id = :id"), {"id": str(document_id)}).scalar_one()
                    if remaining or jobs or chunks:
                        raise RuntimeError("HTTP pipeline test data remains in database")
                print("protected_after=unchanged")
                print("cleanup=exact_uuid_only")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        raise
