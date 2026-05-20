# Agent Instructions: Presbytery Meeting Summary Generator

## Purpose

Produce a professionally formatted HTML meeting summary from a folder of meeting documents (docket, reports, interim moderator reports, financial statements, grant applications, etc.) for a Presbyterian church presbytery meeting.

## Invocation

This toolkit lives in its own folder (the **toolkit folder**) and operates on a separate **meeting folder** that contains the documents to be summarized. The toolkit is **not** copied into the meeting folder.

The user will typically:

1. Open Claude Code (or VS Code + Cline) with the toolkit folder as the working directory. This loads `CLAUDE.md` / `AGENTS.md` automatically.
2. Tell the agent which meeting folder to process — e.g. *"Process the meeting in `..\Business Comittee\2026-05-19`."*

The meeting folder may be on a relative path from the toolkit (e.g. `../Meetings/2026-05-26/`) or an absolute path. Treat whatever path the user gives as the **meeting folder**, and:

- Read documents from the meeting folder.
- Write `index.html` into the meeting folder.
- If you need to write an OCR-searchable PDF (Step 0), place it in the meeting folder next to the original.
- Do **not** copy any toolkit file into the meeting folder. The meeting folder should contain only source documents, OCR'd searchable copies of scans, and the generated `index.html`.

When invoking the helper scripts in `tools/`, use paths relative to the toolkit folder (or absolute paths). All examples below use the placeholder `<toolkit>` and `<meeting>` — substitute the actual paths.

## Inputs and Outputs

- **Input:** a meeting folder (path given by the user) containing the meeting's PDFs, Word documents, and Excel spreadsheets.
- **Output:** a single `index.html` file written into the meeting folder.
- **Word/Excel link behavior:** for every `.doc`/`.docx`/`.xls`/`.xlsx`/`.xlsm` reference in the summary, render both **View** and **Download** links; the document title/file-name link should default to **View**.

## When the toolkit is colocated with meeting documents

The recommended invocation has the toolkit folder and the meeting folder separate (see Invocation above). But the toolkit must also work when its files have been **copied into the meeting folder** (legacy workflow, or the user simply prefers it that way).

When the meeting folder contains toolkit files, they are **not meeting documents** and must be filtered out at every step. Recognize them by these patterns (case-insensitive on Windows):

- `AGENTS.md`, `CLAUDE.md`, `README.md` — toolkit documentation.
- `tools/` and everything under it — including `make_searchable_pdf.py`, `upload_to_ftp.py`, `requirements.txt`, `ftp_config.example.json`, and **`ftp_config.json`** (which contains the FTP server URL and may contain credentials).
- `index.html` — your own output, not a source document.
- `*.bak`, `*.tmp-*.pdf` — backups left by `make_searchable_pdf.py --in-place`. Leave them on disk but don't list them.

For each of these:

- Do **not** include them in the Expected Document Inventory check (don't count toolkit files as "core documents present").
- Do **not** include them in the Supporting Documents table (§9 in the prescribed structure).
- Do **not** include them in the document hash list (§14).
- Do **not** include them in any FTP upload. The `upload_to_ftp.py` script enforces this defensively (it refuses to upload any file matching `ftp_config*.json` and warns on `AGENTS.md` / `CLAUDE.md` / `README.md` / `tools/`), but you should also filter at the agent level.

**Special note on `ftp_config.json`:** it may contain plaintext FTP credentials. Never list it in the output, never reference its contents in the HTML, and never upload it. If you see it in the meeting folder during a colocated run, mention to the user (in chat, not in the HTML) that they should consider whether they want credentials committed to a shared OneDrive/SharePoint location.

## Available Tools in This Bundle

The `tools/` subfolder of this toolkit contains:

- `tools/make_searchable_pdf.py` — embed an invisible searchable text layer onto a scanned PDF after you have OCR'd it via vision. Run `python <toolkit>/tools/make_searchable_pdf.py --help` for full usage. Input and output paths are passed explicitly, so this script does not care where it is invoked from.
- `tools/upload_to_ftp.py` — upload the generated `index.html` **and every local document it references** to an FTP(S) server inside a date-named folder, so links resolve on the live page. Reads `<toolkit>/tools/ftp_config.json` (template at `<toolkit>/tools/ftp_config.example.json`). Pass `--folder <meeting>` so it knows where `index.html` lives and can infer the date. After sending `index.html` the script parses it for `<a href="...">` references to local files in the same folder and uploads each one (skipping external URLs, subdirectories, the credential file, and — with a confirmation — toolkit files). Pass `--only-html` to upload just the HTML and skip the referenced documents. Prefers TLS; warns on unverified certs and cleartext.
- `tools/requirements.txt` — Python dependencies (`pypdf`, `reportlab`). Install with `pip install -r <toolkit>/tools/requirements.txt` if missing. The upload script uses only the Python stdlib (no extra installs).

## Output Format

- Single self-contained HTML file named `index.html`.
- Embedded CSS — no external stylesheets.
- All document links open in new browser tabs (`target="_blank"` with `rel="noopener noreferrer"`).
- For Word/Excel documents, include a native web-view link (no file conversion) plus a direct download link.

## Summary Philosophy

This `index.html` is a **navigation aid for the meeting**, not a substitute for the source documents. It exists to help court members avoid missing things they need to vote on, raise, or act on — while still encouraging them to read the actual reports beforehand.

**The summary must strike a balance:**

- **Help** people scan the package and not miss critical items at the meeting.
- **Don't** be so detailed that members skip the underlying reports.

Concretely, this means:

- **For standing committee reports and the General Presbyter's report** (§3 Pastoral Guidance, §4 Mission Plan / Ministry, §5 General Presbyter, similar): the section should contain **only** (a) a one-line link to the source document and period covered, (b) "Highlights & key issues" callouts, and (c) any motions verbatim. Do **not** reproduce the report's content in bullets, paragraphs, or numbered lists — that's the report's own job. If the meeting only reads the summary, they should know what to pay attention to and what to vote on; if they want detail, they open the report.
- **Highlights & key issues** are styled callouts that draw the eye:
  - ⚠ **Concerns** in a warning box (gray): large financial decisions, missing documentation, date or figure inconsistencies, anticipated future agenda items, pastoral matters needing attention, legal / property / grant decisions.
  - ★ **Things worth celebrating** in a highlight box (teal): significant ministry engagement, successful initiatives, milestones, congregational successes, completed projects, healthy interim ministries. The summary should affirm good news, not just flag problems.
- **Motions and recommendations** appear verbatim in yellow motion boxes — these need a vote.
- **For Call business** (§7): include the facts the court must act on (vote counts, terms, proposed ordination date) — these are themselves the "key issues to act on." Do not re-narrate the call's preamble.
- **For Other Business / informational items** (§8 — memos, position openings, save-the-dates, circulars): a short factual description IS appropriate. These items often *are* the announcement, and there is no other report to read. Keep these to a few bullets per item.
- **For the Treasurer's Report** (§9): link the financial documents, flag any unusual figures or missing items, but do not re-tabulate every line item.

A reader who only skims `index.html` should leave with three things in mind: **what they must vote on, what concerns they should not miss, and what good news the court should affirm.** Everything else is in the documents.

---

## Expected Document Inventory

A typical Brampton Presbytery monthly meeting folder contains the document types listed below, derived from inspecting the last 24 months of meetings. Use this list to:

- **Flag missing core documents** inline as ⚠ key issue warnings at the section they would normally support.
- **Decide what to render** when a document is absent — see "Partial Document Set Handling" below.
- **Identify documents** by their filename pattern so they end up in the right section.

Brackets in patterns are placeholders (`<Date>` = something like `October 28, 2025`; `<Month>` = `October 2025`; `<Congregation>` = a church name).

### Core — always expected; flag inline as ⚠ if missing

- **Docket** — `<Date> - Docket.pdf`. The numbered agenda for the meeting; the authoritative source for meeting date, location, moderator, clerk, worship leaders, and any Stated Hour topic and time.
- **Business Committee Report** — `<Date> - Business Committee Report.pdf`. Contains the RECEIVE/NOTE/FILE table, the REFER table, recommendations and motions for vote, and a Treasurer's summary.
- **Summary Minutes (prior meeting)** — `<Date> - Summary Minutes.pdf`. The approved minutes of the previous regular meeting. Absent from emergent/call meetings is normal — do not flag.
- **Interim Moderator (IM) Reports** — `IM Report - <Congregation> - <Month>.pdf`. One per active congregation under interim ministry oversight; typically 8–12 per meeting. Flag if fewer than 5 are present.
- **Financial set** — every regular meeting:
  - **Balance Sheet** — `Balance Sheet <Date>.xlsx` or `.pdf`. Account balances as of the month end.
  - **Profit & Loss** — `P&L <Month>.xlsx`. Income and expenses for the month.
  - **YTD P&L** — `YTD P&L Jan - <Month>.xlsx` or `.pdf`. Year-to-date rolling income and expenses.
  - **Assessments** — `Assessments <Month>.xlsx` or `.pdf`. Per-congregation assessment tracking.
- **Changes to the Roll** — `<Date> - Changes to the Roll.pdf`. Membership additions, removals, transfers, deaths since the last meeting.

### Standing committee reports — usually present; note absence but do not flag unless unusual

- **General Presbyter's Report** — `General Presbyter's Report <Month>.pdf` or `General Presbyter - Proposals for the Business Committee - <Month>.pdf`. Activities, appointments, and initiatives from the General Presbyter; a recent addition (newer role, appears from late 2025 onward).
- **Pastoral Guidance Committee Report** — `Pastoral Guidance Committee Report - <Month>.pdf` (older: `Pastoral Guidance Report - <Month>.pdf`). Pastoral oversight of congregations and ministers — search committees, stated supply, leave matters.
- **Ministry Committee Report / Mission Plan Committee Report** — `Ministry Committee Report - <Month>.pdf` (older) or `Mission Plan Committee Report - <Month>.pdf` (newer name). Reports on congregational viability, mission plans, and ministry initiatives.
- **Nominations Committee Report** — `Nominations Committee Report - <Month>.pdf`. Slates of nominees for committee and officer positions; appears at most-but-not-all meetings.
- **Standing Orders Report / Standing Orders revisions** — `Standing Orders Report - <Month>.pdf` or `<NNNN> Standing Orders.pdf` (e.g. `2602 Standing Orders.pdf`, where the number encodes the year and meeting). Procedural governance — rule changes, adopted standing orders.

### Specialized / event-driven — include when present; absence is normal

- **Grant Applications and Approvals** — e.g. `Chisholm Fund Application <Congregation> <Date>.pdf`, `Congregational & Community Ministries - Grant approved - <Congregation>.pdf`, `Re Development Grant for_ Accessibility.pdf`. Applications by congregations to PCC funds (Chisholm, Congregational & Community Ministries, Pension & Benefits hardship, etc.) or notices that a grant has been approved. **Distinguish the PCC grant amount allowed from the total project cost** — see Critical Requirement #3.
- **Supply / Stated Supply / Interim Ministry agreements** — `Terms and Guarantee <Name> Signed <Date>.pdf`, `Interim Ministry Contract <Congregation> - <Name>.pdf`. The signed terms-of-call or contract for a pastoral appointment.
- **Ordination / Induction / Call Minutes** — `Minutes - Ordination - <Name> - <Date>.pdf`, `MINUTES Induction - <Name> - <Date>.pdf`, `Extract of Minute Call to <Name>.pdf`. Records of specific liturgical/ecclesiastical actions taken at this or a recent meeting.
- **Overtures** — `Overture re <Topic>.pdf` (e.g. `Overture re Camp Ministry.pdf`, `Overture re Abuse and Harassment.pdf`). Formal proposals being sent up to General Assembly through this presbytery.
- **Memos, Letters, Formal Questions** — `Memo re <Topic> <Date>.pdf`, `Formal Question from <Congregation>.pdf`, `Letter to <Party>.pdf`. One-off correspondence requiring presbytery attention or decision.
- **Amalgamation / Property / Trust documents** — `<Congregation> Amalgamation update.pdf`, `Plan for <X> Amalgamation.pdf`, `Declaration of Trust <Congregation>.pdf`. Tied to specific multi-meeting processes — when one appears, watch for a series across consecutive meetings.
- **General Assembly Reports / Calls** — `Report of <Year> General Assembly to Presbytery.pdf`, `Call for Commissioners to the <Year> General Assembly.pdf`, `Call for nominations for Moderator.pdf`. Appears in the months around the annual GA cycle.
- **Budget documents** — `Proposed Budget <Year>.xlsx`, `REVISED Budget <Year>.xlsx`. Typically appears at the November meeting for the following year.
- **Disciplinary / Voluntary Withdrawal Committee Reports** — rare, congregation-specific, often confidential — handle with care if encountered.
- **Attendance / Sign-in sheets** — `attendance <Date>.docx`, `Sign-in Sheets - <Group>.doc`. Procedural; not normally surfaced in the summary, but list them in the Supporting Documents table at the bottom.

### Naming gotchas

- Docket / report numbering varies (`0`, `00`, `01`, `1.0`, or no prefix). Match on the meaningful part of the filename, not the leading number.
- Date formatting in filenames is inconsistent — `October, 2025`, `October 2025`, `Oct 2025`, `10-28-2025` all occur.
- `Pastoral Guidance Report` and `Pastoral Guidance Committee Report` are the same thing under two names.
- `Ministry Committee Report` was renamed to `Mission Plan Committee Report` — both refer to the same committee.
- IM reports may name the congregation with or without a comma (`St. Paul's Bramalea` vs. `St. Paul's, Bramalea`).

---

## Partial Document Set Handling

When some documents are missing, still produce a useful `index.html` rather than refusing. Specific rules:

- **No docket**:
  - Resolve the meeting date by the rule in Step 1 #9 (standing committee report dates → folder name → ask user). Do not silently default to the folder name.
  - Build the HTML in the standard section order anyway.
  - Mark the Docket section with a prominent ⚠ "Docket PDF not present in folder — structure is inferred from other documents."
  - Skip the "link Docket PDF at item 2" rule.
  - Skip Stated Hour rendering unless a separate document references it.
- **No Business Committee Report**:
  - Render the section header with a ⚠ box noting it is missing.
  - Skip the RECEIVE/NOTE/FILE, REFER, and Recommendations tables.
  - If the financial set is still present, render a Treasurer's summary from those documents directly.
- **No Summary Minutes from prior meeting**:
  - Note the absence in the Reports section.
  - Only raise a ⚠ if this is a regular (non-emergent) meeting.
- **Fewer than 5 IM Reports**:
  - Render the IM table with whatever is present.
  - Flag with ⚠ "Unusually few IM reports present — expected one per active interim ministry charge."
- **Missing items from the financial set**:
  - List whichever of Balance Sheet, P&L, YTD P&L, and Assessments exist in the Treasurer's section.
  - Flag each missing item inline with ⚠.
- **Missing Changes to the Roll**:
  - Note in the appropriate section; flag with ⚠ if this is a regular meeting.
- **Missing standing committee reports** (Pastoral Guidance, Ministry/Mission Plan, Nominations, Standing Orders):
  - Render the section header with a brief "No report circulated for this meeting" note.
  - Do not flag with ⚠ — these are not present every meeting.

In all partial-set cases, render the **Supporting Documents** table at the bottom with whatever files actually exist in the folder. Never link to a file that is not physically present.

---

## Process

### Step 0: Preprocess Scans and Images (Extract Text Sidecars)

Before parsing content, ensure every visual document in the meeting folder is text-accessible so humans can use Ctrl+F and future automated runs can extract text cleanly.

#### 0a. Scanned PDFs → embedded invisible text layer

1. For each `.pdf` in the meeting folder, attempt text extraction with `pypdf`. If a PDF returns essentially zero extractable text it is a scan and needs OCR.
2. Read the scanned PDF with your vision capability, capturing the text page by page.
3. Run the overlay utility to embed the OCR'd text as an invisible layer. The output is written into the **meeting folder** next to the original:
   ```
   python <toolkit>/tools/make_searchable_pdf.py <meeting>/<input.pdf> <pages.json> [--output <meeting>/<output.pdf>] [--in-place]
   ```
   - `pages.json` is a JSON array of strings, one per page, in order. Write this scratch file inside the toolkit folder or `%TEMP%` — do not leave it in the meeting folder.
   - With `--in-place` the original file in the meeting folder is replaced (a `.bak` backup is written next to it in the meeting folder).
   - Without `--in-place` the new file is written as `<name> - searchable.pdf` next to the original in the meeting folder; prefer this when in doubt.
   - Clean up any scratch `pages.json` files after the run so they don't accumulate.

#### 0b. Image files → text sidecar

Image files in meeting packages are usually photos of documents (forms, signed pages), announcement posters (concerts, events), or charts with text labels. They are not searchable by default.

**Always attempt OCR on every image** — don't skip an image because the type looks stylized, the layout is artistic, or you think it won't produce clean text. Partial OCR is still useful for search and for future agent runs, and an honest "this is what I could read; the rest is graphic" sidecar is more helpful than no sidecar.

1. For each image (`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.tiff`, `.webp`) in the meeting folder:
   a. Check whether a sidecar already exists at `<stem>_ocr.txt` (same folder as the image). If it exists and is non-empty, **skip** — already processed.
   b. Read the image with your vision capability. Always transcribe whatever text is legible, even if the typography is stylized or only part of the image is readable. If words are unreadable, write `[illegible]` rather than guessing.
   c. After the transcribed text, on a separate paragraph after a `---` separator, add a short prose description of the image (layout, graphics, photographic content, anything visual that the OCR text alone wouldn't convey). This applies whether the image is a poster (where the description fills in the visual styling), a photo (where the description IS most of the content), a chart (where the description names the chart type and axes), or a form (where the description notes filled-vs-blank fields, signatures, etc.).
   d. Write the result to `<meeting>/<stem>_ocr.txt` (UTF-8). Naming: keep the original stem verbatim and append `_ocr.txt` — e.g. `TPC concert.png` → `TPC concert_ocr.txt`. Always produce a sidecar, even for images where the OCR yields very little — describe what is there.
2. In the generated HTML, link **both** the original image and its `_ocr.txt` sidecar from the same row of the Supporting Documents table. If the image carries substantive meeting content (a poster announcing a Stated Hour item, a chart referenced in a report, a signature page substantiating a vote), also surface a brief summary inline at the section it relates to. Purely decorative or unrelated images can be listed only in Supporting Documents — but a sidecar is still produced for them.

#### 0c. After preprocessing

All subsequent extraction in the meeting folder can rely on (a) embedded text in PDFs and (b) `_ocr.txt` sidecars for images. Build the Expected Document Inventory check, the Supporting Documents table, and the hash list using these enriched sources.

### Step 1: Read and Analyze All Documents

1. List all files in the working directory.
2. Read every PDF and Excel file. PDFs now have embedded text (Step 0). For Excel files, read key figures (balances, totals, dates).
3. Match each file to a type using the **Expected Document Inventory** above. Build a running list of which **core** types are present and which are missing — this drives both the missing-document warnings (Step 7) and the partial-set rendering rules.
4. Identify the **docket** document — it lists the order of business items for the meeting.
5. Identify the **Business Committee Report** — it contains correspondence tables (RECEIVE/NOTE/FILE and REFER), recommendations, and motions.
6. Identify the **General Presbyter's Report** — it covers activities, appointments, and initiatives.
7. Identify **Interim Moderator (IM) / Presbytery Representative reports** — one per congregation.
8. Identify any **grant applications**, **financial statements**, or other supporting documents.
9. Note the meeting date, location, moderator, clerk, worship leaders, and any Stated Hour topic/time from the docket.

> **Meeting date — resolution order:** the folder name is **not** authoritative; folders are often named after when the materials were assembled, not the meeting itself. Resolve the meeting date by walking this list in order and stopping at the first confident answer:
>
> 1. **The docket PDF.** If present, its printed date is canonical. Use it.
> 2. **Standing committee reports.** Pastoral Guidance, Mission Plan / Ministry, General Presbyter's, Nominations, Standing Orders — these reports typically carry the upcoming Presbytery meeting's date in their title or first-line heading (e.g. "Pastoral Guidance Committee Report — May 26, 2026"). If two or more reports agree on a date, trust it. Ignore dates that are clearly signing dates or period-of-coverage dates rather than meeting-date labels.
> 3. **The containing folder name.** Use only if (1) and (2) yield nothing.
> 4. **Ask the user.** If sources disagree and you cannot tell which is authoritative — e.g. one report says May 26 while the folder says May 19 and there is no docket — **ask the user before generating the report.** Do not silently pick one.
>
> Whichever date you use, render the resolution path in §1 (Header) so a reader can see where it came from. If the date you chose disagrees with another plausible candidate (e.g. you used a report date but the folder name differs), flag the disagreement inline as a key issue.

### Step 1.5: Triage Documents That May Not Belong in the Public Summary

A meeting folder sometimes contains documents that are physically present but **should not be surfaced** in the published `index.html` — they may be confidential, intended only for the Business Committee, or simply unrelated material dropped in by accident. Before generating any HTML, scan the inventory you built in Step 1 and **stop to ask the user** about any document that matches one of the categories below.

**Flag — and ask before including:**

- **"For Business Committee only" variants.** Filenames or first-page headings containing "for Business Committee only", "BC only", "Business Committee — confidential", "internal", or "not for distribution". Watch especially for **paired reports** where one variant is labelled "to Presbytery" / "for the Presbytery" (short, public-facing) and another is labelled "for Business Committee only" (long, internal). The long version is BC-internal; only the short version is read at the meeting.
- **"Core Issues" / complaint / grievance / personal-note attachments.** Documents that enumerate concerns about a named individual, internal Session deliberations, personal correspondence, or material that reads like background for a specific officer (e.g. the Deputy Clerk) rather than the whole court.
- **Items referred to a single officer in the BCR REFER table.** When the Business Committee Report refers an item to a single named person (Deputy Clerk, Clerk, Lawyer, etc.) rather than to a committee, treat the underlying document as likely-confidential and ask.
- **Apparent placement errors.** Documents from another presbytery, another year, an unrelated topic, or that aren't referenced by any other document in the folder. Ask whether they belong here at all.
- **Anything whose absence would *not* prevent a court member from following the meeting**, and whose publication could embarrass a person or breach a confidence — when in doubt, flag and ask.

**How to ask.** For each flagged document, present a short prompt to the user that:

1. Names the file.
2. Gives your reason for flagging it (one line — e.g. *"appears to be the long BC-only counterpart to the short 'to Presbytery' report"*, *"refers to a named individual and was referred to the Deputy Clerk in the BCR"*, *"from Presbytery of X, doesn't match this meeting"*).
3. Offers a clear choice:
   - **Include and summarize** — treat as a normal meeting document (link, hash, list in Supporting Documents, surface key content).
   - **Omit entirely** — leave the file on disk for the record, but do **not** link it, summarize its content, hash it, or list it in the Supporting Documents table. Do not mention by name or describe what was omitted; treat it as if it were never in the folder for the purposes of this summary.
   - (Optional third) **Remove from folder** — only if the user confirms the file truly doesn't belong here.

**Wait for the user's answer before generating HTML.** Default to *omission* if the user is unreachable: it is safer to leave something out than to publish it by mistake. A document that is later determined to be safe can always be added in a follow-up regeneration; a document that was published in error cannot easily be unpublished.

**Why this matters for upload.** The FTP uploader (Step 16) uploads `index.html` plus every local file the HTML references. A document that is omitted from `index.html` is automatically also omitted from the upload — that is the intended mechanism for keeping a file local-only. The agent does not need a separate exclusion list; getting the HTML right is sufficient.

### Step 2: Structure the HTML Document

Use the following structure:

```
1. Header (Title, Date, Location, Moderator, Clerk, Worship, Stated Hour info)
2. Top navigation link near the top: **"← Back to meeting documents index"** linking to `../` (relative path only; no hardcoded domain)
3. Docket Section (items listed in order, with Docket.pdf linked at item 2)
4. Reports Section
   a. Business Committee Report (with RECEIVE and REFER tables, recommendations)
   b. Pastoral Guidance Report (note if no document circulated)
   c. General Presbyter's Report
5. IM / Presbytery Representative Reports (table with congregation, reporter, document link)
6. Motions and Recommendations for Vote (summary table)
7. Other Business
8. Adjournment
9. Next Meetings (dates, times, locations, documentation deadline)
10. Supporting Documents (complete reference table of all files and where they are matched)
11. Attribution footer
12. JavaScript to set target="_blank" on document links and wire Word/Excel View+Download behavior
```

### Step 3: Docket Section

- List each docket item as an `<h3>` heading (numbered).
- **Link the Docket PDF inline at item 2** (where the docket is formally adopted), not above the docket list.
- For the Stated Hour docket item, include the **scheduled time** displayed prominently.

### Step 3.5: Top "Back" Link

- Add a visible navigation link near the top of the page (above or immediately below the header block).
- Link target must be `../` so the page navigates up one folder level (e.g. from `/2026-05-26/` to `/` of the meeting docs site path).
- Use a relative URL only — never hardcode protocol, domain, or host-specific absolute URLs.

### Step 4: Business Committee Report

The BCR is the exception to the "no content summaries" rule from the Summary Philosophy — its correspondence tables and recommendations *are* the action items. Parse the BCR PDF and produce:

#### RECEIVE, NOTE AND FILE Table
| Sender | Document | Status |
|--------|----------|--------|
- Include clickable links to any circulated document files.
- For Word/Excel files, each reference must expose **View** and **Download** actions; the main clickable document title should point to **View**.

#### REFER Table
| Sender | Document / Matter | Referred To |
|--------|-------------------|-------------|
- List each item of correspondence and where it is being referred (Business Committee, Pastoral Guidance Committee, Lawyer, etc.).
- Include clickable links to any referenced PDF/XLSX files.
- For Word/Excel files, each reference must expose **View** and **Download** actions; the main clickable document title should point to **View**.

#### Recommendations and Motions
- Display each recommendation in a styled motion box, verbatim.
- Number them sequentially (Recommendation 1, 2, 3, etc.).

#### Treasurer's section
- Link the financial documents.
- Flag any unusual figures or movements as ⚠ key issues; flag healthy positions as ★ highlights.
- Do **not** re-tabulate every line item from the Balance Sheet / P&L — that's what those files are for.

### Step 5: IM / Presbytery Representative Reports

Create a table with columns: # | Congregation | Reporter | Document. Link to any IM report PDFs. **Do not write a paragraph summary of each IM report.** Instead, after the table, add any ★ highlights and ⚠ concerns drawn from the IM reports as inline callouts — examples: search committee progressing to call stage (★), interim minister on leave (⚠), congregation viability concern (⚠), induction date set (★).

### Step 6: Motions and Recommendations Summary

Create a consolidated table listing all motions and recommendations requiring a vote, with:
- The recommendation/motion number
- A brief description
- The source document

### Step 7: Highlights & Key Issues (the heart of every report section)

Per the Summary Philosophy, each report section's body is made of **inline callouts** — concerns to flag and highlights to celebrate. Place them at the section most relevant to each item, not in a separate end-of-document block.

**⚠ Key issues (gray warning boxes)** — things the court should not miss or that need attention:

- **Financial concerns** — unusual balances, large transactions, financial influxes.
- **Property issues** — delays, sales, building concerns.
- **Pastoral matters** — sick leave, stated supply extensions, search committees, ministers in difficulty.
- **Legal matters** — letters to lawyer, suspensions, concerns.
- **Grant decisions** — especially Stated Hour items with financial implications.
- **Anticipated future agenda items** — when a report flags that a funding request, motion, or appointment is *expected at a future meeting*, raise a ⚠ so the next meeting's planners catch it.
- **Date / figure inconsistencies** between documents in the package.
- **Missing Documentation** — apply the rules in **Expected Document Inventory** and **Partial Document Set Handling** (above): raise a ⚠ when a **core** document is absent and at the section that document would normally support. Also raise a ⚠ when a document is referenced by name in another report but no matching file exists in the folder.

**★ Highlights (teal highlight boxes)** — things worth affirming:

- **Significant ministry engagement** — preaching, worship, congregational visits, pastoral care across the presbytery.
- **Successful initiatives** — completed projects, surveys delivered, books read, online groups running.
- **Milestones** — successful interim ministries reaching call stage, ordinations, inductions, anniversaries.
- **Congregational successes** — visioning sessions launched, healthy attendance, financial stability.
- **Healthy collaborations** — regional GP work, partnerships with other presbyteries, Synod-level engagement.

Use highlights sparingly and only for substantive items — don't manufacture positivity. If a section has nothing to celebrate, it's fine for it to have only concerns (or only motions, or even just a link).

**Be specific.** "Active ministry" is not a highlight; "Led worship at four congregations this period and launched a visioning process at Claude PC" is. The same goes for concerns: "Watch the budget" is weak; "Motion 1 locks $2.09M into Internally Restricted Funds — confirm figures against source records before voting" is useful.

### Step 8: Supporting Documents Table

At the bottom of the document, include a complete reference table listing **every file** in the meeting folder and which docket item or report it is matched to. If any files cannot be matched to a specific docket item, note them as standalone supporting documents.
- For Word/Excel rows in this table, include both **View** and **Download** links (with the title/file-name link defaulting to **View**).

### Step 9: Next Meetings

Extract next meeting dates, times, and locations from the docket or Business Committee Report. Include the documentation deadline date.

### Step 10: Styling Requirements

Use the following CSS conventions:
- Motion boxes: yellow background with yellow left border, prefix "Motion N —"
- Key issue warnings: light gray background with gray left border, prefix `⚠`
- Highlight (worth celebrating) callouts: light teal background with teal left border, prefix `★`. Distinct from Stated Hour green to avoid visual ambiguity.
- Stated Hour items: green background with green left border (reserved exclusively for docket-level Stated Hour topics — not for highlights)
- Tables: dark header background, alternating row colors, hover highlight
- Links: blue, no underline by default, underline on hover
- Use a clean, professional sans-serif font stack

### Step 11: JavaScript for Link Behavior

Include a `<script>` block before `</body>` that:

1. Sets `target="_blank"` and `rel="noopener noreferrer"` on all document links.
2. Rewrites Word/Excel "View" links to a native web viewer URL (no conversion), while keeping separate direct local-file download links.
3. Leaves links as direct file links when the page is not being served over `http(s)` (for local offline preview scenarios).
4. Treats Word/Excel "View" links as external service usage: Office web viewer fetches the file over HTTPS, so only use View links for files intended for web publication.

Use this exact script:

```javascript
document.addEventListener('DOMContentLoaded', function() {
    var docLinks = document.querySelectorAll('a[href$=".pdf"], a[href$=".xlsx"], a[href$=".xls"], a[href$=".xlsm"], a[href$=".doc"], a[href$=".docx"]');
    docLinks.forEach(function(link) {
        link.setAttribute('target', '_blank');
        link.setAttribute('rel', 'noopener noreferrer');
    });

    var officeViewLinks = document.querySelectorAll('a[data-office-file]');
    var isWebContext = /^(http|https):$/.test(window.location.protocol);
    officeViewLinks.forEach(function(link) {
        var file = link.getAttribute('data-office-file');
        if (!file) return;

        if (isWebContext) {
            var absoluteUrl = new URL(file, window.location.href).href;
            var officeViewerUrl = 'https://view.officeapps.live.com/op/view.aspx?src=' + encodeURIComponent(absoluteUrl);
            link.setAttribute('href', officeViewerUrl);
        } else {
            // Local file preview: keep direct file URL as fallback.
            link.setAttribute('href', file);
        }
    });
});
```

When rendering Word/Excel links in the HTML body, use this structure (file name shown as example):

```html
<a data-office-file="Assessments May 2026.xlsx" href="Assessments May 2026.xlsx">Assessments May 2026.xlsx</a>
<span class="doc-actions">(
  <a data-office-file="Assessments May 2026.xlsx" href="Assessments May 2026.xlsx">View</a> |
  <a href="Assessments May 2026.xlsx" download>Download</a>
)</span>
```

### Step 12: AI-Generated Disclaimer

Include a prominent disclaimer immediately after the header information block stating that:
- This summary was generated by artificial intelligence and may contain mistakes, omissions, and characterizations that are not correct or appropriate.
- It does not take the place of the official documents, which are assumed to have been fully read.
- It is simply a tool for navigating meeting resources during the meeting.

### Step 13: Version Number and Changelog

Add a version number at the top of the document above the header.
If an existing version of the summary document exists, increment the document version and check the sha256 hashes of the files that were inputs for it and update as required. If the checksums have changed, include a note that the document changed in the changelog for this version. (Don't attempt to infer what has changed within the documents themselves.)

### Step 14: Document Hash List

For each document that is referenced or used in the report, include a list and sha256 checksum of the documents.

> Note: if Step 0 modified a PDF in place (added an OCR layer), its hash will differ from any prior version's record. Include a changelog entry noting "OCR text layer embedded" for those files so the hash delta is explained.

### Step 15: Attribution Footer

Include a centered, muted footer noting the tool used to compile the report.

### Step 16: Publish to FTP (opt-in)

Publishing is **never automatic**. The user may want to process the meeting locally only and skip the upload entirely.

1. After `index.html` is generated and the user has reviewed it, ask explicitly:
   > "Would you like me to upload this to the web (FTP)?"
   If they say no, stop here — the local file is the deliverable.
2. If they say yes, check that `<toolkit>/tools/ftp_config.json` exists. If not:
   - Read `<toolkit>/tools/ftp_config.example.json` for the schema.
   - Walk the user through creating a real config in the toolkit folder (one config covers every meeting). Ask for their server URL; suggest leaving `password` empty so it is prompted at run time; write the file at `<toolkit>/tools/ftp_config.json`.
3. Run the uploader, pointing it at the meeting folder and passing the resolved meeting date:
   ```
   python <toolkit>/tools/upload_to_ftp.py --folder <meeting> --date YYYY-MM-DD
   ```
   - `--folder` tells the uploader where `index.html` lives (it would otherwise look in the cwd).
   - Always pass `--date` based on the meeting date you resolved in Step 1 #9 — not necessarily the folder name. The script's folder-name auto-detect is a fallback only.
   - The script will prompt for any missing username/password.
   - It prefers FTPS. If the server's certificate fails verification, it shows the certificate details and asks the user to confirm trust; trusted fingerprints get pinned in the config so the user is not re-prompted next month.
   - If the server does not speak TLS at all, it warns and asks the user to confirm a plain-FTP fallback.
   - **The script asks "Proceed with upload?" once it has connected, logged in, and resolved the remote path.** This is a second, deliberate confirmation right before any bytes are sent. Let the user answer it themselves — do not pass `--yes` unless the user has already explicitly approved the upload to that specific URL in the current conversation.
   - **After uploading `index.html` the script also uploads every local document the HTML references** (PDFs, XLSX, images, OCR sidecars, etc.) so links resolve when someone visits the live page. Files outside the meeting folder, files in subdirectories, external URLs (`http://`, `mailto:`, etc.), the credential config, and (without confirmation) toolkit files are excluded. If a document is in the folder but deliberately *not* linked from the HTML — e.g. confidential supporting material referred to the Deputy Clerk — it will **not** be uploaded; that's the intended way to keep something local-only.
   - Pass `--only-html` if the user wants to push a minor HTML edit without re-uploading every PDF.
4. On success the script prints how many referenced files were uploaded (and any skipped or failed), then the public URL (if `public_url_template` is set in the config). Share that URL with the user.

If the upload step fails for permission, network, or credential reasons, surface the script's error message to the user verbatim — do not retry blindly.

---

## Critical Requirements (from refinement process)

1. **Docket PDF link** goes at docket item 2 (adoption point), NOT above the docket list.
2. **Stated Hour items** must include the scheduled time displayed prominently.
3. **Grant amounts** must be read from the application document itself — distinguish between the PCC grant amount allowed (e.g., $25,000–$70,000) and the total project cost / total funding sought from all sources. Do NOT conflate these.
4. **REFER table** must correctly show each item referred to the appropriate body. Do not create separate rows for the body — show the sender and what is being referred to them.
5. **All document links** must open in new tabs.
6. **Key issues** are placed inline at relevant sections, not in a separate end-of-document section.
7. **Supporting Documents table** at the bottom lists all files and their docket/report matches.
8. The output is a **single self-contained HTML file**; external viewer URLs are allowed only for Word/Excel **View** links (no file conversion).
9. **AI-Generated Disclaimer** must appear prominently after the header information block, warning that the summary may contain mistakes, omissions, and incorrect characterizations, and does not replace the official documents.
10. **Scanned PDFs are OCR'd in place** (or alongside) as the very first step so all later parsing is text-based.
11. Include a visible top-of-page **Back** link that points to `../` (relative parent directory).
12. Word/Excel document references must provide both **View** and **Download** links, with document-title links defaulting to **View**.

---

## File Naming Convention

- Output: `index.html`, written into the **meeting folder** (the folder the user pointed you at — not the toolkit folder).
- OCR'd searchable copies of scanned PDFs (if not in-place): `<original name> - searchable.pdf` in the meeting folder, next to the original scan.
- Image text sidecars: `<image stem>_ocr.txt` in the meeting folder, next to the original image (e.g. `Poster.png` → `Poster_ocr.txt`). UTF-8.
- Do not write any other files into the meeting folder. Scratch files (e.g. `pages.json` for OCR overlay) go in the toolkit folder or `%TEMP%` and must be cleaned up before the run ends.
