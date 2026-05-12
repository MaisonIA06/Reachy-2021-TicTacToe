# 🕹️ Plan de migration : Interface web rétro arcade

> **Contexte** : Remplacement de l'affichage `cv.imshow` (OpenCV GUI Python) par une page web servie depuis le NUC. Plus économe en CPU, multi-spectateur, esthétique customisable.
>
> Voir aussi : [`OPTIMISATIONS_PERFORMANCES.md`](OPTIMISATIONS_PERFORMANCES.md) et [`OPTIMISATIONS_CPU.md`](OPTIMISATIONS_CPU.md).

---

## 🎯 Objectif

Remplacer la fenêtre OpenCV par une page web légère, accessible depuis n'importe quel appareil du réseau local du robot (`http://<ip-du-nuc>:5000`), avec un rendu **rétro arcade monochrome Game Boy**.

---

## 📋 Cahier des charges (validé)

| Aspect | Choix |
|---|---|
| **Audience principale** | Public / spectateurs + Joueur côté robot |
| **Style visuel** | Rétro arcade, monochrome Game Boy |
| **Palette** | 4 nuances vert olive (Game Boy DMG original) |
| **Effets CRT** | Aucun (sobre, pas de scanlines/glow) |
| **Représentation pièces** | Icônes expressives (🤖 Reachy / 🧑 humain) |
| **Niveau d'information** | Riche (+ action Q-agent + valeur + indicateur "Reachy réfléchit…") |
| **Layout** | Une seule vue responsive (mobile + TV) |
| **Disposition** | Avatars de chaque côté du plateau |
| **Police** | Press Start 2P (Google Fonts) |
| **Avatars** | SVG inline, 4 états : neutre · réfléchit · joue · fin (gagne/perd/égalité) |
| **Score** | Reset à chaque lancement du jeu |
| **Contrôles interactifs** | Aucun (interface passive) |
| **Décor** | Cadre arcade pixel autour de la page |

---

## 🎨 Palette exacte (Game Boy DMG)

```css
:root {
  --gb-lightest: #9BBC0F;  /* Vert le plus clair — fond ou highlights */
  --gb-light:    #8BAC0F;  /* Vert clair — éléments secondaires */
  --gb-dark:     #306230;  /* Vert foncé — texte principal, plateau */
  --gb-darkest:  #0F380F;  /* Vert très foncé — fond principal, bordures */
}
```

**Convention d'usage** :
- Fond global : `--gb-darkest`
- Cadre arcade + bordures plateau : `--gb-dark`
- Texte principal (titres, score, statut) : `--gb-lightest`
- Texte secondaire / inactif : `--gb-light`
- Avatar inactif : assombri via `opacity: 0.4`

---

## 🔤 Police

```html
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
```

```css
body {
  font-family: 'Press Start 2P', monospace;
}
```

⚠️ Press Start 2P est lourde en grand → utiliser des tailles modérées (`14px` body, `24–32px` titres) et `letter-spacing` léger pour la lisibilité.

---

## 🖼️ Wireframe final

### Vue desktop / TV (paysage)

```
  ┌─────────────────────────────────────────────────┐  ← cadre arcade pixel
  │                                                  │
  │              ████ TIC TAC TOE ████               │
  │                                                  │
  │  ┌─────────┐   ┌──────────────────┐  ┌─────────┐ │
  │  │   🤖    │   │   |    |    |    │  │   🧑    │ │
  │  │ REACHY  │   │ ──+────+────+──  │  │  YOU    │ │
  │  │         │   │   | 🤖 | 🧑 |    │  │         │ │
  │  │ R: 03   │   │ ──+────+────+──  │  │ U: 02   │ │
  │  │         │   │   |    | 🤖 | 🧑 │  │         │ │
  │  │ THINK_  │   │   |    |    |    │  │         │ │
  │  └─────────┘   └──────────────────┘  └─────────┘ │
  │                                                  │
  │  > Reachy joue case 5 (Q = 0.87)                │
  │  _                                               │
  │                                                  │
  └─────────────────────────────────────────────────┘
```

### Vue mobile (portrait)

```
  ┌───────────────────┐
  │ ██ TIC TAC TOE ██ │
  │                   │
  │  ┌─────────────┐  │
  │  │     🤖      │  │
  │  │   REACHY    │  │
  │  │   R: 03     │  │
  │  │   THINK_    │  │
  │  └─────────────┘  │
  │                   │
  │  ┌─────────────┐  │
  │  │  |    |     │  │
  │  │ -+----+----+│  │
  │  │  | 🤖 | 🧑  │  │
  │  │ -+----+----+│  │
  │  │  |    | 🤖  │  │
  │  └─────────────┘  │
  │                   │
  │  ┌─────────────┐  │
  │  │     🧑      │  │
  │  │    YOU      │  │
  │  │   U: 02     │  │
  │  └─────────────┘  │
  │                   │
  │ > Reachy joue 5   │
  └───────────────────┘
```

---

## 🤖 Spécifications des avatars SVG

Chaque avatar (Reachy et Humain) est un SVG inline avec **4 états visuels**.

### Avatar Reachy

| État | Trigger | Description visuelle |
|---|---|---|
| `neutral` | État par défaut, attente | Antennes droites, expression neutre |
| `thinking` | Pendant `run_thinking_behavior()` | Antennes qui ondulent (animation CSS `@keyframes`), petits points "..." à côté |
| `playing` | Pendant `play_pawn()` | Bras stylisé levé, pince qui se ferme |
| `win` / `lose` / `draw` | Fin de partie | Sourire + antennes hautes / antennes tombantes / antennes interrogatives |

### Avatar Humain

| État | Trigger | Description visuelle |
|---|---|---|
| `neutral` | État par défaut | Visage neutre |
| `playing` | `current_player == 'human'` | Surligné, animation pulse légère |
| `win` / `lose` / `draw` | Fin de partie | Heureux / déçu / surpris |

### Forme et style

- Style **pixel art** (formes rectangulaires, pas de courbes lisses).
- Dimensions : **64×64 viewBox** suffit, scaling CSS pour responsive.
- Couleurs : **uniquement les 4 nuances Game Boy**.
- Animations : CSS pure (`@keyframes`, `transform`, `opacity`). Pas de JS.

---

## 🏗️ Architecture technique

### Stack

- **Backend** : `Flask` + Server-Sent Events (SSE) natif Python (pas de `flask-sse`).
- **Frontend** : 1 fichier HTML + 1 fichier CSS + 1 fichier JS vanilla.
- **Communication** : Push unidirectionnel serveur → navigateur sur changement d'état.
- **Dépendance ajoutée** : `flask` (~5 Mo).

### Structure de fichiers à créer

```
reachy_tictactoe/
├── web/                          # Nouveau module web
│   ├── __init__.py
│   ├── server.py                 # Serveur Flask + SSE
│   ├── state_publisher.py        # Bus d'événements (queue.Queue)
│   ├── templates/
│   │   └── board.html
│   └── static/
│       ├── style.css
│       ├── app.js
│       └── sprites/              # Si on garde des SVG dans des fichiers
│           ├── reachy.svg
│           └── human.svg
```

### Flux de données

```
TictactoePlayground
       │
       │  state_publisher.publish({
       │    'board': [...],
       │    'current_player': 'robot',
       │    'winner': None,
       │    'reachy_state': 'thinking',
       │    'last_action': 5,
       │    'last_q_value': 0.87,
       │    'scores': {'robot': 3, 'human': 2, 'draw': 0}
       │  })
       │
       ▼
   queue.Queue
       │
       ▼
   Flask SSE endpoint /events
       │
       ▼  (text/event-stream)
   Navigateur
       │
       ▼
   app.js → met à jour le DOM
```

### Point d'intégration dans le code existant

**`tictactoe_playground.py`** :
- Au lieu d'appeler `display_board(board, current_player, winner)` → `state_publisher.publish(...)`.
- Garder `display_board` derrière un flag pendant la migration.
- Démarrer le serveur web dans `setup()` via un `Thread(daemon=True)`.

**`game_launcher.py`** :
- Ajouter un argument `--no-web` pour désactiver le serveur web si besoin.
- Logger l'URL d'accès au démarrage : `INFO: Web UI available at http://<ip>:5000`.

---

## ✅ Liste de tâches d'implémentation

### Phase 1 — Backend minimal

- [ ] **1.1** Créer `reachy_tictactoe/web/__init__.py`
- [ ] **1.2** Ajouter `flask>=2.0` à `requirements.txt` et `setup.py`
- [ ] **1.3** Créer `state_publisher.py` avec une `queue.Queue` globale + fonction `publish(event_dict)`
- [ ] **1.4** Créer `server.py` :
  - [ ] Route `/` → sert `board.html`
  - [ ] Route `/events` → SSE qui yield depuis la queue
  - [ ] Fonction `run_server(host='0.0.0.0', port=5000)` à lancer dans un Thread
- [ ] **1.5** Tester en isolation : lancer le serveur, ouvrir `localhost:5000`, push manuel via `state_publisher.publish(...)` et vérifier la réception SSE dans la console navigateur

### Phase 2 — Frontend statique (sans data)

- [ ] **2.1** Créer `templates/board.html` :
  - [ ] Structure HTML 3 colonnes (avatar gauche / plateau / avatar droit)
  - [ ] Lien vers Google Fonts (Press Start 2P)
  - [ ] Conteneur info en bas (action Q-agent)
- [ ] **2.2** Créer `static/style.css` :
  - [ ] Variables CSS pour la palette Game Boy
  - [ ] Cadre arcade pixel (`border-image` ou bordures multiples)
  - [ ] Grille 3 colonnes (avatar / plateau / avatar)
  - [ ] Media query mobile (empiler verticalement)
  - [ ] Animation curseur clignotant (`@keyframes blink`)
  - [ ] Animation fade-in pour nouvelle pièce
- [ ] **2.3** Créer les sprites SVG inline pour Reachy (4 états) et Humain (4 états)
  - [ ] Pixel art en 64×64 viewBox
  - [ ] Classes CSS `.avatar.thinking`, `.avatar.playing`, etc. pour switcher
- [ ] **2.4** Tester le rendu visuel statique (sans data réelle) avec un mock JS

### Phase 3 — Connexion frontend / backend

- [ ] **3.1** Créer `static/app.js` :
  - [ ] Connexion `EventSource('/events')`
  - [ ] Handler `onmessage` → parse JSON, update DOM
  - [ ] Update des cases du plateau (icône selon `board[i]`)
  - [ ] Update indicateur de tour (highlight de l'avatar actif)
  - [ ] Update état Reachy (classe CSS sur le SVG)
  - [ ] Update info Q-agent
  - [ ] Reconnexion automatique en cas de coupure
- [ ] **3.2** Tester avec des push manuels depuis Python

### Phase 4 — Intégration dans le jeu

- [ ] **4.1** Modifier `TictactoePlayground.setup()` pour démarrer le serveur web en `Thread(daemon=True)`
- [ ] **4.2** Modifier `TictactoePlayground.display_board()` pour publier dans le bus (en plus de l'OpenCV pendant la transition)
- [ ] **4.3** Ajouter publication d'événements à des moments clés :
  - [ ] `run_thinking_behavior()` → `reachy_state: 'thinking'`
  - [ ] `play_pawn()` début/fin → `reachy_state: 'playing'` / `'neutral'`
  - [ ] `run_celebration` / `run_defeat_behavior` / `run_draw_behavior` → `reachy_state: 'win'`/`'lose'`/`'draw'`
  - [ ] `choose_next_action()` → `last_action` + `last_q_value`
- [ ] **4.4** Gérer le compteur de score dans `game_launcher.py` (variable locale, reset au lancement)
- [ ] **4.5** Logger l'URL d'accès au démarrage
- [ ] **4.6** Ajouter argument `--no-web` à `game_launcher.py`

### Phase 5 — Polish

- [ ] **5.1** Tester sur plusieurs appareils simultanément (PC + mobile)
- [ ] **5.2** Tester la coupure / reconnexion réseau
- [ ] **5.3** Ajuster les tailles de police / espaces pour la lisibilité mobile
- [ ] **5.4** Vérifier le rendu en plein écran sur TV (F11 dans le navigateur)
- [ ] **5.5** Retirer définitivement `cv.imshow` une fois validé

---

## 📊 Estimation du coût CPU

| Phase | OpenCV `cv.imshow` actuel | Page web (SSE) |
|---|---|---|
| Plateau stable (entre coups) | ~2–5 % CPU continu (redessin) | **~0 %** |
| Changement d'état | ~5–8 % CPU (pic) | **~0.1 %** (sérialisation JSON + envoi) |
| Démarrage | Quasi nul | ~1–2 s (chargement Flask) |
| RAM | ~50 Mo (OpenCV display) | ~30 Mo (Flask + queue) |
| Dépendances supplémentaires | — | `flask` (~5 Mo) |

**Verdict** : Migration **gagnante** côté NUC. Le rendu graphique passe entièrement chez les clients (navigateur).

---

## 🔄 Plan de migration progressive

1. **Phase 1–3** : développement isolé, le jeu continue à tourner avec OpenCV.
2. **Phase 4** : intégration en double affichage (OpenCV + web en parallèle). Permet de valider que le web reflète bien l'état du jeu.
3. **Phase 5** : une fois la validation faite sur plusieurs parties, **retirer `display_board` OpenCV** définitivement et nettoyer les imports `cv` liés à l'affichage.

⚠️ **Garder OpenCV pour la vision** (`get_board_configuration`, calibration) — seul l'**affichage** disparaît.

---

## 🛡️ Considérations / points d'attention

- **Sécurité réseau** : par défaut binder sur `0.0.0.0:5000` pour accès LAN. Si le NUC est exposé sur une IP publique, restreindre à l'IP locale uniquement.
- **Pare-feu** : vérifier que le port 5000 est ouvert sur le NUC.
- **Bloquage threads** : la queue Python est thread-safe, mais s'assurer que `state_publisher.publish` n'attend jamais (utiliser `Queue` avec `put_nowait` + `maxsize` raisonnable, ex. 100).
- **Logs Flask** : passer Flask en mode silencieux (`logging.getLogger('werkzeug').setLevel(logging.WARNING)`) sinon flood des logs.
- **Performances mobile** : Press Start 2P + animations CSS = OK sur smartphones modernes, vérifier sur appareils plus anciens si nécessaire.
- **Couleurs CSS variables** : supportées partout depuis 2017, OK.
- **SSE Internet Explorer** : non supporté. Acceptable en 2026.

---

## 🚀 Démarrage rapide (pour la prochaine session)

```bash
# Quand tu reprendras le projet :
cd /home/mia/Bureau/Reachy-2021-TicTacToe
source venv/bin/activate

# Installer Flask
pip install flask

# Créer la structure
mkdir -p reachy_tictactoe/web/{templates,static/sprites}
touch reachy_tictactoe/web/__init__.py
touch reachy_tictactoe/web/server.py
touch reachy_tictactoe/web/state_publisher.py
touch reachy_tictactoe/web/templates/board.html
touch reachy_tictactoe/web/static/style.css
touch reachy_tictactoe/web/static/app.js

# Commencer par la Phase 1 — Backend minimal
```

---

## 📈 Suivi de l'avancement

| Phase | Description | Statut |
|---|---|---|
| 1 | Backend minimal (Flask + SSE + bus) | ⬜ |
| 2 | Frontend statique (HTML + CSS + sprites SVG) | ⬜ |
| 3 | Connexion frontend/backend (EventSource) | ⬜ |
| 4 | Intégration dans le jeu (publish à chaque événement) | ⬜ |
| 5 | Polish + retrait définitif d'OpenCV display | ⬜ |

---

## 📝 Notes / Observations

_(à remplir au fur et à mesure)_

```
Date : _______________
Phase en cours : _______________
Problèmes rencontrés : _______________
Décisions prises : _______________
```

---

**Créé le** : 2026-05-11
