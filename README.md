## Eloify v1
Welcome to Eloify, a program powered by Python (by pygame or pygame-ce), that estimates the elo of chess engines. It is customizable and styled.

# ! WARNING !
Before you go out spamming this is AI slop, it is vibecoded. I do not usually code Python and I do not have the time currently to learn it. Apologies if the quality is low. I'm just working on the functionality.

# Still work in progress.

## Engine error reports

When a target engine fails 10 consecutive move attempts (or a fatal startup/reload
error occurs), Eloify shows a scrollable diagnostic report and automatically
copies it to the clipboard. Use **Copy report** (or **Ctrl+C / Cmd+C**) to copy it
again, and **Back to menu** to dismiss it.

Each error also creates a unique UTF-8 `logs/eloify-error-*.log` beside `main.py`.
If that directory is not writable, Eloify tries `~/.eloify/logs`, then
`Eloify/logs` in the system temporary directory. The report shows the actual log
path, or explains why saving failed. Clipboard failure does not discard the
report or the log.

Reports include the exception type/message, failed-attempt history, tracebacks,
engine executable paths, settings, board position/moves, and a bounded tail of
UCI traffic and engine stderr. Review reports for local paths before sharing;
logs stay on your computer and are not uploaded automatically.

## Legacy Cinnamon compatibility

Cinnamon 1.x is limited to **256 MB of hash** (or your smaller requested budget).
Its UCI-advertised 32768 MB maximum is not a safe allocation limit for the legacy
32-bit builds: large requests can terminate the engine inside `Hash.cpp` before
it searches. Eloify leaves other engines' hash budgets unchanged and shows the
actual applied hash size in the engine configuration.

Engine startup now waits for `readyok` after applying options. Configuration-time
crashes are reported immediately with the applied options and recent engine
output, rather than being retried as ten move failures.

## High-Elo (>3600) top-engine extension

When a target engine performs at top-engine strength in the standard pool
(preliminary rating **≥ 3550** and scoring **≥ 50%** against the 3500+ bracket),
Eloify automatically extends the tournament beyond 3600 Elo:

- **Fixed time-odds tiers up to ~4000+ Elo**: Eloify runs the strongest
  available non-Maia engine (such as Stockfish 19 at 3660 Elo) with **2x, 4x,
  8x, 16x, and 32x** per-move search time while keeping the target engine at its
  configured `1x` move time, producing calibrated tiers at **3740, 3815, 3885,
  3950, and 4010 Elo**.
- **Paired book openings for 3600+ matches**: Standard-pool games still start
  from the normal move-1 starting position (`startpos`), while each 2-game
  3600+ extension match uses a curated grandmaster book line played once with
  White and once with Black so top engines do not repeat identical `startpos`
  draws.
- **Fast runs for weaker engines**: Engines below the top-engine threshold skip
  the time-odds stage automatically. On the final summary screen, the
  per-opponent table scrolls with the mouse wheel or arrow/PageUp/PageDown/Home/End
  keys to inspect all tiers.

## Browse Engine dialog

When choosing an engine executable, hidden folders and files (dotfiles/dotfolders,
Windows `FILE_ATTRIBUTE_HIDDEN` items, and macOS `UF_HIDDEN` items) are hidden by
default. Tick **Show hidden folders/files** in the browse toolbar (or press
**Ctrl+H** on Windows/Linux, **Cmd+Shift+.** on macOS) to display them.

## Audio sound effects

Eloify loads chess sound effects from the `audio/` folder beside `main.py`:

- `castle.mp3` — castling (`O-O` / `O-O-O`)
- `game-start.mp3` — when a game starts
- `game-end.mp3` — when a game finishes (win, draw, loss, checkmate, time forfeit, etc.)
- `move-self.mp3` — piece moves and captures
- `move-check.mp3` — moves that deliver check
- `promote.mp3` — pawn promotions

During live play and on the results screen, use the top-bar **Mute** button (or
press **M**) and **Volume slider** to mute or adjust audio on the fly.

## Live arena, chess rules & clocks

- **30-second chess clocks**: Each side receives a **30.0s** chess clock per game
  (ticking live next to the board). Running out of time forfeits the game on time.
- **Standard draw rules without artificial move caps**: Games are never cut off
  at 300 moves — they play to real checkmate, stalemate, insufficient material,
  **threefold repetition**, **50-move rule** (50 full moves without a capture or
  pawn move), or clock flag.
- **Live Evaluation Bar**: A background Stockfish adjudicator worker (`Threads=1`,
  `Hash=16 MB`) analyses the live board without interrupting or competing with
  the playing engines.
- **ETA & Opponent Progress Queue**: The right-side panel shows live **ETA**,
  scrollable past and upcoming opponents with per-opponent `W-D-L` tallies, a
  **300–4010 Elo** scale bar with pointer arrow under each opponent, and **Skip /
  Unskip** toggles for upcoming opponents.
- **Back to Menu confirmation**: Clicking **Back to Menu** prompts for
  confirmation before stopping a running tournament or leaving results.

## Engine playlist (multi-engine testing)

On the main menu, use the **Engine Playlist** panel to queue multiple engines
(`+ Add Engine`, `↑`/`↓` reorder, `✕` remove, `Clear`). Eloify tests every
queued engine sequentially and displays a **Playlist Leaderboard** on the final
results screen so you can click between engines and inspect each run.

## Scrollable results & interactive game replay

- **Calculating ELO progress bar**: After games finish, the reveal screen shows a
  live progress bar while finalizing ratings.
- **Final Elo Result display (for every tested engine)**: Combines **Move Elo
  (85%)** and **Win-Rate Elo (15%)** into a single **Final Estimated Elo** for
  each engine tested (in the 3600+ High-Elo Time-Odds Extension where centipawn
  loss saturates near zero, weights invert to **85% Win-Rate Elo + 15% Move Elo**),
  while still displaying both underlying ratings side by side.
- **Full-page scrollable results**: Scroll through all opponent tiers, optional
  Move-Quality Elo & Engine Data summaries, and the **Played Games** list.
- **Interactive Game Replay Viewer**: Click **Replay →** on any game to step
  through moves with **Left / Right** or **A / D** (`Home` / `End` jump to start
  or end, `Esc` returns to results). While replaying, Stockfish runs with
  **stronger multi-thread / larger-hash analysis** since no match is in progress,
  and each move shows **time spent** and **remaining clock** for both engines.

## Customization & optional analytics (Settings)

Settings are organized into three tabs with a live board preview:

1. **Engine & Rules**: Threads, Hash, Move Time, **Auto-Rotate Board** (always
   view from the target engine's side), **Engine Data Tracking** (live & peak
   CPU %, RAM MB, OS thread count, and UCI NPS), and **Per-Game Move-Quality Elo**
   (ACPL, Accuracy %, and Move-Quality Elo per game and overall).
2. **Board & Pieces**: Toggle **Board Coordinates (`a–h`, `1–8`)**, choose from
   6 premade board skins (Classic Wood, Tournament Green, Ocean Ice, Slate,
   Walnut, Royal Amethyst) or build a **Custom RGB Board Skin**, and pick from
   5 piece styles (Classic 2-Tone, Vector Neo, Unicode Classic, Minimal Tokens,
   Neon Glow).
3. **Appearance**: Switch between **Dark Mode** and **Light Mode** and choose
   from 6 accent themes (Emerald, Ocean Blue, Royal Purple, Crimson, Amber Gold,
   Cyber Cyan).
