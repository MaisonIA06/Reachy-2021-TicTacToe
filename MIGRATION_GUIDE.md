# Guide de migration - SDK 2019 vers SDK 2021

Ce document détaille toutes les modifications apportées au code pour le rendre compatible avec le SDK Reachy 2021.

## 📋 Table des matières

1. [Changements dans les imports](#changements-dans-les-imports)
2. [Initialisation du robot](#initialisation-du-robot)
3. [Contrôle des moteurs](#contrôle-des-moteurs)
4. [Noms des articulations](#noms-des-articulations)
5. [Trajectoires](#trajectoires)
6. [Vision](#vision)
7. [Comportements](#comportements)

---

## 1. Changements dans les imports

### SDK principal

**Avant (2019)** :
```python
from reachy import Reachy
from reachy.parts import RightArm, Head
from reachy.trajectory import TrajectoryPlayer
```

**Après (2021)** :
```python
from reachy_sdk import ReachySDK
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode
```

### Vision (EdgeTPU → TFLite)

**Avant (2019)** :
```python
from edgetpu.utils import dataset_utils
from edgetpu.classification.engine import ClassificationEngine
```

**Après (2021)** :
```python
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite
```

---

## 2. Initialisation du robot

### Connexion

**Avant (2019)** :
```python
self.reachy = Reachy(
    right_arm=RightArm(
        io='/dev/ttyUSB*',
        hand='force_gripper',
    ),
    head=Head(
        io='/dev/ttyUSB*',
    ),
)
```

**Après (2021)** :
```python
self.reachy = ReachySDK(host='localhost')
# ou
self.reachy = ReachySDK(host='192.168.1.100')
```

### Différences clés :
- Le SDK 2021 utilise une connexion réseau (gRPC)
- Plus besoin de spécifier les ports USB
- L'accès se fait via l'adresse IP du robot

---

## 3. Contrôle des moteurs

### Activation des moteurs

**Avant (2019)** :
```python
for m in self.reachy.right_arm.motors:
    m.compliant = False
```

**Après (2021)** :
```python
self.reachy.turn_on('r_arm')
# ou pour tout activer
self.reachy.turn_on('reachy')
```

### Désactivation

**Avant (2019)** :
```python
for m in self.reachy.right_arm.motors:
    m.compliant = True
```

**Après (2021)** :
```python
self.reachy.turn_off('r_arm')
# ou en douceur
self.reachy.turn_off_smoothly('reachy')
```

### Mouvement simple

**Avant (2019)** :
```python
motor.goto(
    goal_position=0,
    duration=2,
    interpolation_mode='minjerk',
)
```

**Après (2021)** :
```python
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode

goto(
    goal_positions={'head.l_antenna': 0.0},
    duration=2.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
```

---

## 4. Noms des articulations

### Mapping complet

| Ancien nom (2019) | Nouveau nom (2021) |
|-------------------|-------------------|
| `right_arm.shoulder_pitch` | `r_arm.r_shoulder_pitch` |
| `right_arm.shoulder_roll` | `r_arm.r_shoulder_roll` |
| `right_arm.arm_yaw` | `r_arm.r_arm_yaw` |
| `right_arm.elbow_pitch` | `r_arm.r_elbow_pitch` |
| `right_arm.hand.forearm_yaw` | `r_arm.r_forearm_yaw` |
| `right_arm.hand.wrist_pitch` | `r_arm.r_wrist_pitch` |
| `right_arm.hand.wrist_roll` | `r_arm.r_wrist_roll` |
| `right_arm.hand.gripper` | `r_arm.r_gripper` |
| `head.left_antenna` | `head.l_antenna` |
| `head.right_antenna` | `head.r_antenna` |

### Fonction de conversion

```python
def _adapt_joint_name(old_name):
    """Convertit les anciens noms vers les nouveaux"""
    mapping = {
        'right_arm.shoulder_pitch': 'r_arm.r_shoulder_pitch',
        'right_arm.shoulder_roll': 'r_arm.r_shoulder_roll',
        'right_arm.arm_yaw': 'r_arm.r_arm_yaw',
        'right_arm.elbow_pitch': 'r_arm.r_elbow_pitch',
        'right_arm.hand.forearm_yaw': 'r_arm.r_forearm_yaw',
        'right_arm.hand.wrist_pitch': 'r_arm.r_wrist_pitch',
        'right_arm.hand.wrist_roll': 'r_arm.r_wrist_roll',
        'right_arm.hand.gripper': 'r_arm.r_gripper',
        'head.left_antenna': 'head.l_antenna',
        'head.right_antenna': 'head.r_antenna',
    }
    return mapping.get(old_name, old_name)
```

---

## 5. Trajectoires

### Mouvement multi-joints

**Avant (2019)** :
```python
self.reachy.goto(
    goal_positions={
        'right_arm.shoulder_pitch': 50,
        'right_arm.elbow_pitch': -80,
    },
    duration=2,
    wait=True,
    interpolation_mode='minjerk',
    starting_point='goal_position',
)
```

**Après (2021)** :
```python
goto(
    goal_positions={
        'r_arm.r_shoulder_pitch': np.deg2rad(50),
        'r_arm.r_elbow_pitch': np.deg2rad(-80),
    },
    duration=2.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
time.sleep(2.0)  # Attendre la fin du mouvement
```

### TrajectoryPlayer

**Avant (2019)** :
```python
from reachy.trajectory import TrajectoryPlayer

TrajectoryPlayer(self.reachy, trajectory_dict).play(wait=True)
```

**Après (2021)** :
```python
# Jouer point par point
for i in range(num_points):
    point = {joint: traj[i] for joint, traj in trajectory_dict.items()}
    goto(
        goal_positions=point,
        duration=0.01,
        interpolation_mode=InterpolationMode.LINEAR,
    )
    time.sleep(0.01)
```

---

## 6. Vision

### Classification avec EdgeTPU → TFLite

**Avant (2019)** :
```python
from edgetpu.classification.engine import ClassificationEngine

classifier = ClassificationEngine('model.tflite')
res = classifier.classify_with_image(pil_img, top_k=1)
```

**Après (2021)** :
```python
import tflite_runtime.interpreter as tflite

class TFLiteClassifier:
    def __init__(self, model_path, label_path):
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
    def classify_with_image(self, img, top_k=1):
        # Préparer l'image
        input_shape = self.input_details[0]['shape']
        img = img.resize((input_shape[2], input_shape[1]))
        input_data = np.expand_dims(img, axis=0)
        
        # Inférence
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        
        # Résultats
        results = np.squeeze(output_data)
        top_indices = np.argsort(results)[-top_k:][::-1]
        return [(int(i), float(results[i])) for i in top_indices]
```

### Caméra

**Avant (2019)** :
```python
success, img = self.reachy.head.right_camera.read()
```

**Après (2021)** :
```python
img = self.reachy.right_camera.read()
```

---

## 7. Comportements

### Antennes

**Avant (2019)** :
```python
self.reachy.head.left_antenna.goal_position = 45
self.reachy.head.right_antenna.goal_position = -45
```

**Après (2021)** :
```python
goto(
    goal_positions={
        'head.l_antenna': np.deg2rad(45),
        'head.r_antenna': np.deg2rad(-45),
    },
    duration=1.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
```

### Pince

**Avant (2019)** :
```python
self.reachy.right_arm.hand.close()
self.reachy.right_arm.hand.open()
```

**Après (2021)** :
```python
def close_gripper():
    goto(
        goal_positions={'r_arm.r_gripper': np.deg2rad(-45)},
        duration=0.5,
        interpolation_mode=InterpolationMode.LINEAR,
    )
    time.sleep(0.5)

def open_gripper():
    goto(
        goal_positions={'r_arm.r_gripper': np.deg2rad(20)},
        duration=0.5,
        interpolation_mode=InterpolationMode.LINEAR,
    )
    time.sleep(0.5)
```

---

## 🎯 Points d'attention

### 1. Unités d'angle

Le SDK 2021 utilise **les radians** par défaut, pas les degrés.

```python
# Conversion nécessaire
angle_rad = np.deg2rad(angle_deg)
```

### 2. Synchronisation

Le SDK 2021 ne bloque pas automatiquement. Il faut gérer l'attente :

```python
goto(goal_positions=..., duration=2.0, ...)
time.sleep(2.0)  # Important !
```

### 3. Accès aux joints

**Avant (2019)** :
```python
for motor in self.reachy.right_arm.motors:
    print(motor.present_position)
```

**Après (2021)** :
```python
for joint in self.reachy.r_arm.joints.values():
    print(joint.present_position)
```

### 4. Températures

**Avant (2019)** :
```python
motor.temperature
```

**Après (2021)** :
```python
joint.temperature
```

---

## 🔍 Checklist de migration

- [ ] Remplacer tous les imports `reachy` par `reachy_sdk`
- [ ] Convertir l'initialisation `Reachy()` en `ReachySDK()`
- [ ] Adapter tous les noms de joints
- [ ] Remplacer `motor.compliant` par `turn_on()`/`turn_off()`
- [ ] Convertir les degrés en radians
- [ ] Remplacer `motor.goto()` par `goto()`
- [ ] Adapter les TrajectoryPlayer
- [ ] Remplacer EdgeTPU par TFLite
- [ ] Ajouter `time.sleep()` après les mouvements
- [ ] Tester toutes les fonctionnalités

---

## 📚 Ressources

- [Documentation SDK 2021](https://docs.pollen-robotics.com/)
- [API Reference](https://docs.pollen-robotics.com/sdk/api/)
- [Forum Pollen Robotics](https://forum.pollen-robotics.com/)

---

## ❓ Questions fréquentes

### Q: Pourquoi les mouvements ne fonctionnent-ils pas ?

R: Vérifiez que :
1. Les moteurs sont activés avec `turn_on()`
2. Les angles sont en radians
3. Vous attendez la fin du mouvement avec `time.sleep()`

### Q: Comment déboguer les problèmes de connexion ?

R: Testez la connexion avec :
```python
from reachy_sdk import ReachySDK
reachy = ReachySDK(host='localhost')
print(reachy.info)
```

### Q: Les anciens fichiers .npz fonctionnent-ils ?

R: Oui, mais les noms de joints doivent être convertis avec la fonction `_adapt_joint_name()`.

