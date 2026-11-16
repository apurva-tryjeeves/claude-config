# Release page template

## Canonical source

| Item | Value |
|---|---|
| Parent hierarchy | Engineering > Releases > `<Year> Releases` > `Q<N>-<Year> Releases` > `<Month> <Year> Releases` |
| Releases root page ID | `e0cf7ecb7f0a47bab606f0db558eb8e6` |

Each month page holds its own `(template)` child, so fetch the month page for
the release's date and duplicate the `(template)` child found there.

## Month page IDs

Check this table first for the release month. When its row is present, fetch
that page ID directly. When it is absent, resolve it by fetching the quarter
page (or the Releases root) and following the `<Month> <Year> Releases` child,
then record the row (see the skill's "Record what you resolve").

| Month | Month page ID | Quarter page ID | `(template)` child ID |
|---|---|---|---|
| September 2026 | `3c31edd5ce8c80559cb1c9fe9afaf471` | `3881edd5ce8c80bdae2ad2be6c7d91fc` | `3df1edd5ce8c800483f3c8fdd0a64eaa` |
| November 2026 | `3eb1edd5ce8c8021acc2c66cb0c7ca26` | `3c31edd5ce8c802399ffc8dc0171812c` | `3eb1edd5ce8c80a791edca1f9098eee2` |

The `(template)` child is re-created per month, so confirm the ID in the table
still resolves to a `(template)` page before duplicating it, and refresh the
row when a month ships a new one.

## Page naming

| Release type | Title format | Example |
|---|---|---|
| Weekly release | `DD-Mon-YYYY - Release` | `23-Sep-2026 - Release` |
| Hotfix | `DD-Mon-YYYY - Hotfix Release (<services>)` | `17-Sep-2026 - Hotfix Release (accounting, jeeves-web)` |
| Hotfix with a ticket | `DD-Mon-YYYY - [HOTFIX] [<repo>] [<context>] (<TICKET>)` | `01-Sep-2026 - [HOTFIX] [backend] [exchange-rates] (WAL-5940)` |

The month abbreviation is three letters (`Sep`), and the day is zero-padded
(`04-Sep-2026`). Hotfix titles vary in the wild — match the shape the release
captain asks for, and default to the `Hotfix Release (<services>)` form.

For a hotfix touching several repos:

- List every repo in the parens, comma-separated.
- Shorten each to the recognisable part of the repo name — `accounting` for
  `accounting-service`, `jeeves-web` as-is.
- Keep that set identical to the repos in the Tickets table and the repos
  seeded in the deployment-status table.
- File the page under the same `<Month> <Year> Releases` parent that weekly
  releases use.

## Fill guide

| Section | What goes in it |
|---|---|
| Release Info › Release captain | `@`-mention of the captain, then ` - co-captain @<name>` when there is one. A hotfix usually runs with the single captain who wrote the fix |
| Release Info › Devops | Left blank until DevOps is assigned |
| Release Info › QA | Left empty — clear the mentions the template pre-fills |
| Release Info › Release Status | One of `NEXT WEEK`, `IN PROGRESS`, `RELEASED`. A weekly page scaffolded ahead of its date opens at `NEXT WEEK`; a hotfix page created on the day it ships opens at `IN PROGRESS` |
| Release Info › Environment | The Pre-Prod block below, carried over unchanged |
| Release Info › Release Playbook, Approved by | Left blank for the captain to fill |
| Tickets table | One row per ticket — see [Tickets table row](#tickets-table-row) below |
| Issues identified by QA | Left empty; QA fills it during Pre-Prod testing |
| Deployment status table | One row per repository, pre-seeded with the full list from the [fallback body](#fallback-body). At creation, set every repo named in the Tickets table to `PENDING` on an orange background and leave every other row blank; move each to `RELEASED` on a green background as it deploys |
| Deployment instructions | Left empty unless the release needs manual steps |
| SCRIPT TO BE EXECUTED POST DEPLOY | An empty `javascript` code block, filled when a post-deploy script is needed |
| SECRETS TO BE ADDED | The ⚠️ secrets callout from the [fallback body](#fallback-body), then bullets naming each secret. Put a Keeper reference here, never a secret value |

## Tickets table row

| Column | What goes in the cell |
|---|---|
| Developer | `@`-mention of the developer who owns the change |
| POD name | The POD in inline code, e.g. `` `Money` `` — see [POD names](#pod-names) below |
| Ticket | The GitHub pull-request link as an `external_object_instance` — see [Ticket cells](#ticket-cells) below |
| Changed Repository | The full canonical repo name in inline code — `` `accounting-service` ``, `` `product-account-service` `` — spelled as the deployment-status table spells it, even where the page title shortens it |
| QA owner on Pre Prod | `@`-mention of the QA owner; on a hotfix this is commonly the developer themself |
| Notes | Left blank at creation. The release captain fills it during testing when there is something to record, such as the dev env the change was verified on (`Dev-11`, `Tested on dev-03`) |

One row per ticket, and a ticket touching two repos gets one row per repo
rather than two repos stacked in one cell. Unused rows from the template can
stay in place — they read as blank.

### Ticket cells

A Ticket cell holds the pull request as an `external_object_instance` — the
native GitHub link preview, which renders the live PR title, number and merge
state in the cell. Write the cell by passing the bare PR URL
(`https://github.com/JeevesInc/<repo>/pull/<number>`) and omitting
`preserve_internal_links`, which lets Notion convert the link to a connected
GitHub resource into the mention on its own.

Reading the page back with `notion-fetch` returns each of these cells as:

```html
<unknown_mention url="https://app.notion.com/p/<page-id>#<block-id>" alt="external_object_instance"/>
```

That URL is the object instance's own block address inside the release page,
not the pull-request URL — so a fetch confirms a PR is linked in that row
without revealing which one. When the actual PR URLs are needed, collect them
from the release captain or from GitHub rather than from the page.

## Defaults to carry over

### Notion user IDs

Lookup for the per-ticket "QA owner on Pre Prod" mention. Record a new person
the first time their ID is resolved (see the skill's "Record what you
resolve").

| Name | Email | Notion user ID |
|---|---|---|
| Pavaneswara Guptha Nsr | pavan@tryjeeves.com | `5bd7ff63-1260-4926-b199-8288bc1a222b` |
| Keshav Gangopalwad | keshav@tryjeeves.com | `5d644217-8efe-4a75-95d2-bf64aa4c8dcc` |
| Bharat Ahuja | bharat@tryjeeves.com | `5c443944-9cd2-4163-8373-c0d5d566ca05` |
| Shikha Singhal | shikha.singhal@tryjeeves.com | `311d872b-594c-8113-92a8-000299d8b4bd` |

### Release captains

Resolve an unlisted captain with `notion-get-users`, then record their row (see
the skill's "Record what you resolve").

| Name | Email | Notion user ID |
|---|---|---|
| Apurva Singh | apurva@tryjeeves.com | `43e7ac5d-b5fa-4e08-9515-d771a98b5b8d` |

### POD names

Seen so far: `Money`, `Megapod`, `Payments`, `Wallet`. Record each new POD the
first time it appears in a Tickets table (see the skill's "Record what you
resolve").

### Pre-Prod environment

| Surface | URL |
|---|---|
| API | http://preprod.test.jeev.es/ |
| Frontend | https://preprod.dev.tryjeeves.com/client/web/login |
| CMS | http://admin-preprod.dev.jeeves.vpn/ |

### Repository list and callouts

The [fallback body](#fallback-body) holds the full repository list for the
deployment-status table, the 💡 UTV coordination callout (directly under the
Tickets table) and the ⚠️ secrets callout (at the foot of the page); carry each
over from there as written.

In the repository list, rows carry a GitHub link where the template has one and
plain text where it does not (`open-banking`, `expense-management-service`,
`trunarrative service`, `lumen engine service`). Links point at
`https://github.com/JeevesInc/<repo>`, with two different link targets:

- `flow (jumanji)` → `jumanji`
- `ai-service` → `jeeves-ai`

The first six rows (`backend`, `frontend`, `cms`, `payment-transfer-service`,
`banking-service`, `stp-transfer-service`) carry bold link text.

## Fallback body

Use this only when the month page carries no `(template)` child. It reproduces
every section in order; the Release Info table arrives as a plain two-column
table rather than Notion's header-column layout, and column widths come out at
Notion's defaults.

````markdown
### Release Info

| | |
|---|---|
| Release captain | <mention-user url="user://CAPTAIN-UUID"/> |
| Devops | |
| QA | |
| Release Status | NEXT WEEK |
| | |
| Environment | `Pre-Prod:`<br>API: [http://preprod.test.jeev.es/](http://preprod.test.jeev.es/)<br>Frontend: [https://preprod.dev.tryjeeves.com/client/web/login](https://preprod.dev.tryjeeves.com/client/web/login)<br>CMS: [http://admin-preprod.dev.jeeves.vpn/](http://admin-preprod.dev.jeeves.vpn/) |
| Release Playbook | |
| Approved by | |
| | |

# Tickets

| Developer | POD name | **Ticket** | Changed Repository | QA owner on Pre Prod | Notes |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |

<callout icon="💡" color="gray_bg">
Automated Release process for UTV(Universal Transaction View) is in-progress so till the time,<br>Release captain has to coordinate with the PR owner of `dbt-transform` and `universal-transactions-glue` to make sure the changes of this two services are released by the PR owners on production at-least a one day before the regular release day, The reason is this service changes need the redshift data reload which can take the time(**~45min**) and during that time or before if we release dependent PR of `transactions-service` then the UTV page UI can break.
</callout>

### Issues identified by QA

### Deployment status For Each Service (Example: PENDING, RELEASED)

do not add "no release" in what is not part of the release, blank ===(=) no release

| Repositories | Deployment Status | Notes |
|---|---|---|
| [**backend**](https://github.com/JeevesInc/backend) | | |
| [**frontend**](https://github.com/JeevesInc/frontend) | | |
| [**cms**](https://github.com/JeevesInc/cms) | | |
| [**payment-transfer-service**](https://github.com/JeevesInc/payment-transfer-service) | | |
| [**banking-service**](https://github.com/JeevesInc/banking-service) | | |
| [**stp-transfer-service**](https://github.com/JeevesInc/stp-transfer-service) | | |
| open-banking | | |
| expense-management-service | | |
| trunarrative service | | |
| lumen engine service | | |
| [cashback-service](https://github.com/JeevesInc/cashback-service) | | |
| [jeeves-drive](https://github.com/JeevesInc/jeeves-drive) | | |
| [authentication-service](https://github.com/JeevesInc/authentication-service) | | |
| [credit-statements-service](https://github.com/JeevesInc/credit-statements-service) | | |
| [flow (jumanji)](https://github.com/JeevesInc/jumanji) | | |
| [jeeves-web](https://github.com/JeevesInc/jeeves-web) | | |
| [product-account-service](https://github.com/JeevesInc/product-account-service) | | |
| [wallet-service](https://github.com/JeevesInc/wallet-service) | | |
| [cards-service](https://github.com/JeevesInc/cards-service) | | |
| [billpay-service](https://github.com/JeevesInc/billpay-service) | | |
| [ocr-service](https://github.com/JeevesInc/ocr-service) | | |
| [accounting-service](https://github.com/JeevesInc/accounting-service) | | |
| [notification-service](https://github.com/JeevesInc/notification-service) | | |
| [underwriting-service](https://github.com/JeevesInc/underwriting-service) | | |
| [universal-transactions-glue](https://github.com/JeevesInc/universal-transactions-glue) | | |
| [dbt-transform](https://github.com/JeevesInc/dbt-transform) | | |
| [transactions-service](https://github.com/JeevesInc/transactions-service) | | |
| [pricing-engine](https://github.com/JeevesInc/pricing-engine) | | |
| [ap-data-source-connector](https://github.com/JeevesInc/ap-data-source-connector) | | |
| [risk-service](https://github.com/JeevesInc/risk-service) | | |
| [recon-service](https://github.com/JeevesInc/recon-service) | | |
| [cards-gateway-service](https://github.com/JeevesInc/cards-gateway-service) | | |
| [btg-integration](https://github.com/JeevesInc/btg-integration) | | |
| [ai-service](https://github.com/JeevesInc/jeeves-ai) | | |
| [credit-service](https://github.com/JeevesInc/credit-service) | | |

Docker image tags used for the release are available here:<br>[https://github.com/JeevesInc/infra-deploy-config-production/blob/master/us-east-1/helm-releases/jeeves-production.yml](https://github.com/JeevesInc/infra-deploy-config-production/blob/master/us-east-1/helm-releases/jeeves-production.yml)

### Deployment instructions

### SCRIPT TO BE EXECUTED POST DEPLOY

```javascript

```

**SECRETS TO BE ADDED**

<callout icon="⚠️" color="gray_bg">
**DO NOT** paste secrets here.
Store them in Keeper, then put a reference here.
</callout>

- item-1
- item-2
````

## Downstream

Once the page exists and its Tickets table is filled, the `release-notify`
skill reads the "Changed Repository" column from it to draft the Slack release
updates.
