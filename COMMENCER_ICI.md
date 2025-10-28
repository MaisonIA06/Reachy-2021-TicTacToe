# 🎯 COMMENCER ICI - Créer vos modèles TicTacToe

**Bienvenue !** Ce fichier vous guide pour créer vos propres modèles de vision en quelques étapes simples.

---

## 📚 Quelle documentation lire ?

Choisissez selon votre niveau et vos besoins :

| Si vous voulez... | Lisez ce fichier |
|-------------------|------------------|
| 🚀 **Commencer immédiatement** | `DEMARRAGE_RAPIDE_MODELES.md` (5 min de lecture) |
| 📖 **Guide détaillé complet** | `GUIDE_CREATION_MODELES.md` (15 min de lecture) |
| 🔧 **Comprendre les scripts** | `SCRIPTS_CREES.md` (résumé technique) |
| ❓ **Juste les commandes** | Ci-dessous ⬇️ |

---

## ⚡ Démarrage ultra-rapide (pour impatients)

### 1️⃣ Installer (30 min)

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
./install_training.sh
```

**Résultat** : TensorFlow et toutes les dépendances installées ✅

### 2️⃣ Calibrer le plateau (15 min)

```bash
python scripts/calibrate_board.py --host localhost
```

**À faire après** : Copier les coordonnées de `/tmp/board_calibration.py` dans `reachy_tictactoe/vision.py`

### 3️⃣ Collecter les images (2-3h répartis en sessions)

```bash
# Session 1 : Cases vides (30 min)
python scripts/collect_boxes_images.py --host localhost --class empty --target 50

# Session 2 : Cubes (45 min)
python scripts/collect_boxes_images.py --host localhost --class cube --target 50

# Session 3 : Cylindres (45 min)
python scripts/collect_boxes_images.py --host localhost --class cylinder --target 50

# Session 4 : Plateaux valides (30 min)
python scripts/collect_valid_board_images.py --host localhost --class valid --target 150

# Session 5 : Plateaux invalides (30 min)
python scripts/collect_valid_board_images.py --host localhost --class invalid --target 150
```

**💡 Astuce** : Vous pouvez faire ces sessions sur plusieurs jours !

### 4️⃣ Vérifier (2 min)

```bash
python scripts/check_training_data.py
```

**Objectif** : Voir "✅ Prêt pour l'entraînement"

### 5️⃣ Entraîner (1-2h automatique)

```bash
python scripts/train_models.py --model all --epochs 15
```

**Attendez** : Allez boire un café ☕, l'entraînement est automatique

### 6️⃣ Convertir (5 min)

```bash
python scripts/convert_to_tflite.py --model all
```

**Résultat** : Modèles TFLite prêts dans `reachy_tictactoe/models/` ✅

### 7️⃣ Tester (30 min)

```bash
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test
```

**Jouez** quelques parties pour valider !

---

## 🎯 Objectifs à atteindre

### Images à collecter

| Classe | Images nécessaires | Méthode |
|--------|-------------------|---------|
| Cases vides | 300-500 | 50 photos du plateau vide × 9 cases |
| Cubes | 300-500 | 50 photos avec cubes à différents endroits |
| Cylindres | 300-500 | 50 photos avec cylindres à différents endroits |
| Plateau valide | 100-200 | 150 photos du plateau bien positionné |
| Plateau invalide | 100-200 | 150 photos de situations problématiques |

**Total** : ~1100-1650 images (~2-3h de collecte)

### Précision des modèles

- ✅ **ttt-boxes** : ≥ 90% de précision
- ✅ **ttt-valid-board** : ≥ 95% de précision

---

## 💡 Conseils essentiels

### Pour réussir la collecte d'images

1. **Variez l'éclairage** 💡
   - Photos le matin ET l'après-midi
   - Avec ET sans lumière artificielle
   - Évitez les ombres portées

2. **Variez les positions** 🎲
   - Cubes/cylindres dans toutes les cases
   - Différentes combinaisons
   - Pièces légèrement décalées

3. **Bougez le plateau** 📐
   - Légèrement décalé entre les photos
   - Différentes orientations (±5 degrés)

4. **Nettoyez vos données** 🧹
   - Supprimez les images floues
   - Supprimez si votre main est visible
   - Gardez seulement les meilleures

### Pour un entraînement réussi

1. **Soyez patient** ⏱️
   - 30-60 minutes par modèle
   - C'est normal sur CPU
   - Laissez tourner, ne pas interrompre

2. **Si mémoire insuffisante** 💾
   ```bash
   python scripts/train_models.py --model all --batch-size 16
   ```

3. **Si précision < 80%** 📉
   - Collectez plus d'images (500+ par classe)
   - Vérifiez la qualité des images
   - Variez davantage les conditions

---

## 🐛 Problèmes fréquents et solutions

| Problème | Solution |
|----------|----------|
| ❌ "Out of memory" pendant l'entraînement | Ajoutez `--batch-size 16` ou `--batch-size 8` |
| ❌ Précision < 80% | Collectez 2× plus d'images variées |
| ❌ "No module named tensorflow" | Exécutez `./install_training.sh` |
| ❌ Images ne se sauvegardent pas | Vérifiez que les dossiers `training_data/` existent |
| ❌ Reachy ne détecte pas bien les pièces | Revérifiez la calibration du plateau |
| ❌ Script ne trouve pas Reachy | Changez `localhost` par l'IP de Reachy |

---

## 📞 Besoin d'aide ?

### Documentation disponible

1. **`DEMARRAGE_RAPIDE_MODELES.md`** 🚀
   - Guide condensé
   - Toutes les commandes essentielles
   - ~120 lignes

2. **`GUIDE_CREATION_MODELES.md`** 📖
   - Guide complet détaillé
   - Explications de chaque étape
   - Solutions aux problèmes
   - Conseils d'expert
   - ~450 lignes

3. **`SCRIPTS_CREES.md`** 🔧
   - Description technique des scripts
   - Fonctionnalités détaillées
   - Résumé de ce qui a été préparé

4. **`README.md`** 📄
   - Documentation générale du projet
   - Installation et configuration

### Ordre recommandé de lecture

1. ✅ Ce fichier (`COMMENCER_ICI.md`) ← Vous êtes ici
2. ➡️ `DEMARRAGE_RAPIDE_MODELES.md` (5 min)
3. ➡️ `GUIDE_CREATION_MODELES.md` (si besoin de détails)

---

## ✅ Checklist rapide

Cochez au fur et à mesure :

### Installation
- [ ] Dépendances installées (`./install_training.sh`)
- [ ] TensorFlow fonctionne (`python -c "import tensorflow"`)
- [ ] Dossiers `training_data/` créés

### Calibration
- [ ] Script de calibration exécuté
- [ ] Coordonnées copiées dans `vision.py`

### Collecte
- [ ] ~450 images de cases vides
- [ ] ~450 images de cubes
- [ ] ~450 images de cylindres
- [ ] ~150 images de plateaux valides
- [ ] ~150 images de plateaux invalides
- [ ] Images nettoyées (floues supprimées)

### Entraînement
- [ ] Modèle boxes entraîné (précision ≥ 90%)
- [ ] Modèle valid-board entraîné (précision ≥ 95%)
- [ ] Courbes d'entraînement vérifiées

### Conversion
- [ ] Modèles convertis en TFLite
- [ ] Fichiers dans `reachy_tictactoe/models/`
- [ ] 4 fichiers créés (.tflite et .txt)

### Test
- [ ] Jeu lancé sans erreurs
- [ ] Plateau détecté correctement
- [ ] Pièces détectées correctement
- [ ] 3-5 parties jouées avec succès

---

## 🎓 Niveau de difficulté

| Aspect | Difficulté | Temps |
|--------|------------|-------|
| Installation | ⭐ Facile | 30 min |
| Calibration | ⭐ Facile | 15 min |
| Collecte | ⭐⭐ Moyen | 2-3h |
| Nettoyage | ⭐ Facile | 30 min |
| Entraînement | ⭐⭐ Moyen | 1-2h (auto) |
| Conversion | ⭐ Facile | 5 min |
| Test | ⭐ Facile | 30 min |
| **TOTAL** | **⭐⭐ Moyen** | **5-8h** |

**Compétences requises** :
- ✅ Utilisation basique de la ligne de commande
- ✅ Patience (pour la collecte et l'entraînement)
- ✅ Aucune connaissance en machine learning nécessaire !

---

## 🎉 Prêt à commencer ?

**Prochaine étape** :

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
./install_training.sh
```

Puis suivez les instructions affichées !

**Bonne chance ! 🚀**

---

*Créé le 28 octobre 2025 - Guide pour débutants en machine learning*

