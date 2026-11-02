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
    def test_auto_uses_free_then_paid(self) -> None:
        text = CONFIG.read_text(encoding="utf-8")
        free = _mihomo_group(text, "FREE")
        paid = _mihomo_group(text, "PAID")
        auto = _mihomo_group(text, "AUTO")
        self.assertIn("type: url-test", free)
        self.assertNotIn("type: fallback", free)
        self.assertNotIn("include-all-providers:", free)
        self.assertIn("url: https://api.telegram.org/bot", free)
        self.assertIn("expected-status: 404", free)
        self.assertIn("max-failed-times: 1", free)
        self.assertIn("tolerance:", free)
        self.assertIn("interval: 30", free)
        self.assertNotIn("interval: 120", free)
        self.assertIn("timeout: 4000", free)
        self.assertNotIn("timeout: 2500", free)
        self.assertIn("lazy: false", free)
        self.assertIn("Anycast", free)
        self.assertNotIn("Singapore", free)
        names = (
            "🏴 ЧЕРНЫЕ СПИСКИ 🏴 BLACK LISTS | Полная • Full | VLESS",
            "🏴 ЧЕРНЫЕ СПИСКИ 🏴 BLACK LISTS | Полная • Full | SS, Hy2, Vmess, Trojan",
            "🏴 ЧЕРНЫЕ СПИСКИ 🏴 BLACK LISTS | Mobile-150",
            "🏳️ БЕЛЫЕ СПИСКИ 🏳️ WHITE LISTS | CIDR | Полная • Full",
            "🏳️ БЕЛЫЕ СПИСКИ 🏳️ WHITE LISTS | SNI-RU",
        )
        free_use = free.split("use:", 1)[1].split("url:", 1)[0]
        for name in names:
            self.assertIn(f'- "{name}"', free_use)
            self.assertIn(f'  "{name}":', text)
            self.assertIn(f'additional-prefix: "{name} | "', text)
            self.assertNotIn(name, paid)
        for sub in ("sub1", "sub2", "sub3", "sub4", "sub5"):
            self.assertNotIn(f"\n  {sub}:\n", text)
            self.assertNotIn(f"- {sub}\n", free_use)
        self.assertIn("type: url-test", paid)
        self.assertIn("lazy: false", paid)
        self.assertNotIn("lazy: true", paid)
        self.assertIn("interval: 60", paid)
        self.assertIn('use:\n      - "Платная"', paid)
        self.assertIn('url: "${PAID_URL}"', text)
        begin = [line for line in text.splitlines() if line.strip() == "# paid-begin"]
        end = [line for line in text.splitlines() if line.strip() == "# paid-end"]
        self.assertEqual(len(begin), 3)
        self.assertEqual(len(end), 3)
        self.assertIn('additional-prefix: "Платная | "', text)
        self.assertIn("path: ./providers/paid.yaml", text)
        self.assertIn("type: fallback", auto)
        self.assertNotIn("type: url-test", auto)
        self.assertNotIn("tolerance:", auto)
        self.assertNotIn("use:", auto)
        auto_proxies = auto.split("proxies:", 1)[1].split("url:", 1)[0]
        self.assertLess(auto_proxies.find("- FREE"), auto_proxies.find("- PAID"))
        self.assertNotIn("- name: FAST", text)
        self.assertNotIn("- name: BACKUP", text)
        self.assertNotIn("- name: WHITELIST", text)
        proxy = _mihomo_group(text, "PROXY")
        self.assertIn("- AUTO", proxy)
        self.assertIn("- DIRECT", proxy)
        self.assertNotIn("WHITELIST", proxy)
        self.assertIn("MATCH,AUTO", text)
        self.assertIn("interval: 300", text)
        paid_provider = text.split('  "Платная":', 1)[1].split("# paid-end", 1)[0]
        self.assertIn("\n      interval: 60\n", paid_provider)
        self.assertIn("lazy: false", paid_provider)
        self.assertNotIn("lazy: true", paid_provider)
        self.assertEqual(text.count("lazy: true"), 5)
        self.assertEqual(
            sum(1 for line in _active_lines(text) if line.strip() == "interval: 900"),
            6,
        )
        self.assertNotIn("interval: 3600", "\n".join(_active_lines(text)))
        self.assertNotIn("    proxy: AUTO\n", text)
        self.assertEqual(sum(1 for line in _active_lines(text) if line.strip() == "proxy: DIRECT"), 0)
        self.assertEqual(sum(1 for line in _active_lines(text) if line.strip() == "proxy: SUBSCRIBE"), 6)
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
        self.assertIn('url: "${PAID_URL}"', text)
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
