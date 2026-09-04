"""API et page de l'interface web.

Le serveur ne parle jamais au SDK : il ne connaît que la ``GameSession``
(état du jeu) et le ``RobotController`` (actions sérialisées). C'est ce
qui permet de le tester sans robot.
"""
import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import asdict

import cv2 as cv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .calibration import apply_calibration
from .controller import RobotBusy

logger = logging.getLogger('reachy.tictactoe.webapp')

STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')

#: Intervalle maximal entre deux messages SSE, même sans changement.
#: Permet au navigateur de distinguer « rien ne bouge » de « serveur mort ».
HEARTBEAT_SECONDS = 8.0


#: Couleurs BGR de la superposition, cohérentes avec la charte MIA.
_OVERLAY_BOARD = (92, 58, 26)        # navy #1a3a5c
_OVERLAY_CASE = (90, 96, 181)        # terracotta #b5605a


def board_rects():
    """Zone du plateau et des 9 cases, en pixels de l'image PLEIN CADRE.

    ⚠️ ``BOARD_CASES`` est exprimé relativement au plateau recadré, alors
    que ``BOARD_POSITION`` l'est dans l'image entière : l'offset est
    appliqué ici, une fois pour toutes.
    """
    from .. import config
    board = config.BOARD_POSITION
    dx, dy = board['left_x'], board['top_y']
    zone = {'x': dx, 'y': dy,
            'width': board['right_x'] - dx,
            'height': board['bottom_y'] - dy}
    # BOARD_CASES : (left, right, top, bottom) par case.
    cases = [
        {'x': int(left) + dx, 'y': int(top) + dy,
         'width': int(right) - int(left), 'height': int(bottom) - int(top)}
        for row in config.BOARD_CASES
        for left, right, top, bottom in row
    ]
    return zone, cases


def _annotate(frame, crop=False, overlay=False, margin=0.06):
    """Superpose les zones de calibration et/ou recadre sur le plateau."""
    zone, cases = board_rects()
    image = frame.copy()

    if overlay:
        cv.rectangle(image, (zone['x'], zone['y']),
                     (zone['x'] + zone['width'], zone['y'] + zone['height']),
                     _OVERLAY_BOARD, 2)
        for i, case in enumerate(cases, start=1):
            cv.rectangle(image, (case['x'], case['y']),
                         (case['x'] + case['width'], case['y'] + case['height']),
                         _OVERLAY_CASE, 2)
            cv.putText(image, str(i), (case['x'] + 4, case['y'] + 18),
                       cv.FONT_HERSHEY_SIMPLEX, 0.5, _OVERLAY_CASE, 1)

    if crop:
        h, w = image.shape[:2]
        mx = int(zone['width'] * margin)
        my = int(zone['height'] * margin)
        x1 = max(0, zone['x'] - mx)
        y1 = max(0, zone['y'] - my)
        x2 = min(w, zone['x'] + zone['width'] + mx)
        y2 = min(h, zone['y'] + zone['height'] + my)
        if x2 > x1 and y2 > y1:
            image = image[y1:y2, x1:x2]

    return image


def should_emit(current, previous, elapsed, heartbeat=HEARTBEAT_SECONDS):
    """Faut-il pousser l'état sur le flux SSE ?

    On émet à chaque changement, et **au moins** toutes les ``heartbeat``
    secondes même si rien ne bouge : sans ce battement, une longue période
    calme serait indiscernable d'un serveur mort côté navigateur, qui
    afficherait un état périmé en silence.
    """
    return current != previous or elapsed >= heartbeat


def _snapshot(session, controller, health=None):
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
            # 'frozen' = contrôleur moteur planté : le robot répond mais
            # aucune consigne n'aboutit. Sans ce signal, la panne est
            # indétectable depuis l'interface.
            'motors': health.status if health is not None else 'unknown',
        },
    }


def create_app(session, controller, health=None):
    """Construit l'application FastAPI.

    Args:
        session: ``GameSession`` — source de l'état du jeu.
        controller: ``RobotController`` — lance les actions du robot.
        health: ``MotorHealth`` optionnel — surveillance du bus moteur.
    """
    app = FastAPI(title='Reachy TicTacToe — MIA')
    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')

    @app.get('/', response_class=HTMLResponse)
    def page():
        with open(os.path.join(STATIC_DIR, 'index.html'), encoding='utf-8') as f:
            return HTMLResponse(f.read())

    @app.get('/api/state')
    def state():
        return _snapshot(session, controller, health)

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

    @app.post('/api/stop', status_code=202)
    def stop_action():
        """Interrompt l'action en cours, partie ou parcours (coopératif)."""
        action = controller.stop()
        if action is None:
            raise HTTPException(status_code=409,
                                detail='Aucune action en cours à arrêter')
        return {'stopping': action}

    @app.post('/api/system/recover', status_code=202)
    def recover():
        """Redémarre le contrôleur moteur de Pollen, puis cette interface.

        Répare le plantage de ``ros2_control_node`` (voir CLAUDE.md).
        Le script est lancé DÉTACHÉ : il redémarre ce serveur, donc il ne
        survivrait pas s'il restait notre processus enfant. C'est systemd
        qui nous relance, et le navigateur se reconnecte tout seul.
        """
        script = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '..', '..',
            'scripts', 'systemd', 'recover_sdk.sh'))
        if not os.path.exists(script):
            raise HTTPException(status_code=500,
                                detail='Script de récupération introuvable')

        # Réservation atomique : redémarrer le contrôleur pendant une
        # partie couperait le bras en pleine trajectoire, pion serré.
        # Tester `running` puis agir laisserait cette fenêtre ouverte.
        try:
            with controller.reserve('recovery'):
                logger.warning('Récupération du contrôleur moteur demandée')
                subprocess.Popen(['bash', script],
                                 stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        except RobotBusy as e:
            raise HTTPException(status_code=409, detail=str(e))
        return {'recovering': True}

    @app.get('/api/calibration')
    def calibration():
        """Zones de calibration, en pixels de l'image PLEIN CADRE."""
        zone, cases = board_rects()
        frame = getattr(session.playground.reachy.right_camera,
                        'last_frame', None)
        height, width = (frame.shape[:2] if frame is not None else (None, None))
        return {
            'board': zone,
            'cases': cases,
            # L'interface doit convertir ses clics en pixels image : elle a
            # besoin des dimensions réelles, pas de celles de l'affichage.
            'image': {'width': width, 'height': height},
        }

    @app.put('/api/calibration')
    def save_calibration(payload: dict):
        """Enregistre une calibration et la rend active immédiatement.

        La réservation du robot est atomique : tester ``running`` puis
        agir laisserait une partie démarrer entre les deux et voir la
        calibration changer en plein ``analyze_board``.
        """
        frame = getattr(session.playground.reachy.right_camera,
                        'last_frame', None)
        image = (None if frame is None
                 else {'width': frame.shape[1], 'height': frame.shape[0]})
        try:
            with controller.reserve('calibration'):
                board_position, _ = apply_calibration(
                    payload['board'], payload['cases'], image=image)
        except RobotBusy as e:
            raise HTTPException(status_code=409, detail=str(e))
        except KeyError as e:
            raise HTTPException(status_code=422,
                                detail=f'Champ manquant : {e}')
        except (ValueError, TypeError) as e:
            # TypeError : coordonnées non numériques (NaN sérialisé en
            # null quand l'image n'a pas pu être mesurée côté navigateur).
            raise HTTPException(status_code=422, detail=str(e))
        return {'saved': board_position}

    @app.get('/api/camera.jpg')
    def camera(crop: bool = False, overlay: bool = False, margin: float = 0.06):
        """Image de la caméra droite.

        Args:
            crop: recadrer sur la zone calibrée du plateau. La caméra voit
                bien plus large que le jeu (bureau, clavier…) ; le recadrage
                donne une vue centrée sur le plateau.
            overlay: dessiner la zone du plateau et les 9 cases telles que
                la vision les découpe — c'est ce qui permet de VOIR si la
                calibration est juste.
            margin: marge autour du plateau lors du recadrage, en fraction
                de sa taille (0.06 = 6 %).
        """
        frame = getattr(session.playground.reachy.right_camera,
                        'last_frame', None)
        if frame is None:
            # Pas d'image : réponse explicite, surtout pas une trace de
            # pile dans le navigateur.
            raise HTTPException(status_code=503,
                                detail='Aucune image de la caméra')

        if overlay or crop:
            frame = _annotate(frame, crop=crop, overlay=overlay, margin=margin)

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

        Un état identique est renvoyé au moins toutes les
        ``HEARTBEAT_SECONDS`` : sans ce battement, une longue période sans
        changement serait indiscernable d'un serveur mort, et l'interface
        afficherait un état périmé en silence.
        """
        async def stream():
            precedent = None
            dernier_envoi = 0.0
            while True:
                courant = _snapshot(session, controller, health)
                maintenant = time.monotonic()
                if should_emit(courant, precedent,
                               maintenant - dernier_envoi):
                    precedent = courant
                    dernier_envoi = maintenant
                    yield f'data: {json.dumps(courant)}\n\n'
                await asyncio.sleep(0.3)

        return StreamingResponse(stream(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-store',
                                          'X-Accel-Buffering': 'no'})

    return app
