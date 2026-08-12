# Setup

## Prérequis

- [uv](https://docs.astral.sh/uv/) installé (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Docker (pour PostgreSQL)

## Démarrage

```bash
cp .env.example .env
make up          # démarre PostgreSQL (docker compose) (sur un tout premier démarrage, attendez quelques secondes que le healthcheck passe au vert avant l'étape suivante)
uv sync          # installe les dépendances Python
make migrate     # applique les migrations Alembic
make seed        # (optionnel) crée quelques events/slots/users de démo
make dev         # démarre l'API sur http://localhost:8000 (docs sur /docs)
```

Dans un autre terminal, pour lancer les tests (contre la vraie base PostgreSQL, pas de mock) :

```bash
make test
```

## Ce qui est déjà en place

- Connexion PostgreSQL async (SQLAlchemy 2.0 + asyncpg) — `app/database.py`
- Modèles `User`, `Event`, `Slot`, `Reservation` — `app/models/`
- Migration initiale créant les 4 tables — `alembic/versions/0001_initial.py`
- Les 4 endpoints de l'énoncé déclarés (routing, schémas Pydantic, injection DB) mais **non implémentés** (`501 Not Implemented`) — `app/routers/`
- Un endpoint `GET /health` pour vérifier que le setup fonctionne

## Ce qu'il reste à faire (c'est le test)

- Implémenter la création de réservation sans survente (`app/routers/reservations.py::create_reservation`)
- Implémenter l'idempotence sur `request_id`
- Implémenter l'annulation (`cancel_reservation`)
- Implémenter `GET /slots/{slot_id}` (disponibilité restante) et `GET /slots/{slot_id}/reservations` (sans N+1)
- Ajouter aux modèles les colonnes nécessaires à votre mécanisme choisi (ex: `version`, contrainte d'unicité sur `request_id`, `status`...) via une nouvelle migration Alembic
- Écrire les tests de concurrence et de comptage de requêtes SQL
- Rédiger le `README.md`

## Commandes utiles

| Commande       | Effet                                             |
|----------------|----------------------------------------------------|
| `make up`      | démarre PostgreSQL                                  |
| `make down`    | arrête PostgreSQL                                   |
| `make reset`   | repart d'une base PostgreSQL vide                   |
| `make migrate` | applique les migrations Alembic                     |
| `make seed`    | peuple la base avec des données de démo             |
| `make dev`     | démarre l'API en local avec rechargement à chaud    |
| `make test`    | lance la suite de tests pytest                      |
| `make lint`    | vérifie le style avec ruff                          |
| `make fmt`     | formate le code avec ruff                           |

## Créer une nouvelle migration

```bash
uv run alembic revision --autogenerate -m "description du changement"
uv run alembic upgrade head
```
