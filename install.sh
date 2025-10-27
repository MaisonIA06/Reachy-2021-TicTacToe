#!/bin/bash
# Script d'installation pour reachy_tictactoe (SDK 2021)

set -e

echo "=========================================="
echo "Installation de Reachy TicTacToe (SDK 2021)"
echo "=========================================="
echo ""

# Couleurs pour l'affichage
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Vérifier Python 3
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 n'est pas installé"
    exit 1
fi
print_status "Python 3 trouvé: $(python3 --version)"

# Vérifier pip
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 n'est pas installé"
    exit 1
fi
print_status "pip3 trouvé"

# Créer l'environnement virtuel si nécessaire
if [ ! -d "venv" ]; then
    echo ""
    echo "Création de l'environnement virtuel..."
    python3 -m venv venv
    print_status "Environnement virtuel créé"
else
    print_warning "L'environnement virtuel existe déjà"
fi

# Activer l'environnement virtuel
echo ""
echo "Activation de l'environnement virtuel..."
source venv/bin/activate
print_status "Environnement virtuel activé"

# Mettre à jour pip
echo ""
echo "Mise à jour de pip..."
pip install --upgrade pip
print_status "pip mis à jour"

# Installer les dépendances
echo ""
echo "Installation des dépendances..."
pip install -r requirements.txt
print_status "Dépendances installées"

# Installer le package en mode développement
echo ""
echo "Installation du package reachy_tictactoe..."
pip install -e .
print_status "Package installé en mode développement"

# Vérifier l'installation
echo ""
echo "Vérification de l'installation..."
if python -c "from reachy_tictactoe import TictactoePlayground; print('Import OK')" 2>/dev/null; then
    print_status "Installation vérifiée avec succès"
else
    print_error "Erreur lors de la vérification"
    print_warning "Il manque peut-être le SDK Reachy. Installez-le avec:"
    echo "    pip install reachy-sdk"
    exit 1
fi

echo ""
echo "=========================================="
print_status "Installation terminée avec succès !"
echo "=========================================="
echo ""
echo "Pour lancer le jeu:"
echo "  1. Activez l'environnement virtuel:"
echo "     source venv/bin/activate"
echo ""
echo "  2. Lancez le jeu:"
echo "     python -m reachy_tictactoe.game_launcher"
echo ""
echo "Pour plus d'informations, consultez README.md"
echo ""

