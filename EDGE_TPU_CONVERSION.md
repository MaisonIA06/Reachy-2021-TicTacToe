# Conversion des modèles EdgeTPU vers CPU

## 🚨 Problème

Les modèles `.tflite` actuels sont compilés pour **EdgeTPU** et contiennent des opérations spécifiques (`edgetpu-custom-op`) qui ne peuvent pas fonctionner sur un NUC sans accélérateur EdgeTPU.

Erreur typique :
```
RuntimeError: Encountered unresolved custom op: edgetpu-custom-op
```

## 💡 Solutions

### Solution 1 : Reconvertir les modèles pour CPU (Recommandé)

Si vous avez accès aux modèles originaux (avant compilation EdgeTPU), vous pouvez les reconvertir.

#### Étapes :

1. **Localiser les modèles originaux**
   - Fichiers `.pb` (TensorFlow)
   - Fichiers `.h5` (Keras)
   - Modèles SavedModel

2. **Convertir en TensorFlow Lite (CPU)**

```python
import tensorflow as tf

# Exemple avec un modèle SavedModel
converter = tf.lite.TFLiteConverter.from_saved_model('path/to/saved_model')

# Configuration pour CPU
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS,  # Opérations TFLite standard
]

# Convertir
tflite_model = converter.convert()

# Sauvegarder
with open('ttt-boxes-cpu.tflite', 'wb') as f:
    f.write(tflite_model)
```

3. **Remplacer les modèles**

```bash
cd reachy_tictactoe/models/
# Sauvegarder les anciens modèles
mv ttt-boxes.tflite ttt-boxes-edgetpu.tflite.backup
mv ttt-valid-board.tflite ttt-valid-board-edgetpu.tflite.backup

# Copier les nouveaux modèles
cp /path/to/ttt-boxes-cpu.tflite ttt-boxes.tflite
cp /path/to/ttt-valid-board-cpu.tflite ttt-valid-board.tflite
```

---

### Solution 2 : Utiliser des modèles de remplacement simples (Temporaire)

Si vous n'avez pas accès aux modèles originaux, utilisez des modèles de remplacement simples pour tester le système.

#### Créer automatiquement :

```bash
cd ~/dev/Reachy-2021-TicTacToe
python scripts/create_fallback_models.py
```

**⚠️ ATTENTION** : Ces modèles sont des placeholders et ne détectent PAS vraiment les pièces. Ils sont uniquement pour tester que le système fonctionne sans EdgeTPU.

---

### Solution 3 : Ajouter un accélérateur EdgeTPU USB

Si vous souhaitez utiliser les modèles EdgeTPU existants, vous pouvez ajouter un accélérateur.

#### Matériel nécessaire :
- [Coral USB Accelerator](https://coral.ai/products/accelerator/)

#### Installation :

1. **Brancher l'accélérateur** sur un port USB 3.0

2. **Installer le runtime EdgeTPU**

```bash
# Ajouter le dépôt Coral
echo "deb https://packages.cloud.google.com/apt coral-edgetpu-stable main" | sudo tee /etc/apt/sources.list.d/coral-edgetpu.list
curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -

# Installer
sudo apt update
sudo apt install libedgetpu1-std

# Version haute performance (chauffe plus)
# sudo apt install libedgetpu1-max
```

3. **Installer la bibliothèque Python**

```bash
pip install pycoral
```

4. **Modifier le code vision.py**

Utiliser `pycoral` au lieu de `tflite_runtime` :

```python
from pycoral.utils import edgetpu
from pycoral.adapters import common
from pycoral.adapters import classify

# Charger le modèle avec EdgeTPU
interpreter = edgetpu.make_interpreter('model_edgetpu.tflite')
interpreter.allocate_tensors()
```

---

## 🔍 Vérifier le type de modèle

Pour vérifier si un modèle est compilé pour EdgeTPU :

```python
import tflite_runtime.interpreter as tflite

try:
    interpreter = tflite.Interpreter('model.tflite')
    interpreter.allocate_tensors()
    print("✓ Modèle compatible CPU")
except RuntimeError as e:
    if 'edgetpu-custom-op' in str(e):
        print("✗ Modèle compilé pour EdgeTPU")
    else:
        print(f"✗ Autre erreur: {e}")
```

---

## 📝 Nomenclature des modèles

Convention de nommage recommandée :

- `model-cpu.tflite` : Modèle pour CPU
- `model-edgetpu.tflite` : Modèle pour EdgeTPU
- `model.tflite` : Modèle actuel (par défaut)

---

## 🎯 Performances comparées

| Matériel | Inférence | Latence |
|----------|-----------|---------|
| NUC CPU (i5) | ~50-100ms | Acceptable |
| NUC CPU (i7) | ~30-50ms | Bonne |
| EdgeTPU | ~5-10ms | Excellente |

Pour le jeu de morpion, les performances CPU sont largement suffisantes.

---

## ❓ FAQ

### Q: Puis-je utiliser TensorFlow complet au lieu de TFLite ?
R: Oui, mais c'est plus lourd. TFLite est recommandé pour la robotique embarquée.

### Q: Où trouver les modèles originaux ?
R: Ils devraient être dans le dépôt original du projet ou dans les notebooks de training.

### Q: Les modèles CPU sont-ils moins précis ?
R: Non, la précision est identique. Seule la vitesse d'exécution diffère.

### Q: Puis-je utiliser un GPU à la place ?
R: Oui, avec TensorFlow GPU, mais c'est plus complexe à configurer.

---

## 🔗 Ressources

- [TensorFlow Lite Guide](https://www.tensorflow.org/lite/guide)
- [Coral EdgeTPU Documentation](https://coral.ai/docs/)
- [Model Converter](https://www.tensorflow.org/lite/convert)
- [Optimization Guide](https://www.tensorflow.org/lite/performance/best_practices)

---

## 📞 Support

Si vous avez des difficultés :

1. Vérifiez les logs : `/tmp/tictactoe*.log`
2. Testez avec les modèles de fallback
3. Consultez le forum Pollen Robotics
4. Ouvrez une issue sur GitHub

