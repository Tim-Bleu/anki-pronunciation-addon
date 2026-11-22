"""Text-to-speech providers. Each returns validated MP3 bytes.

Pure Python; no aqt/anki imports. All network access goes through
``net.request`` with an explicit host allow-list.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
import urllib.parse
from collections.abc import Callable

from . import net
from .audio import validate_mp3
from .i18n import tr
from .text import split_text
from .voices import Voice, google_translate_hosts

MAX_TEXT_CHARS = 1000  # safety cap per note


class TTSError(Exception):
    """User-facing synthesis error."""


Requester = Callable[..., net.Response]


class Provider:
    id = "base"
    label = "base"

    def __init__(self, requester: Requester = net.request) -> None:
        self._request = requester

    def synthesize(self, text: str, voice: Voice, *, slow: bool = False) -> bytes:
        raise NotImplementedError


# --------------------------------------------------------------------------
# Google Translate (no API key required)
# --------------------------------------------------------------------------

_GT_RPC = "jQ1olc"
_GT_AUDIO_RE = re.compile(r'jQ1olc"\s*,\s*"\[\\"([A-Za-z0-9+/=_-]+)\\"')
_B64_ALPHABET_RE = re.compile(r"^[A-Za-z0-9+/=_-]+$")


class GoogleTranslateProvider(Provider):
    """Uses the public Google Translate speech endpoint.

    The regional accent is selected via the Google domain
    (``translate.google.co.uk`` -> British, ``.com`` -> American, ...).
    Long texts are split into chunks of at most 100 characters; the MP3
    frames of all chunks are concatenated (valid for MP3 players).
    """

    id = "google_translate"
    label = "Google Translate"
    CHUNK_LEN = 100

    def synthesize(self, text: str, voice: Voice, *, slow: bool = False) -> bytes:
        text = text.strip()
        if not text:
            raise TTSError(tr("tts.no_text"))
        if len(text) > MAX_TEXT_CHARS:
            raise TTSError(tr("tts.too_long", max=MAX_TEXT_CHARS))
        hosts = google_translate_hosts()
        host = f"translate.google.{voice.gt_tld}"
        if host not in hosts:  # pragma: no cover - guarded by catalogue
            raise TTSError(tr("tts.bad_voice"))
        parts = []
        for chunk in split_text(text, self.CHUNK_LEN):
            parts.append(self._chunk(chunk, voice, host, hosts, slow))
        return validate_mp3(b"".join(parts))

    def _chunk(self, chunk: str, voice: Voice, host: str, hosts, slow: bool) -> bytes:
        try:
            return self._batchexecute(chunk, voice, host, hosts, slow)
        except (TTSError, net.DownloadError) as first_error:
            # Fallback: legacy endpoint that returns MP3 directly.
            try:
                return self._legacy(chunk, voice, host, hosts, slow)
            except (TTSError, net.DownloadError):
                if isinstance(first_error, net.DownloadError):
                    raise TTSError(str(first_error)) from None
                raise first_error from None

    def _batchexecute(self, chunk, voice, host, hosts, slow) -> bytes:
        param = json.dumps([chunk, voice.gt_lang, True if slow else None, "null"], separators=(",", ":"))
        rpc = json.dumps([[[_GT_RPC, param, None, "generic"]]], separators=(",", ":"))
        body = ("f.req=" + urllib.parse.quote(rpc) + "&").encode("ascii")
        resp = self._request(
            f"https://{host}/_/TranslateWebserverUi/data/batchexecute",
            allowed_hosts=hosts,
            method="POST",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
                "Referer": f"https://{host}/",
            },
            max_bytes=4 * 1024 * 1024,
        )
        if resp.status != 200:
            raise TTSError(tr("tts.gt_status", code=resp.status))
        text = resp.body.decode("utf-8", errors="replace")
        match = _GT_AUDIO_RE.search(text)
        if not match:
            raise TTSError(tr("tts.gt_no_audio"))
        return validate_mp3(_b64decode(match.group(1)))

    def _legacy(self, chunk, voice, host, hosts, slow) -> bytes:
        query = urllib.parse.urlencode(
            {
                "ie": "UTF-8",
                "client": "tw-ob",
                "tl": voice.gt_lang,
                "q": chunk,
                "ttsspeed": "0.24" if slow else "1",
            }
        )
        resp = self._request(
            f"https://{host}/translate_tts?{query}",
            allowed_hosts=hosts,
            headers={"Referer": f"https://{host}/"},
            max_bytes=4 * 1024 * 1024,
        )
        if resp.status != 200 or not resp.content_type.startswith("audio/"):
            raise TTSError(tr("tts.gt_no_audio"))
        return validate_mp3(resp.body)


# --------------------------------------------------------------------------
# Google Cloud Text-to-Speech (official API, needs an API key)
# --------------------------------------------------------------------------

CLOUD_HOST = "texttospeech.googleapis.com"
_VOICE_NAME_RE = re.compile(r"^[A-Za-z0-9-]{1,64}$")
_API_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{20,100}$")


class GoogleCloudProvider(Provider):
    id = "google_cloud"
    label = "Google Cloud Text-to-Speech"

    def __init__(self, api_key: str, voice_name: str = "", requester: Requester = net.request) -> None:
        super().__init__(requester)
        api_key = (api_key or "").strip()
        if not _API_KEY_RE.match(api_key):
            raise TTSError(tr("tts.cloud_no_key"))
        voice_name = (voice_name or "").strip()
        if voice_name and not _VOICE_NAME_RE.match(voice_name):
            raise TTSError(tr("tts.cloud_bad_voice_name"))
        self._api_key = api_key
        self._voice_name = voice_name

    def synthesize(self, text: str, voice: Voice, *, slow: bool = False) -> bytes:
        text = text.strip()
        if not text:
            raise TTSError(tr("tts.no_text"))
        if len(text) > MAX_TEXT_CHARS:
            raise TTSError(tr("tts.too_long", max=MAX_TEXT_CHARS))
        voice_cfg: dict = {"languageCode": voice.cloud_code}
        # A specific voice name only makes sense if it belongs to the language.
        if self._voice_name and self._voice_name.lower().startswith(voice.cloud_code.lower()):
            voice_cfg["name"] = self._voice_name
        payload = {
            "input": {"text": text},
            "voice": voice_cfg,
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.75 if slow else 1.0},
        }
        resp = self._request(
            f"https://{CLOUD_HOST}/v1/text:synthesize",
            allowed_hosts={CLOUD_HOST},
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            # Key in a header, never in the URL (URLs end up in logs).
            headers={"Content-Type": "application/json; charset=utf-8", "X-Goog-Api-Key": self._api_key},
            max_bytes=8 * 1024 * 1024,
            accept_error_body=True,
        )
        try:
            doc = json.loads(resp.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise TTSError(tr("tts.cloud_unexpected", code=resp.status)) from None
        if resp.status != 200:
            msg = ""
            if isinstance(doc, dict) and isinstance(doc.get("error"), dict):
                msg = str(doc["error"].get("message", ""))[:300]
            raise TTSError(tr("tts.cloud_error", code=resp.status, msg=msg).strip())
        content = doc.get("audioContent") if isinstance(doc, dict) else None
        if not isinstance(content, str):
            raise TTSError(tr("tts.cloud_no_audio"))
        return validate_mp3(_b64decode(content))


def _b64decode(value: str) -> bytes:
    value = value.strip()
    if not _B64_ALPHABET_RE.match(value):
        raise TTSError(tr("tts.corrupt"))
    try:
        if "-" in value or "_" in value:
            return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        return base64.b64decode(value + "=" * (-len(value) % 4), validate=True)
    except (binascii.Error, ValueError):
        raise TTSError(tr("tts.corrupt")) from None


PROVIDER_IDS = (GoogleTranslateProvider.id, GoogleCloudProvider.id)


def make_provider(config: dict, requester: Requester = net.request) -> Provider:
    pid = config.get("provider", GoogleTranslateProvider.id)
    if pid == GoogleCloudProvider.id:
        return GoogleCloudProvider(
            config.get("google_cloud_api_key", ""),
            config.get("google_cloud_voice_name", ""),
            requester=requester,
        )
    if pid == GoogleTranslateProvider.id:
        return GoogleTranslateProvider(requester=requester)
    raise TTSError(tr("tts.unknown_provider", pid=pid))
