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
# Enregistrer (mode compliant). Voir GUIDE_REENREGISTREMENT_MOUVEMENTS.md et CHECKLIST_MOUVEMENTS.txt
python scripts/moves/record_moves.py --interactive --host localhost
python scripts/moves/record_moves.py --name grab_1 --type position --host localhost
python scripts/moves/record_moves.py --name put_1 --type trajectory --duration 2.5 --host localhost
# Rejouer
python scripts/moves/test_recorded_moves.py --name grab_1 --host localhost
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
- `motors.py` — `safe_turn_on(reachy, part)` : activation du couple **sans à-coup** (source unique, importée par le jeu et les scripts `moves/`). Voir « Pièges ».
- `config.py` — **source unique** pour calibration (`BOARD_POSITION`, `BOARD_CASES`), constantes gripper (`GRIPPER_OPEN=-45`, `GRIPPER_CLOSED=-6`, en degrés, plus négatif = plus ouvert), seuils de détection, chemins modèles. `save_calibration()` réécrit le fichier via regex.
- `moves/__init__.py` — charge dynamiquement tous les `*.npz` du dossier en un dict `moves`. Définit `rest_pos` et `base_pos` (positions cibles joints en degrés).
- `game_launcher.py` — orchestration, gestion des relances après exception (sleep 5 s puis nouvelle partie).

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

- **`goto()` et `head.look_at()` du SDK 2021 sont BLOQUANTS** (ils ne rendent la main qu'à la fin du mouvement — docstring officielle : « This function will block until the movement is over »). ⚠️ **Ne jamais ajouter de `time.sleep(duration)` après un `goto`** : cela double le temps de chaque geste (régression de latence corrigée sur tout le code). Les seuls `sleep` légitimes sont les courtes stabilisations servo (ex. 0,3 s après la fermeture forcée du gripper, avant la lecture de `present_load`) et les balayages à 100 Hz par `goal_position`.
- **Sons en tâche de fond** : `behavior._sound_executor` (1 seul worker — le périphérique ALSA `hw:0,0` est exclusif, deux `mpg123` simultanés échoueraient). Le son de `thinking` est lancé en fond pour ne pas retarder le bras ; échec loggé par callback.
- **Joints en degrés** dans le SDK 2021 (pas radians). Antennes, bras, gripper.
- **Activation du couple : jamais `reachy.turn_on()` brut** — toujours `safe_turn_on()` (`reachy_tictactoe/motors.py`). Au `turn_on`, le registre `goal_position` contient encore la consigne du mouvement précédent et le moteur saute violemment vers cette vieille cible (« coup violent au début » historique). `safe_turn_on` synchronise `goal_position = present_position` (gripper **exclu** : `close_gripper()` sur-commande volontairement la consigne pour serrer — resynchroniser lâcherait le pion), attend 0,05 s (le flux de commandes ~100 Hz est asynchrone vs le RPC `turn_on`), puis active. Exception assumée : les scripts `calibration/` et `training/` (tête seule, sans dépendance au package) gardent `turn_on('head')` brut.
- **Trajectoires 100 Hz : pré-positionnement intégré** — `play_trajectory()` fait d'abord un `goto` doux (0,5 s) vers le premier point si le bras en est à plus de 3° : la première consigne streamée serait sinon un échelon brutal. Ne pas ré-ajouter de `goto` vers le premier point chez les appelants.
- **Limites articulaires (⚠️ enregistrements)** : en compliant on peut pousser le bras **au-delà des butées logicielles** à la main — l'encodeur lit la vraie position, mais **le contrôleur écrête au rejeu** et le bras rate sa cible en silence. Toujours valider un `.npz` contre les limites URDF du bras droit (degrés) : shoulder_pitch [−150, 90], shoulder_roll [−180, 10], **arm_yaw [−90, 90]** (le piège principal), elbow_pitch [−125, 0], forearm_yaw [−100, 100], wrist_pitch [−45, 45], wrist_roll [−35, 54.4], gripper [−68.8, 20]. Conséquence géométrique : les cases du plateau doivent rester **à droite de l'axe du robot** (y ≤ −0,03 m, repère x=avant/y=gauche), sinon `arm_yaw` > 90° est nécessaire et la case est physiquement injouable.
- **Activation gripper** : `self.reachy.r_arm.r_gripper.compliant = False` est appelé explicitement et vérifié dans `play_pawn` ; ne pas supposer qu'il reste actif.
- **Fermeture pince** : `play_pawn` ferme via `close_gripper()`, qui **force** `goal_position` à `GRIPPER_CLOSED` avec `torque_limit=100`, puis lit `present_load` (alerte loggée si `< 80` ⇒ prise probablement à vide). ⚠️ Ne pas remplacer par une fermeture progressive à seuil de charge bas : les pics transitoires de démarrage du moteur déclenchent la détection trop tôt et la pince s'arrête quasi ouverte sans attraper le cube (régression observée et corrigée).
- **Modèles TFLite** : doivent être compilés **CPU**, pas EdgeTPU. Une erreur claire est levée sinon (`vision.py`).
- **NumPy < 2.0** requis pour la compatibilité TensorFlow training (voir `requirements-training.txt`).
- **Mode `--host localhost`** quand le code tourne sur le NUC du robot, IP distante sinon.
- Si le plateau bouge physiquement, il faut **à la fois** recalibrer (`config.py` via `calibrate_board.py`) **et** réenregistrer les fichiers `.npz` de `moves/` — 27 requis par le jeu, plus les 9 `put_N` intermédiaires créés automatiquement (voir `CHECKLIST_MOUVEMENTS.txt`).
- Réponses et logs du jeu en français — conserver cette langue dans les nouveaux messages utilisateur.
