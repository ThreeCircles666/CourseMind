"""Seed legacy test prerequisites in an explicitly named test database only.

Run migrations first. This script never reads or copies real uploaded documents.
"""
from app.core.config import settings
from app.db.session import SessionLocal
from app.models import User, Document
from app.services import PROTECTED_DOCUMENT_ID
from sqlalchemy import text
from sqlalchemy.engine import make_url


def main():
    database = make_url(settings.database_url).database or ''
    if '_test' not in database:
        raise SystemExit('Refusing to seed a database without _test in its name')
    with SessionLocal() as db:
        if db.get(User, 1) is None:
            db.add(User(id=1, username='legacy-test-owner', nickname='Test fixture', password_hash='unusable-test-fixture', is_active=False))
            db.flush()
        if db.get(Document, PROTECTED_DOCUMENT_ID) is None:
            db.add(Document(id=PROTECTED_DOCUMENT_ID, user_id=None, original_name='test2.pdf', safe_name='synthetic-protected-test2.pdf',
                            mime_type='application/pdf', size_bytes=4, sha256='f' * 64, status='succeeded'))
        db.execute(text("SELECT setval(pg_get_serial_sequence('users','id'), GREATEST((SELECT COALESCE(MAX(id),1) FROM users),1))"))
        db.commit()
    print('Synthetic legacy test prerequisites are ready; no real course files were used.')

if __name__ == '__main__':
    main()
