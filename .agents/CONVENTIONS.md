# CONVENTIONS.md — Conventions du projet

> Fichier spécifique à ce projet. L'agent IA doit lire ce fichier avant toute implémentation.
> État : **projet en phase de cadrage** (cahier des charges V0). Les éléments marqués ⏳ sont volontairement non tranchés — voir `DECISIONS.md` § « Questions ouvertes ». Mets ce fichier à jour dès qu'une décision est prise.

---

## Stack technique

| Élément | Valeur |
|---------|--------|
| Langage | Python **3.11 minimum** ; développement sur 3.12 ; tests sur 3.11 à 3.13 |
| Nature du livrable | Bibliothèque Python + CLI `mircapgen` (paquet publiable) |
| Packaging | `pyproject.toml` (PEP 621), backend de build **hatchling**, disposition `src/` |
| Outil de développement | **uv** (environnement, installation, verrouillage `uv.lock`) |
| Protocole exposé | MCP (Model Context Protocol) — tools d'abord (0.1), resources/prompts ensuite (0.2) |
| SDK MCP | SDK officiel `mcp` v2 (décision 2026-09-29), isolé derrière l'adaptateur `mcp/` — aucun autre module n'importe `mcp` directement. Ne pas réimplémenter le protocole (cahier des charges §30) |
| Framework web (admin + HTTP) | **Starlette** (déjà requis par le SDK `mcp`) — pas de FastAPI ni de Flask |
| Validation de données / schémas | **Pydantic v2** (déjà requis par le SDK `mcp`) — produit les schémas JSON d'entrée/sortie MCP depuis les annotations |
| Templates admin | ⏳ (§34 q.3) |
| Persistance (users, clés, groupes, config) | Contrat `Store` ; `SqlStore` fondé sur **SQLAlchemy Core** (sans ORM), SQLite par défaut, base serveur au choix par `database.url` ; `MemoryStore` pour les tests. Interface asynchrone ; en interne SQLAlchemy synchrone exécuté dans des threads. Tables préfixées `mircap_` ; les tables métier du développeur ne sont pas gérées par le cœur |
| Migrations | **Alembic**, migrations livrées avec le paquet, commandes `mircapgen db status/upgrade/history`, en avant uniquement, sauvegarde automatique du fichier SQLite avant migration |
| Manifeste projet | `mircap.yaml` |
| Tests | `pytest` + plugin `anyio` pour l'asynchrone (+ fixtures/helpers fournis par Mircapgen) |
| Lint / formatage | **ruff** (un seul outil pour les deux) |
| Typage statique | **pyright**, mode strict sur `src/` ; le paquet publie un marqueur `py.typed` |
| Conteneurisation | Dockerfile standard généré pour les projets (0.1) |

---

## Installation et commandes

Les dépendances sont déclarées **une seule fois**, dans `pyproject.toml` (dépendances du cœur, extras optionnels et groupe de développement). `uv.lock` fige les versions. Aucun fichier de dépendances écrit à la main en plus : si un `requirements.txt` est nécessaire (Docker, CI), il est **exporté** depuis le verrou avec `uv export`.

Installation automatique complète de l'environnement de développement :

```bash
uv sync
```

Commandes de référence (à confirmer quand le dépôt sera initialisé) :

| Action | Commande |
|--------|----------|
| Installer / mettre à jour l'environnement | `uv sync` |
| Tests | `uv run pytest` |
| Lint | `uv run ruff check` |
| Formatage | `uv run ruff format` |
| Typage | `uv run pyright` |

Ces quatre vérifications (tests, lint, formatage, typage) doivent passer avant de livrer un ticket (`AGENT.md` §7).

---

## Structure de dossiers

Deux structures à ne pas confondre : celle **du framework** (ce dépôt) et celle **d'un microservice généré** (cahier des charges §19).

### Dépôt du framework (proposition, à valider au ticket d'initialisation)

```
mircapgen/
├── src/mircapgen/
│   ├── core/            # MircapApp, registre de Features, pipeline de requête
│   ├── features/        # décorateur @feature, métadonnées, découverte
│   ├── mcp/             # couche d'intégration MCP (gateway, transports, schémas)
│   ├── auth/            # authentification humaine + backends MCP
│   ├── rbac/            # utilisateurs, groupes, permissions
│   ├── config/          # MircapConfig, sources, priorités
│   ├── store/           # contrat Store, MemoryStore, SqlStore, migrations Alembic
│   ├── secrets/         # type Secret, backends de secrets, masquage
│   ├── middleware/      # hooks before/after/on_error
│   ├── logging/         # logs structurés + filtrage des données sensibles
│   ├── admin/           # interface d'administration + formulaires déclaratifs
│   ├── errors.py        # hiérarchie MircapError
│   ├── testing/         # fixtures pytest publiques (mcp_client, as_group…)
│   └── cli/             # commandes new / create / dev / test / inspect / check / docs
├── templates/           # gabarits de projet et de Feature pour la CLI
├── examples/            # microservices d'exemple (CRM…) — jamais importés par le cœur
├── tests/               # tests du framework (unit / integration / security)
├── docs/
├── .agents/             # Ce dossier
├── pyproject.toml
└── mircapgen_cahier_des_charges_v0.md
```

### Microservice généré par `mircapgen new` (référence : cahier des charges §19)

```
my-mcp-service/
├── mircap.yaml
├── pyproject.toml
├── app/
│   ├── main.py
│   ├── config.py
│   ├── features/<domaine>/{<action>.py, instructions.md, tests/}
│   ├── admin/{forms.py, pages.py}
│   └── middleware/
├── tests/{integration, security}/
└── docker/Dockerfile
```

---

## Nommage

### Code Python

| Élément | Convention | Exemple |
|---------|-----------|---------|
| Modules / paquets | `snake_case` | `feature_registry.py` |
| Classes | `PascalCase` | `MircapApp`, `AdminForm`, `SecretField` |
| Fonctions / méthodes / variables | `snake_case` | `resolve_permissions` |
| Constantes | `UPPER_SNAKE_CASE` | `DEFAULT_TIMEOUT` |
| Éléments privés | préfixe `_` | `_registry` |
| Exceptions | suffixe `Error`, héritent de `MircapError` | `AuthorizationError` |
| Fichiers de tests | `test_<module>.py` | `test_registry.py` |

### Concepts métier du framework

| Élément | Convention | Exemple |
|---------|-----------|---------|
| Nom de Feature | `domaine.action`, minuscules, séparé par un point | `customer.search` |
| Nom de permission | `domaine.verbe`, jokers autorisés en suffixe | `customer.read`, `admin.*` |
| Fichiers d'instructions | `instructions.md` par domaine de Feature | `features/customer/instructions.md` |
| Clés de `mircap.yaml` | `snake_case` | `auto_discovery` |
| Commandes CLI | verbes courts, sous-commandes explicites | `mircapgen create feature customer.search` |
| Paquets d'extension | préfixe `mircapgen-` | `mircapgen-vault` |

> Le format exact des noms de permission (§34 q.7) n'est pas encore figé : ces exemples sont indicatifs.

---

## Patterns de code

### Feature (API cible — indicatif, cahier des charges §3 et §32)

```python
@feature(
    name="customer.delete",
    description="Supprime définitivement un client",
    permission="customer.delete",
    risk="high",
)
async def delete_customer(customer_id: int) -> None: ...
```

Le décorateur enregistre la Feature ; l'exposition MCP, la validation, le RBAC, les logs et la documentation sont produits par le framework. Le corps de la fonction ne contient **que** de la logique métier.

### Pipeline de requête (ordre à respecter — cahier des charges §27)

```
Transport MCP → Authentification → Découverte/filtrage → Autorisation
→ Validation entrée → Middleware before → Feature → Middleware after
→ Validation sortie → Sérialisation → Log d'audit → Réponse
```

Aucune étape ne peut être sautée pour une Feature exposée via MCP.

### Erreur

```python
class AuthorizationError(MircapError):
    """Levée quand l'utilisateur n'a pas la permission requise."""
```

Les messages destinés à un agent ou à un humain sont clairs, actionnables et **ne révèlent ni secret ni détail interne**.

---

## Règles spécifiques au projet

- Séparation stricte métier / infrastructure : le code d'une Feature n'importe ni MCP, ni auth, ni RBAC, ni admin, ni logs
- Le cœur du framework n'importe jamais `examples/`
- Toute Feature exposée via MCP a un nom unique, une description non vide, et déclare `permission` ou `public=True` ; sans l'un ni l'autre elle n'est pas exposée et une erreur est journalisée ; avec les deux, la permission est exigée, `public` est ignoré et un avertissement est journalisé (§24)
- Format des permissions : `domaine.verbe` en minuscules, joker `*` seulement en dernier segment ; la permission d'une Feature est celle du décorateur, éventuellement remplacée par un `PermissionField` (§9.2)
- Description ≠ Instructions ≠ Constraints : trois champs distincts, ne pas les fusionner (§5.2)
- La documentation, la découverte des capacités et le helper agent sont **générés depuis les déclarations de Features** — pas de duplication manuelle
- `Secret` est un type natif : sa représentation (`repr`, `str`, JSON, logs) est masquée par défaut ; la révélation est explicite et localisée
- Les backends (secrets, authentification MCP, persistance) sont derrière des interfaces abstraites remplaçables
- Les logs sont structurés (JSON) avec `request_id`, `user`, `feature`, `duration_ms`, `status`, et filtrent automatiquement les données sensibles
- Les tests du framework utilisent `pytest` ; les helpers publics (`mcp_client`, `as_group`, `can_call`) sont stables et documentés
- Le code asynchrone est la norme pour les Features (`async def`) ; les Features synchrones, si supportées, sont exécutées hors de la boucle d'événements
- Configuration : priorité entre sources (env, fichier, base, admin, secret backend) ⏳ à définir avant d'implémenter `MircapConfig`
- Les messages destinés aux utilisateurs finaux et aux agents (erreurs, admin UI) sont en **français** par défaut ; les identifiants techniques (noms de Feature, de permission, clés YAML, logs structurés) restent en anglais
- Le code (identifiants) est en anglais ; docstrings, commentaires et documentation sont en français

---

## Erreurs standardisées

```
MircapError
├── AuthenticationError
├── AuthorizationError
├── ValidationError
├── ConfigurationError
├── FeatureError
└── InternalError
```

Le mapping vers les codes d'erreur MCP / HTTP est à définir avec la couche transport ⏳.

---

## Dépendances approuvées

### Dépendances du cœur

| Usage | Librairie | Remarque |
|-------|-----------|----------|
| Protocole MCP | `mcp` (SDK officiel, `>=2,<3`) | derrière l'adaptateur `mcp/` uniquement |
| Validation, schémas | `pydantic` (v2) | déjà requis par `mcp`, déclaré directement car utilisé directement |
| HTTP / admin | `starlette`, `uvicorn` | déjà requis par `mcp`, déclarés directement dès qu'on les importe |
| Manifeste `mircap.yaml` | `PyYAML` (`safe_load` uniquement) | seule dépendance nouvelle du cœur |
| Jetons OAuth (0.2) | `pyjwt[crypto]` | déjà requis par `mcp` |
| Persistance | `SQLAlchemy` (Core uniquement, pas d'ORM) | nouvelle dépendance du cœur, validée le 2026-09-29 |
| Migrations | `alembic` | nouvelle dépendance du cœur, validée le 2026-09-29 |
| Pilotes de bases serveur | extras optionnels (ex. `mircapgen[postgres]`) | pilotes synchrones (par exemple `psycopg` pour Postgres), choix final à l'implémentation |

### Dépendances de développement

| Usage | Outil |
|-------|-------|
| Environnement, verrou | `uv` |
| Build | `hatchling` |
| Tests | `pytest` + plugin `anyio` (`anyio` est déjà requis par `mcp`) |
| Lint et formatage | `ruff` |
| Typage | `pyright` |

> Toute autre dépendance (persistance, hachage des clés, CLI, gabarits d'administration…) doit être **signalée, justifiée, puis ajoutée ici et dans `DECISIONS.md`**. Distinguer dépendances du cœur et extras optionnels.

---

## Ce qui est hors-scope

Repris du cahier des charges §30 — Mircapgen ne doit pas devenir :

- un framework web généraliste
- un nouvel ORM
- un moteur de templates complet
- un système IAM complet
- un orchestrateur d'agents
- un moteur LLM
- un remplacement de Kubernetes
- un remplacement des SDK MCP existants

Hors MVP 0.1 (repoussé aux versions suivantes) : resources et prompts MCP, système de plugins, OAuth / fournisseurs d'identité externes / SSO, Vault et secret managers, métriques / traces / OpenTelemetry, MFA, migrations de base de données du framework.
