import unittest

from app.core.source_registry import DEFAULT_APPROVED_SOURCES
from app.core.url_validator import validate_url


class TestUrlValidator(unittest.TestCase):
    def test_approved_domain_accepted(self):
        result = validate_url(
            "https://www.msme.gov.in/schemes/pmegp",
            DEFAULT_APPROVED_SOURCES,
            resolve_dns=False,
        )
        self.assertTrue(result.is_valid)
        self.assertEqual(result.matched_source.source_id, "msme")

    def test_unapproved_domain_rejected(self):
        for url in [
            "https://en.wikipedia.org/wiki/MSME",
            "https://www.somerandomblog.com/schemes",
            "https://news.example.com/article",
        ]:
            result = validate_url(url, DEFAULT_APPROVED_SOURCES, resolve_dns=False)
            self.assertFalse(result.is_valid, url)

    def test_disallowed_protocol_rejected(self):
        for url in ["file:///etc/passwd", "ftp://msme.gov.in/x"]:
            result = validate_url(url, DEFAULT_APPROVED_SOURCES, resolve_dns=False)
            self.assertFalse(result.is_valid, url)

    def test_ssrf_localhost_rejected(self):
        for url in [
            "http://localhost/admin",
            "http://127.0.0.1:8000/",
            "http://0.0.0.0/",
        ]:
            result = validate_url(url, DEFAULT_APPROVED_SOURCES, resolve_dns=False)
            self.assertFalse(result.is_valid, url)

    def test_ssrf_private_ip_rejected(self):
        for url in [
            "http://10.0.0.5/",
            "http://192.168.1.1/",
            "http://169.254.169.254/latest/meta-data/",  # cloud metadata endpoint
        ]:
            result = validate_url(url, DEFAULT_APPROVED_SOURCES, resolve_dns=False)
            self.assertFalse(result.is_valid, url)

    def test_malformed_url_rejected(self):
        result = validate_url("not a url", DEFAULT_APPROVED_SOURCES, resolve_dns=False)
        self.assertFalse(result.is_valid)

    def test_disabled_source_domain_rejected(self):
        sources = [s for s in DEFAULT_APPROVED_SOURCES]
        sources[0].enabled = False
        result = validate_url(sources[0].base_url, sources, resolve_dns=False)
        self.assertFalse(result.is_valid)
        sources[0].enabled = True  # reset for other tests

    def test_nat64_public_destinations_allowed(self):
        from unittest.mock import patch
        from app.core.url_validator import _is_private_or_reserved_ip, _resolves_to_disallowed_ip

        # Public IPv4 addresses embedded in NAT64 Well-Known Prefix (64:ff9b::/96)
        self.assertFalse(_is_private_or_reserved_ip("64:ff9b::a464:e6d8"))  # 164.100.230.216 (dcmsme.gov.in)
        self.assertFalse(_is_private_or_reserved_ip("64:ff9b::3132:7577"))  # 49.50.117.119 (sidbi.in)

        # Mock DNS resolution returning dual-stack public IPv4 and NAT64 IPv6
        mock_infos = [
            (23, 0, 0, "", ("64:ff9b::a464:e6d8", 443, 0, 0)),
            (2, 0, 0, "", ("164.100.230.216", 443)),
        ]
        with patch("socket.getaddrinfo", return_value=mock_infos):
            self.assertFalse(_resolves_to_disallowed_ip("dcmsme.gov.in"))
            result = validate_url("https://dcmsme.gov.in/schemes", DEFAULT_APPROVED_SOURCES, resolve_dns=True)
            self.assertTrue(result.is_valid)
            self.assertEqual(result.matched_source.source_id, "dcmsme")

    def test_nat64_unsafe_destinations_rejected(self):
        from unittest.mock import patch
        from app.core.url_validator import _is_private_or_reserved_ip, _resolves_to_disallowed_ip

        # Unsafe IPv4 destinations mapped inside NAT64 prefix must be rejected
        unsafe_nat64 = [
            ("64:ff9b::7f00:1", "loopback 127.0.0.1"),
            ("64:ff9b::a9fe:a9fe", "cloud metadata / link-local 169.254.169.254"),
            ("64:ff9b::a00:1", "private 10.0.0.1"),
            ("64:ff9b::c0a8:101", "private 192.168.1.1"),
            ("64:ff9b::ac10:1", "private 172.16.0.1"),
            ("64:ff9b::0", "unspecified 0.0.0.0"),
            ("64:ff9b::e000:1", "multicast 224.0.0.1"),
            ("64:ff9b::f000:1", "reserved 240.0.0.1"),
        ]
        for ip_str, desc in unsafe_nat64:
            self.assertTrue(_is_private_or_reserved_ip(ip_str), f"Failed to reject unsafe NAT64: {desc}")

        # When DNS maps an approved domain name to an unsafe NAT64 address, SSRF must reject it
        with patch("socket.getaddrinfo", return_value=[(23, 0, 0, "", ("64:ff9b::7f00:1", 443, 0, 0))]):
            self.assertTrue(_resolves_to_disallowed_ip("dcmsme.gov.in"))
            result = validate_url("https://dcmsme.gov.in/schemes", DEFAULT_APPROVED_SOURCES, resolve_dns=True)
            self.assertFalse(result.is_valid)
            self.assertIn("private/internal", result.reason.lower())

    def test_dns_rebinding_mixed_addresses_rejected(self):
        from unittest.mock import patch
        from app.core.url_validator import _resolves_to_disallowed_ip

        # If DNS returns a public IP mixed with a private/loopback destination (DNS rebinding)
        mock_infos = [
            (2, 0, 0, "", ("164.100.230.216", 443)),
            (2, 0, 0, "", ("127.0.0.1", 443)),
        ]
        with patch("socket.getaddrinfo", return_value=mock_infos):
            self.assertTrue(_resolves_to_disallowed_ip("dcmsme.gov.in"))

        mock_infos_nat64 = [
            (2, 0, 0, "", ("164.100.230.216", 443)),
            (23, 0, 0, "", ("64:ff9b::a9fe:a9fe", 443, 0, 0)),  # metadata
        ]
        with patch("socket.getaddrinfo", return_value=mock_infos_nat64):
            self.assertTrue(_resolves_to_disallowed_ip("dcmsme.gov.in"))

    def test_ipv4_mapped_ipv6_destinations(self):
        from app.core.url_validator import _is_private_or_reserved_ip

        self.assertFalse(_is_private_or_reserved_ip("::ffff:164.100.230.216"))
        self.assertTrue(_is_private_or_reserved_ip("::ffff:127.0.0.1"))
        self.assertTrue(_is_private_or_reserved_ip("::ffff:169.254.169.254"))
        self.assertTrue(_is_private_or_reserved_ip("::ffff:10.0.0.1"))

    def test_literal_ip_urls_never_bypass_domain_allowlist(self):
        # Even with safe public NAT64 IPs, raw IP literals in URLs must not match approved domains
        res1 = validate_url("https://[64:ff9b::a464:e6d8]/schemes", DEFAULT_APPROVED_SOURCES, resolve_dns=False)
        self.assertFalse(res1.is_valid)

        res2 = validate_url("https://[64:ff9b::7f00:1]/schemes", DEFAULT_APPROVED_SOURCES, resolve_dns=False)
        self.assertFalse(res2.is_valid)


if __name__ == "__main__":
    unittest.main()

