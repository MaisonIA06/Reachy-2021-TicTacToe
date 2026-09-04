#!/bin/bash
# Installe l'interface web comme service utilisateur systemd.
#
# À lancer SUR LE ROBOT :
#     bash scripts/systemd/install.sh
#
# Ce que ça fait :
#   - copie notre unité dans ~/.config/systemd/user/ ;
#   - l'active pour qu'elle démarre avec la session.
#
# Ce que ça NE fait PAS : toucher au service reachy_sdk_server.service de
# Pollen, ni à leur code. Notre unité est indépendante.
#
# Pour tout annuler :
#     systemctl --user disable --now reachy-tictactoe-web.service
#     rm ~/.config/systemd/user/reachy-tictactoe-web.service
#     systemctl --user daemon-reload
set -euo pipefail

ICI="$(cd "$(dirname "$0")" && pwd)"
PROJET="$(cd "$ICI/../.." && pwd)"
CIBLE="$HOME/.config/systemd/user"
UNITE=reachy-tictactoe-web.service

if [ ! -x "$PROJET/venv/bin/python" ]; then
    echo "ERREUR : $PROJET/venv/bin/python introuvable." >&2
    echo "Créez l'environnement virtuel avant d'installer le service." >&2
    exit 1
fi

echo "Installation de $UNITE dans $CIBLE"
echo "  dépôt : $PROJET"
mkdir -p "$CIBLE"
# Le chemin du dépôt est injecté ici : l'unité versionnée ne présume pas
# de l'endroit où le projet est installé.
sed "s#__PROJET__#$PROJET#g" "$ICI/$UNITE" > "$CIBLE/$UNITE"
chmod 644 "$CIBLE/$UNITE"
chmod +x "$ICI/recover_sdk.sh"

systemctl --user daemon-reload
systemctl --user enable "$UNITE"

# Un serveur lancé à la main occuperait le port 8080.
pkill -f "reachy_tictactoe.webapp" 2>/dev/null || true
sleep 3

systemctl --user restart "$UNITE"
sleep 12

echo
systemctl --user status "$UNITE" --no-pager --lines=5 || true
echo
echo "Priorité effective (doit afficher 5) :"
pid=$(systemctl --user show "$UNITE" -p MainPID --value)
[ "$pid" != "0" ] && ps -o ni= -p "$pid" | tr -d ' ' || echo "processus introuvable"
