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
