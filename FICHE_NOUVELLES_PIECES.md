# Fiche — Nouvelles pièces + nouveau plateau

> Procédure complète à suivre après réception de nouvelles pièces (cubes/cylindres) et d'un nouveau plateau.
> Les modèles de vision (`ttt-boxes.tflite` et `ttt-valid-board.tflite`) doivent être recréés car les pions et le plateau ont changé.

---

## Pré-requis

```bash
# Sur le PC de dev OU sur le NUC du robot
cd /home/mia/Bureau/Reachy-2021-TicTacToe
source venv/bin/activate
```

`--host localhost` si tu lances depuis le NUC du robot.
`--host 10.18.11.62` (ou l'IP actuelle) si tu lances depuis ton PC.

> Dans la suite, remplace `<HOST>` par `localhost` ou l'IP du robot selon ton cas.

---

## ÉTAPE 1 — Calibration du plateau

Le nouveau plateau n'est pas au même endroit que l'ancien. **À faire en premier**, avant tout le reste.

```bash
# 1.1 Calibrer les 4 coins du plateau
python scripts/calibration/calibrate_board.py --host <HOST>

# 1.2 Vérifier visuellement que la grille est bien détectée
python scripts/calibration/check_calibrate_board.py --host <HOST>

# 1.3 Vérifier que les 9 cases sont bien découpées
python scripts/calibration/check_calibrate_cases.py --host <HOST>

# 1.4 (optionnel) Inspecter le résultat dans config.py
python scripts/utils/show_config.py
```

✅ La calibration doit être validée avant de passer à l'étape suivante. Les cases doivent toutes contenir une zone propre du plateau.

---

## ÉTAPE 2 — Tester les mouvements existants

Avant de réenregistrer, vérifie si les mouvements actuels fonctionnent encore avec la nouvelle position du plateau et les nouvelles pièces.

```bash
# 2.1 Tester un mouvement précis (ex : grab_1)
python scripts/moves/test_recorded_moves.py --name grab_1 --host <HOST>

# 2.2 Tester TOUS les mouvements à la suite
python scripts/moves/test_recorded_moves.py --all --host <HOST>

# 2.3 Tester une séquence ciblée (ex : prendre pion 1 et le poser dans la case 1)
python scripts/moves/test_recorded_moves.py --sequence grab_1 lift put_1_smooth_10_kp back_1_upright --host <HOST>
```

### Si TOUS les mouvements sont OK
→ Passe directement à l'**Étape 4** (création des modèles de vision).

### Si certains mouvements échouent (collision, pion mal saisi, mauvaise pose)
→ Passe à l'**Étape 3** (réenregistrement).

---

## ÉTAPE 3 — Réenregistrer les mouvements (si nécessaire)

Voir aussi `GUIDE_REENREGISTREMENT_MOUVEMENTS.md` et `CHECKLIST_MOUVEMENTS.txt`.

```bash
# 3.1 Mode interactif (recommandé pour tout réenregistrer)
python scripts/moves/record_moves.py --interactive --host <HOST>

# 3.2 OU mode ciblé : enregistrer un mouvement précis
# Position (un point unique) :
python scripts/moves/record_moves.py --name grab_1 --type position --host <HOST>

# Trajectoire (séquence enregistrée à 100 Hz) :
python scripts/moves/record_moves.py --name put_1 --type trajectory --duration 2.5 --host <HOST>
```

Liste des 29 fichiers à produire (voir `CHECKLIST_MOUVEMENTS.txt`) :
- `grab_1` à `grab_5` (positions)
- `lift` (position)
- `put_1_smooth_10_kp` à `put_9_smooth_10_kp` (trajectoires)
- `back_1_upright` à `back_9_upright` (positions/trajectoires)
- `back_to_back`, `back_rest`, `shuffle-board` (transitions)
- `my-turn`, `your-turn` (animations)

```bash
# 3.3 Rejouer pour valider chaque enregistrement
python scripts/moves/test_recorded_moves.py --name <nom> --host <HOST>

# 3.4 Quand tout est OK, retester la totalité
python scripts/moves/test_recorded_moves.py --all --host <HOST>
```

---

## ÉTAPE 4 — Créer le modèle `ttt-boxes` (cubes / cylindres / vides)

Ce modèle classe chacune des 9 cases en `empty`, `cube` (Reachy) ou `cylinder` (humain).
Comme tu as **de nouvelles pièces**, ce modèle DOIT être recréé.

### 4.1 Collecter les images

```bash
# Cases vides — viser 50–150 images
python scripts/training/collect_boxes_images.py --host <HOST> --class empty --target 100

# Cases avec un CUBE (pièce Reachy) — viser 50–150 images
python scripts/training/collect_boxes_images.py --host <HOST> --class cube --target 100

# Cases avec un CYLINDRE (pièce humain) — viser 50–150 images
python scripts/training/collect_boxes_images.py --host <HOST> --class cylinder --target 100
```

💡 Varie les positions des pièces dans la case, les éclairages, et fais bouger très légèrement le plateau entre captures pour rendre le modèle robuste.

### 4.2 Vérifier le jeu de données

```bash
python scripts/training/check_training_data.py
```

Doit indiquer environ le même nombre d'images dans chaque classe et ≥ 100 par classe.

### 4.3 Entraîner le modèle

```bash
# Entraîner uniquement boxes
python scripts/training/train_models.py --model boxes --epochs 15
```

Le fichier `.h5` est sauvegardé dans `models/` (ou équivalent — voir le script).

### 4.4 Convertir en TFLite

```bash
python scripts/training/convert_to_tflite.py --model boxes
```

Produit `reachy_tictactoe/models/ttt-boxes.tflite` (le runtime). L'ancien fichier est sauvegardé en backup.

---

## ÉTAPE 5 — Créer le modèle `ttt-valid-board` (plateau valide / invalide)

Ce modèle filtre les images de plateau bruitées (main qui passe, plateau bougé, etc.). Comme tu as **un nouveau plateau**, ce modèle DOIT aussi être recréé.

### 5.1 Collecter les images

```bash
# Plateau VALIDE (plateau propre, bien cadré) — viser 150 images
python scripts/training/collect_valid_board_images.py --host <HOST> --class valid --target 150

# Plateau INVALIDE (main devant, plateau de travers, flou, etc.) — viser 150 images
python scripts/training/collect_valid_board_images.py --host <HOST> --class invalid --target 150
```

💡 Pour les images `invalid` : passe la main devant, déplace le plateau, mets un objet dessus, bouge brusquement la tête de Reachy.

### 5.2 Vérifier

```bash
python scripts/training/check_training_data.py
```

### 5.3 Entraîner

```bash
python scripts/training/train_models.py --model valid-board --epochs 15
```

### 5.4 Convertir en TFLite

```bash
python scripts/training/convert_to_tflite.py --model valid-board
```

Produit `reachy_tictactoe/models/ttt-valid-board.tflite`.

---

## ÉTAPE 6 — Entraîner les DEUX modèles en une fois (alternative)

Si les images sont déjà collectées pour les deux modèles, tu peux tout faire en un coup :

```bash
# Entraîner tout
python scripts/training/train_models.py --model all --epochs 15

# Convertir tout
python scripts/training/convert_to_tflite.py --model all
```

---

## ÉTAPE 7 — Lancer une partie de test

```bash
# Lancement standard
python -m reachy_tictactoe.game_launcher --host <HOST>

# Avec log fichier (très utile pour diagnostiquer)
python -m reachy_tictactoe.game_launcher --host <HOST> --log-file /tmp/tictactoe.log

# Via entry point installé
reachy-tictactoe --host <HOST>
```

### Points à vérifier pendant la partie de test

- [ ] Reachy détecte correctement le plateau vide au démarrage
- [ ] Le `coin_flip` se déroule bien
- [ ] Reachy attrape proprement ses cubes (les 5 pions)
- [ ] Les 9 cases de pose fonctionnent sans collision
- [ ] La détection des cylindres posés par l'humain est fiable
- [ ] Pas de fausse détection de triche
- [ ] La célébration / défaite / égalité se déclenche correctement
- [ ] Pas d'alerte thermique (50 °C)

---

## Récapitulatif rapide (ordre d'exécution)

```bash
# 0. Setup
cd /home/mia/Bureau/Reachy-2021-TicTacToe && source venv/bin/activate

# 1. Calibration plateau
python scripts/calibration/calibrate_board.py --host <HOST>
python scripts/calibration/check_calibrate_board.py --host <HOST>
python scripts/calibration/check_calibrate_cases.py --host <HOST>

# 2. Test mouvements existants
python scripts/moves/test_recorded_moves.py --all --host <HOST>

# 3. (si nécessaire) Réenregistrer les mouvements
python scripts/moves/record_moves.py --interactive --host <HOST>

# 4. Modèle ttt-boxes
python scripts/training/collect_boxes_images.py --host <HOST> --class empty    --target 100
python scripts/training/collect_boxes_images.py --host <HOST> --class cube     --target 100
python scripts/training/collect_boxes_images.py --host <HOST> --class cylinder --target 100

# 5. Modèle ttt-valid-board
python scripts/training/collect_valid_board_images.py --host <HOST> --class valid   --target 150
python scripts/training/collect_valid_board_images.py --host <HOST> --class invalid --target 150

# 6. Vérification + entraînement + conversion
python scripts/training/check_training_data.py
python scripts/training/train_models.py --model all --epochs 15
python scripts/training/convert_to_tflite.py --model all

# 7. Partie de test
python -m reachy_tictactoe.game_launcher --host <HOST> --log-file /tmp/tictactoe.log
```

---

## Notes

- ⚠️ Convention pièces : **humain = cylindres**, **Reachy = cubes** (inversion vs code original Pollen 2019).
- ⚠️ Les modèles TFLite doivent être compilés **CPU** (pas EdgeTPU).
- ⚠️ Si le plateau bouge physiquement entre deux étapes, il faut TOUT refaire (calibration + mouvements + modèles).
- Sauvegarde tes anciens modèles `.tflite` avant de les écraser (le script `convert_to_tflite.py` le fait normalement, mais double-check).
- Date de création de la fiche : 2026-05-12
