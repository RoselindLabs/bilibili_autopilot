"""Real 17.4.2 APIs over mock HTTP; adapted from upstream 78d6dd6 (MIT)."""

import asyncio
import importlib
import os
from pathlib import Path
import ssl
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import AsyncMock, Mock, patch

from bilibili_api import Credential, get_selected_client
from bilibili_api.clients.HTTPXClient import HTTPXClient
from bilibili_api.utils import network
import httpx

from local_bilibili_autopilot import transport
from local_bilibili_autopilot.client import BiliClient, LoginDiagnosticError, LoginRequired, UnknownPublish
from local_bilibili_autopilot.models import VideoItem


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = TemporaryDirectory(prefix="扫码证书-")
        self.addCleanup(self.temp.cleanup)
        self.client = BiliClient(Path(self.temp.name) / "凭据.json", logger=Mock())
        self.addAsyncCleanup(self.client.close)
        self.selected = get_selected_client()
        self.original = network.get_client()
        self.addAsyncCleanup(self.original.close)
        self.old_request = AsyncMock(side_effect=AssertionError("default client must not run"))
        patcher = patch.object(self.original, "request", self.old_request)
        patcher.start()
        self.addCleanup(patcher.stop)
        await self.client.http.aclose()
        await self.client.api_http.close()
        self.requests = []
        self.mid = 1
        self.api_error = self.post_error = None

        async def respond(request):
            self.requests.append(request)
            if request.url.path.endswith("/poll"):
                cookies = {"SESSDATA": "test-session", "bili_jct": "test-csrf", "DedeUserID": "1"}
                headers = [("set-cookie", f"{k}={v}; Path=/; Domain=.bilibili.com; Secure")
                           for k, v in cookies.items()]
                return httpx.Response(200, json={"code": 0, "data": {"code": 0}}, headers=headers)
            if self.api_error:
                raise self.api_error
            if request.method == "POST" and self.post_error:
                raise self.post_error
            data = {"mid": self.mid, "name": "模拟账号"} if request.method == "GET" else {"rpid": 9988}
            return httpx.Response(200, json={"code": 0, "data": data})

        self.client.http = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        self.client.api_http = HTTPXClient(session=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        # Real authentication / request preparation; only unrelated device data is synthetic.
        for name, result in (("get_buvid", ("test-device-3", "test-device-4")),
                             ("get_bili_ticket", ("test-ticket", "9999999999"))):
            patcher = patch.object(network, name, AsyncMock(return_value=result))
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_real_login_and_check_keep_uid_tls_and_private_persistence(self):
        self.assertIn("已登录", await self.client.poll_login("test-qr"))
        self.assertTrue(self.client.credential_path.exists())
        self.assertEqual(await self.client.check_account(), "1")
        self.assertIn("test-session", self.requests[-1].headers["cookie"])
        self.assertEqual(get_selected_client(), self.selected)
        self.old_request.assert_not_awaited()
        logs = "\n".join(call.args[0] % call.args[1:] for call in self.client.logger.mock_calls)
        self.assertIn("stage=验证扫码账号 client=httpx", logs)
        self.assertNotIn("test-session", logs)
        self.mid = 2
        with self.assertRaises(LoginRequired):
            await self.client.check_account()
        self.client.api_http.get_wrapped_session().cookies.set("SESSDATA", "test-session")
        await self.client.logout()
        self.assertEqual(len(self.client.api_http.get_wrapped_session().cookies), 0)

    async def test_bad_uid_and_certificate_failure_do_not_save_credentials(self):
        self.mid = 2
        with self.assertRaises(LoginRequired):
            await self.client.poll_login("test-qr")
        self.api_error = httpx.ConnectError("CERTIFICATE_VERIFY_FAILED")
        with self.assertRaises(LoginDiagnosticError) as raised:
            await self.client.poll_login("test-qr")
        self.assertIn("certificate_verify_failed", str(raised.exception))
        self.assertFalse(self.client.credential_path.exists())
        self.assertIsNone(self.client.credential)
        self.old_request.assert_not_awaited()

    async def test_actual_ticket_buvid_and_wbi_helpers_use_local_transport(self):
        # These helpers call get_client directly, outside Api.request.
        responses = [
            {"data": {"ticket": "test-ticket"}},
            {"data": {"b_3": "three", "b_4": "four"}},
            {"data": {"wbi_img": {"img_url": "https://i.test/" + "a" * 32 + ".png",
                                    "sub_url": "https://i.test/" + "b" * 32 + ".png"}}},
        ]
        with patch.object(self.client.api_http, "request", AsyncMock()) as request:
            request.side_effect = [Mock(json=Mock(return_value=r)) for r in responses]
            self.assertEqual(await self.client._read_stage("ticket", network._get_bili_ticket(Credential())), "test-ticket")
            self.assertEqual(await self.client._read_stage("buvid", network._get_spi_buvid()), {"b_3": "three", "b_4": "four"})
            self.assertEqual(len(await self.client._read_stage("wbi", network._get_mixin_key(Credential()))), 32)
        self.assertEqual(request.await_count, 3)
        self.old_request.assert_not_awaited()

    async def test_real_signing_unknown_post_single_call_and_cancel_before_post(self):
        self.client.credential = Credential(sessdata="test-session", bili_jct="test-csrf", dedeuserid="1",
                                            buvid3="test-device-3", buvid4="test-device-4")
        item = VideoItem("BV1xx411c7mD", 100, "模拟视频", "2", "UP", 60)
        async def signing_key(credential):
            await network.get_client().request(method="GET", url="https://api.bilibili.com/mock-signing")
            return "0123456789abcdef0123456789abcdef"
        self.post_error = httpx.ReadTimeout("unknown POST")
        with patch.object(network, "get_wbi_mixin_key", signing_key):
            with self.assertRaises(UnknownPublish):
                await self.client.publish(item, "测试内容", lambda: True)
        self.assertEqual([r.method for r in self.requests], ["GET", "POST"])
        self.assertIn("w_rid", self.requests[-1].url.params)
        self.old_request.assert_not_awaited()
        entered = asyncio.Event()
        async def blocked(credential):
            self.assertIs(network.get_client(), self.client.api_http)
            entered.set()
            await asyncio.Event().wait()
        with patch.object(network, "get_wbi_mixin_key", blocked):
            task = asyncio.create_task(self.client.publish(item, "测试内容", lambda: True))
            await entered.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertEqual(len(self.requests), 2)
        self.assertIs(network.get_client(), self.original)

    async def test_concurrent_clients_nested_scope_reload_and_cancellation_restore(self):
        other = HTTPXClient(session=httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200))))
        self.addAsyncCleanup(other.close)
        entered, release = asyncio.Event(), asyncio.Event()
        async def local():
            with transport.api_transport(self.client.api_http):
                entered.set()
                try:
                    await release.wait()
                finally:
                    self.assertIs(network.get_client(), self.client.api_http)
        task = asyncio.create_task(local())
        await entered.wait()
        self.assertIs(network.get_client(), self.original)
        wrapper = network.get_client
        importlib.reload(transport)
        self.assertIs(network.get_client, wrapper)
        with transport.api_transport(other):
            with transport.api_transport(self.client.api_http):
                self.assertIs(network.get_client(), self.client.api_http)
            self.assertIs(network.get_client(), other)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertIs(network.get_client(), other)
        self.assertIs(network.get_client(), self.original)
        with self.assertRaises(ValueError), transport.api_transport(other):
            raise ValueError("synthetic")
        self.assertIs(network.get_client(), self.original)

    async def test_configured_proxy_environment_policy_tls_and_owned_close(self):
        settings = network.request_settings
        before = settings.get_all().copy()
        with patch.object(settings, "get_proxy", return_value="http://127.0.0.1:19099"), \
                patch.object(settings, "get_trust_env", return_value=False), \
                patch.object(settings, "get_timeout", return_value=7), \
                patch.object(transport, "HTTPXClient", wraps=HTTPXClient) as factory:
            api = transport.create_api_client()
        self.addAsyncCleanup(api.close)
        self.assertEqual(factory.call_args.kwargs,
                         {"proxy": "http://127.0.0.1:19099", "trust_env": False, "timeout": 7, "verify_ssl": True})
        session = api.get_wrapped_session()
        self.assertFalse(session.trust_env)
        self.assertEqual(session.timeout.connect, 7)
        pools = [t._pool for t in session._mounts.values() if t is not None]
        self.assertTrue(pools)
        self.assertEqual(pools[0]._proxy_url.port, 19099)
        context = session._transport._pool._ssl_context
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        self.assertEqual(settings.get_all(), before)
        with patch.dict(os.environ, {"HTTPS_PROXY": "http://127.0.0.1:19100", "NO_PROXY": ""}), \
                patch.object(settings, "get_proxy", return_value=""), \
                patch.object(settings, "get_trust_env", return_value=True):
            env_api = transport.create_api_client()
        self.addAsyncCleanup(env_api.close)
        pools = [t._pool for t in env_api.get_wrapped_session()._mounts.values() if t is not None]
        self.assertIn(19100, [p._proxy_url.port for p in pools])
        await self.client.close()
        self.assertTrue(self.client.api_http.get_wrapped_session().is_closed)
        self.assertTrue(self.client.http.is_closed)
        self.assertTrue(self.client.public_http.is_closed)

    async def test_close_failure_still_releases_other_owned_clients(self):
        with patch.object(self.client.http, "aclose", AsyncMock(side_effect=RuntimeError("close"))):
            with self.assertRaises(RuntimeError):
                await self.client.close()
        self.assertTrue(self.client.public_http.is_closed)
        self.assertTrue(self.client.api_http.get_wrapped_session().is_closed)
