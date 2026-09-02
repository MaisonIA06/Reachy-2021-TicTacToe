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

from concurrent.futures import ThreadPoolExecutor, as_completed
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode


logger = logging.getLogger('reachy.tictactoe.behavior')


# ============================================================================
# THREADPOOL GLOBAL POUR OPTIMISATION DES PERFORMANCES
# ============================================================================

# Pool de threads réutilisable (évite création/destruction répétée de threads)
_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="reachy_behavior_")

# Executor dédié aux sons joués en tâche de fond : UN seul worker, car le
# périphérique ALSA (hw:0,0) est exclusif — deux mpg123 simultanés
# échoueraient en « device busy ». La file d'attente sérialise les sons.
_sound_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="reachy_sound_")


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


def run_parallel_tasks(*tasks, timeout=TASK_TIMEOUT):
    """
    Exécute plusieurs tâches en parallèle avec gestion des erreurs et timeout.
    
    Args:
        *tasks: Fonctions à exécuter en parallèle
        timeout: Timeout global en secondes
        
    Returns:
        list: Résultats des tâches (ou None si erreur)
    """
    if not tasks:
        return []
    
    futures = [_executor.submit(task) for task in tasks]
    results = []
    
    try:
        for future in as_completed(futures, timeout=timeout):
            try:
                result = future.result(timeout=1)
                results.append(result)
            except Exception as e:
                logger.warning(f'Task failed: {e}')
                results.append(None)
    except TimeoutError:
        logger.warning(f'Parallel tasks timed out after {timeout}s')
        # Annuler les tâches en cours
        for future in futures:
            future.cancel()
    
    return results


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


def head_home(reachy, duration=1.0):
    """
    Remet la tête en position neutre
    
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

    # Exécuter en parallèle avec ThreadPoolExecutor
    run_parallel_tasks(antenna_movement, play_sound)
    
    logger.info('Ending behavior', extra={'behavior': 'sad'})

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
    
    # Exécuter en parallèle avec ThreadPoolExecutor
    run_parallel_tasks(antenna_movement, play_sound)
    
    logger.info('Ending behavior', extra={'behavior': 'surprise'})


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
    
    # Exécuter en parallèle avec ThreadPoolExecutor
    run_parallel_tasks(antenna_movement, play_sound)
    
    logger.info('Ending behavior', extra={'behavior': 'celebrate'})


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

    # Son en tâche de fond : le bras ne doit pas attendre la fin du MP3
    # pour commencer à jouer. Échec loggé via le callback.
    _sound_executor.submit(play_sound).add_done_callback(_log_sound_failure)
    run_parallel_tasks(antenna_movement)

    logger.info('Ending behavior', extra={'behavior': 'thinking'})
