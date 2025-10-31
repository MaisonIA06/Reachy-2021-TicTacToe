#!/bin/bash
# Script d'aide pour enregistrer tous les mouvements TicTacToe
# Usage: ./scripts/record_all_moves.sh [--host IP]

set -e  # Arrêter en cas d'erreur

# Couleurs pour l'affichage
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Adresse du robot
HOST=${1:-localhost}
if [[ "$1" == "--host" ]]; then
    HOST=${2:-localhost}
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Enregistrement des mouvements TicTacToe${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "Robot: ${GREEN}$HOST${NC}"
echo -e "Projet: ${GREEN}$PROJECT_DIR${NC}"
echo ""

# Fonction d'aide
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --host IP     Adresse IP du robot (défaut: localhost)"
    echo "  --help        Afficher cette aide"
    echo ""
    echo "Ce script vous guide pour enregistrer tous les mouvements."
    exit 0
}

if [[ "$1" == "--help" ]]; then
    show_help
fi

# Vérifier que le script record_moves.py existe
if [ ! -f "$SCRIPT_DIR/record_moves.py" ]; then
    echo -e "${RED}❌ Erreur: record_moves.py non trouvé${NC}"
    echo "Assurez-vous d'être dans le bon répertoire"
    exit 1
fi

# Fonction pour enregistrer un mouvement
record_move() {
    local name=$1
    local type=$2
    local duration=${3:-""}
    
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📝 Enregistrement : ${GREEN}$name${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ "$type" == "position" ]; then
        python "$SCRIPT_DIR/record_moves.py" --name "$name" --type position --host "$HOST"
    else
        python "$SCRIPT_DIR/record_moves.py" --name "$name" --type trajectory --duration "$duration" --host "$HOST"
    fi
    
    local status=$?
    if [ $status -eq 0 ]; then
        echo -e "${GREEN}✅ $name enregistré avec succès${NC}"
    else
        echo -e "${RED}❌ Erreur lors de l'enregistrement de $name${NC}"
        read -p "Continuer malgré l'erreur ? (o/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
            exit 1
        fi
    fi
}

# Menu principal
show_menu() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║        MENU D'ENREGISTREMENT                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  1. Enregistrer les mouvements GRAB (1-5)"
    echo "  2. Enregistrer le mouvement LIFT"
    echo "  3. Enregistrer les trajectoires PUT (1-9)"
    echo "  4. Enregistrer les mouvements BACK_UPRIGHT (1-9)"
    echo "  5. Enregistrer les TRANSITIONS"
    echo "  6. Enregistrer les ANIMATIONS"
    echo "  7. Tout enregistrer (session complète)"
    echo "  8. Mode interactif (recommandé)"
    echo "  9. Afficher l'aide"
    echo "  q. Quitter"
    echo ""
    echo -ne "${YELLOW}Votre choix: ${NC}"
}

# Enregistrer tous les grab
record_grabs() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ENREGISTREMENT DES MOUVEMENTS GRAB${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo "Préparez 5 pions alignés devant le robot"
    read -p "Prêt ? (appuyez sur Entrée)"
    
    for i in {1..5}; do
        record_move "grab_$i" "position"
    done
    
    echo -e "\n${GREEN}✅ Tous les mouvements grab enregistrés !${NC}"
}

# Enregistrer lift
record_lift() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ENREGISTREMENT DU MOUVEMENT LIFT${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo "Placez le bras en position grab (avec pince fermée)"
    read -p "Prêt ? (appuyez sur Entrée)"
    
    record_move "lift" "position"
    
    echo -e "\n${GREEN}✅ Mouvement lift enregistré !${NC}"
}

# Enregistrer tous les put
record_puts() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ENREGISTREMENT DES TRAJECTOIRES PUT${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo "Numérotation des cases:"
    echo "  1 | 2 | 3"
    echo "  ---------"
    echo "  4 | 5 | 6"
    echo "  ---------"
    echo "  7 | 8 | 9"
    echo ""
    echo "Placez le bras en position lift avant chaque enregistrement"
    read -p "Prêt ? (appuyez sur Entrée)"
    
    for i in {1..9}; do
        echo ""
        echo -e "${YELLOW}➡️  Case $i${NC}"
        record_move "put_$i" "trajectory" "2.5"
        echo "Replacez le bras en position lift pour la prochaine case"
        if [ $i -lt 9 ]; then
            read -p "Appuyez sur Entrée pour continuer..."
        fi
    done
    
    echo -e "\n${GREEN}✅ Toutes les trajectoires put enregistrées !${NC}"
}

# Enregistrer tous les back_upright
record_backs() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ENREGISTREMENT DES MOUVEMENTS BACK${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo "Pour chaque case, partez de la position de dépôt"
    read -p "Prêt ? (appuyez sur Entrée)"
    
    for i in {1..9}; do
        echo ""
        echo -e "${YELLOW}➡️  Retour depuis case $i${NC}"
        echo "Placez le bras à la position de dépôt de la case $i"
        read -p "Appuyez sur Entrée quand prêt..."
        record_move "back_${i}_upright" "position"
    done
    
    echo -e "\n${GREEN}✅ Tous les mouvements back enregistrés !${NC}"
}

# Enregistrer les transitions
record_transitions() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ENREGISTREMENT DES TRANSITIONS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    echo "1/3 - back_to_back (position intermédiaire)"
    read -p "Prêt ? (appuyez sur Entrée)"
    record_move "back_to_back" "position"
    
    echo ""
    echo "2/3 - back_rest (transition vers repos)"
    read -p "Prêt ? (appuyez sur Entrée)"
    record_move "back_rest" "position"
    
    echo ""
    echo "3/3 - shuffle-board (balayage du plateau)"
    read -p "Prêt ? (appuyez sur Entrée)"
    record_move "shuffle-board" "trajectory" "4.0"
    
    echo -e "\n${GREEN}✅ Toutes les transitions enregistrées !${NC}"
}

# Enregistrer les animations
record_animations() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  ENREGISTREMENT DES ANIMATIONS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    echo "1/2 - my-turn (c'est mon tour)"
    read -p "Prêt ? (appuyez sur Entrée)"
    record_move "my-turn" "trajectory" "2.0"
    
    echo ""
    echo "2/2 - your-turn (c'est votre tour)"
    read -p "Prêt ? (appuyez sur Entrée)"
    record_move "your-turn" "trajectory" "2.0"
    
    echo -e "\n${GREEN}✅ Toutes les animations enregistrées !${NC}"
}

# Mode interactif
interactive_mode() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  MODE INTERACTIF${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    
    python "$SCRIPT_DIR/record_moves.py" --interactive --host "$HOST"
}

# Session complète
record_all() {
    echo -e "\n${BLUE}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     SESSION COMPLÈTE D'ENREGISTREMENT         ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Cette session va enregistrer TOUS les mouvements."
    echo "Temps estimé: 30-45 minutes"
    echo ""
    read -p "Êtes-vous prêt à continuer ? (o/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[OoYy]$ ]]; then
        return
    fi
    
    record_grabs
    read -p "Pause. Appuyez sur Entrée pour continuer..."
    
    record_lift
    read -p "Pause. Appuyez sur Entrée pour continuer..."
    
    record_puts
    read -p "Pause. Appuyez sur Entrée pour continuer..."
    
    record_backs
    read -p "Pause. Appuyez sur Entrée pour continuer..."
    
    record_transitions
    read -p "Pause. Appuyez sur Entrée pour continuer..."
    
    record_animations
    
    echo -e "\n${GREEN}╔════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ SESSION COMPLÈTE TERMINÉE !                ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Prochaines étapes:"
    echo "  1. Testez les mouvements avec: ./scripts/test_recorded_moves.py --interactive"
    echo "  2. Lancez un jeu test: python -m reachy_tictactoe.game_launcher"
}

# Afficher l'aide
show_detailed_help() {
    echo -e "\n${BLUE}═══════════════════════════════════════${NC}"
    echo -e "${BLUE}  AIDE - ENREGISTREMENT DES MOUVEMENTS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════${NC}"
    echo ""
    echo "Documentation complète:"
    echo "  • GUIDE_REENREGISTREMENT_MOUVEMENTS.md"
    echo "  • AIDE_RAPIDE_MOUVEMENTS.md"
    echo ""
    echo "Scripts disponibles:"
    echo "  • record_moves.py       : Enregistrement individuel"
    echo "  • test_recorded_moves.py : Test des mouvements"
    echo "  • record_all_moves.sh   : Assistant complet (ce script)"
    echo ""
    read -p "Appuyez sur Entrée pour revenir au menu..."
}

# Boucle principale
while true; do
    show_menu
    read choice
    
    case $choice in
        1) record_grabs ;;
        2) record_lift ;;
        3) record_puts ;;
        4) record_backs ;;
        5) record_transitions ;;
        6) record_animations ;;
        7) record_all ;;
        8) interactive_mode ;;
        9) show_detailed_help ;;
        q|Q) 
            echo -e "\n${GREEN}Au revoir ! 👋${NC}\n"
            exit 0
            ;;
        *) 
            echo -e "\n${RED}❌ Choix invalide${NC}"
            ;;
    esac
done

