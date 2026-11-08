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
