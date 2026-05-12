# 🚀 Plan d'optimisation des performances — `play_pawn`

> **Problème constaté** : Reachy met ~20 secondes pour poser une pièce.
> **Objectif** : Réduire à 6–8 secondes sans dégrader la fiabilité de la prise ni la précision de la pose.

---

## 📊 Budget temps actuel (estimé)

Mesures approximatives sur la séquence `play_pawn` dans `reachy_tictactoe/tictactoe_playground.py` :

| Étape | Durée | Localisation |
|---|---|---|
| `goto_base_position(2.0)` au début | ~2.0 s | ligne 540 |
| Activation gripper (3× `time.sleep`) | 0.25–0.45 s | lignes 526–534 |
| Approche `goto(grab, 1.0)` | 1.0 s | lignes 559–562 |
| Stabilisation après approche | 0.15 s | ligne 565 |
| Fermeture pince (2× consécutivement) | **~1.7 s** | lignes 574–590 |
| Animation antennes 45°/-45° | 1.0 s | lignes 593–600 |
| Pause avant lift | 0.1 s | ligne 615 |
| `goto(lift, 1.0)` | 1.0 s | lignes 618–622 |
| `goto(first_pos, 0.5)` | 0.5 s | ligne 635 |
| `play_trajectory(put)` (100 Hz) | 2.0–3.0 s | ligne 638 |
| `open_gripper` | 0.6 s | ligne 641 |
| `goto(back_upright, 1.0)` | 1.0 s | lignes 644–648 |
| Antennes retour à 0 | 1.0 s | lignes 651–658 |
| `goto_rest_position(2.0)` final | ~2.0 s | ligne 660 |
| **Total pion proche** | **~14–17 s** | |
| **+ passe `grab_3` intermédiaire si grab_index ≥ 4** | **+2 s** | lignes 543–548 |
| **Total pion lointain** | **~17–20 s** | |

---

## ✅ Liste des optimisations (par ordre d'impact estimé)

### 🥇 1. Vérifier si `goto_position` double l'attente

- **Statut** : ⬜ À faire
- **Priorité** : 🔴 Critique
- **Gain estimé** : **−6 à −8 s** (potentiellement la moitié du temps)
- **Risque** : Faible (vérification simple)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 779–784, 901–910, 918–923

**Hypothèse** : Dans `goto_position`, `close_gripper`, `open_gripper`, on appelle `goto(...)` *puis* `time.sleep(duration)`. Or `trajectory.goto` du SDK Reachy 2021 est **déjà bloquant par défaut**. Si confirmé, chaque appel met deux fois sa durée.

**Test à effectuer** :
```python
import time
from reachy_sdk import ReachySDK
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode

reachy = ReachySDK(host='localhost')
reachy.turn_on('r_arm')

t0 = time.time()
goto(
    goal_positions={reachy.r_arm.r_shoulder_pitch: 20},
    duration=2.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
print(f"Durée réelle de goto: {time.time() - t0:.2f}s")
# Si ≈ 2.0s → goto est bloquant → supprimer les time.sleep redondants
# Si ≈ 0.0s → goto est non bloquant → conserver les time.sleep
```

**Action si bloquant confirmé** :
- Supprimer le `time.sleep(duration)` ligne 784 (`goto_position`).
- Supprimer le `time.sleep(0.5)` ligne 906 (`close_gripper`).
- Supprimer le `time.sleep(0.3)` ligne 923 (`open_gripper`).

---

### 🥈 2. Paralléliser antennes + mouvements du bras

- **Statut** : ⬜ À faire
- **Priorité** : 🟠 Haute
- **Gain estimé** : **−2 s**
- **Risque** : Faible (le `ThreadPoolExecutor` est déjà en place dans `behavior.py`)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 593–600 et 651–658

**Actions** :
- Lancer le `goto` antennes (45°/-45°) dans un thread pendant que le bras exécute `lift` et `goto(first_pos)`.
- Lancer le `goto` antennes retour à 0 en parallèle de `goto(back_upright)` et `goto_rest_position`.
- Utiliser le `_executor` global de `behavior.py` ou un `Thread` simple.

---

### 🥉 3. Supprimer la double fermeture de la pince

- **Statut** : ⬜ À faire
- **Priorité** : 🟠 Haute
- **Gain estimé** : **−1 à −1.5 s**
- **Risque** : Moyen (à valider que la prise reste fiable)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 567–590 et 891–912

**Problème actuel** :
1. `r_gripper.goal_position = GRIPPER_CLOSED` + `sleep(0.5)` (ligne 574–575)
2. `self.close_gripper()` qui refait :
   - `goto(GRIPPER_CLOSED, duration=0.5)` (ligne 901)
   - `sleep(0.5)` (ligne 906)
   - `goal_position = GRIPPER_CLOSED` (ligne 909)
   - `sleep(0.15)` (ligne 910)

**Action** : Conserver une seule fermeture (~0.6 s) bien dimensionnée, garder le check `if actual_pos < -12` en filet de sécurité.

---

### 4. Réduire les durées des `goto` de transit

- **Statut** : ⬜ À faire
- **Priorité** : 🟡 Moyenne
- **Gain estimé** : **−1.5 à −2 s**
- **Risque** : Moyen (à valider sur le robot — risque de saccades)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 540, 660, 870–885

**Actions** :
- `goto_base_position()` : passer `duration` de 2.0 s → **1.2 s**
- `goto_rest_position()` : passer `duration` de 2.0 s → **1.2 s**
- Tester d'abord sur banc à vide avant intégration dans le jeu.

---

### 5. Pipeliner avec l'analyse du plateau

- **Statut** : ⬜ À faire
- **Priorité** : 🟡 Moyenne
- **Gain estimé** : **−1 s** sur le tour humain suivant
- **Risque** : Faible
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 644–660 + `analyze_board` ligne 303

**Action** : Pendant `goto_rest_position` final et le retour des antennes, démarrer dans un thread :
- `reachy.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)`
- (optionnel) première capture de frame

Au tour suivant, `analyze_board` n'a plus à attendre que la tête se positionne.

---

### 6. Supprimer le `goto(first_pos, 0.5)` avant `play_trajectory(put)`

- **Statut** : ⬜ À faire
- **Priorité** : 🟢 Basse
- **Gain estimé** : **−0.5 s**
- **Risque** : Moyen (peut créer un saccade au démarrage de la trajectoire `put`)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 627–635

**Options** :
- **Option A** : Supprimer `goto(first_pos, 0.5)` si les trajectoires `put_*` ont été enregistrées depuis la fin de `lift` (premier point déjà proche).
- **Option B** : Absorber le `first_pos` dans la fin du `lift` (one-shot direct).

**À vérifier** : Ouvrir un `.npz` et inspecter les premiers points pour voir s'ils sont proches de la position post-`lift`.

---

### 7. Sous-échantillonner / accélérer `play_trajectory`

- **Statut** : ⬜ À faire
- **Priorité** : 🟢 Basse
- **Gain estimé** : **−1 à −1.5 s**
- **Risque** : Élevé (peut dégrader la fluidité visuelle ou la précision de pose)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` lignes 828–868

**Options** :
- **Option A** : Lire un point sur deux (50 Hz au lieu de 100 Hz) → conserver `time.sleep(0.02)`.
- **Option B** : Garder 100 Hz mais consommer 2 points par tick.
- ⚠️ `time.sleep(0.005)` n'est pas fiable en Python (granularité OS).

**À tester d'abord sur banc à vide.**

---

### 8. Réévaluer les sleeps de stabilisation

- **Statut** : ⬜ À faire
- **Priorité** : 🟢 Basse
- **Gain estimé** : **−0.3 à −0.5 s** cumulés
- **Risque** : Faible (peut être supprimé un par un)
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` partout

**Sleeps à reconsidérer** :
| Ligne | Sleep | Justification actuelle | Probablement supprimable ? |
|---|---|---|---|
| 307 | 0.05 s | après `turn_on('head')` | ✅ Oui |
| 312 | 0.1 s | après `look_at` | ❌ Non (le look_at sleep déjà ?) |
| 526 | 0.15 s | avant gripper | ✅ Oui (probablement) |
| 528 | 0.1 s | après `compliant=False` | ✅ Oui |
| 565 | 0.15 s | stabilisation grab | ⚠️ À tester |
| 615 | 0.1 s | avant lift | ✅ Oui |
| 873 | 0.05 s | après `turn_on('r_arm')` | ✅ Oui |
| 885 | 0.05 s | stabilisation rest | ✅ Oui |

Ces marges étaient probablement nécessaires avec le SDK 2019 ; sur le SDK 2021, beaucoup sont du folklore.

---

### 9. Garder le bras en `base_pos` entre coups successifs de Reachy

- **Statut** : ⬜ À faire
- **Priorité** : 🟢 Très basse
- **Gain estimé** : **−2 s** (mais cas rare au morpion)
- **Risque** : Faible
- **Fichier** : `reachy_tictactoe/tictactoe_playground.py` ligne 660

**Action** : Si Reachy enchaîne plusieurs coups d'affilée (rare au TicTacToe), éviter le `rest → base` redondant entre les deux. Pas prioritaire vu le contexte du jeu.

---

## 📈 Suivi des gains

| Optimisation | Gain estimé | Gain mesuré | Statut |
|---|---|---|---|
| 1. Suppression double-attente | −6 à −8 s | _____ | ⬜ |
| 2. Antennes en parallèle | −2 s | _____ | ⬜ |
| 3. Suppression double fermeture | −1 à −1.5 s | _____ | ⬜ |
| 4. Durées `goto` réduites | −1.5 à −2 s | _____ | ⬜ |
| 5. Pipeline analyse plateau | −1 s | _____ | ⬜ |
| 6. Suppression `first_pos` | −0.5 s | _____ | ⬜ |
| 7. Trajectoire 50 Hz | −1 à −1.5 s | _____ | ⬜ |
| 8. Sleeps de stabilisation | −0.3 à −0.5 s | _____ | ⬜ |
| 9. Skip rest entre coups | −2 s (rare) | _____ | ⬜ |
| **TOTAL** | **−13 à −17 s** | _____ | |

**Objectif final** : Passer de ~17 s à **6–8 s** par pose.

---

## 🔧 Méthodologie recommandée

1. **Mesurer avant** : ajouter un chrono autour de `play_pawn` pour avoir une baseline précise (le total estimé ci-dessus est approximatif).
2. **Tester l'optimisation #1 en isolation** : c'est 5 minutes et potentiellement la moitié du temps gagnée.
3. **Faire les optimisations une par une**, en mesurant après chaque changement.
4. **Tester sur le robot après chaque batch** : vérifier que la fiabilité de la prise et la précision de pose ne sont pas dégradées.
5. **Garder une branche `main` propre** : faire les optimisations dans une branche dédiée (`perf/play-pawn-speedup`).

---

## 📝 Notes / Observations

_(à remplir au fur et à mesure)_

```
Date : _______________
Optimisation testée : _______________
Résultat : _______________
Problèmes rencontrés : _______________
```

---

**Créé le** : 2026-05-11
