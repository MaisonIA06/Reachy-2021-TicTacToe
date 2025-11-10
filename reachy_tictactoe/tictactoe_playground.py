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
from .config import GRIPPER_OPEN, GRIPPER_CLOSED


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
        # Track des sons utilisés pendant la partie
        self.used_thinking_sounds = set()
    
    def display_board(self, board, current_player=None, winner=None):
        """
        Affiche le plateau de jeu à l'écran pour que plusieurs personnes puissent voir
        
        Args:
            board: Array numpy (9 éléments) représentant le plateau
            current_player: 'robot' ou 'human' - joueur actuel
            winner: 'robot', 'human', 'nobody' ou None - gagnant si partie terminée
        """
        import cv2 as cv
        import numpy as np
        
        # Dimensions de la fenêtre
        cell_size = 150
        board_size = cell_size * 3
        margin = 50
        window_width = board_size + 2 * margin
        window_height = board_size + 2 * margin + 100  # Espace pour le texte
        
        # Créer une image blanche
        img = np.ones((window_height, window_width, 3), dtype=np.uint8) * 255
        
        # Convertir le board en matrice 3x3
        board_2d = board.reshape(3, 3)
        
        # Dessiner la grille et les pièces
        for row in range(3):
            for col in range(3):
                x = margin + col * cell_size
                y = margin + row * cell_size
                
                # Dessiner le rectangle de la case
                cv.rectangle(img, (x, y), (x + cell_size, y + cell_size), (0, 0, 0), 2)
                
                # Afficher la pièce
                piece_id = board_2d[row, col]
                center_x = x + cell_size // 2
                center_y = y + cell_size // 2
                
                if piece_id == piece2id['cube']:  # Humain (X)
                    # Dessiner un X rouge
                    thickness = 5
                    cv.line(img, 
                           (x + 20, y + 20), 
                           (x + cell_size - 20, y + cell_size - 20), 
                           (0, 0, 255), thickness)
                    cv.line(img, 
                           (x + cell_size - 20, y + 20), 
                           (x + 20, y + cell_size - 20), 
                           (0, 0, 255), thickness)
                    # Texte "X"
                    cv.putText(img, 'X', (center_x - 15, center_y + 10),
                              cv.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
                    
                elif piece_id == piece2id['cylinder']:  # Robot (O)
                    # Dessiner un cercle bleu
                    radius = cell_size // 2 - 20
                    cv.circle(img, (center_x, center_y), radius, (255, 0, 0), 5)
                    # Texte "O"
                    cv.putText(img, 'O', (center_x - 15, center_y + 10),
                              cv.FONT_HERSHEY_SIMPLEX, 1.5, (255, 0, 0), 3)
        
        # Afficher le statut du jeu
        status_y = board_size + 2 * margin + 30
        
        if winner:
            if winner == 'robot':
                status_text = "Reachy a gagne !"
                color = (255, 0, 0)  # Bleu
            elif winner == 'human':
                status_text = "Vous avez gagne !"
                color = (0, 0, 255)  # Rouge
            else:
                status_text = "Egalite !"
                color = (0, 128, 0)  # Vert
        elif current_player:
            if current_player == 'robot':
                status_text = "Tour de Reachy (O)"
                color = (255, 0, 0)  # Bleu
            else:
                status_text = "Votre tour (X)"
                color = (0, 0, 255)  # Rouge
        else:
            status_text = "Partie en cours"
            color = (0, 0, 0)  # Noir
        
        # Afficher le texte de statut
        cv.putText(img, status_text, (margin, status_y),
                  cv.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        
        # Titre
        cv.putText(img, "TIC TAC TOE - Reachy", (margin, 30),
                  cv.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        
        # Afficher la fenêtre
        cv.imshow('TicTacToe - Reachy', img)
        cv.waitKey(1)  # Nécessaire pour mettre à jour l'affichage
    
    def close_display(self):
        """Ferme la fenêtre d'affichage"""
        import cv2 as cv
        cv.destroyAllWindows()
        
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
        # Réinitialiser le track des sons utilisés
        self.used_thinking_sounds = set()
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
    
    def run_thinking_behavior(self):
        """Comportement de réflexion"""
        logger.info('Reachy is thinking about its next move')
        behavior.thinking(self.reachy, used_sounds=self.used_thinking_sounds)

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
        import random
        import subprocess

        def ears_no():
            """Animation des antennes pour dire non"""
            d = 3
            f = 2
            time.sleep(2.5)
            t = np.linspace(0, d, d * 100)
            p = 25 + 25 * np.sin(2 * np.pi * f * t)

            for pp in p:
                # Définir directement goal_position au lieu d'utiliser goto()
                self.reachy.head.l_antenna.goal_position = pp
                time.sleep(0.01)

        def play_random_sound():
            """Joue un son aléatoire parmi les 3 disponibles"""
            try:
                # Chemin vers le dossier sounds
                sounds_dir = os.path.join(os.path.dirname(__file__), 'sounds')

                # Liste des fichiers audio disponibles
                sound_files = [
                    'Esprit_antisportif.mp3',
                    'Joueur_déloyal.mp3',
                    'Mauvais_perdant.mp3'
                ]

                # Choisir un fichier aléatoirement
                selected_sound = random.choice(sound_files)
                sound_path = os.path.join(sounds_dir, selected_sound)

                logger.info(f'Playing sound: {selected_sound}')

                # Jouer le son avec mpg123 (ou ffplay en alternative)
                # Spécifier explicitement le périphérique audio (ReSpeaker = hw:0,0)
                subprocess.run(['mpg123', '-a', 'hw:0,0', '-q', sound_path], check=False)

            except Exception as e:
                logger.error(f'Erreur lors de la lecture du son: {e}')

        # Créer les trois threads pour les mouvements parallèles
        antenna_thread = Thread(target=ears_no)
        sound_thread = Thread(target=play_random_sound)

        # Démarrer le son et les antennes en parallèle
        antenna_thread.start()
        sound_thread.start()

        # Effectuer les mouvements du bras
        self.goto_base_position()
        self.play_trajectory(moves['shuffle-board'])
        self.goto_rest_position()

        # Attendre que les antennes et le son soient terminés
        antenna_thread.join()
        sound_thread.join()
        
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
        
        # CRITIQUE: Forcer l'activation du gripper
        time.sleep(0.3)
        self.reachy.r_arm.r_gripper.compliant = False
        time.sleep(0.2)
        
        # Vérifier que le gripper est bien activé
        if self.reachy.r_arm.r_gripper.compliant:
            logger.error("❌ GRIPPER TOUJOURS EN MODE COMPLIANT!")
            self.reachy.r_arm.r_gripper.compliant = False
            time.sleep(0.5)
        
        logger.info(f"Gripper state: compliant={self.reachy.r_arm.r_gripper.compliant}, "
                    f"position={self.reachy.r_arm.r_gripper.present_position:.1f}°")

        # Aller à la position de base
        self.goto_base_position()
    
        # Si c'est le 4ème pion ou plus, position intermédiaire
        if grab_index >= 4:
            self.goto_position(
                moves['grab_3'],
                duration=1.0,
                filter_gripper=True,  # Filtrer le gripper
            )
    
        # CORRECTION: Filtrer le gripper du mouvement grab pour ne pas rouvrir la pince
        grab_move = dict(moves[f'grab_{grab_index}'])
        # Supprimer le gripper du dictionnaire s'il existe
        grab_move_filtered = {
            k: v for k, v in grab_move.items() 
            if 'gripper' not in k.lower()
        }
    
        # Attraper le pion (sans toucher au gripper)
        self.goto_position(
            grab_move_filtered,
            duration=1.0,
        )
        
        # Attendre stabilisation
        time.sleep(0.3)
        
        # Augmenter le couple du gripper pour une meilleure prise
        self.reachy.r_arm.r_gripper.torque_limit = 100
        
        # Fermer la pince progressivement et avec force
        logger.info(f'Closing gripper (before: {self.reachy.r_arm.r_gripper.present_position:.1f}°)')
        
        # Première fermeture
        self.reachy.r_arm.r_gripper.goal_position = GRIPPER_CLOSED
        time.sleep(0.8)
        
        # Fermeture complète avec la fonction
        self.close_gripper()
        
        # Vérifier que la pince est bien fermée
        actual_pos = self.reachy.r_arm.r_gripper.present_position
        logger.info(f'Gripper closed at: {actual_pos:.1f}°')
        
        # Si pas assez fermé (plus négatif que -12)
        if actual_pos < -12:
            logger.warning(f'Gripper not closed enough ({actual_pos:.1f}°), forcing closure...')
            self.reachy.r_arm.r_gripper.goal_position = GRIPPER_CLOSED
            time.sleep(1.0)
            actual_pos = self.reachy.r_arm.r_gripper.present_position
            logger.info(f'Gripper forced to: {actual_pos:.1f}°')
    
        # Animation des antennes (SDK 2021 travaille en degrés)
        goto(
            goal_positions={
                self.reachy.head.l_antenna: 45,
                self.reachy.head.r_antenna: -45,
            },
            duration=1.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        
        # Ajustement pour les pions éloignés
        if grab_index >= 4:
            # Les joints du bras travaillent en degrés dans le SDK 2021
            goto(
                goal_positions={
                    self.reachy.r_arm.r_shoulder_pitch: self.reachy.r_arm.r_shoulder_pitch.present_position + 10,
                    self.reachy.r_arm.r_elbow_pitch: self.reachy.r_arm.r_elbow_pitch.present_position - 30,
                },
                duration=1.0,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
        
        # Pause supplémentaire avant de lever (maintenir la pression)
        time.sleep(0.2)
        
        # Lever le pion (CRITIQUE: Ne pas rouvrir le gripper!)
        self.goto_position(
            moves['lift'],
            duration=1.0,
            filter_gripper=True,  # Ne pas toucher au gripper
        )
        
        time.sleep(0.1)
        
        # Placer le pion
        put = moves[f'put_{box_index}_smooth_10_kp']
        
        # Aller à la première position du mouvement (SANS gripper)
        first_pos = {
            joint_name: traj[0]
            for joint_name, traj in put.items()
            if 'gripper' not in joint_name.lower()
        }
        self.goto_position(first_pos, duration=0.5)
        
        # Jouer la trajectoire complète (CRITIQUE: filtrer le gripper!)
        self.play_trajectory(put, filter_gripper=True)
        
        # Maintenant on peut ouvrir la pince
        self.open_gripper()
        
        # Revenir en position de repos (SANS gripper)
        self.goto_position(
            moves[f'back_{box_index}_upright'],
            duration=1.0,
            filter_gripper=True,
        )
        
        # Remettre les antennes à zéro
        goto(
            goal_positions={
                self.reachy.head.l_antenna: 0.0,
                self.reachy.head.r_antenna: 0.0,
            },
            duration=1.0,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
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
        behavior.celebrate(self.reachy)
        
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
        
    def goto_position(self, goal_positions, duration=2.0, filter_gripper=False):
        """
        Déplace le robot vers une position cible
        
        Args:
            goal_positions: dict {nom_joint: position_cible}
            duration: Durée du mouvement
            filter_gripper: Si True, ignore le gripper dans les positions
        """
        # Filtrer le gripper si demandé
        if filter_gripper:
            goal_positions = {
                k: v for k, v in goal_positions.items() 
                if 'gripper' not in k.lower()
            }
        
        # Convertir les noms de joints en objets Joint
        joint_positions = {}
        for joint_name, pos in goal_positions.items():
            # Récupérer l'objet Joint correspondant (noms déjà au format SDK 2021)
            joint_obj = self._get_joint_by_name(joint_name)
            if joint_obj is not None:
                joint_positions[joint_obj] = pos
                
        goto(
            goal_positions=joint_positions,
            duration=duration,
            interpolation_mode=InterpolationMode.MINIMUM_JERK,
        )
        time.sleep(duration)
        
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
        
    def play_trajectory(self, trajectory_dict, filter_gripper=False):
        """
        Joue une trajectoire complète en utilisant goal_position natif du SDK
        
        Args:
            trajectory_dict: dict {nom_joint: array_positions}
            filter_gripper: Si True, ignore le gripper dans la trajectoire
        """
        # Filtrer le gripper si demandé
        if filter_gripper:
            trajectory_dict = {
                k: v for k, v in trajectory_dict.items() 
                if 'gripper' not in k.lower()
            }
        
        # Convertir les noms de joints en objets Joint
        adapted_traj = {}
        for joint_name, positions in trajectory_dict.items():
            # Récupérer l'objet Joint correspondant (noms déjà au format SDK 2021)
            joint_obj = self._get_joint_by_name(joint_name)
            if joint_obj is not None:
                adapted_traj[joint_obj] = positions
            
        if not adapted_traj:
            logger.warning('No valid joints found in trajectory')
            return
            
        # Déterminer la durée totale basée sur le nombre de points
        num_points = len(list(adapted_traj.values())[0])
        duration = num_points * 0.01  # 100 Hz
        
        logger.info(f'Playing trajectory with {num_points} points ({duration:.1f}s)')
        
        # Jouer la trajectoire en définissant goal_position directement (méthode native SDK 2021)
        for i in range(num_points):
            # Définir goal_position pour chaque joint simultanément
            for joint_obj, traj in adapted_traj.items():
                joint_obj.goal_position = traj[i]
            
            # Attendre 10ms pour maintenir la fréquence de 100 Hz
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
        # S'assurer que le gripper est activé
        self.reachy.r_arm.r_gripper.compliant = False
        self.reachy.r_arm.r_gripper.torque_limit = 100
        time.sleep(0.1)

        logger.info(f"Closing gripper from {self.reachy.r_arm.r_gripper.present_position:.1f}°")

        # Fermer pour tenir les cylindres
        goto(
            goal_positions={self.reachy.r_arm.r_gripper: GRIPPER_CLOSED},
            duration=0.8,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.8)

        # Forcer la position
        self.reachy.r_arm.r_gripper.goal_position = GRIPPER_CLOSED
        time.sleep(0.3)

        logger.info(f"Gripper closed to {self.reachy.r_arm.r_gripper.present_position:.1f}°")
        
    def open_gripper(self):
        """Ouvre la pince"""
        logger.info(f"Opening gripper from {self.reachy.r_arm.r_gripper.present_position:.1f}°")
        
        goto(
            goal_positions={self.reachy.r_arm.r_gripper: GRIPPER_OPEN},
            duration=0.5,
            interpolation_mode=InterpolationMode.LINEAR,
        )
        time.sleep(0.5)
        
        logger.info(f"Gripper opened to {self.reachy.r_arm.r_gripper.present_position:.1f}°")
        
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
                # SDK 2021 travaille en degrés
                goto(
                    goal_positions={
                        self.reachy.head.l_antenna: p,
                        self.reachy.head.r_antenna: -p,
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
