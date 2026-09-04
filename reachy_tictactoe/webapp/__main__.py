"""Point d'entrée du serveur web.

    python -m reachy_tictactoe.webapp --host localhost
    python -m reachy_tictactoe.webapp --host localhost --port 8000

Le serveur écoute sur 0.0.0.0 : l'interface est accessible depuis
n'importe quel navigateur du réseau, à http://<ip-du-robot>:8000/
"""
import argparse
import logging

import uvicorn

from .. import TictactoePlayground
from ..game_launcher import GameSession
from .controller import RobotController
from .health import MotorHealth
from .server import create_app

logger = logging.getLogger('reachy.tictactoe.webapp')


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

    logger.info(f'Connexion au robot ({args.host})…')
    with TictactoePlayground(host=args.host) as playground:
        playground.setup()
        session = GameSession(playground)

        # setup() alimente bras et tête ; l'interface peut ensuite attendre
        # des heures sans qu'on clique. On repose donc immédiatement : les
        # moteurs ne doivent pas chauffer à ne rien faire.
        session.rest()

        # Surveillance du contrôleur moteur : détecte son plantage, dont
        # le symptôme (robot qui répond mais n'obéit plus) est invisible
        # autrement. La vérification lit /proc, donc n'a de sens que si le
        # serveur tourne sur le robot lui-même.
        local = args.host in ('localhost', '127.0.0.1', '::1')
        if not local:
            logger.warning(
                f'Robot distant ({args.host}) : la surveillance du '
                f'contrôleur moteur est désactivée.')

        app = create_app(session=session,
                         controller=RobotController(session),
                         health=MotorHealth(local=local))

        logger.info(f'Interface disponible sur http://{args.bind}:{args.port}/')
        uvicorn.run(app, host=args.bind, port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
