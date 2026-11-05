import asyncio
import base64
from io import BytesIO
import unittest
from unittest.mock import patch

import httpx
from PIL import Image

from local_bilibili_autopilot import cover, journal
from local_bilibili_autopilot.plugin import BilibiliAutopilotPlugin
from local_bilibili_autopilot.config import AutopilotConfig
from maibot_sdk.context import PluginContext
from test_autopilot import ITEM, EVIDENCE


class CoverTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_sdk_preserves_image_in_single_generation(self):
        calls = []
        async def rpc(method, plugin_id, payload, **kwargs):
            calls.append(payload)
            return {'success': True, 'response': 'synthetic'}
        plugin = BilibiliAutopilotPlugin()
        plugin._ctx = PluginContext('local.bilibili-autopilot', rpc_call=rpc)
        prompt = journal.prompt(ITEM, EVIDENCE, '', '', [], 1, 'Asia/Shanghai', cover.encode_image(self.image()))
        await plugin._generate(prompt, AutopilotConfig())
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['args']['prompt'], prompt)
        self.assertNotIn('tools', calls[0]['args'])

    def image(self):
        output = BytesIO()
        Image.new('RGB', (1200, 800), 'blue').save(output, format='PNG')
        return output.getvalue()

    async def test_real_http_stream_and_image_decode_stay_bounded(self):
        requests = []
        def handle(request):
            requests.append(request)
            return httpx.Response(200, content=self.image())
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch.object(cover.httpx, 'AsyncClient', return_value=client):
            data = await cover.load_cover('http://i0.hdslb.com/bfs/archive/test.png')
        self.assertEqual(str(requests[0].url), 'https://i0.hdslb.com/bfs/archive/test.png')
        self.assertNotIn('cookie', requests[0].headers)
        self.assertNotIn('authorization', requests[0].headers)
        with Image.open(BytesIO(base64.b64decode(data.split(',', 1)[1]))) as image:
            self.assertEqual(image.format, 'JPEG')
            self.assertLessEqual(max(image.size), 768)

    async def test_bad_origin_redirect_oversize_and_nonimage_fall_back(self):
        for url in ['https://127.0.0.1/bfs/a', 'https://i0.hdslb.com.evil.com/bfs/a',
                    'https://x@i0.hdslb.com/bfs/a', 'https://i0.hdslb.com:443/bfs/a',
                    'https://i0.hdslb.com/bfs/a?token=secret']:
            with patch.object(cover.httpx, 'AsyncClient') as client:
                self.assertEqual(await cover.load_cover(url), '')
                client.assert_not_called()
        for response in [httpx.Response(302, headers={'location': 'http://127.0.0.1'}),
                         httpx.Response(200, content=b'x' * (cover.MAX_BYTES + 1)),
                         httpx.Response(200, content=b'<html>not an image</html>')]:
            client = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: response))
            with patch.object(cover.httpx, 'AsyncClient', return_value=client):
                self.assertEqual(await cover.load_cover('https://i1.hdslb.com/bfs/a'), '')

    async def test_cancellation_propagates(self):
        async def handle(request):
            raise asyncio.CancelledError()
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        with patch.object(cover.httpx, 'AsyncClient', return_value=client), self.assertRaises(asyncio.CancelledError):
            await cover.load_cover('https://i2.hdslb.com/bfs/a')

    def test_prompt_distinguishes_cover_from_video_and_keeps_quote_contract(self):
        data = cover.encode_image(self.image())
        prompt = journal.prompt(ITEM, EVIDENCE, '合成人设', '', [], 1, 'Asia/Shanghai', data)
        self.assertEqual(prompt[1]['content'][1]['image_url']['url'], data)
        self.assertIn('静态封面', prompt[0]['content'])
        self.assertIn('evidence_quote仍须引用正文', prompt[0]['content'])
        self.assertIn('不用先复述视频', prompt[0]['content'])
        text = journal.prompt(ITEM, EVIDENCE, '合成人设', '', [], 1, 'Asia/Shanghai')
        self.assertIsInstance(text[1]['content'], str)
        self.assertIn('本次未提供封面', text[0]['content'])
