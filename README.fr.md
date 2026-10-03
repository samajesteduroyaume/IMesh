# IMesh

> **Réseau maillé intelligent local-first pour les agents OpenClaw.**

IMesh est un maillage Python léger et modulaire permettant aux agents IA autonomes de se découvrir, d'exécuter des tâches à distance, de partager leurs capacités et de se coordonner de manière sécurisée — sans serveur central.

---

## Sommaire

- [Démarrage rapide](#démarrage-rapide)
- [Référence CLI](#référence-cli)
- [Gateway et portail](#gateway-et-portail)
- [Compatibilité API](#compatibilité-api)
- [Authentification](#authentification)
- [Registre de skills](#registre-de-skills)
- [Skill ClawHub](#skill-clawhub)
- [Référence de configuration](#référence-de-configuration)
- [Vue d'ensemble des fonctionnalités](#vue-densemble-des-fonctionnalités)
- [Architecture](#architecture)
- [Licence](#licence)

---

## Démarrage rapide

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Vérifier l'installation
IMesh version
IMesh --help
```

> Le paquet s'appelle `IMesh`. La commande `openclaw-mesh` reste disponible comme alias de compatibilité.

---

## Référence CLI

### Démarrer un nœud local

```bash
IMesh start --host 127.0.0.1 --port 8765
# Équivalent :
IMesh node --host 127.0.0.1 --port 8765 --no-wan
```

Le nœud démarre un serveur WebSocket asynchrone, s'enregistre sur le service mDNS local (`_openclawmesh._tcp`) et annonce ses skills disponibles à distance.

### Découvrir les pairs sur le LAN

```bash
IMesh discover
```

Retourne une liste JSON des pairs découverts avec leur nom, adresse, port, skills et statut de disponibilité.

### Appeler un skill sur un pair

```bash
IMesh call local echo \
  --url ws://127.0.0.1:8765 \
  --payload '{"message": "bonjour"}'
```

### Démarrer le gateway HTTP

```bash
IMesh gateway --host 127.0.0.1 --port 8000
```

### Gestion de l'identité

```bash
# Générer une clé d'identité Ed25519
IMesh keygen
IMesh keygen --output /chemin/vers/identity.pem

# Afficher l'identité du nœud courant
IMesh identity
IMesh identity --key /chemin/vers/identity.pem
```

### Autres commandes

```bash
IMesh health    # Contrôle de santé local (JSON)
IMesh version   # Affiche la version
IMesh peers     # Conseil : utiliser 'discover' pour la découverte mDNS
```

---

## Gateway et portail

Démarrez le gateway puis ouvrez `http://127.0.0.1:8000/` dans votre navigateur.

```bash
IMesh gateway --host 127.0.0.1 --port 8000
```

### Fonctionnalités du portail

| Section | Description |
|---|---|
| **Tableau de bord** | Résumé temps réel : pairs, pairs accessibles, skills, logs |
| **Pairs** | Tableau avec recherche, filtres par statut/skill et indicateurs de disponibilité |
| **Diagnostics** | Paramètres du gateway, indicateurs de fonctionnalités et liste de skills en direct |
| **Journaux** | Événements récents avec filtrage par texte et niveau, export JSON |
| **Testeur de skills** | Formulaire interactif pour appeler n'importe quel skill depuis le navigateur |

Le portail se rafraîchit automatiquement toutes les 5 secondes.

### Endpoints REST

| Méthode | Chemin | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Sonde de santé |
| `GET` | `/api/v1/skills` | Liste les skills exposés |
| `GET` | `/api/v1/peers` | Liste les pairs découverts |
| `GET` | `/api/v1/models` | Liste les modèles disponibles |
| `GET` | `/api/v1/portal-data` | Données complètes du portail (résumé, pairs, diagnostics, logs) |
| `POST` | `/api/v1/execute` | Exécuter un skill par son nom |
| `POST` | `/api/v1/test-skill` | Identique à execute (pour le portail) |
| `POST` | `/api/v1/checkout/free-key` | Émettre une clé API |
| `POST` | `/v1/chat/completions` | Endpoint de chat compatible OpenAI |
| `POST` | `/v1/messages` | Endpoint de messages compatible Anthropic |

---

## Compatibilité API

### OpenAI

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"bonjour"}]}'
```

Vous pouvez cibler un skill spécifique en ajoutant `"skill": "nom_du_skill"` au corps, ou en préfixant le message avec `skill: nom_du_skill` ou `call nom_du_skill`.

### Anthropic

```bash
curl -X POST http://127.0.0.1:8000/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"bonjour"}]}'
```

---

## Authentification

Par défaut, le gateway fonctionne sans authentification (adapté au développement local). Pour exiger des clés API sur tous les endpoints d'exécution :

```bash
export OPENCLAW_AUTH_REQUIRED=true
IMesh gateway --host 127.0.0.1 --port 8000
```

**Émettre une clé API :**

```bash
curl -X POST http://127.0.0.1:8000/api/v1/checkout/free-key
# → {"api_key": "imesh_..."}
```

**Utiliser la clé :**

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer imesh_..." \
  -H 'Content-Type: application/json' \
  -d '{"model":"openclaw-mesh","messages":[{"role":"user","content":"bonjour"}]}'
```

Endpoints protégés par l'authentification : `/api/v1/execute`, `/v1/chat/completions`, `/v1/messages`.
Les clés sont stockées dans la base SQLite définie par `OPENCLAW_GATEWAY_DB_PATH`.

---

## Registre de skills

### Skills intégrés

| Skill | Description |
|---|---|
| `echo` | Retourne le payload d'entrée inchangé |
| `openclaw_info` | Retourne le nom et la version du maillage |
| `system_info` | Retourne la plateforme et la version Python |
| `_health` | Contrôle de santé — retourne `{"status": "ok"}` |
| `_describe_skills` | Liste tous les skills au format outil OpenAI |

### Enregistrer un skill personnalisé

```python
from openclaw_mesh.registry import SkillRegistry

registry = SkillRegistry()

# Skill synchrone
@registry.register(name="additionner", description="Additionner deux nombres")
def additionner(x: int, y: int) -> dict:
    return {"somme": x + y}

# Skill asynchrone
@registry.register(name="recuperer", description="Récupérer une URL")
async def recuperer(url: str) -> dict:
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return {"statut": r.status_code}

# Skill en streaming (générateur)
@registry.register(name="compter", description="Flux de nombres")
def compter(n: int = 5):
    for i in range(n):
        yield i

# Skill privé (non accessible à distance)
@registry.register(name="secret", expose_remote=False)
def secret():
    return {"valeur": "local uniquement"}
```

### Appeler un skill par programmation

```python
import asyncio
from openclaw_mesh.registry import get_default_registry

registry = get_default_registry()

# Appel synchrone (sûr dans et hors d'une boucle d'événements)
resultat = registry.call("echo", {"bonjour": "monde"})

# Appel asynchrone (préféré dans un contexte async)
async def main():
    resultat = await registry.acall("echo", {"bonjour": "monde"})
```

### Utiliser le client WebSocket

```python
import asyncio
from openclaw_mesh.client import MeshClient, MeshTaskError

async def main():
    client = MeshClient(secret="ma-cle-secrete")
    client.add_peer("noeud-a", "ws://192.168.1.10:8765")
    try:
        resultat = await client.call("noeud-a", "echo", {"ping": True})
        print(resultat)
    except MeshTaskError as e:
        print(f"Tâche échouée : {e}")
    finally:
        await client.stop()

asyncio.run(main())
```

### Recevoir des chunks d'un skill en streaming

```python
async def main():
    client = MeshClient(secret="ma-cle-secrete")
    client.add_peer("noeud-a", "ws://127.0.0.1:8765")

    chunks = []
    resultat = await client.stream_call(
        "noeud-a",
        "compter",
        {"n": 5},
        on_chunk=lambda c: chunks.append(c["chunk"]),
    )
    print(chunks)    # ["0", "1", "2", "3", "4"]
    print(resultat)  # {"items": ["0", "1", "2", "3", "4"]}
```

---

## Skill ClawHub

Le paquet de skill agent est disponible dans [`skills/imesh/SKILL.md`](skills/imesh/SKILL.md) et décrit par [`clawhub.json`](clawhub.json).

Il fournit des commandes sûres pour démarrer un nœud, découvrir les pairs de confiance, appeler un skill, vérifier le gateway et gérer les identités.

---

## Référence de configuration

Tous les paramètres utilisent le préfixe `OPENCLAW_` et peuvent également être définis dans un fichier `.env`.

| Variable | Défaut | Description |
|---|---|---|
| `OPENCLAW_NODE_NAME` | `openclaw-node` | Identifiant annoncé sur mDNS |
| `OPENCLAW_CLIENT_NAME` | `openclaw-client` | Identifiant utilisé dans les requêtes de tâches |
| `OPENCLAW_DEFAULT_HOST` | `127.0.0.1` | Adresse d'écoute du nœud |
| `OPENCLAW_DEFAULT_PORT` | `8765` | Port WebSocket du nœud |
| `OPENCLAW_PSK` | *(aucune)* | Secret partagé pour la signature HMAC |
| `OPENCLAW_MDNS_ENABLED` | `true` | Activer la découverte mDNS |
| `OPENCLAW_WAN_ENABLED` | `false` | Activer le transport WAN (opt-in) |
| `OPENCLAW_DHT_ENABLED` | `false` | Activer le routage DHT (opt-in) |
| `OPENCLAW_QUIC_ENABLED` | `false` | Activer le transport QUIC (opt-in) |
| `OPENCLAW_GOSSIPSUB_ENABLED` | `false` | Activer GossipSub (opt-in) |
| `OPENCLAW_E2EE_ENABLED` | `false` | Activer le chiffrement bout-en-bout |
| `OPENCLAW_IDENTITY_KEY_PATH` | `./.openclaw_identity.pem` | Fichier de clé privée Ed25519 |
| `OPENCLAW_TRUST_STORE_PATH` | `./.openclaw_trust_store.json` | Magasin de confiance des pairs |
| `OPENCLAW_MAX_ACTIVE_TASKS` | `32` | Maximum de tâches concurrentes par nœud |
| `OPENCLAW_MAX_QUEUED_TASKS` | `128` | Maximum de tâches en attente |
| `OPENCLAW_TASK_TIMEOUT` | `30.0` | Délai d'exécution des tâches (secondes) |
| `OPENCLAW_MAX_OUTPUT_BYTES` | `1000000` | Taille maximale de la réponse |
| `OPENCLAW_GATEWAY_HOST` | `127.0.0.1` | Adresse d'écoute du gateway |
| `OPENCLAW_GATEWAY_PORT` | `8000` | Port HTTP du gateway |
| `OPENCLAW_GATEWAY_DB_PATH` | `./openclaw_gateway.db` | Chemin de la base SQLite |
| `OPENCLAW_PEER_TTL_SECONDS` | `120` | Expiration des pairs après dernière vue (secondes) |
| `OPENCLAW_AUTH_REQUIRED` | `false` | Exiger un token Bearer sur les endpoints d'exécution |
| `OPENCLAW_LOG_LEVEL` | `INFO` | Niveau de journalisation |

> **WAN, DHT, QUIC et GossipSub** sont opt-in. N'exposez jamais un nœud publiquement sans `OPENCLAW_PSK` robuste, une politique de confiance et un reverse proxy TLS.

---

## Vue d'ensemble des fonctionnalités

- **Nœud WebSocket asynchrone** — gestion de tâches concurrent non-bloquante avec limites configurables
- **Protocole de tâches signé HMAC** — signature canonique avec protection anti-rejeu
- **Registre de skills** — skills sync, async et générateur ; contrôle d'accès `expose_remote` appliqué au niveau protocole
- **Streaming temps réel** — les skills générateurs envoient des trames `TaskChunk` sur WebSocket
- **Découverte mDNS** — découverte de pairs LAN zéro-config avec expiration TTL et désenregistrement propre
- **Identité Ed25519** — paire de clés persistante par nœud ; magasin de confiance pour l'autorisation des pairs
- **Payloads E2EE** — échange de clés X25519 + chiffrement ChaCha20-Poly1305 avec garde anti-rejeu
- **Gateway FastAPI** — API REST, portail web, export JSON
- **Compatibilité OpenAI & Anthropic** — endpoints compatibles pour les clients LLM
- **Authentification Bearer** — protection optionnelle par clé API stockée en SQLite
- **Moteurs adaptés au matériel** — détection automatique CUDA / ROCm / OpenVINO / MLX / CPU
- **Primitives distribuées** — DHT, gossip, relay, vector store (similarité cosinus), RAG, MoE (stubs opt-in, prêts pour WAN)
- **Docker** — `Dockerfile` minimal inclus

---

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│               Agent OpenClaw / Client LLM                      │
│        (SDK OpenAI · SDK Anthropic · Skill ClawHub)            │
└────────────────────────┬───────────────────────────────────────┘
                         │ HTTP / Bearer token
          ┌──────────────▼────────────────┐
          │        IMesh Gateway           │
          │  FastAPI · Portail · API REST  │
          └──────────────┬────────────────┘
                         │ SkillRegistry.acall()
          ┌──────────────▼────────────────┐
          │     Registre de Skills local   │  ◄── garde expose_remote
          └──────────────┬────────────────┘
                         │ WebSocket (TaskRequest signé HMAC)
     ┌───────────────────┼──────────────────────┐
     │                   │                      │
┌────▼─────┐    ┌────────▼──┐    ┌──────────────▼──┐
│  Nœud A  │   │   Nœud B  │   │     Nœud C       │
│  (CPU)   │   │   (CUDA)  │   │  (Apple MLX)     │
└──────────┘   └───────────┘   └─────────────────-┘
     │                   │                      │
     └──────── mDNS _openclawmesh._tcp ─────────┘
```

Voir [`ARCHITECTURE.md`](ARCHITECTURE.md) pour l'architecture détaillée par couches et les flux d'exécution.

---

## Licence

MIT — voir [`LICENSE`](LICENSE).
