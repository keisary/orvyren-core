"""Vérification ciblée du fix P0 (Astra 18/10) — `_verify_hashed_jsonl`.

Le head recomputé de la DERNIÈRE ligne doit être comparé au hash enregistré
de cette ligne. Sans cette comparaison, une dernière ligne altérée (payload
modifié, record_hash conservé) passe la vérification.
"""

import hashlib
import json
import unittest

from orvyren.api.artifacts import _verify_hashed_jsonl

GENESIS = "0" * 64


def digest(payload):
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_chain():
    """Chaîne valide sous la forme « all_minus_hash » (hash = digest sans hash)."""
    row0 = {"seq": 1, "content": "a", "prev": GENESIS, "record_hash": ""}
    row0["record_hash"] = digest({k: v for k, v in row0.items() if k != "record_hash"})
    row1 = {"seq": 2, "content": "b", "prev": row0["record_hash"], "record_hash": ""}
    row1["record_hash"] = digest({k: v for k, v in row1.items() if k != "record_hash"})
    return [row0, row1]


class VerifyHashedJsonlTest(unittest.TestCase):
    def test_intact_chain_verified(self):
        rows = build_chain()
        report = _verify_hashed_jsonl(rows, "record_hash", "prev", GENESIS)
        self.assertTrue(report["links_ok"])
        self.assertTrue(report["verified"])
        self.assertEqual(report["hash_form"], "all_minus_hash")
        self.assertEqual(report["head"], rows[-1]["record_hash"])

    def test_tampered_last_row_is_not_verified(self):
        rows = build_chain()
        rows[-1]["content"] = "tampered"  # payload altéré, record_hash inchangé
        report = _verify_hashed_jsonl(rows, "record_hash", "prev", GENESIS)
        self.assertFalse(report["verified"])
        self.assertEqual(report["hash_form"], "not_reproduced")

    def test_broken_prev_link_is_not_verified(self):
        rows = build_chain()
        rows[1]["prev"] = "f" * 64
        report = _verify_hashed_jsonl(rows, "record_hash", "prev", GENESIS)
        self.assertFalse(report["links_ok"])
        self.assertFalse(report["verified"])


if __name__ == "__main__":
    unittest.main()
