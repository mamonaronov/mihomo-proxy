from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "config.yaml"


def _mihomo_group(text: str, name: str) -> str:
    marker = f"- name: {name}"
    rest = text.split("proxy-groups:", 1)[1]
    start = rest.index(marker)
    tail = rest[start + len(marker) :]
    nxt = tail.find("\n  - name:")
    return rest[start:] if nxt < 0 else rest[start : start + len(marker) + nxt]


def _active_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


class TestMihomoConfig(unittest.TestCase):
    def test_mihomo_auto_is_fallback_of_tunnel_providers(self) -> None:
        text = CONFIG.read_text(encoding="utf-8")
        auto = _mihomo_group(text, "AUTO")
        fast = _mihomo_group(text, "FAST")
        backup = _mihomo_group(text, "BACKUP")
        self.assertIn("type: fallback", auto)
        self.assertNotIn("type: url-test", auto)
        self.assertIn("- FAST", auto)
        self.assertIn("- BACKUP", auto)
        self.assertNotIn("include-all-providers:", auto)
        self.assertIn("url: https://api.telegram.org/bot", auto)
        self.assertIn("expected-status: 404", auto)
        self.assertIn("max-failed-times: 1", auto)
        self.assertIn("type: url-test", fast)
        self.assertIn("tolerance:", fast)
        self.assertIn("interval: 30", fast)
        self.assertNotIn("interval: 120", fast)
        self.assertIn("timeout: 4000", fast)
        self.assertNotIn("timeout: 2500", fast)
        self.assertIn("Anycast", fast)
        fast_use = fast.split("use:", 1)[1].split("url:", 1)[0]
        self.assertIn("- sub3", fast_use)
        self.assertNotIn("- sub1", fast_use)
        self.assertNotIn("- sub2", fast_use)
        self.assertNotIn("- sub4", fast_use)
        self.assertNotIn("- sub5", fast_use)
        self.assertIn("type: fallback", backup)
        self.assertNotIn("type: url-test", backup)
        self.assertIn("lazy: true", backup)
        self.assertIn("timeout: 4000", backup)
        self.assertIn("max-failed-times: 1", backup)
        backup_use = backup.split("use:", 1)[1].split("url:", 1)[0]
        self.assertIn("- sub1", backup_use)
        self.assertIn("- sub2", backup_use)
        self.assertNotIn("- sub3", backup_use)
        self.assertNotIn("- sub4", backup_use)
        self.assertNotIn("- sub5", backup_use)
        whitelist = _mihomo_group(text, "WHITELIST")
        self.assertIn("- sub4", whitelist)
        self.assertIn("- sub5", whitelist)
        self.assertIn("MATCH,AUTO", text)
        self.assertNotIn("MATCH,WHITELIST", text)
        self.assertIn("interval: 300", text)
        self.assertGreaterEqual(text.count("lazy: true"), 6)
        self.assertIn("timeout: 4000", auto)
        self.assertNotIn("    proxy: AUTO\n", text)
        self.assertEqual(sum(1 for line in _active_lines(text) if line.strip() == "proxy: DIRECT"), 0)
        self.assertEqual(sum(1 for line in _active_lines(text) if line.strip() == "proxy: SUBSCRIBE"), 5)
        subscribe = _mihomo_group(text, "SUBSCRIBE")
        self.assertIn("type: fallback", subscribe)
        self.assertIn("- DIRECT", subscribe)
        self.assertIn("- AUTO", subscribe)
        self.assertNotIn("api.telegram.org", subscribe)
        self.assertLess(subscribe.find("- DIRECT"), subscribe.find("- AUTO"))
        self.assertIn("url: https://github.com/favicon.ico", subscribe)

    def test_template_has_placeholders_not_secrets_or_urls(self) -> None:
        text = CONFIG.read_text(encoding="utf-8")
        self.assertNotIn("raw.githubusercontent.com", text)
        self.assertNotIn("8176598712630598761082765412765789012506456781928765078960", text)
        self.assertNotIn("compose up --build", text)
        self.assertIn('secret: "${MIHOMO_API_SECRET}"', text)
        for n in range(1, 9):
            self.assertIn(f'url: "${{SUB{n}_URL}}"', text)
        self.assertNotIn("REPLACE_ME", text)
        self.assertIn('bind-address: "*"', text)
        self.assertIn("allow-lan: true", text)
        self.assertIn("mixed-port: 11808", text)
        self.assertIn("external-controller: 0.0.0.0:19090", text)

    def test_dns_uses_doh_not_fake_ip(self) -> None:
        text = CONFIG.read_text(encoding="utf-8")
        dns = text.split("proxy-providers:", 1)[0].split("\ndns:", 1)[1]
        active = "\n".join(_active_lines(dns))
        self.assertIn("enhanced-mode: redir-host", active)
        self.assertNotIn("enhanced-mode: fake-ip", active)
        self.assertIn("https://1.1.1.1/dns-query", active)
        self.assertIn("https://8.8.8.8/dns-query", active)
        self.assertNotIn("tls://1.1.1.1", active)
        self.assertNotIn("tls://8.8.8.8", active)
        nameserver = active.split("\n  nameserver:", 1)[1].split("\n  fallback:", 1)[0]
        self.assertNotIn("- 8.8.8.8", nameserver)
        self.assertNotIn("- 1.1.1.1", nameserver)
        self.assertIn("default-nameserver:", active)


if __name__ == "__main__":
    unittest.main()
