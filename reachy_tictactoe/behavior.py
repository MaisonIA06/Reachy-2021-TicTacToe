"""
Comportements émotionnels de Reachy adaptés pour le SDK 2021
Optimisé avec ThreadPoolExecutor pour une meilleure gestion des ressources
"""
import time
import logging
import numpy as np
import os
import random
import subprocess
import shutil

from concurrent.futures import ThreadPoolExecutor
# ⚠️ Avant Python 3.11, concurrent.futures.TimeoutError est une classe
# DISTINCTE du TimeoutError natif : un `except TimeoutError` nu ne
# l'attrape pas. Le robot tourne en 3.10 — d'où l'import explicite.
from concurrent.futures import TimeoutError as FutureTimeoutError
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode


logger = logging.getLogger('reachy.tictactoe.behavior')


# ============================================================================
# UN EXECUTOR PAR RESSOURCE EXCLUSIVE
# ============================================================================
# Chaque executor n'a qu'UN worker : il ne sert pas à paralléliser, mais à
# garantir qu'une ressource physique exclusive n'est pilotée que par un
# seul fil à la fois. La sérialisation est ainsi structurelle, et non
# laissée à la vigilance des appelants.

# Executor dédié aux sons joués en tâche de fond : UN seul worker, car le
# périphérique ALSA (hw:0,0) est exclusif — deux mpg123 simultanés
# échoueraient en « device busy ». La file d'attente sérialise les sons.
_sound_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reachy_sound_")

# Executor dédié aux antennes : UN seul worker, car les deux antennes sont
# une ressource exclusive — deux animations simultanées écriraient
# concurremment dans `goal_position` et se disputeraient la consigne.
# C'est ce qui permet de rendre `thinking` non bloquant sans risque : la
# sérialisation est structurelle, pas laissée à la vigilance des appelants.
_antenna_executor = ThreadPoolExecutor(max_workers=1,
                                       thread_name_prefix="reachy_antenna_")


def _log_sound_failure(future):
    """Callback de fin : un son en tâche de fond ne doit pas échouer
    silencieusement (Future orphelin)."""
    exc = future.exception()
    if exc is not None:
        logger.warning(f'Background sound failed: {exc}')


def play_sound_background(sound_path, device='hw:0,0'):
    """Joue un son SANS bloquer l'appelant.

    ``play_sound_safe`` attend la fin de la lecture (jusqu'à 10 s) : appelée
    en pleine séquence de jeu, elle fige le bras. On passe donc par
    l'executor à un worker, qui sérialise les sons sur le périphérique ALSA
    exclusif et logge les échecs.
    """
    future = _sound_executor.submit(play_sound_safe, sound_path, device)
    future.add_done_callback(_log_sound_failure)
    return future


# Timeout global pour les tâches parallèles (sécurité)
TASK_TIMEOUT = 15  # secondes


def _log_animation_failure(future):
    """Callback de fin : une animation lancée en fond ne doit pas échouer
    silencieusement (Future orphelin)."""
    exc = future.exception()
    if exc is not None:
        logger.warning(f'Antenna animation failed: {exc}')


def animate_antennas(animation, wait=True, timeout=TASK_TIMEOUT):
    """Joue une animation d'antennes sur l'executor dédié.

    Args:
        animation: fonction sans argument qui pilote les antennes
        wait: True pour attendre la fin (fin de partie : la durée EST le
            spectacle), False pour rendre la main aussitôt (pendant une
            partie : le bras doit pouvoir partir tout de suite)
        timeout: sécurité pour le mode bloquant

    Returns:
        Future: poignée sur l'animation, pour l'attendre plus tard
    """
    future = _antenna_executor.submit(animation)
    # Dans les deux modes : un échec survenu APRÈS notre attente (ou
    # pendant, en mode non bloquant) doit rester visible dans les logs.
    future.add_done_callback(_log_animation_failure)

    if not wait:
        return future

    try:
        future.result(timeout=timeout)
    except FutureTimeoutError:
        # ⚠️ Un seul worker : l'animation continue d'occuper la file et les
        # suivantes attendront derrière elle. On ne peut pas l'annuler (une
        # tâche démarrée n'est pas interruptible), mais l'incident doit être
        # signalé — un dépassement de TASK_TIMEOUT sur une animation de
        # quelques secondes trahit un robot qui ne répond plus.
        logger.warning(
            f'Antenna animation still running after {timeout}s — '
            'les animations suivantes attendront derrière elle')
    except Exception as erreur:
        # Une animation ratée ne doit jamais interrompre la partie.
        logger.warning(f'Antenna animation failed: {erreur}')

    return future


def _animate_and_play(animation, play_sound, timeout=TASK_TIMEOUT):
    """Animation et son en parallèle, en attendant les deux.

    Réservé aux comportements de FIN de partie : rien ne les suit, donc
    leur durée ne coûte aucune latence de jeu.

    ⚠️ Le son passe par ``_sound_executor`` (un seul worker) et non par le
    pool généraliste : le périphérique ALSA est exclusif, deux ``mpg123``
    simultanés échoueraient. Un son de célébration pouvait auparavant
    recouvrir un son de réflexion encore en cours.
    """
    son = _sound_executor.submit(play_sound)
    son.add_done_callback(_log_sound_failure)

    animation_future = animate_antennas(animation, wait=True, timeout=timeout)

    try:
        son.result(timeout=timeout)
    except Exception as erreur:
        # Déjà loggé par le callback ; on ne propage pas.
        logger.debug(f'End-of-game sound: {erreur}')

    return animation_future


def _find_audio_player():
    """
    Trouve un lecteur audio disponible sur le système.
    
    Returns:
        str: Chemin du lecteur ou None si non trouvé
    """
    for player in ['mpg123', 'ffplay', 'aplay', 'paplay']:
        path = shutil.which(player)
        if path:
            return player
    return None


def play_sound_safe(sound_path, device='hw:0,0'):
    """
    Joue un son de manière sécurisée avec fallback.
    
    Args:
        sound_path: Chemin vers le fichier audio
        device: Périphérique audio (défaut: hw:0,0)
    """
    if not os.path.exists(sound_path):
        logger.warning(f'Sound file not found: {sound_path}')
        return
    
    player = _find_audio_player()
    if player is None:
        logger.warning('No audio player found (mpg123/ffplay/aplay)')
        return
    
    try:
        if player == 'mpg123':
            cmd = [player, '-a', device, '-q', sound_path]
        elif player == 'ffplay':
            cmd = [player, '-nodisp', '-autoexit', '-loglevel', 'quiet', sound_path]
        else:
            cmd = [player, '-q', sound_path]
        
        subprocess.run(cmd, check=False, timeout=10)
    except subprocess.TimeoutExpired:
        logger.warning('Sound playback timed out')
    except Exception as e:
        logger.error(f'Sound playback failed: {e}')


def move_antennas(reachy, left, right, duration=1.0, wait=True):
    """Amène les deux antennes à une position donnée, via l'executor dédié.

    À préférer à un ``goto`` direct partout hors d'une animation : c'est ce
    qui rend l'exclusivité des antennes structurelle plutôt que dépendante
    de la vigilance de l'appelant.

    ⚠️ **Ne JAMAIS appeler depuis une animation déjà en cours** : l'executor
    n'a qu'un worker, une attente sur lui-même se bloquerait pour toujours.
    Les animations utilisent ``head_home``, qui appelle ``goto``
    directement — elles s'exécutent déjà dans le worker.
    """
    def mouvement():
        goto(
            goal_positions={
                reachy.head.l_antenna: left,
                reachy.head.r_antenna: right,
            },
            duration=duration,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )

    return animate_antennas(mouvement, wait=wait)


def head_home(reachy, duration=1.0):
    """
    Remet la tête en position neutre.

    ⚠️ Appelée DEPUIS les animations (donc déjà dans le worker antennes) :
    elle fait un ``goto`` direct, sans repasser par l'executor — sinon
    l'animation attendrait sa propre file et se bloquerait pour toujours.

    Args:
        reachy: Instance ReachySDK
        duration: Durée du mouvement
    """
    # CORRECTION: Utiliser objets Joint au lieu de chaînes
    goto(
        goal_positions={
            reachy.head.l_antenna: 0.0,
            reachy.head.r_antenna: 0.0,
        },
        duration=duration,
        interpolation_mode=InterpolationMode.MINIMUM_JERK,
    )


def sad(reachy):
    """
    Comportement de tristesse (défaite)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'sad'})

    # Fonction pour le mouvement des antennes
    def antenna_movement():
        # Séquence de positions pour exprimer la tristesse (optimisée)
        positions = [
            (150, 1.0),   # Antennes vers le haut (réduit de 1.5 à 1.0)
            (110, 1.0),   # Légèrement baissées
            (150, 1.0),   # Remontées
            (90, 1.0),    # Position intermédiaire
            (20, 1.0),    # Position basse (tristesse)
        ]
        
        for antenna_pos, dur in positions:
            reachy.head.l_antenna.goal_position = antenna_pos
            reachy.head.r_antenna.goal_position = -antenna_pos
            time.sleep(dur)
    
    # Fonction pour jouer un son aléatoire
    def play_sound():
        sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        sound_files = [
            'Coup_de_chance.mp3',
            'Laissé_gagner.mp3',
            'Le_jeu_est_truqué.mp3'
        ]
        selected_sound = random.choice(sound_files)
        sound_path = os.path.join(sounds_dir, selected_sound)
        logger.info(f'Playing sound: {selected_sound}')
        play_sound_safe(sound_path)

    # Fin de partie : on attend la fin du spectacle.
    animation = _animate_and_play(antenna_movement, play_sound)

    logger.info('Ending behavior', extra={'behavior': 'sad'})
    return animation

def surprise(reachy):
    """
    Comportement de surprise (égalité)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'surprise'})
    
    # Fonction pour le mouvement des antennes (animation optimisée)
    def antenna_movement():
        # 1. Mouvement rapide et asymétrique initial (surprise)
        goto(
            goal_positions={
                reachy.head.l_antenna: -5,
                reachy.head.r_antenna: -90,
            },
            duration=0.25,  # Optimisé
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        
        # 2. Retour au centre
        goto(
            goal_positions={
                reachy.head.l_antenna: 0,
                reachy.head.r_antenna: 0,
            },
            duration=0.3,  # Optimisé
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        
        # 3. Oscillation symétrique (réduite à 1 cycle)
        for _ in range(1):
            goto(
                goal_positions={
                    reachy.head.l_antenna: 45,
                    reachy.head.r_antenna: -45,
                },
                duration=0.4,  # Optimisé
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            
            goto(
                goal_positions={
                    reachy.head.l_antenna: -45,
                    reachy.head.r_antenna: 45,
                },
                duration=0.4,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
        
        # 4. Animation finale ondulante (réduite)
        dur = 1.5  # Réduit de 2 à 1.5
        t = np.linspace(0, dur, int(dur * 100))
        pos = 30 * np.sin(2 * np.pi * 2 * t)
        
        for p in pos:
            reachy.head.l_antenna.goal_position = p
            reachy.head.r_antenna.goal_position = -p
            time.sleep(0.01)
        
        head_home(reachy, duration=0.8)  # Optimisé
    
    # Fonction pour jouer le son d'égalité
    def play_sound():
        sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        sound_path = os.path.join(sounds_dir, 'Egalité.mp3')
        logger.info('Playing draw sound: Egalité.mp3')
        play_sound_safe(sound_path)
    
    # Fin de partie : on attend la fin du spectacle.
    animation = _animate_and_play(antenna_movement, play_sound)

    logger.info('Ending behavior', extra={'behavior': 'surprise'})
    return animation


def celebrate(reachy):
    """
    Comportement de célébration plus élaboré
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'celebrate'})
    
    # Fonction pour le mouvement des antennes (optimisée)
    def antenna_movement():
        # Animation pour une grande victoire (réduite à 2 cycles)
        for _ in range(2):
            goto(
                goal_positions={
                    reachy.head.l_antenna: 180,
                    reachy.head.r_antenna: -180,
                },
                duration=0.4,  # Optimisé
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            
            goto(
                goal_positions={
                    reachy.head.l_antenna: 0,
                    reachy.head.r_antenna: 0,
                },
                duration=0.4,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            
        # Animation finale ondulante (réduite)
        dur = 1.5  # Réduit de 2 à 1.5
        t = np.linspace(0, dur, int(dur * 100))
        pos = 45 * np.sin(2 * np.pi * 3 * t)
        
        for p in pos:
            reachy.head.l_antenna.goal_position = p
            reachy.head.r_antenna.goal_position = -p
            time.sleep(0.01)
        
        head_home(reachy, duration=0.8)  # Optimisé
    
    # Fonction pour jouer un son de célébration
    def play_sound():
        sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        sound_files = [
            "J'enregistre_cette_victoire.mp3",
            'Mon_processeur_jubile.mp3',
            'Statistiquement.mp3'
        ]
        selected_sound = random.choice(sound_files)
        sound_path = os.path.join(sounds_dir, selected_sound)
        logger.info(f'Playing celebration sound: {selected_sound}')
        play_sound_safe(sound_path)
    
    # Fin de partie : on attend la fin du spectacle.
    animation = _animate_and_play(antenna_movement, play_sound)

    logger.info('Ending behavior', extra={'behavior': 'celebrate'})
    return animation


def thinking(reachy, used_sounds=None):
    """
    Comportement de réflexion (pendant que Reachy calcule son coup)
    
    Args:
        reachy: Instance ReachySDK
        used_sounds: Set des sons déjà utilisés (pour éviter les doublons)
    """
    logger.info('Starting behavior', extra={'behavior': 'thinking'})
    
    if used_sounds is None:
        used_sounds = set()
    
    # Fonction pour le mouvement des antennes (optimisée)
    def antenna_movement():
        # Mouvement plus court pour la réflexion
        dur = 1.5  # Réduit de 2 à 1.5
        t = np.linspace(0, dur, int(dur * 100))
        pos = 30 + 20 * np.sin(2 * np.pi * 0.5 * t)
        
        for p in pos:
            reachy.head.l_antenna.goal_position = p
            reachy.head.r_antenna.goal_position = p  # Même direction = réflexion
            time.sleep(0.01)
        
        # Retour à la position neutre (les antennes glissent d'elles-mêmes,
        # inutile d'attendre : le bras enchaîne immédiatement)
        reachy.head.l_antenna.goal_position = 0.0
        reachy.head.r_antenna.goal_position = 0.0
        
    # Fonction pour jouer un son aléatoire
    def play_sound():
        sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
        sound_files = [
            'Calcul_en_cours.mp3',
            'Je_joue_stratègique.mp3',
            'Le_bon_coup.mp3',
            'Observe.mp3',
            'Téléchargement.mp3'
        ]
        
        # Filtrer les sons non utilisés
        available_sounds = [s for s in sound_files if s not in used_sounds]

        # Si tous les sons ont été utilisés, réinitialiser
        if not available_sounds:
            logger.info('Tous les sons ont été utilisés, réinitialisation')
            used_sounds.clear()
            available_sounds = sound_files

        # Choisir un son aléatoire
        selected_sound = random.choice(available_sounds)
        used_sounds.add(selected_sound)
        
        sound_path = os.path.join(sounds_dir, selected_sound)
        logger.info(f'Playing sound: {selected_sound}')
        play_sound_safe(sound_path)

    # Son ET antennes en tâche de fond : le bras ne doit attendre ni la fin
    # du MP3, ni celle de l'animation. `thinking` est appelé juste avant que
    # Reachy choisisse et joue son coup — bloquer ici immobilisait le bras
    # ~1,5 s à chaque tour, soit 6 à 7 s par partie. Antennes et bras ne
    # partagent aucun moteur : rien ne justifiait de les sérialiser.
    _sound_executor.submit(play_sound).add_done_callback(_log_sound_failure)
    animation = animate_antennas(antenna_movement, wait=False)

    logger.info('Ending behavior', extra={'behavior': 'thinking'})
    return animation
