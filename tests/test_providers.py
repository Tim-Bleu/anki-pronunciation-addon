import base64
import json
import urllib.parse

import pytest

from pronunciation_tts import net
from pronunciation_tts.providers import (
    GoogleCloudProvider,
    GoogleTranslateProvider,
    TTSError,
    make_provider,
)
from pronunciation_tts.voices import VOICES, get_voice, google_translate_hosts

MP3 = b"ID3" + b"\x01" * 200
KEY = "AIzaFAKEFAKEFAKEFAKEFAKEFAKE12345"


class Recorder:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, **kw):
        self.calls.append((url, kw))
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def batch_response(data: bytes) -> net.Response:
    b64 = base64.b64encode(data).decode()
    body = ")]}'\n\n123\n" + json.dumps([["wrb.fr", "jQ1olc", json.dumps([b64]), None, None, None, "generic"]])
    return net.Response(200, {"Content-Type": "application/json"}, body.encode())


def test_translate_uses_accent_domain_and_allowlist():
    rec = Recorder([batch_response(MP3)])
    out = GoogleTranslateProvider(rec).synthesize("hello", get_voice("en-GB"))
    assert out == MP3
    url, kw = rec.calls[0]
    assert url.startswith("https://translate.google.co.uk/")
    assert kw["allowed_hosts"] == google_translate_hosts()
    body = urllib.parse.unquote(kw["data"].decode())
    assert '\\"hello\\",\\"en\\"' in body


def test_translate_american():
    rec = Recorder([batch_response(MP3)])
    GoogleTranslateProvider(rec).synthesize("hello", get_voice("en-US"))
    assert rec.calls[0][0].startswith("https://translate.google.com/")


def test_translate_chunks_long_text():
    text = "word " * 60  # 300 chars
    rec = Recorder([batch_response(MP3)] * 4)
    out = GoogleTranslateProvider(rec).synthesize(text, get_voice("en-US"))
    assert len(rec.calls) >= 3
    assert out == MP3 * len(rec.calls)


def test_translate_fallback_to_legacy():
    rec = Recorder(
        [
            net.Response(200, {}, b"garbage"),
            net.Response(200, {"Content-Type": "audio/mpeg"}, MP3),
        ]
    )
    assert GoogleTranslateProvider(rec).synthesize("hi", get_voice("fr-FR")) == MP3
    assert "translate_tts" in rec.calls[1][0]


def test_translate_rejects_non_audio():
    rec = Recorder(
        [
            batch_response(b"<html>not audio</html>" * 10),
            net.Response(200, {"Content-Type": "text/html"}, b"<html>"),
        ]
    )
    with pytest.raises(Exception):
        GoogleTranslateProvider(rec).synthesize("hi", get_voice("en-US"))


def test_translate_network_error_is_tts_error():
    rec = Recorder([net.DownloadError("boom"), net.DownloadError("boom")])
    with pytest.raises(TTSError, match="boom"):
        GoogleTranslateProvider(rec).synthesize("hi", get_voice("en-US"))


def test_empty_and_too_long():
    p = GoogleTranslateProvider(Recorder([]))
    with pytest.raises(TTSError):
        p.synthesize("  ", get_voice("en-US"))
    with pytest.raises(TTSError):
        p.synthesize("x" * 5000, get_voice("en-US"))


def test_cloud_key_in_header_not_url():
    content = base64.b64encode(MP3).decode()
    rec = Recorder([net.Response(200, {}, json.dumps({"audioContent": content}).encode())])
    p = GoogleCloudProvider(KEY, "en-GB-Neural2-B", requester=rec)
    assert p.synthesize("hello", get_voice("en-GB")) == MP3
    url, kw = rec.calls[0]
    assert KEY not in url
    assert kw["headers"]["X-Goog-Api-Key"] == KEY
    assert kw["allowed_hosts"] == {"texttospeech.googleapis.com"}
    payload = json.loads(kw["data"])
    assert payload["voice"] == {"languageCode": "en-GB", "name": "en-GB-Neural2-B"}


def test_cloud_voice_name_ignored_for_other_language():
    content = base64.b64encode(MP3).decode()
    rec = Recorder([net.Response(200, {}, json.dumps({"audioContent": content}).encode())])
    GoogleCloudProvider(KEY, "en-GB-Neural2-B", requester=rec).synthesize("hola", get_voice("es-ES"))
    assert json.loads(rec.calls[0][1]["data"])["voice"] == {"languageCode": "es-ES"}


def test_cloud_error_message():
    body = json.dumps({"error": {"message": "API key not valid"}}).encode()
    rec = Recorder([net.Response(400, {}, body)])
    with pytest.raises(TTSError, match="API key not valid"):
        GoogleCloudProvider(KEY, requester=rec).synthesize("x", get_voice("en-US"))


def test_cloud_requires_key():
    with pytest.raises(TTSError):
        GoogleCloudProvider("")
    with pytest.raises(TTSError):
        GoogleCloudProvider("bad key with spaces and more chars")


def test_make_provider():
    assert isinstance(make_provider({}), GoogleTranslateProvider)
    assert isinstance(make_provider({"provider": "google_cloud", "google_cloud_api_key": KEY}), GoogleCloudProvider)
    with pytest.raises(TTSError):
        make_provider({"provider": "evil"})


def test_voice_catalogue_unique():
    ids = [v.id for v in VOICES]
    assert len(ids) == len(set(ids))
