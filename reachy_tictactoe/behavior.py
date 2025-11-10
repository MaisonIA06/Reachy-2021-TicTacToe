"""
Comportements émotionnels de Reachy adaptés pour le SDK 2021
"""
import time
import logging
import numpy as np

from threading import Event, Thread
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode


logger = logging.getLogger('reachy.tictactoe.behavior')


class FollowHand(object):
    """Comportement de suivi de la main avec la tête"""
    
    def __init__(self, reachy):
        """
        Initialise le comportement de suivi
        
        Args:
            reachy: Instance ReachySDK
        """
        self.reachy = reachy
        self.running = Event()
        
    def start(self):
        """Lance le comportement de suivi"""
        logger.info('Launching follow hand behavior')
        self.t = Thread(target=self.asserv)
        self.running.set()
        self.t.start()
        
    def stop(self):
        """Arrête le comportement de suivi"""
        logger.info('Stopping follow hand behavior')
        self.running.clear()
        self.t.join()
        
    def asserv(self):
        """Boucle d'asservissement pour suivre la main"""
        while self.running.is_set():
            try:
                # Récupérer la position de la main via la cinématique directe
                # Note: Cette fonctionnalité nécessite d'avoir accès à la FK
                # qui n'est pas directement disponible dans le SDK 2021
                # Cette partie devrait être adaptée selon les besoins
                pass
            except Exception as e:
                logger.warning(f'Follow hand error: {e}')
                
            time.sleep(0.01)


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
    time.sleep(duration)


def sad(reachy):
    """
    Comportement de tristesse (défaite)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'sad'})
    
    import os
    import random
    import subprocess

    # Fonction pour le mouvement des antennes
    def antenna_movement():
        # Séquence de positions pour exprimer la tristesse
        positions = [
            (150, 1.5),   # Antennes vers le haut
            (110, 1.5),   # Légèrement baissées
            (150, 1.5),   # Remontées
            (110, 1.5),   # Baissées à nouveau
            (150, 1.5),   # Remontées
            (90, 1.5),    # Position intermédiaire
            (20, 1.5),    # Position basse (tristesse)
        ]
        
        for antenna_pos, dur in positions:
            # Définir directement goal_position (SDK 2021 travaille en degrés)
            reachy.head.l_antenna.goal_position = antenna_pos
            reachy.head.r_antenna.goal_position = -antenna_pos
            time.sleep(dur)
    
    # Fonction pour jouer un son aléatoire
    def play_random_sound():
        """Joue un son aléatoire parmi les 3 disponibles"""
        try:
            sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
            sound_files = [
                'Coup_de_chance.mp3',
                'Laissé_gagner.mp3',
                'Le_jeu_est_truqué.mp3'
            ]
            
            selected_sound = random.choice(sound_files)
            sound_path = os.path.join(sounds_dir, selected_sound)
            
            logger.info(f'Playing sound: {selected_sound}')
            subprocess.run(['mpg123', '-a', 'hw:0,0', '-q', sound_path], check=False)
            
        except Exception as e:
            logger.error(f'Erreur lors de la lecture du son: {e}')

    # Créer et lancer les trois threads en parallèle
    antenna_thread = Thread(target=antenna_movement)
    sound_thread = Thread(target=play_random_sound)
    
    # Démarrer les trois mouvements simultanément
    antenna_thread.start()
    sound_thread.start()
    
    # Attendre que tous les mouvements soient terminés
    antenna_thread.join()
    sound_thread.join()
    
    logger.info('Ending behavior', extra={'behavior': 'sad'})

def happy(reachy):
    """
    Comportement de joie (victoire)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'happy'})
    
    # Animation joyeuse des antennes
    dur = 3
    t = np.linspace(0, dur, int(dur * 100))
    pos = 10 * np.sin(2 * np.pi * 5 * t)  # Oscillation rapide
    
    for p in pos:
        # SDK 2021 travaille en degrés
        goto(
            goal_positions={
                reachy.head.l_antenna: p,
                reachy.head.r_antenna: -p,
            },
            duration=0.01,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.01)
        
    time.sleep(1)
    head_home(reachy, duration=1)
    
    logger.info('Ending behavior', extra={'behavior': 'happy'})


def surprise(reachy):
    """
    Comportement de surprise (égalité)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'surprise'})
    
    import os
    import subprocess
    
    # Fonction pour le mouvement des antennes (animation plus élaborée)
    def antenna_movement():
        # Séquence de mouvements pour exprimer la surprise/égalité
        # 1. Mouvement rapide et asymétrique initial (surprise)
        goto(
            goal_positions={
                reachy.head.l_antenna: -5,
                reachy.head.r_antenna: -90,
            },
            duration=0.3,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(0.3)
        
        # 2. Retour au centre puis oscillation
        goto(
            goal_positions={
                reachy.head.l_antenna: 0,
                reachy.head.r_antenna: 0,
            },
            duration=0.4,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(0.4)
        
        # 3. Oscillation symétrique (hésitation/égalité)
        for _ in range(2):
            goto(
                goal_positions={
                    reachy.head.l_antenna: 45,
                    reachy.head.r_antenna: -45,
                },
                duration=0.5,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            time.sleep(0.5)
            
            goto(
                goal_positions={
                    reachy.head.l_antenna: -45,
                    reachy.head.r_antenna: 45,
                },
                duration=0.5,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            time.sleep(0.5)
        
        # 4. Animation finale ondulante (acceptation de l'égalité)
        dur = 2
        t = np.linspace(0, dur, int(dur * 100))
        pos = 30 * np.sin(2 * np.pi * 2 * t)  # Oscillation douce
        
        for p in pos:
            goto(
                goal_positions={
                    reachy.head.l_antenna: p,
                    reachy.head.r_antenna: -p,
                },
                duration=0.01,
                interpolation_mode=InterpolationMode.LINEAR,
            )
            time.sleep(0.01)
        
        # Retour à la position neutre
        head_home(reachy, duration=1)
    
    # Fonction pour jouer le son d'égalité
    def play_draw_sound():
        """Joue le son d'égalité"""
        try:
            sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
            sound_path = os.path.join(sounds_dir, 'Egalité.mp3')
            
            logger.info('Playing draw sound: Egalité.mp3')
            subprocess.run(['mpg123', '-a', 'hw:0,0', '-q', sound_path], check=False)
            
        except Exception as e:
            logger.error(f'Erreur lors de la lecture du son d\'égalité: {e}')
    
    # Créer et lancer les threads en parallèle
    antenna_thread = Thread(target=antenna_movement)
    sound_thread = Thread(target=play_draw_sound)
    
    # Démarrer les mouvements simultanément
    antenna_thread.start()
    sound_thread.start()
    
    # Attendre que tous les mouvements soient terminés
    antenna_thread.join()
    sound_thread.join()
    
    logger.info('Ending behavior', extra={'behavior': 'surprise'})


def celebrate(reachy):
    """
    Comportement de célébration plus élaboré
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'celebrate'})
    
    import os
    import random
    import subprocess
    
    # Fonction pour le mouvement des antennes
    def antenna_movement():
        # Animation élaborée pour une grande victoire
        for _ in range(3):
            # Mouvement rapide haut-bas (SDK 2021 en degrés)
            goto(
                goal_positions={
                    reachy.head.l_antenna: 180,
                    reachy.head.r_antenna: -180,
                },
                duration=0.5,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            time.sleep(0.5)
            
            goto(
                goal_positions={
                    reachy.head.l_antenna: 0,
                    reachy.head.r_antenna: 0,
                },
                duration=0.5,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            time.sleep(0.5)
            
        # Animation finale ondulante
        dur = 2
        t = np.linspace(0, dur, int(dur * 100))
        pos = 45 * np.sin(2 * np.pi * 3 * t)
        
        for p in pos:
            # SDK 2021 travaille en degrés
            goto(
                goal_positions={
                    reachy.head.l_antenna: p,
                    reachy.head.r_antenna: -p,
                },
                duration=0.01,
                interpolation_mode=InterpolationMode.LINEAR,
            )
            time.sleep(0.01)
        
        head_home(reachy, duration=1)
    
    # Fonction pour jouer un son de célébration
    def play_celebration_sound():
        """Joue un son aléatoire parmi les 3 sons de célébration"""
        try:
            sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
            sound_files = [
                "J'enregistre_cette_victoire.mp3",
                'Mon_processeur_jubile.mp3',
                'Statistiquement.mp3'
            ]
            
            selected_sound = random.choice(sound_files)
            sound_path = os.path.join(sounds_dir, selected_sound)
            
            logger.info(f'Playing celebration sound: {selected_sound}')
            subprocess.run(['mpg123', '-a', 'hw:0,0', '-q', sound_path], check=False)
            
        except Exception as e:
            logger.error(f'Erreur lors de la lecture du son de célébration: {e}')
    
    # Créer et lancer les threads en parallèle
    antenna_thread = Thread(target=antenna_movement)
    sound_thread = Thread(target=play_celebration_sound)
    
    # Démarrer les mouvements simultanément
    antenna_thread.start()
    sound_thread.start()
    
    # Attendre que tous les mouvements soient terminés
    antenna_thread.join()
    sound_thread.join()
    
    logger.info('Ending behavior', extra={'behavior': 'celebrate'})


def thinking(reachy, used_sounds=None):
    """
    Comportement de réflexion (pendant que Reachy calcule son coup)
    
    Args:
        reachy: Instance ReachySDK
        used_sounds: Set des sons déjà utilisés (pour éviter les doublons)
    """
    logger.info('Starting behavior', extra={'behavior': 'thinking'})
    
    import os
    import random
    import subprocess
    
    # Fonction pour le mouvement des antennes
    def antenna_movement():
        # Mouvement lent et régulier pour simuler la réflexion
        dur = 2
        t = np.linspace(0, dur, int(dur * 100))
        pos = 30 + 20 * np.sin(2 * np.pi * 0.5 * t)
        
        for p in pos:
            reachy.head.l_antenna.goal_position = p
            reachy.head.r_antenna.goal_position = p  # Même direction = réflexion
            time.sleep(0.01)
        
        # Retour à la position neutre
        reachy.head.l_antenna.goal_position = 0.0
        reachy.head.r_antenna.goal_position = 0.0
        time.sleep(1.0)
        
    # Fonction pour jouer un son aléatoire
    def play_random_sound():
        """Joue un son aléatoire parmi les 5 disponibles"""
        try:
            sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')
            sound_files = [
                'Calcul_en_cours.mp3',
                'Je_joue_stratègique.mp3',
                'Le_bon_coup.mp3',
                'Observe.mp3',
                'Téléchargement.mp3'
            ]
            
            # Filtrer les son non utilisés
            available_sounds = [s for s in sound_files if s not in used_sounds]

            # Si tout les sons ont été utilisés, réinitialiser
            if not available_sounds:
                logger.info('Tous les sons ont été utilisés, réinitialisation du set des sons utilisés')
                used_sounds.clear()
                available_sounds = sound_files

            # Choisir un son aléatoire parmi les sons disponibles
            selected_sound = random.choice(available_sounds)
            used_sounds.add(selected_sound)
            
            sound_path = os.path.join(sounds_dir, selected_sound)
            
            logger.info(f'Playing sound: {selected_sound}')
            subprocess.run(['mpg123', '-a', 'hw:0,0', '-q', sound_path], check=False)
            
        except Exception as e:
            logger.error(f'Erreur lors de la lecture du son: {e}')
    
    # Créer et lancer les TROIS threads en parallèle
    antenna_thread = Thread(target=antenna_movement)
    sound_thread = Thread(target=play_random_sound)
    
    # Démarrer les trois mouvements simultanément
    antenna_thread.start()
    sound_thread.start()
    
    # Attendre que tous les mouvements soient terminés
    antenna_thread.join()
    sound_thread.join()
    
    logger.info('Ending behavior', extra={'behavior': 'thinking'})

def wave_hello(reachy):
    """
    Fait un signe de la main pour saluer
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'wave_hello'})
    
    # Animation des antennes pour accompagner le salut (SDK 2021 en degrés)
    for _ in range(3):
        goto(
            goal_positions={
                reachy.head.l_antenna: 45,
                reachy.head.r_antenna: -45,
            },
            duration=0.4,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(0.4)
        
        goto(
            goal_positions={
                reachy.head.l_antenna: -45,
                reachy.head.r_antenna: 45,
            },
            duration=0.4,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(0.4)
        
    head_home(reachy, duration=1)
    
    logger.info('Ending behavior', extra={'behavior': 'wave_hello'})


def impatient(reachy):
    """
    Comportement d'impatience (quand l'humain met trop de temps à jouer)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'impatient'})
    
    # Mouvements rapides et saccadés (SDK 2021 en degrés)
    for _ in range(5):
        goto(
            goal_positions={
                reachy.head.l_antenna: 90,
                reachy.head.r_antenna: -90,
            },
            duration=0.2,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.2)
        
        goto(
            goal_positions={
                reachy.head.l_antenna: 0,
                reachy.head.r_antenna: 0,
            },
            duration=0.2,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.2)
        
    head_home(reachy, duration=0.5)
    
    logger.info('Ending behavior', extra={'behavior': 'impatient'})
