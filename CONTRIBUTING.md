# Contributing to IMesh

Merci de contribuer a IMesh.

## Environnement

IMesh supporte Python 3.10 et les versions plus recentes.

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Avant une pull request

```bash
python -m black --check --target-version py310 openclaw_mesh tests
python -m ruff check openclaw_mesh tests
python -m pytest -q
```

Les changements doivent rester focalises, conserver l'API publique et ajouter
un test pour tout nouveau comportement. Les dependances optionnelles doivent
etre importees de maniere sure et ne doivent pas rendre le coeur inutilisable.

## Commits et pull requests

- Decrivez le probleme resolu et le comportement attendu.
- Indiquez les commandes de validation executees.
- Documentez toute variable `OPENCLAW_` ajoutee.
- Ne committez jamais de secrets, de cles privees ou de bases locales.

## Compatibilite

Le nom de paquet est `IMesh`, tandis que `openclaw-mesh` reste un alias CLI
historique. Toute modification de ces interfaces doit etre documentee.
