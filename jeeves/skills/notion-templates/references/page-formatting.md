# Format pages built from markdown

Apply this by default to every page body written as Notion-flavored markdown —
the fallback body, a new template's body, a write-up page — without waiting to
be asked. A duplicated `(template)` page keeps the formatting it already has.

| Content | Element |
| --- | --- |
| Page identity | An emoji `icon` on `notion-create-pages` |
| Top of page | A `gray_bg` `<callout>` with a one-line purpose, then `<table-of-contents />` |
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
- Write each sub-section as a `### <emoji> …` header, with a leading emoji on
  every `##` and `###` header, in place of a bold-only line such as
  `**Pagination**`.
- Send a page over about 20k characters as a short `notion-create-pages`
  body (callout, table of contents, first sections), then append each later
  `##` section with `insert_content` at `position: end`.
- A `notion-fetch` result over about 50k characters is saved to a file; verify
  edits by parsing that file (`json.loads(...)['text']`) rather than reading it
  inline.

