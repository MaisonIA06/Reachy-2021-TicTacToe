# 🚀 Démarrage rapide : Créer vos modèles

Guide ultra-simplifié pour créer vos modèles TicTacToe en quelques commandes.

## ⏱️ Temps estimé : 5-8 heures

| Phase | Durée | Difficulté |
|-------|-------|------------|
| Installation | 30 min | ⭐ Facile |
| Calibration | 15 min | ⭐ Facile |
| Collecte images | 2-3h | ⭐⭐ Moyen |
| Entraînement | 1-2h | ⭐⭐ Moyen |
| Test | 30 min | ⭐ Facile |

---

## 📋 Commandes essentielles

### 1️⃣ Installation (une seule fois)

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
./install_training.sh
```

### 2️⃣ Calibration du plateau (une seule fois)

```bash
python scripts/calibrate_board.py --host localhost
# Puis copiez les coordonnées dans reachy_tictactoe/vision.py
```

### 3️⃣ Collecte des images (2-3 heures)

```bash
# Cases vides (30 min)
python scripts/collect_boxes_images.py --host localhost --class empty --target 50

# Cases avec cubes (45 min)
python scripts/collect_boxes_images.py --host localhost --class cube --target 50

# Cases avec cylindres (45 min)
python scripts/collect_boxes_images.py --host localhost --class cylinder --target 50

# Plateaux valides (30 min)
python scripts/collect_valid_board_images.py --host localhost --class valid --target 150

# Plateaux invalides (30 min)
python scripts/collect_valid_board_images.py --host localhost --class invalid --target 150

# Vérifier les données
python scripts/check_training_data.py
```

### 4️⃣ Entraînement (1-2 heures)

```bash
# Entraîner les deux modèles
python scripts/train_models.py --model all --epochs 15
```

### 5️⃣ Conversion (5 min)

```bash
# Convertir en TFLite
python scripts/convert_to_tflite.py --model all
```

### 6️⃣ Test (30 min)

```bash
# Lancer le jeu
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test

# Dans un autre terminal, voir les logs
tail -f /tmp/tictactoe_test.log
```

---

## 🎯 Objectifs de collecte

| Classe | Minimum | Recommandé | Comment |
|--------|---------|------------|---------|
| empty | 300 | 450 | 50 photos × 9 cases |
| cube | 300 | 450 | 50 photos × variable |
| cylinder | 300 | 450 | 50 photos × variable |
| valid | 100 | 150 | 150 photos |
| invalid | 100 | 150 | 150 photos |

**Total** : ~1100-1650 images

---

## ✅ Critères de succès

Vos modèles sont bons si :

- ✅ Précision d'entraînement :
  - ttt-boxes : ≥ 90%
  - ttt-valid-board : ≥ 95%
- ✅ Le jeu fonctionne sans erreurs de vision
- ✅ Reachy détecte correctement les pièces pendant le jeu

---

## 💡 Conseils clés

### Pour la collecte

1. **Variez l'éclairage** : matin, après-midi, lumière artificielle
2. **Variez les positions** : pièces dans différentes cases
3. **Bougez le plateau** : légèrement entre les captures
4. **Nettoyez** : supprimez les images floues

### Pour l'entraînement

1. **Soyez patient** : 30-60 min par modèle sur CPU
2. **Surveillez la précision** : elle doit augmenter progressivement
3. **Si précision < 80%** : collectez plus d'images variées

---

## 🐛 Problèmes courants

| Problème | Solution rapide |
|----------|-----------------|
| "Out of memory" | `--batch-size 16` |
| Précision trop basse | Collecter plus d'images |
| Détection instable | Vérifier calibration plateau |
| Script ne trouve pas les images | Vérifier chemins dans `training_data/` |

---

## 📚 Documentation complète

- **Guide détaillé** : `GUIDE_CREATION_MODELES.md`
- **Scripts** : `scripts/README.md`
- **Projet général** : `README.md`

---

## 📞 Besoin d'aide ?

1. Consultez `GUIDE_CREATION_MODELES.md` pour les détails
2. Vérifiez les logs d'entraînement
3. Examinez les courbes dans `models/*.png`

---

**🎉 Bonne chance pour la création de vos modèles !**

