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

        app = create_app(session=session,
                         controller=RobotController(session))

        logger.info(f'Interface disponible sur http://{args.bind}:{args.port}/')
        uvicorn.run(app, host=args.bind, port=args.port, log_level='warning')


if __name__ == '__main__':
    main()
