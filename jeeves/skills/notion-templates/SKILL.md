---
name: notion-templates
description: Create Jeeves Notion pages from the stored template library — currently the weekly/hotfix release page under Engineering > Releases. Trigger when asked to create, set up, or scaffold a Notion release page (or another catalogued template) for a given date, Also holds the default formatting (heading icons, callouts, toggles) for any Notion page written from markdown — load it before creating or editing one.
---

# Jeeves Notion Templates

A catalogue of Jeeves Notion page templates plus the steps to stamp out a new
page from one. More templates land here over time — see
[Add a new template](#add-a-new-template).

## Template catalogue

| Template | Reference file | Creates |
|---|---|---|
| Release page | `references/release-page.md` | A weekly or hotfix release page under Engineering > Releases |

## Pick the template

When the request names a template outright ("create next week's release
page"), use it. When several could fit, narrow by the words in the request; ask
with `AskUserQuestion` while four or fewer remain, and print the catalogue as a
numbered list in chat for the user to pick by name or number once it grows past
that.

Read the chosen template's reference file before creating anything — it holds
the page naming convention, the parent location, the section-by-section fill
guide, and the fallback body.

## Create the page

Duplicate the live Notion template page. It carries the fixtures that survive
only as native Notion blocks: header-column tables, fixed column widths,
callout background colours, and the embed block.

1. Resolve the month page from the reference file's month-ID table, fetch it
   with `notion-fetch`, and pick the child page whose title ends in
   `(template)`. When the lookup was resolved live, record the month's row
   (see "Record what you resolve" below).
2. Duplicate it with `notion-duplicate-page`. Duplication finishes
   asynchronously, so re-fetch the new page until its content is present
   before editing it.
3. Rename it to the real page title with `notion-update-page` /
   `update_properties`, following the naming convention in the reference file.
4. Fill in the values with `notion-update-page` / `update_content`, using
   `old_str`/`new_str` pairs scoped tightly enough to match once. Empty the
   Release Info › QA cell, which the template pre-fills with mentions — release
   pages carry no default QA.

When the month page carries a `(template)` child, that path is complete. When
it carries none, build the page from the reference file's fallback body:

- Read the `notion://docs/enhanced-markdown-spec` resource — it is the spec
  for the Notion-flavored markdown those bodies use, including the
  `<mention-user url="user://UUID"/>` syntax the `@`-mentions need.
- Create the page with `notion-create-pages`, passing the month page's
  `page_id` as the parent.
- Tell the release captain that column widths and the Release Info table's
  header-column layout arrive at Notion defaults, so they can set those by
  hand or seed a `(template)` child for next month.

## Confirm before filling in people and dates

Confirm with the user, before the page is created:

- The page date and release type (weekly release vs hotfix) — these set the
  title.
- The release captain, and the co-captain when there is one.
- The repos in the release. For a hotfix these also name the page, e.g.
  `17-Sep-2026 - Hotfix Release (accounting, jeeves-web)`.
- The tickets: developer, POD, pull-request link, repo, and QA owner per row.

Carry over every other default from the reference file as-is — the Pre-Prod
environment block, the UTV callout, the full repository list.

### Record what you resolve

The reference file's month page IDs, Notion user IDs, and POD names grow with
use. Read the copy in your clone of the plugin
(`${JEEVES_PLUGIN_SRC:-$HOME/github/apurva-tryjeeves/claude-config}/jeeves/skills/notion-templates/references/release-page.md`)
when it exists — it carries rows not yet released — else this skill's own
copy, and check it before resolving anything live. Record a newly confirmed
month page, user ID, or POD name in the clone's copy, leave the change
uncommitted, and tell the user it is ready to review and push. When the clone
is missing, report the value instead.

Keep the title, the Tickets table, and the deployment-status table naming the
same set of repos: each repo in the Tickets table starts at `PENDING` on an
orange background in the deployment-status table, and every other row keeps an
empty status cell — blank is how the page says a service sits out the release.

## Format pages built from markdown

Apply this by default to every page body written as Notion-flavored markdown —
the fallback body, a new template's body, a write-up page — without waiting to
be asked. A duplicated `(template)` page keeps the formatting it already has.

| Content | Element |
| --- | --- |
| Page identity | An emoji `icon` on `notion-create-pages` |
| Top of page | A `gray_bg` `<callout>` with a one-line purpose, then `<table_of_contents/>` |
| Section headings | One leading emoji per `##` / `###` that names the content (`## 🧪 Safety net`); numbered headings keep the number first (`## 1. 📋 TL;DR`) |
| Warning or priority groups | A sub-heading carrying a signal icon — `### 🚨 Money safety`, `### 🔑 Decides order of work` |
| Long code, before/after sketches | A `<toggle heading="h3">` block: the title on the line after the opening tag, a blank line, then the children unindented, code in fenced blocks, and `</toggle>` right after the last child |
| Diagrams | A `mermaid` code block |
| Repeating columns | `<table header-row="true">` |
| Questions and follow-ups | `- [ ]` checkboxes |

To bring an existing page up to this style, change markup alone — heading
icons, callouts, toggles — and keep every word. Patch each heading line
with `update_content`, using the exact heading text as `old_str`.

Write through the Notion MCP with these behaviours in mind:

- Wrap filenames and `file:line` references in inline code — bare `CLAUDE.md`
  or `File:line` in text is auto-linked (`[CLAUDE.md](http://CLAUDE.md)`).
- In a table cell, join two inline-code spans with "and" or "plus": a literal
  `` `a` + `b` `` renders as `` `a` • `b` ``, and `update_content` cannot
  correct it afterwards.
- Escape `< > { } | ~ $ ^` in plain text; code spans stay literal. A code span
  cannot hold a backtick, so rephrase instead (e.g. "the template literal
  `balance - ${x}`").
- Keep a `<page url="…">` tag for every child page in a `replace_content`
  body — a child left out is deleted.
- Write each sub-section as a `### <emoji> …` header: the doc-format-gate
  hook rejects a bold-only line such as `**Pagination**` standing in for a
  header, and any `##`/`###` header without a leading emoji.
- Send a page over about 20k characters as a short `notion-create-pages`
  body (callout, table of contents, first sections), then append each later
  `##` section with `insert_content` at `position: end`.
- A `notion-fetch` result over about 50k characters is saved to a file; verify
  edits by parsing that file (`json.loads(...)['text']`) rather than reading it
  inline.

## Add a new template

To add the next template to this skill:

1. Fetch the page that is to become the template with `notion-fetch`.
2. Write `references/<template-name>.md` following the shape of
   `references/release-page.md`: canonical source page, parent location, page
   naming, a section-by-section fill guide, the defaults worth carrying over,
   and a fallback markdown body.
3. Add a row to the catalogue table above.
4. Extend this skill's `description` frontmatter so the new template's
   trigger words reach the matcher.

## Reporting results

Report the created page's title, any field left for the user to fill in by
hand, and anything that needs their attention — a duplicate page already
existing for that date, or fixtures lost on the markdown fallback path. Leave
out a recap of the template's sections, usage examples, and closing offers.

End every run with the new page's Notion URL alone on the final line, after
any caveats, as a bare URL the terminal makes clickable:

```
https://app.notion.com/p/<page-id>
```
