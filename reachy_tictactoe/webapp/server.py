"""API et page de l'interface web.

Le serveur ne parle jamais au SDK : il ne connaît que la ``GameSession``
(état du jeu) et le ``RobotController`` (actions sérialisées). C'est ce
qui permet de le tester sans robot.
"""
import asyncio
import json
import logging
import os
from dataclasses import asdict

import cv2 as cv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .controller import RobotBusy

logger = logging.getLogger('reachy.tictactoe.webapp')

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


def _snapshot(session, controller):
    """État complet consommé par l'interface."""
    game = asdict(session.state)
    game['board'] = list(game['board'])
    running = controller.running
    return {
        'game': game,
        'robot': {
            'running': running,
            'busy': running is not None,
            'last_error': controller.last_error,
        },
    }


def create_app(session, controller):
    """Construit l'application FastAPI.

    Args:
        session: ``GameSession`` — source de l'état du jeu.
        controller: ``RobotController`` — lance les actions du robot.
    """
    app = FastAPI(title='Reachy TicTacToe — MIA')
    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

    @app.get('/', response_class=HTMLResponse)
    def page():
        with open(os.path.join(STATIC_DIR, 'index.html'), encoding='utf-8') as f:
            return HTMLResponse(f.read())

    @app.get('/api/state')
    def state():
        return _snapshot(session, controller)

    @app.post('/api/game', status_code=202)
    def start_game():
        try:
            controller.start_game()
        except RobotBusy as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {'started': 'game'}

    @app.post('/api/moves-check', status_code=202)
    def check_moves():
        try:
            controller.check_moves()
        except RobotBusy as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {'started': 'moves_check'}

    @app.get('/api/calibration')
    def calibration():
        """Zones de calibration, en pixels de l'image PLEIN CADRE.

        Attention au repère : ``BOARD_CASES`` est exprimé relativement au
        plateau recadré, alors que ``BOARD_POSITION`` l'est dans l'image
        entière. On applique donc l'offset ici, pour que les rectangles
        puissent se superposer directement à ``/api/camera.jpg``.
        """
        from .. import config
        board = config.BOARD_POSITION
        dx, dy = board['left_x'], board['top_y']
        return {
            'board': {
                'x': dx, 'y': dy,
                'width': board['right_x'] - dx,
                'height': board['bottom_y'] - dy,
            },
            # BOARD_CASES : (left, right, top, bottom) par case.
            'cases': [
                {'x': int(left) + dx, 'y': int(top) + dy,
                 'width': int(right) - int(left),
                 'height': int(bottom) - int(top)}
                for row in config.BOARD_CASES
                for left, right, top, bottom in row
            ],
        }

    @app.get('/api/camera.jpg')
    def camera():
        frame = getattr(session.playground.reachy.right_camera,
                        'last_frame', None)
        if frame is None:
            # Pas d'image : réponse explicite, surtout pas une trace de
            # pile dans le navigateur.
            raise HTTPException(status_code=503,
                                detail='Aucune image de la caméra')
        ok, buffer = cv.imencode('.jpg', frame,
                                 [int(cv.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            raise HTTPException(status_code=503, detail='Encodage JPEG échoué')
        return Response(content=buffer.tobytes(), media_type='image/jpeg',
                        headers={'Cache-Control': 'no-store'})

    @app.get('/api/events')
    async def events():
        """Flux SSE : pousse l'état à chaque changement.

        On interroge l'instantané plutôt que de s'abonner à la session :
        cela couvre aussi les changements d'état du robot (action en
        cours), qui ne passent pas par ``GameState``.
        """
        async def stream():
            precedent = None
            while True:
                courant = _snapshot(session, controller)
                if courant != precedent:
                    precedent = courant
                    yield f'data: {json.dumps(courant)}\n\n'
                await asyncio.sleep(0.3)

        return StreamingResponse(stream(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-store',
                                          'X-Accel-Buffering': 'no'})

    return app
