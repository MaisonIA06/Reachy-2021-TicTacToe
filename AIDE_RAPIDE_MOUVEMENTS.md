# 🚀 Aide Rapide - Ré-enregistrement des Mouvements

## Commandes essentielles

### 📝 Enregistrer des mouvements

```bash
# Mode interactif (RECOMMANDÉ)
python scripts/record_moves.py --interactive --host localhost

# Position simple
python scripts/record_moves.py --name grab_1 --type position --host localhost

# Trajectoire (2-3 secondes recommandé)
python scripts/record_moves.py --name put_1 --type trajectory --duration 2.5 --host localhost
```

### 🧪 Tester des mouvements

```bash
# Mode interactif (RECOMMANDÉ)
python scripts/test_recorded_moves.py --interactive --host localhost

# Tester un mouvement
python scripts/test_recorded_moves.py --name grab_1 --host localhost

# Tester tous les mouvements
python scripts/test_recorded_moves.py --all --host localhost
```

---

## 📋 Ordre d'enregistrement

### 1️⃣ Positions grab (5 mouvements)
```bash
python scripts/record_moves.py --name grab_1 --type position
python scripts/record_moves.py --name grab_2 --type position
python scripts/record_moves.py --name grab_3 --type position
python scripts/record_moves.py --name grab_4 --type position
python scripts/record_moves.py --name grab_5 --type position
```

### 2️⃣ Position lift (1 mouvement)
```bash
python scripts/record_moves.py --name lift --type position
```

### 3️⃣ Trajectoires put (9 mouvements)
```bash
python scripts/record_moves.py --name put_1 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_2 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_3 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_4 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_5 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_6 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_7 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_8 --type trajectory --duration 2.5
python scripts/record_moves.py --name put_9 --type trajectory --duration 2.5
```

### 4️⃣ Positions back_upright (9 mouvements)
```bash
python scripts/record_moves.py --name back_1_upright --type position
python scripts/record_moves.py --name back_2_upright --type position
python scripts/record_moves.py --name back_3_upright --type position
python scripts/record_moves.py --name back_4_upright --type position
python scripts/record_moves.py --name back_5_upright --type position
python scripts/record_moves.py --name back_6_upright --type position
python scripts/record_moves.py --name back_7_upright --type position
python scripts/record_moves.py --name back_8_upright --type position
python scripts/record_moves.py --name back_9_upright --type position
```

### 5️⃣ Transitions (3 mouvements)
```bash
python scripts/record_moves.py --name back_to_back --type position
python scripts/record_moves.py --name back_rest --type position
python scripts/record_moves.py --name shuffle-board --type trajectory --duration 4.0
```

### 6️⃣ Animations (2 mouvements)
```bash
python scripts/record_moves.py --name my-turn --type trajectory --duration 2.0
python scripts/record_moves.py --name your-turn --type trajectory --duration 2.0
```

---

## 🎯 Numérotation des cases

```
1 | 2 | 3
---------
4 | 5 | 6
---------
7 | 8 | 9
```

---

## 💾 Sauvegarde préalable

```bash
# Sauvegarder les anciens mouvements
cp -r reachy_tictactoe/moves reachy_tictactoe/moves_backup_$(date +%Y%m%d_%H%M%S)
```

---

## 🧪 Tests

```bash
# Test interactif
python scripts/test_recorded_moves.py --interactive

# Test d'un jeu complet
python -m reachy_tictactoe.game_launcher --log-file /tmp/tictactoe_test
```

---

## 📚 Documentation complète

Consultez `GUIDE_REENREGISTREMENT_MOUVEMENTS.md` pour les instructions détaillées.

