"""Lance le service d'exemple avec deux utilisateurs de démonstration.

    uv run python -m crm_service

Les clés sont générées à chaque démarrage et affichées une seule fois : copiez-les dans la
configuration de votre client MCP (en-tête `Authorization: Bearer <clé>`).
"""

from crm_service.app import build_app
from mircapgen import MemoryStore, User
from mircapgen.auth.keys import generate_key
from mircapgen.store.base import ApiKeyRecord


def main() -> None:
    alice, bob = generate_key(), generate_key()
    store = MemoryStore(
        [User("alice", groups=("reader",)), User("bob", groups=("manager",))],
        [
            ApiKeyRecord(alice.prefix, alice.key_hash, "alice", label="démo"),
            ApiKeyRecord(bob.prefix, bob.key_hash, "bob", label="démo"),
        ],
    )
    print("Service d'exemple sur http://127.0.0.1:8000/mcp")
    print(f"  alice (lecture)             : {alice.secret}")
    print(f"  bob   (lecture + suppression): {bob.secret}")
    build_app(store).run()


if __name__ == "__main__":
    main()
