# Memory Index

- [GitHub push auth](github-push-auth.md) — Replit credential helper broken here; push via PAT secret URL, checkout main first; PAT has repo+workflow scopes.
- [SQLAlchemy 2 native enum asyncpg](sqlalchemy-native-enum-asyncpg.md) — must add values_callable to ALL native enum columns or asyncpg sends .name (uppercase) not .value.
- [Test isolation: stale DB state](test-isolation-stale-db.md) — claim_next/dispatch tests must park leftover workers and retire stale PENDING assignments at test start.
- [RLS + flush vs commit](rls-flush-vs-commit.md) — never commit mid-route when RLS set_config is active; use flush instead so the config stays in-transaction.
