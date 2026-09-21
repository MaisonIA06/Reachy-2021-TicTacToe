#!/bin/bash
# Récupération après un plantage du contrôleur moteur.
#
# Contexte : ros2_control_node peut être tué au démarrage du robot par un
# recalage NTP (voir CLAUDE.md). Le SDK répond encore, mais les positions
# sont figées et aucune consigne n'aboutit. Redémarrer le service de
# Pollen répare la situation en une vingtaine de secondes.
#
# ⚠️ Ce script est lancé DÉTACHÉ par l'interface web, car il redémarre
# aussi cette interface : sans détachement, il se tuerait lui-même avant
# d'avoir fini. C'est systemd qui relance ensuite le serveur web, et le
# navigateur se reconnecte tout seul.
#
# Rien de ce script ne modifie le code ni les fichiers de Pollen : il ne
# fait que redémarrer un service existant.
set -u

JOURNAL=/tmp/recover_sdk.log

{
    echo "$(date +%T) === récupération demandée ==="

    echo "$(date +%T) redémarrage de reachy_sdk_server.service (Pollen)"
    systemctl --user restart reachy_sdk_server.service

    echo "$(date +%T) attente du contrôleur moteur"
    for i in $(seq 1 45); do
        if pgrep -f ros2_control_node > /dev/null; then
            echo "$(date +%T) ros2_control_node présent après ${i}x2 s"
            break
        fi
        sleep 2
    done

    if ! pgrep -f ros2_control_node > /dev/null; then
        echo "$(date +%T) ÉCHEC : contrôleur toujours absent"
        # On redémarre quand même l'interface : sans cela le navigateur ne
        # verrait AUCUN changement et l'utilisateur resterait sans signal.
        # Au retour, le bandeau d'alerte s'affichera de nouveau.
    else
        # Laisser le SDK finir d'exposer ses services avant de reconnecter.
        sleep 5
    fi

    # ⚠️ DERNIÈRE ACTION, obligatoirement.
    # `setsid` ne sort pas du cgroup de l'unité systemd : ce script est
    # tué par le redémarrage qu'il déclenche lui-même. Tout ce qui serait
    # écrit après cette ligne ne s'exécuterait jamais.
    echo "$(date +%T) redémarrage de l'interface web (fin du script)"
    systemctl --user restart reachy-tictactoe-web.service
} >> "$JOURNAL" 2>&1
