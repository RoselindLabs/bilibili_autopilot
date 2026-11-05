# Neko Bilibili maintenance fork

0.10.0 turns automatic reading with publication disabled into an independent journal.
Append-only experiences live in the existing state database (20,000 entries, no automatic deletion),
with bounded real-history context and source quotes, not renamed comment drafts. A week-old
completed reading may be revisited if recommended again. Interrupted/failed reflections never replay.
The custom journal page uses the Host management bridge; legacy administration remains available
inside its collapsed management section (0.10.1), with no separate legacy sidebar/table page.
Explicit `ecosystem.qq_friend_ids` defaults empty; private scope resolution requires the declared
`chat.get_private_streams` capability and both sides' existing grants for proactive sharing.
Neko Proactive 2.9.4 preserves reflection and conversation relevance within the original prompt budget.
Old comments, unknowns and all handoff tombstones survive; rollback keeps the latest database.

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

CI timing: the test runner prints the slowest 20 cases including setup/cleanup.
Optional `python -X utf8 scripts/run_tests.py --workers 2` uses two isolated
processes split whole modules, retaining original SQLite files and durability,
asyncio settings, class fixtures and every test. The parent checks each child's
exit code, discovered IDs, executed count and zero skips against the full suite;
missing reports, worker failure or incomplete coverage fail the job. Both CI platforms
use the single-process full run: hosted Windows parallel measurement regressed to
349s vs the prior serial 245.6s, despite the local benefit below. No runtime deployment is needed.
Local paired measurement on 2026-11-05: 337 cases, serial 65.656s vs two-process
49.530s wall (including child startup); hosted runner timings can differ.
Business fixtures now copy a pristine schema created once by the real initializer,
then run normal initialization, transactions and restart recovery on their own files.
Store/migration tests still build from scratch. No shared mutable database, SQLite
durability bypass, production change or dropped test is involved.
