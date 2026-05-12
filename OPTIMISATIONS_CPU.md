# 💻 Plan d'optimisation de la charge CPU / RAM

> **Contexte** : Le NUC de Reachy (Intel Core mobile, ~8 Go RAM, pas de GPU) est limité.
> **Objectif** : Réduire la charge CPU/RAM pour libérer des marges, sans dégrader la fiabilité de la vision ni la réactivité du jeu.
>
> Voir aussi : [`OPTIMISATIONS_PERFORMANCES.md`](OPTIMISATIONS_PERFORMANCES.md) pour les optimisations de **temps** sur `play_pawn`.

---

## 📊 Où va le CPU actuellement (estimé)

| Poste | Charge estimée | Localisation |
|---|---|---|
| Inférence TFLite (10× par analyse : 9 cases + validité) | 🔥 Élevée | `vision.py` |
| Écriture `/tmp/snap.<rand>.jpg` à **chaque** analyse | 🔥 Élevée (I/O) | `tictactoe_playground.py` lignes 326–328 |
| `analyze_board` jusqu'à 10 Hz | Modérée | `tictactoe_playground.py` ligne 303 |
| `play_trajectory` à 100 Hz (boucle Python + `sleep(0.01)`) | Modérée (pic 100 % d'un cœur) | `tictactoe_playground.py` lignes 828–868 |
| Logs INFO verbeux (zzlog avec JSON) | Faible mais constante | partout |
| Affichage OpenCV redessiné à chaque tick | Faible | `tictactoe_playground.py` lignes 49–145 |
| Lecture températures Dynamixel (I²C) | Faible | `need_cooldown` ligne 950 |

---

## ✅ Liste des optimisations (par ordre d'impact estimé)

### 🥇 1. Activer XNNPACK + multi-thread sur TFLite

- **Statut** : ⬜ À faire
- **Priorité** : 🔴 Critique
- **Gain estimé** : **Inférence 2–3× plus rapide** (= charge CPU divisée d'autant pour le même throughput)
- **Risque** : 🟢 Nul
- **Fichier** : `reachy_tictactoe/vision.py` ligne ~64

**Aujourd'hui** :
```python
self.interpreter = tflite.Interpreter(model_path=model_path)
self.interpreter.allocate_tensors()
```

**Action** :
```python
import os
self.interpreter = tflite.Interpreter(
    model_path=model_path,
    num_threads=max(1, os.cpu_count() - 1),  # garde 1 cœur pour le reste
)
self.interpreter.allocate_tensors()
```

XNNPACK est activé par défaut dans `tflite-runtime ≥ 2.5`. Le passage à `num_threads > 1` suffit. Bench rapide à faire avant/après avec `time.time()` autour d'un `classify_with_image`.

---

### 🥈 2. Quantifier les modèles TFLite en INT8

- **Statut** : ⬜ À faire
- **Priorité** : 🔴 Critique
- **Gain estimé** : **CPU ÷ 2 à ÷ 4**, **RAM ÷ 4**, modèle ~4× plus petit
- **Risque** : 🟡 Moyen (perte de précision à valider, typiquement < 1 %)
- **Fichier** : `scripts/training/convert_to_tflite.py`

**Hypothèse** : les modèles `ttt-boxes.tflite` et `ttt-valid-board.tflite` sont en FP32.

**Action** : Modifier la conversion pour utiliser **post-training quantization** :
```python
converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
# Pour quantification INT8 complète (recommandé) :
converter.representative_dataset = representative_data_gen
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8
tflite_model = converter.convert()
```

**À valider** :
- Précision sur le jeu de test existant (`scripts/training/check_training_data.py`).
- Comparer taille des fichiers `.tflite` avant/après.
- Bench inférence sur le NUC.

---

### 🥉 3. Supprimer / contrôler l'écriture des snapshots de debug

- **Statut** : ⬜ À faire
- **Priorité** : 🟠 Haute
- **Gain estimé** : I/O disque ÷ 10+, économie SSD à long terme
- **Risque** : 🟢 Nul (juste un debug)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 325–328

**Problème actuel** : `cv.imwrite('/tmp/snap.<rand>.jpg', img)` à chaque appel d'`analyze_board`, soit jusqu'à 10/s. De plus, `np.random.randint(1000)` → collisions fréquentes, `/tmp` se remplit.

**Action — 3 options** :
- **A (recommandée)** : flag debug dans `config.py` (`DEBUG_SAVE_SNAPSHOTS = False`).
- **B** : un seul fichier écrasé `/tmp/snap.jpg`.
- **C** : ring buffer (`/tmp/snap_{i % 10}.jpg`) pour garder les 10 dernières.

---

### 4. Court-circuiter l'inférence si l'image est identique

- **Statut** : ⬜ À faire
- **Priorité** : 🟠 Haute
- **Gain estimé** : **70–80 % d'inférences évitées** en phase d'attente
- **Risque** : 🟡 Moyen (à valider — le seuil de similarité est critique)
- **Fichier** : `reachy_tictactoe/vision.py` (à wrapper avant `get_board_configuration`)

**Idée** : L'import `hashlib` déjà présent dans `vision.py` suggère que c'était l'intention initiale.

**Action** : Avant l'inférence, comparer la frame courante à la précédente via :
- Hash perceptuel (`imagehash` ou maison sur image downscale 8×8), **ou**
- `cv.absdiff` + `cv.mean` < seuil → identique.

Si identique → réutiliser le `board` précédent sans relancer TFLite.

```python
_last_frame_hash = None
_last_board = None

def get_board_configuration(img):
    global _last_frame_hash, _last_board
    # Downscale + hash rapide
    small = cv.resize(img, (32, 32))
    h = hashlib.md5(small.tobytes()).hexdigest()
    if h == _last_frame_hash and _last_board is not None:
        return _last_board
    # ... inférence normale ...
    _last_frame_hash = h
    _last_board = result
    return result
```

---

### 5. Augmenter `MAX_ANALYSIS_INTERVAL`

- **Statut** : ⬜ À faire
- **Priorité** : 🟡 Moyenne
- **Gain estimé** : Charge ÷ 2 à 3 en phase d'attente
- **Risque** : 🟢 Faible (réactivité légèrement dégradée, mais imperceptible)
- **Fichier** : `reachy_tictactoe/game_launcher.py` ligne 22

**Aujourd'hui** :
```python
MIN_ANALYSIS_INTERVAL = 0.1   # 100 ms
MAX_ANALYSIS_INTERVAL = 0.5   # 500 ms
```

**Action** : Passer à **1.0 s ou 1.5 s** en phase stable. L'humain pose une pièce en 2–3 s, donc une analyse toutes les 1–1.5 s reste largement suffisante. Idem `STABLE_THRESHOLD` peut passer de 3 à 2.

```python
MIN_ANALYSIS_INTERVAL = 0.2   # 200 ms (au lieu de 100 ms)
MAX_ANALYSIS_INTERVAL = 1.5   # 1.5 s (au lieu de 500 ms)
STABLE_THRESHOLD = 2
```

---

### 6. Réduire la résolution d'entrée des modèles

- **Statut** : ⬜ À faire
- **Priorité** : 🟡 Moyenne
- **Gain estimé** : **CPU × 2 à × 5** sur l'inférence
- **Risque** : 🟠 Élevé (nécessite ré-entraînement + validation)
- **Fichiers** : `scripts/training/train_models.py`, `scripts/training/convert_to_tflite.py`, `reachy_tictactoe/vision.py`

**Hypothèse** : Modèles entraînés en 224×224 (standard MobileNet).

**Action** : Ré-entraîner en 96×96 ou 128×128. Les classes (vide / cube / cylindre) sont visuellement très distinctes, la résolution réduite suffit largement.

**Workflow** :
1. Modifier `IMG_SIZE` dans `train_models.py`.
2. Ré-entraîner.
3. Convertir en TFLite.
4. Bench + validation sur dataset de test.

---

### 7. Logs INFO → WARNING en production

- **Statut** : ⬜ À faire
- **Priorité** : 🟡 Moyenne
- **Gain estimé** : Faible mais constant, économie d'écriture disque
- **Risque** : 🟢 Nul
- **Fichier** : `reachy_tictactoe/game_launcher.py` lignes 211–214

**Action** : Garder INFO **seulement** si `--log-file` est explicitement passé. Sinon, niveau WARNING par défaut.

```python
log_level = logging.INFO if args.log_file else logging.WARNING
logger = zzlog.setup(logger_root='', filename=args.log_file, level=log_level)
```

Bonus : ajouter un flag `--verbose` / `-v` pour forcer INFO sans fichier de log.

---

### 8. Ne redessiner l'affichage OpenCV que sur changement

- **Statut** : ⬜ À faire
- **Priorité** : 🟢 Basse
- **Gain estimé** : Faible (mais simple à faire)
- **Risque** : 🟢 Nul
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` `display_board` lignes 49–145

**Action** : Mémoriser le dernier `(board, current_player, winner)` rendu et skip tout le dessin si identique. Garder uniquement `cv.waitKey(1)` pour la responsivité de la fenêtre.

```python
def display_board(self, board, current_player=None, winner=None):
    state = (tuple(board), current_player, winner)
    if state == getattr(self, '_last_display_state', None):
        cv.waitKey(1)
        return
    self._last_display_state = state
    # ... dessin existant ...
```

---

### 9. Espacer `need_cooldown()`

- **Statut** : ⬜ À faire
- **Priorité** : 🟢 Très basse
- **Gain estimé** : Marginal
- **Risque** : 🟢 Nul
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` ligne 950 + `game_launcher.py` ligne 244

**Problème** : Lecture des températures Dynamixel via I²C — relativement lent et bloquant. Appelé après **chaque** partie.

**Action** : N'appeler que toutes les N parties (ex. tous les 3 jeux), ou seulement si la dernière partie a duré > X secondes. Pas critique vu la fréquence des appels.

---

### 10. Préchauffer le modèle quantifié au démarrage

- **Statut** : ⬜ À faire (dépend de #2)
- **Priorité** : 🟢 Basse
- **Gain estimé** : Latence du 1er coup
- **Risque** : 🟢 Nul
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` `_preload_resources` lignes 181–223

**Note** : Le warmup TFLite existe déjà — vérifier qu'il reste pertinent après quantification INT8 (le 1er appel peut être plus lent).

---

## 📈 Suivi des gains

| Optimisation | Gain estimé | Gain mesuré | Statut |
|---|---|---|---|
| 1. TFLite multi-thread | Inférence × 2–3 | _____ | ⬜ |
| 2. Quantification INT8 | CPU ÷ 2–4 | _____ | ⬜ |
| 3. Supprimer snapshots debug | I/O ÷ 10+ | _____ | ⬜ |
| 4. Cache inférence par hash | −70 % inférences | _____ | ⬜ |
| 5. Espacer la boucle d'analyse | Charge ÷ 2–3 | _____ | ⬜ |
| 6. Réduire résolution modèles | CPU × 2–5 | _____ | ⬜ |
| 7. Logs WARNING par défaut | Faible mais constant | _____ | ⬜ |
| 8. Affichage OpenCV conditionnel | Faible | _____ | ⬜ |
| 9. Espacer `need_cooldown` | Marginal | _____ | ⬜ |
| 10. Warmup modèle quantifié | Latence 1er coup | _____ | ⬜ |

**Objectif final** : Libérer **40–60 % de CPU** sur le NUC en phase d'attente, ouvrir la marge pour le parallélisme des optimisations de temps.

---

## 🔧 Méthodologie recommandée

1. **Mesurer la baseline** : `htop` / `top` pendant 10 min de jeu, noter %CPU moyen et pic.
2. **Démarrer par les quick wins** : optim #1 et #3 sont triviales et sans risque.
3. **Quantification (#2)** ensuite — gain massif mais demande validation sur dataset.
4. **Cache d'inférence (#4)** est un excellent ROI mais demande de calibrer le seuil de similarité.
5. **Tester chaque changement avec `htop`** + `time` autour d'`analyze_board`.
6. **Branche dédiée** : `perf/cpu-optimization`.

---

## 🔗 Combinaisons gagnantes

- **#1 + #2** : Inférence **× 4 à × 12** au total (multi-thread + INT8). C'est l'optimisation la plus rentable.
- **#3 + #4 + #5** : En phase d'attente, on passe de ~10 Hz d'analyses lourdes à ~1 Hz d'analyses légères. Énorme libération CPU.
- **#1 + #4** : Tellement plus rapide que la fréquence d'analyse peut rester élevée sans saturer.

---

## 📝 Notes / Observations

_(à remplir au fur et à mesure)_

```
Date : _______________
Baseline CPU : _______________ % moyen, _______________ % pic
Optimisation testée : _______________
CPU après : _______________ % moyen, _______________ % pic
Problèmes rencontrés : _______________
```

---

**Créé le** : 2026-05-11
