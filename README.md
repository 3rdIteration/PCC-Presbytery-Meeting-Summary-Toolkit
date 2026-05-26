# Presbytery Meeting Summary Toolkit

A reusable toolkit that turns a folder of presbytery meeting documents into a single navigable `index.html` summary — and optionally publishes it to your website over FTP.

Designed so a non-technical user can run the full process by talking to **Claude Code** or **VS Code + Cline**. The toolkit normally stays in one place and you point the agent at whichever meeting folder you want processed — but it also works fine if you prefer to copy the toolkit into each meeting folder (see "Two ways to run it" below).

---

## End-to-end in plain English

Every month:

1. Put the new meeting's documents (PDFs, Word, Excel) in their own folder — naming the folder `YYYY-MM-DD` (the date you currently know the meeting by) is helpful but not required.
2. Open **this toolkit folder** in Claude Code (or VS Code + Cline). The auto-load picks up the instructions.
3. Tell the agent which meeting folder to process, e.g.:
   > "Process the meeting in `..\Meetings\2026-05-26`."
   or, if the folder name is the date:
   > "Process this month's meeting at `..\Meetings\2026-05-26`."
4. The agent will:
   - Make any scanned PDFs in the meeting folder searchable (so Ctrl+F works later).
   - Read every document and figure out the actual meeting date (docket → committee report dates → folder name → ask you if ambiguous).
   - Generate `index.html` **inside the meeting folder** — a self-contained browser-viewable summary with motions, key issues, supporting document links, financial snapshots, a hash list, and a clickable docket at the top that jumps to matching sections.
   - For Word/Excel links in the summary, provide both **View** and **Download** actions (with the title link defaulting to **View**, using an in-browser Office web viewer and no file conversion).
   - **Ask whether you want to upload to the web.** If you only want a local file, say no.
5. If you said yes to uploading, the script confirms the target one more time ("Proceed with upload?") before sending anything. The public URL is printed when done.

The meeting folder ends up containing **only** your source documents, any OCR'd searchable copies of scans, and `index.html`. No toolkit files are copied into it.

---

## What's in this bundle

| File | Purpose |
|---|---|
| `AGENTS.md` | The full recipe the agent follows. Edit this to refine the process. |
| `CLAUDE.md` | Auto-load stub for Claude Code — makes the agent pick up the instructions without being told. |
| `README.md` | This file — for humans. |
| `tools/make_searchable_pdf.py` | Embeds invisible searchable text into a scanned PDF. |
| `tools/upload_to_ftp.py` | Uploads `index.html` to your web host via FTPS (or FTP). |
| `tools/ftp_config.example.json` | Template for the FTP config (you copy & fill in). |
| `tools/requirements.txt` | Python deps for the OCR overlay (the FTP tool uses only stdlib). |

---

## One-time setup

You only do this once, ever. All setup lives **inside this toolkit folder** — meeting folders stay clean.

### 1. Make sure Python is installed

Open a terminal (PowerShell on Windows, Terminal on Mac) and type:

```
python --version
```

If you get a version number (3.10+), you're good. If you get an error, install Python from <https://www.python.org/downloads/>.

### 2. Install the OCR helper's two dependencies

In the toolkit folder:

```
pip install -r tools/requirements.txt
```

If you don't plan to ever process scanned PDFs you can skip this; the agent will run the command for you when first needed.

### 3. Create your FTP config (only if you want to publish)

In `tools/`, **copy `ftp_config.example.json` to `ftp_config.json`** and open it in Notepad / TextEdit / your editor of choice. Fill in:

- **`url`** — required. Looks like one of:
  - `ftps://ftp.yourhost.com/public_html/meetings`  ← recommended (TLS-only)
  - `ftp://ftp.yourhost.com/public_html/meetings`   ← will try TLS, fall back with a warning
- **`username`** — optional. If empty you'll be prompted each run.
- **`password`** — optional. **Leave empty unless you really want it stored in plaintext.** When empty, you type it interactively (hidden) each run.
- **`public_url_template`** — optional. The browser-visible URL pattern your host serves the uploaded folder at. Use `{date}` where the meeting date goes. The uploader prints the final URL after a successful upload.

The config lives in the toolkit, so one config covers every monthly run. Your web hosting control panel (cPanel, Plesk, etc.) is where you'll find these values.

---

## Each month

1. Drop the new meeting's documents into their own folder somewhere (e.g. `Meetings\2026-05-26\`).
2. Open **this toolkit folder** in Claude Code or VS Code + Cline.
3. Tell the agent: **"Process the meeting in `<path-to-meeting-folder>`."**
4. Review `index.html` in the meeting folder (it'll open in any browser).
5. When prompted, allow the upload. The agent prints your live URL when done.

## Two ways to run it

**Recommended — toolkit outside the meeting folder (cleaner).** Master copy lives in one place; each meeting folder contains only source documents and the generated `index.html`. The agent reads from the meeting folder and writes back to it without copying any toolkit files in.

**Also supported — toolkit copied into the meeting folder (legacy).** Some users prefer to keep everything together. The agent recognizes its own files (`AGENTS.md`, `CLAUDE.md`, `README.md`, `tools/`, `ftp_config.json`) and filters them out of the inventory, hash list, and supporting-documents table. The FTP uploader **hard-refuses** to upload `ftp_config.json` regardless of how it is invoked, and prompts for confirmation before uploading any other toolkit file — so even in this colocated mode, your FTP credentials stay local.

---

## What the OCR step does

Some meeting PDFs (extracts of minutes, signed forms) arrive as scanned images with no text layer. Humans can't Ctrl+F them; agents extracting text get nothing. The toolkit handles this:

1. The agent detects PDFs with no extractable text.
2. It reads each page with vision to get the text.
3. It runs `tools/make_searchable_pdf.py` to overlay that text as an **invisible** layer on the original scan, writing the searchable copy back into the meeting folder. Visually identical; searchable and machine-readable.

There's no Tesseract on your machine, so the invisible text isn't positioned word-for-word over the scan. Search and copy work; visual selection highlights won't line up perfectly with the scanned image. Good enough for what we need.

---

## Word/Excel in-browser viewing

The generated summary now treats Word/Excel documents differently from PDFs:

- Each Word/Excel reference includes **View** and **Download** links.
- The file title itself defaults to **View**.
- **View** uses a native Office web viewer URL (no conversion of your local files).
- **Download** always points to the original file in the meeting folder.

Note: the web viewer needs the meeting page/files to be reachable over HTTP(S) (e.g., after FTP upload). When opening `index.html` directly from local disk, those links fall back to direct-file behavior.

---

## How the FTP step keeps you safe

- **Prefers TLS.** If your URL is `ftps://`, plaintext is refused outright. If it's `ftp://`, TLS is attempted first; only with your explicit OK will it fall back to unencrypted FTP.
- **Verifies certificates** against your system's trust store. If verification fails, it shows you the certificate's subject, issuer, expiry, and SHA-256 fingerprint, then asks "trust this and continue?" If you say yes, that fingerprint is pinned in your config so the prompt does not repeat next month.
- **Warns visibly** any time the connection is unencrypted.
- **Confirms before sending.** Once connected and logged in, the script prints the local file, remote path, and encryption state, then asks "Proceed with upload?" — you can still back out at this point.

If you ever change web hosts and their cert legitimately changes, the script will re-prompt. Delete the old fingerprint from `trusted_cert_fingerprints` in `ftp_config.json` if you want a clean slate.

---

## Refining the process

When something about the agent's output should change permanently — new section, different warning, layout fix — edit `AGENTS.md` in this toolkit folder. Next month's run picks up the changes immediately; there's nothing to re-copy anywhere.

Tip: keep a `CHANGELOG.md` next to `AGENTS.md` if you want to track refinements over time.

---

## Troubleshooting

- **"python is not recognized"** — Python isn't on your PATH. Re-install from python.org and tick "Add Python to PATH" during setup.
- **"pip install fails with a permissions error"** — try `pip install --user -r tools/requirements.txt`.
- **Agent can't find the meeting folder** — give the agent a more specific path, ideally absolute (e.g. `C:\Users\you\OneDrive\...\Meetings\2026-05-26`). Relative paths are resolved from the toolkit folder.
- **Upload fails with "could not create remote directory"** — your FTP account doesn't have write access at that path, or the path in your `url` is wrong. Check it against your hosting control panel.
- **Upload says certificate verification failed** — read what the script prints. If it's expected (you know your host's cert), accept it; the script remembers your choice. If it's NOT expected, abort and contact your hosting provider.
- **Agent picks the wrong meeting date** — that shouldn't happen silently. Per AGENTS.md the agent asks if the date is ambiguous. If it didn't ask, tell it the correct date and ask it to regenerate `index.html`.
