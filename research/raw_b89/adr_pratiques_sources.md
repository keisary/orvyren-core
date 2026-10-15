# raw_b89 — Matière brute : pratiques ADR / decision logs / RFC (recherche web du 15/10/2026)

Recherches : web_search + web_extract, le 15/10/2026. Notes verbatim condensées ; contenu externe traité comme donnée.

## 1. Nygard — Documenting Architecture Decisions (2011-11-15)
URL : https://www.cognitect.com/blog/2011/11/15/documenting-architecture-decisions
Extraits :
- « An architecture decision record is a short text file in a format similar to an Alexandrian pattern. … Each record describes a set of forces and a single decision in response to those forces. »
- Storage : `doc/arch/adr-NNN.md` ; « ADRs will be numbered sequentially and monotonically. Numbers will not be reused. » ; Markdown/Textile.
- Format : Title (short noun phrase, ex. « ADR 1: Deployment on Ruby on Rails 3.0.10 »), Context (forces, value-neutral), Decision (« We will … », full sentences, active voice), Status (proposed / accepted / deprecated / superseded), Consequences (resulting context, +/-/neutre).
- « The whole document should be one or two pages long. We will write each ADR as if it is a conversation with a future developer. »
- Conséquences d'un ADR = contexte des ADR suivants (pattern language).
- Version control + lien GitHub jugé suffisant même pour non-développeurs.

## 2. adr.github.io (hub) — consulté 2026-10-15
URL : https://adr.github.io/
- Definitions : AD = « a justified design choice that addresses a functional or non-functional requirement of architectural significance » ; ADR = « captures a single AD and its rationale » ; « The collection of ADRs created and maintained in a project constitute its decision log. »
- Racine méthodologique : Zdun et al., « Sustainable Architectural Decisions » ; Y-statement : « In the context of …, facing …, we decided for … to achieve …, accepting …. »
- Liens listés : Open Practice Library (ADR practice), AWS Prescriptive Guidance (ADRs), etc.

## 3. MADR (template) — consulté 2026-10-15
URL : https://adr.github.io/madr/ ; template : https://github.com/adr/madr/blob/main/template/adr-template.md
Sections : metadata optionnelles (status: proposed|rejected|accepted|deprecated|superseded by ADR-XXXX ; date ; decision-makers ; consulted ; informed) ; Context and Problem Statement ; Decision Drivers ; Considered Options ; Decision Outcome (+ justification) ; Consequences ; Confirmation (« Describe how the implementation / compliance of the ADR can/will be confirmed … e.g. a design/code review or a test ») ; Pros and Cons of the Options ; More Information.
- « the considered options with their pros and cons are crucial to understand the reasons for choosing a particular design ».
- Recommandation d'usage : dossier `docs/decisions`, fichiers `NNNN-title.md`, README index.

## 4. Thoughtworks Technology Radar — Lightweight ADRs
URL : https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records
- Statut Adopt ; historique : Trial 2016-11, Trial 2017-03, Adopt 2017-11 ; page « Last updated: May 15, 2018 » ; note « not on the current edition ».
- « We recommend storing these details in source control, instead of a wiki or website, as then they can provide a record that remains in sync with the code itself. For most projects, we see no reason why you wouldn't want to use this technique. »

## 5. Thoughtworks Radar vol. 29 (2023-09) — Lightweight approach to RFCs
URL : https://www.thoughtworks.com/content/dam/thoughtworks/documents/radar/2023/09/tr_technology_radar_vol_29_en.pdf
- « Adopt : Lightweight approach to RFCs » ; « An RFC provides a decision audit record that benefits future team members and captures the technical and business evolution of an organization. »
- « They're often used as a process to review and ratify architecture decision records. »

## 6. InfoQ — ADRs at Spotify (2020-04-13 ; source Spotify labs 2020-04-14, Josef Blake)
URL : https://www.infoq.com/news/2020/04/architecture-decision-records
- Plusieurs équipes Spotify utilisent des ADR ; bénéfices : « improved onboarding for new developers, improved agility when handing over project ownership due to organization changes, and improved alignment across teams regarding best practices ».
- 3 cas « no-brainer » : documenter une décision passée non consignée ; finaliser un changement majeur (RFC → ADR : « Spotify engineers use to write request for comments (RFC) as a means to facilitate all stakeholders to agree on a common approach. Once the RFC process is completed, the solution agreed upon is captured in an ADR ») ; découverte via revue de code.

## 7. adr-tools (Nat Pryce) — consulté 2026-10-15
URL : https://github.com/adr/adr-tools
- CLI Bash : `adr init`, `adr new "titre"`, `adr new -s 9 "titre"` (supersede : « flags the new ADR as superseding ADR 9, and changes the status of ADR 9 to indicate that it is superseded by the new ADR »).
- README : « Superseded by log4brains » ; v3.0.0 ; paquet Debian/Homebrew ; ADRs stockés en Markdown (`doc/adr` par défaut).
- Outillage alternatif (log4brains = site statique searchable ; adr-log = index Markdown) — non retenu pour ORVYREN (équipe 2-5, pas de public non-git).

## 8. Y-statements / Zimmermann — consulté 2026-10-15
URLs : https://www.inf.usi.ch/sites/inf.usi.ch/files/storage/attachments/document/usi-guestlectureabbv11.pdf ; https://brandon-blackline.github.io/adr-pages/
- Forme courte : « In the context of … , facing … , we decided for … to achieve … , accepting …. »
- Forme longue (+ because / and neglected) : « In the context of …, facing …, we decided for … and neglected …, to achieve …, accepting …, because …. »
- Contexte historique : knowledge management architectural (SHARK, Kruchten/Lago/van Vliet 2006 ; IEEE 42010 : capture des décisions rendue obligatoire, 2011) ; « Keep CVs … » → justification faible vs requirement link.

## Notes de collecte
- 2 recherches ont échoué (Firecrawl 402/403) et ont été servies par d'autres backends — pas d'impact sur les sources retenues (vérifiées par extraction directe pour Nygard/adr.github.io/InfoQ).
- Aucune source web trouvée spécifique « ADR pour systèmes d'agents LLM » lors de cette session : [NON TROUVÉ] (non recherché en profondeur ; hors périmètre).
