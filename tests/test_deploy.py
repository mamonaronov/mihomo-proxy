from __future__ import annotations

import os
import re
import stat
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestDeploy(unittest.TestCase):
    def test_deploy_sh_is_valid_executable_bash(self) -> None:
        path = REPO / "deploy.sh"
        subprocess.check_call(["bash", "-n", str(path)])
        mode = path.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, f"{path} must be executable")
        self.assertTrue(os.access(path, os.X_OK), f"{path} must be executable")

    def test_deploy_sh_rebuilds_with_pull_and_recreate(self) -> None:
        text = (REPO / "deploy.sh").read_text(encoding="utf-8")
        self.assertIn("docker compose up -d --build --pull always --force-recreate", text)
        self.assertIn("--skip-docker", text)
        self.assertIn("git pull --ff-only && ./deploy.sh", text)
        self.assertNotIn("yay -S", text)
        self.assertNotIn("pacman -S", text)
        self.assertNotIn("compose down -v", text)
        self.assertNotIn("network_mode", text)
        self.assertIn("MIHOMO_API_SECRET", text)
        self.assertIn("change-me", text)
        self.assertIn("mihomo-proxy.service", text)
        self.assertIn("does not change .env", text.lower())

    def test_deploy_sh_does_not_fetch_git(self) -> None:
        text = (REPO / "deploy.sh").read_text(encoding="utf-8")
        self.assertNotIn("git fetch", text)
        self.assertNotRegex(text, re.compile(r"^\s*git pull\b", re.M))

    def test_systemd_unit_starts_compose_not_host_mihomo(self) -> None:
        text = (REPO / "deploy" / "mihomo-proxy.service").read_text(encoding="utf-8")
        self.assertIn("Type=oneshot", text)
        self.assertIn("RemainAfterExit=yes", text)
        self.assertIn("Requires=docker.service", text)
        self.assertIn("docker compose up -d", text)
        self.assertIn("docker compose stop", text)
        self.assertNotIn("ExecStart=/usr/bin/mihomo", text)
        self.assertNotIn("/etc/mihomo", text)


if __name__ == "__main__":
    unittest.main()
