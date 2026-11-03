# Telegram campaign: first playable chapter

For a free closed playtest without running your own computer, follow [Render Free + Neon Free + Telegram setup](free-playtest.md). The repository contains a Free-only `render.yaml`; no external service has been published automatically.

The default welcome action now starts the separate **ruler_v1** chapter, “Утвердить власть”. See [ruler.md](ruler.md) for people, councils, physical orders, multiple armies, local supplies and obligations; [ruler-acceptance.md](ruler-acceptance.md) records acceptance and remaining work. Existing campaigns retain their legacy rules. The legacy mechanics described below, including Murad's unlock, do not automatically apply to ruler_v1.

This is the first implementation milestone of the agreed 1299–1453 campaign, not the complete Mediterranean game. The existing Pygame application remains available through `main.py` / `run.sh`.

## Local launch

Requirements: Python 3.11+, Node.js 22.12+.

```sh
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cd web
npm ci
npm run build
cd ..
bash scripts/run_web.sh
```

Open http://127.0.0.1:8000. The local demo signs a separate browser session; campaigns persist in `saves/campaign-v1.db`. A local session signing key is generated in `saves/dev-session.key`, with restricted permissions, so restarting the server does not discard browser access. Both files are ignored by Git. The original `saves/savegame.json` is not touched.

For client development, start the server and run `npm run dev` inside `web`; Vite proxies `/api` to port 8000.

## What the chapter implements

- 162 playable Mediterranean settlements across39 factions with explicit land, ferry and sea corridors. Campaign and world modes share illustrated vector geography, fortress/village icons, flags, pan/pinch zoom, region navigation and global search. See [world details and historical limits](world.md).
- A seasonal shared simulation for39 factions. An army has typed troops, a location, supply, morale, transported siege engines and a next-season order.
- Recruitment, mobilization in the capital and other controlled locations, movement, field combat, blockade, siege works, assault, negotiated surrender and retreat.
- Siege outcome depends on garrison, walls, blockade coverage, provisions and morale. A port retains sea resupply; this chapter has no player-controlled fleet or naval blockade.
- Occupation is distinct from ownership. Peace transfers occupied territory and cancels relevant sieges and offensive orders; trade stops on war.
- Seasonal taxation, occupation penalties, administrative overload, food, manpower, military upkeep including besiegers, pay arrears and desertion. Four ordinary buildings, fortress foundations/repairs and three reforms affect the simulation.
- Ten knowledge nodes across five branches. One active priority; progress survives a pause and restoration. Workshop construction and army equipment are separate from learning.
- Conditional council events, including dynastic accessions through1451. The founding choice changes later merchant obligations or military demands. A city charter leads to a later conflict over local rights. Bursa has a post-capture decision before the chapter is marked complete.
- Scheduled succession from Osman through Mehmed II, paid fortress foundations from Murad I (1362), and continued play through1453; freely changing multi-generation genealogy, claimants and civil wars are **not implemented yet**.
- Copy-on-write game commands, versioned snapshots, atomic persistence, optimistic revision checks and idempotent command receipts. Stored campaigns can be resumed and loaded by their owner only.

## Gameplay rules in this milestone

One road takes one season. Entering an enemy stronghold starts a siege. Supply requires a connected friendly rear area. Siege works reduce walls; blockade reduces the city's stores only when enough soldiers are present. Ports replenish their stores by sea. Assault is risky and uses troop strengths, morale, supply, training and wall integrity; all survivors keep their types. Detached occupation garrisons come from the occupying army.

The first chapter can be completed by mobilizing and recruiting in Sogut, moving to Inegol, preparing or maintaining the siege, responding to the council after capture, then advancing to Bursa. A peace agreement recognizes occupied locations. This is one possible path, not a scripted automatic victory.

Military strength and economic figures are game balance values, not historical population estimates. The initial map is a historical draft. Existing locations' coordinates were carried over from the original project without the old pixel offsets. Karacahisar starts under Ottoman control based on the traditional 1288 conquest dating reported by the Turkish Culture Portal. Other 1299 ownership and road details still need a sourced historical pass before public release.

Historical reference: https://kulturportali.gov.tr/turkiye/eskisehir/gezilecekyer/karacahisar-kalesi

## Telegram deployment

Set an HTTPS `PUBLIC_URL`, a Telegram bot token, a random session secret of at least 32 characters and an independent database password. `.env.example` documents the variable names; the application reads environment variables, while Compose also reads `.env` substitutions.

```sh
docker compose up --build -d
```

Run HTTPS termination in front of `127.0.0.1:8000`, then configure the bot's Mini App launch button in BotFather to that HTTPS address. The frontend passes Telegram `initData` to the backend, which verifies the HMAC, user identity and authentication age before setting an HTTP-only session cookie. Production refuses incomplete configuration and has no demo login route.

No bot has been configured or published by this change. Docker/PostgreSQL and actual Telegram iOS/Android operation require a separate environment verification. The browser build can be tested locally now.

## Architecture and commands

- `campaign/`: UI-independent rules and content; all mutations pass through `apply_command`.
- `server/`: FastAPI, Telegram verification and SQLAlchemy persistence. PostgreSQL in production; SQLite for local development.
- `web/`: React/TypeScript mobile interface; the server is the authority for game results.

`GET /api/catalog` supplies available content. `POST /api/auth/telegram` validates a Telegram launch. Authenticated clients create a campaign with `POST /api/campaigns` and resume with `GET /api/campaigns/latest`. `POST /api/campaigns/{id}/commands` accepts `command_id`, `revision`, `kind`, and `payload`. A rejected command leaves the snapshot unchanged; a repeated successful command returns its saved receipt. Reusing the ID with different content or submitting an outdated revision returns 409.

Supported commands: choose, recruit, mobilize, move, retreat, siege_mode, build, equip, research, pause_research, reform, diplomacy, integrate, found_fortress, repair_walls, end_turn.

The first schema is initialized automatically. Version2 explicitly migrates version1 campaign snapshots and command receipts; other unsupported version combinations are rejected; replacing existing campaign tables is not an upgrade strategy. Rules and content versions are stored with each snapshot and unsupported versions are rejected.

## Verification

```sh
.venv/bin/pytest -q
cd web
npm run build
```

Tests include troop conservation with generated inputs, failed-command atomicity, siege upkeep, assaults under multiple seeds, peace/occupation consistency, affordability of narrative choices, research pause/restore, all available buildings, deterministic continuation, a complete first chapter from the real starting state, long seasonal runs, authorization, replay and competing writes. CI additionally executes the store contract against PostgreSQL.

## Remaining work from the overall plan

Per-settlement historical verification and territorial borders; strategic AI and diplomacy; fleets and naval blockade; governors and commander personalities; taxes and credit agreements; dynamic heirs, interregnum and contested succession; authored regional and later-ruler story arcs; late-medieval knowledge and artillery; multiple final campaign assessments; balance review; physical-device testing and public deployment. See [integrated mechanics review](mechanics-review.md).

Paid-foundation browser regression (disposable database and local server): `PYTHONPATH=. python tests/browser_fortress.py`.
