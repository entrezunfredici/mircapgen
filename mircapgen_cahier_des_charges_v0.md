# Mircapgen — Cahier des charges fonctionnel et technique

> Version de travail : V0
>
> Objectif : définir une première architecture cohérente de **Mircapgen**, un framework Python destiné à simplifier la création de microservices MCP orientés agents IA.

---

## 1. Vision du projet

**Mircapgen** est un framework Python permettant de créer rapidement des microservices exposés via le protocole MCP, avec un maximum de briques techniques déjà intégrées.

L'objectif est que le développeur puisse se concentrer principalement sur :

- la logique métier ;
- les fonctionnalités exposées aux agents IA ;
- les instructions décrivant comment et quand utiliser ces fonctionnalités ;
- la configuration spécifique du microservice ;
- les tests métier.

Mircapgen prend en charge les éléments techniques récurrents nécessaires autour d'un microservice MCP :

- serveur MCP ;
- exposition des fonctionnalités ;
- authentification ;
- gestion des utilisateurs ;
- gestion des groupes ;
- gestion des permissions ;
- interface d'administration ;
- configuration ;
- secrets ;
- logs ;
- tests ;
- documentation destinée aux agents ;
- outils de développement.

L'idée centrale est la suivante :

> Le développeur écrit une fonctionnalité métier, et Mircapgen se charge de la transformer en fonctionnalité exploitable de manière sécurisée par un agent IA.

---

# 2. Principes d'architecture

Mircapgen doit suivre plusieurs principes fondamentaux.

## 2.1 Séparation métier / infrastructure

Le code métier doit rester indépendant autant que possible de :

- MCP ;
- l'authentification ;
- la gestion des permissions ;
- l'interface d'administration ;
- les logs ;
- le stockage de configuration.

Mircapgen fournit ces couches automatiquement autour du code métier.

Architecture logique :

```text
Agent IA
   │
   │ MCP
   ▼
┌─────────────────────────────────────┐
│             Mircapgen               │
│                                     │
│  MCP Gateway                        │
│       │                             │
│       ▼                             │
│  Authentication                    │
│       │                             │
│       ▼                             │
│  Authorization / RBAC              │
│       │                             │
│       ▼                             │
│  Middleware                        │
│       │                             │
│       ▼                             │
│  Business Features                 │
│       │                             │
│       ▼                             │
│  Configuration / Persistence       │
│                                     │
│  Admin UI                          │
│  Helper / Agent Instructions       │
│  Logs / Tests / Observability      │
└─────────────────────────────────────┘
```

---

# 3. Concept central : la Feature

La **Feature** est l'unité principale de développement dans Mircapgen.

Une Feature représente une capacité métier pouvant être exposée à un agent IA.

Exemples :

```text
customer.search
customer.create
customer.update
invoice.read
invoice.generate
server.restart
file.upload
```

Le développeur ne devrait pas avoir à écrire directement toute la couche MCP autour de chaque fonction.

Exemple conceptuel :

```python
@mircap.feature(
    name="customer.search",
    description="Recherche un client",
    permission="customer.read"
)
async def search_customer(query: str):
    ...
```

À partir de cette déclaration, Mircapgen pourrait automatiquement gérer :

```text
fonction Python
      │
      ├── exposition MCP
      ├── validation des paramètres
      ├── génération du schéma d'entrée
      ├── génération du schéma de sortie
      ├── permissions
      ├── documentation
      ├── instructions destinées à l'agent
      ├── logs
      └── tests / helpers de tests
```

## 3.1 Métadonnées d'une Feature

Une Feature pourrait posséder notamment :

```text
name
label
description
permission
public
instructions
constraints
risk
mcp
tags
version
deprecated
```

Une Feature déclare `permission` ou `public=True` (§8.9, §24) ; si les deux sont déclarées, la règle la plus restrictive s'applique et un avertissement est journalisé (§24). `risk` est décrit au §25 et `mcp` au §7.

Exemple :

```python
@mircap.feature(
    name="customer.delete",
    label="Supprimer un client",
    description="Supprime définitivement un client",
    permission="customer.delete",
    tags=["customer", "dangerous"]
)
async def delete_customer(customer_id: int):
    ...
```

---

# 4. Organisation du code métier

Chaque domaine métier peut être organisé dans un module dédié.

Exemple :

```text
app/
└── features/
    ├── customer/
    │   ├── search.py
    │   ├── create.py
    │   ├── update.py
    │   ├── delete.py
    │   ├── instructions.md
    │   └── tests/
    │
    ├── invoice/
    │   ├── search.py
    │   ├── generate.py
    │   ├── instructions.md
    │   └── tests/
    │
    └── system/
        ├── status.py
        ├── restart.py
        └── instructions.md
```

Le framework doit permettre deux approches :

1. petites instructions directement déclarées dans la Feature ;
2. documentation plus riche stockée dans des fichiers dédiés.

---

# 5. Helper destiné aux agents IA

Chaque microservice Mircapgen doit exposer un **Helper** permettant à un agent IA de comprendre :

- ce que fait le microservice ;
- quelles fonctionnalités sont disponibles ;
- comment les utiliser ;
- dans quel ordre utiliser certaines fonctionnalités ;
- quelles contraintes doivent être respectées.

Exemple conceptuel :

```yaml
name: crm-service

description:
  Microservice permettant de consulter et modifier les données CRM.

instructions:
  - Toujours rechercher un client avant d'en créer un nouveau.
  - Vérifier l'identifiant avant toute modification.
  - Une suppression doit être explicitement demandée par l'utilisateur.
```

## 5.1 Instructions par Feature

Chaque Feature peut posséder ses propres instructions.

Exemple :

```markdown
# customer.delete

## Usage

Utiliser cette fonctionnalité uniquement lorsqu'un utilisateur demande explicitement la suppression d'un client.

## Préconditions

- vérifier que le client existe ;
- récupérer son identifiant ;
- vérifier les permissions de l'utilisateur.

## Contraintes

Ne jamais utiliser cette fonction pour nettoyer automatiquement des doublons sans validation.
```

## 5.2 Séparation des concepts

Mircapgen doit distinguer :

### Description

Ce que fait la fonctionnalité.

### Instructions

Comment et quand un agent doit l'utiliser.

### Constraints

Ce que l'agent ne doit pas faire avec cette fonctionnalité.

Cette séparation doit permettre de produire de meilleures descriptions MCP et de meilleurs prompts pour les agents.

---

# 6. Découverte automatique des capacités

Mircapgen doit pouvoir générer automatiquement une vue des fonctionnalités disponibles.

Exemple :

```text
CRM MCP Service

Capabilities

customer.search
  Recherche des clients.
  Permission : customer.read

customer.create
  Crée un nouveau client.
  Permission : customer.create

customer.delete
  Supprime un client.
  Permission : customer.delete
```

Cette découverte doit être générée à partir des déclarations de Features afin d'éviter les duplications de documentation.

---

# 7. Couche MCP

Mircapgen doit fournir une couche d'intégration MCP standardisée.

Le framework doit notamment gérer :

- les tools ;
- les resources ;
- les prompts ;
- les transports ;
- la sérialisation ;
- la validation des entrées et sorties.

## 7.1 Exposition automatique

Une Feature peut être exposée automatiquement sous forme de tool MCP.

Exemple :

```python
@mircap.feature(
    name="customer.search",
    mcp=True
)
async def search_customer(query: str):
    ...
```

Mircapgen génère automatiquement le tool correspondant.

## 7.2 Contrôle explicite

Le développeur doit pouvoir décider qu'une Feature reste interne.

```python
@mircap.feature(
    name="customer.reindex",
    mcp=False
)
async def reindex_customers():
    ...
```

---

# 8. Modèle d'identité et authentification

Mircapgen distingue **trois identités** qui ne doivent jamais être confondues.

**Principe fondateur : l'identité de l'utilisateur est prouvée par un identifiant d'accès (clé ou jeton) que détient le client, jamais déclarée par le modèle de langage.** L'IA ne choisit pas pour qui elle agit et ne voit jamais le secret qui la prouve.

```text
┌──────────────────┐        ┌──────────────────────────┐
│  Administrateur  │        │  Utilisateur de l'agent  │
│  (humain)        │        │  (personne représentée)  │
└────────┬─────────┘        └────────────┬─────────────┘
         │ interface web                 │ configure une fois :
         ▼                               │ clé personnelle ou connexion OAuth
┌──────────────────┐        ┌────────────▼─────────────┐
│    Admin UI      │        │  Agent IA (client MCP)   │
│  paramétrage     │        │  Claude, ChatGPT, Hermes │
└──────────────────┘        │  OpenClaw, application…  │
                            └────────────┬─────────────┘
                                         │ MCP + identifiant d'accès
                                         ▼
                            ┌──────────────────────────┐
                            │   Endpoint MCP           │
                            │   Features + RBAC        │
                            └──────────────────────────┘
```

## 8.1 Les trois acteurs

### Administrateur

Compte humain permettant de se connecter à l'interface d'administration pour paramétrer le microservice (configuration, secrets, utilisateurs d'agents, groupes, permissions, clés, consultation des logs).

- s'authentifie par identifiant et mot de passe, avec session ;
- ne passe pas par le MCP ;
- ses droits sont des droits d'**administration** de l'interface, distincts du RBAC métier ;
- n'appartient à aucun groupe de droits métier et n'a donc pas, en tant qu'administrateur, accès aux Features ;
- jusqu'à l'arrivée de l'interface d'administration (0.3), ce rôle est tenu par la personne qui utilise la CLI (§18.6) sur la machine ou le conteneur du service.

### Client MCP (agent IA)

Application ou agent IA qui se connecte à l'endpoint MCP du microservice : un assistant grand public (Claude, ChatGPT), un agent auto-hébergé (Hermes, OpenClaw) ou une application développée en interne.

- présente à Mircapgen l'identifiant d'accès de l'utilisateur (clé ou jeton OAuth, voir §8.4) ;
- ne porte aucun droit métier par lui-même ;
- garde l'identifiant d'accès dans sa configuration : le modèle de langage ne le voit pas.

### Utilisateur de l'agent

Personne (ou entité) pour le compte de laquelle l'agent agit.

- c'est **son identité** qui est utilisée pour l'autorisation, le filtrage des Features visibles et l'audit ;
- il appartient à un ou plusieurs **groupes de droits** (§9) ;
- Mircapgen ne stocke pas de mot de passe pour lui : sa preuve d'identité est soit une clé personnelle (Mircapgen n'en garde que l'empreinte), soit un jeton émis par un fournisseur d'identité externe.

## 8.2 Résumé des rôles

| Acteur | Interface | Preuve d'identité | Sert à | Porte des groupes ? |
|--------|-----------|-------------------|--------|---------------------|
| Administrateur | Admin UI | mot de passe + session | paramétrer le service | Non |
| Client MCP | Endpoint MCP | présente l'identifiant d'accès | se connecter et agir | Non |
| Utilisateur de l'agent | (via l'agent) | clé personnelle ou jeton OAuth | autorisation, visibilité, audit | **Oui** |

## 8.3 Authentification de l'administrateur

Fonctions prévues :

- mots de passe sécurisés ;
- sessions ;
- logout ;
- changement de mot de passe ;
- réinitialisation éventuelle ;
- MFA optionnel à terme.

## 8.4 Les deux méthodes d'identification de l'utilisateur d'agent

Mircapgen propose **deux méthodes**, activables séparément ou ensemble :

```yaml
identity:
  methods: [key, oauth]
```

Objectif commun : l'utilisateur **configure son agent une seule fois**, puis n'a plus rien à faire à l'usage. Les jetons OAuth se renouvellent automatiquement, et les clés n'expirent que si le développeur le décide.

| | Clé personnelle | OAuth 2.1 |
|---|---|---|
| **Principe** | une clé secrète liée à un utilisateur, collée dans la configuration de l'agent | l'utilisateur se connecte une fois dans son navigateur, l'agent reçoit un jeton |
| **Configuration** | une fois : coller la clé dans l'agent | une fois : ajouter l'URL du service et se connecter |
| **À l'usage** | rien | rien (renouvellement automatique du jeton) |
| **Qui délivre la preuve** | Mircapgen (l'administrateur crée la clé) | un fournisseur d'identité externe |
| **Usage visé** | services internes, agents auto-hébergés, applications maison | services internes ou grand public, assistants grand public |
| **Inscription d'utilisateurs** | créés par l'administrateur | création manuelle ou automatique (§8.8) |
| **Prérequis** | aucun | un fournisseur d'identité compatible |

Le framework doit permettre d'ajouter d'autres méthodes plus tard sans modifier le cœur.

Les deux méthodes reposent sur le même principe côté serveur : Mircapgen reçoit un identifiant d'accès dans la requête, le vérifie, en déduit l'utilisateur, puis applique les règles communes (§8.7, §8.8). Cette uniformité repose sur le mécanisme de vérification de jeton du SDK MCP (§7, à valider par un prototype).

## 8.5 Méthode 1 : clé personnelle

Une clé est un secret lié à **un** utilisateur d'agent.

**Cycle de vie**

- créée par l'administrateur, en ligne de commande dès la 0.1 (§18.6) puis depuis l'interface d'administration (§10) ; un écran de création en libre-service pourra être fourni par le développeur ;
- affichée **une seule fois**, au moment de la création ;
- Mircapgen ne conserve que son **empreinte** (hachage), jamais la clé en clair ;
- possède un préfixe identifiable (pour la retrouver dans les logs sans la révéler) ;
- révocable à tout moment ; expiration facultative ; rotation possible en créant une nouvelle clé avant de révoquer l'ancienne ;
- horodatage de dernier usage conservé.

**Bonnes pratiques prévues**

- une clé par utilisateur **et par agent** (étiquette libre, par exemple « Hermes du bureau »), pour révoquer un agent sans toucher aux autres ;
- transmission uniquement dans un en-tête HTTP (`Authorization: Bearer …`), jamais dans l'URL ;
- chaque clé peut avoir son propre plafond de permissions (§8.7).

**Protection anti-fraude**

- le modèle de langage ne voit pas la clé (elle est dans la configuration du client) ;
- une clé volée permet d'usurper son utilisateur : c'est la limite de cette méthode. Elle est réduite par le plafond, l'expiration, la révocation et l'audit du dernier usage ;
- comparaison de clés à temps constant et limitation du nombre d'essais.

**Limite de compatibilité**

D'après la documentation actuelle de Claude, la clé statique d'un connecteur est partagée par toute l'organisation et ne doit pas servir à identifier un utilisateur. Cette méthode est donc pensée pour les agents où chaque utilisateur configure sa propre clé (agents auto-hébergés, applications, Claude Code…). Pour les assistants grand public, c'est OAuth qui identifie l'utilisateur.

## 8.6 Méthode 2 : OAuth 2.1

Mircapgen se comporte comme un **serveur de ressources OAuth** standard du protocole MCP. Il **vérifie** des jetons ; il n'en émet pas et ne devient pas un fournisseur d'identité (§30). La connexion des utilisateurs est déléguée à un **fournisseur d'identité externe** (par exemple Keycloak, Auth0, Microsoft Entra ou Google).

**Déroulement pour l'utilisateur**

1. Il ajoute l'URL du service dans son agent.
2. À la première connexion, une page de connexion du fournisseur d'identité s'ouvre dans son navigateur.
3. Il se connecte et autorise l'accès.
4. L'agent reçoit un jeton et le renouvelle seul ensuite. L'utilisateur n'a plus rien à faire.

**Ce que fait Mircapgen**

- répondre `401` avec un en-tête `WWW-Authenticate` pointant vers les métadonnées de ressource, quand un appel protégé arrive sans jeton valide ;
- publier les métadonnées de ressource protégée (RFC 9728) qui désignent le fournisseur d'identité ;
- vérifier chaque jeton :

| Revendication | Vérification |
|---|---|
| signature | clés publiques du fournisseur d'identité (JWKS), algorithme **fixé par la configuration**, jamais lu dans le jeton |
| `iss` | doit figurer dans la liste des émetteurs de confiance |
| `aud` | doit être **ce microservice** : un jeton émis pour un autre service est refusé, et un jeton reçu n'est jamais retransmis à un autre service |
| `exp` / `iat` | jeton expiré ou émis dans le futur refusé ; durée de vie maximale imposée |
| `sub` | identifie l'utilisateur ; doit correspondre à un utilisateur d'agent connu (ou créé si le provisioning est activé) |
| `client_id` / `azp` | identifie le client MCP (Claude, ChatGPT…) ; sert au plafond de permissions |

**Prérequis côté fournisseur d'identité**

- PKCE avec `S256` ;
- enregistrement automatique des clients (DCR, RFC 7591) ou documents de métadonnées de client (CIMD), afin que des assistants génériques puissent se connecter sans enregistrement manuel ;
- métadonnées de découverte (RFC 8414 ou OpenID Connect) joignables depuis Internet ;
- renouvellement de jeton (refresh) pour que l'utilisateur ne se reconnecte pas.

**Configuration**

```yaml
identity:
  oauth:
    issuers:
      - name: keycloak-main
        issuer_url: https://id.example.com/realms/main
        algorithm: RS256
    audience: crm-service         # doit correspondre à l'URL/identifiant de ce service
    max_lifetime: 3600            # secondes
```

**Droits**

- les groupes et permissions de l'utilisateur viennent de **Mircapgen** (§8.8 et §9), pas du jeton : le fournisseur d'identité prouve *qui* est l'utilisateur, pas *ce qu'il peut faire* ;
- un lien optionnel entre les scopes OAuth et le plafond de permissions est envisagé (§34).

**Révocation**

- pas de liste de révocation propre à Mircapgen dans un premier temps : la protection repose sur des jetons de courte durée et sur la révocation côté fournisseur d'identité ;
- un utilisateur désactivé dans Mircapgen est refusé même avec un jeton valide.

**Service grand public**

Avec un fournisseur d'identité qui permet l'inscription libre et le provisioning automatique activé (§8.8), des utilisateurs inconnus peuvent s'inscrire seuls et recevoir uniquement des groupes restreints. Le développeur choisit ainsi entre service interne (utilisateurs créés à la main) et service ouvert.

## 8.7 Plafond de permissions

Chaque identifiant d'accès peut se voir attribuer un **plafond de permissions** : l'ensemble maximal de permissions qu'il peut exercer, quel que soit l'utilisateur.

```yaml
clients:
  claude-web:                      # client OAuth identifié par son client_id
    permission_ceiling:
      - customer.read
      - invoice.read
```

Pour une clé personnelle, le plafond se définit à la création de la clé.

Règles :

- les droits effectifs d'un appel sont l'**intersection** des permissions de l'utilisateur et du plafond ;
- le plafond limite les dégâts si une clé fuite ou si un client est compromis ;
- il accepte les jokers (`customer.*`) ;
- il s'applique aussi à la visibilité : les Features hors plafond ne sont pas présentées (§9.1) ;
- sans plafond défini, aucun plafonnement ; `mircapgen check` le signale ;
- les Features publiques (§8.9) ne sont pas concernées.

## 8.8 Cycle de vie des utilisateurs d'agents

Par défaut, les utilisateurs d'agents sont créés et rattachés à des groupes par l'administrateur, en ligne de commande dès la 0.1 (§18.6) puis via l'interface d'administration (§10). Un identifiant d'accès dont l'utilisateur est inconnu est refusé.

### Création automatique (provisioning)

Pour la méthode OAuth uniquement, la création automatique d'un utilisateur à sa première connexion est **une option activable ou désactivable** par le développeur :

```yaml
identity:
  auto_provision: false      # désactivée par défaut
  default_groups: []         # groupes attribués à un utilisateur créé automatiquement
```

Règles :

- désactivée par défaut ;
- un utilisateur créé automatiquement reçoit uniquement les groupes indiqués dans `default_groups`, qui doivent rester restreints ;
- l'administrateur peut ensuite modifier ses groupes ou le désactiver ;
- les clés personnelles ne sont jamais créées automatiquement : elles sont émises pour un utilisateur existant ;
- la création est tracée dans les logs d'audit.

### Règles générales d'identification

- une requête sans identifiant d'accès valide est refusée (deny by default), sauf Feature explicitement publique (§8.9) ;
- un utilisateur inconnu ou désactivé est refusé ;
- **le modèle de langage n'est jamais une source d'identité** : l'identité n'est ni un paramètre de Feature, ni une information que l'IA renseigne à partir du Helper ;
- les Features accèdent à l'utilisateur par un objet de contexte fourni par le framework (par exemple `ctx.user`), sans gérer elles-mêmes l'identité ;
- l'audit enregistre l'utilisateur, le client, la méthode utilisée (`key` ou `oauth`) et l'identifiant de l'identifiant d'accès (préfixe de clé ou `jti`), **jamais le secret ni le jeton lui-même**.

## 8.9 Features publiques

Le développeur peut déclarer une Feature **publique**, c'est-à-dire appelable sans utilisateur identifié. C'est un choix explicite, Feature par Feature.

```python
@mircap.feature(
    name="system.status",
    description="Indique l'état du service",
    public=True
)
async def system_status():
    ...
```

Règles :

- une Feature est privée par défaut ;
- une Feature publique n'a pas besoin de permission et est visible sans identification ;
- avant identification, un client ne voit que les Features publiques ; avec OAuth, l'appel à une Feature privée déclenche alors la connexion de l'utilisateur (`401`), ce qui permet d'utiliser les Features publiques immédiatement ;
- l'option `identity.require_credential: true` (désactivée par défaut) exige un identifiant d'accès valide pour toute connexion, y compris pour appeler les Features publiques ; elle convient aux services purement internes ;
- elle reste validée, journalisée et soumise aux middlewares comme les autres ;
- `mircapgen check` liste les Features publiques pour qu'elles soient relues.

---

# 9. Gestion des permissions et RBAC

Mircapgen doit intégrer un système de droits basé sur des groupes.

Les groupes et permissions s'appliquent aux **utilisateurs d'agents IA** (§8.1). Ils ne concernent ni les administrateurs de l'interface, ni les clients MCP.

Structure :

```text
Utilisateur d'agent
 │
 ├── Group
 │     ├── customer.read
 │     ├── customer.write
 │     └── invoice.read
 │
 └── Group
       └── admin.*
```

## 9.0 Définition des groupes

Les groupes de droits forment **une liste unique**, que le développeur renseigne dans le code.

```python
groups = [
    Group(name="reader", permissions=["customer.read", "invoice.read"]),
    Group(name="manager", permissions=["customer.*", "invoice.read"]),
]
```

Cette liste peut ensuite être **complétée par l'administrateur** si le développeur le souhaite : il suffit d'inclure dans un formulaire d'administration un champ dédié à la gestion des groupes (§11.1), par exemple :

```python
class AccessSettings(AdminForm):

    groups = GroupsField(
        label="Groupes de droits",
        assignable_permissions=["customer.read", "invoice.read"]
    )
```

Le formulaire généré permet alors à l'administrateur d'ajouter, modifier et supprimer des groupes, sans toucher au code. Si le développeur n'inclut pas ce champ, la liste reste figée telle que définie dans le code.

### Limiter les droits que l'administrateur peut attribuer

Par défaut, un administrateur pourrait composer un groupe avec n'importe quelle permission existante, ce qui lui donnerait de fait le pouvoir de s'accorder des droits sensibles (suppression, paiement…). Le développeur peut donc **restreindre depuis le code** les permissions attribuables via le champ :

- `assignable_permissions` : liste des seules permissions que l'administrateur peut ajouter à un groupe ;
- `forbidden_permissions` : permissions que l'administrateur ne peut jamais attribuer, quelles que soient les autres règles (par exemple les permissions des Features à risque élevé, §25).

Les permissions hors périmètre n'apparaissent pas dans le formulaire et sont refusées côté serveur si elles sont envoyées quand même. Seul le code du développeur peut attribuer ces permissions, via les groupes qu'il déclare.

Règles :

- les **permissions** sont toujours déclarées dans le code, par les Features qui les exigent ; les groupes ne font que les assembler ;
- un groupe ajouté par l'administrateur ne peut référencer que des permissions existantes **et** autorisées par le développeur (voir ci-dessus) ;
- les groupes déclarés dans le code ne sont ni supprimables ni modifiables depuis l'interface ; seuls les groupes ajoutés par l'administrateur le sont ;
- un nom de groupe est unique dans la liste : l'administrateur ne peut pas créer un groupe portant le nom d'un groupe du code ;
- la liste complète (code + ajouts de l'administrateur) est celle que voient le RBAC, le filtrage de visibilité (§9.1) et les fixtures de test.

Le stockage des groupes ajoutés par l'administrateur dépend de la persistance retenue (§34).

Les permissions doivent pouvoir être associées directement aux Features.

Exemple :

```python
@mircap.feature(
    name="customer.delete",
    permission="customer.delete"
)
async def delete_customer(...):
    ...
```

Mircapgen prend alors en charge automatiquement :

```text
Request
   ↓
Identifiant d'accès (clé ou jeton OAuth)
   ↓
Utilisateur d'agent
   ↓
Groups
   ↓
Permissions
   ↓
Feature access
   ↓
Business logic
```

## 9.1 Permission = accès + visibilité

Une fonctionnalité non autorisée ne devrait idéalement pas seulement échouer lors de son appel.

Elle peut également être cachée lors de la découverte des capacités.

Exemple :

```text
Utilisateur du groupe "manager"

customer.search
customer.create
customer.update
customer.delete

Utilisateur du groupe "reader"

customer.search
```

La liste des Features visibles dépend de l'**utilisateur de l'agent** (et du plafond de permissions de son identifiant d'accès, §8.7), pas du client MCP en lui-même : deux utilisateurs passant par le même agent voient des listes différentes.

Cela évite de présenter inutilement à un agent des outils qu'il ne pourra jamais utiliser.

## 9.2 Déclaration et format des permissions

**Déclaration.** Une permission se déclare dans le décorateur de la Feature qui l'exige. L'ensemble des permissions du service est celui de ces déclarations : il n'y a pas de registre séparé à tenir à la main.

**Paramétrage par formulaire.** Si le développeur le souhaite, la permission exigée par une Feature peut être modifiée par l'administrateur depuis un formulaire lié à cette Feature, grâce à un champ dédié (`PermissionField`, nom indicatif, voir §11.1) :

```python
class CustomerDeleteSettings(AdminForm):

    permission = PermissionField(
        feature="customer.delete",
        assignable_permissions=["customer.write", "customer.delete"]
    )
```

Règles :

- la valeur du décorateur est la valeur par défaut ; la valeur choisie dans le formulaire est conservée par le `Store` (§12.2) et prime sur elle ;
- le formulaire ne propose que les permissions autorisées par le développeur (`assignable_permissions`, `forbidden_permissions`), comme pour les groupes (§9.0), et le serveur refuse les autres ;
- le formulaire modifie la permission exigée mais ne peut pas rendre une Feature publique ;
- chaque modification est journalisée dans le journal d'audit (§15) ;
- la permission effective (décorateur ou formulaire) est celle qu'utilisent le RBAC, la visibilité (§9.1), `mircapgen check` et `mircapgen inspect`.

**Format.**

- minuscules, segments séparés par des points, de la forme `domaine.verbe` (`customer.read`) ; lettres, chiffres et `_` autorisés ;
- joker `*` uniquement en dernier segment, dans les groupes et les plafonds : `customer.*` couvre toute permission commençant par `customer.` ;
- un `*` seul est réservé aux groupes déclarés dans le code et n'est pas attribuable par `GroupsField` (§9.0) ;
- une seule permission par Feature dans la 0.1 ;
- le nom d'une Feature et la permission qu'elle exige sont deux notions distinctes : la Feature `customer.search` peut exiger la permission `customer.read`.

**Détection des fautes de frappe.** Une permission mal orthographiée rendrait une Feature inaccessible sans erreur visible. `mircapgen check` signale donc :

- en **erreur** : un groupe ou un plafond qui référence une permission qu'aucune Feature n'exige ;
- en **avertissement** : une permission exigée qu'aucun groupe n'accorde.

---

# 10. Interface d'administration

Mircapgen doit fournir une interface d'administration prête à l'emploi, réservée aux **administrateurs** (§8.1). Elle est prévue pour la version 0.3 (§29) ; la 0.1 est administrée en ligne de commande (§18.6).

Elle permet notamment de gérer les utilisateurs d'agents, leurs groupes et permissions, les clés personnelles, les plafonds de permissions par client, la configuration et les secrets, et de consulter les logs.

Routes standards potentielles (`/admin/users` désigne les utilisateurs d'agents, pas les administrateurs) :

```text
/login

/admin
/admin/users
/admin/groups
/admin/permissions
/admin/config
/admin/logs
```

Le développeur doit pouvoir ajouter ses propres écrans et formulaires.

---

# 11. Formulaires déclaratifs

L'un des objectifs est d'éviter au développeur de construire manuellement chaque formulaire HTML.

Exemple conceptuel :

```python
class OpenAIConfig(AdminForm):

    api_key = SecretField(
        label="API key",
        required=True
    )

    model = SelectField(
        label="Model",
        choices=[
            "model-a",
            "model-b"
        ]
    )

    timeout = IntegerField(
        label="Timeout",
        default=30
    )
```

Mircapgen génère automatiquement :

- le formulaire ;
- la validation ;
- l'affichage ;
- le stockage ;
- les messages d'erreur.

## 11.1 Types de champs envisagés

```text
TextField
TextAreaField
IntegerField
FloatField
BooleanField
SelectField
MultiSelectField
SecretField
URLField
JSONField
FileField
GroupsField
PermissionField
```

`GroupsField` est un champ spécialisé permettant à l'administrateur de compléter la liste des groupes de droits (§9.0). `PermissionField` permet de paramétrer la permission exigée par une Feature (§9.2). Leurs noms sont indicatifs.

---

# 12. Configuration

Mircapgen doit proposer un système standard de configuration.

Exemple :

```python
class Config(MircapConfig):

    api_url: str
    api_key: Secret
    timeout: int = 30
```

Le framework doit permettre d'accéder simplement aux valeurs :

```python
config.api_url
config.timeout
```

## 12.1 Sources de configuration

Plusieurs sources peuvent être supportées :

```text
environment variables
configuration file
database
admin interface
secret backend
```

Un système de priorité devra être défini.

## 12.2 Persistance des données du framework

Mircapgen conserve ses propres données (utilisateurs d'agents et leurs groupes, clés personnelles, identités OAuth, puis groupes ajoutés par l'administrateur et paramètres modifiés depuis l'interface) dans une base de données. Les données métier du développeur sont **distinctes** : Mircapgen n'y accède jamais.

**Contrat de stockage.** Le framework ne connaît que l'interface `Store`. Implémentations :

- `SqlStore` : implémentation par défaut, fondée sur SQLAlchemy Core (sans ORM), qui couvre SQLite et les bases serveur ;
- `MemoryStore` : pour les tests, utilisée par les fixtures (§17) ;
- implémentation personnalisée fournie par le développeur (`MircapApp(store=...)`).

Une suite de tests de conformité commune garantit que toutes les implémentations se comportent de la même façon.

Pour le reste du framework, l'accès au `Store` est asynchrone. En interne, `SqlStore` exécute SQLAlchemy de façon synchrone dans des threads : le développeur n'a aucun choix à faire à ce sujet.

**Choix de la base.** Par configuration, SQLite étant le choix par défaut :

```yaml
database:
  url: sqlite:///data/mircap.db
```

ou une base serveur :

```yaml
database:
  url: postgresql://mircap@db.example.com:5432/mircap
```

Le mot de passe est un `Secret` fourni par variable d'environnement ou par le backend de secrets (§13), jamais écrit en clair dans le fichier. Mircapgen se connecte à une base déjà fournie par le développeur ou son hébergeur ; il n'installe ni ne gère jamais de serveur de base. Le pilote d'une base serveur est un extra optionnel (par exemple `mircapgen[postgres]`).

**Tables.** Toutes les tables du framework sont préfixées `mircap_`, afin de cohabiter avec celles du développeur dans une même base.

**Migrations.** Sur le modèle de Django ou de Sequelize :

- fichiers de migration versionnés, livrés avec le paquet Mircapgen (Alembic) ; le développeur n'en écrit pas pour les tables du framework ;
- table de suivi des migrations appliquées ;
- application explicite par `mircapgen db upgrade`, état par `mircapgen db status` (§18.7) ;
- migrations **en avant uniquement** : pas de retour arrière, la sauvegarde tient lieu de filet de sécurité ;
- sauvegarde automatique du fichier SQLite avant toute migration ; pour une base serveur, les sauvegardes restent à la charge du développeur ou de son hébergeur ;
- au démarrage, si des migrations sont en attente, le service **refuse de démarrer** et indique la commande à lancer ;
- `mircapgen new` et `mircapgen dev` appliquent les migrations automatiquement ;
- l'option `database.auto_migrate: true` permet de les appliquer au démarrage, avec un verrou pour éviter que deux instances migrent en même temps ;
- mettre à jour Mircapgen vers une version qui modifie le schéma se fait comme pour Django : installer la nouvelle version, puis `mircapgen db upgrade`.

**Limites de la 0.1.** SQLite ne convient qu'à une seule instance du service : plusieurs instances imposent une base serveur. Les tables propres au développeur ne sont pas gérées par le cœur (séparation métier / infrastructure, §2.1) : il utilise l'outil de son choix, et une extension (par exemple `mircapgen-sqlalchemy`, §26) pourra les prendre en charge plus tard.

---

# 13. Gestion des secrets

Mircapgen doit intégrer une notion native de secret.

Un secret ne doit jamais apparaître accidentellement dans :

- les logs ;
- les traces ;
- les réponses MCP ;
- les erreurs ;
- les prompts ;
- l'interface HTML ;
- les exports de configuration.

Exemple :

```python
api_key: Secret
```

Backend de secrets envisageables :

```text
environment variables
encrypted database
Docker secrets
Kubernetes secrets
Vault
external secret manager
```

Le backend doit être abstrait pour permettre plusieurs implémentations.

---

# 14. Middleware et Hooks

Mircapgen doit permettre l'exécution de logique avant et après l'appel d'une Feature.

Pipeline conceptuel :

```text
MCP Request
   ↓
Vérification de l'identifiant d'accès
   ↓
Résolution de l'utilisateur
   ↓
Autorisation (droits ∩ plafond)
   ↓
Validation de l'entrée
   ↓
Middleware Before
   ↓
Feature
   ↓
Middleware After
   ↓
Validation de la sortie
   ↓
Sérialisation
   ↓
Audit
   ↓
MCP Response
```

Le cycle complet, avec la découverte des Features, est détaillé au §27.

Exemples de hooks :

```python
@before_feature
async def before_feature_call(...):
    ...

@after_feature
async def after_feature_call(...):
    ...

@on_feature_error
async def feature_error(...):
    ...
```

Cas d'usage :

- audit ;
- métriques ;
- limitation de débit ;
- gestion de transactions ;
- validation avancée ;
- journalisation ;
- instrumentation.

---

# 15. Logs

Mircapgen doit fournir un système de logs homogène.

Chaque appel de Feature peut produire une entrée structurée.

Exemple :

```text
timestamp: 2026-09-29T09:30:00
request_id: 9912c...
client: crm-assistant
user: user-42
auth_method: key
credential: mk_ab12
feature: customer.search
duration_ms: 43
status: success
```

Les données sensibles doivent être filtrées automatiquement.

Le **journal d'audit** (qui a appelé quelle Feature, avec quel identifiant d'accès et avec quel résultat) est un flux distinct des logs techniques. Son stockage et sa protection contre la modification restent à définir (§34).

Les logs doivent idéalement être structurés afin de faciliter leur exploitation.

Exemple JSON :

```json
{
  "feature": "customer.search",
  "duration_ms": 43,
  "status": "success"
}
```

---

# 16. Observabilité

À terme, Mircapgen doit pouvoir exposer :

- métriques ;
- traces ;
- logs ;
- nombre d'appels par Feature ;
- erreurs par Feature ;
- latence ;
- statut du microservice.

Une intégration OpenTelemetry pourrait être ajoutée dans une version ultérieure.

---

# 17. Tests intégrés

Mircapgen doit s'appuyer sur `pytest` plutôt que créer un nouveau framework de tests.

Il peut cependant fournir des fixtures et helpers spécifiques.

Exemple :

```python
def test_search(mcp_client):

    result = mcp_client.call_tool(
        "customer.search",
        {"query": "Dupont"}
    )

    assert result.success
```

## 17.1 Helpers RBAC

```python
def test_reader_permissions(mcp_client):

    client = mcp_client.as_group("reader")

    assert client.can_call("customer.search")
    assert not client.can_call("customer.delete")
```

`as_group` simule un utilisateur d'agent appartenant au groupe donné. Un helper `as_user("user-42")` permet de tester une identité précise, et les cas de refus (identité absente, inconnue ou désactivée) doivent aussi être testables.

## 17.2 Tests automatiques du framework

Mircapgen pourrait également fournir des validations automatiques :

```text
Feature sans description
Permission inexistante
Nom de Feature dupliqué
Instruction manquante
Configuration invalide
Secret exposé accidentellement
Schéma MCP invalide
```

---

# 18. CLI Mircapgen

Mircapgen doit fournir une CLI afin d'accélérer le développement.

## 18.1 Création de projet

```bash
mircapgen new crm-service
```

Génère automatiquement la structure de base.

## 18.2 Création d'une Feature

```bash
mircapgen create feature customer.search
```

Peut générer :

```text
app/features/customer/search.py
app/features/customer/tests/test_search.py
```

## 18.3 Lancement du serveur de développement

```bash
mircapgen dev
```

Fonctions possibles :

- MCP server ;
- admin UI (à partir de la 0.3) ;
- hot reload ;
- logs ;
- validation du projet.

## 18.4 Tests

```bash
mircapgen test
```

## 18.5 Inspection du projet

```bash
mircapgen inspect
```

Exemple de sortie :

```text
Service : CRM

Features

✓ customer.search
✓ customer.create
✓ customer.update
✓ customer.delete

Permissions

✓ customer.read
✓ customer.create
✓ customer.write
✓ customer.delete

Configuration

✓ DATABASE_URL
✓ API_URL
⚠ API_KEY missing
```

## 18.6 Gestion des utilisateurs et des clés

Dès la 0.1, les utilisateurs d'agents et leurs clés se gèrent en ligne de commande (les noms de commandes sont indicatifs) :

```bash
mircapgen user create alice --group reader
mircapgen user list
mircapgen user disable alice

mircapgen key create alice --label "Hermes du bureau" --expires 90d --ceiling customer.read
mircapgen key list alice
mircapgen key revoke mk_ab12
```

Règles :

- une clé n'est affichée qu'à sa création et n'est jamais relisible ensuite (§8.5) ;
- les groupes indiqués doivent exister dans le code (§9.0) ;
- chaque commande est journalisée dans le journal d'audit (§15).

## 18.7 Base de données

Les migrations du framework se gèrent comme celles de Django (les noms de commandes sont indicatifs) :

```bash
mircapgen db status     # migrations appliquées et en attente
mircapgen db upgrade    # applique les migrations en attente
mircapgen db history    # historique des migrations
```

Règles :

- `upgrade` peut être relancée sans risque : seules les migrations en attente sont appliquées ;
- avec SQLite, le fichier est sauvegardé avant chaque migration ;
- chaque migration appliquée est journalisée dans le journal d'audit (§15) ;
- aucun retour arrière n'est proposé (§12.2).

---

# 19. Structure proposée d'un projet

```text
my-mcp-service/
│
├── mircap.yaml
├── pyproject.toml
├── README.md
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── groups.py              # groupes de droits (§9.0)
│   ├── helper.yaml            # description et instructions globales (§5)
│   │
│   ├── features/
│   │   ├── customer/
│   │   │   ├── search.py
│   │   │   ├── create.py
│   │   │   ├── update.py
│   │   │   ├── delete.py
│   │   │   ├── instructions.md
│   │   │   └── tests/
│   │   │
│   │   └── invoice/
│   │       ├── search.py
│   │       ├── generate.py
│   │       ├── instructions.md
│   │       └── tests/
│   │
│   ├── admin/
│   │   ├── forms.py
│   │   └── pages.py
│   │
│   └── middleware/
│       └── audit.py
│
├── tests/
│   ├── integration/
│   └── security/
│
└── docker/
    └── Dockerfile
```

Cette structure doit rester personnalisable.

Les utilisateurs et les clés ne figurent pas dans l'arborescence : ils sont conservés par la couche de persistance (§34).

---

# 20. Fichier mircap.yaml

Le fichier `mircap.yaml` peut devenir le manifeste principal du microservice.

Exemple :

```yaml
service:
  name: crm-service
  version: 0.1.0
  description: CRM accessible aux agents IA

mcp:
  enabled: true
  transports:
    - stdio
    - http

admin:
  enabled: false         # interface d'administration : à partir de la 0.3

identity:
  methods: [key]         # key ; oauth à partir de la 0.2
  auto_provision: false
  default_groups: []
  require_credential: false

database:
  url: sqlite:///data/mircap.db   # ou une base serveur (§12.2)
  auto_migrate: false

features:
  auto_discovery: true

logging:
  format: json
```

L'identification et le RBAC ne sont pas des options du manifeste : ils sont toujours actifs (§24). Un éventuel mode de développement sans authentification, s'il existe, devra être explicite et signalé par `mircapgen check` (§34).

---

# 21. Validation automatique du projet

Mircapgen doit pouvoir analyser la cohérence d'un projet.

Commande :

```bash
mircapgen check
```

Contrôles possibles :

```text
✓ manifest valid
✓ 12 Features found
✓ 8 permissions found
✓ all permissions referenced exist
✓ all Features have descriptions
✓ all tests passed
⚠ 2 Features without instructions
⚠ unused permission: invoice.admin
⚠ 1 public Feature: system.status
⚠ Feature with both permission and public=True: customer.delete (permission applied)
⚠ client without permission ceiling: claude-web
⚠ key never used for 90 days: alice / Hermes du bureau
```

---

# 22. Génération de documentation

Mircapgen peut générer automatiquement une documentation à partir des Features.

Commande potentielle :

```bash
mircapgen docs
```

Documentation générée :

```text
service description
Features
permissions
parameters
outputs
agent instructions
configuration
```

Cette documentation pourrait servir :

- aux développeurs ;
- aux administrateurs ;
- aux agents IA ;
- aux équipes intégrant le microservice.

---

# 23. Erreurs standardisées

Le framework doit définir une hiérarchie d'erreurs standard.

Exemple :

```text
MircapError
├── AuthenticationError
├── AuthorizationError
├── ValidationError
├── ConfigurationError
├── FeatureError
└── InternalError
```

L'objectif est d'éviter de transmettre directement des exceptions Python brutes aux agents.

---

# 24. Sécurité par défaut

Mircapgen doit adopter une philosophie de sécurité par défaut.

Principes :

```text
Deny by default
Least privilege
Secrets masked
Explicit permissions
Validated inputs
Controlled outputs
Structured audit logs
```

Une Feature exposée via MCP doit déclarer `permission` ou `public=True`. Sinon elle **n'est pas accessible** : elle n'est ni listée ni appelable, et une erreur est enregistrée dans les logs au démarrage. Le service continue de fonctionner pour les autres Features, et `mircapgen check` signale la même situation comme une erreur.

Si `permission` et `public=True` sont déclarés ensemble, un avertissement est enregistré dans les logs et la règle **la plus restrictive** s'applique : la permission est exigée et `public` est ignoré. Une erreur de déclaration rend ainsi une Feature plus fermée, jamais plus ouverte. `mircapgen check` le signale.

---

# 25. Features sensibles

Certaines fonctionnalités présentent davantage de risques.

Exemples :

```text
suppression
paiement
modification massive
exécution de code
arrêt d'un service
accès administrateur
```

Mircapgen pourrait permettre :

```python
@mircap.feature(
    name="server.restart",
    permission="server.restart",
    risk="high"
)
```

Cette information peut être utilisée par :

- le helper IA ;
- les logs ;
- l'admin ;
- des politiques de confirmation ;
- les tests de sécurité.

---

# 26. Plugins / extensions

L'architecture doit permettre d'ajouter des extensions sans modifier Mircapgen Core.

Exemples :

```text
mircapgen-sqlalchemy
mircapgen-redis
mircapgen-vault
mircapgen-otel
mircapgen-keycloak
mircapgen-kubernetes
```

Le système de plugins pourra être défini après stabilisation du noyau.

---

# 27. Cycle de vie d'une requête

Exemple de cycle complet :

```text
Agent
  │
  ▼
MCP Transport
  │
  ▼
Vérification de l'identifiant d'accès (clé ou jeton OAuth)
  │
  ▼
Résolution de l'utilisateur
  │
  ▼
Feature discovery
  │
  ▼
Authorization
  │
  ▼
Input validation
  │
  ▼
Before middleware
  │
  ▼
Business Feature
  │
  ▼
After middleware
  │
  ▼
Output validation
  │
  ▼
Serialization
  │
  ▼
Audit log
  │
  ▼
Agent
```

---

# 28. Scope du MVP

La première version ne doit pas chercher à résoudre immédiatement tous les problèmes possibles.

Le MVP est la version **0.1** : un framework permettant de construire un microservice MCP **sécurisé**, administré en **ligne de commande et par fichiers**, sans interface web. Il est précédé d'un prototype **0.0** qui valide l'architecture.

## 28.1 Principes de découpage

- **Tranche verticale d'abord** : une Feature complète, de bout en bout, avant d'élargir le périmètre ;
- **la sécurité est dans le cœur** dès la première version (identification, autorisation, plafond, masquage des secrets) et n'est jamais reportée ;
- **pas d'interface web avant que le cœur soit stable** : la CLI suffit pour créer des utilisateurs et des clés ;
- **une méthode d'identification à la fois** : les clés personnelles (simples, sans dépendance externe) avant OAuth ;
- **ce qui est repoussé reste prévu dans l'architecture** : les points d'extension (identification, secrets, persistance) sont des interfaces dès le départ, même si une seule implémentation existe.

## 28.2 Mircapgen 0.0 — Prototype (tranche verticale)

**Objectif** : valider l'architecture et lever les incertitudes techniques avant de construire le reste. Le code peut être partiellement jeté.

Contenu :

- décorateur `@feature` (nom, description, permission, public) ;
- exposition d'une Feature en tool MCP via le SDK officiel, derrière l'adaptateur `mcp/` ;
- identification par clé personnelle, avec utilisateurs et clés lus dans un fichier de configuration ;
- groupes déclarés dans le code ;
- autorisation par permission, avec plafond de permissions (intersection) ;
- liste des Features filtrée selon l'utilisateur ;
- accès à l'utilisateur dans la Feature (`ctx.user`) ;
- erreurs `MircapError` et logs JSON minimaux ;
- client de test en mémoire avec `as_user` ;
- un exemple minimal dans `examples/`.

**Critères de sortie** :

- deux utilisateurs ayant des groupes différents voient des listes de Features différentes ;
- un appel sans la permission requise est refusé sans exécuter la Feature ;
- l'utilisateur est identifié dès la liste des tools, pas seulement à l'appel (§34, question 16) ;
- un client MCP réel (par exemple Claude Code ou Hermes) se connecte avec une clé et appelle une Feature.

**Décisions nécessaires avant de commencer** : version minimale de Python, outil de packaging, outils de lint et de typage.

## 28.3 Mircapgen 0.1 — MVP

**Objectif** : permettre de construire un microservice MCP sécurisé avec un minimum de code, administré par CLI.

Contenu :

**Features et agent**
- déclaration de Features avec toutes leurs métadonnées (label, description, instructions, constraints, permission, tags, version, `risk`, `public`) ;
- validation des entrées et des sorties, génération des schémas ;
- Helper global, instructions par Feature (`instructions.md`), découverte automatique ;
- erreurs standardisées (`MircapError`).

**Identité et droits**
- utilisateurs d'agents persistés, groupes déclarés dans le code ;
- clés personnelles complètes : hachage, révocation, expiration facultative, plafond propre, dernier usage ;
- RBAC, plafond de permissions, filtrage de la visibilité, Features publiques ;
- gestion par CLI (création d'utilisateurs, création et révocation de clés).

**Configuration et secrets**
- `MircapConfig` (variables d'environnement et fichier) et manifeste `mircap.yaml` ;
- type `Secret` masqué partout (logs, erreurs, réponses, exports), backend par variables d'environnement.

**Exploitation**
- hooks de base `before`, `after`, `on_error` ;
- logs structurés et journal d'audit avec filtrage des données sensibles.

**Développement**
- intégration `pytest` : `mcp_client`, `as_user`, `as_group`, `can_call`, tests de sécurité ;
- CLI : `new`, `create feature`, `dev`, `test`, `inspect`, `check`, `user`, `key` ;
- Dockerfile standard.

**Persistance** : contrat `Store`, `SqlStore` (SQLite par défaut, base serveur au choix du développeur par configuration), `MemoryStore` pour les tests, et migrations automatisables (§12.2).

**Critères de sortie** :

- un développeur crée un service avec `mircapgen new`, ajoute des Features, crée des utilisateurs et des clés en CLI, et lance les tests ;
- `mircapgen check` détecte : Feature sans description, permission inexistante, nom dupliqué, client sans plafond, Feature publique ;
- des tests prouvent qu'un `Secret` ne fuit dans aucun log, message d'erreur ni réponse MCP ;
- le service fonctionne avec au moins un client MCP réel.

**Décisions nécessaires avant de commencer** : chargement des instructions du Helper (question 10), format des clés (question 19).

## 28.4 Repoussé après le MVP

| Fonctionnalité | Version | Raison |
|---|---|---|
| OAuth 2.1 et fournisseur d'identité externe | 0.2 | nécessite un fournisseur d'identité et des tests avec les clients réels |
| Création automatique d'utilisateurs | 0.2 | dépend d'OAuth |
| Interface d'administration web | 0.3 | plus gros chantier, la CLI suffit pour commencer |
| Formulaires déclaratifs, `GroupsField` | 0.3 | dépendent de l'interface d'administration |
| Authentification de l'administrateur (mot de passe, sessions) | 0.3 | dépend de l'interface d'administration |
| Resources et prompts MCP | 0.4 | hors du cœur « Features → tools » |
| Système de plugins, secret managers (Vault…) | 0.4 | à définir après stabilisation du noyau |
| Génération de documentation (`mircapgen docs`) | 0.4 | le Helper couvre le besoin des agents en 0.1 |
| Observabilité (métriques, traces, OpenTelemetry) | 0.5 | les logs structurés suffisent au début |

---

# 29. Roadmap indicative

## 0.0 — Prototype

```text
Feature → tool MCP
Clé personnelle
Permission + plafond
Filtrage par utilisateur
Client de test as_user
```

## 0.1 — Core (MVP)

```text
Features complètes
Helper
Utilisateurs / groupes (code) / RBAC
Clés personnelles
Config / Secrets
Logs / audit
Tests pytest
CLI
Dockerfile
```

## 0.2 — OAuth et clients grand public

```text
OAuth 2.1 (serveur de ressources)
Fournisseur d'identité de référence
Création automatique d'utilisateurs
Scopes ↔ plafond de permissions
Tests de compatibilité : Claude, ChatGPT, Hermes, OpenClaw
```

## 0.3 — Administration web

```text
Authentification de l'administrateur
Interface d'administration
Formulaires déclaratifs
GroupsField / permissions attribuables
Clés en libre-service (optionnel)
```

## 0.4 — MCP avancé et extensibilité

```text
Resources
Prompts
Middleware avancé
Lifecycle hooks
Plugin system
Secret managers / Vault
Génération de documentation
```

## 0.5 — Observabilité

```text
Metrics
Tracing
OpenTelemetry
Dashboards
```

## 1.0 — Stabilisation

```text
Stable API
Stable plugin API
Documentation complète
Migration system
Backward compatibility policy
Production hardening
```

## Choix d'ordre

OAuth (0.2) est placé **avant** l'administration web (0.3) parce qu'il ouvre le service aux assistants grand public (Claude, ChatGPT) et qu'il est critique pour la sécurité, alors que la CLI couvre déjà l'administration. L'ordre inverse reste possible si l'interface d'administration est jugée prioritaire.

---

# 30. Ce que Mircapgen ne doit pas devenir

Il est important de limiter le scope du projet.

Mircapgen ne doit pas chercher à devenir :

- un framework web généraliste ;
- un nouvel ORM ;
- un nouveau moteur de templates complet ;
- un système IAM complet ;
- un orchestrateur d'agents ;
- un moteur LLM ;
- un remplacement de Kubernetes ;
- un remplacement des SDK MCP existants.

Il doit rester spécialisé dans :

> la création de microservices MCP sécurisés, configurables et facilement compréhensibles par les agents IA.

---

# 31. Proposition de philosophie du framework

Mircapgen pourrait adopter les principes suivants.

### Convention over configuration

Les comportements standards fonctionnent sans configuration complexe.

### Secure by default

Les fonctionnalités exposées doivent être sécurisées par défaut.

### Business-first

Le développeur écrit principalement de la logique métier.

### Agent-aware

Chaque Feature est conçue pour être facilement comprise et utilisée par un agent IA.

### Explicit permissions

Les accès aux fonctionnalités sont déclarés explicitement.

### Extensible

Les fonctions avancées peuvent être ajoutées via plugins ou middleware.

### Testable

Tout composant important doit pouvoir être testé sans lancer une infrastructure complète.

---

# 32. Exemple complet minimal

Exemple conceptuel d'un petit service Mircapgen :

```python
from mircapgen import MircapApp, feature

app = MircapApp(
    name="crm-service"
)


@feature(
    name="customer.search",
    description="Recherche un client dans le CRM",
    permission="customer.read"
)
async def search_customer(query: str):

    return [
        {
            "id": 42,
            "name": "John Doe"
        }
    ]


@feature(
    name="customer.delete",
    description="Supprime un client",
    permission="customer.delete",
    risk="high"
)
async def delete_customer(customer_id: int):

    ...


app.run()
```

Le développeur ne code pas directement :

```text
MCP router
authentication
permission checks
logging
schemas
discovery
admin authentication
```

Ces éléments sont pris en charge par Mircapgen.

L'écriture exacte de l'API (`@mircap.feature`, `@feature` ou `@app.feature`) n'est pas encore figée : les exemples de ce document sont indicatifs (§34).

---

# 33. Critère de réussite du projet

Mircapgen est réussi si un développeur peut créer un microservice MCP sérieux en écrivant principalement :

```text
business logic
+ Features
+ instructions
+ configuration
+ tests
```

et non :

```text
MCP plumbing
authentication
RBAC
admin UI
configuration UI
logging
serialization
boilerplate
```

Le framework doit réduire fortement le boilerplate tout en gardant une architecture lisible, extensible et contrôlable.

---

# 34. Questions d'architecture restant à trancher

Les points suivants devront être discutés avant ou pendant le développement du prototype :

1. Quel framework web sous-jacent utiliser pour l'admin et les routes HTTP ?
2. Quel système de validation de données utiliser ?
3. Quel moteur de templates utiliser pour l'interface admin ?
4. Faut-il embarquer un ORM ou seulement définir une interface de persistance ? *Tranchée : interface `Store`, `SqlStore` fondé sur SQLAlchemy Core (sans ORM) (§12.2).*
5. Quel stockage par défaut utiliser pour utilisateurs, groupes et configuration ? *Tranchée : SQLite par défaut, base serveur au choix du développeur par configuration (§12.2).*
6. Comment gérer les migrations de base de données ? *Tranchée : Alembic, migrations livrées avec le paquet, commandes explicites `mircapgen db ...`, en avant uniquement (§12.2, §18.7).*
7. Comment déclarer précisément les permissions ? *Tranchée : dans le décorateur de la Feature, paramétrable par formulaire (§9.2).*
8. Les permissions doivent-elles être obligatoires sur toutes les Features MCP ? *Tranchée : `permission` ou `public=True` requis, sinon la Feature est inaccessible et une erreur est journalisée ; le cas où les deux sont déclarés fait l'objet de la question 34 (§24).*
9. Comment associer resources et prompts aux Features ?
10. Comment charger dynamiquement les instructions du Helper ?
11. Quels mécanismes de confirmation prévoir pour les Features sensibles ?
12. Jusqu'où doit aller l'interface admin déclarative ?
13. Quelle API publique doit être considérée stable à terme ?
14. Quel système de plugins adopter ?
15. Comment gérer le versioning d'un microservice Mircapgen ?
16. Valider par un prototype que le mécanisme de vérification de jeton du SDK MCP officiel (`TokenVerifier`) permet de traiter uniformément clés personnelles et jetons OAuth (§8.4), et que l'utilisateur identifié est disponible dès `tools/list` pour filtrer les Features (§9.1) ainsi que dans les Features (`ctx.user`). *Principe acquis : le modèle de langage n'est jamais source d'identité.*
17. Quel fournisseur d'identité de référence pour OAuth (§8.6) et faut-il prévoir plus tard un serveur d'autorisation intégré optionnel (plugin) pour les services sans fournisseur d'identité ? *Principe acquis : Mircapgen est serveur de ressources, pas fournisseur d'identité.*
18. Une Feature publique doit-elle être appelable sans aucun identifiant d'accès, ou le développeur peut-il exiger un identifiant valide pour toute connexion (§8.9) ? *Tranchée : Feature par Feature, avec l'option `identity.require_credential` pour exiger un identifiant valide partout (§8.9).*
19. Clés personnelles (§8.5) : format et préfixe, algorithme de hachage, expiration par défaut, création en libre-service, rotation, limitation des essais.
20. Où sont stockés les groupes ajoutés par l'administrateur via `GroupsField`, et comment sont-ils fusionnés avec la liste du code (§9.0) ? *Principe acquis : liste unique renseignée dans le code, complétable par l'administrateur si le développeur inclut le champ.*
21. Le provisioning automatique (§8.8) : comportement à définir quand l'utilisateur créé est désactivé ou supprimé ensuite. *Principe acquis : option activable pour OAuth, désactivée par défaut.*
22. Faut-il relier les scopes OAuth au plafond de permissions (§8.7) ? Attention : avec l'enregistrement dynamique de client (DCR), le `client_id` change à chaque connexion, donc un plafond par `client_id` ne fonctionne qu'avec CIMD ou un client préenregistré.
23. Compatibilité réelle : tester le flux OAuth et les clés avec Claude, ChatGPT, Hermes et OpenClaw avant de figer l'API (§8.4).
24. Journal d'audit : où est-il stocké et comment est-il protégé contre la modification (§15) ?
25. Écriture définitive de l'API publique : `@mircap.feature`, `@feature` ou `@app.feature` (§3, §32) ?
26. Identité en stdio : comment une clé est-elle fournie (variable d'environnement) et quel modèle de confiance appliquer (§8.5) ?
27. Sécurité du transport HTTP : refus ou avertissement sans HTTPS, validation de l'en-tête `Origin`, limitation des essais de clés (§8.5) ?
28. Autorisation au niveau des données : le RBAC s'arrête à la Feature. Comment documenter et outiller le filtrage par utilisateur dans les Features (`ctx.user`) ?
29. Comportement minimal de `risk` dans la 0.1, ou report à la 0.4 (§25, question 11) ?
30. Faut-il un mode de développement sans authentification, et comment le rendre explicite (§20) ?
31. Helper : branchement sur le champ `instructions` du protocole MCP, et variation selon l'utilisateur (§5, question 10) ?
32. Le développeur peut-il aussi versionner et appliquer les migrations de ses propres tables avec `mircapgen db` (plusieurs branches Alembic), ou cela reste-t-il hors du framework (§12.2) ? *Tranchée : hors du cœur ; une extension (§26) pourra s'en charger.*
33. Mode d'accès à la base : SQLAlchemy synchrone exécuté dans des threads, ou asynchrone avec des pilotes asynchrones (§12.2) ? *Tranchée : synchrone dans des threads, invisible pour le développeur.*
34. Une Feature déclarant à la fois `permission` et `public=True` : quelle règle de résolution, la plus permissive ou la plus restrictive (§24) ? *Tranchée : la plus restrictive (la permission est exigée, `public` est ignoré), avec avertissement.*
35. Le formulaire `PermissionField` peut-il rendre une Feature publique, ou seulement changer la permission exigée (§9.2) ? *Tranchée : seulement changer la permission.*

Ces décisions devront être prises progressivement afin d'éviter de figer prématurément une architecture trop complexe.

---

# 35. Résumé

Mircapgen repose sur cinq concepts principaux :

```text
Feature
Helper
Security / RBAC
Admin déclaratif
Infrastructure automatique
```

Le développeur crée des **Features métier**.

Mircapgen transforme ces Features en capacités MCP sécurisées et documentées.

L'agent IA découvre uniquement les capacités pertinentes auxquelles l'utilisateur qu'il représente a accès.

L'administrateur, distinct des utilisateurs d'agents, configure le microservice via une interface commune.

Le framework gère automatiquement l'essentiel du code répétitif nécessaire autour d'un microservice MCP.
