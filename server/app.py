from __future__ import annotations

from dataclasses import dataclass
import os
import logging
from time import perf_counter
from pathlib import Path
import secrets
from typing import Literal
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response, Query
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import text

from campaign.engine import RuleError, catalog
from server.auth import read_session, session_token, telegram_user
from server.storage import MissingCampaign, Store, VersionConflict

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Settings:
    mode: str = "development"
    database_url: str = "sqlite:///saves/campaign-v1.db"
    session_secret: str = ""
    bot_token: str = ""
    public_url: str = "http://127.0.0.1:8000"

    @classmethod
    def environment(cls):
        return cls(os.getenv("APP_ENV", "development"), os.getenv("DATABASE_URL", "sqlite:///saves/campaign-v1.db"), os.getenv("SESSION_SECRET", ""), os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or "http://127.0.0.1:8000")


class Login(BaseModel):
    init_data: str = Field(max_length=16000)


class CreateCampaign(BaseModel):
    scenario: Literal['legacy', 'ruler_v1'] = 'legacy'
    campaign_mode: Literal['chapter','long'] = 'chapter'


class Command(BaseModel):
    command_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,64}$")
    revision: int = Field(ge=0, strict=True)
    kind: Literal["choose", "recruit", "mobilize", "move", "retreat", "siege_mode", "build", "equip", "research", "pause_research", "reform", "diplomacy", "integrate", "end_turn", "found_fortress", "repair_walls", "decide", "consult", "advance", "raise", "form_army", "transfer", "split_army", "merge_armies", "lead", "appoint_commander", "mission", "recall", "provision", "requisition", "appoint", "policy", "grant", "revoke_grant", "audit", "fulfil", "trade", "transport_order", "institution", "construction", "ransom", "release_envoy", "demobilize", "trade_reparation", "continue_campaign", "summon", "begin_reign", "tactical_mode", "battle_deploy", "battle_step", "battle_delegate", "battle_retreat"]
    payload: dict = Field(default_factory=dict)


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings.environment()
    if cfg.mode not in ("development", "production", "test"): raise RuntimeError("Unknown APP_ENV")
    if cfg.mode == "production":
        if not cfg.database_url.startswith("postgresql+psycopg://") or len(cfg.session_secret) < 32 or not cfg.bot_token or not cfg.public_url.startswith("https://"):
            raise RuntimeError("Production requires PostgreSQL, SESSION_SECRET (32+ characters), TELEGRAM_BOT_TOKEN and HTTPS PUBLIC_URL")
    secret = cfg.session_secret
    if cfg.database_url == "sqlite:///saves/campaign-v1.db":
        (ROOT / "saves").mkdir(exist_ok=True)
        if not secret:
            keyfile = ROOT / "saves" / "dev-session.key"
            try:
                with keyfile.open("x") as file:
                    keyfile.chmod(0o600)
                    file.write(secrets.token_urlsafe(48))
            except FileExistsError:
                pass
            secret = keyfile.read_text()
    secret = secret or secrets.token_urlsafe(48)
    store = Store(cfg.database_url)
    app = FastAPI(title="Османская кампания", docs_url="/api/docs" if cfg.mode != "production" else None, redoc_url=None)
    app.state.store = store
    app.state.settings = cfg

    @app.middleware("http")
    async def headers(request: Request, call_next):
        started = perf_counter()
        request_id = secrets.token_hex(8)
        origin = request.headers.get("origin")
        if request.method == "POST" and origin:
            public = urlparse(cfg.public_url)
            accepted = {f"{public.scheme}://{public.netloc}"}
            if cfg.mode != "production": accepted |= {"http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"}
            if origin not in accepted: return JSONResponse({"detail": "Недопустимый источник запроса"}, status_code=403)
        response = await call_next(request)
        response.headers['X-Request-ID'] = request_id
        if request.url.path.startswith('/api/') and request.url.path != '/api/health':
            route = request.scope.get('route')
            logging.getLogger('uvicorn.error').info('api request_id=%s method=%s route=%s status=%s duration_ms=%.1f', request_id, request.method, getattr(route, 'path', '/api/unknown'), response.status_code, (perf_counter()-started)*1000)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"): response.headers["Cache-Control"] = "no-store"
        return response

    def user(request: Request) -> str:
        try:
            authorization = request.headers.get("authorization", "")
            token = authorization[7:] if authorization.startswith("Bearer ") else request.cookies.get("campaign_session", "")
            return read_session(token, secret)
        except (ValueError, KeyError, TypeError): raise HTTPException(401, "Откройте игру из Telegram или войдите в локальную демонстрацию")

    def login_response(response: Response, uid: str):
        response.set_cookie("campaign_session", session_token(uid, secret), httponly=True, secure=cfg.mode == "production", samesite="lax", max_age=86400)
        return {"authenticated": True, "session_token": session_token(uid, secret)}

    @app.post("/api/auth/telegram")
    def login(body: Login, response: Response):
        if not cfg.bot_token: raise HTTPException(503, "Вход через Telegram ещё не настроен")
        try: uid = telegram_user(body.init_data, cfg.bot_token)
        except (ValueError, TypeError, KeyError): raise HTTPException(401, "Не удалось проверить вход Telegram. Откройте игру заново.")
        return login_response(response, uid)

    if cfg.mode != "production":
        @app.post("/api/auth/demo")
        def demo(request: Request, response: Response):
            try: uid = read_session(request.cookies.get("campaign_session", ""), secret)
            except (ValueError, KeyError, TypeError): uid = "demo:" + secrets.token_hex(16)
            return login_response(response, uid)

    @app.get("/api/config")
    def configuration():
        return {"demo_available": cfg.mode != "production", "telegram_ready": bool(cfg.bot_token), "chapter": "Утвердить власть", "scenarios": ["ruler_v1", "legacy"]}

    @app.get("/api/health")
    def health():
        with store.engine.connect() as db: db.execute(text("SELECT 1"))
        return {"status": "ok", "rules_version": 2, "available_rules_versions": [2, 3, 4]}

    @app.get("/api/catalog")
    def content(): return catalog()

    # Avoid postponed local Annotated resolution: dependency is passed directly.
    @app.get("/api/campaigns/latest")
    def latest(uid: str = Depends(user)): return store.latest(uid)

    @app.get("/api/campaigns")
    def campaigns(uid: str = Depends(user)): return store.list_campaigns(uid)

    @app.post("/api/campaigns", status_code=201)
    def create(body: CreateCampaign = CreateCampaign(), uid: str = Depends(user)): return store.create(uid, secrets.randbits(53), body.scenario, body.campaign_mode)

    @app.get("/api/campaigns/{campaign}")
    def get(campaign: str, uid: str = Depends(user)):
        try: return store.get(campaign, uid)
        except MissingCampaign: raise HTTPException(404, "Кампания не найдена")

    @app.get("/api/campaigns/{campaign}/archive")
    def archive(campaign: str, after: int = Query(0, ge=0), limit: int = Query(40, ge=1, le=100), uid: str = Depends(user)):
        try: return store.archive(campaign, uid, after, limit)
        except MissingCampaign: raise HTTPException(404, "Кампания не найдена")

    @app.post("/api/campaigns/{campaign}/commands")
    def command(campaign: str, body: Command, uid: str = Depends(user)):
        try: return store.command(campaign, uid, body.command_id, body.revision, body.kind, body.payload)
        except MissingCampaign: raise HTTPException(404, "Кампания не найдена")
        except VersionConflict as exc: raise HTTPException(409, str(exc))
        except RuleError as exc: raise HTTPException(422, str(exc))

    dist = ROOT / "web" / "dist"
    @app.get('/favicon.ico', include_in_schema=False)
    def favicon_legacy(): return RedirectResponse('/favicon.svg')

    @app.get('/favicon.svg', include_in_schema=False)
    def favicon(): return FileResponse(ROOT / 'web' / 'public' / 'favicon.svg', media_type='image/svg+xml')
    if (dist / "assets").is_dir(): app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    if (dist / "media").is_dir(): app.mount("/media", StaticFiles(directory=dist / "media"), name="media")

    @app.get("/land.geojson")
    def geography(): return FileResponse(ROOT / "web" / "public" / "land.geojson")

    @app.get("/mediterranean-geography.json")
    def world_geography():
        return FileResponse(ROOT / "web" / "public" / "mediterranean-geography.json")

    @app.get("/bithynia-geography.json")
    def chapter_geography():
        return FileResponse(ROOT / "web" / "public" / "bithynia-geography.json")

    @app.get("/")
    def index():
        if not (dist / "index.html").exists(): raise HTTPException(503, "Сначала соберите интерфейс: cd web && npm ci && npm run build")
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return app
