# AGENT.md — Directives pour agents IA

> Fichier universel pour le projet Mircapgen (framework Python de microservices MCP pour agents IA).
> Complété par `CONVENTIONS.md` (stack et règles) et `DECISIONS.md` (décisions techniques).
> Référence fonctionnelle : `mircapgen_cahier_des_charges_v0.md` (à la racine du dépôt).

---

## 1. En début de session

Avant toute chose, lis dans cet ordre :
1. `AGENT.md` — ce fichier
2. `CONVENTIONS.md` — stack, structure, nommage, patterns de code
3. `CHANGELOG_AGENT.md` — état actuel du code, ce qui a déjà été fait
4. `DECISIONS.md` — pourquoi le code est comme il est, et les questions encore ouvertes
5. Le cahier des charges (`mircapgen_cahier_des_charges_v0.md`) pour la partie concernée par le ticket
6. Le ticket ou la demande courante

`CHANGELOG_AGENT.md` est ta mémoire de session — il te dit où en est le projet sans que tu aies à inférer depuis le code.

> Ces fichiers peuvent devenir volumineux. Lis d'abord l'« État global » et les dernières entrées du changelog, puis cherche (grep) dans `DECISIONS.md` les sujets liés au ticket plutôt que de tout charger.

---

## 2. Nature du projet

Mircapgen est un **framework** (bibliothèque + CLI), pas une application. Deux conséquences permanentes :

- **L'API publique est le produit.** Tout ce qui est importable par un développeur de microservice (`from mircapgen import ...`), les options des décorateurs, le format de `mircap.yaml`, les commandes CLI et les noms de permissions sont des interfaces publiques.
- **Le code du framework ne doit pas dépendre d'un microservice donné.** Les exemples (CRM, `customer.search`…) vivent dans `examples/` ou dans les tests, jamais dans le cœur.

Principes directeurs (cahier des charges §31) : convention over configuration · secure by default · business-first · agent-aware · permissions explicites · extensible · testable.

Anti-périmètre (cahier des charges §30) : pas de framework web généraliste, pas d'ORM, pas de moteur de templates complet, pas de système IAM complet, pas d'orchestrateur d'agents, pas de moteur LLM, pas de remplacement des SDK MCP existants. Si une demande y ressemble, signale-le.

---

## 3. Comportement général

### Avant de coder

- Lis `CONVENTIONS.md` avant toute implémentation.
- Si une information manque pour réaliser la tâche, **pose une question avant de coder** — ne fais pas d'hypothèse silencieuse.
- Le cahier des charges §34 liste des questions d'architecture **non tranchées** (framework web, validation, ORM, stockage, migrations, plugins…). Si le ticket dépend de l'une d'elles et qu'elle n'est pas résolue dans `DECISIONS.md`, **ne la tranche pas seul** : propose une recommandation argumentée et attends validation.
- Si la tâche modifie une interface publique (voir §2), **signale-le explicitement** et attends validation avant de continuer.

### Tickets en séquence — audit obligatoire avant implémentation

Les tickets sont livrés dans un ordre qui respecte les dépendances. Avant de coder, systématiquement :

**1. Identifier les fichiers concernés**
Liste les fichiers existants directement liés au ticket (modules du cœur, CLI, tests, manifeste, templates de projet...).

**2. Auditer l'état réel du code**
Pour chaque dépendance listée dans le ticket, vérifie ce qui est déjà implémenté :
- Ce qui existe et que tu dois utiliser tel quel
- Ce qui existe mais doit être étendu
- Ce qui n'existe pas encore et est dans ton périmètre

**3. Signaler les écarts**
Si l'état du code ne correspond pas à ce que le ticket suppose, **signale-le avant de coder** — ne comble pas silencieusement.

**4. Attends validation si un écart bloque**
Si une dépendance supposée présente est absente, pose la question.

> Résumé : **lis le code existant avant d'écrire une ligne, adapte-toi à ce qui est là.**

### Pendant le codage

- Travaille **un module à la fois**, dans les contraintes d'architecture définies.
- Ne refactore pas du code hors du périmètre du ticket en cours.
- N'ajoute pas de dépendance externe sans la signaler et justifier le choix (voir liste dans `CONVENTIONS.md`). Pour un framework, chaque dépendance est imposée à tous ses utilisateurs : préfère la bibliothèque standard, et rends optionnelles (extras) les dépendances non essentielles.
- Si tu détectes un problème dans un module adjacent, **signale-le dans un commentaire `TODO:`** plutôt que de le corriger silencieusement.

### En cas d'ambiguïté

- Priorité : sécurité par défaut > respect de l'architecture définie > conventions > simplicité de l'API pour le développeur final > performance > concision.
- Si deux approches sont valides, choisis la plus simple et documente le choix dans `DECISIONS.md`.

---

## 4. Standards de code

### Documentation obligatoire

Toute fonction, classe ou méthode publique doit avoir une docstring (style Google, en français) :

```python
def resolve_permissions(user: User) -> frozenset[str]:
    """Calcule l'ensemble des permissions effectives d'un utilisateur.

    Args:
        user: Utilisateur dont on résout les groupes.

    Returns:
        Les permissions accordées, jokers (`admin.*`) déjà développés.

    Raises:
        AuthorizationError: Si un groupe référence une permission inconnue.
    """
```

Le typage est obligatoire sur toute signature publique (les schémas MCP sont générés à partir des annotations).

### Commentaires de décision

Pour tout choix non-trivial :

```python
# CHOIX: [approche retenue] plutôt que [alternative écartée]
# RAISON: [justification courte]
```

### Gestion d'erreurs

- Ne jamais `except:` / `except Exception: pass` silencieux.
- Toute erreur est soit propagée, soit journalisée via le logger structuré du framework avec contexte.
- Le framework lève des exceptions de la hiérarchie `MircapError` (`AuthenticationError`, `AuthorizationError`, `ValidationError`, `ConfigurationError`, `FeatureError`, `InternalError`). **Une exception Python brute ne doit jamais atteindre un agent** (cahier des charges §23).
- Les erreurs attendues (validation, refus de permission) sont distinguées des erreurs système.

### Sécurité (non négociable)

- Deny by default : sans permission explicite, une Feature suit la politique du projet, et le défaut est le refus.
- Un `Secret` n'apparaît jamais dans les logs, traces, réponses MCP, erreurs, prompts, HTML ou exports de configuration. Tout nouveau chemin de sortie doit être couvert par un test de non-fuite.
- Un agent ne voit que les Features auxquelles son utilisateur a accès (permission = accès + visibilité).
- Aucune donnée d'entrée n'est de confiance : validation avant toute logique.

### Nommage

Suit les conventions définies dans `CONVENTIONS.md` — nommage descriptif > nommage court en cas de doute.

---

## 5. Tests

- Framework : `pytest` (pas de framework de tests maison — voir cahier des charges §17). Les fixtures/helpers fournis aux utilisateurs (`mcp_client`, `as_group`, `can_call`…) font partie de l'API publique.
- Chaque module livré inclut ses tests. Ils couvrent : le cas nominal, les cas limites, les erreurs attendues.
- Tout code touchant l'auth, le RBAC ou les secrets inclut des **tests de sécurité** (accès refusé, fonctionnalité masquée, secret non divulgué).
- Un composant important doit être testable sans infrastructure complète (base, serveur MCP réel…).
- Format des noms de test : `test_[fonction]__[contexte]__[résultat_attendu]`

```
test_resolve_permissions__wildcard_group__expands_all_matching_permissions
test_call_feature__missing_permission__raises_authorization_error
test_mask_secret__secret_in_error_message__value_is_redacted
```

---

## 6. Ce que l'agent NE doit PAS faire

| Interdit | Raison |
|----------|--------|
| Modifier l'API publique (décorateurs, manifeste, CLI, fixtures) sans validation | Casse tous les microservices bâtis dessus |
| Trancher seul une question ouverte du cahier des charges §34 | Décisions structurantes réservées à l'utilisateur |
| Refactorer hors du périmètre du ticket | Introduit du risque non planifié |
| Ajouter une dépendance externe sans signalement | Vérifier d'abord les dépendances approuvées dans `CONVENTIONS.md` |
| Supprimer des tests existants | Même s'ils échouent — les signaler à la place |
| Changer la structure de dossiers | Sauf si c'est explicitement dans le ticket |
| Laisser du code commenté | Utiliser `TODO:` avec contexte ou supprimer |
| Contourner le pipeline auth → autorisation → validation → feature | Le RBAC et l'audit ne doivent jamais être court-circuités |
| Faire dériver le framework vers l'anti-périmètre (§2) | Le scope est volontairement restreint |
| Mettre des exemples métier (CRM…) dans le cœur du framework | Le cœur reste générique |

---

## 7. Livraison d'un ticket

Checklist avant de considérer un ticket terminé :

- [ ] Code dans les contraintes d'architecture (séparation métier / infrastructure, pipeline de requête)
- [ ] Type hints et docstrings sur l'API publique
- [ ] Commentaires de décision sur les choix non-triviaux
- [ ] Tests (nominal + limites + erreurs, + sécurité si auth/RBAC/secrets)
- [ ] Lint, formatage et typage passent (commandes exactes dans `CONVENTIONS.md` une fois l'outillage posé)
- [ ] `pytest` passe
- [ ] Aucun secret ni donnée sensible dans logs, erreurs, fixtures
- [ ] `DECISIONS.md` mis à jour si un choix structurant a été fait
- [ ] `CHANGELOG_AGENT.md` mis à jour — fichiers créés/modifiés, ce qui est utilisable, hypothèses posées, dette éventuelle

---

## 8. Format de rapport de fin de ticket

```
## Ticket [ID] — [Titre]

**Ce qui a été fait** : ...
**Choix techniques** : ...
**Impact sur l'API publique** : ... (aucun / détail)
**Ce qui n'est PAS couvert** : ...
**Points d'attention** : ... (dette, risques, dépendances fragiles)
```

---

## 9. Conventions Git

- Commits : `[ADD]` (nouveau), `[IMP]` (amélioration), `[REF]` (refacto), `[FIX]` (bug)
- Branches : à définir par l'utilisateur (le dépôt n'a pour l'instant que `main`) — ne pas inventer de schéma, demander avant de créer une branche
