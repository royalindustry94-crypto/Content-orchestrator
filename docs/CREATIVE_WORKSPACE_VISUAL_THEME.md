# Creative Workspace visual theme

**Status:** Visual-only Founder Preview restyle.  
**Stock reference:** Adobe Stock asset `#235999682` (watermarked preview supplied as a mood board).  
**Implementation:** original CSS/SVG in `apps/web`. No purchased template files, licence keys, credentials, or proprietary rasters are in this repository.

## Licence confirmation

The supplied reference is a **watermarked Adobe Stock preview**. A watermarked comp is for evaluation only and is **not** a production licence.

This change does **not** copy or redistribute that file. The dark neon dashboard language (charcoal ground, pink-to-orange actions, cyan spend chrome, glass cards, dock) was recreated as original application chrome.

If the Founder later holds an Adobe Stock licence for `#235999682`:

| Question | Standard License (Adobe Stock Product Specific Terms) |
|---|---|
| Modification allowed? | Yes, for non-editorial works |
| Commercial use in a website or app? | Yes. Audience caps do not apply to websites, social, or mobile apps |
| Upload the purchased file to public GitHub? | **No.** Stand-alone redistribution of the Work is prohibited |
| Use the Work as an electronic design template? | **No.** Standard License §3.1(B)(3) forbids incorporating the Work into an electronic template |

This repository therefore ships only converted app code. Keep any purchased download, invoice, or licence key off public GitHub.

## Visual template gallery

`#/template` (also “View neon dashboard template” on sign-in) opens an original five-phone kit on a dark grid — Dashboard, Stats, Transfer, Planning, History — locked to the mood-board hexes: charcoal `#121212`, panel `#1C1C21`, magenta `#FF007A`, orange `#FF9A00`, cyan `#00D9FF`, lime `#B8F54A`. Sample figures such as `$1,490.00` are decorative template chrome and never appear on Home Bankroll.

## Public visual preview

Vercel preview builds set `VITE_CREATIVE_PREVIEW=1`. That build installs a **browser-only** fetch adapter so the themed UI can be opened without a managed database. The adapter is inert in normal Docker/`AUTH_MODE=local` builds.

Preview rules:

- Sign-in accepts any email/password and opens a labeled disposable workspace.
- Home Bankroll remains **Not connected**.
- Human Review Approve/Reject updates only this browser tab.
- Operator actions (emergency stop, DLQ clear) return `ok: false` and change nothing live.
- A persistent banner states that the preview is disposable fixture data.

## Controls preserved

- Human Review Gate approve/reject and version binding are unchanged.
- Workspace switcher and membership-scoped API calls are unchanged.
- Spend reads still come from workspace spend/cost-control endpoints; caps remain fail-closed.
- Home Bankroll still renders **Not connected** until a financial source exists. No synthetic `$0`, profit, or completion percentage was added.
- Home uses a 2×2 ring layout (Revenue, Spending, Net profit, Profit margin) with 3D–1Y range pills. Changing a range does not invent a series.
