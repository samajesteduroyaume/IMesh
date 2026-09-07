# IMesh

Ce projet fournit un maillage Python léger et modulaire pour la découverte locale d’agents IA, l’exécution de tâches et la coordination sécurisée de pairs.

## Démarrage rapide

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
openclaw-mesh --help
```

L’identité du paquet est `IMesh`; les commandes historiques `openclaw-mesh` restent
disponibles pour compatibilité.

## Utilisation

Démarrer un nœud local :

```bash
IMesh start --host 127.0.0.1 --port 8765
```

Découvrir les pairs mDNS présents sur le LAN :

```bash
IMesh discover
```

Appeler un skill distant :

```bash
IMesh call local echo --url ws://127.0.0.1:8765 --payload '{"message":"bonjour"}'
```

Démarrer le gateway HTTP :

```bash
IMesh gateway --host 127.0.0.1 --port 8000
```

Le gateway expose `/api/v1/health`, `/api/v1/skills`, `/api/v1/execute`,
`/api/v1/models`, ainsi que des routes compatibles OpenAI et Anthropic.

## Configuration

Toutes les variables utilisent le préfixe `OPENCLAW_` pour conserver la
compatibilité avec les déploiements existants :

```bash
export OPENCLAW_DEFAULT_PORT=8765
export OPENCLAW_PSK='une-cle-secrete-longue'
export OPENCLAW_MDNS_ENABLED=true
export OPENCLAW_WAN_ENABLED=false
export OPENCLAW_GATEWAY_DB_PATH=./openclaw_gateway.db
```

WAN, DHT, QUIC et gossip sont désactivés par défaut. Leur activation doit être
explicite et accompagnée d'une authentification adaptée au déploiement.

## Fonctionnalités

- Runtime de nœud asynchrone via WebSocket
- Protocole de tâches signé
- Registre de skills
- Support E2EE pour les payloads
- Découverte locale de pairs via mDNS
- Passerelle FastAPI et portail local
- Backends d’inférence dépendants du matériel avec repli CPU

## Licence

MIT
