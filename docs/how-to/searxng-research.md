# Online research: SearXNG and legacy Google

Preferred → fallback order (matches the control-plane research path):

1. **SearXNG** when `AXON_WATCH_SEARXNG_URL` is set (recommended local path)
2. **Google Custom Search** (legacy) when `AXON_WATCH_GOOGLE_CSE_API_KEY` and
   `AXON_WATCH_GOOGLE_CSE_CX` are set (DashPro aliases `EXPO_PUBLIC_GOOGLE_CSE_*`
   still work)
3. **DuckDuckGo Instant** as the last resort (often sparse)

## Preferred: local SearXNG

Start the local instance and point research at it:

```bash
./scripts/dev/run-searxng.sh
# then set AXON_WATCH_SEARXNG_URL=http://127.0.0.1:8080 in .env (or vault)
```

`config/searxng/settings.yml` must keep `json` under `search.formats` (SearXNG
returns **403** for `format=json` when JSON is disabled). Do not rely on public
instances that disable the JSON API. After a successful search, capability /
receipts should show `provider: searxng`.

SearXNG Search API:
https://docs.searxng.org/dev/search_api.html

## Legacy: Google Custom Search 403

If SearXNG is not configured and live search reports **403 — this project does
not have access to Custom Search JSON API** (reason often `forbidden`):

1. Open [Google Cloud Console → APIs & Services → Library](https://console.cloud.google.com/apis/library)
   for the project that owns that API key (DashPro’s Firebase/Cloud project is
   often `edudashpro`).
2. Find **Custom Search API** (`customsearch.googleapis.com`) and click **Enable**.
3. In **APIs & Services → Enabled APIs / Dashboard**, confirm Custom Search API
   is listed as enabled for that same project (not a different Cloud project).
4. Confirm the Programmable Search Engine ID (`cx`) still matches the engine in
   the [Programmable Search control panel](https://programmablesearchengine.google.com/).
5. Retry a search, or prefer local SearXNG instead of unblocking Google.

If Enable was already clicked and the 403 persists, Google’s docs state the
Custom Search JSON API is **closed to new customers** (existing customers only,
through 2027). In that case, enabling the library toggle cannot grant access;
use SearXNG (`./scripts/dev/run-searxng.sh`) rather than creating a new Google
search project for Axon-X.

Official Google overview (legacy path only):
https://developers.google.com/custom-search/v1/overview
