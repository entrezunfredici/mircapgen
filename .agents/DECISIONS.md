# DECISIONS.md — Décisions techniques structurantes

> Journal des choix qui expliquent pourquoi le code est comme il est.
> Format de chaque entrée : **Contexte / Décision / Alternative écartée / Conséquences**.
> Entrées les plus récentes en bas de la section « Décisions prises ». Ne jamais supprimer une décision : la marquer *Remplacée par…* si elle change.

---

## Décisions prises

### 2026-09-29 — Le projet cible Python et le protocole MCP

**Contexte** : le cahier des charges V0 définit Mircapgen comme un framework Python pour créer des microservices exposés via MCP (§1).

**Décision** : langage Python ; MCP comme protocole d'exposition aux agents ; `pytest` comme framework de tests (§17) ; `mircap.yaml` comme manifeste de projet (§20) ; concept central = la *Feature* déclarée par décorateur.

**Alternative écartée** : réimplémenter le protocole MCP ou créer un framework de tests maison (§30, §17).

**Conséquences** : le framework s'appuie sur un SDK MCP existant (choix à faire, voir questions ouvertes) ; les annotations de type Python servent de source de vérité pour les schémas d'entrée/sortie.

---

### 2026-09-29 — Découpage du MVP 0.1

> **Remplacée** par « Redécoupage du MVP en 0.0 / 0.1 et roadmap révisée ».

**Contexte** : le cahier des charges (§28-29) distingue un noyau 0.1 et des extensions ultérieures.

**Décision** : le MVP 0.1 couvre Features, tools MCP, helper global + instructions par Feature, découverte, utilisateurs/groupes/RBAC avec filtrage de visibilité, configuration, secrets, admin avec formulaires déclaratifs simples, logs structurés, intégration pytest, CLI, Dockerfile. Resources/prompts, plugins, OAuth/SSO, Vault et observabilité sont **hors 0.1**.

**Alternative écartée** : viser d'emblée les plugins et l'observabilité (risque de figer prématurément l'architecture — §34, dernière phrase).

**Conséquences** : les points d'extension (backends de secrets, d'auth MCP, de persistance) sont définis comme interfaces abstraites dès 0.1, mais sans système de plugins.

---

### 2026-09-29 — Réinitialisation des fichiers `.agents/`

**Contexte** : les fichiers d'agents provenaient du projet MyMemoMaster (Node/Express/Vue) et contenaient ~1,8 Mo d'historique sans rapport avec Mircapgen.

**Décision** : réécriture complète pour Mircapgen ; historique de l'ancien projet supprimé (il reste dans l'historique de l'autre dépôt, pas dans celui-ci).

**Alternative écartée** : conserver l'ancien historique en archive dans ce dépôt (pollue le contexte des agents).

**Conséquences** : `CLAUDE.md` et `.agents/` ne mentionnent plus Node, Express, Sequelize, Vue ni JWT. Les règles génériques utiles (audit avant ticket, mise à jour des docs en fin de ticket, préfixes de commit) ont été conservées.

---

### 2026-09-29 — Modèle d'identité à trois acteurs

**Contexte** : le §8 du cahier des charges V0 parlait d'« utilisateurs » sans dire s'il s'agissait de l'humain de l'admin, de l'agent ou de la personne représentée, ce qui bloquait le RBAC et l'audit.

**Décision** : trois identités distinctes (cahier des charges §8) :
- **Administrateur** : compte humain de l'interface d'administration (mot de passe + session), sans accès aux Features et sans groupe métier.
- **Client MCP (agent IA)** : s'authentifie sur l'endpoint MCP (token / API key / OAuth), ne porte aucun droit métier.
- **Utilisateur de l'agent** : identité transmise par l'agent ; c'est elle qui porte les groupes et permissions, et qui sert à l'autorisation, au filtrage de visibilité et à l'audit.

L'identité utilisateur vient du contexte de connexion MCP, jamais d'un paramètre de Feature. Sans identité valide : refus (deny by default). L'audit enregistre client **et** utilisateur.

**Alternative écartée** : un modèle unique d'« utilisateur » qui serait à la fois l'agent, l'humain et l'admin (mélange l'authentification du client et l'autorisation métier).

**Conséquences** : le RBAC ne s'applique qu'aux utilisateurs d'agents ; Mircapgen ne gère pas de mot de passe pour eux et fait confiance à un client authentifié, d'où les questions 20 à 25 ci-dessous ; la visibilité des Features est calculée par utilisateur, pas par client ; les logs et les fixtures de test (`as_user`, `as_group`) portent les deux identités.

---

### 2026-09-29 — Transmission de l'identité, anti-usurpation, Features publiques, provisioning, groupes

> **Partiellement remplacée** : les modes `trusted` / `scoped` / `signed` et la transmission par l'agent sont remplacés par « Deux méthodes d'identification ». Restent en vigueur : Features publiques, provisioning optionnel (désormais réservé à OAuth), groupes (liste unique + `GroupsField`).

**Contexte** : suite au modèle à trois acteurs, il fallait fixer comment l'identité utilisateur arrive, comment éviter l'usurpation, et comment sont définis groupes et utilisateurs (cahier des charges §8.5-8.7, §9.0).

**Décision** :
- L'identité utilisateur est transmise **par l'agent via MCP**, injectée par l'application hôte et non par le modèle de langage.
- Protection contre l'usurpation **configurable par client MCP** : `trusted` (interne), `scoped` (utilisateurs/groupes autorisés + plafond de permissions), `signed` (jeton signé vérifié). Les trois modes et le défaut restent à valider (question 21).
- Les Features publiques sont un choix explicite du développeur, Feature par Feature (`public=True`) ; privées par défaut.
- Le provisioning automatique des utilisateurs est une option, désactivée par défaut, avec `default_groups` restreints.
- Les groupes forment **une liste unique** renseignée par le développeur dans le code ; l'administrateur peut la compléter uniquement si le développeur inclut dans un formulaire un champ dédié (`GroupsField`, nom indicatif). Les groupes du code ne sont pas modifiables depuis l'interface. Les permissions restent toujours déclarées dans le code. Le développeur peut restreindre depuis le code les permissions que l'administrateur peut attribuer (`assignable_permissions` / `forbidden_permissions` sur le champ), pour éviter qu'un admin s'accorde des droits sensibles ; la restriction est aussi appliquée côté serveur.

**Alternative écartée** : identité déclarée acceptée sans condition pour tous les cas (ne convient pas si des tiers utilisent le framework) ; groupes uniquement en base (empêche de versionner les droits avec le code) ; deux mécanismes séparés « en dur » et « dynamique » (remplacé par une liste unique complétable, plus simple).

**Conséquences** : le framework doit gérer un mode d'identité par client MCP ; `mircapgen check` signale les clients `trusted` et les Features publiques ; le plafond de permissions s'ajoute au calcul des droits effectifs ; le framework doit fournir un `GroupsField` et fusionner la liste du code avec les ajouts de l'administrateur (nom unique, groupes du code en lecture seule).

---

### 2026-09-29 — Plafond de permissions pour tous les modes et spécification du mode `signed`

> **Partiellement remplacée** : le plafond de permissions reste en vigueur (attaché à la clé ou au client OAuth). La spécification `signed` est remplacée par la méthode OAuth 2.1.

**Contexte** : le plafond de permissions n'existait qu'en mode `scoped` alors qu'un token de client `trusted` qui fuit expose tous les utilisateurs ; le mode `signed` n'était pas spécifié.

**Décision** :
- Le **plafond de permissions par client** s'applique dans tous les modes ; droits effectifs = permissions de l'utilisateur ∩ plafond du client ; il filtre aussi la visibilité. Sans plafond défini : pas de plafonnement, mais `mircapgen check` avertit.
- Mode **`signed`** : JWT signé par un émetteur de confiance ; Mircapgen **vérifie seulement** (pas d'émission hors utilitaire de test) ; revendications `iss`/`sub`/`aud`/`exp`/`iat`/`azp` ; algorithme fixé par la configuration de l'émetteur (jamais lu dans le jeton) ; asymétrique recommandé, symétrique opt-in ; durée de vie maximale imposée ; clés gérées via le système de secrets ; les droits viennent de Mircapgen, pas du jeton ; pas de liste de révocation au départ (jetons courts + utilisateur désactivable).

**Alternative écartée** : faire émettre les jetons par Mircapgen (en ferait un IAM, hors périmètre §30) ; lire groupes et permissions dans le jeton (l'émetteur déciderait des droits) ; accepter l'algorithme indiqué par le jeton (attaque par changement d'algorithme).

**Conséquences** : il faut une bibliothèque JWT (dépendance à valider, sans doute en extra optionnel) ; le lien `azp` ↔ client authentifié oblige à identifier chaque client de façon unique ; le calcul des droits effectifs et de la visibilité doit intégrer le plafond ; l'échéance du mode `signed` dans la roadmap reste à décider.

---

### 2026-09-29 — SDK MCP : le SDK officiel `mcp` (v2)

**Contexte** : il fallait choisir la brique de protocole MCP (cahier des charges §7, §30 : ne pas réimplémenter MCP). Candidats étudiés : SDK officiel `mcp` v2 (`MCPServer`) et FastMCP 3 (PrefectHQ).

**Décision** : Mircapgen s'appuie sur le **SDK officiel `mcp` v2**. Le SDK est isolé derrière un adaptateur (`mcp/` dans le dépôt) : le reste du framework n'importe jamais `mcp` directement.

**Alternative écartée** : FastMCP 3. Il fournirait nativement le masquage des tools par utilisateur et un middleware mature, mais Mircapgen deviendrait une surcouche d'un autre framework avec des concepts en double (providers, transforms, checks d'autorisation), et une dépendance à un projet tiers en plus du SDK.

**Conséquences** : le filtrage des Features par utilisateur (§9.1), la résolution de l'identité (claims du jeton, en-tête, `_meta`, variable d'environnement) et le pipeline d'autorisation sont **à construire par Mircapgen** ; le middleware du SDK est marqué provisoire, donc le pipeline de Mircapgen ne doit pas en dépendre pour la logique de sécurité ; les fixtures `as_user` / `as_group` sont à construire ; les points non vérifiés (accès à l'identité dans un handler `tools/list`, canal d'identité en stdio) doivent être validés par un spike avant de figer l'architecture.

---

### 2026-09-29 — L'identité est renseignée par l'agent selon le format du Helper

> **Remplacée** par « Deux méthodes d'identification : clé personnelle et OAuth 2.1 » : le modèle de langage n'est plus une source d'identité.

**Contexte** : il fallait préciser qui produit l'identité utilisateur et comment Mircapgen s'assure qu'elle est correcte (cahier des charges §8.5).

**Décision** : l'agent lit le Helper à la connexion, qui lui indique les informations d'identité à transmettre et leur format ; il les renseigne, et Mircapgen **vérifie la conformité** de la réponse (format, champs, utilisateur connu et actif) et renvoie une erreur explicite sinon. Les Features accèdent à l'identité par un objet de contexte (ex. `ctx.user`), jamais par un paramètre métier.

**Alternative écartée** : imposer que l'identité soit toujours injectée par le code de l'application hôte, hors modèle (plus sûr, mais exclut les clients MCP génériques où l'IA est seule à parler au serveur). Conservée uniquement pour les modes `scoped` et `signed`.

**Conséquences** : en mode `trusted`, l'identité produite par le modèle peut être erronée ou détournée par injection de prompt ; le plafond de permissions par client en limite l'impact ; l'identité doit être connue avant `tools/list` pour filtrer les Features (§9.1), ce qui exige soit une étape d'identification en début de session, soit une identité jointe à chaque requête (question ouverte 20) ; à valider par spike : persistance de l'identité dans la session avec le SDK officiel, notification de changement de la liste des tools, comportement si le protocole est sans état.

### 2026-09-29 — Deux méthodes d'identification : clé personnelle et OAuth 2.1

**Contexte** : l'étude des clients (Claude, ChatGPT, Hermes, OpenClaw) montre qu'avec un assistant générique, une identité renseignée par le modèle est de fait auto-déclarée par la personne qui écrit à l'IA (aucune protection anti-fraude). Claude ne fournit d'identité utilisateur vérifiable que par OAuth ; son en-tête statique est partagé par l'organisation. Exigence de l'utilisateur : configuration une seule fois, aucune action à l'usage, utilisable en service interne comme grand public.

**Décision** (cahier des charges §8) :
- **Principe** : l'identité est prouvée par un identifiant d'accès que détient le client (clé ou jeton), jamais déclarée par le modèle. Le Helper ne porte plus de format d'identité.
- **Méthode 1, clé personnelle** : secret lié à un utilisateur, créé par l'admin, affiché une fois, conservé haché, révocable, expiration facultative, plafond de permissions propre, une clé par utilisateur et par agent.
- **Méthode 2, OAuth 2.1** : Mircapgen = **serveur de ressources** (401 + métadonnées RFC 9728, vérification signature / `iss` / `aud` / `exp` / `sub`), fournisseur d'identité **externe** ; prérequis : PKCE S256, DCR ou CIMD, métadonnées joignables, refresh. Jamais de jeton accepté s'il n'est pas émis pour ce service ni retransmis à un autre.
- Les droits viennent de Mircapgen, pas du jeton. Le plafond de permissions s'applique aux deux méthodes. Provisioning automatique réservé à OAuth. Features publiques utilisables avant connexion.
- Méthodes activables séparément ou ensemble (`identity.methods`).

**Alternative écartée** : identité relayée par le modèle (modes `trusted` / `scoped`) ; serveur d'autorisation intégré à Mircapgen (ferait de Mircapgen un IAM, contraire au §30) ; jetons signés émis par l'application hôte comme méthode à part entière (recouvert par OAuth).

**Conséquences** : dépendance à un fournisseur d'identité pour OAuth (choix de référence à faire) ; la clé statique de Claude étant partagée par l'organisation, les clés personnelles ne conviennent pas aux connecteurs Claude hébergés (OAuth seulement) ; le SDK officiel gère `TokenVerifier` + `AuthSettings`, à valider par prototype pour l'usage uniforme clé / jeton et pour la disponibilité de l'utilisateur dès `tools/list` ; la roadmap (§29) place encore « OAuth » en 0.3 : à réviser avec le redécoupage du MVP ; sources partiellement secondaires (ChatGPT, OpenClaw, Hermes), à confirmer par des tests réels.

### 2026-09-29 — Redécoupage du MVP en 0.0 / 0.1 et roadmap révisée

**Contexte** : avec deux méthodes d'identification, RBAC, admin, secrets et CLI, la 0.1 initiale (cahier des charges §28) était trop grosse et retardait la validation de l'idée centrale.

**Décision** (cahier des charges §28-29) :
- **0.0 prototype** : tranche verticale (Feature → tool MCP, clé personnelle, permission + plafond, filtrage par utilisateur, `as_user`), pour lever les incertitudes techniques.
- **0.1 MVP** : cœur complet sécurisé, **sans interface web**, administré par CLI et fichiers (clés personnelles, RBAC, Helper, config/secrets, logs/audit, pytest, CLI, Dockerfile).
- **0.2** OAuth 2.1 et clients grand public ; **0.3** administration web et formulaires déclaratifs ; **0.4** MCP avancé et extensibilité (resources, prompts, plugins, Vault, `docs`) ; **0.5** observabilité ; **1.0** stabilisation.
- OAuth est placé **avant** l'administration web (sécurité et accès aux assistants grand public ; la CLI couvre l'administration).

**Alternative écartée** : garder l'administration web dans la 0.1 (plus gros chantier, retarde la première version utilisable) ; placer l'administration web avant OAuth (reste possible si elle est jugée prioritaire).

**Conséquences** : le cahier de la 0.1 impose des commandes CLI de gestion des utilisateurs et clés ; la persistance par défaut doit être décidée avant la 0.1 ; les fixtures et l'adaptateur `mcp/` sont validés dès la 0.0 ; chaque version a des critères de sortie et des décisions préalables listés en §28.

### 2026-09-29 — Outillage Python et dépendances du cœur

**Contexte** : la version minimale de Python, le packaging, le lint, le typage, le framework web et la validation bloquaient le démarrage de la 0.0. Vérifications faites : poste de développement en Python 3.12.0 ; `mcp` 2.2.0 (MIT) exige Python ≥ 3.10 et dépend de `anyio`, `pydantic` ≥ 2.12, `starlette`, `uvicorn`, `pyjwt[crypto]`, `jsonschema`, `opentelemetry-api` ; le nom `mircapgen` est libre sur PyPI.

**Décision** :
- **Python 3.11 minimum**, développement sur 3.12, tests sur 3.11 à 3.13 (3.10 arrive en fin de vie en octobre 2026).
- **`pyproject.toml`** (PEP 621), backend **`hatchling`**, disposition `src/`.
- **`uv`** pour l'environnement, l'installation et le verrou (`uv.lock`) ; installé sur le poste de développement (0.12.20).
- **`ruff`** pour le lint et le formatage ; **`pyright`** en mode strict sur `src/` ; **`pytest`** avec le plugin `anyio`.
- **Starlette** (framework web) et **Pydantic v2** (validation et schémas), déjà requis par le SDK ; **PyYAML** (`safe_load`) pour `mircap.yaml`.
- **Dépendances déclarées une seule fois dans `pyproject.toml`**, verrou dans `uv.lock`, installation automatique par `uv sync`. Un `requirements.txt` n'est produit que par export (`uv export`) si Docker ou la CI en ont besoin.

**Alternative écartée** : `mypy` (moins adapté au typage des décorateurs qui conservent la signature, central pour `@feature`) ; `pytest-asyncio` (dépendance de plus alors que `anyio` est déjà là) ; FastAPI/Flask (doublon avec Starlette déjà requis) ; un fichier de dépendances tenu à la main en plus de `pyproject.toml` (deux sources de vérité à synchroniser).

**Conséquences** : pas de dépendance nouvelle hors PyYAML pour la 0.0 ; `pyright` demande Node (le paquet `pyright` le télécharge automatiquement pour les contributeurs qui n'en ont pas) ; les versions de Python et de `mcp` sont bornées dans `pyproject.toml` (`mcp>=2,<3`) ; les commandes de vérification de `CONVENTIONS.md` sont la référence de la checklist de livraison.

### 2026-09-29 — Persistance : contrat `Store`, SQLAlchemy Core, migrations à la Django

**Contexte** : les utilisateurs, clés, groupes ajoutés et paramètres doivent être conservés, et le développeur doit pouvoir choisir SQLite (par défaut) ou une base serveur fournie par lui ou son hébergeur, avec des migrations automatisables (cahier des charges §12.2).

**Décision** :
- **Contrat `Store`** (async) ; implémentations : `SqlStore` (défaut), `MemoryStore` (tests), implémentation personnalisée via `MircapApp(store=...)`. Suite de tests de conformité commune.
- **`SqlStore` fondé sur SQLAlchemy Core** (sans ORM) : une seule voie de code pour SQLite et les bases serveur ; base choisie par `database.url` ; mot de passe fourni comme `Secret` (variable d'environnement ou backend de secrets) ; pilote d'une base serveur en extra optionnel. Mircapgen ne gère jamais de serveur de base.
- **Migrations avec Alembic**, livrées avec le paquet, appliquées explicitement (`mircapgen db upgrade`, `status`, `history`), en avant uniquement, sauvegarde automatique du fichier SQLite avant migration, table de suivi. Au démarrage, migrations en attente = refus de démarrer avec message ; `new` et `dev` migrent automatiquement ; `database.auto_migrate: true` en option avec verrou.
- Tables du framework préfixées `mircap_` ; les données métier du développeur restent hors du framework.
- **Nouvelles dépendances du cœur validées** : `SQLAlchemy` et `alembic`.

**Alternative écartée** : `sqlite3` standard + implémentation Postgres séparée avec notre propre système de migrations (deux voies de code à maintenir) ; migration automatique silencieuse au démarrage pour tous (risquée avec plusieurs instances) ; retours arrière (non testés, dangereux pour des données de sécurité) ; SQLAlchemy ORM (contraire au §30).

**Conséquences** : SQLite ne convient qu'à une seule instance (limite documentée de la 0.1) ; `last_used_at` des clés à écrire de façon espacée (au plus une fois par minute et par clé) ; chaque version qui change le schéma doit livrer sa migration, testée ; questions ouvertes : migrations des tables propres au développeur (question 36), mode d'accès synchrone en threads ou asynchrone (question 37).

### 2026-09-29 — Tables métier hors du cœur ; accès à la base synchrone dans des threads

**Contexte** : deux questions restaient ouvertes après la décision de persistance (migrations des tables du développeur, mode d'accès synchrone ou asynchrone). Principe donné par l'utilisateur : le développeur écrit des variables et fonctions Python métier, le framework gère l'infrastructure derrière.

**Décision** :
- Les **tables métier du développeur ne sont pas gérées par le cœur** : il garde l'outil de son choix ; une extension (par exemple `mircapgen-sqlalchemy`, §26) pourra les prendre en charge plus tard.
- **Accès à la base** : interface `Store` asynchrone ; `SqlStore` exécute SQLAlchemy de façon **synchrone dans des threads** (`anyio.to_thread`). Invisible pour le développeur.

**Alternative écartée** : gérer les migrations des tables métier dans le cœur (le code métier dépendrait de la couche de données du framework, contraire au §2.1 et au §30) ; SQLAlchemy asynchrone dès le départ (matrice de pilotes asynchrones à maintenir pour un gain nul à ce volume de données).

**Conséquences** : un seul pilote synchrone à livrer par base serveur ; le passage à l'asynchrone reste possible sans changer l'API ; pas de branche Alembic pour le développeur dans le cœur.

### 2026-09-29 — Déclaration des permissions, Features sans permission, `require_credential`

**Contexte** : questions 7, 8 et 18 du cahier des charges (déclaration des permissions, permissions obligatoires, Features publiques).

**Décision** (cahier §9.2, §24, §8.9) :
- Les permissions se **déclarent dans le décorateur** de la Feature ; pas de registre séparé ; format `domaine.verbe`, joker `*` en dernier segment, `*` seul réservé aux groupes du code, une permission par Feature en 0.1.
- Le développeur peut proposer un **formulaire** (`PermissionField`) qui permet à l'administrateur de changer la permission exigée par une Feature, dans la limite de `assignable_permissions` / `forbidden_permissions` ; la valeur du formulaire prime sur celle du décorateur ; modifications journalisées.
- Une Feature sans `permission` ni `public=True` **n'est pas accessible** (ni listée ni appelable) et une erreur est journalisée ; le service démarre quand même ; `check` la signale en erreur.
- `identity.require_credential: true` (désactivé par défaut) exige un identifiant valide pour toute connexion, Features publiques comprises.
- `check` signale les permissions inconnues référencées par un groupe ou un plafond (erreur) et les permissions exigées mais jamais accordées (avertissement).

**Alternative écartée** : refuser de démarrer si une Feature n'a ni permission ni `public` (proposé par l'agent ; l'utilisateur préfère qu'une Feature défaillante n'empêche pas le reste du service de tourner) ; registre de permissions séparé tenu à la main.

**Conséquences** : le calcul de la permission effective doit lire le `Store` (valeur du formulaire) avant le décorateur ; le RBAC, la visibilité, `check` et `inspect` utilisent la permission effective ; une erreur de configuration sur une Feature est visible surtout dans les logs et dans `check` (à lancer en CI).

**Cas `permission` + `public=True`** : l'utilisateur envisageait « le plus permissif fait foi » ; l'agent a signalé que cela contredit *deny by default* et *least privilege* (une erreur de copier-coller rendrait publique une Feature protégée) et a recommandé la règle la plus restrictive. **Retenu (recommandation de l'agent, validée par l'utilisateur)** : la permission est exigée, `public` est ignoré, un avertissement est journalisé et `check` le signale. `PermissionField` peut seulement changer la permission, jamais rendre une Feature publique.

### 2026-10-01 — Le décorateur de Feature se nomme `@feature`

**Contexte** : l'écriture de l'API (`@mircap.feature`, `@feature` ou `@app.feature`) était ouverte (cahier §34, question 25) ; l'API publique est le produit.

**Décision** : `@feature`, importé depuis le paquet (`from mircapgen import feature`), comme dans l'exemple du §32. Choix de l'utilisateur, motivé par la brièveté.

**Alternative écartée** : `@mircap.feature` (plus long, suppose un objet `mircap` à définir) ; `@app.feature` (lie chaque Feature à l'instance de l'application dès l'écriture).

**Conséquences** : le décorateur n'est lié à aucune instance d'application, donc le registre des Features est a priori global au module ; cela pose la question de l'isolation des tests et de plusieurs applications dans un même processus (question 40) ; l'accès au contexte (`ctx.user`) reste à définir (question 41). Les noms `MircapApp` et `app.run()` du §32 restent indicatifs.

### 2026-10-01 — Prototype 0.0 : choix d'implémentation

**Contexte** : première implémentation du cahier des charges (§28.2) sur le SDK officiel `mcp` 2.2.0.

**Décision** :
- **Serveur MCP bas niveau** (`mcp.server.lowlevel.Server` avec `on_list_tools` et `on_call_tool`) plutôt que `MCPServer` : la liste des tools et le traitement des appels passent par le `Dispatcher` de Mircapgen.
- **`@feature` est un marqueur** : il attache une `FeatureSpec` à la fonction sans état global ; `MircapApp` découvre les fonctions marquées en parcourant un module ou un paquet (questions 36 et 37 : provisoire, validation de l'utilisateur en attente pour la 37 — paramètre annoté `Context`).
- **Identité transportée dans l'`AccessToken` du SDK** (`claims["mircap_identity"]`) par un `TokenVerifier` de clés, lue dans les handlers par `get_access_token()`. En test, une source d'identité fixe la remplace.
- **Un identifiant présenté mais refusé donne un 401**, jamais un accès anonyme (middleware `CredentialGateMiddleware`).
- **Un tool caché et un tool inexistant donnent la même réponse** (`UnknownFeatureError`), pour ne pas révéler l'existence d'une Feature.
- **Les arguments des Features ne sont jamais journalisés**, et les erreurs de validation n'affichent jamais les valeurs reçues.
- **Format de clé provisoire** : `mk_<8 hex>_<secret>`, empreinte SHA-256 (clé aléatoire à haute entropie, hachage lent inutile).
- `starlette` et `uvicorn` déclarés comme dépendances directes.

**Alternative écartée** : `MCPServer` (filtrage par utilisateur à bricoler dans le middleware provisoire du SDK) ; registre global de Features ; lire l'identité dans un en-tête personnalisé (le SDK déconseille d'y mettre l'identité).

**Conséquences** : le SDK étant en 2.x avec un middleware « provisoire », seule l'authentification par `TokenVerifier` et `get_access_token()` est utilisée côté sécurité ; l'identité doit rester un objet `Identity` non sérialisé dans les claims (à revoir si le SDK les sérialise un jour).

---

## Questions ouvertes

> Reprises du cahier des charges §34. **L'agent ne tranche pas seul** : il propose une recommandation argumentée, l'utilisateur valide, puis la question est déplacée ci-dessus en décision prise.
> Ajouter une ligne « Recommandation de l'agent » quand une analyse a été faite.

| # | Question | Bloque | Statut |
|---|----------|--------|--------|
| 1 | ~~Framework web sous-jacent (admin + routes HTTP) ?~~ | Admin, transport HTTP | **Résolue : Starlette** (voir « Outillage Python et dépendances du cœur ») |
| 2 | ~~Système de validation de données / génération de schémas ?~~ | Features, MCP | **Résolue : Pydantic v2** (idem) |
| 3 | Moteur de templates pour l'admin ? | Admin | Ouverte |
| 4 | ~~Embarquer un ORM ou seulement une interface de persistance ?~~ | RBAC, config | **Résolue** : interface `Store` + `SqlStore` sur SQLAlchemy Core, sans ORM |
| 5 | ~~Stockage par défaut (utilisateurs, groupes, configuration) ?~~ | RBAC, config | **Résolue** : SQLite par défaut, base serveur au choix par configuration |
| 6 | ~~Gestion des migrations de base de données ?~~ | Persistance | **Résolue** : Alembic, commandes `mircapgen db ...`, en avant uniquement |
| 7 | ~~Déclaration précise des permissions (format, jokers, registre) ?~~ | RBAC | **Résolue** : dans le décorateur, paramétrable par formulaire (cahier §9.2) |
| 8 | ~~Permissions obligatoires sur toutes les Features MCP ?~~ | Features, sécurité | **Résolue** : `permission` ou `public=True` requis, sinon Feature inaccessible + erreur journalisée ; cas des deux : question 38 |
| 9 | Association resources / prompts aux Features ? | 0.4 | Reportée |
| 10 | Chargement dynamique des instructions du Helper ? | Helper | Ouverte |
| 11 | Mécanismes de confirmation pour les Features sensibles (`risk`) ? | Sécurité | Ouverte |
| 12 | Périmètre de l'admin déclarative ? | Admin | Ouverte |
| 13 | Quelle API publique est considérée stable ? | 1.0 | Reportée |
| 14 | Système de plugins ? | 0.4 | Reportée |
| 15 | Versioning d'un microservice Mircapgen ? | Manifeste | Ouverte |
| 16 | ~~Version minimale de Python, outil de packaging, lint/format/typage ?~~ | Initialisation | **Résolue** : Python 3.11+, hatchling, uv, ruff, pyright (voir « Outillage Python et dépendances du cœur ») |
| 17 | ~~Choix du SDK MCP à encapsuler ?~~ | Couche MCP | **Résolue : SDK officiel `mcp` v2** (voir décision ci-dessus). Étude 2026-09-29 : candidats = SDK officiel `mcp` v2 (classe `MCPServer`, ex-FastMCP intégré) et FastMCP 3 (PrefectHQ, Apache-2.0). Les deux : TokenVerifier/AccessToken avec claims, client de test en mémoire, transports stdio/HTTP. FastMCP 3 masque nativement les tools par utilisateur (`auth=` sur le composant, filtrage de `list_tools`, activation par session) ; le SDK officiel ne le fait pas nativement (middleware « provisoire » ou handler bas niveau). Aucun des deux ne permet de simuler un utilisateur en test : `as_user` / `as_group` sont à construire. Docs SDK officiel : les en-têtes sont des entrées client, « jamais l'identité ». Recommandation : spike comparatif avant de choisir, et isoler le SDK derrière un adaptateur `mcp/`. |
| 18 | Priorité entre sources de configuration (env, fichier, base, admin, secrets) ? | Config | Ouverte (§12.1) |
| 19 | Schéma de branches Git ? | Workflow | Ouverte (ajoutée) |
| 20 | Prototype : `TokenVerifier` traite-t-il uniformément clés et jetons OAuth, et l'utilisateur est-il disponible dès `tools/list` (filtrage §9.1) et dans les Features (`ctx.user`) ? | Auth, MCP | **Partiellement résolue (0.0)** : oui pour les clés en HTTP, utilisateur disponible dès `tools/list` et dans les Features ; le cas des jetons OAuth reste à vérifier en 0.2 (cahier §34 q.16) |
| 21 | Fournisseur d'identité de référence pour OAuth ; serveur d'autorisation intégré optionnel plus tard (plugin) ? | Auth OAuth | Ouverte (cahier §34 q.17) |
| 22 | ~~Feature publique : appelable sans aucun identifiant, ou identifiant exigé pour toute connexion (option) ?~~ | Features, sécurité | **Résolue** : Feature par Feature + option `identity.require_credential` (cahier §8.9) |
| 23 | Clés personnelles : format, préfixe, hachage, expiration par défaut, libre-service, rotation, limitation des essais ? | Auth clés | Ouverte (cahier §34 q.19) |
| 24 | Stockage des groupes ajoutés par l'administrateur via `GroupsField` et fusion avec la liste du code ? | RBAC | Principe acquis (liste unique complétable), détail ouvert (cahier §34 q.20) |
| 25 | Comportement du provisioning automatique pour un utilisateur ensuite désactivé/supprimé ? | RBAC | Option acquise (désactivée par défaut), détail ouvert (cahier §34 q.21) |
| 26 | Relier les scopes OAuth au plafond de permissions ? (le `client_id` d'un client DCR change à chaque connexion : un plafond par `client_id` ne tient qu'avec CIMD ou un client préenregistré) | Auth OAuth | Ouverte (cahier §34 q.22) |
| 27 | Tests réels du flux OAuth et des clés avec Claude, ChatGPT, Hermes et OpenClaw avant de figer l'API ? | Auth | Ouverte (cahier §34 q.23) |
| 28 | Stockage et protection du journal d'audit ? | Logs, sécurité | Ouverte (cahier §34 q.24) |
| 29 | ~~Écriture définitive de l'API publique (`@mircap.feature` / `@feature` / `@app.feature`) ?~~ | API publique | **Résolue** : `@feature` importé depuis `mircapgen` (cahier §34 q.25) |
| 30 | Identité en stdio (clé en variable d'environnement ?) | Auth | Ouverte (cahier §34 q.26) |
| 31 | Sécurité du transport HTTP : HTTPS, `Origin`, limitation des essais de clés ? | Sécurité | Ouverte (cahier §34 q.27) |
| 32 | Autorisation au niveau des données (filtrage par utilisateur dans les Features) ? | RBAC | Ouverte (cahier §34 q.28) |
| 33 | Comportement minimal de `risk` en 0.1, ou report à la 0.4 ? | Sécurité | Ouverte (cahier §34 q.29, lié à q.11) |
| 34 | Mode de développement sans authentification ? | CLI, sécurité | Ouverte (cahier §34 q.30) |
| 35 | Helper branché sur le champ `instructions` de MCP ; variation par utilisateur ? | Helper | Ouverte (cahier §34 q.31, lié à q.10) |
| 36 | ~~Le développeur peut-il versionner et appliquer les migrations de ses propres tables via `mircapgen db` (branches Alembic) ?~~ | Persistance | **Résolue** : hors du cœur, extension plus tard (cahier §34 q.32) |
| 37 | ~~SQLAlchemy synchrone en threads, ou asynchrone avec pilotes asynchrones ?~~ | Persistance | **Résolue** : synchrone en threads, invisible (cahier §34 q.33) |
| 38 | ~~Feature déclarant `permission` **et** `public=True` : résolution la plus permissive ou la plus restrictive ?~~ | Sécurité | **Résolue** : la plus restrictive, avec avertissement (cahier §34 q.34) |
| 39 | ~~`PermissionField` peut-il rendre une Feature publique, ou seulement changer la permission ?~~ | Admin, sécurité | **Résolue** : seulement changer la permission (cahier §34 q.35) |
| 40 | ~~Registre des Features global au module ou lié à `MircapApp` ; isolation des tests ?~~ | API publique, tests | **Résolue provisoirement** : marqueur + découverte, sans état global (cahier §34 q.36) |
| 41 | Accès d'une Feature au contexte (`ctx.user`) : paramètre annoté `Context` ou fonction d'accès ? | API publique | **Implémentée provisoirement** : paramètre annoté `Context`, à valider (cahier §34 q.37) |

---

### 2026-10-13 — CI GitHub Actions et audit des dépendances

**Contexte** : le projet a déjà `pytest`, `ruff` et `pyright` ; sans CI, rien n'empêche de fusionner du code qui échoue, et la promesse de sécurité du framework exige de surveiller les CVE des dépendances.

**Décision** : GitHub Actions, avec `uv sync --locked`. Audit via `pip-audit` lancé par `uvx` sur `uv export` : **outil de CI uniquement, non ajouté à `pyproject.toml`**. Audit rejoué chaque semaine (cron).

**Alternative écartée** : `pip-audit` dans le groupe `dev` (dépendance supplémentaire à maintenir pour un usage uniquement CI) ; Dependabot/CodeQL reportés.

**Conséquences** : toute PR doit passer lint, format, typage et tests sur 2 OS et 2 versions de Python ; une CVE sur une dépendance fait échouer le job `audit`.
