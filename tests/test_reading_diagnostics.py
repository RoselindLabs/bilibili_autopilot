"""Offline SQLite/engine proofs for choice budgets, grounded handoffs and diagnostics."""
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest

from local_bilibili_autopilot import journal
from local_bilibili_autopilot.client import PlatformError, VideoIdentityError, VideoReadError
from local_bilibili_autopilot.models import Evidence
from local_bilibili_autopilot.reading_bridge import ReadingStore
import test_autopilot as fixtures
from test_autopilot import ITEM, EVIDENCE, reflection


class ReadingDiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.EngineTests.asyncSetUp

    async def test_one_remaining_keeps_ten_choices_and_only_reads_selected_tail(self):
        self.cfg.comment.publish_enabled = False
        self.cfg.browse.autonomous_enabled = True
        self.cfg.browse.videos_per_round = 3
        self.cfg.browse.videos_per_day = 1
        items = [replace(ITEM, bvid=f'BV{i:010d}') for i in range(12)]
        self.client.recommended.return_value = items
        self.client.understand.return_value = items[9], EVIDENCE
        def generate(prompt, cfg):
            if '[autopilot:reflection]' in prompt[0]['content']:
                return reflection()
            data = json.loads(prompt[1]['content'])
            self.assertEqual(len(data['current_recommendations']), 10)
            self.assertIn('最多 1 条', prompt[0]['content'])
            return json.dumps({'should_browse': True, 'reason': '想读最后一条', 'next_check_minutes': 30,
                               'selected_bvids': [items[9].bvid]})
        self.generate.side_effect = generate
        await self.engine.start()
        await self.engine.round()
        self.assertEqual(self.generate.await_count, 2)
        self.client.recommended.assert_awaited_once()
        self.client.understand.assert_awaited_once()
        self.assertEqual(self.client.understand.call_args.args[0].bvid, items[9].bvid)
        self.assertEqual(self.store.stats('1001', 0)['views'], 1)
        self.client.publish.assert_not_awaited()

    async def test_over_remaining_selection_is_invalid_without_repair_or_read(self):
        self.cfg.comment.publish_enabled = False
        self.cfg.browse.autonomous_enabled = True
        self.cfg.browse.videos_per_day = 1
        other = replace(ITEM, bvid='BV0000000001')
        self.client.recommended.return_value = [ITEM, other]
        self.generate.return_value = json.dumps({'should_browse': True, 'reason': '想读', 'next_check_minutes': 30,
                                                 'selected_bvids': [ITEM.bvid, other.bvid]})
        await self.engine.start()
        await self.engine.round()
        self.generate.assert_awaited_once()
        self.client.understand.assert_not_awaited()
        self.assertEqual(self.store.stats('1001', 0)['views'], 0)

    async def test_grounded_quote_tail_context_old_payload_and_bounds(self):
        store = ReadingStore(self.temp.name)
        quote = '深海生物利用发光器官吸引猎物'
        evidence = Evidence('字幕', '开头'*500 + quote + '后文'*300)
        decision = journal.parse(reflection(evidence_quote=quote), evidence, [])
        registration = store.remember('1001', ITEM, evidence, decision, self.now, 'j1')
        self.assertEqual(registration, journal.registration('registered', 'registered', self.now))
        offer = store.claim('1001', 's', '123', self.now, 2, 0, True)
        candidate = store.operate('prompt', '1001', 's', '123', {**offer, 'host_task': 'proactive:neko.proactive:1234567890123'}, self.now)['candidate']
        self.assertEqual(candidate['evidence_quote'], quote)
        self.assertIn(quote, candidate['summary'])
        for field, maximum in (('evidence_quote', 400), ('summary', 480), ('opinion', 800), ('share_reason', 200)):
            self.assertLessEqual(len(candidate[field]), maximum)
        for i, invalid in enumerate(('不在实际正文中的伪造引用', '字'*401, ''), 1):
            item = replace(ITEM, bvid=f'BV{i:010d}')
            store.remember('1001', item, evidence, SimpleNamespace(reason='旧记录', evidence_quote=invalid), self.now)
            with store.connect() as db:
                payload = json.loads(db.execute('SELECT payload FROM readings WHERE bvid=?', (item.bvid,)).fetchone()[0])
            self.assertNotIn('evidence_quote', payload)
            self.assertEqual(payload['summary'], evidence.text[:480])
        # Valid normalized match with no exact location keeps original quote and old excerpt.
        quote = 'ＤＥＥＰ  ocean'
        item = replace(ITEM, bvid='BV0000000009')
        source = Evidence('字幕', 'context '*100 + 'deep-ocean')
        store.remember('1001', item, source, SimpleNamespace(reason='old', evidence_quote=quote), self.now)
        with store.connect() as db:
            payload = json.loads(db.execute('SELECT payload FROM readings WHERE bvid=?', (item.bvid,)).fetchone()[0])
        self.assertEqual(payload['evidence_quote'], quote)
        self.assertEqual(payload['summary'], source.text[:480])

    async def test_readonly_diagnostics_expiry_unknown_registration_and_offer_ownership(self):
        store = ReadingStore(self.temp.name)
        entries = [{'id': 'j1', 'bvid': ITEM.bvid}, {'id': 'old', 'bvid': ITEM.bvid}]
        self.assertEqual(store.journal_diagnostics('1001', entries, self.now)['j1']['material'], 'unknown')
        self.assertFalse(store.path.exists())
        # An existing old/empty database is read as unknown without creating tables.
        db = sqlite3.connect(store.path)
        db.close()
        empty = store.path.read_bytes()
        self.assertFalse(store.journal_diagnostics('1001', entries, self.now)['j1']['offers_known'])
        self.assertEqual(empty, store.path.read_bytes())
        decision = journal.parse(reflection(), EVIDENCE, [])
        registration = store.remember('1001', ITEM, EVIDENCE, decision, self.now, 'j1')
        entries[0]['material_registration'] = registration
        first = store.claim('1001', 's', '123', self.now, 2, 0)
        store.operate('receipt', '1001', 's', '123', {**first, 'status': 'unknown'}, self.now)
        second = store.claim('1001', 'other', '123', self.now, 2, 0)
        store.operate('prompt', '1001', 'other', '123', {**second, 'host_task': 'proactive:neko.proactive:1234567890123'}, self.now)
        before, files = store.path.read_bytes(), sorted(Path(self.temp.name).iterdir())
        result = store.journal_diagnostics('1001', entries, self.now)
        self.assertEqual(result['j1']['material'], 'available')
        self.assertEqual(result['old']['material'], 'unknown')
        self.assertEqual(result['j1']['offer_counts'], {'unknown': 1, 'shown': 1})
        self.assertEqual(result['old']['offer_counts'], result['j1']['offer_counts'])
        self.assertEqual(result['j1']['offer_scope'], 'account_video_history')
        self.assertEqual(store.journal_diagnostics('2', entries, self.now)['j1']['offer_counts'], {})
        self.assertEqual(store.journal_diagnostics('1001', entries, self.now+172800)['j1']['material'], 'expired')
        self.assertEqual(store.path.read_bytes(), before)
        self.assertEqual(sorted(Path(self.temp.name).iterdir()), files)
        with store.connect() as db:
            db.execute('DELETE FROM readings')
        self.assertEqual(store.journal_diagnostics('1001', entries, self.now)['j1']['material'], 'unknown')
        self.assertEqual(store.journal_diagnostics('1001', entries, self.now+172800)['j1']['material'], 'expired')
        entries[1]['material_registration'] = journal.registration('not_registered', 'no_share_reason')
        self.assertEqual(store.journal_diagnostics('1001', entries, self.now)['old']['material'], 'not_registered')
        # Tombstones persist; diagnostics never release or reoffer unknown/shown.
        self.assertIsNone(store.claim('1001', 's', '123', self.now, 20, 0))

    async def test_journal_classifies_real_failures_and_registration_without_error_text(self):
        self.cfg.comment.publish_enabled = False
        await self.engine.start()
        cases = [(VideoReadError('secret', True, stage='subtitle_list', reason_code='network_or_timeout'), 'subtitle_list', 'network_or_timeout'),
                 (PlatformError('读取 AI 摘要', -504), 'ai_summary', 'timeout'),
                 (VideoIdentityError('secret'), 'video_info', 'identity_mismatch')]
        for i, (error, stage, code) in enumerate(cases):
            item = replace(ITEM, bvid=f'BV{i:010d}')
            self.client.understand.side_effect = error
            try:
                await self.engine._journal_read('1001', item, self.cfg, 'persona')
            except PlatformError:
                pass
            row = journal.page(self.store, '1001', 'Asia/Shanghai')['entries'][0]
            # Same-time order is by UUID; select exact video rather than assume order.
            row = next(r for r in journal.page(self.store, '1001', 'Asia/Shanghai')['entries'] if r['bvid'] == item.bvid)
            self.assertEqual(row['diagnostic']['stage'], stage)
            self.assertEqual(row['diagnostic']['reason_code'], code)
            self.assertNotIn('secret', json.dumps(row))
            self.assertEqual(row['material_registration']['status'], 'not_registered')
        item = replace(ITEM, bvid='BV9999999999')
        self.client.understand.side_effect = None
        self.client.understand.return_value = item, replace(EVIDENCE, read_warning_code='summary_timeout')
        self.generate.return_value = reflection()
        sink = ReadingStore(self.temp.name)
        async def remember(uid, item, evidence, decision, journal_id):
            return sink.remember(uid, item, evidence, decision, self.now, journal_id)
        self.engine.reading_sink = remember
        await self.engine._journal_read('1001', item, self.cfg, 'persona')
        row = next(r for r in journal.page(self.store, '1001', 'Asia/Shanghai')['entries'] if r['bvid'] == item.bvid)
        self.assertEqual(row['diagnostic'], journal.diagnostic('complete', 'ok', 'summary_timeout'))
        self.assertEqual(row['material_registration']['registered_at'], self.now)
        # The bridge may have committed before its result is lost. Keep uncertainty.
        async def lost_result(*args, **kwargs):
            raise RuntimeError('secret external error')
        self.engine.reading_sink = lost_result
        failed_item = replace(ITEM, bvid='BV8888888888')
        self.client.understand.return_value = failed_item, EVIDENCE
        await self.engine._journal_read('1001', failed_item, self.cfg, 'persona')
        row = next(r for r in journal.page(self.store, '1001', 'Asia/Shanghai')['entries'] if r['bvid'] == failed_item.bvid)
        self.assertEqual(row['status'], 'noted')
        self.assertEqual(row['material_registration'], journal.registration('unknown', 'registration_error'))
        self.assertNotIn('secret', json.dumps(row))
        old = journal.begin(self.store, '1001', replace(ITEM, bvid='old'), self.now)
        journal.finish(self.store, old, '1001', 'failed', {'reason': 'historic timeout text'}, self.now)
        before = self.store.path.read_bytes()
        row = next(r for r in journal.page(self.store, '1001', 'Asia/Shanghai')['entries'] if r['id'] == old)
        self.assertEqual(row['diagnostic'], journal.diagnostic())
        self.assertEqual(row['material_registration']['status'], 'unknown')
        self.assertEqual(before, self.store.path.read_bytes())
