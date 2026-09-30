# Prioritized authorized DeviantArt connector

Live OAuth authorization and authenticated identity lookup were **verified on 2026-09-30** after the operator personally authorized the provider permissions. A separately authorized, bounded own-gallery import was attempted but returned HTTP 400, `No supported images found`; it did not produce a dataset or start training. Offline `MockTransport` tests verify protocol/privacy/ingestion behavior using generated fixture pixels; they are not evidence of a successful live artwork import.

## Human setup

Use your existing account, not a second account. Open [developer app registration](https://www.deviantart.com/developers/register), sign in yourself and review the current API/developer terms. Register a **public** Authorization Code / OAuth 2.1 application with S256 PKCE. Whitelist exactly:

```text
http://127.0.0.1:8016/oauth/deviantart/callback
```

If your provider registration rejects loopback HTTP for your app type, do not bypass its restrictions; use an allowed provider redirect strategy after updating/testing the connector. Do not enter a client secret or password into this application or a public issue/chat. Only the public numeric client ID goes into Datasets & glossary → DeviantArt connector. Prepare authorization, follow the official provider link, and review the requested `basic browse user` scopes and every actual permission before deciding whether to authorize yourself.

Live inspection on 2026-09-30 verified a human-submitted public application registration with the loopback callback. Consent prompts for **both** `basic browse user` and `basic browse` advertised Sta.sh use/management in addition to username/public browsing. Removing `user` did not remove that advertised permission, and the official `whoami` reference identifies `basic` and `user` as required scopes. The connector therefore retains the identity-required scopes; it does not request explicit `stash`, `publish`, or `user.manage` scopes. This is **not proof of a read-only token grant**: the actual provider consent screen takes precedence over scope names and over this app's read-only API operations. Decline unless you accept all listed permissions and terms. In this validation, the operator personally accepted account-access permissions, then separately confirmed training rights and provider terms for a sample of at most 24 own-gallery entries. Registration, account access and training-rights confirmation are distinct steps.

Callback state is unpredictable, single-use and expires after ten minutes. PKCE proves possession of a private verifier. The token exchange is server-side over HTTPS; identity comes from `user/whoami`, not an operator-entered username. Credentials live only in process memory, are never logged/persisted/browser-stored, and expire within the provider's access-token lifetime. This version deliberately does not persist a refresh token. Restart/expiry requires browser authorization again.

## Explicit import, not permission inferred from account access

Select at most 96 entries (24 by default). Confirm **training rights for every entry** and that this use is permitted by provider terms. Gallery access is not proof of ownership/licensing of every component in an artwork. Known NoAI/opt-out fields are skipped; explicit AI-tool labels/tags are retained and quarantined. Unknown/absent labels are not proof of human-only origin. Review metadata before ordinary training.

Only the authenticated user's own gallery is visited; entries whose author differs fail validation. Mature entries, unavailable raster content and known opt-outs are skipped. Metadata descriptions become inert bounded text; titles, tags and artist are retained. Downloads use only approved HTTPS provider/CDN hosts, no bearer header at a CDN, no redirects/bypasses, raster format/byte/pixel caps and a five-minute import budget. Pagination must advance and entries must be unique. A failed import never publishes a partial dataset.

There is no favourites scraper, paywall/login bypass, arbitrary website crawler or automatic training. Forget Connection clears local credentials; revoke app permissions separately in DeviantArt's account settings if desired. Do not commit account artwork, private dataset manifests or tokens. The provider may change API responses/rate limits; a future live test must start with a bounded authorized sample and record failures honestly.

## Observed live result and next input

The successful callback and authenticated status verified token exchange and account identity. The subsequent import took approximately 0.47 seconds and returned `No supported images found`. The own-gallery browser view showed one application listing rather than a collection of training images. No import staging directories remained, and no dataset for this attempt was registered. The error itself does not expose provider item/skip counts, so it cannot distinguish an empty API response from an entirely unsupported or excluded sample; no specific exclusion reason is claimed.

This is a data-availability boundary, not a successful account-artwork training demonstration. Supply an owned, permitted raster-image folder/ZIP with descriptive captions, or eligible own-gallery artwork, to test that training path. Favourites and account access do not establish training rights to other artists' work. Keep AI-origin entries quarantined and respect known opt-outs. The separate 6,000-step synthetic custom model was genuinely trained and used for browser generation; see [validation](reports/validation.md). No account artwork, identifiers or model weights are included in public evidence.

Protocol sources: [authentication](https://deviantart.readme.io/docs/authentication), [gallery/all](https://deviantart.readme.io/reference/gallery_all), [deviation metadata](https://deviantart.readme.io/reference/deviation_metadata), [whoami](https://deviantart.readme.io/reference/user_whoami), [getting started/API terms](https://deviantart.readme.io/docs/getting-started).
