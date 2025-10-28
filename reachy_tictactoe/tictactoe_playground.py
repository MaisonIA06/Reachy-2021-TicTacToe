"""
TicTacToe Playground adapté pour Reachy SDK 2021
Ce module gère la logique du jeu et le contrôle du robot Reachy V1
"""
import numpy as np
import logging
import time
import os

from threading import Thread, Event
from reachy_sdk import ReachySDK
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode

from .vision import get_board_configuration, is_board_valid
from .utils import piece2id, id2piece, piece2player
from .moves import moves, rest_pos, base_pos
from .rl_agent import value_actions
from . import behavior


logger = logging.getLogger('reachy.tictactoe')


class TictactoePlayground(object):
    """Classe principale pour gérer le jeu de TicTacToe avec Reachy"""
    
    def __init__(self, host='localhost'):
        """
        Initialise la connexion avec Reachy
        
        Args:
            host: Adresse IP du robot Reachy (default: 'localhost')
        """
        logger.info('Creating the playground')
        
        # Connexion avec le SDK 2021
        self.reachy = ReachySDK(host=host)
        self.pawn_played = 0
        
    def setup(self):
        """Configure le robot pour le jeu"""
        logger.info('Setup the playground')
        
        # Activer les moteurs des antennes
        self.reachy.turn_on('head')
        
        # Position initiale des antennes
        goto(
            goal_positions={
                self.reachy.head.l_antenna: 0.0,
                self.reachy.head.r_antenna: 0.0,
            },
            duration=2.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        
        self.goto_rest_position()
        
    def __enter__(self):
        return self
        
    def __exit__(self, *exc):
        logger.info(
            'Closing the playground',
            extra={
                'exc': exc,
            }
        )
        # Désactiver tous les moteurs
        self.reachy.turn_off_smoothly('reachy')
        
    # Playground and game functions
    
    def reset(self):
        """Réinitialise le jeu"""
        logger.info('Resetting the playground')
        
        self.pawn_played = 0
        empty_board = np.zeros((3, 3), dtype=np.uint8).flatten()
        
        return empty_board
        
    def is_ready(self, board):
        """Vérifie si le plateau est vide et prêt"""
        return np.sum(board) == 0
        
    def random_look(self):
        """Fait regarder Reachy dans une direction aléatoire"""
        dy = 0.4
        y = np.random.rand() * dy - (dy / 2)
        
        dz = 0.75
        z = np.random.rand() * dz - 0.5
        
        self.look_at(0.5, y, z, duration=1.5)
        time.sleep(1.5)
        
    def run_random_idle_behavior(self):
        """Comportement d'attente aléatoire"""
        logger.info('Reachy is playing a random idle behavior')
        time.sleep(2)
        
    def coin_flip(self):
        """Détermine qui commence (aléatoire)"""
        coin = np.random.rand() > 0.5
        logger.info(
            'Coin flip',
            extra={
                'first player': 'reachy' if coin else 'human',
            },
        )
        return coin
        
    def look_at(self, x, y, z, duration=1.0):
        """
        Oriente la tête de Reachy vers un point dans l'espace
        
        Args:
            x, y, z: Coordonnées du point cible (en mètres)
            duration: Durée du mouvement
        """
        try:
            # SDK 2021: Utiliser la méthode look_at de head
            # Format: reachy.head.look_at(x, y, z, duration)
            self.reachy.head.look_at(x=x, y=y, z=z, duration=duration)
            time.sleep(duration)  # Attendre la fin du mouvement
        except Exception as e:
            logger.warning(f'Look at failed: {e}')
            
    def analyze_board(self):
        """Analyse l'état actuel du plateau de jeu"""
        # Activer les moteurs du cou
        self.reachy.turn_on('head')
        time.sleep(0.1)
        
        # Regarder vers le plateau (position calibrée dans Check_boxes.ipynb)
        # z=-0.6 pour voir le plateau complet
        self.reachy.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)
        time.sleep(0.2)
        
        # Attendre une image de la caméra
        self.wait_for_img()
        
        # Capturer l'image depuis la caméra droite
        try:
            img = self.reachy.right_camera.last_frame
        except Exception as e:
            logger.warning(f'Failed to read camera: {e}')
            return None
            
        # Sauvegarder l'image (debug)
        import cv2 as cv
        i = np.random.randint(1000)
        path = f'/tmp/snap.{i}.jpg'
        cv.imwrite(path, img)
        
        logger.info(
            'Getting an image from camera',
            extra={
                'img_path': path,
            },
        )
        
        # Vérifier que le plateau est valide
        if not is_board_valid(img):
            return None
            
        # Analyser la configuration du plateau
        board, _ = get_board_configuration(img)
        
        logger.info(
            'Board analyzed',
            extra={
                'board': board,
                'img_path': path,
            },
        )
        
        return board.flatten()
        
    def incoherent_board_detected(self, board):
        """Détecte si le plateau a un état incohérent"""
        nb_cubes = len(np.where(board == piece2id['cube'])[0])
        nb_cylinders = len(np.where(board == piece2id['cylinder'])[0])
        
        if abs(nb_cubes - nb_cylinders) <= 1:
            return False
            
        logger.warning('Incoherent board detected', extra={
            'current_board': board,
        })
        
        return True
        
    def cheating_detected(self, board, last_board, reachy_turn):
        """Détecte si le joueur humain a triché"""
        delta = board - last_board
        
        # Rien n'a changé
        if np.all(delta == 0):
            return False
            
        # Un seul cube a été ajouté
        if len(np.where(delta == piece2id['cube'])[0]) == 1:
            return False
            
        # Un seul cylindre a été ajouté
        if len(np.where(delta == piece2id['cylinder'])[0]) == 1:
            # Si l'humain a ajouté un cylindre, c'est de la triche
            if not reachy_turn:
                return True
            return False
            
        logger.warning('Cheating detected', extra={
            'last_board': last_board,
            'current_board': board,
        })
        
        return True
        
    def shuffle_board(self):
        """Mélange le plateau (comportement de réprimande)"""
        def ears_no():
            """Animation des antennes pour dire non"""
            d = 3
            f = 2
            time.sleep(2.5)
            t = np.linspace(0, d, d * 100)
            p = 25 + 25 * np.sin(2 * np.pi * f * t)
            
            for pp in p:
                goto(
                    goal_positions={self.reachy.head.l_antenna: np.deg2rad(pp)},
                    duration=0.01,
                    interpolation_mode=InterpolationMode.LINEAR,
                )
                time.sleep(0.01)
                
        t = Thread(target=ears_no)
        t.start()
        
        self.goto_base_position()
        self.play_trajectory(moves['shuffle-board'])
        self.goto_rest_position()
        
        t.join()
        
    def choose_next_action(self, board):
        """Choisit la prochaine action à jouer"""
        actions = value_actions(board)
        
        # Si le plateau est vide, commence avec une action aléatoire
        if np.all(board == 0):
            while True:
                i = np.random.randint(0, 9)
                a, _ = actions[i]
                if a != 8:
                    break
                    
        elif np.sum(board) == piece2id['cube']:
            a, _ = actions[0]
            if a == 8:
                i = 1
            else:
                i = 0
        else:
            i = 0
            
        best_action, value = actions[i]
        
        logger.info(
            'Selecting Reachy next action',
            extra={
                'board': board,
                'actions': actions,
                'selected action': best_action,
            },
        )
        
        return best_action, value
        
    def play(self, action, actual_board):
        """Joue un pion à la position spécifiée"""
        board = actual_board.copy()
        
        self.play_pawn(
            grab_index=self.pawn_played + 1,
            box_index=action + 1,
        )
        
        self.pawn_played += 1
        board[action] = piece2id['cylinder']
        
        logger.info(
            'Reachy playing pawn',
            extra={
                'board-before': actual_board,
                'board-after': board,
                'action': action + 1,
                'pawn_played': self.pawn_played + 1,
            },
        )
        
        return board
        
    def play_pawn(self, grab_index, box_index):
        """
        Séquence complète pour jouer un pion
        
        Args:
            grab_index: Index du pion à prendre (1-5)
            box_index: Index de la case où placer le pion (1-9)
        """
        # Activer le bras droit
        self.reachy.turn_on('r_arm')
        
        # Aller à la position de base
        self.goto_base_position()
        
        # Si c'est le 4ème pion ou plus, position intermédiaire
        if grab_index >= 4:
            self.goto_position(
                moves['grab_3'],
                duration=1.0,
            )
            
        # Attraper le pion
        self.goto_position(
            moves[f'grab_{grab_index}'],
            duration=1.0,
        )
        
        # Fermer la pince
        self.close_gripper()
        
        # Animation des antennes
        goto(
            goal_positions={
                self.reachy.head.l_antenna: np.deg2rad(45),
                self.reachy.head.r_antenna: np.deg2rad(-45),
            },
            duration=1.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        
        # Ajustement pour les pions éloignés
        if grab_index >= 4:
            # CORRECTION: Utiliser objets Joint
            goto(
                goal_positions={
                    self.reachy.r_arm.r_shoulder_pitch: self.reachy.r_arm.r_shoulder_pitch.present_position + np.deg2rad(10),
                    self.reachy.r_arm.r_elbow_pitch: self.reachy.r_arm.r_elbow_pitch.present_position - np.deg2rad(30),
                },
                duration=1.0,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            
        # Lever le pion
        self.goto_position(
            moves['lift'],
            duration=1.0,
        )
        
        time.sleep(0.1)
        
        # Placer le pion
        put = moves[f'put_{box_index}_smooth_10_kp']
        
        # Aller à la première position du mouvement
        first_pos = {
            joint_name: traj[0]
            for joint_name, traj in put.items()
        }
        self.goto_position(first_pos, duration=0.5)
        
        # Jouer la trajectoire complète
        self.play_trajectory(put)
        
        # Ouvrir la pince
        self.open_gripper()
        
        # Revenir en position de repos
        self.goto_position(
            moves[f'back_{box_index}_upright'],
            duration=1.0,
        )
        
        # Remettre les antennes à zéro
        goto(
            goal_positions={
                self.reachy.head.l_antenna: 0.0,
                self.reachy.head.r_antenna: 0.0,
            },
            duration=0.2,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        
        # Position intermédiaire pour certaines cases
        if box_index in (8, 9):
            self.goto_position(
                moves['back_to_back'],
                duration=1.0,
            )
            
        self.goto_position(
            moves['back_rest'],
            duration=2.0,
        )
        
        self.goto_rest_position()
        
    def is_final(self, board):
        """Vérifie si le jeu est terminé"""
        winner = self.get_winner(board)
        if winner in ('robot', 'human'):
            return True
        else:
            return 0 not in board
            
    def has_human_played(self, current_board, last_board):
        """Vérifie si l'humain a joué"""
        cube = piece2id['cube']
        
        return (
            np.any(current_board != last_board) and
            np.sum(current_board == cube) > np.sum(last_board == cube)
        )
        
    def get_winner(self, board):
        """Détermine le gagnant"""
        win_configurations = (
            (0, 1, 2),
            (3, 4, 5),
            (6, 7, 8),
            
            (0, 3, 6),
            (1, 4, 7),
            (2, 5, 8),
            
            (0, 4, 8),
            (2, 4, 6),
        )
        
        for c in win_configurations:
            trio = set(board[i] for i in c)
            for id in id2piece.keys():
                if trio == set([id]):
                    winner = piece2player[id2piece[id]]
                    if winner in ('robot', 'human'):
                        return winner
                        
        return 'nobody'
        
    def run_celebration(self):
        """Comportement de victoire"""
        logger.info('Reachy is playing its win behavior')
        behavior.happy(self.reachy)
        
    def run_draw_behavior(self):
        """Comportement d'égalité"""
        logger.info('Reachy is playing its draw behavior')
        behavior.surprise(self.reachy)
        
    def run_defeat_behavior(self):
        """Comportement de défaite"""
        logger.info('Reachy is playing its defeat behavior')
        behavior.sad(self.reachy)
        
    def run_my_turn(self):
        """Animation 'mon tour'"""
        self.goto_base_position()
        self.play_trajectory(moves['my-turn'])
        self.goto_rest_position()
        
    def run_your_turn(self):
        """Animation 'votre tour'"""
        self.goto_base_position()
        self.play_trajectory(moves['your-turn'])
        self.goto_rest_position()
        
    # Robot lower-level control functions
    
    def get_joint_positions(self, parts):
        """
        Récupère les positions actuelles des articulations
        
        Args:
            parts: Liste des parties du robot ('r_arm', 'head', etc.)
            
        Returns:
            dict: Dictionnaire {nom_joint: position}
        """
        positions = {}
        
        if 'r_arm' in parts or 'reachy' in parts:
            for joint in self.reachy.r_arm.joints.values():
                positions[f'r_arm.{joint.name}'] = joint.present_position
                
        if 'head' in parts or 'reachy' in parts:
            for joint in self.reachy.head.joints.values():
                positions[f'head.{joint.name}'] = joint.present_position
                
        return positions
        
    def goto_position(self, goal_positions, duration=2.0):
        """
        Déplace le robot vers une position cible
        
        Args:
            goal_positions: dict {nom_joint: position_cible}
            duration: Durée du mouvement
        """
        # CORRECTION: Convertir les noms de joints en objets Joint
        joint_positions = {}
        for old_name, pos in goal_positions.items():
            # Conversion des anciens noms vers les nouveaux noms du SDK 2021
            new_name = self._adapt_joint_name(old_name)
            # Récupérer l'objet Joint correspondant
            joint_obj = self._get_joint_by_name(new_name)
            if joint_obj is not None:
                # Convertir les degrés en radians si nécessaire
                if isinstance(pos, (int, float)):
                    position_value = np.deg2rad(pos) if pos > 6.28 or pos < -6.28 else pos
                else:
                    position_value = pos
                joint_positions[joint_obj] = position_value
                
        goto(
            goal_positions=joint_positions,
            duration=duration,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(duration)
        
    def _adapt_joint_name(self, old_name):
        """
        Adapte les anciens noms de joints vers les nouveaux
        
        Args:
            old_name: Ancien nom de joint (ex: 'right_arm.shoulder_pitch')
            
        Returns:
            str: Nouveau nom de joint (ex: 'r_arm.r_shoulder_pitch')
        """
        # Mapping des anciens noms vers les nouveaux
        mapping = {
            'right_arm.shoulder_pitch': 'r_arm.r_shoulder_pitch',
            'right_arm.shoulder_roll': 'r_arm.r_shoulder_roll',
            'right_arm.arm_yaw': 'r_arm.r_arm_yaw',
            'right_arm.elbow_pitch': 'r_arm.r_elbow_pitch',
            'right_arm.hand.forearm_yaw': 'r_arm.r_forearm_yaw',
            'right_arm.hand.wrist_pitch': 'r_arm.r_wrist_pitch',
            'right_arm.hand.wrist_roll': 'r_arm.r_wrist_roll',
            'right_arm.hand.gripper': 'r_arm.r_gripper',
            'head.left_antenna': 'head.l_antenna',
            'head.right_antenna': 'head.r_antenna',
        }
        
        return mapping.get(old_name, old_name)
        
    def _get_joint_by_name(self, joint_name):
        """
        Récupère un objet Joint à partir de son nom
        
        Args:
            joint_name: Nom du joint (ex: 'r_arm.r_shoulder_pitch')
            
        Returns:
            Joint: Objet Joint ou None si non trouvé
        """
        # Parcourir tous les joints disponibles
        try:
            # Méthode 1: Accès direct par attribut
            parts = joint_name.split('.')
            if len(parts) == 2:
                part_name, joint_short_name = parts
                
                # Accès direct via attribut (ex: reachy.r_arm.r_shoulder_pitch)
                if part_name == 'r_arm' and hasattr(self.reachy, 'r_arm'):
                    if hasattr(self.reachy.r_arm, joint_short_name):
                        return getattr(self.reachy.r_arm, joint_short_name)
                elif part_name == 'l_arm' and hasattr(self.reachy, 'l_arm'):
                    if hasattr(self.reachy.l_arm, joint_short_name):
                        return getattr(self.reachy.l_arm, joint_short_name)
                elif part_name == 'head' and hasattr(self.reachy, 'head'):
                    if hasattr(self.reachy.head, joint_short_name):
                        return getattr(self.reachy.head, joint_short_name)
            
            # Méthode 2: Essayer via le dictionnaire joints (si disponible)
            if hasattr(self.reachy, 'joints') and hasattr(self.reachy.joints, '__getitem__'):
                try:
                    return self.reachy.joints[joint_name]
                except (KeyError, TypeError):
                    pass
                        
            logger.warning(f'Joint not found: {joint_name}')
            return None
            
        except Exception as e:
            logger.error(f'Error accessing joint {joint_name}: {e}')
            return None
        
    def play_trajectory(self, trajectory_dict):
        """
        Joue une trajectoire complète
        
        Args:
            trajectory_dict: dict {nom_joint: array_positions}
        """
        # CORRECTION: Adapter les noms de joints et convertir en objets Joint
        adapted_traj = {}
        for old_name, positions in trajectory_dict.items():
            new_name = self._adapt_joint_name(old_name)
            joint_obj = self._get_joint_by_name(new_name)
            if joint_obj is not None:
                adapted_traj[joint_obj] = positions
            
        if not adapted_traj:
            logger.warning('No valid joints found in trajectory')
            return
            
        # Déterminer la durée totale basée sur le nombre de points
        num_points = len(list(adapted_traj.values())[0])
        duration = num_points * 0.01  # 100 Hz
        
        # Jouer la trajectoire point par point
        for i in range(num_points):
            point = {
                joint_obj: traj[i] for joint_obj, traj in adapted_traj.items()
            }
            goto(
                goal_positions=point,
                duration=0.01,
                interpolation_mode=InterpolationMode.LINEAR,
            )
            time.sleep(0.01)
            
    def goto_base_position(self, duration=2.0):
        """Va à la position de base"""
        self.reachy.turn_on('r_arm')
        time.sleep(0.1)
        
        self.goto_position(base_pos, duration)
        
    def goto_rest_position(self, duration=2.0):
        """Va à la position de repos"""
        time.sleep(0.1)
        
        self.goto_base_position(0.6 * duration)
        time.sleep(0.1)
        
        self.goto_position(rest_pos, 0.4 * duration)
        time.sleep(0.1)
        
        # Réduire le couple de certains moteurs
        # Note: Dans le SDK 2021, il faut utiliser compliant mode
        time.sleep(0.25)
        
    def close_gripper(self):
        """Ferme la pince"""
        # CORRECTION: Utiliser objet Joint
        goto(
            goal_positions={self.reachy.r_arm.r_gripper: np.deg2rad(-45)},
            duration=0.5,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.5)
        
    def open_gripper(self):
        """Ouvre la pince"""
        # CORRECTION: Utiliser objet Joint
        goto(
            goal_positions={self.reachy.r_arm.r_gripper: np.deg2rad(20)},
            duration=0.5,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.5)
        
    def wait_for_img(self):
        """Attend qu'une image soit disponible"""
        # MODE TEST: Désactiver le timeout strict pour éviter les reboots
        # TODO: Réactiver quand la caméra sera configurée
        start = time.time()
        timeout = 5  # Réduit à 5 secondes au lieu de 30
        
        while time.time() - start <= timeout:
            try:
                img = self.reachy.right_camera.last_frame
                if img is not None and len(img) > 0:
                    logger.info('Image received from camera')
                    return
            except Exception as e:
                logger.debug(f'Camera read attempt failed: {e}')
                pass
            time.sleep(0.1)
            
        # MODE TEST: Ne pas rebooter, juste logger l'erreur
        logger.warning(f'No image received after {timeout} sec. Camera may not be configured.')
        logger.warning('Continuing without camera (TEST MODE)')
        # os.system('sudo reboot')  # Désactivé en mode test
        
    def need_cooldown(self):
        """Vérifie si un refroidissement est nécessaire"""
        temperatures = {}
        
        # Récupérer les températures de tous les moteurs
        for joint in self.reachy.joints.values():
            temp = joint.temperature
            temperatures[joint.name] = temp
            
        logger.info(
            'Checking Reachy motors temperature',
            extra={
                'temperatures': temperatures
            }
        )
        
        # Vérifier les seuils
        motor_temps = [t for t in temperatures.values() if t is not None]
        if motor_temps:
            return np.any(np.array(motor_temps) > 50)
        return False
        
    def wait_for_cooldown(self):
        """Attend que les moteurs refroidissent"""
        self.goto_rest_position()
        
        while True:
            temperatures = {}
            for joint in self.reachy.joints.values():
                temp = joint.temperature
                temperatures[joint.name] = temp
                
            logger.warning(
                'Motors cooling down...',
                extra={
                    'temperatures': temperatures
                },
            )
            
            motor_temps = [t for t in temperatures.values() if t is not None]
            if motor_temps and np.all(np.array(motor_temps) < 45):
                break
                
            time.sleep(30)
            
    def enter_sleep_mode(self):
        """Entre en mode veille"""
        self._idle_running = Event()
        self._idle_running.set()
        
        def _idle():
            """Animation d'attente des antennes"""
            f = 0.15
            amp = 30
            offset = 30
            
            while self._idle_running.is_set():
                p = offset + amp * np.sin(2 * np.pi * f * time.time())
                # CORRECTION: Utiliser objets Joint
                goto(
                    goal_positions={
                        self.reachy.head.l_antenna: np.deg2rad(p),
                        self.reachy.head.r_antenna: np.deg2rad(-p),
                    },
                    duration=0.01,
                    interpolation_mode=InterpolationMode.LINEAR,
                )
                time.sleep(0.01)
                
        self._idle_t = Thread(target=_idle)
        self._idle_t.start()
        
    def leave_sleep_mode(self):
        """Sort du mode veille"""
        self._idle_running.clear()
        self._idle_t.join()
        
        # CORRECTION: Utiliser objets Joint
        goto(
            goal_positions={
                self.reachy.head.l_antenna: 0.0,
                self.reachy.head.r_antenna: 0.0,
            },
            duration=1.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(1.0)
