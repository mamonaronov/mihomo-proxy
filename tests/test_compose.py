from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestComposeAndEntrypoint(unittest.TestCase):
    def test_compose_has_no_ports_or_named_volumes(self) -> None:
        text = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("ports:", text)
        self.assertNotIn("network_mode:", text)
        self.assertNotIn("privileged:", text)
        self.assertIn("./data:/etc/mihomo", text)
        self.assertIn("./data:/root/.config/mihomo", text)
        self.assertIn("container_name: mihomo-proxy", text)
        self.assertIn("name: telegram-proxy", text)
        self.assertIn("aliases:", text)
        self.assertIn("- proxy", text)
        self.assertIn("env_file: .env", text)
        self.assertIn("nofile:", text)
        self.assertIn("1048576", text)
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("-") and ":/etc/mihomo" in stripped:
                self.assertTrue(stripped.startswith("- ./data:"))

    def test_entrypoint_uses_pipefail_and_exec(self) -> None:
        text = (REPO / "docker-entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", text)
        self.assertIn("exec /mihomo", text)
        self.assertIn(
            "envsubst '${SUB1_URL} ${SUB2_URL} ${SUB3_URL} ${SUB4_URL} ${SUB5_URL} ${SUB6_URL} ${SUB7_URL} ${SUB8_URL} ${MIHOMO_API_SECRET}'",
            text,
        )

    def test_readme_has_no_host_mihomo_or_host_network(self) -> None:
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("yay -S mihomo", text)
        self.assertNotIn("network_mode: host", text)
        self.assertNotIn("host network", text.lower())


if __name__ == "__main__":
    unittest.main()
