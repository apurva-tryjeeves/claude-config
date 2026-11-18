---
name: notion-templates
description: Create Jeeves Notion pages from the template library: the weekly or hotfix release page under Engineering > Releases, and design docs. Trigger when asked to create or scaffold a release page, a design doc or another catalogued Notion page, and load before writing any Notion page from markdown for its default formatting.
---

# Jeeves Notion Templates

A catalogue of Jeeves Notion page templates plus the steps to stamp out a new
page from one. More templates land here over time — see
[Add a new template](#add-a-new-template).

## Template catalogue

| Template | Reference file | Creates |
|---|---|---|
| Release page | `references/release-page.md` | A weekly or hotfix release page under Engineering > Releases |
| Design doc | `references/design-doc.md` | A design doc under the owning team's technical-docs page |

## Pick the template

When the request names a template outright ("create next week's release
page"), use it. When several could fit, narrow by the words in the request; ask
with `AskUserQuestion` while four or fewer remain, and print the catalogue as a
numbered list in chat for the user to pick by name or number once it grows past
that.

Read the chosen template's reference file before creating anything — it holds
the page naming convention, the parent location, the section-by-section fill
guide, and the fallback body.

## Confirm before filling in people and dates

Show the user these values, then wait for the user's yes before creating the
page:

- The page date and release type (weekly release vs hotfix) — these set the
  title.
- The release captain, and the co-captain when there is one.
- The repos in the release. For a hotfix these also name the page, e.g.
  `17-Sep-2026 - Hotfix Release (accounting, jeeves-web)`. The title, the
  Tickets table and the deployment-status table name this same set of repos;
  the reference file's fill guide says how each repo's status cell starts.
- The tickets: developer, POD, pull-request link, repo, and QA owner per row.

Carry over every other default from the reference file as-is — the Pre-Prod
environment block, the UTV callout, the full repository list.

### Record what you resolve

The reference file's month page IDs, Notion user IDs, and POD names grow with
use. Check `references/release-page.md` before resolving anything live, and
record a newly confirmed month page, user ID, or POD name in it, following
`${CLAUDE_PLUGIN_ROOT}/references/write-back.md`.

## Create the page

Duplicate the live Notion template page. It carries the fixtures that survive
only as native Notion blocks: header-column tables, fixed column widths,
callout background colours, and the embed block.

1. Resolve the month page from the reference file's month-ID table, fetch it
   with `notion-fetch`, and scan its children for a page with this release's
   date (and, for a hotfix, the same service) — someone else shipping that day
   may have created it. When one exists, show the user its title and URL, then
   wait for the user's choice of which page the release runs on. Otherwise
   pick the child page whose title ends in `(template)`. When the lookup was
   resolved live, record the month's row (see "Record what you resolve"
   above).
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

## Format pages built from markdown

Every page body written as Notion-flavored markdown — the fallback body, a new
template's body, a write-up page — gets heading icons, a purpose callout, a
table of contents and toggles for long code, and follows the Notion MCP's
escaping and size limits. Read `references/page-formatting.md` before writing
or restyling any such body.

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
