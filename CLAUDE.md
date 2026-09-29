# CLAUDE.md — Instructions pour Claude Code

> Ce fichier est lu automatiquement par Claude Code à chaque session.
> Il sert de pont vers les fichiers `.agents/` qui contiennent les règles du projet.

**Projet** : Mircapgen — framework Python pour créer des microservices MCP sécurisés (Features, RBAC, admin, secrets, logs, CLI) destinés aux agents IA.
**Référence fonctionnelle** : [mircapgen_cahier_des_charges_v0.md](mircapgen_cahier_des_charges_v0.md)

---

## Lecture obligatoire en début de session

**Avant toute action, lis ces fichiers dans cet ordre :**

1. [.agents/AGENT.md](.agents/AGENT.md) — comportement général, standards, checklist de livraison
2. [.agents/CONVENTIONS.md](.agents/CONVENTIONS.md) — stack, structure, nommage, règles spécifiques au projet
3. [.agents/CHANGELOG_AGENT.md](.agents/CHANGELOG_AGENT.md) — état actuel du code, ce qui a déjà été fait
4. [.agents/DECISIONS.md](.agents/DECISIONS.md) — décisions techniques prises et questions encore ouvertes

Ces fichiers sont la mémoire du projet. Les ignorer entraîne des incohérences avec le travail déjà livré. S'ils deviennent volumineux, lis l'« État global » et les dernières entrées du changelog, puis cherche dans `DECISIONS.md` les sujets liés à la tâche.

---

## Documentation obligatoire en fin de ticket

Après chaque ticket ou tâche significative, tu **dois** mettre à jour :

### `.agents/CHANGELOG_AGENT.md`
- Section "État global" : met à jour le statut du module concerné
- Nouvelle entrée en bas avec : fichiers créés/modifiés, ce qui est utilisable, hypothèses posées, dette éventuelle

### `.agents/DECISIONS.md`
- Ajoute une entrée pour chaque choix technique structurant (bibliothèque retenue, format de donnée, contrat d'API publique, contournement d'une lib, etc.)
- Format : Contexte / Décision / Alternative écartée / Conséquences
- Si le choix résout une « Question ouverte », déplace-la dans les décisions prises

**Ne considère pas un ticket terminé tant que ces deux fichiers ne sont pas à jour.**

---

## Stack technique (rappel)

Python · SDK officiel `mcp` v2 (isolé derrière l'adaptateur `mcp/`) · `pytest` · manifeste `mircap.yaml` · CLI `mircapgen`.
Python 3.11+ · `pyproject.toml` + hatchling + `uv` · `ruff` · `pyright` · Starlette · Pydantic v2 · PyYAML. Installation : `uv sync`. Vérifications : `uv run pytest`, `uv run ruff check`, `uv run ruff format`, `uv run pyright`.
Templates admin, persistance : **non tranchés** — voir `DECISIONS.md` (Questions ouvertes).

---

## Règles rapides

- **Framework, pas application** : l'API publique (décorateurs, `mircap.yaml`, CLI, fixtures pytest, noms de permissions) est le produit — toute modification est signalée et validée avant
- **Ne tranche pas seul** les questions d'architecture ouvertes (`DECISIONS.md`) : propose une recommandation argumentée et attends validation
- Séparation stricte **métier / infrastructure** : le code d'une Feature n'importe ni MCP, ni auth, ni RBAC, ni logs
- Pipeline de requête à respecter : authentification → découverte/filtrage → autorisation → validation → middleware → Feature → validation sortie → audit. Jamais de contournement
- **Sécurité par défaut** : deny by default, un `Secret` ne fuite jamais (logs, erreurs, réponses MCP, HTML, exports), un agent ne voit que les Features autorisées
- Erreurs : hiérarchie `MircapError` — jamais d'exception Python brute vers un agent
- Type hints + docstrings (français) sur toute API publique
- Tests avec `pytest` : cas nominal + cas limites + erreurs attendues (+ tests de sécurité pour auth/RBAC/secrets)
- Ne pas ajouter de dépendance externe sans la signaler (voir `CONVENTIONS.md` pour la liste approuvée — vide au départ)
- Respecter l'anti-périmètre : pas de framework web généraliste, ORM, IAM complet, orchestrateur d'agents ni moteur LLM
- Identifiants de code en anglais ; docstrings, commentaires, messages utilisateur/agent en français
- Commits : `[ADD]` nouveau · `[IMP]` amélioration · `[REF]` refacto · `[FIX]` bug
