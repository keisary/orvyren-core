# raw_b1 — matière brute du chantier B1 (bloc AGENTS)

Collecte du **2026-10-15** (sauf mention contraire). Tout ce dossier est de la matière première :
les pages officielles archivées, les résultats de recherche, et les calculs. Le document final est
`../B1_AGENTS_ETUDE.md`.

## Pages officielles archivées (texte extrait ou HTML brut)

| Fichier | Source | Contenu |
|---|---|---|
| `ds_pricing.txt` (+ `curl_api_docs_deepseek_com_quick_start_pricing.html`) | api-docs.deepseek.com/quick_start/pricing | prix DeepSeek flash / v4-pro, contexte 1M, sortie 384K, pointe/hors pointe, concurrence |
| `q_deepseek…function_calling.md`, `ds_chat_api.txt` | api-docs.deepseek.com (guides, API ref) | JSON mode (`json_object`), `tool strict` bêta, `response_format` |
| `ds_…rate_limit.md` / `official_deepseek_pricing.txt` | api-docs.deepseek.com | rate limits (2500 / 500), 429 |
| `q_…structured-output.md`, `mimo_*structured-output.md` | mimo.mi.com docs | structured output `json_object` + recommandation `jsonschema` |
| `mimo_models.txt` (+ HTML) | mimo.mi.com/docs/en-US/quick-start/summary/model | capacités MiMo, contexte 1M, sortie 128K |
| `mimo_rate_limit.md` | mimo.mi.com/static/docs/api/guidance/rate-limit.md | RPM 100 / TPM 10M par modèle |
| `curl_…pay-as-you-go.md` | mimo.mi.com/docs/price/pay-as-you-go | prix MiMo USD et CNY (v2.6 pro/flash/ultraspeed, batch) |
| `mimo_free_trial.md` | mimo.mi.com (news) | opération d'essai gratuit passée (jusqu'au 2026-04-02) |
| `curl_…pricing_chat_md` | platform.kimi.ai/docs/pricing/chat | prix Kimi K3 / K2.7 / K2.6, cache write TTL |
| `curl_…minimax_io_docs_guides_pricing.html` (+ `mm_pricing.txt`) | platform.minimax.io/docs/guides/pricing | prix MiniMax M3 / M2.7 / legacy |
| `curl_…alibabacloud…model-pricing.html` (+ `qwen_pricing.txt`) | alibabacloud.com/help/en/model-studio/model-pricing | prix Qwen3.8-max/flash, paliers, cache, batch |
| `p_docs_z_ai_guides_overview_pricing.md` | docs.z.ai/guides/overview/pricing | prix GLM (4.6, 5, 5.3, 5.3-Flash) |

## Littérature / preuves tierces

| Fichier | Référence | Date de publication |
|---|---|---|
| `lit_arxiv_org_abs_2304_03442.html` | Generative Agents (memory stream) | 2023-04-07 (v2 2023-08-06) |
| `lit_arxiv_org_abs_2603_10062.html` | Multi-Agent Memory (architecture) | 2026-03-09 (v2 2026-03-30) |
| `lit_arxiv_org_abs_2606_24535.html` | Governed Shared Memory (MemClaw) | 2026-06-23 |
| `lit_arxiv_org_abs_2601_17768.html` | LLM-42 (déterminisme) | 2026-01-25 (v2 2026-01-30) |
| `lit_arxiv_org_abs_2606_08998.html` | The Token Not Taken (stochasticité) | 2026-06-08 (v3 2026-07-02) |
| `lit_arxiv_org_abs_2605_03378.html` | ARGUS (anti-injection contextuelle) | 2026-05-05 (v2 2026-07-08) |
| `lit_thinkingmachines…html` | Defeating Nondeterminism (blog) | 2025-09-10 |
| `arxiv_dates.xml` | dates officielles arXiv (API) | — |
| `searches_models_01.json` … `searches_sys_02.json` | résultats de recherche web | 2026-10-15 |

## Calculs

| Fichier | Contenu |
|---|---|
| `couts_b1.json` | prix unitaires relevés + coût estimé d'une décision (P1/P2/P3) et d'un replay (1/3 épisodes, 1 ou 2 passes) pour 12 modèles — [MESURÉ] |

## Avertissements

- Les extractions web ont été limitées en débit (firecrawl « Rate Limit Exceeded », puis « Insufficient credits ») :
  une partie des pages a été récupérée par `curl` + `C:/Users/User/html2txt.py` (HTML brut conservé).
- Le navigateur local (Chromium) n'est pas installé sur ce poste : pas de rendu des pages dynamiques.
- Aucune de ces pages ne constitue une décision : voir `../B1_AGENTS_ETUDE.md`.
