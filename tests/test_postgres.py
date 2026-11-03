"""Run in CI or with TEST_DATABASE_URL pointing to a dedicated test database."""
import os
from uuid import uuid4

import pytest

from server.storage import Store


@pytest.mark.skipif(not os.getenv('TEST_DATABASE_URL'),reason='Dedicated PostgreSQL test database is not configured')
def test_postgres_snapshot_and_command_receipt():
    store=Store(os.environ['TEST_DATABASE_URL'])
    owner='test:'+str(uuid4())
    try:
        first=store.create(owner,42)
        result=store.command(first['id'],owner,'postgres-command',0,'choose',{'choice':'frontier'})
        assert result['state']['revision']==1
        assert store.command(first['id'],owner,'postgres-command',0,'choose',{'choice':'frontier'})==result
        assert store.latest(owner)==result
    finally:
        from sqlalchemy import delete
        from server.storage import CampaignRow,CommandRow
        with store.session.begin() as db:
            ids=list(db.scalars(__import__('sqlalchemy').select(CampaignRow.id).where(CampaignRow.owner==owner)))
            db.execute(delete(CommandRow).where(CommandRow.campaign.in_(ids)))
            db.execute(delete(CampaignRow).where(CampaignRow.owner==owner))
        store.engine.dispose()
