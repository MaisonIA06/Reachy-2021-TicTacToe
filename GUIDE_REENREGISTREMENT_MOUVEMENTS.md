# 📖 Guide de Ré-enregistrement des Mouvements

Ce guide vous accompagne pas à pas pour ré-enregistrer tous les mouvements du robot Reachy suite au changement de position/taille/hauteur du plateau.

---

## 📍 Récapitulatif : D'où → Où (chaque mouvement)

| Mouvement | **Départ (FROM)** | **Arrivée (TO)** |
|-----------|-------------------|------------------|
| **rest_pos** | — | Bras détendu le long du robot (position de référence) |
| **base_pos** | — | Bras légèrement levé, prêt à agir (position de référence) |
| **grab_1 à grab_5** | N'importe où (mode compliant) | Pince **ouverte** juste au-dessus du pion N (1=le plus proche, 5=le plus éloigné) |
| **lift** | **Depuis** une position grab (pince fermée sur un pion) | **Vers** le haut : bras levé, ~20–30 cm au-dessus du plateau, position sûre pour se déplacer |
| **put_1 à put_9** | **Depuis** position **lift** (pion en main) | **Vers** la case N du plateau : descente jusqu’à la hauteur de dépôt au-dessus de la case |
| **back_1_upright à back_9_upright** | **Depuis** la position de dépôt (fin du put_N, pince ouverte) | **Vers** le haut : bras relevé en position sûre (éviter collisions avec le plateau) |
| **shuffle-board** | Au-dessus du plateau | Balayage latéral fluide au-dessus du plateau (remettre les pions) |
| **my-turn** | Position de base / repos | Animation courte « c’est mon tour » puis retour |
| **your-turn** | Position de base / repos | Animation courte « c’est votre tour » puis retour |

**Enchaînement typique d’un coup :**  
`rest/base` → `grab_N` → `lift` → `put_case` → `back_N_upright` → `rest`

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

**D'où → Où :** **Depuis** n'importe où (mode compliant, vous déplacez le bras à la main) **→ vers** pince ouverte juste au-dessus du pion N (grab_1 = pion le plus proche, grab_5 = le plus éloigné). Vous enregistrez uniquement la **position d'arrivée**.

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

**D'où → Où :** **Depuis** une position grab (pince fermée sur un pion) **→ vers** le haut : bras levé à ~20–30 cm au-dessus du plateau (position sûre pour se déplacer vers n'importe quelle case).

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

**D'où → Où :** **Depuis** la position **lift** (pion en main) **→ vers** la case N : descente jusqu'à la hauteur de dépôt au-dessus de la case (position finale = au-dessus du plateau, prêt à ouvrir la pince).

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

**D'où → Où :** **Depuis** la position de dépôt (fin du put_N, pince ouverte au-dessus de la case) **→ vers** le haut : bras relevé en position sûre (éviter les collisions avec le plateau).

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

### Étape 6 : Animation shuffle-board (réprimande apres triche)

**D'où → Où :** balayage latéral fluide **au-dessus du plateau** (geste de « mélanger » les pions).

```bash
python scripts/moves/record_moves.py --name shuffle-board --type trajectory --duration 4.0 --host localhost
```

Points d'attention :
- Rester au-dessus du plateau sans toucher les pions réels
- Mouvement ample et lisible (il accompagne le son de réprimande)

### Étape 7 : Animations "turn" (C'est à qui le tour)

**7.1 - my-turn** (C'est mon tour)

**D'où → Où :** **Depuis** position de base ou repos **→** petit geste expressif **→** retour (trajectoire complète ~2 s).

```bash
python scripts/record_moves.py --name my-turn --type trajectory --duration 2.0
```

- Animation expressive pour indiquer que c'est le tour du robot
- Peut être un petit geste, un mouvement des antennes du bras
- Créatif et expressif !

**7.2 - your-turn** (C'est votre tour)

**D'où → Où :** **Depuis** position de base ou repos **→** geste invitant **→** retour (trajectoire complète ~2 s). Différent de my-turn.

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
