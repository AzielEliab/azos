# azos download tracker

Isolated Worker `azos-download-tracker`. Project `azos`.
KV namespace `AZOS_DOWNLOADS` bound as `DOWNLOADS`.
Does **not** 302 to GitHub on `/download`. Serves gzip via `ASSETS.fetch`,
`Cache-Control: private, no-store`.

GET `/` increments a **page-view** counter (separate from downloads).
GET `/download` increments **downloads**.
`/v1` never increments DOWNLOADS KV.
GET `/install.sh` one-click install (does not increment; script curls `/download`).
GET `/v1/skill` returns skill markdown (`text/markdown`). Does not increment views or downloads.

Hosted `/v1` is the ethics-coded remote shell (`/v1/session`, `/v1/exec`).
Status is read-only. `/v1` never increments DOWNLOADS.

Host: https://azos-download-tracker.vibelock.workers.dev
