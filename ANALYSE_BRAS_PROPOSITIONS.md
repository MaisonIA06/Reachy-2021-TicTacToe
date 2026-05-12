# Analyse du contrôle du bras + propositions d'amélioration

> Document d'analyse du système actuel de déplacement du bras de Reachy dans le projet TicTacToe,
> avec propositions d'amélioration pour résoudre les problèmes de **précision** et de **tenue du cube**.
> Date : 2026-05-12

---

## 1. Comment fonctionne le système actuel

### 1.1 Vue d'ensemble

Le bras de Reachy est contrôlé entièrement en **espace articulaire** (joint space), avec des positions enregistrées **manuellement** par "kinesthetic teaching" (apprentissage par démonstration : on désactive les moteurs, on bouge le bras à la main, on capture).

**Aucune cinématique inverse (IK)** n'est utilisée dans le code actuel. Tout repose sur des fichiers `.npz` qui contiennent des séquences d'angles articulaires (en degrés).

### 1.2 Pipeline d'enregistrement (`scripts/moves/record_moves.py`)

```
1. reachy.turn_off('r_arm')           → mode compliant (moteurs OFF)
2. L'utilisateur bouge le bras à la main jusqu'à la position désirée
3. Pour chaque joint des 8 (7 bras + gripper) :
     position_deg = joint.present_position    → angle lu via encodeur Dynamixel
4. Sauvegarde dans un .npz :
     - "position" : un seul point → dict {joint_name: angle}
     - "trajectory" : séquence à 100 Hz → dict {joint_name: array[N]}
```

**Joints enregistrés** :
- `r_shoulder_pitch`, `r_shoulder_roll`, `r_arm_yaw` (épaule)
- `r_elbow_pitch` (coude)
- `r_forearm_yaw`, `r_wrist_pitch`, `r_wrist_roll` (poignet)
- `r_gripper` (pince)

### 1.3 Pipeline de replay (`tictactoe_playground.py`)

Deux modes selon le type de mouvement :

**A. Position simple (`goto_position`, ligne 755)**
```python
goto(
    goal_positions={joint_obj: pos for ...},
    duration=2.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
time.sleep(duration)
```
Le SDK calcule une **interpolation minimum-jerk** (lisse, sans à-coups) entre la position actuelle et la cible, sur la durée demandée. Utilisé pour `grab_X`, `lift`, `back_X`, `rest_pos`, `base_pos`.

**B. Trajectoire (`play_trajectory`, ligne 828)**
```python
for i in range(num_points):
    for joint_obj, traj in adapted_traj.items():
        joint_obj.goal_position = traj[i]
    time.sleep(0.01)   # 100 Hz
```
Boucle Python qui écrit directement `goal_position` joint par joint, à 100 Hz, en suivant la trajectoire brute enregistrée. Utilisé pour `put_X_smooth_10_kp`, `shuffle-board`, `my-turn`, `your-turn`.

### 1.4 Contrôle du gripper (`tictactoe_playground.py`)

```python
self.reachy.r_arm.r_gripper.compliant = False          # activer le moteur
self.reachy.r_arm.r_gripper.torque_limit = 100         # limite de couple
self.reachy.r_arm.r_gripper.goal_position = GRIPPER_CLOSED   # -6° (fermé)
time.sleep(0.5)
```

**Constantes** (`config.py`) :
```
GRIPPER_OPEN   = -45°    # complètement ouvert
GRIPPER_CLOSED = -6°     # fermé pour tenir un pion
```

Le gripper est un servo Dynamixel asservi **en position uniquement** : on lui dit "va à -6°", il y va et reste à cet angle. Il n'y a **pas de feedback de force** dans le code actuel.

Pour s'assurer que la pince est bien fermée, le code fait :
- une première fermeture rapide (`goal_position = -6` + sleep)
- une vérification de la position actuelle (`present_position`)
- une seconde fermeture forcée si `present_position < -12`

---

## 2. Pourquoi c'est imprécis

### 2.1 Problèmes structurels du joint-space teaching

| Cause | Conséquence |
|---|---|
| **Mode compliant + gravité** | Quand on lâche le bras, la gravité tire les segments vers le bas. La position "où j'ai senti que c'était bien" n'est pas exactement la position des encodeurs. |
| **Jeu mécanique** | Les engrenages des Dynamixel ont un jeu (~0.5°). Le sens du dernier mouvement avant l'enregistrement biaise la position lue. |
| **Bruit du présent_position** | Les encodeurs ont une résolution finie. Une seule lecture peut être bruitée. |
| **Pas de moyenne temporelle** | Le code lit `present_position` UNE seule fois (`record_moves.py:64`). Pas de filtrage. |
| **Espace articulaire = fragile** | Si le plateau bouge de 5 mm, **tous** les `.npz` sont invalides. Pas de moyen simple d'ajuster. |
| **Trajectoires enregistrées à la main** | Si la main de l'opérateur tremble, la trajectoire `put_X` tremble aussi. Pas de lissage post-enregistrement. |

### 2.2 Problèmes du replay

| Cause | Conséquence |
|---|---|
| **100 Hz via `time.sleep(0.01)`** | Python sur Linux non-RT a une granularité de ~5-10 ms. La fréquence réelle peut varier entre 60 et 110 Hz selon la charge. |
| **Pas de PID adapté à la charge** | Le bras a une dynamique différente avec/sans pion (inertie + couple). Le gain proportionnel des Dynamixel reste constant. |
| **Discontinuité goto → trajectoire** | Au début de `play_trajectory`, on saute brusquement du goto `first_pos` au premier point de la trajectoire (`goto(first_pos, 0.5)` puis attaque directe). |

### 2.3 Problèmes spécifiques du gripper (tenue du cube)

| Cause | Conséquence |
|---|---|
| **Asservissement en position uniquement** | Le moteur essaie d'aller à -6°, peu importe si un cube est entre les mors ou pas. S'il bloque sur le cube : tension constante mais limitée par `torque_limit`. |
| **`torque_limit = 100`** | Sur 1024 max des Dynamixel MX, c'est ~10 % du couple max. Probablement **trop faible** pour serrer fort. Si le cube est lisse, ça glisse. |
| **`GRIPPER_CLOSED = -6` figé** | Cette valeur a été calibrée pour l'ancien pion. Avec un nouveau cube de taille différente, l'angle optimal change. |
| **Pas de détection de saisie** | Le code ne lit jamais `present_load` ou `present_current` pour vérifier qu'un objet est réellement entre les mors. Si le cube tombe, le code ne le sait pas. |
| **Matériau des mors** | Reachy V1 gripper d'origine est un plastique relativement lisse. Sans grip antidérapant, un cube de bois ou plastique poli glisse facilement. |

---

## 3. Propositions d'amélioration (par effort / impact)

### Niveau 1 — Quick wins gripper (effort : faible, impact : élevé sur la tenue)

C'est ici que tu auras le plus de gains rapides sur le problème "tient mal le cube".

#### 1.1 Augmenter `torque_limit`

Actuellement `torque_limit = 100`. Les Dynamixel MX-28 / MX-64 acceptent jusqu'à **1023**. Tester progressivement :
```python
self.reachy.r_arm.r_gripper.torque_limit = 300  # puis 500, 700
```
À surveiller : surchauffe du moteur si on serre fort en permanence.

#### 1.2 Recalibrer `GRIPPER_CLOSED` pour le nouveau cube

L'angle optimal est celui où **le cube est juste serré** sans que le moteur soit en survitesse. Procédure :
1. Mesurer la largeur du nouveau cube au pied à coulisse.
2. Mode compliant + placer le cube entre les mors + fermer manuellement jusqu'à serrage.
3. Lire `present_position` → c'est ton nouveau `GRIPPER_CLOSED`.
4. Mettre à jour `config.py`.

#### 1.3 Ajouter une grip surface anti-dérapante

Solution mécanique simple : colle un **patch de silicone, caoutchouc fin ou gommettes anti-glisse** sur la face intérieure des mors. Souvent c'est le plus gros gain et c'est gratuit.

#### 1.4 Fermeture par détection de blocage (stall detection)

Au lieu d'un angle final fixe, faire une fermeture progressive qui s'arrête quand le moteur force :

```python
def close_gripper_with_stall_detection(self, max_torque_load=150):
    g = self.reachy.r_arm.r_gripper
    g.compliant = False
    g.torque_limit = 500

    # Fermer progressivement
    for target in range(int(g.present_position), -10, -1):  # ouvert → fermé
        g.goal_position = target
        time.sleep(0.05)
        # present_load est en pourcentage signé
        if abs(g.present_load) > max_torque_load:
            logger.info(f'Cube détecté à {target}° (load={g.present_load:.0f})')
            return True   # cube saisi
    logger.warning('Aucun cube détecté (pince fermée complètement)')
    return False
```

Avantages :
- Marche avec n'importe quelle taille de cube
- On sait si le cube a bien été saisi
- Pas de risque de "écraser" un cube trop grand

---

### Niveau 2 — Améliorer la qualité de l'enregistrement (effort : moyen)

#### 2.1 Moyenne sur plusieurs lectures

Modifier `record_moves.py` : au lieu de lire `present_position` une fois, lire **10 fois sur 0.5 s** et moyenner. Réduit le bruit d'encodeur.

```python
def get_current_positions_averaged(self, n_samples=10, delay=0.05):
    samples = {j: [] for j in self.right_arm_joints}
    for _ in range(n_samples):
        for joint_name in self.right_arm_joints:
            joint = getattr(self.reachy.r_arm, joint_name)
            samples[joint_name].append(joint.present_position)
        time.sleep(delay)
    return {f'r_arm.{j}': np.mean(v) for j, v in samples.items()}
```

#### 2.2 Compensation de gravité pendant l'enregistrement

Reachy 2021 supporte un mode "compliant avec gravity compensation" : les moteurs ne forcent pas mais compensent la gravité, donc le bras reste où tu le poses (au lieu de tomber doucement).

Vérifier si dispo dans ton SDK. Sinon, alternative : enregistrer avec le bras **soutenu par la main** au moment précis du clic d'enregistrement.

#### 2.3 Lissage des trajectoires post-enregistrement

Filtrer les `.npz` de trajectoires avant utilisation avec un filtre **Savitzky-Golay** ou un **B-spline** :

```python
from scipy.signal import savgol_filter

def smooth_trajectory(npz_path, window=21, polyorder=3):
    data = dict(np.load(npz_path))
    for joint, traj in data.items():
        if 'gripper' in joint.lower():
            continue   # ne pas lisser le gripper (changements brusques)
        data[joint] = savgol_filter(traj, window, polyorder)
    np.savez(npz_path, **data)
```

À faire une fois après chaque session d'enregistrement.

---

### Niveau 3 — Passage en espace cartésien via cinématique inverse (effort : élevé, impact : très élevé sur la robustesse)

**C'est le changement le plus important pour la précision.**

#### 3.1 Principe

Au lieu d'enregistrer des angles articulaires, on **enregistre la position 3D et l'orientation** du bout du bras (l'effecteur, soit ici le centre du gripper). Le SDK Reachy 2021 expose :

```python
# Position actuelle du end-effector (matrice 4x4)
current_pose = self.reachy.r_arm.forward_kinematics()

# Calcul des angles articulaires pour atteindre une pose cible
joint_solution = self.reachy.r_arm.inverse_kinematics(target_pose)
```

Documentation : voir `reachy_kinematics` (ROS package) et l'API gRPC `ComputeArmIK`/`ComputeArmFK` du SDK.

#### 3.2 Avantages massifs pour TicTacToe

- **Si le plateau bouge de 1 cm**, il suffit d'ajouter un offset cartésien aux 9 poses des cases, **pas de réenregistrement**.
- On peut **générer les 9 cases programmatiquement** à partir de la calibration plateau (qui est déjà connue dans `config.py`).
- On peut **générer les 5 grab_X** programmatiquement à partir d'une seule position de référence.
- Les trajectoires `lift` / `back` deviennent triviales : approche +10 cm en Z.

#### 3.3 Schéma d'architecture cible

```
┌────────────────────────────────────────────────────┐
│ Position 3D du plateau (config.py — cartésien)     │
│   board_origin = (x0, y0, z0)                       │
│   case_size    = 0.05  (5 cm)                       │
└──────────────────┬─────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────┐
│ Calcul des 9 poses (case_pose_1 … case_pose_9)     │
│   = board_origin + offsets_3D[index]                │
└──────────────────┬─────────────────────────────────┘
                   │ IK
                   ▼
┌────────────────────────────────────────────────────┐
│ joint_positions = r_arm.inverse_kinematics(pose)   │
└──────────────────┬─────────────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────────────┐
│ goto(joint_positions, duration=1.5)                 │
└────────────────────────────────────────────────────┘
```

#### 3.4 Étapes de migration progressives

1. **Garder les `grab_X` enregistrés** (les pions ont des positions fixes, c'est OK)
2. **Migrer juste les 9 cases en IK** :
   - Enregistrer une seule fois la pose de la case 5 (centre) en cartésien
   - Générer les 8 autres par offset (±5 cm en X et Y)
   - Générer les trajectoires de pose : `approach_above → descend → release → retreat`
3. **Migrer `lift` et `back`** : juste un offset Z de +10 cm depuis la pose courante
4. **Optionnel : migrer les `grab_X` aussi** quand tout est validé

---

### Niveau 4 — Approche programmatique pure (effort : élevé, idéal long terme)

Aller au bout : **zéro fichier `.npz` enregistré**, tout calculé à partir d'un modèle de scène.

**Modèle de scène** (à mettre dans `config.py`) :
```python
PIECES_POSITIONS = [           # 5 cubes alignés à droite du plateau
    (0.55, -0.25, -0.05),
    (0.55, -0.20, -0.05),
    ...
]

BOARD_ORIGIN = (0.40, 0.00, -0.10)   # coin haut-gauche du plateau
CASE_OFFSET  = 0.06                   # 6 cm entre cases
```

**Génération automatique des séquences** :
```python
def play_pawn_cartesian(self, pawn_idx, case_idx):
    pawn_pose  = pose_from(PIECES_POSITIONS[pawn_idx-1], gripper_orient='down')
    case_pose  = pose_from(case_position(case_idx),      gripper_orient='down')

    self.move_to(above(pawn_pose, dz=+0.05))     # approche
    self.move_to(pawn_pose)                       # descente
    self.close_gripper_with_stall_detection()    # saisie
    self.move_to(above(pawn_pose, dz=+0.10))     # lever
    self.move_to(above(case_pose, dz=+0.10))     # transit
    self.move_to(case_pose)                       # descente case
    self.open_gripper()                           # lâcher
    self.move_to(above(case_pose, dz=+0.10))     # remontée
    self.goto_rest_position()
```

Avantages : **zéro maintenance** quand le plateau bouge. Tu changes 3 valeurs dans `config.py` et c'est fini.

Inconvénient : les mouvements sont "robotiques" (plus rigides), moins "naturels" que des trajectoires enregistrées par un humain.

---

### Niveau 5 — Asservissement visuel + force (effort : très élevé, projet de R&D)

Pour aller au-delà :

- **Visual servoing pour la saisie** : avant chaque `grab_X`, détecter la position exacte du cube via la caméra (carrés rouges/bleus à détecter par couleur ou modèle), corriger en temps réel l'approche.
- **Force feedback continu** : pendant `play_trajectory`, surveiller `present_load` du gripper. Si la charge tombe brusquement → le cube est tombé → recommencer la prise.
- **Capteur de force du gripper** : Reachy 2021 expose `force_gripper` via les services ROS. À investiguer si exposé dans le SDK Python (sinon passer par gRPC direct).

---

## 4. Recommandation prioritaire pour ton cas

Voici ce que je ferais dans l'ordre, avec les gains attendus :

| # | Action | Effort | Impact "tient mal le cube" | Impact "imprécis" |
|---|--------|--------|----------------------------|-------------------|
| 1 | Patch antidérapant sur les mors | 5 min | 🟢🟢🟢 | — |
| 2 | Recalibrer `GRIPPER_CLOSED` pour le nouveau cube | 10 min | 🟢🟢🟢 | — |
| 3 | Augmenter `torque_limit` à 300-500 | 5 min | 🟢🟢 | — |
| 4 | Fermeture par stall detection (`present_load`) | 1-2 h | 🟢🟢🟢 | 🟢 |
| 5 | Moyenne sur 10 lectures dans `record_moves.py` | 30 min | — | 🟢🟢 |
| 6 | Lissage post-enregistrement des trajectoires | 1 h | — | 🟢🟢 |
| 7 | Migration IK des 9 cases (Niveau 3) | 1-2 jours | 🟢 | 🟢🟢🟢 |
| 8 | Approche programmatique pure (Niveau 4) | 3-5 jours | 🟢 | 🟢🟢🟢 |

**Si tu n'as qu'une heure** : fais les actions 1, 2, 3. C'est probablement 80 % du problème de tenue résolu.

**Si tu veux investir** : ajoute l'action 4 (stall detection), c'est élégant et rend le système robuste à tout changement de pion.

**Pour vraiment changer de méthode** : actions 7 ou 8 — passer en cartésien via IK transforme le projet et le rend beaucoup plus pérenne.

---

## 5. Pistes complémentaires à explorer

- **Compliance dynamique** : passer en mode "compliant" sur certains joints pendant la descente vers le pion → le bras "s'adapte" mécaniquement si la hauteur est légèrement off (mais nécessite tests).
- **Multi-tentative** : si la stall detection ne détecte rien → réessayer une fois avec un offset Z plus bas.
- **Logging des échecs de prise** : sauvegarder l'image caméra + `present_load` à chaque grab pour analyser après coup.

---

## Sources

- [Master Reachy 2 Arm Kinematics: Coordinate Systems, Forward and Inverse Kinematics](https://docs.pollen-robotics.com/developing-with-reachy-2/basics/4-use-arm-kinematics/) — Documentation officielle FK/IK
- [pollen-robotics/reachy_kinematics (GitHub)](https://github.com/pollen-robotics/reachy_kinematics) — Package ROS2 FK/IK Reachy 2021
- [pollen-robotics/reachy-sdk (GitHub)](https://github.com/pollen-robotics/reachy-sdk) — SDK Python officiel
- [pollen-robotics/reachy_controllers (GitHub)](https://github.com/pollen-robotics/reachy_controllers) — Contrôleurs ROS2 (force sensor exposé)
- [Reachy 2021 — Overall presentation](https://pollen-robotics.github.io/reachy-2021-docs/advanced/software/presentation/) — Architecture logicielle
- [Dynamixel — meaning of max_torque, torque_enable, torque_limit](https://github.com/ROBOTIS-GIT/dynamixel-workbench/issues/27) — Signification des paramètres Dynamixel
- [Torque readings: Dynamixel MX 64 (Poppy Forum)](https://poppy.discourse.group/t/torque-readings-dynamixel-mx-64/1347) — Lecture du couple sur Dynamixel
