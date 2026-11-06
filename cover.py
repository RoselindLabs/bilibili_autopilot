"""One bounded public cover, held in memory only, for the existing reflection call."""
import asyncio
import base64
from io import BytesIO
import re
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image

from .reading_bridge import io as durable_io

MAX_BYTES = 2 * 1024 * 1024
MAX_PIXELS = 8_000_000
COVER_TIMEOUT = 6


def cover_url(value):
    if not isinstance(value, str) or len(value) > 1000:
        return ''
    try:
        url = urlsplit('https:' + value if value.startswith('//') else value)
        if (url.scheme not in {'http', 'https'} or url.username or url.password or url.port
                or not re.fullmatch(r'i[0-2]\.hdslb\.com', url.hostname or '')
                or not url.path.startswith('/bfs/') or url.query or url.fragment):
            return ''
        return urlunsplit(('https', url.hostname, url.path, '', ''))
    except ValueError:
        return ''


def encode_image(raw):
    if len(raw) > MAX_BYTES:
        raise ValueError('cover_too_large')
    with Image.open(BytesIO(raw)) as image:
        if image.format not in {'JPEG', 'PNG', 'WEBP'} or image.width * image.height > MAX_PIXELS:
            raise ValueError('unsupported_cover')
        image.seek(0)
        image.thumbnail((768, 768))
        with BytesIO() as output:
            image.convert('RGB').save(output, format='JPEG', quality=80)
            return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode('ascii')


async def load_cover(value):
    # Shield cancellation cleanup itself: repeated unload/cancel requests must
    # not release the engine lock while wait_for is still draining its child.
    job = asyncio.create_task(_load_cover(value))
    try:
        return await asyncio.shield(job)
    except asyncio.CancelledError:
        job.cancel()
        while not job.done():
            try:
                await asyncio.shield(job)
            except asyncio.CancelledError:
                pass
            except Exception:
                break
        if not job.cancelled():
            job.exception()
        raise


async def _load_cover(value):
    url = cover_url(value)
    if not url:
        return ''
    async def download():
        async with httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False) as client:
            async with client.stream('GET', url, headers={'Accept-Encoding': 'identity'}) as response:
                response.raise_for_status()
                if response.headers.get('content-encoding', 'identity') != 'identity':
                    raise ValueError('encoded_cover')
                if int(response.headers.get('content-length', '0')) > MAX_BYTES:
                    raise ValueError('cover_too_large')
                raw = bytearray()
                async for chunk in response.aiter_bytes(65536):
                    raw.extend(chunk)
                    if len(raw) > MAX_BYTES:
                        raise ValueError('cover_too_large')
        # The engine's single round lock owns this worker until it really exits.
        # Cancellation/timeout drains the thread before returning, so reload or
        # another round cannot accumulate abandoned decoders. No model is added.
        return await durable_io(encode_image, raw)
    try:
        return await asyncio.wait_for(download(), timeout=COVER_TIMEOUT)
    except (httpx.HTTPError, OSError, ValueError, asyncio.TimeoutError, Image.DecompressionBombError):
        return ''
