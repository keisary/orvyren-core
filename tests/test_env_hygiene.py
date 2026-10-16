#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN-Core — tests W5/L5.2 : hygiène des secrets et scripts de montage.

Hors ligne (git local pour l'hygiène), aucune clé réelle, aucun réseau :

* ``check_env_hygiene`` — .env versionné détecté (H1), valeur de clé dans un
  fichier suivi détectée (H2), .gitignore vérifié (H3), dépôt propre (OK) ;
* ``verify_addresses`` — mode offline : format EIP-55, complétude, écart = FAIL ;
* ``faucet_check`` — mode offline : OFFLINE_PASS (aucun réseau) ;
* ``generate_signer_key`` — génération dans un fichier temporaire, garde-fou
  anti-écrasement, ``--check`` adresse dérivée ↔ déclarée (eth-account requis).

Run: python -m pytest tests/test_env_hygiene.py -q
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from demo import check_env_hygiene, faucet_check, generate_signer_key, verify_addresses  # noqa: E402

GOOD_SAFE = "0x000e11a54daadf202542a0136f974f24d7c38be0"
GOOD_AGENT = "0xe1039e345fa2ad9ecceab7bb160fd5e53f58f01c"
GOOD_MODULE = "0x7e2b7798ab4b4db837b30107f0d2a3ffb24e95e8"
GOOD_USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
FAKE_KEY = "0x" + "aa" * 32  # clé FACTICE (test seulement — jamais une clé réelle)


def _git(root, *args):
    return subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)


@unittest.skipUnless(shutil.which("git"), "git requis pour les tests d'hygiène")
class EnvHygieneTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_hygiene_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        init = _git(self.tmp, "init", "-q")
        if init.returncode != 0:
            self.skipTest("git init indisponible")

    def _write(self, rel, content):
        path = os.path.join(self.tmp, rel)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        return path

    def test_tracked_env_detected_then_clean(self):
        env = self._write(".env", "ORVYREN_PRIVATE_KEY=%s\n" % FAKE_KEY)
        self._write("normal.txt", "texte anodin\n")
        _git(self.tmp, "add", "normal.txt")
        report = check_env_hygiene.run(env_files=[env], repo_root=self.tmp)
        ids = {check["id"]: check for check in report["checks"]}
        self.assertEqual(ids["H1.tracked_env"]["status"], "PASS")  # pas encore suivi

        _git(self.tmp, "add", "-f", ".env")
        report = check_env_hygiene.run(env_files=[env], repo_root=self.tmp)
        ids = {check["id"]: check for check in report["checks"]}
        self.assertEqual(ids["H1.tracked_env"]["status"], "FAIL")
        self.assertEqual(report["verdict"], "FAIL")

    def test_secret_value_in_tracked_file_detected(self):
        env = self._write(".env", "ORVYREN_PRIVATE_KEY=%s\n" % FAKE_KEY)
        leak = self._write("leak.txt", "valeur: %s : fin\n" % FAKE_KEY)
        self._write(".gitignore", ".env\n")
        _git(self.tmp, "add", "leak.txt", ".gitignore")
        report = check_env_hygiene.run(env_files=[env], repo_root=self.tmp)
        ids = {check["id"]: check for check in report["checks"]}
        self.assertEqual(ids["H2.secret_values"]["status"], "FAIL")
        self.assertIn("leak.txt", ids["H2.secret_values"]["detail"])

        _git(self.tmp, "rm", "-q", "--cached", "leak.txt")
        os.unlink(leak)
        self._write("clean.txt", "aucun secret ici\n")
        _git(self.tmp, "add", "clean.txt")
        report = check_env_hygiene.run(env_files=[env], repo_root=self.tmp)
        ids = {check["id"]: check for check in report["checks"]}
        self.assertEqual(ids["H2.secret_values"]["status"], "PASS")
        self.assertEqual(ids["H1.tracked_env"]["status"], "PASS")
        self.assertEqual(report["verdict"], "OK")

    def test_not_ignored_env_detected(self):
        env = self._write(".env", "ORVYREN_PRIVATE_KEY=%s\n" % FAKE_KEY)
        self._write(".gitignore", "autre-chose\n")
        _git(self.tmp, "add", ".gitignore")
        report = check_env_hygiene.run(env_files=[env], repo_root=self.tmp)
        ids = {check["id"]: check for check in report["checks"]}
        self.assertEqual(ids["H3.gitignore"]["status"], "FAIL")


class VerifyAddressesOfflineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orvyren_addr_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.env = os.path.join(self.tmp, ".env")
        with open(self.env, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("ORVYREN_SAFE_ADDRESS=%s\nORVYREN_AGENT_ADDRESS=%s\n"
                         "ORVYREN_MODULE_ADDRESS=%s\nORVYREN_USDC_ADDRESS=%s\n"
                         % (GOOD_SAFE, GOOD_AGENT, GOOD_MODULE, GOOD_USDC))

    def test_offline_pass(self):
        report = verify_addresses.run(env_files=[self.env], rpc_url=None,
                                      expected_chain_id=84532)
        self.assertEqual(report["verdict"], "OFFLINE_PASS")
        self.assertEqual(len(report["addresses"]), 4)

    def test_bad_format_fails(self):
        with open(self.env, "a", encoding="utf-8", newline="\n") as handle:
            handle.write("ORVYREN_RECIPIENT_B=0x123\n")
        report = verify_addresses.run(env_files=[self.env], rpc_url=None,
                                      expected_chain_id=84532)
        self.assertEqual(report["verdict"], "FAIL")
        bad = [entry for entry in report["addresses"] if entry["key"] == "ORVYREN_RECIPIENT_B"]
        self.assertEqual(bad[0]["status"], "FAIL")

    def test_missing_required_fails(self):
        with open(self.env, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("ORVYREN_AGENT_ADDRESS=%s\n" % GOOD_AGENT)
        report = verify_addresses.run(env_files=[self.env], rpc_url=None,
                                      expected_chain_id=84532)
        self.assertEqual(report["verdict"], "FAIL")


class FaucetOfflineTest(unittest.TestCase):
    def test_offline_pass_exit_zero(self):
        env = {"ORVYREN_AGENT_ADDRESS": GOOD_AGENT, "ORVYREN_SAFE_ADDRESS": GOOD_SAFE,
               "ORVYREN_USDC_ADDRESS": GOOD_USDC}
        report = faucet_check.run(env=env, rpc_url=None, min_eth=0.001, min_usdc=1.0)
        self.assertEqual(report["verdict"], "OFFLINE_PASS")
        with tempfile.TemporaryDirectory(prefix="orvyren_faucet_") as tmp:
            env_path = os.path.join(tmp, ".env")
            with open(env_path, "w", encoding="utf-8", newline="\n") as handle:
                for key, value in env.items():
                    handle.write("%s=%s\n" % (key, value))
            self.assertEqual(faucet_check.main(["--env-file", env_path, "--quiet"]),
                             faucet_check.EXIT_OK)


@unittest.skipUnless(generate_signer_key._require_eth_account, "eth-account requis")
class GenerateSignerKeyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from eth_account import Account  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("eth-account requis")

    def test_generate_and_check_roundtrip(self):
        from eth_account import Account
        with tempfile.TemporaryDirectory(prefix="orvyren_key_") as tmp:
            env_path = os.path.join(tmp, ".env")
            report = generate_signer_key.generate(env_path, force=False)
            self.assertTrue(os.path.isfile(env_path))
            values = {}
            with open(env_path, "r", encoding="utf-8") as handle:
                for line in handle:
                    if "=" in line and not line.strip().startswith("#"):
                        key, _, value = line.partition("=")
                        values[key.strip()] = value.strip()
            self.assertIn("ORVYREN_PRIVATE_KEY", values)
            self.assertTrue(values["ORVYREN_PRIVATE_KEY"].startswith("0x"))
            derived = Account.from_key(values["ORVYREN_PRIVATE_KEY"]).address
            self.assertEqual(values["ORVYREN_AGENT_ADDRESS"], derived)
            self.assertEqual(report["agent_address"], derived)

            check = generate_signer_key.check_existing(env_path)
            self.assertTrue(check["match"])

            with self.assertRaises(SystemExit) as ctx:
                generate_signer_key.generate(env_path, force=False)
            self.assertEqual(ctx.exception.code, generate_signer_key.EXIT_REFUSED)

            first_key = values["ORVYREN_PRIVATE_KEY"]
            generate_signer_key.generate(env_path, force=True)
            with open(env_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            self.assertNotIn(first_key, content)


if __name__ == "__main__":
    unittest.main()
