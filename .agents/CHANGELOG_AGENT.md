# CHANGELOG_AGENT.md — Mémoire de session

> Ce fichier est la mémoire du projet pour les agents IA : il dit où en est le code sans avoir à l'inférer.
> À mettre à jour à la fin de chaque ticket (voir `AGENT.md` §7).
> Ordre : « État global » en haut (à jour), entrées détaillées en bas (les plus récentes en dernier).

---

## État global

Périmètre = roadmap du cahier des charges (`mircapgen_cahier_des_charges_v0.md` §29).

| Module | Version cible | Statut |
|--------|---------------|--------|
| Cadrage / cahier des charges | — | 🟡 V0 en cours de finalisation par l'utilisateur |
| Initialisation du dépôt (packaging, outillage, CI) | 0.0 | ⚪ Non démarré |
| Features (décorateur, registre, métadonnées) | 0.0 → 0.1 | ⚪ Non démarré |
| Couche MCP (tools, adaptateur `mcp/`) | 0.0 | ⚪ Non démarré |
| Helper agent / découverte des capacités | 0.1 | ⚪ Non démarré |
| Identification : clés personnelles (0.0 → 0.1), OAuth (0.2) ; authentification admin (0.3) | 0.0 → 0.3 | ⚪ Non démarré |
| RBAC (utilisateurs, groupes, permissions, filtrage) | 0.1 | ⚪ Non démarré |
| Configuration | 0.1 | ⚪ Non démarré |
| Secrets | 0.1 | ⚪ Non démarré |
| Middleware / hooks (base 0.1, avancé 0.4) | 0.1 / 0.4 | ⚪ Non démarré |
| Logs structurés | 0.1 | ⚪ Non démarré |
| Interface d'administration + formulaires déclaratifs | 0.3 | ⚪ Non démarré |
| Intégration pytest (fixtures, helpers RBAC) | 0.0 → 0.1 | ⚪ Non démarré |
| CLI (`new`, `create`, `dev`, `test`, `inspect`, `check`, `docs`) | 0.1 | ⚪ Non démarré |
| Dockerfile standard | 0.1 | ⚪ Non démarré |
| Resources / prompts MCP, plugins, Vault | 0.4 | ⚪ Hors MVP |
| OAuth / IdP externes | 0.2 | ⚪ Hors MVP |
| Observabilité (métriques, traces, OpenTelemetry) | 0.5 | ⚪ Hors MVP |

Légende : ⚪ non démarré · 🟡 en cours · 🟢 livré · 🔴 bloqué

**Code existant** : aucun. Le dépôt ne contient que le cahier des charges, `CLAUDE.md` et `.agents/`.

---

## Historique

### 2026-09-29 — Cahier des charges : modèle d'identité (§8)

**Fichiers modifiés** : `mircapgen_cahier_des_charges_v0.md` (§2 non touché ; §8 réécrit ; ajustements §9, §9.1, §10, §15, §17.1, §27, §34, §35), `.agents/DECISIONS.md`.

**Décision** : trois acteurs (administrateur, client MCP, utilisateur de l'agent) ; les groupes de droits ne concernent que les utilisateurs d'agents. Voir `DECISIONS.md`.

**Hypothèses posées** : l'administrateur n'a pas accès aux Features ; l'identité utilisateur est refusée si absente ou inconnue ; les utilisateurs d'agents sont créés par l'admin (pas de provisioning automatique en 0.1).

**Complément (même jour)** : §8.5 étendu (transmission par l'agent, modes anti-usurpation `trusted`/`scoped`/`signed`, plafond de permissions), §8.6 (provisioning optionnel), nouveau §8.7 (Features publiques), nouveau §9.0 (groupes en dur ou dynamiques), §34 questions 16-21 reformulées. Voir `DECISIONS.md`.

**Dette / à faire** : les modes anti-usurpation sont une proposition à valider ; le canal de transmission dépend du SDK MCP retenu ; la section §1 et le schéma §2.1 du cahier n'ont pas été reformulés.

---

### 2026-09-29 — Permissions, Features sans permission, `require_credential` (cahier §9.2, §24, §8.9)

**Fichiers modifiés** : `mircapgen_cahier_des_charges_v0.md` (nouveau §9.2, §3.1, §8.9, §11.1, §20, §24, §28.3, §34 questions 7, 8, 18 tranchées, questions 34-35 ajoutées), `.agents/CONVENTIONS.md`, `.agents/DECISIONS.md` (questions 7, 8, 22 résolues, questions 38-39).

**Décision** : permissions déclarées dans le décorateur, paramétrables par `PermissionField` ; Feature sans `permission` ni `public` inaccessible + erreur journalisée ; `identity.require_credential`. Voir `DECISIONS.md`.

**Cas `permission` + `public=True`** : tranché ensuite — règle la plus restrictive (permission exigée, `public` ignoré, avertissement, signalé par `check`) ; `PermissionField` ne peut pas rendre une Feature publique.

**Hypothèses posées** : le format des permissions et les jokers ont été proposés par l'agent et non contestés ; `PermissionField` ne peut pas rendre une Feature publique (validé).

---

### 2026-09-29 — Persistance et migrations décidées (cahier §12.2, §18.7)

**Fichiers modifiés** : `mircapgen_cahier_des_charges_v0.md` (nouveau §12.2, §18.7, §20, §28.3, §34 questions 4 à 6 tranchées, questions 32-33 ajoutées), `.agents/CONVENTIONS.md` (persistance, migrations, arborescence `store/`, dépendances), `.agents/DECISIONS.md` (décision de persistance, questions 4, 5, 6 résolues, questions 36-37).

**Décision** : contrat `Store` ; `SqlStore` sur SQLAlchemy Core + Alembic ; SQLite par défaut, base serveur au choix par configuration ; migrations explicites à la Django, en avant uniquement, sauvegarde automatique du fichier SQLite. Voir `DECISIONS.md`.

**Hypothèses posées** : Mircapgen ne gère jamais de serveur de base (il se connecte à une base fournie) ; le refus de démarrer avec des migrations en attente et l'absence de retour arrière sont des ajustements proposés à l'idée « comme Django / Express », à confirmer.

**Complément (même jour)** : questions 32 et 33 du cahier tranchées : tables métier hors du cœur (extension plus tard), accès à la base synchrone dans des threads derrière une interface asynchrone.

**Dette / à faire** : choisir le pilote de base serveur à l'implémentation ; schéma initial des tables `mircap_*` ; décisions préalables restantes de la 0.1 (déclaration des permissions, instructions du Helper, format des clés).

---

### 2026-09-29 — Outillage Python validé, `uv` installé

**Fichiers modifiés** : `.agents/CONVENTIONS.md` (stack, section « Installation et commandes », dépendances approuvées), `.agents/DECISIONS.md` (décision d'outillage, questions 1, 2 et 16 résolues), `CLAUDE.md` (rappel de stack).

**Fait sur le poste** : `uv` 0.12.20 installé avec `pip install uv` (Python 3.12.0).

**Décision** : Python 3.11+, hatchling, uv, ruff, pyright, pytest + anyio, Starlette, Pydantic v2, PyYAML. Dépendances déclarées une seule fois dans `pyproject.toml`, installation automatique par `uv sync`. Voir `DECISIONS.md`.

**Hypothèses posées** : « fichier de dépendances pour une installation automatique » interprété comme `pyproject.toml` + `uv.lock` (source unique), avec `requirements.txt` exporté seulement au besoin.

**Dette / à faire** : aucun fichier de projet (`pyproject.toml`, `src/`) n'existe encore ; commandes de `CONVENTIONS.md` à confirmer à l'initialisation du dépôt ; décisions préalables à la 0.1 (persistance, format des permissions, instructions du Helper, format des clés).

---

### 2026-09-29 — Cahier des charges : relecture complète et corrections de cohérence

**Fichiers modifiés** : `mircapgen_cahier_des_charges_v0.md` (§3.1, §8.1, §8.5, §8.8, §10, §14, §15, §18, §19, §20, §21, §28.3, §32, §34), `.agents/DECISIONS.md` (questions 28 à 35).

**Corrigé** : métadonnées de Feature complétées (`public`, `risk`, `mcp`) ; gestion par CLI des utilisateurs et clés (§18.6) ; références à l'interface d'administration alignées sur la 0.3 ; pipeline du §14 aligné sur le §27 ; exemple de log et journal d'audit ; chemins de fichiers cohérents ; manifeste `mircap.yaml` avec `identity` (plus de drapeau `security.authentication`) ; nouveaux contrôles de `check`.

**Ajouté comme questions ouvertes (non tranchées)** : stockage de l'audit, écriture de l'API publique, identité en stdio, sécurité du transport HTTP, autorisation au niveau des données, comportement de `risk`, mode de développement sans authentification, Helper et champ `instructions` de MCP. Alerte sur les plafonds par `client_id` avec DCR.

**Non appliqué volontairement** : la règle « permission ou `public=True` obligatoire » du §24 (question 8) reste une décision à prendre.

---

### 2026-09-29 — Cahier des charges : redécoupage du MVP (§28-29)

**Fichiers modifiés** : `mircapgen_cahier_des_charges_v0.md` (§28 et §29 réécrits), `.agents/DECISIONS.md`, `.agents/CHANGELOG_AGENT.md` (versions cibles de l'état global).

**Décision** : 0.0 prototype, 0.1 MVP sans interface web, 0.2 OAuth, 0.3 administration web, 0.4 MCP avancé et plugins, 0.5 observabilité, 1.0 stabilisation. Voir `DECISIONS.md`.

**Dette / à faire** : décisions préalables à la 0.0 (version de Python, packaging, lint, typage) ; décisions préalables à la 0.1 (persistance, format des permissions, instructions du Helper, format des clés) ; ordre 0.2 / 0.3 à confirmer.

---

### 2026-09-29 — Cahier des charges : deux méthodes d'identification (§8 réécrit)

**Fichiers modifiés** : `mircapgen_cahier_des_charges_v0.md` (§8 entièrement réécrit ; §9, §9.1, §10, §27, §34 ajustés), `.agents/DECISIONS.md`.

**Décision** : identité prouvée par un identifiant d'accès (clé personnelle ou jeton OAuth 2.1), jamais déclarée par le modèle. Mircapgen = serveur de ressources OAuth, fournisseur d'identité externe. Plafond de permissions conservé. Les modes `trusted` / `scoped` / `signed` et l'identité renseignée via le Helper sont abandonnés.

**Hypothèses posées** : la clé statique de Claude étant partagée par organisation, les clés personnelles visent les agents auto-hébergés ; OAuth vise les assistants grand public ; un fournisseur d'identité externe est acceptable pour le développeur.

**Dette / à faire** : réviser la roadmap §29 (OAuth était en 0.3) et le périmètre §28 lors du redécoupage du MVP ; prototype SDK officiel ; tests réels avec les quatre clients ; renseigner le fournisseur d'identité de référence.

---

### 2026-09-29 — Réinitialisation de `.agents/` et de `CLAUDE.md` pour Mircapgen

**Fichiers modifiés** : `.agents/AGENT.md`, `.agents/CONVENTIONS.md`, `.agents/CHANGELOG_AGENT.md`, `.agents/DECISIONS.md`, `CLAUDE.md`.

**Contexte** : ces fichiers avaient été copiés depuis un autre projet (MyMemoMaster : Node/Express/Vue). Tout leur contenu (stack, historique, décisions) a été retiré et remplacé par un cadre adapté à Mircapgen (framework Python de microservices MCP).

**Utilisable** : cadre de travail des agents (règles, conventions, checklist de livraison, gabarits de décision).

**Hypothèses posées** :
- La stack Python est déduite du cahier des charges (§1, exemples de code) ; aucune version ni bibliothèque n'est encore choisie — tout est listé en « Questions ouvertes » dans `DECISIONS.md`.
- La structure du dépôt du framework (`CONVENTIONS.md`) est une proposition à valider au ticket d'initialisation.
- Le schéma de branches Git n'est pas défini (l'ancien schéma `dev_front/dev_back` a été retiré).
- Convention de langue : identifiants en anglais, docstrings/commentaires/messages en français.

**Dette / à faire** :
- Trancher les questions ouvertes de `DECISIONS.md` avant ou pendant le premier ticket d'implémentation.
- Renseigner les commandes de lint/format/typage/tests dans `CONVENTIONS.md` et `AGENT.md` §7 une fois l'outillage posé.
- Le fichier `.agents/2024 Référentiel Expert en développement logiciel YNOV (2).md` a été conservé tel quel (document de référence scolaire, non lié au code) ; à déplacer hors du dépôt ou à supprimer si inutile.
