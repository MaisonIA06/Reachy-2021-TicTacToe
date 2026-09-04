"""Tests de réactivité (latence du tour de Reachy).

Le goto() du SDK 2021 est BLOQUANT : il ne rend la main qu'à la fin du
mouvement. Tout time.sleep(duration) ajouté après un goto() double donc
le temps de chaque geste. Ici goto est mocké (retour immédiat) : le
temps mesuré ne contient QUE les sleeps résiduels du code — il doit
rester très en dessous des durées de mouvement demandées.
"""
import time
from unittest.mock import MagicMock

import numpy as np
import pytest

from reachy_tictactoe import behavior


@pytest.fixture
def sleep_budget(monkeypatch):
    """Exécute une fonction et renvoie le total des ``sleep`` DEMANDÉS.

    ⚠️ On ne chronomètre plus le temps réel : les seuils laissaient trop
    peu de marge (``play_pawn`` mesurait 1,07 s pour un seuil de 1,5 s) et
    le CI est tombé sur un runner chargé alors qu'aucun code de production
    n'avait changé. En interceptant ``time.sleep``, on mesure exactement
    ce que le test veut surveiller — les attentes que le code s'impose —
    sans dépendre de la vitesse de la machine. Les tests deviennent en
    prime instantanés.
    """
    import reachy_tictactoe.behavior as behavior_mod
    import reachy_tictactoe.tictactoe_playground as playground_mod
    import reachy_tictactoe.motors as motors_mod

    total = {'s': 0.0}

    def faux_sleep(duree):
        total['s'] += duree

    for module in (playground_mod, behavior_mod, motors_mod):
        monkeypatch.setattr(module.time, 'sleep', faux_sleep, raising=False)

    def run(fn, *args, **kwargs):
        total['s'] = 0.0
        fn(*args, **kwargs)
        return total['s']

    return run


# ---------------------------------------------------------------------------
# Plus de double attente après les goto() bloquants
# ---------------------------------------------------------------------------

class TestNoRedundantSleep:
    """goto() est bloquant : tout sleep(duration) qui le suit double le
    geste. Les budgets ci-dessous sont en secondes d'attente DEMANDÉE ;
    ils doivent rester très en dessous des durées de goto (1 à 2 s)."""

    def test_goto_position(self, playground, sleep_budget):
        attente = sleep_budget(
            playground.goto_position,
            {'r_arm.r_shoulder_pitch': 0.0}, 2.0)
        assert attente < 0.5

    def test_goto_rest_position(self, playground, sleep_budget):
        attente = sleep_budget(playground.goto_rest_position, 2.0)
        assert attente < 0.5

    def test_close_gripper(self, playground, sleep_budget):
        # Les courtes pauses de stabilisation du servo sont légitimes,
        # mais pas le sleep qui recopiait la durée du goto.
        playground.reachy.r_arm.r_gripper.present_position = -20.0
        attente = sleep_budget(playground.close_gripper)
        assert attente < 0.5

    def test_open_gripper(self, playground, sleep_budget):
        playground.reachy.r_arm.r_gripper.present_position = -6.0
        attente = sleep_budget(playground.open_gripper)
        assert attente < 0.3

    def test_look_at(self, playground, sleep_budget):
        attente = sleep_budget(playground.look_at, 0.5, 0.0, -0.6, 1.0)
        assert attente < 0.5

    def test_head_home(self, sleep_budget):
        attente = sleep_budget(behavior.head_home, MagicMock(), 1.0)
        assert attente < 0.5

    def test_play_pawn(self, playground, monkeypatch, sleep_budget):
        # Robot factice avec des lectures numériques plausibles.
        gripper = playground.reachy.r_arm.r_gripper
        gripper.present_position = -20.0
        gripper.present_load = 150.0
        playground.reachy.r_arm.r_shoulder_pitch.present_position = 10.0
        playground.reachy.r_arm.r_elbow_pitch.present_position = -60.0
        # Le playback 100 Hz de la trajectoire de dépose est un vrai
        # temps de mouvement, pas une attente : on l'exclut.
        monkeypatch.setattr(playground, 'play_trajectory', MagicMock())

        attente = sleep_budget(playground.play_pawn, 1, 5)

        # Il ne doit rester que les courtes pauses de stabilisation.
        assert attente < 1.5


# ---------------------------------------------------------------------------
# analyze_board ne re-vise le plateau que si la tête a bougé
# ---------------------------------------------------------------------------

class TestAnalyzeBoardLookAt:
    @pytest.fixture
    def camera_ready(self, playground):
        playground.reachy.right_camera.last_frame = np.zeros(
            (480, 640, 3), dtype=np.uint8)
        return playground

    def test_look_at_une_seule_fois_si_la_tete_n_a_pas_bouge(
            self, camera_ready):
        camera_ready.analyze_board()
        camera_ready.analyze_board()
        assert camera_ready.reachy.head.look_at.call_count == 1

    def test_look_at_refait_apres_un_mouvement_de_tete(self, camera_ready):
        camera_ready.analyze_board()
        camera_ready.look_at(0.3, 0.2, 0.0, duration=0.1)  # tête ailleurs
        camera_ready.analyze_board()
        # 1er analyze + look_at manuel + re-visée du 2e analyze
        assert camera_ready.reachy.head.look_at.call_count == 3

    def test_re_visee_apres_une_serie_d_analyses_echouees(self, camera_ready):
        # Avec le stub vision, is_board_valid échoue : chaque analyse
        # retourne None. Si la tête a été bousculée, le cache de visée
        # rendrait le jeu aveugle pour toujours — après une série
        # d'échecs, analyze_board doit re-viser le plateau.
        for _ in range(6):
            camera_ready.analyze_board()
        assert camera_ready.reachy.head.look_at.call_count == 2

    def test_reset_force_une_nouvelle_visee(self, camera_ready):
        # Nouvelle partie = nouvelle visée (la tête a pu bouger
        # pendant les célébrations ou un cooldown).
        camera_ready.analyze_board()
        camera_ready.reset()
        camera_ready.analyze_board()
        assert camera_ready.reachy.head.look_at.call_count == 2


# ---------------------------------------------------------------------------
# Le son « thinking » ne bloque pas le départ du bras
# ---------------------------------------------------------------------------

def test_thinking_n_attend_pas_la_fin_du_son(monkeypatch):
    """Le son doit être joué en tâche de fond, pas attendu.

    ⚠️ Ce test mesurait auparavant le temps écoulé (< 2,5 s pour une
    animation de ~1,5 s). La marge était trop étroite : il échouait par
    intermittence sur les machines chargées, jusqu'à faire tomber le CI
    sans qu'aucun code de production n'ait changé. On vérifie désormais
    le CONTRAT — le son part sur l'executor, il n'est pas appelé
    directement — ce qui ne dépend plus de la vitesse de la machine.
    """
    import threading

    fil_appelant = threading.current_thread()
    fils_du_son = []
    monkeypatch.setattr(
        behavior, 'play_sound_safe',
        lambda *a, **kw: fils_du_son.append(threading.current_thread()))

    soumissions = []
    vrai_submit = behavior._sound_executor.submit

    def submit_trace(fn, *a, **kw):
        soumissions.append(fn)
        return vrai_submit(fn, *a, **kw)

    monkeypatch.setattr(behavior._sound_executor, 'submit', submit_trace)

    behavior.thinking(MagicMock())
    # Laisser l'executor consommer sa file avant de conclure.
    behavior._sound_executor.submit(lambda: None).result(timeout=5)

    assert soumissions, 'le son doit être confié à l\'executor'
    assert fils_du_son, 'le son doit finir par être joué'
    assert fil_appelant not in fils_du_son, (
        'play_sound_safe ne doit pas être appelé dans le fil du geste : '
        'le bras attendrait la fin du son'
    )


def test_thinking_logge_l_echec_du_son(monkeypatch, caplog):
    # Le son est joué en tâche de fond : son échec ne doit pas être
    # avalé silencieusement (Future orphelin), mais loggé.
    import logging
    caplog.set_level(logging.WARNING, logger='reachy.tictactoe.behavior')

    def broken_sound(*args, **kwargs):
        raise RuntimeError('boom audio')

    monkeypatch.setattr(behavior, 'play_sound_safe', broken_sound)
    behavior.thinking(MagicMock())

    assert any('boom audio' in str(record.message)
               for record in caplog.records)
