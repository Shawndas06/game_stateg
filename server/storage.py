from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import time
from uuid import uuid4

from sqlalchemy import BigInteger, JSON, Integer, String, UniqueConstraint, create_engine, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from campaign.runtime import apply_command, new_campaign, view, load_state
from campaign.models import State


class Base(DeclarativeBase):
    pass


class CampaignRow(Base):
    __tablename__ = "campaigns"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner: Mapped[str] = mapped_column(String(100), index=True)
    revision: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[int] = mapped_column(BigInteger)
    snapshot: Mapped[dict] = mapped_column(JSON)


class CommandRow(Base):
    __tablename__ = "commands"
    __table_args__ = (UniqueConstraint("campaign", "command_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    campaign: Mapped[str] = mapped_column(String(36), index=True)
    command_id: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    response: Mapped[dict] = mapped_column(JSON)


class ArchiveRow(Base):
    __tablename__ = "ruler_archive"
    __table_args__ = (UniqueConstraint("campaign", "sequence"),)
    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    campaign: Mapped[str] = mapped_column(String(36), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    entry: Mapped[dict] = mapped_column(JSON)


class MissingCampaign(Exception):
    pass


class VersionConflict(Exception):
    pass


class Store:
    def __init__(self, url: str):
        self.engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15} if url.startswith("sqlite") else {}, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.session = sessionmaker(self.engine, expire_on_commit=False)

    @staticmethod
    def response(row: CampaignRow) -> dict:
        return {"id": row.id, "state": view(load_state(deepcopy(row.snapshot)))}

    def create(self, owner: str, seed: int, scenario: str = 'legacy', campaign_mode: str = 'chapter') -> dict:
        s = new_campaign(seed, scenario, campaign_mode)
        entries = getattr(s, "outbox", [])[:]
        if hasattr(s, "outbox"): s.outbox = []
        row = CampaignRow(id=str(uuid4()), owner=owner, revision=0, created_at=time.time_ns(), snapshot=s.to_dict())
        with self.session.begin() as db:
            db.add(row)
            self._archive(db, row.id, entries)
        return self.response(row)

    def latest(self, owner: str) -> dict | None:
        with self.session() as db:
            # A player resumes the last campaign they created, even after server restart.
            row = db.scalar(select(CampaignRow).where(CampaignRow.owner == owner).order_by(CampaignRow.created_at.desc(), CampaignRow.id.desc()).limit(1))
            return self.response(row) if row else None

    def get(self, campaign: str, owner: str) -> dict:
        with self.session() as db:
            row = db.scalar(select(CampaignRow).where(CampaignRow.id == campaign, CampaignRow.owner == owner))
            if row is None: raise MissingCampaign()
            return self.response(row)

    def command(self, campaign: str, owner: str, command_id: str, revision: int, kind: str, payload: dict) -> dict:
        fingerprint = hashlib.sha256(json.dumps([revision, kind, payload], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with self.session.begin() as db:
            row = db.scalar(select(CampaignRow).where(CampaignRow.id == campaign, CampaignRow.owner == owner).with_for_update())
            if row is None: raise MissingCampaign()
            old = db.scalar(select(CommandRow).where(CommandRow.campaign == campaign, CommandRow.command_id == command_id))
            if old is not None:
                if old.fingerprint != fingerprint: raise VersionConflict("Идентификатор команды уже использован для другого действия")
                if old.response['state'].get('scenario') == 'ruler_v1': return deepcopy(old.response)
                return {"id": old.response["id"], "state": view(load_state(old.response["state"]))}
            if row.revision != revision: raise VersionConflict("Кампания уже изменилась. Обновите состояние.")
            state = apply_command(load_state(row.snapshot), kind, payload)
            entries = getattr(state, 'outbox', [])[:]
            if hasattr(state, 'outbox'): state.outbox = []
            # Compare-and-swap also protects SQLite, whose SELECT FOR UPDATE is a no-op.
            changed = db.execute(update(CampaignRow).where(CampaignRow.id == campaign, CampaignRow.revision == revision).values(revision=state.revision, snapshot=state.to_dict()))
            if changed.rowcount != 1: raise VersionConflict("Другой запрос уже изменил кампанию")
            self._archive(db, campaign, entries)
            response = {"id": campaign, "state": view(state)}
            db.add(CommandRow(id=str(uuid4()), campaign=campaign, command_id=command_id, fingerprint=fingerprint, response=response))
            return response


    @staticmethod
    def _archive(db, campaign, entries):
        for item in entries:
            db.add(ArchiveRow(id=f"{campaign}:{item['seq']}", campaign=campaign, sequence=item['seq'], entry=item))

    def archive(self, campaign: str, owner: str, after: int = 0, limit: int = 40) -> dict:
        with self.session() as db:
            row = db.scalar(select(CampaignRow).where(CampaignRow.id == campaign, CampaignRow.owner == owner))
            if row is None: raise MissingCampaign()
            entries = list(db.scalars(select(ArchiveRow).where(ArchiveRow.campaign == campaign, ArchiveRow.sequence > after).order_by(ArchiveRow.sequence).limit(limit)))
            items = [deepcopy(x.entry) for x in entries]
            return {'items': items, 'next': items[-1]['seq'] if items else after}


    def list_campaigns(self, owner: str) -> list[dict]:
        with self.session() as db:
            rows = list(db.scalars(select(CampaignRow).where(CampaignRow.owner == owner).order_by(CampaignRow.created_at.desc(), CampaignRow.id.desc()).limit(30)))
            return [{'id': row.id, 'scenario': row.snapshot.get('scenario', 'legacy'), 'revision': row.revision, 'ruler': row.snapshot.get('ruler', row.snapshot.get('people', {}).get(row.snapshot.get('ruler_id'), {}).get('name', 'Правитель'))} for row in rows]
