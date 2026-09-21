"""Point d'entrée du serveur web.

    python -m reachy_tictactoe.webapp --host localhost
    python -m reachy_tictactoe.webapp --host localhost --port 8000

Le serveur écoute sur 0.0.0.0 : l'interface est accessible depuis
n'importe quel navigateur du réseau, à http://<ip-du-robot>:8080/

⚠️ Le serveur démarre AVANT d'avoir joint le robot, et se connecte en
tâche de fond. Voir ``link.py`` : sans cela, un SDK pas encore prêt
faisait mourir le processus, et le bouton « Réparer » — qui vit dans
cette interface — devenait inaccessible précisément quand il sert.
"""
import argparse
import logging

import uvicorn

from .. import TictactoePlayground
from ..game_launcher import GameSession
from .controller import RobotController
from .health import MotorHealth
from .link import RobotLink
from .server import create_app

logger = logging.getLogger('reachy.tictactoe.webapp')


def connect_robot(host, register=None):
    """Établit la connexion au robot. Lève s'il est injoignable.

    Appelée en tâche de fond par ``RobotLink``, et retentée jusqu'au
    succès : c'est le seul endroit qui parle au SDK au démarrage.

    Args:
        host: adresse du robot.
        register: prévenu dès que le playground existe, AVANT ``setup()``.
            ⚠️ Indispensable : ``setup()`` alimente les moteurs et dure
            plusieurs secondes. Si le service est arrêté pendant ce
            temps — cas courant, ``recover_sdk.sh`` nous relance juste
            après le retour du contrôleur — le fil démon est tué net et
            les moteurs resteraient sous tension. L'appelant doit pouvoir
            les couper sans attendre que la session soit publiée.
    """
    logger.info(f'Connexion au robot ({host})…')
    playground = TictactoePlayground(host=host)
    if register is not None:
        register(playground)

    try:
        playground.setup()
        session = GameSession(playground)

        # setup() alimente bras et tête ; l'interface peut ensuite attendre
        # des heures sans qu'on clique. On repose donc immédiatement : les
        # moteurs ne doivent pas chauffer à ne rien faire.
        session.rest()
    except Exception:
        # ⚠️ Le SDK peut répondre alors que `ros2_control_node` est mort —
        # précisément la panne visée. Sans cette fermeture, chaque
        # tentative laisserait derrière elle un canal gRPC et son fil de
        # synchronisation, toutes les 5 s, indéfiniment.
        _fermer_sans_bruit(playground)
        raise

    return session, RobotController(session)


def _fermer_sans_bruit(playground):
    """Coupe le couple sans jamais masquer l'erreur d'origine."""
    if playground is None:
        return
    try:
        playground.close()
    except Exception as erreur:
        logger.warning(f'Fermeture du playground impossible : {erreur}')


def main():
    parser = argparse.ArgumentParser(
        description="Interface web de pilotage du TicTacToe Reachy")
    parser.add_argument('--host', default='localhost',
                        help='Adresse du robot Reachy (défaut: localhost)')
    # 8000 est déjà utilisé sur le NUC du robot.
    parser.add_argument('--port', type=int, default=8080,
                        help='Port d\'écoute du serveur (défaut: 8080)')
    parser.add_argument('--bind', default='0.0.0.0',
                        help='Interface d\'écoute (défaut: 0.0.0.0, tout le réseau)')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    # Surveillance du contrôleur moteur : détecte son plantage, dont le
    # symptôme (robot qui répond mais n'obéit plus) est invisible
    # autrement. La vérification lit /proc, donc n'a de sens que si le
    # serveur tourne sur le robot lui-même — et reste valable même quand
    # le SDK ne répond pas, ce qui justifie le bouton « Réparer ».
    local = args.host in ('localhost', '127.0.0.1', '::1')
    if not local:
        logger.warning(
            f'Robot distant ({args.host}) : la surveillance du '
            f'contrôleur moteur est désactivée.')

    # Playground en cours de construction : il existe avant la session et
    # doit pouvoir être fermé même si l'on s'arrête en plein setup().
    en_construction = {'playground': None}

    link = RobotLink(connect=lambda: connect_robot(
        args.host, register=lambda pg: en_construction.update(playground=pg)))
    link.start()

    app = create_app(link=link, health=MotorHealth(local=local))

    logger.info(f'Interface disponible sur http://{args.bind}:{args.port}/')
    try:
        uvicorn.run(app, host=args.bind, port=args.port, log_level='warning')
    finally:
        # On ne laisse pas les moteurs sous tension derrière nous — y
        # compris si l'on s'arrête pendant la connexion, bras déjà
        # alimenté et session pas encore publiée.
        session = link.session
        _fermer_sans_bruit(session.playground if session is not None
                           else en_construction['playground'])


if __name__ == '__main__':
    main()
