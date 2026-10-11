# Booking API — Test technique

API FastAPI asynchrone pour réserver des places sur des créneaux d'événements. Le projet utilise SQLAlchemy 2, PostgreSQL et Alembic.

## Prérequis et démarrage

- Python 3.12 (version du projet, indiquée dans `.python-version`)
- [`uv`](https://docs.astral.sh/uv/)
- Docker et Docker Compose

```bash
cp .env.example .env
docker compose up -d
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed
uv run uvicorn app.main:app --reload
```

L'API et sa documentation interactive sont disponibles sur `http://localhost:8000` et `http://localhost:8000/docs`. Le contrôle de santé est exposé à `GET /health`.

La variable `DATABASE_URL` peut remplacer l'URL de base définie dans `app/config.py`. Les tests fonctionnels utilisent une vraie base PostgreSQL configurée par cette URL : appliquer les migrations avant de les lancer.

## Endpoints

### `POST /slots/{slot_id}/reservations`

Crée une réservation confirmée. Corps JSON :

```json
{
  "user_id": 1,
  "request_id": "client-generated-unique-key"
}
```

- `201 Created` : réservation créée ou réponse à une répétition idempotente.
- `404 Not Found` : créneau ou utilisateur inconnu.
- `409 Conflict` : créneau complet ou clé `request_id` déjà utilisée pour un autre créneau par cet utilisateur.
- La clé d'idempotence est unique par utilisateur (`user_id`, `request_id`).

### `DELETE /reservations/{reservation_id}`

Annule une réservation en faisant passer son statut à `cancelled`, sans supprimer la ligne. Une annulation répétée est sans effet supplémentaire. Renvoie `204 No Content` ou `404 Not Found` si la réservation n'existe pas.

### `GET /slots/{slot_id}`

Retourne l'identifiant du créneau, son événement, sa capacité et le nombre de places disponibles. Les réservations annulées ne consomment plus de capacité. Un créneau inconnu renvoie `404`.

### `GET /slots/{slot_id}/reservations?limit=20&offset=0`

Retourne les réservations du créneau, y compris l'historique des réservations annulées, avec les informations utilisateur et événement.

La réponse est paginée :

```json
{
  "items": [],
  "total": 0,
  "limit": 20,
  "offset": 0
}
```

`limit` doit être compris entre 1 et 100 ; `offset` doit être positif ou nul. L'ordre est déterministe : date de création décroissante, puis identifiant décroissant.

## Garanties et décisions techniques

- **Pas de survente :** la création verrouille la ligne du créneau avec `SELECT ... FOR UPDATE`, compte les réservations confirmées et insère la nouvelle réservation dans la même transaction. Les créations concurrentes pour un même créneau sont donc sérialisées.
- **Idempotence :** la contrainte unique PostgreSQL sur `(user_id, request_id)` est la garantie finale contre les doublons. Le code renvoie la réservation existante pour un retry qui réutilise la clé sur le même créneau.
- **Annulation conservatrice :** on conserve la ligne et on change son statut ; les comptes de disponibilité ne comptent que les réservations `confirmed`.
- **Liste sans N+1 :** les champs de réservation, utilisateur et événement sont récupérés par une seule requête avec jointures. Une requête supplémentaire calcule le total paginé : l'endpoint effectue deux `SELECT`, indépendamment du nombre de résultats.
- **Index :** l'index `(slot_id, status)` prend en charge les filtres fréquents de disponibilité et de liste ; la contrainte unique prend en charge l'idempotence.

La pagination `offset`/`limit` convient au périmètre du test. Pour une liste très volumineuse et très dynamique, une pagination par curseur serait une évolution possible.

## Vérifications

```bash
uv run ruff check app tests
uv run pytest
uv run alembic current
```

Les tests de réservations créent des événements, créneaux et utilisateurs isolés dans la base configurée, vérifient la concurrence avec plusieurs requêtes asynchrones et suppriment leurs propres données après chaque test. **Ne configure pas les tests sur une base de production.**

Les tests de concurrence nécessitent PostgreSQL réel et les migrations à jour ; une base SQLite ne reproduit pas les verrous PostgreSQL testés ici.

## Historique du travail

1. Vérification de l'environnement initial.
2. Statut, contrainte d'idempotence et index.
3. Création transactionnelle des réservations, verrouillage de créneau et retries.
4. Annulation et disponibilité.
5. Liste enrichie par jointures et pagination.
6. Tests de concurrence, idempotence, annulation et comptage SQL.
7. Documentation du fonctionnement, des garanties et des compromis.
