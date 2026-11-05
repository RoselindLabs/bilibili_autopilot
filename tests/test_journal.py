"""Reading continuity, cancellation, account isolation and opt-in private scopes."""
import asyncio
from dataclasses import asdict, replace
import json
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from maibot_sdk.context import PluginContext
from local_bilibili_autopilot import journal
from local_bilibili_autopilot.activity import query_activity, activity_reply_prompt
from local_bilibili_autopilot.models import Evidence
from local_bilibili_autopilot.reading_bridge import authorized_chat
from local_bilibili_autopilot.reading_bridge import ReadingStore
import test_autopilot as fixtures
from bilibili_api.exceptions import WbiRetryTimesExceedException
from test_autopilot import ITEM, EVIDENCE, reflection


class JournalTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.EngineTests.asyncSetUp

    async def setup_journal(self):
        self.cfg.comment.publish_enabled = False
        self.generate.return_value = reflection()
        await self.engine.start()

    def entries(self, **kwargs):
        return journal.page(self.store, self.client.uid, self.cfg.browse.timezone, **kwargs)['entries']

    async def test_two_reads_recall_then_revisit_preserves_both_and_old_attempt(self):
        await self.setup_journal()
        self.store.reserve('1001', ITEM.bvid, '旧评论', self.now - 100, 0, 10, 0, .99)
        self.store.finish('1001', ITEM.bvid, 'unknown')
        await self.engine.round()
        original = self.entries()[0]
        self.now += journal.REVISIT_SECONDS + 1
        self.generate.return_value = reflection(thought='再读时更在意光信号如何避免被误解。', related_ids=[original['id']])
        await self.engine.round()
        entries = self.entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[1]['thought'], original['thought'])
        self.assertEqual(entries[0]['related'][0]['id'], original['id'])
        self.assertIn(original['thought'], self.generate.call_args.args[0][1]['content'])
        self.assertEqual(self.store.stats('1001', 0)['unresolved'], [ITEM.bvid])
        self.client.publish.assert_not_awaited()
        self.engine.review.assert_not_awaited()

    async def test_no_thought_and_short_content_do_not_produce_share(self):
        await self.setup_journal()
        self.engine.reading_sink = AsyncMock()
        self.generate.return_value = reflection(thought='', related_ids=[], evidence_quote='', share_reason='')
        await self.engine.round()
        self.assertEqual(self.entries()[0]['status'], 'passed')
        self.engine.reading_sink.assert_not_awaited()
        self.now += journal.REVISIT_SECONDS + 1
        self.client.understand.return_value = ITEM, Evidence('unavailable', '')
        self.generate.reset_mock()
        await self.engine.round()
        self.assertEqual(self.entries()[0]['status'], 'unread')
        self.generate.assert_not_awaited()

    async def test_cancelled_generation_and_restart_never_replay(self):
        await self.setup_journal()
        entered = asyncio.Event()
        async def generate(*args):
            entered.set()
            await asyncio.Future()
        self.generate.side_effect = generate
        task = asyncio.create_task(self.engine.round())
        await asyncio.wait_for(entered.wait(), 3)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(self.entries()[0]['status'], 'interrupted')
        self.now += 30 * 86400
        await self.engine.initialize()
        self.generate.reset_mock()
        await self.engine.round()
        self.generate.assert_not_awaited()
        self.assertEqual(len(self.entries()), 1)

    async def test_pause_during_generation_drops_result_and_sink(self):
        await self.setup_journal()
        self.engine.reading_sink = AsyncMock()
        async def generate(*args):
            await self.engine.pause('手动暂停', kind='manual')
            return reflection()
        self.generate.side_effect = generate
        await self.engine.round()
        self.assertEqual(self.entries()[0]['status'], 'cancelled')
        self.assertNotIn('thought', self.entries()[0])
        self.engine.reading_sink.assert_not_awaited()

    async def test_failed_output_does_not_repair_or_consume_send_ledger(self):
        await self.setup_journal()
        self.generate.return_value = reflection(evidence_quote='一段实际资料没有出现的虚构引文')
        await self.engine.round()
        self.assertEqual(self.entries()[0]['status'], 'failed')
        self.generate.assert_awaited_once()
        self.assertEqual(self.store.stats('1001', 0)['attempts'], 0)

    async def test_fenced_reflection_is_saved_once_without_repair_call(self):
        await self.setup_journal()
        self.generate.return_value = '\n```json\n' + reflection() + '\n```\n'
        await self.engine.round()
        self.assertEqual(self.entries()[0]['status'], 'noted')
        self.generate.assert_awaited_once()
        self.client.publish.assert_not_awaited()

    async def test_wbi_read_failure_does_not_pause_or_replay(self):
        await self.setup_journal()
        self.client.understand.side_effect = WbiRetryTimesExceedException()
        await self.engine.round()
        self.assertFalse(self.engine.paused)
        self.assertEqual(self.entries()[0]['status'], 'failed')
        self.generate.assert_not_awaited()
        self.client.publish.assert_not_awaited()
        self.now += 30 * 86400
        self.client.understand.reset_mock()
        await self.engine.round()
        self.client.understand.assert_not_awaited()

    def test_fence_support_does_not_accept_extra_text_or_invalid_json(self):
        for raw in ('正文\n```json\n' + reflection() + '\n```',
                    '```json\n' + reflection() + '\n```\n正文',
                    '```json\n{"thought":\n```'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                journal.parse(raw, EVIDENCE, [])

    async def test_capacity_pauses_without_new_read_and_preserves_old_records(self):
        await self.setup_journal()
        await self.engine.round()
        with patch.object(journal, 'CAPACITY', 1):
            self.client.understand.reset_mock()
            await self.engine.round()
            self.client.understand.assert_not_awaited()
            self.assertTrue(self.engine.paused)
            self.assertEqual(len(self.entries()), 1)

    async def test_delete_scrubs_copies_and_pending_material_but_keeps_unknown_and_dedupe(self):
        await self.setup_journal()
        await self.engine.round()
        original = self.entries()[0]
        bridge = ReadingStore(self.store.path.parent)
        decision = journal.parse(reflection(), EVIDENCE, [])
        bridge.remember('1001', ITEM, EVIDENCE, decision, self.now, original['id'])
        offer = bridge.claim('1001', 'chat', 'robot', self.now, 10, 0)
        self.store.reserve('1001', ITEM.bvid, '旧评论', self.now, 0, 10, 0, .99)
        self.store.finish('1001', ITEM.bvid, 'unknown')
        self.now += journal.REVISIT_SECONDS + 1
        self.generate.return_value = reflection(related_ids=[original['id']])
        await self.engine.round()
        expected, _ = journal.deletion_selection(self.store, '1001', original['id'])
        self.assertEqual(journal.delete_entries(self.store, '1001', expected, bridge.path), 1)
        remaining = self.entries()
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]['related'], [{'id': original['id'], 'deleted': True}])
        with self.store.connect() as db:
            tombstone = db.execute('SELECT * FROM journal WHERE id=?', (original['id'],)).fetchone()
            self.assertEqual((tombstone['video'], tombstone['payload'], tombstone['status']), ('{}','{}','deleted'))
        self.assertEqual(self.store.stats('1001', 0)['unresolved'], [ITEM.bvid])
        self.assertIsNone(bridge.operate('prompt', '1001', 'chat', 'robot',
                         {**offer, 'host_task': 'proactive:neko.proactive:1234567890'}, self.now)['candidate'])
        self.assertIsNone(bridge.claim('1001', 'other', 'robot', self.now, 10, 0))
        self.assertTrue(self.store.seen('1001', ITEM.bvid, 'journal', now=self.now+86400*30))
        self.assertEqual(len(journal.context(self.store,'1001')),1)

    async def test_delete_selection_is_frozen_owned_and_frees_capacity(self):
        await self.setup_journal()
        first = journal.begin(self.store, '1001', ITEM, self.now)
        journal.finish(self.store, first, '1001', 'failed', {'reason':'失败内容'}, self.now)
        expected, _ = journal.deletion_selection(self.store,'1001',failed=True)
        second = journal.begin(self.store, '1001', replace(ITEM,bvid='BV0987654321'), self.now+1)
        journal.finish(self.store,second,'1001','interrupted',{'reason':'后来的失败'},self.now+2)
        bridge=ReadingStore(self.store.path.parent)
        bridge.journal_shares('1001',[])
        with self.assertRaises(ValueError):
            journal.delete_entries(self.store,'2002',expected,bridge.path)
        with patch.object(journal,'CAPACITY',2):
            self.assertFalse(journal.capacity(self.store))
            journal.delete_entries(self.store,'1001',expected,bridge.path)
            self.assertTrue(journal.capacity(self.store))
        self.assertEqual([r['id'] for r in self.entries()],[second])
        with self.assertRaises(ValueError):
            journal.delete_entries(self.store,'1001',expected,bridge.path)
        with self.assertRaises(ValueError):
            journal.deletion_selection(self.store,'2002',second)
        with self.assertRaises(ValueError):
            journal.begin(self.store,'1001',ITEM,self.now+86400*30)

    async def test_delete_failure_rolls_back_both_databases(self):
        await self.setup_journal()
        await self.engine.round()
        key=self.entries()[0]['id']
        expected,_=journal.deletion_selection(self.store,'1001',key)
        bridge=ReadingStore(self.store.path.parent)
        bridge.remember('1001',ITEM,EVIDENCE,journal.parse(reflection(),EVIDENCE,[]),self.now,key)
        with bridge.connect() as db:
            db.execute("CREATE TRIGGER reject_delete BEFORE DELETE ON readings BEGIN SELECT RAISE(ABORT,'blocked'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            journal.delete_entries(self.store,'1001',expected,bridge.path)
        self.assertEqual(self.entries()[0]['status'],'noted')
        with bridge.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM readings').fetchone()[0],1)

    async def test_legacy_material_is_bound_to_its_read_and_latest_visit_is_scrubbed(self):
        await self.setup_journal()
        await self.engine.round()
        first=self.entries()[0]['id']
        self.now += journal.REVISIT_SECONDS + 1
        await self.engine.round()
        second=self.entries()[0]['id']
        bridge=ReadingStore(self.store.path.parent)
        bridge.remember('1001',ITEM,EVIDENCE,journal.parse(reflection(),EVIDENCE,[]),self.now)
        expected,_=journal.deletion_selection(self.store,'1001',first)
        journal.delete_entries(self.store,'1001',expected,bridge.path)
        with bridge.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM readings').fetchone()[0],1)
        expected,_=journal.deletion_selection(self.store,'1001',second)
        journal.delete_entries(self.store,'1001',expected,bridge.path)
        with bridge.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM readings').fetchone()[0],0)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT detail FROM visits WHERE mode='journal'").fetchone()[0],'{}')
        self.assertEqual(self.store.page_records('1001','visits','',1)['rows'],[])
        self.assertEqual(query_activity(self.store,'1001',now=self.now,timezone='Asia/Shanghai',days=0)['records'],[])

    async def test_history_day_pagination_and_account_isolation(self):
        await self.setup_journal()
        first = journal.begin(self.store, '1001', ITEM, self.now)
        data = asdict(journal.parse(reflection(), EVIDENCE, []))
        data['source'] = '字幕'
        journal.finish(self.store, first, '1001', 'noted', data, self.now)
        other = journal.begin(self.store, '2002', ITEM, self.now)
        journal.finish(self.store, other, '2002', 'noted', data, self.now)
        second = journal.begin(self.store, '1001', ITEM, self.now + 86400)
        journal.finish(self.store, second, '1001', 'noted', data, self.now + 86400)
        page = journal.page(self.store, '1001', 'Asia/Shanghai', limit=1)
        self.assertEqual(page['entries'][0]['id'], second)
        self.assertEqual(self.entries(before=page['next'])[0]['id'], first)
        with self.assertRaises(ValueError):
            self.entries(before=other)
        self.assertEqual(len(self.entries(day='2026-10-19')), 1)
        result = query_activity(self.store, '1001', now=self.now + 86401, timezone='Asia/Shanghai', kind='browse')
        self.assertEqual(len(result['records']), 2)
        self.assertEqual(result['records'][0]['kind'], 'journal')
        self.assertIn(data['thought'], activity_reply_prompt(result))
        self.assertEqual(self.entries(query='%'), [])

    def test_only_supplied_links_and_grounded_quotes_are_accepted(self):
        for changes in ({'related_ids': ['foreign']}, {'related_ids': 'x'}, {'thought': '', 'share_reason': '分享'},
                        {'evidence_quote': '非真实资料'}, {'thought': 'a' * 801}):
            with self.assertRaises(ValueError):
                journal.parse(reflection(**changes), EVIDENCE, [])

    async def test_private_routes_require_opt_in_real_sdk_and_unique_account(self):
        rows = [{'session_id': 'private', 'user_id': '123456', 'account_id': '777',
                 'chat_type': 'private', 'platform': 'qq', 'group_id': ''}]
        async def rpc(method, plugin_id, payload):
            cap = payload['capability']
            return {'success': True, 'streams': rows if cap == 'chat.get_private_streams' else []}
        ctx = PluginContext('local.bilibili-autopilot', rpc_call=rpc)
        with self.assertRaises(ValueError):
            await authorized_chat(ctx, 'private', [], [], '')
        self.assertEqual((await authorized_chat(ctx, 'private', [], ['123456'], '777'))['user_id'], '123456')
        rows.append({**rows[0], 'session_id': 'other', 'account_id': '888'})
        with self.assertRaises(ValueError):
            await authorized_chat(ctx, 'private', [], ['123456'], '')
        with self.assertRaises(ValueError):
            await authorized_chat(ctx, 'private', [], ['123456'], '888')
        self.assertEqual((await authorized_chat(ctx, 'private', [], ['123456'], '777'))['account_id'], '777')
