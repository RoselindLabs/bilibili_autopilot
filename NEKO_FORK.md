# Neko Bilibili maintenance fork

Upstream: [namchengwuqiu/bilibili_autopilot](https://github.com/namchengwuqiu/bilibili_autopilot),
starting from `bf362a6364421a7c6ac3fcf90ad62f47a227d9a1` (0.7.1). Original MIT LICENSE,
author attribution and history remain intact. Fork contributions: NekoLaska.

0.9.1 integrates upstream `v0.8.7`, commit
`026ab4f5cdd7f13f967772a6b298ce3b7c9271ce` (2026-11-04), including v0.8.3–v0.8.6.
0.9.0 previously integrated `v0.8.0` / `0f15ff0ae44036a772cf3206a4faad36495ed162`.
The upstream version overlaps our original 0.8.0; maintenance versions remain independent.
Comment candidates now use interest-only screening during cooldown/quota waits and
independent selection before a fresh read/review. This is Bilibili comment scheduling,
not a second QQ proactive trigger. Richer direct-share copy applies only outside
ecosystem mode. No dependency, config-key or table-schema changes; only provable
legacy capacity evictions gain the `evicted` label. Preserve current publication
settings, credentials, every send/unknown ledger and discovery tombstone on updates.

0.9.1 adds account-scoped activity queries and per-message fact handoff, explicit
browse-selection limits, redacted staged login diagnostics, and continued browsing
while unknown comments/replies block publication. Already-paused instances still
need an explicit start; unknown records are never acknowledged or replayed automatically.
History access uses the existing provider QQ group/account grants, including real
shared-Focus routing; private/unlisted/ambiguous sessions fail closed. This read-only
history tool does not consume or bypass the signed proactive discovery protocol.
Upstream's experimental NapCat mini-app card is deliberately excluded: no card API,
send.custom/api.call permissions, cover fields or card-schema migration. Config format
remains 0.2.0; business keys, defaults and SQLite schema are unchanged. Explicit host
compatibility is 1.3.10–1.3.19; the inherited same-SHA CI/package policy is retained.

- Same `local.bilibili-autopilot` ID, runtime directory, credentials and original
  comment/reply/unknown ledgers. Replace the existing directory; never run two copies.
- Comments and reply following retain upstream behavior. Publication is independently
  controlled by `comment.publish_enabled`; migration never enables it.
- Optional `ecosystem.enabled` records automatic, successfully read, interesting
  videos without another model call. Manual preview is not an automatic read.
- Signed `discovery_v1@1` supplies optional metadata to Neko Proactive's existing
  trigger, limited to both sides' group grants. Private targets are not implicit.
- Handoffs are at most once per Bilibili UID/video/QQ session. `shown` means only
  prepared request context, not model adoption or QQ delivery. Unknowns never replay.
- Ecosystem mode suppresses direct post-comment QQ sharing, avoiding two broadcasters;
  Bilibili comments are not suppressed. There is no new timer or Life dependency.
- Evidence is a subtitle/AI-summary excerpt, not visual/audio observation or personal
  experience. No cross-plugin database/cookie reads, host or persona mutation.
- Credentials, pairing keys, SQLite, config.toml and runtime data never enter Git/ZIP.
- Inherited release workflow is archived. Exact-SHA dual-case CI and package import
  must pass before standard hot update; no auto deployment/release.

Local QA: `python scripts/run_tests.py`, `python scripts/check_archive.py`.
All fixtures use synthetic data/mocked IPC; no paid/model/QQ/Bilibili mutations.
