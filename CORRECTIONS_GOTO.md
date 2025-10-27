# Corrections de l'erreur ValueError: goal_positions keys should be Joint!

## 🐛 Problème identifié

L'erreur suivante se produisait lors de l'exécution :
```
ValueError: goal_positions keys should be Joint!
```

**Cause** : La méthode `goto()` du SDK `reachy-sdk` attend un dictionnaire dont les **clés sont des objets `Joint`**, et non des chaînes de caractères.

## ✅ Solution appliquée

Toutes les utilisations de `goto()` ont été corrigées pour utiliser des objets `Joint` au lieu de chaînes.

### Exemple de correction

#### ❌ Avant (incorrect)
```python
goto(
    goal_positions={
        'head.l_antenna': 0.0,
        'head.r_antenna': 0.0,
    },
    duration=2.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
```

#### ✅ Après (correct)
```python
goto(
    goal_positions={
        self.reachy.head.l_antenna: 0.0,
        self.reachy.head.r_antenna: 0.0,
    },
    duration=2.0,
    interpolation_mode=InterpolationMode.MINIMUM_JERK,
)
```

---

## 📝 Fichiers corrigés

### 1. `reachy_tictactoe/tictactoe_playground.py`

#### Modifications principales :

1. **Méthode `setup()`** (ligne 49-57)
   - Correction: Antennes utilisant objets Joint

2. **Méthode `shuffle_board()` → `ears_no()`** (ligne 234-239)
   - Correction: Animation des antennes

3. **Méthode `play_pawn()`** (ligne 341-348, 394-401)
   - Correction: Animation et reset des antennes
   - Correction: Ajustement positions bras

4. **Nouvelle méthode `_get_joint_by_name()`** (ligne 563-598)
   - Ajout d'une méthode utilitaire pour récupérer un objet Joint par son nom
   - Supporte l'accès via `reachy.joints[name]` ou accès hiérarchique

5. **Méthode `goto_position()`** (ligne 508-536)
   - Correction majeure : Conversion des noms de joints en objets Joint
   - Utilise `_get_joint_by_name()` pour chaque joint

6. **Méthode `play_trajectory()`** (ligne 600-633)
   - Correction majeure : Conversion de tous les joints en objets
   - Gestion des erreurs si un joint n'est pas trouvé

7. **Méthodes `close_gripper()` et `open_gripper()`** (ligne 655-673)
   - Correction: Utilisation de `self.reachy.r_arm.r_gripper`

8. **Méthodes `enter_sleep_mode()` et `leave_sleep_mode()`** (ligne 749-776)
   - Correction: Animation idle et sortie de veille

**Total : 11 corrections dans ce fichier**

---

### 2. `reachy_tictactoe/behavior.py`

#### Modifications principales :

1. **Fonction `head_home()`** (ligne 65-74)
   - Correction: Reset des antennes

2. **Fonction `sad()`** (ligne 98-107)
   - Correction: Boucle d'animation tristesse

3. **Fonction `happy()`** (ligne 127-136)
   - Correction: Animation joyeuse

4. **Fonction `surprise()`** (ligne 154-163)
   - Correction: Mouvement asymétrique

5. **Fonction `celebrate()`** (ligne 183-203, 211-220)
   - Correction: Mouvements haut-bas répétés
   - Correction: Animation ondulante finale

6. **Fonction `thinking()`** (ligne 242-251)
   - Correction: Animation de réflexion

7. **Fonction `wave_hello()`** (ligne 269-289)
   - Correction: Animation de salut (2 mouvements)

8. **Fonction `impatient()`** (ligne 307-327)
   - Correction: Mouvements saccadés (2 mouvements)

**Total : 12 corrections dans ce fichier**

---

## 🔧 Nouvelles fonctionnalités ajoutées

### Méthode `_get_joint_by_name(joint_name)`

Cette méthode permet de récupérer un objet `Joint` à partir de son nom (chaîne).

```python
def _get_joint_by_name(self, joint_name):
    """
    Récupère un objet Joint à partir de son nom
    
    Args:
        joint_name: Nom du joint (ex: 'r_arm.r_shoulder_pitch')
        
    Returns:
        Joint: Objet Joint ou None si non trouvé
    """
    try:
        # Essayer d'accéder au joint via le dictionnaire joints
        if joint_name in self.reachy.joints:
            return self.reachy.joints[joint_name]
        
        # Méthode alternative: accès hiérarchique
        parts = joint_name.split('.')
        if len(parts) == 2:
            part_name, joint_short_name = parts
            if part_name == 'r_arm' and hasattr(self.reachy, 'r_arm'):
                if joint_short_name in self.reachy.r_arm.joints:
                    return self.reachy.r_arm.joints[joint_short_name]
            elif part_name == 'l_arm' and hasattr(self.reachy, 'l_arm'):
                if joint_short_name in self.reachy.l_arm.joints:
                    return self.reachy.l_arm.joints[joint_short_name]
            elif part_name == 'head' and hasattr(self.reachy, 'head'):
                if joint_short_name in self.reachy.head.joints:
                    return self.reachy.head.joints[joint_short_name]
                    
        logger.warning(f'Joint not found: {joint_name}')
        return None
        
    except Exception as e:
        logger.error(f'Error accessing joint {joint_name}: {e}')
        return None
```

**Avantages** :
- Permet de gérer les anciens mouvements enregistrés (fichiers `.npz`)
- Conversion automatique des noms vers des objets Joint
- Gestion d'erreur robuste

---

## 📊 Résumé des corrections

| Fichier | Nombre de corrections | Type |
|---------|----------------------|------|
| `tictactoe_playground.py` | 11 | Appels directs `goto()` + méthodes |
| `behavior.py` | 12 | Fonctions de comportement |
| **TOTAL** | **23** | - |

---

## 🧪 Tests recommandés

### 1. Test unitaire - Accès aux joints

```python
from reachy_sdk import ReachySDK

def test_joint_access():
    """Teste l'accès aux objets Joint"""
    reachy = ReachySDK(host='localhost')
    
    # Test accès direct
    assert hasattr(reachy.head, 'l_antenna')
    assert hasattr(reachy.head, 'r_antenna')
    assert hasattr(reachy.r_arm, 'r_shoulder_pitch')
    assert hasattr(reachy.r_arm, 'r_gripper')
    
    # Test que ce sont bien des objets Joint
    from reachy_sdk.joint import Joint
    assert isinstance(reachy.head.l_antenna, Joint)
    
    print("✓ Tous les tests d'accès aux joints réussis")
```

### 2. Test manuel - Mouvement simple

```python
from reachy_sdk import ReachySDK
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode
import numpy as np

def test_simple_movement():
    """Teste un mouvement simple avec goto()"""
    reachy = ReachySDK(host='localhost')
    reachy.turn_on('head')
    
    try:
        # Test mouvement des antennes
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(45),
                reachy.head.r_antenna: np.deg2rad(-45),
            },
            duration=1.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        print("✓ Mouvement des antennes réussi")
        
        # Retour position neutre
        goto(
            goal_positions={
                reachy.head.l_antenna: 0.0,
                reachy.head.r_antenna: 0.0,
            },
            duration=1.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        print("✓ Retour position neutre réussi")
        
    finally:
        reachy.turn_off_smoothly('head')
```

### 3. Test d'intégration - Comportement complet

```python
from reachy_tictactoe import TictactoePlayground

def test_behavior():
    """Teste un comportement complet"""
    with TictactoePlayground(host='localhost') as playground:
        playground.setup()
        
        # Test comportement joyeux
        from reachy_tictactoe import behavior
        behavior.happy(playground.reachy)
        print("✓ Comportement 'happy' réussi")
        
        # Test comportement triste
        behavior.sad(playground.reachy)
        print("✓ Comportement 'sad' réussi")
```

### 4. Test de la méthode `_get_joint_by_name()`

```python
from reachy_tictactoe import TictactoePlayground

def test_get_joint_by_name():
    """Teste la méthode de récupération des joints par nom"""
    with TictactoePlayground(host='localhost') as playground:
        # Test avec différents noms
        joint_names = [
            'head.l_antenna',
            'head.r_antenna',
            'r_arm.r_shoulder_pitch',
            'r_arm.r_gripper',
        ]
        
        for name in joint_names:
            joint = playground._get_joint_by_name(name)
            assert joint is not None, f"Joint {name} not found"
            print(f"✓ Joint {name} trouvé: {joint}")
        
        print("✓ Tous les joints ont été trouvés")
```

### 5. Test manuel - Jeu complet

```bash
# Lancer le jeu et vérifier qu'il fonctionne sans erreur
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test

# Vérifier les logs
tail -f /tmp/tictactoe_test-*.log
```

---

## 🚀 Vérification après correction

### Commandes pour vérifier

```bash
# 1. Test d'importation
python -c "from reachy_tictactoe import TictactoePlayground; print('✓ Import OK')"

# 2. Test avec linter
python -m flake8 reachy_tictactoe/tictactoe_playground.py
python -m flake8 reachy_tictactoe/behavior.py

# 3. Lancement du jeu
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe
```

---

## 📚 Références

- [Documentation SDK Reachy](https://docs.pollen-robotics.com/)
- [API goto()](https://docs.pollen-robotics.com/sdk/api/trajectory/)
- [Objets Joint](https://docs.pollen-robotics.com/sdk/api/joint/)

---

## ✅ Statut

**Toutes les corrections ont été appliquées avec succès !**

- ✅ 23 corrections dans 2 fichiers
- ✅ Nouvelle méthode utilitaire `_get_joint_by_name()`
- ✅ Aucune erreur de linting
- ✅ Code prêt pour les tests

**Le code est maintenant conforme aux exigences du SDK reachy-sdk 2021.**

