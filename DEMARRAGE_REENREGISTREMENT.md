# 🚀 Démarrage Rapide - Ré-enregistrement des Mouvements

## ⚡ Pour commencer immédiatement

### Option 1 : Assistant complet (recommandé) 🎯

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
./scripts/record_all_moves.sh
```

L'assistant vous guidera à travers un menu interactif pour enregistrer tous les mouvements.

---

### Option 2 : Mode interactif Python 🐍

```bash
cd /home/mia/Bureau/reachy-2019-tictactoe
source venv/bin/activate
python scripts/record_moves.py --interactive --host localhost
```

Vous pouvez enregistrer chaque mouvement individuellement selon vos besoins.

---

## 📋 Checklist de préparation

Avant de commencer, assurez-vous que :

- [ ] Le robot Reachy est allumé et fonctionnel
- [ ] Vous êtes connecté au robot (SSH ou local)
- [ ] L'environnement virtuel est activé : `source venv/bin/activate`
- [ ] Le plateau est positionné à sa nouvelle place
- [ ] Vous avez les coordonnées du plateau mises à jour dans `reachy_tictactoe/vision.py`
- [ ] Vous avez 5 pions disponibles pour les tests
- [ ] Vous avez ~30-45 minutes devant vous

---

## 🎯 Ordre d'enregistrement recommandé

1. **Mouvements grab** (5 mouvements) - ~5 minutes
   - Alignez 5 pions devant le robot
   - Enregistrez grab_1 à grab_5

2. **Mouvement lift** (1 mouvement) - ~1 minute
   - Position de levage du pion

3. **Trajectoires put** (9 trajectoires) - ~15 minutes
   - Placement dans les cases 1-9
   - Partir de la position lift à chaque fois

4. **Mouvements back_upright** (9 mouvements) - ~10 minutes
   - Retour depuis chaque case

5. **Transitions** (3 mouvements) - ~5 minutes
   - back_to_back, back_rest, shuffle-board

6. **Animations** (2 trajectoires) - ~3 minutes
   - my-turn, your-turn

---

## 🧪 Tester les mouvements

Après l'enregistrement, testez immédiatement :

```bash
# Mode interactif pour tester
python scripts/test_recorded_moves.py --interactive

# Ou tester un mouvement spécifique
python scripts/test_recorded_moves.py --name grab_1
```

---

## 🎮 Lancer un jeu test complet

Une fois tous les mouvements enregistrés et testés :

```bash
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test
```

---

## 📚 Documentation

- **Guide complet** : `GUIDE_REENREGISTREMENT_MOUVEMENTS.md`
- **Aide rapide** : `AIDE_RAPIDE_MOUVEMENTS.md`
- **README scripts** : `scripts/README.md`

---

## 💾 Sauvegarde (Important !)

Avant de commencer, sauvegardez vos anciens mouvements :

```bash
cp -r reachy_tictactoe/moves reachy_tictactoe/moves_backup_$(date +%Y%m%d_%H%M%S)
```

Vous pourrez ainsi revenir en arrière si nécessaire.

---

## 🆘 Besoin d'aide ?

### Problème de connexion au robot

```bash
# Vérifier que le robot est accessible
ping <IP_ROBOT>

# Vérifier l'état du serveur Reachy
ssh reachy@<IP_ROBOT>
systemctl status reachy_sdk_server
```

### Le bras ne bouge pas en mode compliant

```python
# Vérifier manuellement
from reachy_sdk import ReachySDK
reachy = ReachySDK('localhost')
reachy.turn_off('r_arm')  # Active le mode compliant
```

### Erreur lors de l'enregistrement

- Vérifiez que le dossier `reachy_tictactoe/moves/` existe
- Vérifiez les permissions : `ls -la reachy_tictactoe/moves/`
- Créez le dossier si nécessaire : `mkdir -p reachy_tictactoe/moves`

---

## ⏱️ Temps estimés

- **Préparation** : 5 minutes
- **Enregistrement complet** : 30-45 minutes
- **Tests** : 10-15 minutes
- **Jeu test** : 5 minutes

**Total** : ~1 heure

---

## ✅ Après le ré-enregistrement

Une fois tout terminé :

1. ✅ Tous les mouvements sont enregistrés (29 fichiers .npz)
2. ✅ Tous les mouvements ont été testés
3. ✅ Un jeu complet fonctionne sans erreur
4. ✅ Pas de collision détectée
5. ✅ Les mouvements sont fluides et naturels

**Félicitations ! 🎉** Votre robot Reachy est maintenant adapté à votre nouveau plateau !

---

**Prêt ? Lancez l'assistant :**

```bash
./scripts/record_all_moves.sh
```

Bonne chance ! 🤖

