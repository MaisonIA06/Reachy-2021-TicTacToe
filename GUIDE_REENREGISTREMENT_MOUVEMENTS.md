# 📖 Guide de Ré-enregistrement des Mouvements

Ce guide vous accompagne pas à pas pour ré-enregistrer tous les mouvements du robot Reachy suite au changement de position/taille/hauteur du plateau.

---

## 🎯 Prérequis

### ✅ Checklist avant de commencer

- [ ] Le robot Reachy est allumé et accessible
- [ ] Les coordonnées du plateau sont mises à jour dans `reachy_tictactoe/vision.py`
- [ ] Le plateau est à sa nouvelle position
- [ ] Vous avez 5 pions à disposition (alignés devant le robot)
- [ ] Vous êtes connecté au robot (SSH ou local)
- [ ] L'environnement virtuel est activé : `source venv/bin/activate`

---

## 📋 Ordre d'enregistrement recommandé

### Étape 1 : Positions de référence

Ces positions sont définies directement dans le code. Mesurez-les et notez-les :

```bash
# Démarrer le script en mode interactif
python scripts/record_moves.py --interactive --host localhost
```

**Mouvements à mesurer manuellement :**

1. **rest_pos** - Position de repos naturelle du bras
   - Bras détendu le long du robot
   - Notez les angles et mettez à jour `reachy_tictactoe/moves/__init__.py` si nécessaire

2. **base_pos** - Position de base avant action
   - Position préparatoire, bras légèrement levé
   - Notez les angles et mettez à jour `reachy_tictactoe/moves/__init__.py` si nécessaire

---

### Étape 2 : Mouvements "grab" (Attraper les pions)

**Préparation :**
- Alignez 5 pions devant le robot (ordre : de gauche à droite ou autre ordre cohérent)
- Les pions doivent être à portée du bras

**Enregistrement :**

```bash
# Mode interactif recommandé
python scripts/record_moves.py --interactive

# Ou individuellement
python scripts/record_moves.py --name grab_1 --type position
python scripts/record_moves.py --name grab_2 --type position
python scripts/record_moves.py --name grab_3 --type position
python scripts/record_moves.py --name grab_4 --type position
python scripts/record_moves.py --name grab_5 --type position
```

**Pour chaque grab :**
1. Le script active le mode compliant
2. Déplacez manuellement le bras au-dessus du pion N
3. Positionnez la pince ouverte juste au-dessus du pion (prêt à attraper)
4. Appuyez sur ENTRÉE pour enregistrer
5. Confirmez la position

💡 **Astuce :** Les positions grab_4 et grab_5 sont généralement plus éloignées

---

### Étape 3 : Mouvement "lift" (Lever le pion)

**Préparation :**
- Placez le bras dans une position grab (peu importe laquelle)
- Fermez la pince manuellement (ou imaginez qu'elle est fermée avec un pion)

**Enregistrement :**

```bash
python scripts/record_moves.py --name lift --type position
```

**Instructions :**
1. À partir d'une position grab, levez le bras verticalement
2. Hauteur de sécurité : ~20-30cm au-dessus du plateau
3. Cette position doit permettre de se déplacer vers n'importe quelle case sans collision
4. Appuyez sur ENTRÉE pour enregistrer

---

### Étape 4 : Trajectoires "put" (Placer dans les cases)

**Préparation :**
- Placez le bras en position "lift"
- Assurez-vous que le plateau est vide et visible

**Numérotation des cases :**
```
1 | 2 | 3
---------
4 | 5 | 6
---------
7 | 8 | 9
```

**Enregistrement (durée recommandée : 2-3 secondes) :**

```bash
# Mode interactif recommandé
python scripts/record_moves.py --interactive

# Ou individuellement
python scripts/record_moves.py --name put_1 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_2 --type trajectory --duration 2.5
# ... et ainsi de suite jusqu'à put_9
```

**Pour chaque case (1 à 9) :**
1. Partez de la position "lift"
2. Le script démarre un compte à rebours de 3 secondes
3. Pendant l'enregistrement (~2-3 secondes) :
   - Déplacez le bras vers la case N
   - Descendez jusqu'à la hauteur de dépôt (au-dessus du plateau)
   - Arrêtez-vous à la position finale
4. Le script enregistre automatiquement la trajectoire
5. Il crée aussi la version `put_N_smooth_10_kp.npz`

💡 **Astuces :**
- Mouvements fluides et réguliers
- Ne forcez pas, restez naturel
- La vitesse d'enregistrement est de 100 Hz (très précis)

---

### Étape 5 : Mouvements "back_upright" (Retour après dépôt)

**Préparation :**
- Pour chaque case, positionnez le bras à la position de dépôt (fin du put)

**Enregistrement :**

```bash
python scripts/record_moves.py --name back_1_upright --type position
python scripts/record_moves.py --name back_2_upright --type position
# ... jusqu'à back_9_upright
```

**Pour chaque case :**
1. Partez de la position de dépôt (après put_N)
2. Levez le bras verticalement en position sûre
3. Cette position doit éviter les collisions avec le plateau
4. Appuyez sur ENTRÉE pour enregistrer

---

### Étape 6 : Mouvements de transition

**6.1 - back_to_back** (Position intermédiaire)

```bash
python scripts/record_moves.py --name back_to_back --type position
```

- Position intermédiaire entre une position back_upright et le retour au repos
- Généralement à mi-chemin

**6.2 - back_rest** (Transition vers repos)

```bash
python scripts/record_moves.py --name back_rest --type position
```

- Position entre back_to_back et rest_pos
- Transition douce vers le repos

**6.3 - shuffle-board** (Mélanger le plateau) - OPTIONNEL

```bash
python scripts/record_moves.py --name shuffle-board --type trajectory --duration 4.0
```

- Trajectoire pour balayer le plateau (remettre les pions en place)
- Mouvement latéral fluide au-dessus du plateau
- Utilisé en fin de partie

---

### Étape 7 : Animations "turn" (C'est à qui le tour)

**7.1 - my-turn** (C'est mon tour)

```bash
python scripts/record_moves.py --name my-turn --type trajectory --duration 2.0
```

- Animation expressive pour indiquer que c'est le tour du robot
- Peut être un petit geste, un mouvement des antennes du bras
- Créatif et expressif !

**7.2 - your-turn** (C'est votre tour)

```bash
python scripts/record_moves.py --name your-turn --type trajectory --duration 2.0
```

- Animation pour indiquer que c'est le tour de l'humain
- Différent de my-turn
- Geste invitant, accueillant

---

## ✅ Étape 8 : Tests et validation

### Test individuel

```bash
# Tester un mouvement spécifique
python scripts/test_recorded_moves.py --name grab_1 --host localhost
```

### Test interactif (recommandé)

```bash
# Mode interactif pour tester à la demande
python scripts/test_recorded_moves.py --interactive --host localhost
```

### Test complet

```bash
# Tester TOUS les mouvements d'un coup (attention !)
python scripts/test_recorded_moves.py --all --host localhost
```

---

## 📊 Checklist finale

### Mouvements de base
- [ ] rest_pos (noté dans `__init__.py`)
- [ ] base_pos (noté dans `__init__.py`)

### Attraper les pions
- [ ] grab_1.npz
- [ ] grab_2.npz
- [ ] grab_3.npz
- [ ] grab_4.npz
- [ ] grab_5.npz
- [ ] lift.npz

### Placer dans les cases
- [ ] put_1.npz et put_1_smooth_10_kp.npz
- [ ] put_2.npz et put_2_smooth_10_kp.npz
- [ ] put_3.npz et put_3_smooth_10_kp.npz
- [ ] put_4.npz et put_4_smooth_10_kp.npz
- [ ] put_5.npz et put_5_smooth_10_kp.npz
- [ ] put_6.npz et put_6_smooth_10_kp.npz
- [ ] put_7.npz et put_7_smooth_10_kp.npz
- [ ] put_8.npz et put_8_smooth_10_kp.npz
- [ ] put_9.npz et put_9_smooth_10_kp.npz

### Retours
- [ ] back_1_upright.npz
- [ ] back_2_upright.npz
- [ ] back_3_upright.npz
- [ ] back_4_upright.npz
- [ ] back_5_upright.npz
- [ ] back_6_upright.npz
- [ ] back_7_upright.npz
- [ ] back_8_upright.npz
- [ ] back_9_upright.npz

### Transitions
- [ ] back_to_back.npz
- [ ] back_rest.npz
- [ ] shuffle-board.npz

### Animations
- [ ] my-turn.npz
- [ ] your-turn.npz

### Tests
- [ ] Tous les mouvements testés individuellement
- [ ] Test d'un jeu complet
- [ ] Pas de collision détectée
- [ ] Mouvements fluides et naturels

---

## 🎮 Lancer un jeu de test

Une fois tous les mouvements enregistrés et testés :

```bash
# Lancer le jeu
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test

# Observer le comportement
# Vérifier :
# - Fluidité des mouvements
# - Précision des placements
# - Absence de collisions
# - Cohérence globale
```

---

## 🐛 Dépannage

### Le bras ne bouge pas en mode compliant

**Solution :**
```python
# Vérifier que le bras est bien désactivé
from reachy_sdk import ReachySDK
reachy = ReachySDK('localhost')
reachy.turn_off('r_arm')
```

### Erreur "Joint not found"

**Solution :**
- Vérifiez que vous utilisez le bon nom de joint
- Le script devrait gérer automatiquement la conversion des noms

### Le mouvement ne se rejoue pas correctement

**Causes possibles :**
1. La position enregistrée est hors limites
2. Collision avec un obstacle
3. Moteurs pas assez puissants

**Solutions :**
- Ré-enregistrer le mouvement avec une trajectoire différente
- Vérifier les angles limites des joints
- Tester sans obstacle d'abord

### Les fichiers .npz ne se créent pas

**Solution :**
```bash
# Vérifier les permissions
ls -la reachy_tictactoe/moves/

# Créer le dossier si nécessaire
mkdir -p reachy_tictactoe/moves
```

---

## 💡 Conseils et bonnes pratiques

### Pendant l'enregistrement

1. **Mouvements naturels** : Ne forcez pas, suivez les capacités du bras
2. **Sécurité** : Gardez toujours une marge de sécurité (hauteur, distance)
3. **Cohérence** : Gardez le même style de mouvement pour tous les enregistrements
4. **Fluidité** : Les trajectoires doivent être douces et continues

### Organisation

1. **Sauvegarde** : Avant de commencer, sauvegardez l'ancien dossier `moves/`
   ```bash
   cp -r reachy_tictactoe/moves reachy_tictactoe/moves_backup_$(date +%Y%m%d)
   ```

2. **Enregistrement par étapes** : Ne faites pas tout d'un coup, prenez des pauses

3. **Tests réguliers** : Testez chaque mouvement juste après l'avoir enregistré

### Optimisation

1. **Vitesse** : Les mouvements rapides sont plus impressionnants mais moins précis
2. **Précision** : Privilégiez la précision pour les placements (put)
3. **Expression** : Les animations peuvent être créatives et expressives

---

## 📞 Besoin d'aide ?

Si vous rencontrez des problèmes :

1. Vérifiez ce guide en détail
2. Consultez les logs : `/tmp/tictactoe_test.log`
3. Testez les mouvements individuellement
4. Vérifiez la connexion au robot : `ping <IP_REACHY>`

---

**Bon enregistrement ! 🎉**

Une fois terminé, vous aurez un robot Reachy parfaitement adapté à votre nouveau plateau !

