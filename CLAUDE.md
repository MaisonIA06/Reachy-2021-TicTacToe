# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Adaptation du TicTacToe Pollen Robotics (2019) pour le **SDK Reachy 2021** (`reachy-sdk>=0.7.0`). Le robot Reachy V1 joue au morpion contre un humain via vision par ordinateur (TensorFlow Lite), un agent Q-learning préentraîné, et des trajectoires enregistrées du bras droit.

Communication avec l'utilisateur en **français** (voir aussi les sons MP3 et les logs).

## Commandes essentielles

### Setup
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt   # runtime
pip install -e .                  # package en mode dev
pip install -r requirements-training.txt   # SI entraînement (inclut tensorflow)
```

### Lancer le jeu
```bash
# Robot local
python -m reachy_tictactoe.game_launcher
# Robot distant
python -m reachy_tictactoe.game_launcher --host 192.168.1.XXX
# Avec log fichier
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe.log
# Une seule partie puis arrêt (le bras se repose et les moteurs sont
# relâchés à la fin de CHAQUE partie, quel que soit le mode)
python -m reachy_tictactoe.game_launcher --once
# Via entry point installé
reachy-tictactoe
```

### Calibration plateau (à refaire si le plateau bouge)
```bash
python scripts/calibration/calibrate_board.py --host localhost
python scripts/calibration/check_calibrate_board.py --host localhost
python scripts/calibration/check_calibrate_cases.py --host localhost
# Édition directe / inspection
python scripts/utils/show_config.py
python scripts/utils/show_config.py --set-board LEFT RIGHT TOP BOTTOM
```

### Mouvements (à refaire à chaque déplacement du plateau)
```bash
# 1) Surveillance sonore, dans un 2e terminal, PENDANT tout l'enregistrement
#    « Joueur déloyal » = hors butée ; « Observe » = trop bas, risque de balayage
python scripts/moves/watch_recording.py --host localhost
# 2) Enregistrer (mode compliant). Voir GUIDE_REENREGISTREMENT_MOUVEMENTS.md (§ Méthode de travail)
python scripts/moves/record_moves.py --interactive --host localhost
python scripts/moves/record_moves.py --name grab_1 --type position --host localhost
python scripts/moves/record_moves.py --name put_1 --type trajectory --duration 2.5 --host localhost
# 3) Valider APRÈS CHAQUE mouvement (sans robot ; --host ajoute le profil de hauteur)
python scripts/moves/validate_moves.py --name put_1
python scripts/moves/validate_moves.py --host localhost
# 4) Rejouer
python scripts/moves/test_recorded_moves.py --name grab_1 --host localhost
python scripts/moves/test_recorded_moves.py --sequence --host localhost   # les 9 cycles du jeu
python scripts/moves/test_recorded_moves.py --all --host localhost
```

### Vision / modèles (voir GUIDE_CREATION_MODELES.md)
```bash
python scripts/training/collect_boxes_images.py --host localhost --class {empty|cube|cylinder} --target 50
python scripts/training/collect_valid_board_images.py --host localhost --class {valid|invalid} --target 150
python scripts/training/train_models.py --model {all|boxes|valid-board} --epochs 15
python scripts/training/convert_to_tflite.py
python scripts/training/check_training_data.py
```

### Diagnostic moteurs / pince
```bash
# Relevé position/température/charge/compliant de chaque joint (à un instant T)
python scripts/utils/check_motors.py --host localhost
# Moniteur continu temp/charge pendant une partie (à lancer dans un 2e terminal)
python scripts/utils/monitor_temps.py --host localhost --joint r_wrist_roll
# Libérer le couple d'un moteur resté rigide/bloqué après un arrêt brutal du jeu
python scripts/utils/release_arm.py --host localhost
```

Tous les scripts robot prennent `--host`.

### Tests (sans robot)
```bash
pip install -r requirements-dev.txt
pytest          # suite complète, < 1 s
```
La suite (`tests/`) couvre la logique pure : règles du jeu, agent Q-learning, conventions pièces/joueurs, format des mouvements `.npz` (poses 0-d pour `goto_position` vs trajectoires 1-d à 100 Hz pour `play_trajectory`). `tests/conftest.py` injecte des **stubs inconditionnels** de `reachy_sdk`, `tflite_runtime` et `zzlog` dans `sys.modules` — aucun robot ni modèle réel n'est sollicité, même sur le NUC. **CI GitHub Actions** (`.github/workflows/ci.yml`) : la suite tourne à chaque push/PR ; le CI doit être vert avant d'enchaîner. Les tests matériels restent les scripts ci-dessus, exécutés contre le robot.

## Architecture

### Boucle de jeu (`reachy_tictactoe/game_launcher.py`)
1. Attente plateau vide → `coin_flip()` pour décider qui commence.
2. Boucle adaptative : `analyze_board()` est appelée toutes les 100 ms (plateau changeant) ou 500 ms (plateau stable depuis ≥ 3 analyses).
3. Au tour humain : `has_human_played()` détecte un nouveau **cylindre** déposé.
4. Au tour robot : `choose_next_action()` (Q-learning) → `play()` → `play_pawn(grab_index, box_index)`.
5. Détection de triche/incohérence (ajout illégal, retrait ou **déplacement** d'une pièce) avec **double vérification** — une analyse non concluante (`None`) ne vaut pas confirmation. Si confirmée : `shuffle_board()` et la partie retourne `'aborted'`.
6. Fin de partie → célébration/défaite/égalité, vérification température (`need_cooldown()` → 50 °C, sortie à 45 °C).

### Convention pièces (⚠️ inversion vs code original Pollen 2019)
- **Humain** : **cylindres** (`piece2id['cylinder'] = 2`)
- **Reachy** : **cubes** (`piece2id['cube'] = 1`)
- Q-learning : `Q[1] = QX` (cube/robot), `Q[2] = QO` (cylindre/humain). Voir `reachy_tictactoe/utils.py` et `rl_agent.py`.

### Modules
- `tictactoe_playground.py` — `TictactoePlayground` : encapsule `ReachySDK`, la boucle de jeu, l'affichage OpenCV (`display_board`), la séquence `play_pawn` (grab → fermer pince → lift → put trajectoire → ouvrir pince → back), et le cycle thermique. Précharge `moves/*.npz` + warmup TFLite dans un thread démon au `setup()`.
- `behavior.py` — animations émotionnelles (`thinking`, `celebrate`, `sad`, `surprise`), `ThreadPoolExecutor` global (3 workers) pour paralléliser antennes/sons/bras.
- `vision.py` — wrapper `TFLiteClassifier` (CPU uniquement, pas EdgeTPU). `get_board_configuration()` classe les 9 cases via `ttt-boxes.tflite` ; `is_board_valid()` filtre les images bruitées via `ttt-valid-board.tflite`. Si un modèle est compilé EdgeTPU, le wrapper lève une erreur avec instructions.
- `rl_agent.py` — charge `Q-value.npz` (table Q précalculée) et renvoie les actions triées par valeur.
- `motors.py` — helpers moteurs/pince (source unique, importés par le jeu et les scripts `moves/`) : `safe_turn_on(reachy, part)` activation du couple **sans à-coup**, `wait_until_settled(read_position)` attente d'immobilité réelle, `is_holding_pawn(position)` détection du cube saisi. Voir « Pièges ».
- `moves_validation.py` — validation des `.npz` (fonctions pures, sans robot) : `JOINT_LIMITS` (butées URDF, **source unique**), `limit_violations()`, `is_frozen()`, `unexpected_duplicates()`, `amplitude()`. Utilisé par `scripts/moves/validate_moves.py`, `watch_recording.py` et la suite de tests.
- `config.py` — **source unique** pour calibration (`BOARD_POSITION`, `BOARD_CASES`), constantes gripper (`GRIPPER_OPEN=-45`, `GRIPPER_CLOSED=-6`, en degrés, plus négatif = plus ouvert), seuils de détection, chemins modèles. `save_calibration()` réécrit le fichier via regex.
- `moves/__init__.py` — charge dynamiquement tous les `*.npz` du dossier en un dict `moves`. Définit `rest_pos` et `base_pos` (positions cibles joints en degrés).
- `game_launcher.py` — orchestration. `run_game_loop(playground, report=None)` joue **une** partie et publie son avancement via `report`. `GameSession` la pilote partie par partie : `play_one_game()` joue puis **repose le bras et coupe le couple** (`rest()`), compte les parties et publie un `GameState` figé (`state`, `subscribe(listener)`) — c'est ce que consommera l'interface web. CLI : `--once` pour une seule partie, sinon boucle avec relance après exception (sleep 5 s).

### Mouvements enregistrés (`reachy_tictactoe/moves/*.npz`)
Format : `np.load` → dict `{joint_name: array_positions}` à 100 Hz. Noms de joints au format SDK 2021 (`r_arm.r_shoulder_pitch`, etc.).
- `grab_{1..5}` : prendre le pion N (les pions ≥ 4 passent d'abord par `grab_3` comme intermédiaire).
- `lift` : remonter avec le pion serré.
- `put_{1..9}_smooth_10_kp` : trajectoire de dépose dans la case (numérotation 1 = haut-gauche, 9 = bas-droite).
- `back_{1..9}_upright` : retour depuis chaque case.
- `my-turn`, `your-turn`, `shuffle-board` : animations.

### Filtrage du gripper (⚠️ critique)
Dans `goto_position` et `play_trajectory`, **toujours** passer `filter_gripper=True` quand on rejoue un mouvement enregistré pendant qu'un pion est tenu — sinon les positions de gripper enregistrées rouvrent la pince et le pion tombe. Voir `play_pawn()` dans `tictactoe_playground.py` : seule l'étape de pose appelle explicitement `open_gripper()`.

### Caméra / vision
`analyze_board()` : tête regarde `(0.5, 0, -0.6)` — **visée mise en cache** (`_looking_at_board`) : le `look_at` d'1 s n'est refait que si la tête a bougé (`look_at()`), au début de chaque partie (`reset()`), ou après `ANALYSIS_FAILURES_BEFORE_REAIM` (5) analyses ratées d'affilée (récupération si la tête a été bousculée). Capture `reachy.right_camera.last_frame`, sauvegarde dans `/tmp/snap.<rand>.jpg` (debug), valide via `is_board_valid`, puis classifie. `wait_for_img` a un timeout de 5 s et ne reboot plus le système (mode test) — la ligne `os.system('sudo reboot')` est volontairement commentée.

### Sons
MP3 dans `reachy_tictactoe/sounds/`, joués via `subprocess.run(['mpg123', '-a', 'hw:0,0', '-q', path])` (sortie audio ReSpeaker). Pour ajouter un son, le placer dans le dossier et l'appeler depuis `behavior.py` ou `tictactoe_playground.shuffle_board()`.

## Pièges & conventions

- **`goto()` et `head.look_at()` du SDK 2021 sont BLOQUANTS** (ils ne rendent la main qu'à la fin du mouvement — docstring officielle : « This function will block until the movement is over »). ⚠️ **Ne jamais ajouter de `time.sleep(duration)` après un `goto`** : cela double le temps de chaque geste (régression de latence corrigée sur tout le code). Les seuls `sleep` légitimes sont les courtes stabilisations servo et les balayages à 100 Hz par `goal_position` — pour la pince, préférer `motors.wait_until_settled()` à un délai fixe (voir plus bas).
- **Sons en tâche de fond** : `behavior.play_sound_background()` (et non `play_sound_safe()`, qui **bloque** jusqu'à 10 s et figerait le bras en pleine séquence). Un seul worker dans `_sound_executor` — le périphérique ALSA `hw:0,0` est exclusif, deux `mpg123` simultanés échoueraient ; la file sérialise. Échecs loggés par callback. ⚠️ Dans les tests, **stubber** `play_sound_background` : sinon la suite joue réellement du son et monopolise l'unique worker, ce qui fait échouer les tests de sons.
- **Joints en degrés** dans le SDK 2021 (pas radians). Antennes, bras, gripper.
- **Activation du couple : jamais `reachy.turn_on()` brut** — toujours `safe_turn_on()` (`reachy_tictactoe/motors.py`). Au `turn_on`, le registre `goal_position` contient encore la consigne du mouvement précédent et le moteur saute violemment vers cette vieille cible (« coup violent au début » historique). `safe_turn_on` synchronise `goal_position = present_position` (gripper **exclu** : `close_gripper()` sur-commande volontairement la consigne pour serrer — resynchroniser lâcherait le pion), attend 0,05 s (le flux de commandes ~100 Hz est asynchrone vs le RPC `turn_on`), puis active. Exception assumée : les scripts `calibration/` et `training/` (tête seule, sans dépendance au package) gardent `turn_on('head')` brut.
- **Trajectoires 100 Hz : pré-positionnement intégré** — `play_trajectory()` fait d'abord un `goto` doux (0,5 s) vers le premier point si le bras en est à plus de 3° : la première consigne streamée serait sinon un échelon brutal. Ne pas ré-ajouter de `goto` vers le premier point chez les appelants.
- **Limites articulaires (⚠️ enregistrements)** : en compliant on peut pousser le bras **au-delà des butées logicielles** à la main — l'encodeur lit la vraie position, mais **le contrôleur écrête au rejeu** et le bras rate sa cible en silence. Valeurs dans `moves_validation.JOINT_LIMITS` (source unique, degrés) : shoulder_pitch [−150, 90], shoulder_roll [−180, 10], **arm_yaw [−90, 90]** (le piège principal), elbow_pitch [−125, 0], forearm_yaw [−100, 100], wrist_pitch [−45, 45], wrist_roll [−35, 54.4], gripper [−68.8, 20]. Conséquence géométrique : les cases du plateau doivent rester **à droite de l'axe du robot** (y ≤ −0,03 m, repère x=avant/y=gauche), sinon `arm_yaw` > 90° est nécessaire et la case est physiquement injouable.
- **Enregistrer un mouvement : toujours surveiller + valider** — deux défauts sont invisibles au moment de l'enregistrement et ont chacun coûté une session entière : le **flux de positions gelé** (fichiers figés et identiques entre eux) et le **dépassement de butée**. Un troisième, la descente trop précoce, fait **balayer le plateau** en transit. Procédure : `watch_recording.py` en fond (alertes sonores en direct) + `validate_moves.py --name <move>` après **chaque** capture, avant de passer au suivant. Détail dans `GUIDE_REENREGISTREMENT_MOUVEMENTS.md` (§ Méthode de travail). Geste `put_N` correct : rester haut pendant tout le transit, descendre **verticalement** seulement une fois au-dessus de la case (≥ 3 cm de garde).
- **Activation gripper** : `self.reachy.r_arm.r_gripper.compliant = False` est appelé explicitement et vérifié dans `play_pawn` ; ne pas supposer qu'il reste actif.
- **Fermeture pince** : `play_pawn` ferme via `close_gripper()`, qui **force** `goal_position` à `GRIPPER_CLOSED` avec `torque_limit=100`. ⚠️ Ne pas remplacer par une fermeture progressive à seuil de charge bas : les pics transitoires de démarrage du moteur déclenchent la détection trop tôt et la pince s'arrête quasi ouverte sans attraper le cube (régression observée et corrigée).
- **Détection « cube saisi » : par POSITION, jamais par `present_load`** — mesures du 2026-09-02 : la charge vaut **2 aussi bien pince vide que cube serré**, elle ne discrimine rien (l'ancien seuil `< 80` criait au loup à chaque coup et n'aurait jamais vu une vraie prise à vide). La position de blocage, elle, sépare franchement : **−8,0° à vide**, **−10,6° à −19,8° avec un cube** ; seuil `config.GRIPPER_HOLDING_THRESHOLD = −9`, prédicat `motors.is_holding_pawn()`.
- **Lire une position de pince APRÈS stabilisation** (`motors.wait_until_settled`) — piège coûteux : la pince met bien plus longtemps que prévu à finir sa course. L'ancien `sleep(0.3)` la lisait **en plein mouvement** (−12,0° au lieu de −8,0° à vide), ce qui faisait passer une pince vide pour une prise réussie. Une seule lecture stable ne suffit pas non plus (−9,1° mesuré, à 0,1° du seuil) : le servo ralentit en fin de course, d'où `stable_readings=2` avec des lectures espacées de 0,1 s. Avec un cube la pince est bloquée donc immobile tout de suite — c'est le cas à vide qui exige l'attente.
- **Prise à vide = `PawnNotGrabbed`** : `play_pawn` réessaie `GRAB_ATTEMPTS` (3) fois avec une alerte sonore, ramène le bras en position de base, puis lève `PawnNotGrabbed`. Le launcher **garde le tour de Reachy** et réessaie. ⚠️ Ne jamais marquer la case quand la prise échoue : le plateau interne divergerait de la vision et l'humain serait accusé de tricher (partie annulée).
- **Fin de partie : bras au repos, couple coupé** — `GameSession.play_one_game()` termine toujours par `rest()`, y compris si la partie lève une exception (les moteurs ne doivent pas chauffer bras tendu). Trois pièges qui en découlent : ① couper le couple rend la tête molle, donc `rest()` appelle `invalidate_head_aim()` — sans quoi la partie suivante analyse avec la visée en cache d'une tête tombante (`reset()` n'invalide qu'**après** l'attente d'un plateau vide, trop tard) ; ② `wait_for_cooldown(move_to_rest=False)` quand le bras est déjà hors tension, sinon `goto_rest_position()` le réalimente pour tout le refroidissement ; ③ l'animation de veille pilote les antennes, donc `safe_turn_on('head')` avant `enter_sleep_mode()` sinon elle est silencieusement inerte.
- **Prise toujours en `grab_1`** : `play()` passe systématiquement `grab_index=1` — il n'y a pas la place d'aligner cinq cubes à côté du plateau, l'humain en redépose un au même endroit à chaque tour. `grab_2..5` restent supportés par `play_pawn` mais ne sont plus exercés par une partie (donc plus validés).
- **Modèles TFLite** : doivent être compilés **CPU**, pas EdgeTPU. Une erreur claire est levée sinon (`vision.py`).
- **NumPy < 2.0** requis pour la compatibilité TensorFlow training (voir `requirements-training.txt`).
- **Mode `--host localhost`** quand le code tourne sur le NUC du robot, IP distante sinon.
- Si le plateau bouge physiquement, il faut **à la fois** recalibrer (`config.py` via `calibrate_board.py`) **et** réenregistrer les fichiers `.npz` de `moves/` — 27 requis par le jeu, plus les 9 `put_N` intermédiaires créés automatiquement (voir `CHECKLIST_MOUVEMENTS.txt`).
- Réponses et logs du jeu en français — conserver cette langue dans les nouveaux messages utilisateur.
