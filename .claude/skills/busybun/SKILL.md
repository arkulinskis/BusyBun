---
name: busybun
description: Context, workflow and recipes for Busy Bun (folder BusyBun-forms), the user's Anvil top-down canvas game (a bao bun on a culinary journey) built as native Anvil Forms, with guest play, accounts and an #admin level builder. Load this before any feature request, bug fix, new level/territory/collectable, art change or deploy for this project.
---

# Busy Bun: working on the game

**What it is:** a 2D top-down canvas game on anvil.works (busybun.com). A bao bun collects meat and ingredients, does
neighbours' errands, smashes pest nests, and enters a steamer to finish a level. 16 worlds / 118 built-in levels
(6 territories × 3 hand-drawn + worlds 7-16 × 10 generated), bonuses, oven knobs, 13 pests incl. 2 bosses, collectables
(37 ingredients, 13 recipes with perks, 9 hats, chopsticks, postcards, 25 badges, coins, stars), guest play + accounts,
leaderboards, and a level builder at `#admin`.

**Where it lives:**
- Folder `C:\Users\arkvi\Documents\CLAUDE\BusyBun-forms\` = the git clone of **github.com/arkulinskis/BusyBun**.
  "git" layout: the folder *is* the Anvil app; pushing is the deploy. Converted to native Forms on branch `forms`
  (2026-11-08); until the user merges it, master still runs the old Custom-HTML version from
  `C:\Users\arkvi\Documents\CLAUDE\BusyBun` (source layout + tools/deploy.py; retire it after the merge).
- Made in the shape of `APP_MAKER\template-forms` (read its guide for the general patterns: pages, layout, items,
  dialogs, accessibility, design kit). `APP_MAP.md` is the code map: read it first.

**What the user wants:** "see the extent you can take it to make it fun": a culinary journey that taps into collecting.
Claude assumes and builds; Claude deploys. The look is the cartoon kitchen: dough/cream surfaces, soy-sauce red, gold,
chunky ink outlines with hard `0 4px 0` shadows, Fredoka + Nunito, emoji items. Light only. Every page fits 390 px.

## Workflow

1. `git pull --ff-only` (read any "Edited ..." commits from the Anvil IDE).
2. Edit: a page's template and Python side by side (`client_code/Pages/X/form_template.html` + `__init__.py`), engines
   in `theme/assets/bb-*.js`, styles in `theme/assets/app.css`.
3. `python tools/check.py` (no -I) → **ALL CHECKS PASSED**: Anvil's validator, JS syntax, asset hashes, the server
   tests (`tools/testing/test_server.py`, strict mock reading anvil.yaml's db_schema; includes the LevelPack check).
4. `python -I tools/ui_test.py` (Docker running) → smoke test `tools/ui/smoke.js` at 1280 and 390 px in the local App
   Server (container `busybun-dev`): every address as a guest, a new player and the admin, a level starts and pauses.
   `--shots DIR` = screenshots. `--stop` stops the container. Server edits need `--restart`.
5. Commit as arkulinskis with the Co-Authored-By line; push. New tables/columns: the user accepts Anvil's Schema
   Mismatch alert ("The schema of the source code is correct").

## Architecture (Forms)

```
client_code/
  startup.py        admin_whoami -> state.me, Privacy & Terms kit, router.start()
  router.py         "" title (Landing), #journey #pantry #kitchen #shop #badges (hub, Layouts/Shell), #play/<level>, #admin
  bun.py            the game state in the browser (st: me, progress, status, journey, catalog, market...), ensure()/act()
                    (guests call the guest_ twins with the progress kept in localStorage "bb.guest.v1"), lookups
                    (level_info, goals, where_found...), sound/music/toast/portrait bridges to window.BB
  flows.py          dialogs several pages open: how to play, sign in (+ adopt guest progress), settings, daily box,
                    level intro, postcard, item info
  auth.py, state.py, legal.py (legal kit: don't edit here)
  Layouts/Shell     player bar (avatar = settings, coins/stars/chopsticks, daily box, settings), the 5 tabs, footer
  Pages/            Landing (title + Watch + footer), Journey, Pantry, Kitchen, Shop, Badges, Play, Admin
  Components/       Portrait (the bun on a canvas), LevelThumb, TitleBg (falling food), Stage (the play screen engine),
                    LevelBuilder (the admin editor engine)
  Items/            WorldCard, RoadNode, PantrySection, PantryItem, PostcardTile, RecipeCard, OfferCard, HatCard,
                    BadgeCard, Chip, Goal, BoardRow, Banner, TerritoryEditor, PlayerRow, FeedbackRow
  Dialogs/          HowTo, SignIn, LevelIntro, Start, Pause, Lose, Results, ItemInfo, Postcard, Cook, Daily, Settings, NewLevel
server_code/        Game.py (every rule: apply_* + signed-in callable + guest_* twin), Catalog.py, Levels.py,
                    LevelPack.py (generated), Admin.py, legal_server.py, seo_routes.py, SchemaCheck.py
theme/assets/       app.css, app-kit.js, ark-music.js, bb-kit.js (window.BB helpers + Sound), bb-art.js (drawing),
                    bb-engine.js (BB.Game), bb-stage.js (play HUD/touch, title bg, road layout, click sound),
                    bb-builder.js (level editor), legal-kit.js
tools/              check.py, assets.py, ui_test.py + ui/smoke.js, gen_levels.py, testing/, live/drive.mjs
```

- **Pages/menus/dialogs/lists are Forms; the engines stay JavaScript.** Text in items is set once with
  `dom_nodes[...].textContent` (no innerHTML lists); changing header text uses Labels.
- **Buttons**: Anvil Buttons with roles `["bb-btn", "red"|"green"|"cream"|"jade", "small"|"big", "block"]`; app.css
  aliases every `.bb-btn` rule to `.anvil-role-bb-btn > button`. Plain `<button class="bb-btn">` also works.
- **Dialogs**: `flows.dialog(Form(...), closable=False)` for the old "noClose" cards (Start, Lose, Results, Cook).
  Each closes with `raise_event("x-close-alert", value=...)`; the page acts on the value.
- **After an action** (buy, cook, wear, daily): `router.show()` redraws the page from `bun.st` (like the old renderHub).
- **Play**: `Pages/Play` mounts `Components/Stage` (BB.mountStage) and opens `Dialogs/Start`; the stage sends
  "pause"/"win"/"lose" (JSON) back; a win goes to `bun.act("finish_level", key, result)` and `Dialogs/Results`.
  "Next level" sets `bun.st["open"]` so the Journey opens that level's intro card. Leaving the page destroys the engine.
- **Admin**: `Pages/Admin` shows a sign-in card to non-admins; admins get Levels (Components/LevelBuilder: the
  engine's server calls go through its `_emit` with the ADMIN_CALLS whitelist; "+ New level" opens Dialogs/NewLevel),
  Territories, Players and Feedback (Forms + items).

## Game rules (server)

- Every progress-changing rule is an `apply_*(progress, ...)` in Game.py with a signed-in callable and a `guest_*`
  twin (guests send their browser progress). New action = both + a call through `bun.act(name, ...)`.
- Progress is one Simple Object in `users.progress`; `normalize()` cleans anything from a browser.
- `apply_finish` caps everything by `Levels.totals(level data)` and requires the goals; NPC order = order of `t:"npc"`.
- Collectables live only in `server_code/Catalog.py` (sent to the client). Art: emoji for items; the rest is drawn in
  `bb-art.js`.
- Engine: `bb-engine.js` (`BB.Game`). World units are tiles. Static tiles are cached offscreen; water/stoves/conveyors/
  crates are drawn per frame.
- Levels: built-ins are ASCII in `Levels.py` (`from_ascii`, `SYMBOLS`, digits via `legend`, `n` = next npc, `O` = next
  nest). Seeded only when missing (`seed_defaults`): editing a built-in doesn't change a live game unless the admin
  uses "↺ Original". `Levels.check` (server) and `check()` in bb-builder.js are the same rules: keep them in step.
- Combat: `attacking()` in bb-engine.js (dashing or 0.15 s after) bonks instead of hurting; `player.safe` blocks damage
  briefly after a dash or a bounce.
- Built-in level versions: `Game.upgrade_builtins()` replaces live built-in data only if it still equals the old
  shipped version, so admin edits survive. To ship a level change, add a new layer the same way.
- **Worlds 7-16** live in `LevelPack.py`, written by `tools/gen_levels.py`. Never edit LevelPack by hand: change `WORLDS`
  or the generator and rerun `python -I tools/gen_levels.py` (a server test fails if they disagree).
- Live installs get new territories through `Game.seed_new_territories()` (never re-adds levels to existing ones).
- Bosses: `Catalog.BOSSES` (`king`, `queen`); `Catalog.FLYERS` may sit over walls (keep `FLYERS` in bb-builder.js in step).
- Feedback: Prepsto is the only channel ("Submit feedback", code xww6ue9). The old `feedback` table stays readable in
  Admin → Feedback.

## Recipes

- **New ingredient/recipe/hat/badge:** Catalog.py (badge logic in `Game.check_badges`, progress bars for count badges in
  `Items/BadgeCard` COUNTS; hat drawing in `Art.drawHat`).
- **New tile:** Catalog.TILES + `Art.drawTile` (+ `Art.SOLID` if solid) + engine behaviour.
- **New pest:** Catalog.PESTS (+ `boss`/FLYERS) + `PEST` table and AI in bb-engine.js + `Art.drawPest` + `bun.PEST_EMOJI`
  + the nest map in bb-builder.js + a `PEST_TIP` in gen_levels.py.
- **New world:** `WORLDS` in tools/gen_levels.py, a theme in `Art.THEMES` + Catalog.THEMES + `.th-<key>` in app.css (+
  `bun.DARK_THEMES` if dark), a music mood in bb-kit.js, then regenerate.
- **New page:** `Pages/X` + router PAGES/_form (+ a tab in Layouts/Shell if it belongs in the hub) + smoke.js.

## Gotchas

- **Continue with Google** (auth.py `google`): `login_with_google()` returns None for someone without an account, so it
  then calls `signup_with_google()`; on the sign-up view the Privacy & Terms tick comes first.
- Guest progress is in localStorage `bb.guest.v1`; after sign-in `bun.after_sign_in` imports it (`import_guest`) when
  the account is empty, then deletes it. Other browser keys: `bb.sfx`, `bb.music`, `bb.seenNew`, `bb.lastHat`.
- `ADMIN_EMAILS` in Game.py grants admin on sign-in; Users email confirmation is off.
- Loading spinner: Anvil's `#loadingSpinner` is restyled in app.css to the bouncing bun; `Art.installMascot()` draws it
  into `--bb-mascot` at load.
- Headless Chrome emoji look flatter than on real devices.
- `python -I` hides PyYAML: run check.py / assets.py without `-I`.

## Privacy & Terms (legal kit)

From `C:/Users/arkvi/Documents/CLAUDE/APP_MAKER/legal-kit` (`apps/busybun.json`): change it there, build and install
into this folder, then `python tools/assets.py`. Don't edit `theme/assets/legal-kit.js`, `client_code/legal.py` or
`server_code/legal_server.py` here. Sign-up keeps the tick box (`legal.consent_field()` in Dialogs/SignIn).

## Music

Mood -> tracks in `Sound.startMusic` (TRACKS / MOOD_TRACKS in bb-kit.js); the synth tune is the fallback. Player =
`window.ArkMusic` (theme/assets/ark-music.js, a copy written by `APP_MAKER/tools/music_sync.py`: after the merge, point
music_sync at this file).
