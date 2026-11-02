from __future__ import annotations

import subprocess
import tempfile
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
        self.assertIn("./config.yaml:/template/config.yaml:ro", text)
        self.assertIn("image: mihomo-proxy", text)
        self.assertNotIn("v1.19.31", text)
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
            "envsubst '${SUB1_URL} ${SUB2_URL} ${SUB3_URL} ${SUB4_URL} ${SUB5_URL} ${SUB6_URL} ${SUB7_URL} ${SUB8_URL} ${PAID_URL} ${MIHOMO_API_SECRET}'",
            text,
        )
        self.assertIn("change-me", text)
        self.assertIn("REPLACE_ME", text)
        self.assertIn("is a placeholder", text)
        self.assertIn(
            "for var in SUB1_URL SUB2_URL SUB3_URL SUB4_URL SUB5_URL MIHOMO_API_SECRET; do",
            text,
        )
        self.assertNotIn("SUB5_URL PAID_URL", text)
        self.assertIn('if [ -z "$PAID_URL" ]; then', text)

    def test_empty_paid_url_drops_paid_blocks(self) -> None:
        entry = (REPO / "docker-entrypoint.sh").read_text(encoding="utf-8")
        deploy = (REPO / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("for var in SUB1_URL SUB2_URL SUB3_URL SUB4_URL SUB5_URL; do", deploy)
        self.assertNotIn("SUB5_URL PAID_URL", deploy)
        start = entry.index("drop_paid_blocks()")
        func = entry[start : entry.index("\n}\n", start) + 3]
        template = (REPO / "config.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.yaml"
            dst = Path(tmp) / "out.yaml"
            src.write_text(template, encoding="utf-8")
            subprocess.check_call(["sh", "-c", func + f'\ndrop_paid_blocks "{src}" "{dst}"\n'])
            out = dst.read_text(encoding="utf-8")
        self.assertNotIn("Платная", out)
        self.assertNotIn("- name: PAID", out)
        self.assertNotIn("- PAID", out)
        self.assertFalse(any(line.strip() == "# paid-begin" for line in out.splitlines()))
        self.assertFalse(any(line.strip() == "# paid-end" for line in out.splitlines()))
        self.assertIn("- name: FREE", out)
        self.assertIn("- name: AUTO", out)
        self.assertIn("MATCH,AUTO", out)
        auto = out.split("- name: AUTO", 1)[1].split("- name: SUBSCRIBE", 1)[0]
        self.assertIn("- FREE", auto)
        self.assertIn('url: "${SUB1_URL}"', out)

    def test_dockerfile_is_the_only_mihomo_base_tag(self) -> None:
        dockerfile = (REPO / "Dockerfile").read_text(encoding="utf-8")
        self.assertRegex(dockerfile, r"^FROM metacubex/mihomo:latest\n")
        compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertNotRegex(compose, r"mihomo-proxy:v\d+")

    def test_dockerignore_keeps_env_and_data_out_of_build(self) -> None:
        text = (REPO / ".dockerignore").read_text(encoding="utf-8")
        self.assertIn(".env", text)
        self.assertIn("data", text)
        lines = text.splitlines()
        self.assertIn("tests", lines)
        self.assertIn("deploy.sh", lines)
        self.assertIn("deploy", lines)
        self.assertNotIn("config.yaml", lines)
        self.assertNotIn("docker-entrypoint.sh", lines)

    def test_readme_has_no_host_mihomo_or_host_network(self) -> None:
        text = (REPO / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("yay -S mihomo", text)
        self.assertNotIn("network_mode: host", text)
        self.assertNotIn("host network", text.lower())
        self.assertNotIn("8176598712630598761082765412765789012506456781928765078960", text)
        self.assertIn("./deploy.sh", text)
        self.assertIn("git pull --ff-only", text)


if __name__ == "__main__":
    unittest.main()
