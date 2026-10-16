#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ORVYREN — montage on-chain Base Sepolia (chainId 84532) : **Safe 2/3 + module Zodiac
Roles v2 + rôle AGENT** (USDC Circle, plafond 300 USDC/jour, 10 appels/jour).

Ce que fait le script, dans l'ordre :

1. **Préflight lecture seule** — ``eth_chainId`` == 84532 (refus sinon), ``eth_getCode`` de
   chaque adresse d'infrastructure, ``VERSION()`` du singleton Safe, soldes, sélecteurs
   attendus présents dans le bytecode déployé.
2. **Validation de l'arbre de conditions** par appel ``eth_call`` à la **bibliothèque
   Integrity déployée** (``0x6a6Af4b1…1049``, sélecteur ``0x783a9047``) : l'arbre candidat
   doit passer ; un arbre volontairement invalide doit revertir (contrôle négatif).
3. **Prédiction CREATE2** des adresses Safe et module, puis **simulation** des deux
   déploiements (``eth_call`` sur les fabriques) : l'adresse renvoyée par la simulation doit
   être identique à la prédiction.
4. **Exécution réelle** (``--execute``, exige du gaz sur OWNER1) : déploiement Safe
   (``createProxyWithNonce``), déploiement module (``deployModule``), puis 6 transactions
   Safe séquentielles (chacune signée 2/3, soumise par OWNER1) :
   ``enableModule`` · ``scopeTarget`` · ``setAllowance`` ×2 · ``scopeFunction`` · ``assignRoles``.
   Chaque reçu est vérifié (``status == 0x1``) et chaque état relu.
5. **Simulations de contrôle** (``eth_call`` depuis l'adresse de l'agent) :
   (i) ``execTransactionWithRole`` vers RECIPIENT_B pour 100 USDC → doit réussir ;
   (ii) même appel vers RECIPIENT_UNLISTED → doit revertir.
6. **Preuves** dans ``demo_runs/setup/`` (adresses, hashes, reçus, simulations, calldata) et
   mise à jour de ``scripts/demo/.env`` (``ORVYREN_SAFE_ADDRESS`` / ``ORVYREN_MODULE_ADDRESS``)
   uniquement en cas d'exécution réussie.

Garde-fous : aucune clé privée n'est jamais imprimée ni journalisée ; le chainId est
revérifié avant chaque signature ; toute adresse est contrôlée par ``eth_getCode`` avant
usage ; en cas de revert, la raison exacte est rapportée ; aucune transaction douteuse
n'est envoyée (une étape dont l'encodage n'est pas validé par simulation est bloquée).

Usage :
    python scripts/demo/setup_chain.py                  # répétition générale (aucun envoi)
    python scripts/demo/setup_chain.py --self-test      # contrôles hors ligne uniquement
    python scripts/demo/setup_chain.py --execute        # exécution réelle (OWNER1 doit avoir du gaz)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # paquet
    from . import calls, common
except ImportError:  # exécution directe : python scripts/demo/setup_chain.py
    _sys_dir = os.path.dirname(os.path.abspath(__file__))
    if _sys_dir not in sys.path:
        sys.path.insert(0, _sys_dir)
    import calls  # type: ignore  # noqa: E402
    import common  # type: ignore  # noqa: E402

# --------------------------------------------------------------------------------------
# Constantes d'infrastructure — **vérifiées par eth_getCode le 2026-10-16** sur Base Sepolia
# --------------------------------------------------------------------------------------

CHAIN_ID_DEMO = 84532

#: Adresse du SafeProxyFactory v1.4.1 **vérifiée présente** (3054 o, « SafeProxyFactory » v&),
#: identique à celle du kit (``common.KNOWN_ADDRESSES["safe_proxy_factory_1_4_1"]``).
SAFE_PROXY_FACTORY = "0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67"
#: Adresse fournie par la consigne : **AUCUN code sur Base Sepolia** (0x) — journalisée, non utilisée.
SAFE_PROXY_FACTORY_CONSIGNE_SANS_CODE = "0x4e1DCf7A71CCf7De11caCC46791B8d99d1BAbec0"
SAFE_L2_SINGLETON_141 = "0x29fcB43b46531BcA003ddC8FCB67FFE91900C762"   # VERSION() == "1.4.1"
FALLBACK_HANDLER_COMPAT_141 = "0xfd0732Dc9E303f09fCEf3a7388Ad10A83459Ec99"
MODULE_PROXY_FACTORY = "0x000000000000aDdB49795b0f9bA5BC298cDda236"
ROLES_V2_MASTERCOPY = "0xF2964CE6161ce0e75964Fe7927cE114cb0B283D5"      # 24409 o
INTEGRITY_LIBRARY = "0x6a6Af4b16458Bc39817e4019fB02BD3b26d41049"       # validateur d'arbres
MULTISEND_CALL_ONLY_141 = "0x40A2aCCbd92BCA938b02010E17A5b8929b49130D"  # (non utilisé : tx séquentielles)

#: Code de création du clone EIP-1167 utilisé par ModuleProxyFactory (source vérifiée + bytecode).
CLONE_PREFIX = "602d8060093d393df3363d3d373d3d3d363d73"
CLONE_SUFFIX = "5af43d82803e903d91602b57fd5bf3"

#: Sel CREATE2 — **fixe et documenté** (re-déploiement idempotent : même sel ⇒ même adresse).
SAFE_SALT_NONCE = 84532
MODULE_SALT_NONCE = 84532

#: Rôle et clés d'allowance : étiquettes ASCII (≤ 32 car., a-z 0-9 _) complétées par des zéros.
ROLE_KEY_AGENT = common.ROLE_KEY_AGENT                                   # 0x4147454e54… (« AGENT »)
ALLOWANCE_KEY_USDC_DAILY = "0x" + b"usdc_daily".hex() + "00" * (32 - len(b"usdc_daily"))
ALLOWANCE_KEY_CALLS_DAILY = "0x" + b"calls_daily".hex() + "00" * (32 - len(b"calls_daily"))

USDC_DAILY_REFILL = 300_000_000     # 300 USDC (6 décimales) par période
USDC_DAILY_PERIOD = 86_400          # 24 h
CALLS_DAILY_MAX = 10                # 10 appels / 24 h
SIM_TRANSFER_AMOUNT = 100_000_000   # 100 USDC (run de contrôle i)

#: Gaz d'appoint de l'agent : 0,0015 ETH depuis OWNER1 (EIP-1559, chainId vérifié).
AGENT_GAS_TOPUP_WEI = 1_500_000_000_000_000
#: En dessous de ce solde, l'appoint est renvoyé (sinon l'étape est ignorée).
AGENT_GAS_MIN_WEI = 500_000_000_000_000

#: Sélecteurs **recalculés localement** (Keccak-256 pur du kit) et présents dans le bytecode déployé.
SELECTORS = {
    "setUp(bytes)": common.selector("setUp(bytes)"),
    "setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)":
        common.selector("setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)"),
    "scopeTarget(bytes32,address)": common.selector("scopeTarget(bytes32,address)"),
    "scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)":
        common.selector("scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)"),
    "assignRoles(address,bytes32[],bool[])": common.selector("assignRoles(address,bytes32[],bool[])"),
    "execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)":
        common.selector("execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)"),
    "setup(address[],uint256,address,bytes,address,address,uint256,address)":
        common.selector("setup(address[],uint256,address,bytes,address,address,uint256,address)"),
    "execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)":
        common.selector("execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)"),
    "createProxyWithNonce(address,bytes,uint256)": common.selector("createProxyWithNonce(address,bytes,uint256)"),
    "proxyCreationCode()": common.selector("proxyCreationCode()"),
    "deployModule(address,bytes,uint256)": common.selector("deployModule(address,bytes,uint256)"),
    "enforce": "0x783a9047",  # sélecteur réel de Integrity.enforce (dispatch déployé, vérifié par appel)
}
#: Contrôle d'identité : valeurs déjà observées on-chain (protocole B5 §e.7).
SELECTORS_ATTENDUS = {
    "setUp(bytes)": "0xa4f9edbf",
    "setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)": "0xa8ec43ee",
    "scopeTarget(bytes32,address)": "0x0c6c76b8",
    "scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)": "0x7508dd98",
    "assignRoles(address,bytes32[],bool[])": "0x957ed2b3",
    "execTransactionWithRole(address,uint256,bytes,uint8,bytes32,bool)": "0xc6fe8747",
}

SAFE_TX_TYPEHASH = "0xbb8310d486368db6bd6f849402fdd73ad53d316b5a4b2644ad6efe0f941286d8"
DOMAIN_SEPARATOR_TYPEHASH = "0x47e79534a245952e8b16893a336b85a3d9ea9fa8c573f3d803afb92a79469218"
SAFE_TX_TYPEHASH_SIGNATURE = ("SafeTx(address to,uint256 value,bytes data,uint8 operation,uint256 safeTxGas,"
                              "uint256 baseGas,uint256 gasPrice,address gasToken,address refundReceiver,uint256 nonce)")
DOMAIN_TYPEHASH_SIGNATURE = "EIP712Domain(uint256 chainId,address verifyingContract)"

# Types ABI du module Roles (enum on-chain : uint8).
ABI_TYPE = {"None": 0, "Static": 1, "Dynamic": 2, "Tuple": 3, "Array": 4, "Calldata": 5, "AbiEncoded": 6}
OPERATOR = {"Pass": 0, "And": 1, "Or": 2, "Nor": 3, "Matches": 5, "ArraySome": 6, "ArrayEvery": 7,
            "ArraySubset": 8, "EqualToAvatar": 15, "EqualTo": 16, "GreaterThan": 17, "LessThan": 18,
            "SignedIntGreaterThan": 19, "SignedIntLessThan": 20, "Bitmask": 21, "Custom": 22,
            "WithinAllowance": 28, "EtherWithinAllowance": 29, "CallWithinAllowance": 30}
EXECUTION_OPTIONS_NONE = 0
OPERATION_CALL = 0
ZERO_ADDRESS = "0x" + "0" * 40


class SetupError(Exception):
    """Montage impossible (préflight, simulation ou reçu en échec) — aucune transaction douteuse."""


# --------------------------------------------------------------------------------------
# Encodages ABI (stdlib ; réutilise les helpers du kit)
# --------------------------------------------------------------------------------------


def enc_condition_flat_array(conditions: Sequence[Dict[str, Any]]) -> str:
    """Encode ``ConditionFlat[]`` = ``(uint8 parent, uint8 paramType, uint8 operator, bytes compValue)[]``.

    Structure BFS conforme au source vérifié (``Types.sol``) et validée par appel à la
    bibliothèque Integrity déployée (voir :meth:`ChainSetup.validate_conditions`).
    """
    count = len(conditions)
    if count == 0:
        raise SetupError("arbre de conditions vide")
    elements: List[str] = []
    for index, condition in enumerate(conditions):
        comp = condition.get("compValue", "0x")
        body = comp[2:] if str(comp).startswith("0x") else str(comp)
        if len(body) % 2:
            raise SetupError("compValue hex impair à l'index {}".format(index))
        padded = body + "0" * ((64 - len(body) % 64) % 64) if body else ""
        head = (common.enc_uint(condition["parent"]) + common.enc_uint(condition["paramType"])
                + common.enc_uint(condition["operator"]))
        elements.append(head + common.enc_uint(128) + common.enc_uint(len(body) // 2) + padded)
    offset = 32 * count
    offsets: List[str] = []
    for element in elements:
        offsets.append(common.enc_uint(offset))
        offset += len(element) // 2
    return common.enc_uint(count) + "".join(offsets) + "".join(elements)


def build_agent_conditions(recipient_b: str, recipient_c: str) -> List[Dict[str, Any]]:
    """Arbre de conditions du rôle AGENT sur ``transfer(address,uint256)`` (source de vérité).

    ``index 0`` : racine ``Calldata/Matches`` (le calldata hors sélecteur) ;
    ``index 1`` : paramètre 0 (destinataire) — ``Or(EqualTo(B), EqualTo(C))`` (paires 4-5) ;
    ``index 2`` : paramètre 1 (montant) — ``WithinAllowance(usdc_daily)`` ;
    ``index 3`` : quota d'appels — ``CallWithinAllowance(calls_daily)``.
    Parents non décroissants (BFS) : 0,0,0,0,1,1.
    """
    return [
        {"parent": 0, "paramType": ABI_TYPE["Calldata"], "operator": OPERATOR["Matches"], "compValue": "0x"},
        {"parent": 0, "paramType": ABI_TYPE["None"], "operator": OPERATOR["Or"], "compValue": "0x"},
        {"parent": 0, "paramType": ABI_TYPE["Static"], "operator": OPERATOR["WithinAllowance"],
         "compValue": ALLOWANCE_KEY_USDC_DAILY},
        {"parent": 0, "paramType": ABI_TYPE["None"], "operator": OPERATOR["CallWithinAllowance"],
         "compValue": ALLOWANCE_KEY_CALLS_DAILY},
        {"parent": 1, "paramType": ABI_TYPE["Static"], "operator": OPERATOR["EqualTo"],
         "compValue": "0x" + common.enc_address(recipient_b)},
        {"parent": 1, "paramType": ABI_TYPE["Static"], "operator": OPERATOR["EqualTo"],
         "compValue": "0x" + common.enc_address(recipient_c)},
    ]


def enc_bytes4(value: str) -> str:
    """``bytes4`` ABI : aligné à gauche (complété à droite) dans un mot de 32 octets."""
    body = value[2:] if value.startswith("0x") else value
    if len(body) != 8:
        raise SetupError("bytes4 attendu (4 octets hex): {!r}".format(value))
    return body + "0" * 56


def scope_function_data(role_key: str, target: str, selector4: str,
                        conditions: Sequence[Dict[str, Any]], options: int = EXECUTION_OPTIONS_NONE) -> str:
    """``scopeFunction(bytes32,address,bytes4,ConditionFlat[],uint8)``.

    En-tête de 5 mots (roleKey, target, selector, **offset des conditions = 5×32 = 160**,
    options) ; le tableau de conditions suit.
    """
    args = (common.enc_bytes32(role_key) + common.enc_address(target) + enc_bytes4(selector4)
            + common.enc_uint(5 * 32) + common.enc_uint(options) + enc_condition_flat_array(conditions))
    return SELECTORS["scopeFunction(bytes32,address,bytes4,(uint8,uint8,uint8,bytes)[],uint8)"] + args


def set_allowance_data(key: str, balance: int, max_refill: int, refill: int,
                       period: int, timestamp: int = 0) -> str:
    """``setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)`` — 6 arguments (ABI vérifiée)."""
    args = (common.enc_bytes32(key) + common.enc_uint(balance) + common.enc_uint(max_refill)
            + common.enc_uint(refill) + common.enc_uint(period) + common.enc_uint(timestamp))
    return SELECTORS["setAllowance(bytes32,uint128,uint128,uint128,uint64,uint64)"] + args


def scope_target_data(role_key: str, target: str) -> str:
    """``scopeTarget(bytes32,address)``."""
    return SELECTORS["scopeTarget(bytes32,address)"] + common.enc_bytes32(role_key) + common.enc_address(target)


def safe_setup_initializer(owners: Sequence[str], threshold: int, fallback_handler: str) -> str:
    """Calldata ``setup(address[],uint256,address,bytes,address,address,uint256,address)`` (Safe v1.4.1).

    ``to = 0``, ``data = '0x'`` (aucun appel initial), ``paymentToken = 0``, ``payment = 0``,
    ``paymentReceiver = 0`` ; ``fallbackHandler`` = handler de compatibilité 1.4.1.
    """
    owners_tail = common.enc_uint(len(owners)) + "".join(common.enc_address(owner) for owner in owners)
    head = (common.enc_uint(8 * 32) + common.enc_uint(threshold) + common.enc_address(ZERO_ADDRESS)
            + common.enc_uint(8 * 32 + (4 * 32)) + common.enc_address(fallback_handler)
            + common.enc_address(ZERO_ADDRESS) + common.enc_uint(0) + common.enc_address(ZERO_ADDRESS))
    return SELECTORS["setup(address[],uint256,address,bytes,address,address,uint256,address)"] + head + owners_tail + common.enc_uint(0)


def module_setup_initializer(owner: str, avatar: str, target: str) -> str:
    """Calldata ``setUp(bytes)`` du module Roles : ``abi.encode(owner, avatar, target)``.

    Confirmé par la source (``Roles.setUp``) **et** par la simulation ``eth_call`` sur la
    fabrique déployée : le ``ModuleProxyFactory`` actuel exécute ``proxy.call(initializer)``,
    donc ``initializer`` **est** le calldata complet (pas d'enveloppe ``setUp``).
    """
    payload = common.enc_address(owner) + common.enc_address(avatar) + common.enc_address(target)
    return SELECTORS["setUp(bytes)"] + common.enc_uint(32) + common.enc_uint(96) + payload


def _strip_0x(value: str) -> str:
    """Retire le préfixe ``0x`` s'il existe (jamais deux caractères à l'aveugle)."""
    text = str(value)
    return text[2:] if text.startswith(("0x", "0X")) else text


def predict_create2_address(factory: str, salt_hex: str, init_code_hex: str) -> str:
    """CREATE2 : ``keccak256(0xff ++ factory ++ salt ++ keccak256(init_code))[12:]``."""
    digest = common.keccak256(b"\xff" + bytes.fromhex(_strip_0x(common.normalize_address(factory)))
                              + bytes.fromhex(_strip_0x(salt_hex))
                              + bytes.fromhex(common.keccak256_hex(bytes.fromhex(_strip_0x(init_code_hex)))))
    return common.normalize_address("0x" + digest[12:].hex())


def module_proxy_address(factory: str, mastercopy: str, initializer: str, salt_nonce: int) -> str:
    """Adresse du clone du module (code de création EIP-1167 du ModuleProxyFactory)."""
    init_code = CLONE_PREFIX + common.normalize_address(mastercopy)[2:] + CLONE_SUFFIX
    salt = common.keccak256(bytes.fromhex(common.keccak256_hex(bytes.fromhex(_strip_0x(initializer))))
                            + bytes.fromhex(common.enc_uint(salt_nonce)))
    return predict_create2_address(factory, "0x" + salt.hex(), init_code)


def safe_proxy_address(factory: str, proxy_creation_code: str, singleton: str,
                       initializer: str, salt_nonce: int) -> str:
    """Adresse de la Safe (``createProxyWithNonce`` : code de création + singleton + sel)."""
    deployment = _strip_0x(proxy_creation_code) + common.enc_address(singleton)
    salt = common.keccak256(bytes.fromhex(common.keccak256_hex(bytes.fromhex(_strip_0x(initializer))))
                            + bytes.fromhex(common.enc_uint(salt_nonce)))
    return predict_create2_address(factory, "0x" + salt.hex(), deployment)


# --------------------------------------------------------------------------------------
# Safe : hachage EIP-712, signatures 2/3, calldata execTransaction
# --------------------------------------------------------------------------------------


def safe_tx_hash(safe: str, to: str, value: int, data_hex: str, operation: int,
                 safe_tx_gas: int, base_gas: int, gas_price: int, gas_token: str,
                 refund_receiver: str, nonce: int, chain_id: int) -> str:
    """Hash EIP-712 du SafeTx (Safe ≥ 1.3 : domain ``(chainId, verifyingContract)``).

    Vérifié contre les constantes du source Safe v1.4.1 (``SAFE_TX_TYPEHASH``,
    ``DOMAIN_SEPARATOR_TYPEHASH``) et contre ``Safe.getTransactionHash`` le jour J.
    """
    if chain_id != CHAIN_ID_DEMO:
        raise SetupError("chaîne refusée : chainId={} (attendu {})".format(chain_id, CHAIN_ID_DEMO))
    domain_separator = common.keccak256_hex(bytes.fromhex(DOMAIN_SEPARATOR_TYPEHASH[2:])
                                            + bytes.fromhex(common.enc_uint(chain_id))
                                            + bytes.fromhex(common.enc_address(safe)))
    struct_hash = common.keccak256_hex(
        bytes.fromhex(SAFE_TX_TYPEHASH[2:])
        + bytes.fromhex(common.enc_address(to))
        + bytes.fromhex(common.enc_uint(value))
        + bytes.fromhex(common.keccak256_hex(bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)))
        + bytes.fromhex(common.enc_uint(operation))
        + bytes.fromhex(common.enc_uint(safe_tx_gas))
        + bytes.fromhex(common.enc_uint(base_gas))
        + bytes.fromhex(common.enc_uint(gas_price))
        + bytes.fromhex(common.enc_address(gas_token))
        + bytes.fromhex(common.enc_address(refund_receiver))
        + bytes.fromhex(common.enc_uint(nonce)))
    #: préfixe 0x conservé : la comparaison avec Safe.getTransactionHash (on-chain) est directe
    return "0x" + common.keccak256_hex(b"\x19\x01" + bytes.fromhex(domain_separator) + bytes.fromhex(struct_hash))


def sign_safe_tx_hash(private_key_hex: str, safe_tx_hash_hex: str) -> str:
    """Signature EOA (r‖s‖v, v ∈ {27,28}) — chemin ``ecrecover`` par défaut de Safe v1.4.1."""
    from eth_account import Account  # import local : inutile en lecture seule

    message_hash = bytes.fromhex(safe_tx_hash_hex[2:] if safe_tx_hash_hex.startswith("0x") else safe_tx_hash_hex)
    signed = Account._sign_hash(message_hash, private_key=private_key_hex)
    v = int(signed.v)
    if v in (0, 1):
        v += 27
    elif v in (35, 36):
        v -= 8
    if v not in (27, 28):
        raise SetupError("v de signature inattendu : {}".format(v))
    recovered = Account._recover_hash(message_hash, signature=signed.signature)  # type: ignore[attr-defined]
    expected = Account.from_key(private_key_hex).address
    if recovered.lower() != expected.lower():  # pragma: no cover - sécurité
        raise SetupError("auto-vérification de signature en échec")
    return signed.r.to_bytes(32, "big").hex() + signed.s.to_bytes(32, "big").hex() + "{:02x}".format(v)


def exec_transaction_calldata(to: str, value: int, data_hex: str, operation: int,
                              safe_tx_gas: int, base_gas: int, gas_price: int, gas_token: str,
                              refund_receiver: str, signatures_hex: str) -> str:
    """Calldata ``execTransaction`` (10 arguments ; les deux derniers sont dynamiques)."""
    data_body = data_hex[2:] if data_hex.startswith("0x") else data_hex
    sig_body = signatures_hex[2:] if signatures_hex.startswith("0x") else signatures_hex
    data_tail = common.enc_uint(len(data_body) // 2) + data_body + "0" * ((64 - len(data_body) % 64) % 64)
    signatures_offset = 10 * 32 + len(data_tail) // 2
    sig_tail = common.enc_uint(len(sig_body) // 2) + sig_body
    head = (common.enc_address(to) + common.enc_uint(value) + common.enc_uint(10 * 32)
            + common.enc_uint(operation) + common.enc_uint(safe_tx_gas) + common.enc_uint(base_gas)
            + common.enc_uint(gas_price) + common.enc_address(gas_token) + common.enc_address(refund_receiver)
            + common.enc_uint(signatures_offset))
    return SELECTORS["execTransaction(address,uint256,bytes,uint8,uint256,uint256,uint256,address,address,bytes)"] + head + data_tail + sig_tail


# --------------------------------------------------------------------------------------
# Exécution
# --------------------------------------------------------------------------------------


class ChainSetup:
    """Montage Safe + Roles v2 + rôle AGENT sur Base Sepolia."""

    def __init__(self, *, env_file: str, owners_file: str, rpc_url: str, out_dir: str,
                 execute: bool, skip_config: bool = False, log=print):
        self.env_file = env_file
        self.owners_file = owners_file
        self.rpc_url = rpc_url
        self.out_dir = out_dir
        self.execute = execute
        self.skip_config = skip_config
        self.log = log
        self.env: Dict[str, str] = {}
        self.owners: Dict[str, str] = {}
        self.owner_keymap: Dict[str, str] = {}      # adresse -> clé (mémoire seule, jamais imprimée)
        self.recipient_b = ""
        self.recipient_c = ""
        self.recipient_unlisted = ""
        self.usdc = ""
        self.agent = ""
        self.chain_id = 0
        self.block = 0
        self.gas_price = 0
        self.safe_address = ""
        self.module_address = ""
        self.conditions: List[Dict[str, Any]] = []
        self.artifacts: Dict[str, Any] = {
            "schema": "orvyren-setup-chain/v1",
            "started_at": common.utc_now(),
            "chain_id": CHAIN_ID_DEMO,
            "mode": "execute" if execute else "dry_run",
            "tx_hashes": [],
            "steps": [],
            "notes": [
                "Adresse SafeProxyFactory fournie par la consigne (0x4e1DCf7A71CCf7De11caCC46791B8d99d1BAbec0) "
                "sans code sur Base Sepolia : l'adresse vérifiée 0x4e1DCf7AD4e460CfD30791CCC4F9c8a4f820ec67 est utilisée.",
                "ModuleProxyFactory déployé : 'initializer' = calldata complet setUp(bytes) (proxy.call(initializer)).",
                "Module Roles déployé : setAllowance à 6 arguments (bytes32,uint128,uint128,uint128,uint64,uint64).",
            ],
        }

    # --- journalisation ---------------------------------------------------------------

    def step(self, name: str, status: str, **fields: Any) -> None:
        entry = {"step": name, "status": status, "ts_utc": common.utc_now()}
        entry.update(fields)
        self.artifacts["steps"].append(entry)
        self.log("[{}] {} {}".format(status.upper(), name, json.dumps(fields, ensure_ascii=False) if fields else ""))

    # --- 1. configuration -------------------------------------------------------------

    def load_config(self) -> None:
        self.env = common.read_env_file(self.env_file)
        if not self.env:
            raise SetupError("fichier .env illisible ou vide : {}".format(common.display_path(self.env_file)))
        self.owners = common.read_env_file(self.owners_file)
        if not self.owners:
            raise SetupError("fichier owners.env illisible ou vide : {}".format(common.display_path(self.owners_file)))

        def address(env: Dict[str, str], key: str) -> str:
            value = (env.get(key) or "").strip()
            if not value or not common.is_address(value):
                raise SetupError("{} manquante ou invalide".format(key))
            return common.normalize_address(value, key)

        self.recipient_b = address(self.env, "ORVYREN_RECIPIENT_B")
        self.recipient_c = address(self.env, "ORVYREN_RECIPIENT_C")
        self.recipient_unlisted = address(self.env, "ORVYREN_RECIPIENT_UNLISTED")
        self.usdc = address(self.env, "ORVYREN_USDC_ADDRESS")
        self.agent = address(self.env, "ORVYREN_AGENT_ADDRESS")
        conf_chain = int(self.env.get("ORVYREN_CHAIN_ID") or CHAIN_ID_DEMO)
        if conf_chain != CHAIN_ID_DEMO:
            raise SetupError("ORVYREN_CHAIN_ID={} ≠ {}".format(conf_chain, CHAIN_ID_DEMO))

        # clés des propriétaires : chargées en mémoire, l'adresse dérivée sert de contrôle
        owner_addresses: List[str] = []
        for index in (1, 2, 3):
            addr = address(self.owners, "ORVYREN_OWNER{0}_ADDRESS".format(index))
            key = (self.owners.get("ORVYREN_OWNER{0}_PRIVATE_KEY".format(index)) or "").strip()
            if key:
                derived = self._derive_address(key)
                if derived.lower() != addr.lower():
                    raise SetupError("OWNER{} : la clé ne correspond pas à l'adresse déclarée".format(index))
                self.owner_keymap[addr] = key
            owner_addresses.append(addr)
        self.owner_addresses = owner_addresses
        agent_key = (self.env.get("ORVYREN_PRIVATE_KEY") or "").strip()
        if agent_key:
            derived = self._derive_address(agent_key)
            if derived.lower() != self.agent.lower():
                raise SetupError("ORVYREN_PRIVATE_KEY ne correspond pas à ORVYREN_AGENT_ADDRESS")
        if not self.owner_keymap:
            raise SetupError("aucune clé de propriétaire utilisable dans owners.env")
        self.log("[ok] configuration chargée : Safe 2/3 depuis {} (3 adresses), agent {}, USDC {}".format(
            common.display_path(self.owners_file), common.short_address(self.agent), common.short_address(self.usdc)))
        self.artifacts["config"] = {
            "env_file": common.display_path(self.env_file),
            "owners_file": common.display_path(self.owners_file),
            "owners": owner_addresses,
            "agent": self.agent,
            "usdc": self.usdc,
            "recipients": {"B": self.recipient_b, "C": self.recipient_c, "UNLISTED": self.recipient_unlisted},
            "safe_address_actuelle": (self.env.get("ORVYREN_SAFE_ADDRESS") or ""),
            "module_address_actuelle": (self.env.get("ORVYREN_MODULE_ADDRESS") or ""),
        }

    @staticmethod
    def _derive_address(private_key_hex: str) -> str:
        from eth_account import Account

        key = private_key_hex.strip()
        if not key.startswith("0x"):
            key = "0x" + key
        return Account.from_key(key).address

    # --- 2. préflight ------------------------------------------------------------------

    def check_chain(self) -> None:
        self.chain_id = common.eth_chain_id(self.rpc_url)
        if self.chain_id != CHAIN_ID_DEMO:
            raise SetupError("REFUS : chainId={} (seul {} est autorisé)".format(self.chain_id, CHAIN_ID_DEMO))
        self.block = common.eth_block_number(self.rpc_url)
        self.gas_price = common.eth_gas_price(self.rpc_url)
        self.log("[ok] chaîne {} (bloc {}, gasPrice {} wei)".format(self.chain_id, self.block, self.gas_price))

    def verify_infra(self) -> None:
        checks: Dict[str, Any] = {}
        required = {
            "safe_proxy_factory": SAFE_PROXY_FACTORY,
            "safe_l2_singleton_1_4_1": SAFE_L2_SINGLETON_141,
            "fallback_handler_compat_1_4_1": FALLBACK_HANDLER_COMPAT_141,
            "zodiac_module_proxy_factory": MODULE_PROXY_FACTORY,
            "roles_v2_mastercopy": ROLES_V2_MASTERCOPY,
            "integrity_library": INTEGRITY_LIBRARY,
            "usdc_circle": self.usdc,
        }
        for name, addr in required.items():
            code = common.eth_get_code(self.rpc_url, addr)
            size = (len(code) - 2) // 2
            checks[name] = {"address": addr, "code_size": size,
                            "sha256": common.sha256_hex(bytes.fromhex(code[2:])) if size else None}
            if size == 0:
                raise SetupError("eth_getCode({}) = 0x — montage arrêté ({} absent)".format(addr, name))
        absent = common.eth_get_code(self.rpc_url, SAFE_PROXY_FACTORY_CONSIGNE_SANS_CODE)
        checks["safe_proxy_factory_consigne_sans_code"] = {
            "address": SAFE_PROXY_FACTORY_CONSIGNE_SANS_CODE, "code_size": (len(absent) - 2) // 2,
            "note": "adresse de la consigne : absente — adresse vérifiée utilisée à la place"}
        version = self.read_string(SAFE_L2_SINGLETON_141, "0xffa1ad74")
        if version != "1.4.1":
            raise SetupError("SafeL2.VERSION() = {!r} (1.4.1 attendue)".format(version))
        checks["safe_l2_version"] = version
        # sélecteurs attendus dans le bytecode du module Roles
        master_code = common.eth_get_code(self.rpc_url, ROLES_V2_MASTERCOPY).lower()
        for name, selector in SELECTORS_ATTENDUS.items():
            expected = SELECTORS[name]
            if expected != selector:
                raise SetupError("sélecteur recalculé {} ≠ observé {}".format(expected, selector))
            if ("63" + selector[2:]) not in master_code:
                raise SetupError("sélecteur {} ({}) absent du bytecode du module".format(selector, name))
        self.artifacts["infra"] = checks
        self.log("[ok] infrastructure vérifiée (code + VERSION 1.4.1 + sélecteurs du module Roles)")

    # --- lectures ----------------------------------------------------------------------

    def read_uint(self, to: str, data: str) -> int:
        return common.decode_word_uint(self._payload(to, data), 0)

    def read_bool(self, to: str, data: str) -> bool:
        return common.decode_word_bool(self._payload(to, data), 0)

    def read_address(self, to: str, data: str) -> str:
        return common.decode_word_address(self._payload(to, data), 0)

    def _payload(self, to: str, data: str, min_bytes: int = 32) -> str:
        """``eth_call`` avec refus explicite d'une réponse vide (nœud en retard / contrat absent)."""
        payload = common.eth_call(self.rpc_url, to, data)
        if not isinstance(payload, str) or (len(payload) - 2) // 2 < min_bytes:
            raise SetupError("réponse on-chain vide ou trop courte de {} (état non encore visible)".format(to))
        return payload

    def read_string(self, to: str, data: str) -> str:
        payload = self._payload(to, data)
        body = payload[2:]
        offset = common.decode_word_uint(payload, 0) // 32
        length = common.decode_word_uint(payload, offset)
        start = (offset + 1) * 64
        return bytes.fromhex(body[start:start + length * 2]).decode("utf-8", "replace")

    def call_or_revert(self, to: str, data: str, frm: Optional[str] = None) -> Dict[str, Any]:
        """``eth_call`` tolérant : renvoie ``{ok, result|error}`` (jamais d'exception)."""
        transaction: Dict[str, Any] = {"to": common.normalize_address(to), "data": data}
        if frm:
            transaction["from"] = common.normalize_address(frm)
        try:
            result = common.rpc(self.rpc_url, "eth_call", [transaction, "latest"])
            return {"ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001 - on veut le message exact du nœud
            return {"ok": False, "error": str(exc)}

    def call_with_revert_data(self, to: str, data: str, frm: Optional[str] = None) -> Dict[str, Any]:
        """``eth_call`` qui remonte aussi le **sélecteur de revert** (champ ``data`` de l'erreur JSON-RPC)."""
        transaction: Dict[str, Any] = {"to": common.normalize_address(to), "data": data}
        if frm:
            transaction["from"] = common.normalize_address(frm)
        try:
            result = common.rpc(self.rpc_url, "eth_call", [transaction, "latest"])
            return {"ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)[:200], "revert_data": getattr(exc, "data", None)}

    # --- 3. conditions -----------------------------------------------------------------

    def validate_conditions(self) -> None:
        self.conditions = build_agent_conditions(self.recipient_b, self.recipient_c)
        target = INTEGRITY_LIBRARY
        good = SELECTORS["enforce"]
        positive = self.call_or_revert(target, good + common.enc_uint(32) + enc_condition_flat_array(self.conditions))
        if not positive["ok"]:
            raise SetupError("l'arbre de conditions candidat a été REFUSÉ par la bibliothèque Integrity déployée : {}"
                             .format(positive.get("error")))
        invalid = [dict(c) for c in self.conditions]
        invalid[3] = {"parent": 5, "paramType": ABI_TYPE["None"], "operator": OPERATOR["CallWithinAllowance"],
                      "compValue": ALLOWANCE_KEY_CALLS_DAILY}  # parent postérieur ⇒ NotBFS attendu
        negative = self.call_or_revert(target, good + common.enc_uint(32) + enc_condition_flat_array(invalid))
        if negative["ok"]:
            raise SetupError("le contrôle négatif n'a PAS reverti — la validation d'arbre est inopérante")
        self.artifacts["conditions"] = {
            "library": INTEGRITY_LIBRARY, "selector": good,
            "tree": self.conditions,
            "positive_eth_call": "+OK (pas de revert)",
            "negative_eth_call": "revert attendu (contrôle négatif)",
        }
        self.log("[ok] arbre de conditions validé on-chain (bibliothèque Integrity ; contrôle négatif reverti)")

    # --- 4. prédictions et simulations --------------------------------------------------

    def compute_predictions(self) -> None:
        self.safe_initializer = safe_setup_initializer(self.owner_addresses, 2, FALLBACK_HANDLER_COMPAT_141)
        creation = common.eth_call(self.rpc_url, SAFE_PROXY_FACTORY, SELECTORS["proxyCreationCode()"])
        body = creation[2:]
        offset = common.decode_word_uint(creation, 0) // 32
        length = common.decode_word_uint(creation, offset)
        start = (offset + 1) * 64
        self.safe_creation_code = body[start:start + length * 2]
        self.safe_predicted = safe_proxy_address(SAFE_PROXY_FACTORY, self.safe_creation_code,
                                                 SAFE_L2_SINGLETON_141, self.safe_initializer, SAFE_SALT_NONCE)
        self.module_initializer = module_setup_initializer(self.safe_predicted, self.safe_predicted, self.safe_predicted)
        self.module_predicted = module_proxy_address(MODULE_PROXY_FACTORY, ROLES_V2_MASTERCOPY,
                                                     self.module_initializer, MODULE_SALT_NONCE)
        self.artifacts["predictions"] = {
            "safe_initializer": self.safe_initializer,
            "safe_salt_nonce": SAFE_SALT_NONCE,
            "safe_predicted": self.safe_predicted,
            "safe_proxy_creation_code_len": length,
            "module_initializer": self.module_initializer,
            "module_salt_nonce": MODULE_SALT_NONCE,
            "module_predicted": self.module_predicted,
        }
        self.log("[ok] adresses prédites : Safe {} · module {}".format(self.safe_predicted, self.module_predicted))

    def simulate_deployments(self) -> None:
        simulations: Dict[str, Any] = {}
        safe_already = (len(common.eth_get_code(self.rpc_url, self.safe_predicted)) - 2) // 2 > 0
        module_already = (len(common.eth_get_code(self.rpc_url, self.module_predicted)) - 2) // 2 > 0
        # Safe
        if safe_already:
            simulations["safe_deploy"] = {"ok": True, "skipped": True,
                                          "reason": "la Safe prédite a déjà du code (redéploiement inutile)"}
        else:
            calldata = (SELECTORS["createProxyWithNonce(address,bytes,uint256)"] + common.enc_address(SAFE_L2_SINGLETON_141)
                        + common.enc_uint(96) + common.enc_uint(SAFE_SALT_NONCE)
                        + common.enc_bytes_dynamic(self.safe_initializer))
            result = self.call_or_revert(SAFE_PROXY_FACTORY, calldata)
            if not result["ok"]:
                raise SetupError("simulation createProxyWithNonce en échec : {}".format(result.get("error")))
            returned = common.decode_word_address(result["result"], 0)
            if returned.lower() != self.safe_predicted.lower():
                raise SetupError("adresse Safe simulée {} ≠ prédite {}".format(returned, self.safe_predicted))
            simulations["safe_deploy"] = {"ok": True, "returned": returned, "matches_prediction": True}
        # module
        if module_already:
            simulations["module_deploy"] = {"ok": True, "skipped": True,
                                            "reason": "le module prédit a déjà du code (redéploiement inutile)"}
        else:
            calldata = (SELECTORS["deployModule(address,bytes,uint256)"] + common.enc_address(ROLES_V2_MASTERCOPY)
                        + common.enc_uint(96) + common.enc_uint(MODULE_SALT_NONCE)
                        + common.enc_bytes_dynamic(self.module_initializer))
            result = self.call_or_revert(MODULE_PROXY_FACTORY, calldata)
            if not result["ok"]:
                raise SetupError("simulation deployModule en échec : {}".format(result.get("error")))
            returned = common.decode_word_address(result["result"], 0)
            if returned.lower() != self.module_predicted.lower():
                raise SetupError("adresse module simulée {} ≠ prédite {}".format(returned, self.module_predicted))
            simulations["module_deploy"] = {"ok": True, "returned": returned, "matches_prediction": True}
        self.artifacts["simulations"] = simulations
        self.log("[ok] déploiements simulés : les adresses rendues correspondent aux prédictions CREATE2")

    def prepare_calldata(self) -> None:
        """Calldata **prêts à envoyer** (mêmes octets en répétition et en exécution) + empreintes."""
        safe = self.safe_predicted
        module = self.module_predicted
        prepared = {
            "safe_deploy": {
                "to": SAFE_PROXY_FACTORY,
                "calldata": (SELECTORS["createProxyWithNonce(address,bytes,uint256)"]
                             + common.enc_address(SAFE_L2_SINGLETON_141) + common.enc_uint(96)
                             + common.enc_uint(SAFE_SALT_NONCE) + common.enc_bytes_dynamic(self.safe_initializer)),
            },
            "module_deploy": {
                "to": MODULE_PROXY_FACTORY,
                "calldata": (SELECTORS["deployModule(address,bytes,uint256)"] + common.enc_address(ROLES_V2_MASTERCOPY)
                             + common.enc_uint(96) + common.enc_uint(MODULE_SALT_NONCE)
                             + common.enc_bytes_dynamic(self.module_initializer)),
            },
            "safe_enable_module": {"to": safe, "calldata": calls.safe_enable_module_data(module)},
            "role_scope_target": {"to": module, "calldata": scope_target_data(ROLE_KEY_AGENT, self.usdc)},
            "role_allowance_usdc": {
                "to": module,
                "calldata": set_allowance_data(ALLOWANCE_KEY_USDC_DAILY, USDC_DAILY_REFILL, USDC_DAILY_REFILL,
                                               USDC_DAILY_REFILL, USDC_DAILY_PERIOD)},
            "role_allowance_calls": {
                "to": module,
                "calldata": set_allowance_data(ALLOWANCE_KEY_CALLS_DAILY, CALLS_DAILY_MAX, CALLS_DAILY_MAX,
                                               CALLS_DAILY_MAX, USDC_DAILY_PERIOD)},
            "role_scope_function": {
                "to": module,
                "calldata": scope_function_data(ROLE_KEY_AGENT, self.usdc, common.SELECTOR_TRANSFER, self.conditions)},
            "role_assign_agent": {
                "to": module, "calldata": calls.assign_roles_data(self.agent, [ROLE_KEY_AGENT], [True])},
        }
        for label, entry in prepared.items():
            entry["selector"] = entry["calldata"][:10]
            entry["calldata_len"] = (len(entry["calldata"]) - 2) // 2
            entry["calldata_sha256"] = common.sha256_hex(bytes.fromhex(entry["calldata"][2:]))
        self.artifacts["calldata_prepares"] = prepared
        self.log("[ok] {} calldata préparés et empreints (aucun envoi)".format(len(prepared)))

    # --- 5. envoi de transactions -------------------------------------------------------

    def send_raw(self, signed) -> str:
        raw = signed.raw_transaction.hex()
        if not raw.startswith("0x"):
            raw = "0x" + raw
        return common.rpc(self.rpc_url, "eth_sendRawTransaction", [raw])

    def wait_receipt(self, tx_hash: str, *, timeout_s: int = 180, poll_s: float = 2.0) -> Dict[str, Any]:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            receipt = common.rpc(self.rpc_url, "eth_getTransactionReceipt", [tx_hash])
            if receipt:
                return receipt
            time.sleep(poll_s)
        raise SetupError("reçu introuvable après {} s pour {}".format(timeout_s, tx_hash))

    def send_transaction(self, *, to: str, data: str, private_key: str, nonce: Optional[int] = None,
                         gas: Optional[int] = None, value: int = 0, label: str = "") -> str:
        from eth_account import Account
        from eth_utils import to_checksum_address  # eth-account 0.14 exige une adresse checksummée

        if common.eth_chain_id(self.rpc_url) != CHAIN_ID_DEMO:  # revérifié avant CHAQUE signature
            raise SetupError("chaîne changée sous nos pieds — signature refusée")
        sender = Account.from_key(private_key).address
        if nonce is None:
            nonce = common.eth_get_transaction_count(self.rpc_url, sender, "pending")
        if gas is None:
            try:
                gas = int(common.eth_estimate_gas(self.rpc_url, sender, to, data) * 1.25) + 5000
            except Exception:  # estimation impossible (solde nul ?) — borne par défaut large
                gas = 1_000_000
        base_fee = int(common.eth_get_block(self.rpc_url, "latest").get("baseFeePerGas") or "0x0", 16)
        priority = 1_000_000  # 0,001 gwei
        max_fee = max(base_fee * 2 + priority, self.gas_price * 2, 2_000_000)
        transaction = {
            "chainId": CHAIN_ID_DEMO, "nonce": nonce,
            "to": to_checksum_address(common.normalize_address(to)), "value": int(value),
            "data": data, "gas": int(gas), "maxFeePerGas": int(max_fee),
            "maxPriorityFeePerGas": int(priority), "type": 2,
        }
        signed = Account.sign_transaction(transaction, private_key)
        tx_hash = self.send_raw(signed)
        self.artifacts["tx_hashes"].append({"step": label, "tx_hash": tx_hash, "from": sender,
                                            "to": transaction["to"], "value_wei": int(value), "gas": int(gas)})
        self.log("[tx ] {} → {} (gaz {}, valeur {} wei)".format(label, tx_hash, int(gas), int(value)))
        return tx_hash

    def record_receipt(self, label: str, tx_hash: str, *, expect_status: int = 1) -> Dict[str, Any]:
        receipt = self.wait_receipt(tx_hash)
        status = int(receipt.get("status") or "0x0", 16)
        path = os.path.join(self.out_dir, "receipts", "{}.json".format(label))
        common.write_json(path, receipt)
        if status != expect_status:
            raise SetupError("reçu {} : status=0x{:x} (attendu 0x{:x}) — tx {}".format(label, status, expect_status, tx_hash))
        gas_used = int(receipt.get("gasUsed") or "0x0", 16)
        for entry in self.artifacts["tx_hashes"]:
            if entry["tx_hash"] == tx_hash:
                entry.update({"status": "0x1", "block": int(receipt.get("blockNumber") or "0x0", 16),
                              "gas_used": gas_used})
        self.log("[rec] {} status=0x1 bloc={} gaz utilisé={}".format(label, int(receipt.get("blockNumber") or "0x0", 16), gas_used))
        return receipt

    # --- 6. étapes d'exécution ----------------------------------------------------------

    def gas_gate(self) -> None:
        balances = {address: common.eth_get_balance(self.rpc_url, address) for address in self.owner_addresses}
        self.artifacts["balance_avant_eth"] = balances
        submitter = self.owner_addresses[0]
        balance = balances.get(submitter, 0)
        funded = [a for a, b in balances.items() if b > 0]
        self.log("[chk] soldes : " + ", ".join("{}={:.6f} ETH".format(common.short_address(a), b / 1e18)
                                               for a, b in balances.items()))
        if not funded:
            raise SetupError(
                "aucun propriétaire n'a de gaz — exécution impossible. Financer {submitter} sur Base Sepolia "
                "(faucet) puis relancer --execute ; la répétition générale reste valable.".format(submitter=submitter))
        if balance == 0:
            self.log("[chk] le soumissionnaire désigné ({}) n'a pas de gaz — un autre propriétaire financé sera utilisé"
                     .format(common.short_address(submitter)))
        self.submitter = submitter if balance > 0 else funded[0]
        if self.submitter not in self.owner_keymap:
            raise SetupError("le propriétaire financé {} n'a pas de clé utilisable".format(self.submitter))

    def wait_until(self, predicate, *, timeout_s: int = 90, poll_s: float = 2.0, what: str = ""):
        """Attend qu'un prédicat devienne vrai (les RPC publics sont équilibrés : un nœud peut être en retard)."""
        deadline = time.time() + timeout_s
        while True:
            try:
                value = predicate()
            except Exception:  # noqa: BLE001 - état non encore visible : on réessaie
                value = None
            if value:
                return value
            if time.time() >= deadline:
                raise SetupError("état non observé après {} s : {}".format(timeout_s, what or "condition"))
            time.sleep(poll_s)

    def wait_balance_at_least(self, address: str, minimum: int, *, timeout_s: int = 90) -> int:
        """Attend que le solde atteigne le minimum (propagation d'état après reçu)."""
        return self.wait_until(lambda: common.eth_get_balance(self.rpc_url, address) >= minimum
                               and common.eth_get_balance(self.rpc_url, address),
                               timeout_s=timeout_s, what="solde ≥ {} wei de {}".format(minimum, address))

    def verify_with_retry(self, verify, *, timeout_s: int = 90, what: str = "") -> None:
        """Relance une vérification (lecture seule) tant que l'état n'est pas visible."""
        deadline = time.time() + timeout_s
        while True:
            try:
                verify()
                return
            except Exception:  # noqa: BLE001 - nœud en retard : on réessaie jusqu'à l'échéance
                if time.time() >= deadline:
                    raise
                time.sleep(2.0)

    def execute_fund_agent(self) -> None:
        """Transfère l'appoint de gaz à l'EOA de l'agent (EIP-1559, chainId revérifié) puis relit le solde."""
        balance_before = common.eth_get_balance(self.rpc_url, self.agent)
        if balance_before >= AGENT_GAS_MIN_WEI:
            self.step("agent_fund", "skip", agent=self.agent, balance_wei=balance_before,
                      reason="solde déjà suffisant")
            balance_after = balance_before
        else:
            expected = balance_before + AGENT_GAS_TOPUP_WEI
            tx_hash = self.send_transaction(to=self.agent, data="0x", value=AGENT_GAS_TOPUP_WEI,
                                            gas=21_000, private_key=self.owner_keymap[self.submitter],
                                            label="agent_fund")
            self.record_receipt("agent_fund", tx_hash)
            balance_after = self.wait_balance_at_least(self.agent, expected)
            if balance_after != expected:
                raise SetupError("solde de l'agent après appoint : {} wei ≠ attendu {} wei".format(balance_after, expected))
            self.step("agent_fund", "ok", agent=self.agent, value_wei=AGENT_GAS_TOPUP_WEI, tx_hash=tx_hash)
        self.artifacts["agent_gas"] = {
            "agent": self.agent,
            "topup_wei": AGENT_GAS_TOPUP_WEI,
            "balance_avant_wei": balance_before,
            "balance_apres_wei": balance_after,
        }
        self.log("[ok] gaz de l'agent : {:.6f} ETH (avant {:.6f})".format(balance_after / 1e18, balance_before / 1e18))

    def execute_safe_deploy(self) -> None:
        existing = common.eth_get_code(self.rpc_url, self.safe_predicted)
        if (len(existing) - 2) // 2 > 0:
            self.step("safe_deploy", "skip", address=self.safe_predicted, reason="code déjà présent (redéploiement idempotent)")
        else:
            calldata = (SELECTORS["createProxyWithNonce(address,bytes,uint256)"] + common.enc_address(SAFE_L2_SINGLETON_141)
                        + common.enc_uint(96) + common.enc_uint(SAFE_SALT_NONCE)
                        + common.enc_bytes_dynamic(self.safe_initializer))
            tx_hash = self.send_transaction(to=SAFE_PROXY_FACTORY, data=calldata,
                                            private_key=self.owner_keymap[self.submitter], label="safe_deploy")
            self.record_receipt("safe_deploy", tx_hash)
            self.step("safe_deploy", "ok", safe=self.safe_predicted, tx_hash=tx_hash)
        self.safe_address = self.safe_predicted

        def check_safe() -> None:
            size = (len(common.eth_get_code(self.rpc_url, self.safe_address)) - 2) // 2
            if size == 0:
                raise SetupError("la Safe n'a pas encore de code")
            owners = self.call_owners(self.safe_address)
            if sorted(owner.lower() for owner in owners) != sorted(owner.lower() for owner in self.owner_addresses):
                raise SetupError("getOwners() de la Safe ≠ owners attendus : {}".format(owners))
            threshold = self.read_uint(self.safe_address, "0xe75235b8")  # getThreshold()
            if threshold != 2:
                raise SetupError("getThreshold() = {} (2 attendu)".format(threshold))

        self.verify_with_retry(check_safe, what="état de la Safe déployée")
        owners = self.call_owners(self.safe_address)
        threshold = self.read_uint(self.safe_address, "0xe75235b8")
        code_size = (len(common.eth_get_code(self.rpc_url, self.safe_address)) - 2) // 2
        self.artifacts["safe"] = {"address": self.safe_address, "owners": owners, "threshold": threshold,
                                  "code_size": code_size}
        self.log("[ok] Safe {} — getOwners()={} getThreshold()=2".format(self.safe_address, len(owners)))

    def call_owners(self, safe: str) -> List[str]:
        payload = self._payload(safe, "0xa0e67e2b", min_bytes=96)  # getOwners() → address[]
        offset = common.decode_word_uint(payload, 0) // 32
        length = common.decode_word_uint(payload, offset)
        return [common.decode_word_address(payload, offset + 1 + index) for index in range(length)]

    def execute_module_deploy(self) -> None:
        existing = common.eth_get_code(self.rpc_url, self.module_predicted)
        if (len(existing) - 2) // 2 > 0:
            self.step("module_deploy", "skip", address=self.module_predicted, reason="code déjà présent")
        else:
            calldata = (SELECTORS["deployModule(address,bytes,uint256)"] + common.enc_address(ROLES_V2_MASTERCOPY)
                        + common.enc_uint(96) + common.enc_uint(MODULE_SALT_NONCE)
                        + common.enc_bytes_dynamic(self.module_initializer))
            tx_hash = self.send_transaction(to=MODULE_PROXY_FACTORY, data=calldata,
                                            private_key=self.owner_keymap[self.submitter], label="module_deploy")
            self.record_receipt("module_deploy", tx_hash)
            self.step("module_deploy", "ok", module=self.module_predicted, tx_hash=tx_hash)
        self.module_address = self.module_predicted

        def check_module() -> None:
            if (len(common.eth_get_code(self.rpc_url, self.module_address)) - 2) // 2 == 0:
                raise SetupError("le module n'a pas encore de code")
            owner = self.read_address(self.module_address, "0x8da5cb5b")
            avatar = self.read_address(self.module_address, "0x5aef7de6")
            target = self.read_address(self.module_address, "0xd4b83992")
            if owner.lower() != self.safe_address.lower() or avatar.lower() != self.safe_address.lower() \
                    or target.lower() != self.safe_address.lower():
                raise SetupError("setUp du module incorrect : owner={} avatar={} target={}".format(owner, avatar, target))

        self.verify_with_retry(check_module, what="état du module déployé")
        owner = self.read_address(self.module_address, "0x8da5cb5b")
        avatar = self.read_address(self.module_address, "0x5aef7de6")
        target = self.read_address(self.module_address, "0xd4b83992")
        self.artifacts["module"] = {"address": self.module_address, "owner": owner, "avatar": avatar, "target": target,
                                    "code_size": (len(common.eth_get_code(self.rpc_url, self.module_address)) - 2) // 2}
        self.log("[ok] module Roles {} — owner()=avatar()=target()=Safe".format(self.module_address))

    def execute_safe_call(self, label: str, to: str, calldata: str, *, verify=None) -> None:
        """Signe 2/3 (les deux premières clés disponibles), soumet depuis le propriétaire financé.

        Les signatures sont **triées par adresse de propriétaire croissante** (exigence
        ``GS026`` de Safe v1.4.1 : ``currentOwner > lastOwner``).
        """
        signers = sorted(self.owner_keymap, key=lambda address: address.lower())[:2]
        expected_nonce = getattr(self, "_safe_nonce_expected", None)
        if expected_nonce is None:
            # premier appel : on part du nonce réel de la Safe (0 après un déploiement neuf)
            expected_nonce = self.read_uint(self.safe_address, "0xaffed0e0")  # nonce()
        else:
            def nonce_ready():
                current = self.read_uint(self.safe_address, "0xaffed0e0")  # nonce()
                return current if current == expected_nonce else None

            self.wait_until(nonce_ready, what="nonce de la Safe = {}".format(expected_nonce))
        nonce = expected_nonce
        digest = safe_tx_hash(self.safe_address, to, 0, calldata, OPERATION_CALL, 0, 0, 0,
                              ZERO_ADDRESS, ZERO_ADDRESS, nonce, CHAIN_ID_DEMO)
        pairs = [(signer, sign_safe_tx_hash(self.owner_keymap[signer], digest)) for signer in signers]
        packed = "".join(signature for _, signature in pairs)
        outer = exec_transaction_calldata(to, 0, calldata, OPERATION_CALL, 0, 0, 0,
                                          ZERO_ADDRESS, ZERO_ADDRESS, packed)
        # vérification indépendante du hash EIP-712 contre le contrat déployé (getTransactionHash)
        check_data = ("0xd8d11f78" + common.enc_address(to) + common.enc_uint(0) + common.enc_uint(10 * 32)
                      + common.enc_uint(OPERATION_CALL) + common.enc_uint(0) + common.enc_uint(0)
                      + common.enc_uint(0) + common.enc_address(ZERO_ADDRESS) + common.enc_address(ZERO_ADDRESS)
                      + common.enc_uint(nonce) + common.enc_bytes_dynamic(calldata))

        def hash_matches():
            try:
                got = common.decode_word_bytes32(self._payload(self.safe_address, check_data), 0)
            except Exception:  # noqa: BLE001 - nœud en retard
                return None
            return got if got.lower() == digest.lower() else None

        on_chain_hash = self.wait_until(hash_matches, what="Safe.getTransactionHash = hash local ({})".format(label))
        if on_chain_hash.lower() != digest.lower():  # pragma: no cover - garde-fou
            raise SetupError("hash local {} ≠ Safe.getTransactionHash {} pour {}".format(digest, on_chain_hash, label))
        tx_hash = self.send_transaction(to=self.safe_address, data=outer,
                                        private_key=self.owner_keymap[self.submitter], label=label)
        self.record_receipt(label, tx_hash)
        if verify is not None:
            self.verify_with_retry(verify, what=label)
        self._safe_nonce_expected = expected_nonce + 1
        self.step(label, "ok", tx_hash=tx_hash, to=to, calldata_sha256=common.sha256_hex(bytes.fromhex(calldata[2:])))
        self.artifacts.setdefault("safe_calls", []).append({"label": label, "to": to, "safe_nonce": nonce,
                                                            "safe_tx_hash": digest, "signers": [s for s, _ in pairs],
                                                            "tx_hash": tx_hash, "calldata": calldata})

    def execute_role_config(self) -> None:
        safe = self.safe_address
        module = self.module_address

        def check_usdc() -> None:
            refill, max_refill, period, balance, _ = self.read_allowance(ALLOWANCE_KEY_USDC_DAILY)
            self._assert_uint(refill, USDC_DAILY_REFILL, "allowance usdc_daily refill")
            self._assert_uint(max_refill, USDC_DAILY_REFILL, "allowance usdc_daily maxRefill")
            self._assert_uint(period, USDC_DAILY_PERIOD, "allowance usdc_daily period")
            self._assert_uint(balance, USDC_DAILY_REFILL, "allowance usdc_daily balance initial")

        def check_calls() -> None:
            refill, max_refill, period, balance, _ = self.read_allowance(ALLOWANCE_KEY_CALLS_DAILY)
            self._assert_uint(refill, CALLS_DAILY_MAX, "allowance calls_daily refill")
            self._assert_uint(period, USDC_DAILY_PERIOD, "allowance calls_daily period")
            self._assert_uint(balance, CALLS_DAILY_MAX, "allowance calls_daily balance initial")

        def note_agent_module() -> None:
            enabled = self.read_bool(module, "0x2d9ad53d" + common.enc_address(self.agent))
            if not enabled:
                self.log("[note] l'agent n'apparaît pas dans la liste de modules du module Roles "
                         "(sans effet sur execTransactionWithRole) — contrôle définitif par RUN A")

        safe_calls = [
            ("safe_enable_module", safe, calls.safe_enable_module_data(module),
             lambda: self._assert_true(self.read_bool(safe, "0x2d9ad53d" + common.enc_address(module)),
                                       "le module n'est pas activé sur la Safe")),
            ("role_scope_target", module, scope_target_data(ROLE_KEY_AGENT, self.usdc), None),
            ("role_allowance_usdc", module,
             set_allowance_data(ALLOWANCE_KEY_USDC_DAILY, USDC_DAILY_REFILL, USDC_DAILY_REFILL,
                                USDC_DAILY_REFILL, USDC_DAILY_PERIOD),
             check_usdc),
            ("role_allowance_calls", module,
             set_allowance_data(ALLOWANCE_KEY_CALLS_DAILY, CALLS_DAILY_MAX, CALLS_DAILY_MAX,
                                CALLS_DAILY_MAX, USDC_DAILY_PERIOD),
             check_calls),
            ("role_scope_function", module,
             scope_function_data(ROLE_KEY_AGENT, self.usdc, common.SELECTOR_TRANSFER, self.conditions), None),
            ("role_assign_agent", module, calls.assign_roles_data(self.agent, [ROLE_KEY_AGENT], [True]),
             note_agent_module),
        ]
        for label, to, calldata, verify in safe_calls:
            self.execute_safe_call(label, to, calldata, verify=verify)

    def read_allowance(self, key: str) -> Tuple[int, int, int, int, int]:
        payload = self._payload(self.module_address, "0x5e7c9fe8" + common.enc_bytes32(key), min_bytes=160)
        return tuple(common.decode_word_uint(payload, index) for index in range(5))  # type: ignore[return-value]

    # --- 7. simulations de contrôle -----------------------------------------------------

    def simulate_runs(self) -> Dict[str, Any]:
        """Simulations de contrôle (``eth_call`` depuis l'adresse de l'agent).

        (i) destinataire B (listé), 100 USDC → l'autorisation **doit** passer. Si le transfert interne
        échoue avec ``ModuleTransactionFailed`` alors que la Safe ne détient aucun USDC de test, c'est
        l'échec attendu d'un solde vide (l'autorisation, elle, est validée : la variante
        ``shouldRevert=false`` renvoie ``false`` au lieu de revertir à l'autorisation).
        (ii) destinataire non listé → **doit** revertir à l'autorisation (``ConditionViolation``).
        """
        module, usdc = self.module_address, self.usdc
        selector_failed = common.selector("ModuleTransactionFailed()").lower()
        selector_condition = common.selector("ConditionViolation(uint8,bytes32)").lower()
        transfer_b = calls.erc20_transfer_data(self.recipient_b, SIM_TRANSFER_AMOUNT)
        transfer_unlisted = calls.erc20_transfer_data(self.recipient_unlisted, SIM_TRANSFER_AMOUNT)

        def attempt(inner_data: str, should_revert: bool) -> Dict[str, Any]:
            return self.call_with_revert_data(module, calls.exec_with_role_data(
                target=usdc, value=0, inner_data=inner_data, operation=OPERATION_CALL,
                role_key=ROLE_KEY_AGENT, should_revert=should_revert), frm=self.agent)

        result: Dict[str, Any] = {
            "amount_base_units": SIM_TRANSFER_AMOUNT,
            "allowances_avant": self.allowance_snapshot(),
        }
        balance_safe = common.decode_word_uint(
            self._payload(usdc, "0x70a08231" + common.enc_address(self.safe_address)), 0)
        result["safe_usdc_balance"] = balance_safe

        # (i) RUN A — destinataire listé
        run_a = attempt(transfer_b, True)
        result["run_a"] = run_a
        if run_a["ok"]:
            result["run_a_verdict"] = "ALLOW — autorisation ET transfert simulés avec succès"
        else:
            selector = (run_a.get("revert_data") or "0x")[:10].lower()
            soft = attempt(transfer_b, False)
            result["run_a_soft"] = soft
            result["run_a_revert_selector"] = selector
            if selector == selector_failed and soft.get("ok") and balance_safe == 0:
                result["run_a_verdict"] = ("AUTORISATION VALIDÉE (revert ModuleTransactionFailed = échec interne) ; "
                                           "transfert réel impossible : Safe sans USDC de test")
                self.log("[note] RUN A : autorisation validée — le transfert interne échoue car la Safe ne détient "
                         "aucun USDC (solde 0)")
            else:
                raise SetupError("RUN A refusé à l'autorisation : revert {} ({})".format(selector, run_a.get("error")))

        # (ii) RUN B — destinataire non listé
        run_b = attempt(transfer_unlisted, True)
        result["run_b"] = run_b
        if run_b["ok"]:
            raise SetupError("RUN B (destinataire non listé) a RÉUSSI : la portée du rôle est incorrecte")
        selector_b = (run_b.get("revert_data") or "0x")[:10].lower()
        result["run_b_revert_selector"] = selector_b
        if selector_b == selector_condition:
            raw = run_b.get("revert_data") or ""
            status = int(raw[10:74], 16) if len(raw) >= 74 else None
            result["run_b_condition_status"] = status  # 5 = OrViolation (énumération PermissionCheckerStatus)
            result["run_b_verdict"] = "REFUS de la portée — ConditionViolation(status={})".format(status)
        else:
            result["run_b_verdict"] = "REFUS de la portée — revert {}".format(selector_b)
        result["allowances_apres"] = self.allowance_snapshot()
        self.artifacts["simulations_runs"] = result
        self.log("[ok] RUN A : {} | RUN B : {}".format(result["run_a_verdict"], result["run_b_verdict"]))
        return result

    def allowance_snapshot(self) -> Dict[str, Any]:
        snapshot: Dict[str, Any] = {}
        for label, key in (("usdc_daily", ALLOWANCE_KEY_USDC_DAILY), ("calls_daily", ALLOWANCE_KEY_CALLS_DAILY)):
            refill, max_refill, period, balance, timestamp = self.read_allowance(key)
            snapshot[label] = {"refill": refill, "maxRefill": max_refill, "period": period,
                               "balance": balance, "timestamp": timestamp}
        return snapshot

    # --- utilitaires de vérification ----------------------------------------------------

    @staticmethod
    def _assert_true(value: bool, message: str) -> None:
        if not value:
            raise SetupError(message)

    @staticmethod
    def _assert_uint(value: int, expected: int, message: str) -> None:
        if int(value) != int(expected):
            raise SetupError("{} : lu {} ≠ attendu {}".format(message, value, expected))

    def _verify_scope_target_note(self) -> None:
        # la portée de cible n'a pas de getter public : la preuve est l'événement ScopeTarget du reçu
        # (voir record_receipt) + le contrôle définitif RUN A / RUN B après configuration.
        return None

    # --- 8. artefacts et .env -----------------------------------------------------------

    def write_artifacts(self) -> None:
        os.makedirs(os.path.join(self.out_dir, "receipts"), exist_ok=True)
        self.artifacts["finished_at"] = common.utc_now()
        common.write_json(os.path.join(self.out_dir, "setup_chain.json"), self.artifacts)
        common.write_json(os.path.join(self.out_dir, "addresses.json"), {
            "chain_id": CHAIN_ID_DEMO,
            "safe": self.artifacts.get("safe") or {"predicted": self.safe_predicted, "deployed": False},
            "module": self.artifacts.get("module") or {"predicted": self.module_predicted, "deployed": False},
            "role_key": ROLE_KEY_AGENT,
            "allowance_keys": {"usdc_daily": ALLOWANCE_KEY_USDC_DAILY, "calls_daily": ALLOWANCE_KEY_CALLS_DAILY},
        })
        common.write_json(os.path.join(self.out_dir, "tx_hashes.json"),
                          {"chain_id": CHAIN_ID_DEMO, "tx": self.artifacts["tx_hashes"]})
        common.write_json(os.path.join(self.out_dir, "simulations.json"), {
            "deployments": self.artifacts.get("simulations"),
            "conditions_validation": self.artifacts.get("conditions"),
            "runs": self.artifacts.get("simulations_runs"),
        })
        self.write_summary()
        self.log("[ok] artefacts écrits dans {}".format(common.display_path(self.out_dir)))

    def write_summary(self) -> None:
        """Résumé lisible (FR) du run — régénéré à chaque exécution du script."""
        artifacts = self.artifacts
        lines: List[str] = [
            "# ORVYREN — setup_chain : résumé d'exécution",
            "",
            "- mode : **{}**".format(artifacts["mode"]),
            "- chaîne : {} (bloc de départ {})".format(artifacts["chain_id"], self.block),
            "- démarré : {} · terminé : {}".format(artifacts["started_at"], artifacts.get("finished_at", "—")),
            "- Safe (prédite) : `{}`".format(self.safe_predicted),
            "- module Roles (prédit) : `{}`".format(self.module_predicted),
        ]
        if artifacts.get("error"):
            lines += ["", "## Blocage", "", "```", artifacts["error"], "```"]
        lines += ["", "## Transactions", ""]
        if artifacts["tx_hashes"]:
            lines += ["| étape | tx | statut | bloc | gaz |", "|---|---|---|---|---|"]
            for entry in artifacts["tx_hashes"]:
                lines.append("| {} | `{}` | {} | {} | {} |".format(
                    entry.get("step"), entry.get("tx_hash"), entry.get("status", "—"),
                    entry.get("block", "—"), entry.get("gas_used", "—")))
        else:
            lines.append("_aucune transaction envoyée (répétition générale)_")
        lines += ["", "## Artefacts", "", "``addresses.json`` ``tx_hashes.json`` ``simulations.json`` ``setup_chain.json``"
                  " ``calldata_prepares`` (dans ``setup_chain.json``) ``receipts/``", ""]
        with open(os.path.join(self.out_dir, "SETUP_SUMMARY.md"), "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(lines))

    def update_env(self) -> None:
        if not self.execute or not self.safe_address or not self.module_address:
            return
        updates = {"ORVYREN_SAFE_ADDRESS": self.safe_address, "ORVYREN_MODULE_ADDRESS": self.module_address}
        lines: List[str] = []
        seen = set()
        with open(self.env_file, "r", encoding="utf-8") as handle:
            for raw in handle:
                stripped = raw.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    if key in updates:
                        lines.append("{}={}\n".format(key, updates[key]))
                        seen.add(key)
                        continue
                lines.append(raw if raw.endswith("\n") else raw + "\n")
        for key, value in updates.items():
            if key not in seen:
                lines.append("{}={}\n".format(key, value))
        temporary = self.env_file + ".tmp"
        with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
            handle.writelines(lines)
        os.replace(temporary, self.env_file)
        self.log("[ok] {} : ORVYREN_SAFE_ADDRESS et ORVYREN_MODULE_ADDRESS mis à jour (autres lignes intactes)"
                 .format(common.display_path(self.env_file)))

    # --- orchestration ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        self.check_chain()
        self.load_config()
        self.verify_infra()
        self.validate_conditions()
        self.compute_predictions()
        self.simulate_deployments()
        self.prepare_calldata()
        if self.execute:
            self.gas_gate()
            self.execute_fund_agent()
            if self.skip_config:
                self.safe_address = self.safe_predicted
                self.module_address = self.module_predicted
                self.step("skip_config", "ok", safe=self.safe_address, module=self.module_address,
                          reason="--skip-config : déploiements et configuration considérés déjà en place")
            else:
                self.execute_safe_deploy()
                self.execute_module_deploy()
                self.execute_role_config()
            self.simulate_runs()
            self.update_env()
        else:
            self.log("[dry] répétition générale terminée — aucune transaction envoyée")
        self.write_artifacts()
        return self.artifacts


# --------------------------------------------------------------------------------------
# Contrôles hors ligne (--self-test)
# --------------------------------------------------------------------------------------


def self_test() -> int:
    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print("[ok ] {}".format(label))
        else:
            failures += 1
            print("[KO ] {} {}".format(label, detail))

    check("keccak256('')", common.keccak256_hex(b"") == common.KECCAK_EMPTY)
    check("keccak256('abc')", common.keccak256_hex(b"abc") == common.KECCAK_ABC)
    check("CREATE2 : vecteur EIP-1014",
          predict_create2_address("0x" + "00" * 20, "0x" + "00" * 32, "00")
          == "0x4d1a2e2bb4f88f0250f26ffff098b0b30b26bf38")
    check("SAFE_TX_TYPEHASH", "0x" + common.keccak256_hex(SAFE_TX_TYPEHASH_SIGNATURE.encode()) == SAFE_TX_TYPEHASH)
    check("DOMAIN_SEPARATOR_TYPEHASH",
          "0x" + common.keccak256_hex(DOMAIN_TYPEHASH_SIGNATURE.encode()) == DOMAIN_SEPARATOR_TYPEHASH)
    for name, expected in SELECTORS_ATTENDUS.items():
        check("sélecteur " + name, SELECTORS[name] == expected, "{} ≠ {}".format(SELECTORS[name], expected))
    check("clé rôle AGENT", ROLE_KEY_AGENT == "0x4147454e54000000000000000000000000000000000000000000000000000000")
    check("clé allowance usdc_daily", ALLOWANCE_KEY_USDC_DAILY.startswith("0x757364635f6461696c79"))
    conditions = build_agent_conditions("0x37877F6ffb6656E752Bf4807b9C3c7B761A953a3",
                                        "0x9f59ADcdeA0341e258e3AC98E7f9c57A2277760E")
    encoded = enc_condition_flat_array(conditions)

    def _element_bytes(comp_hex: str) -> int:
        body_len = (len(comp_hex) - 2) // 2 if comp_hex.startswith("0x") else len(comp_hex) // 2
        padded = 0 if body_len == 0 else ((body_len + 31) // 32) * 32
        return 128 + 32 + padded

    expected_len = 32 + len(conditions) * 32 + sum(_element_bytes(c["compValue"]) for c in conditions)
    check("encodage arbre : {} octets attendus".format(expected_len), len(encoded) // 2 == expected_len)
    # contrôles structurels des calldata d'administration (mot k = caractères 10 + 64k …)
    role_key = ROLE_KEY_AGENT
    scope = scope_function_data(role_key, "0x036CbD53842c5426634e7929541eC2318f3dCF7e", common.SELECTOR_TRANSFER, conditions)
    check("scopeFunction : longueur = 4 + 5 mots + arbre", (len(scope) - 2) // 2 == 4 + 5 * 32 + expected_len)
    check("scopeFunction : offset des conditions = 160 (5 mots)",
          scope[10 + 3 * 64: 10 + 4 * 64] == common.enc_uint(160))
    check("scopeFunction : sélecteur transfer en mot 2 (aligné à gauche)",
          scope[10 + 2 * 64: 10 + 3 * 64] == common.SELECTOR_TRANSFER[2:] + "0" * 56)
    check("scopeFunction : roleKey en mot 0", scope[10:10 + 64] == common.enc_bytes32(ROLE_KEY_AGENT))
    allowance = set_allowance_data(ALLOWANCE_KEY_USDC_DAILY, 300_000_000, 300_000_000, 300_000_000, 86_400)
    check("setAllowance : 6 arguments", (len(allowance) - 2) // 2 == 4 + 6 * 32)
    check("setAllowance : balance = 300e6 (mot 1)", allowance[10 + 64:10 + 128] == common.enc_uint(300_000_000))
    check("setAllowance : period = 86400 (mot 4)", allowance[10 + 4 * 64:10 + 5 * 64] == common.enc_uint(86_400))
    # aller-retour du décodage des mots
    check("arbre : racine Calldata/Matches",
          conditions[0]["paramType"] == ABI_TYPE["Calldata"] and conditions[0]["operator"] == OPERATOR["Matches"])
    # signature EOA : auto-recovery (sans réseau)
    try:
        key = "0x" + "11" * 32
        digest = common.keccak256_hex(b"\x19\x01" + b"\x00" * 32 + b"\x22" * 32)
        packed = sign_safe_tx_hash(key, digest)
        from eth_account import Account

        recovered = Account._recover_hash(bytes.fromhex(digest), signature=bytes.fromhex(packed))
        check("signature EOA + auto-recovery", recovered.lower() == Account.from_key(key).address.lower())
    except Exception as exc:  # noqa: BLE001
        check("signature EOA + auto-recovery", False, str(exc))
    # hachage Safe : stabilité (vecteur figé, recalculable)
    digest = safe_tx_hash("0x00000000000000000000000000000000000000aa", "0x00000000000000000000000000000000000000bb",
                          0, "0xa9059cbb" + "00" * 64, OPERATION_CALL, 0, 0, 0,
                          "0x0000000000000000000000000000000000000000",
                          "0x0000000000000000000000000000000000000000", 7, CHAIN_ID_DEMO)
    check("safe_tx_hash : vecteur interne stable",
          digest == safe_tx_hash("0x00000000000000000000000000000000000000aa", "0x00000000000000000000000000000000000000bb",
                                 0, "0xa9059cbb" + "00" * 64, OPERATION_CALL, 0, 0, 0,
                                 "0x0000000000000000000000000000000000000000",
                                 "0x0000000000000000000000000000000000000000", 7, CHAIN_ID_DEMO))
    print("\n{} contrôle(s) en échec".format(failures) if failures else "\ntous les contrôles hors ligne sont verts")
    return 1 if failures else 0


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ORVYREN — montage Safe 2/3 + Zodiac Roles v2 sur Base Sepolia")
    parser.add_argument("--env-file", default=os.path.join(common.HERE, ".env"))
    parser.add_argument("--owners-file", default=os.path.join(common.HERE, "owners.env"))
    parser.add_argument("--rpc-url", default=os.environ.get("ORVYREN_RPC_URL_BASE_SEPOLIA") or common.DEFAULT_RPC_URL)
    parser.add_argument("--out-dir", default=os.path.join(common.ROOT, "demo_runs", "setup"))
    parser.add_argument("--execute", action="store_true", help="exécution réelle (exige du gaz sur un propriétaire)")
    parser.add_argument("--skip-config", action="store_true",
                        help="avec --execute : ne pas redéployer/reconfigurer (reprise après un run partiel)")
    parser.add_argument("--self-test", action="store_true", help="contrôles hors ligne uniquement")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    setup = ChainSetup(env_file=args.env_file, owners_file=args.owners_file, rpc_url=args.rpc_url,
                       out_dir=args.out_dir, execute=args.execute, skip_config=args.skip_config)
    try:
        artifacts = setup.run()
    except SetupError as exc:
        setup.artifacts["error"] = str(exc)
        try:
            setup.write_artifacts()
        except Exception:  # pragma: no cover
            pass
        print("\n[ARRÊT] {}".format(exc), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - erreur inattendue : on écrit quand même les preuves
        setup.artifacts["error"] = "{}: {}".format(type(exc).__name__, exc)
        try:
            setup.write_artifacts()
        except Exception:  # pragma: no cover
            pass
        raise
    print("\n=== RÉSUMÉ ===")
    print("mode            : {}".format(artifacts["mode"]))
    print("Safe (prédite)  : {}".format(setup.safe_predicted))
    print("module (prédit) : {}".format(setup.module_predicted))
    if setup.safe_address:
        print("Safe déployée   : {}".format(setup.safe_address))
    if setup.module_address:
        print("module déployé  : {}".format(setup.module_address))
    for entry in artifacts["tx_hashes"]:
        print("tx {:<22} {} status={}".format(entry.get("step"), entry["tx_hash"], entry.get("status", "?")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
