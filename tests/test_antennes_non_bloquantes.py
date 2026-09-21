"""Les antennes doivent s'animer PENDANT que le bras joue.

``thinking`` est déclenché juste avant que Reachy choisisse et joue son
coup (``game_launcher`` → ``run_thinking_behavior``). Tant que cette
animation bloque l'appelant, le bras reste immobile ~1,5 s à chaque tour,
soit 6 à 7 s perdues par partie. Les antennes et le bras ne partagent
aucun moteur : rien ne justifie de les sérialiser.

⚠️ Les antennes restent une ressource EXCLUSIVE entre elles : deux
animations simultanées écriraient concurremment dans ``goal_position`` et
se disputeraient la consigne. D'où un executor à un seul worker, comme
pour le périphérique ALSA.
"""
import threading
import time

import pytest
from unittest.mock import MagicMock

from reachy_tictactoe import behavior


class AntenneFactice:
    """Antenne qui MÉMORISE ses consignes.

    ⚠️ Indispensable : sur un ``MagicMock``, lire ``goal_position`` renvoie
    un mock — jamais ``None``. Une assertion du type « la consigne n'est
    pas None » resterait verte même si l'animation était entièrement
    supprimée. Il faut un objet qui enregistre vraiment les écritures.
    """

    def __init__(self):
        self.consignes = []

    @property
    def goal_position(self):
        return self.consignes[-1] if self.consignes else None

    @goal_position.setter
    def goal_position(self, valeur):
        self.consignes.append(valeur)


@pytest.fixture
def robot():
    reachy = MagicMock(name='reachy')
    reachy.head.l_antenna = AntenneFactice()
    reachy.head.r_antenna = AntenneFactice()
    return reachy


@pytest.fixture(autouse=True)
def sons_muets(monkeypatch):
    """Aucun son réel : la suite ne doit pas monopoliser le worker ALSA."""
    monkeypatch.setattr(behavior, 'play_sound_safe', lambda *a, **kw: None)


@pytest.fixture
def compteur_de_concurrence(monkeypatch):
    """Compte les animations d'antennes simultanées.

    ⚠️ ``behavior.time`` EST le module ``time`` global : le patcher affecte
    tout le programme, y compris les pauses de stabilisation servo du bras
    dans un autre fil. Sans le filtre sur le nom du fil, on compterait un
    bras et des antennes comme « deux animations concurrentes ».
    """
    etat = {'en_cours': 0, 'maximum': 0}
    verrou = threading.Lock()
    vrai_sleep = time.sleep

    def faux_sleep(duree):
        if not threading.current_thread().name.startswith('reachy_antenna_'):
            return
        with verrou:
            etat['en_cours'] += 1
            etat['maximum'] = max(etat['maximum'], etat['en_cours'])
        # ⚠️ sleep(0) cède le GIL sans dormir : deux workers s'entrelaceraient
        # et seraient détectés, alors qu'un vrai délai coûterait des secondes
        # (sous Windows, sleep(0.001) dort ~15 ms, × 300 itérations).
        vrai_sleep(0)
        with verrou:
            etat['en_cours'] -= 1

    monkeypatch.setattr(behavior.time, 'sleep', faux_sleep)
    return etat


# ---------------------------------------------------------------------------
# thinking ne bloque plus le bras
# ---------------------------------------------------------------------------

def test_thinking_rend_la_main_avant_la_fin_de_l_animation(robot, monkeypatch):
    """Le cœur du gain : l'appelant repart pendant que les antennes bougent."""
    barriere = threading.Event()
    premier_passage = {'fait': False}

    def sleep_bloquant(duree):
        if not premier_passage['fait']:
            premier_passage['fait'] = True
            barriere.wait(timeout=3)

    monkeypatch.setattr(behavior.time, 'sleep', sleep_bloquant)

    animation = behavior.thinking(robot)

    assert animation is not None, (
        'thinking doit rendre une poignée sur son animation, pour que '
        "l'appelant puisse l'attendre s'il en a besoin"
    )
    assert not animation.done(), (
        "thinking ne doit pas attendre la fin de l'animation : le bras "
        'perdrait ~1,5 s à chaque tour'
    )

    barriere.set()
    animation.result(timeout=5)
    assert animation.done()


def test_l_animation_de_thinking_s_execute_bien(robot, monkeypatch):
    """Non bloquant ne veut pas dire jamais exécuté."""
    monkeypatch.setattr(behavior.time, 'sleep', lambda duree: None)

    animation = behavior.thinking(robot)
    animation.result(timeout=5)

    assert animation.exception() is None
    # L'ondulation fait 1,5 s à 100 Hz, soit 150 consignes, plus le retour
    # à 0 : on vérifie le balayage complet, pas sa simple existence.
    assert len(robot.head.l_antenna.consignes) == 151
    assert len(robot.head.r_antenna.consignes) == 151
    assert robot.head.l_antenna.consignes[-1] == 0.0, (
        'les antennes doivent revenir au neutre en fin de réflexion')


def test_thinking_ne_bloque_pas_dans_le_fil_appelant(robot, monkeypatch):
    """L'animation doit tourner dans un AUTRE fil que celui du geste."""
    fils = []
    monkeypatch.setattr(
        behavior.time, 'sleep',
        lambda duree: fils.append(threading.current_thread()))

    animation = behavior.thinking(robot)
    animation.result(timeout=5)

    assert fils, "l'animation doit bien s'exécuter"
    assert threading.current_thread() not in fils


# ---------------------------------------------------------------------------
# Les antennes restent une ressource exclusive
# ---------------------------------------------------------------------------

def test_deux_thinking_ne_se_chevauchent_jamais(robot, compteur_de_concurrence):
    """Deux tours rapprochés ne doivent pas se disputer les antennes."""
    animations = [behavior.thinking(robot), behavior.thinking(robot)]
    for animation in animations:
        animation.result(timeout=10)

    assert compteur_de_concurrence['maximum'] == 1, (
        'deux animations simultanées écriraient concurremment dans '
        'goal_position : la consigne serait imprévisible'
    )


def test_une_celebration_ne_chevauche_pas_une_reflexion_en_cours(
        robot, compteur_de_concurrence):
    """Cas réel : Reachy gagne, la célébration suit de près le dernier coup."""
    reflexion = behavior.thinking(robot)
    behavior.celebrate(robot)
    reflexion.result(timeout=10)

    assert compteur_de_concurrence['maximum'] == 1


# ---------------------------------------------------------------------------
# Les animations de fin de partie restent bloquantes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('nom', ['celebrate', 'sad', 'surprise'])
def test_les_animations_de_fin_de_partie_restent_bloquantes(
        nom, robot, monkeypatch):
    """Rien ne les suit : leur durée est le spectacle, pas une latence."""
    monkeypatch.setattr(behavior.time, 'sleep', lambda duree: None)

    animation = getattr(behavior, nom)(robot)

    assert animation.done(), (
        f'{nom} se joue en fin de partie : elle doit être terminée quand '
        'la fonction rend la main'
    )


# ---------------------------------------------------------------------------
# Le périphérique ALSA reste exclusif, lui aussi
# ---------------------------------------------------------------------------

def test_les_sons_ne_se_chevauchent_jamais(robot, monkeypatch):
    """hw:0,0 est exclusif : deux mpg123 simultanés échoueraient."""
    etat = {'en_cours': 0, 'maximum': 0}
    verrou = threading.Lock()
    vrai_sleep = time.sleep

    def son_lent(*args, **kwargs):
        with verrou:
            etat['en_cours'] += 1
            etat['maximum'] = max(etat['maximum'], etat['en_cours'])
        vrai_sleep(0.01)
        with verrou:
            etat['en_cours'] -= 1

    monkeypatch.setattr(behavior, 'play_sound_safe', son_lent)
    monkeypatch.setattr(behavior.time, 'sleep', lambda duree: None)

    reflexion = behavior.thinking(robot)
    behavior.celebrate(robot)
    reflexion.result(timeout=10)
    behavior._sound_executor.submit(lambda: None).result(timeout=10)

    assert etat['maximum'] == 1, (
        'le son de célébration passait par le pool à 3 workers : il pouvait '
        'recouvrir un son de réflexion encore en cours'
    )


# ---------------------------------------------------------------------------
# Le jeu consomme bien la version non bloquante
# ---------------------------------------------------------------------------

def test_run_thinking_behavior_ne_bloque_pas(playground, monkeypatch):
    monkeypatch.setattr(behavior.time, 'sleep', lambda duree: None)

    animation = playground.run_thinking_behavior()

    assert animation is not None, (
        'le playground doit propager la poignée : sans elle, impossible '
        "d'attendre les antennes avant de couper le couple de la tête"
    )
    animation.result(timeout=5)


# ---------------------------------------------------------------------------
# play_pawn ne doit pas non plus attendre ses antennes
# ---------------------------------------------------------------------------

def test_play_pawn_n_attend_pas_ses_antennes(playground, monkeypatch):
    """Les deux gestes d'antennes de play_pawn coûtaient 1 s chacun.

    ``goto`` est bloquant : relever puis rabaisser les antennes immobilisait
    le bras 2 s par tour, alors qu'ils ne partagent aucun moteur.
    """
    gripper = playground.reachy.r_arm.r_gripper
    gripper.present_position = -20.0
    monkeypatch.setattr(playground, 'play_trajectory', MagicMock())

    appels = []
    vrai_move = behavior.move_antennas

    def espion(reachy, left, right, duration=1.0, wait=True):
        appels.append({'left': left, 'right': right, 'wait': wait})
        return vrai_move(reachy, left, right, duration=duration, wait=wait)

    monkeypatch.setattr(behavior, 'move_antennas', espion)

    playground.play_pawn(grab_index=1, box_index=5)

    assert len(appels) == 2, 'antennes relevées puis remises au neutre'
    assert all(not appel['wait'] for appel in appels), (
        'play_pawn ne doit attendre aucun de ses deux gestes d\'antennes'
    )
    assert appels[-1]['left'] == 0.0, 'retour au neutre en fin de coup'


def test_move_antennas_s_execute_dans_le_worker_dedie(robot, monkeypatch):
    """L'exclusivité est structurelle : toute consigne part du worker unique.

    C'est ce qui garantit qu'une animation de réflexion encore en cours ne
    peut pas se disputer les antennes avec le geste de ``play_pawn``.
    """
    fils = []
    monkeypatch.setattr(
        behavior, 'goto',
        lambda **kwargs: fils.append(threading.current_thread().name))

    behavior.move_antennas(robot, 45, -45, duration=1.0, wait=False)
    behavior.move_antennas(robot, 0.0, 0.0, duration=1.0, wait=True)

    assert len(fils) == 2
    assert all(nom.startswith('reachy_antenna_') for nom in fils), (
        f'consignes émises hors du worker dédié : {fils}'
    )


# ---------------------------------------------------------------------------
# Une animation interminable ne doit pas faire tomber la partie
# ---------------------------------------------------------------------------

def test_une_animation_trop_longue_est_signalee_sans_lever(caplog):
    """Un seul worker : l'incident doit être visible dans les logs."""
    import logging
    caplog.set_level(logging.WARNING, logger='reachy.tictactoe.behavior')

    liberation = threading.Event()

    def animation_interminable():
        liberation.wait(timeout=10)

    behavior.animate_antennas(animation_interminable, wait=True, timeout=0.05)

    assert any('still running' in str(enregistrement.message)
               for enregistrement in caplog.records), (
        "un dépassement de délai doit être signalé : les animations "
        'suivantes attendent derrière celle-ci'
    )

    liberation.set()
    behavior._antenna_executor.submit(lambda: None).result(timeout=10)
