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
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(antenna_pos),
                reachy.head.r_antenna: np.deg2rad(-antenna_pos),
            },
            duration=dur,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(dur)
        
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
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(p),
                reachy.head.r_antenna: np.deg2rad(-p),
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
    
    # Mouvement rapide et asymétrique des antennes pour exprimer la surprise
    # CORRECTION: Utiliser objets Joint
    goto(
        goal_positions={
            reachy.head.l_antenna: np.deg2rad(-5),
            reachy.head.r_antenna: np.deg2rad(-90),
        },
        duration=0.3,
        interpolation_mode=InterpolationMode.MINIMUM_JERK,
    )
    time.sleep(0.3)
    
    time.sleep(1)
    head_home(reachy, duration=1)
    
    logger.info('Ending behavior', extra={'behavior': 'surprise'})


def celebrate(reachy):
    """
    Comportement de célébration plus élaboré
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'celebrate'})
    
    # Animation élaborée pour une grande victoire
    for _ in range(3):
        # Mouvement rapide haut-bas
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(180),
                reachy.head.r_antenna: np.deg2rad(-180),
            },
            duration=0.5,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(0.5)
        
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(0),
                reachy.head.r_antenna: np.deg2rad(0),
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
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(p),
                reachy.head.r_antenna: np.deg2rad(-p),
            },
            duration=0.01,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.01)
        
    head_home(reachy, duration=1)
    
    logger.info('Ending behavior', extra={'behavior': 'celebrate'})


def thinking(reachy):
    """
    Comportement de réflexion (pendant que Reachy calcule son coup)
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'thinking'})
    
    # Mouvement lent et régulier pour simuler la réflexion
    dur = 2
    t = np.linspace(0, dur, int(dur * 100))
    pos = 30 + 20 * np.sin(2 * np.pi * 0.5 * t)
    
    for p in pos:
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(p),
                reachy.head.r_antenna: np.deg2rad(p),  # Même direction = réflexion
            },
            duration=0.01,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.01)
        
    head_home(reachy, duration=1)
    
    logger.info('Ending behavior', extra={'behavior': 'thinking'})


def wave_hello(reachy):
    """
    Fait un signe de la main pour saluer
    
    Args:
        reachy: Instance ReachySDK
    """
    logger.info('Starting behavior', extra={'behavior': 'wave_hello'})
    
    # Animation des antennes pour accompagner le salut
    for _ in range(3):
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(45),
                reachy.head.r_antenna: np.deg2rad(-45),
            },
            duration=0.4,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(0.4)
        
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(-45),
                reachy.head.r_antenna: np.deg2rad(45),
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
    
    # Mouvements rapides et saccadés
    for _ in range(5):
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(90),
                reachy.head.r_antenna: np.deg2rad(-90),
            },
            duration=0.2,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.2)
        
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                reachy.head.l_antenna: np.deg2rad(0),
                reachy.head.r_antenna: np.deg2rad(0),
            },
            duration=0.2,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.2)
        
    head_home(reachy, duration=0.5)
    
    logger.info('Ending behavior', extra={'behavior': 'impatient'})
