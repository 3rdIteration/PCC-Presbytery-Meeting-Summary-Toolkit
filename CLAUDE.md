# Claude Code Auto-Load

This is the **Presbytery Meeting Summary Toolkit**. Open this folder in Claude Code / VS Code + Cline, then the user will name the meeting folder to process — typically something like `..\Business Comittee\<YYYY-MM-DD>` or `..\Meetings\<YYYY-MM-DD>`.

Follow [AGENTS.md](AGENTS.md) end-to-end:

- Read everything in the meeting folder (do **not** copy any toolkit files into it).
- Make scanned PDFs searchable (Step 0).
- Resolve the meeting date by the precedence in Step 1 #9 — **ask the user if the date is ambiguous**, do not guess.
- Generate `index.html` directly into the meeting folder.
- Ask before uploading (Step 16). Publishing is opt-in.
