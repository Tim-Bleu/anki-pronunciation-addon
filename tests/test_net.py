"""Security tests for the hardened HTTPS client against a local TLS server."""

import http.server
import shutil
import ssl
import subprocess
import threading

import pytest

from pronunciation_tts import net

pytestmark = pytest.mark.skipif(shutil.which("openssl") is None, reason="openssl missing")


@pytest.fixture(scope="module")
def cert(tmp_path_factory):
    d = tmp_path_factory.mktemp("cert")
    key, crt = d / "key.pem", d / "cert.pem"
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1",
            "-keyout", str(key), "-out", str(crt), "-subj", "/CN=localhost",
            "-addext", "subjectAltName=DNS:localhost",
        ],
        check=True,
        capture_output=True,
    )
    return str(crt), str(key)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "https://evil.example/")
            self.end_headers()
        elif self.path == "/big":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"x" * 5000)
        elif self.path == "/404":
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.end_headers()
            self.wfile.write(b"ID3audio")


@pytest.fixture(scope="module")
def server(cert):
    crt, key = cert
    httpd = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(crt, key)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"https://localhost:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def trusted(cert):
    return net.make_ssl_context(cafile=cert[0])


ALLOWED = {"localhost"}


def test_rejects_plain_http():
    with pytest.raises(net.DownloadError, match="HTTPS"):
        net.request("http://localhost/", allowed_hosts=ALLOWED)


def test_rejects_unlisted_host():
    with pytest.raises(net.DownloadError, match="allow-list"):
        net.request("https://evil.example/", allowed_hosts=ALLOWED)


def test_rejects_lookalike_host():
    with pytest.raises(net.DownloadError):
        net.request("https://translate.google.com.evil.example/", allowed_hosts={"translate.google.com"})


def test_rejects_userinfo():
    with pytest.raises(net.DownloadError):
        net.request("https://user:pw@localhost/", allowed_hosts=ALLOWED)


def test_untrusted_certificate_is_rejected(server):
    # default trust store does not know our self-signed cert
    with pytest.raises(net.DownloadError, match="TLS"):
        net.request(server + "/ok", allowed_hosts=ALLOWED, ssl_context=net.make_ssl_context())


def test_hostname_mismatch_rejected(server, trusted):
    url = server.replace("localhost", "127.0.0.1") + "/ok"
    with pytest.raises(net.DownloadError):
        net.request(url, allowed_hosts={"127.0.0.1"}, ssl_context=trusted)


def test_trusted_ok(server, trusted):
    r = net.request(server + "/ok", allowed_hosts=ALLOWED, ssl_context=trusted)
    assert r.status == 200 and r.body == b"ID3audio" and r.content_type == "audio/mpeg"


def test_redirect_not_followed(server, trusted):
    with pytest.raises(net.DownloadError, match="redirect"):
        net.request(server + "/redirect", allowed_hosts=ALLOWED, ssl_context=trusted)


def test_size_limit(server, trusted):
    with pytest.raises(net.DownloadError, match="too large"):
        net.request(server + "/big", allowed_hosts=ALLOWED, ssl_context=trusted, max_bytes=1000)


def test_http_error(server, trusted):
    with pytest.raises(net.DownloadError, match="404"):
        net.request(server + "/404", allowed_hosts=ALLOWED, ssl_context=trusted)
    r = net.request(server + "/404", allowed_hosts=ALLOWED, ssl_context=trusted, accept_error_body=True)
    assert r.status == 404


def test_context_settings():
    ctx = net.make_ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2
