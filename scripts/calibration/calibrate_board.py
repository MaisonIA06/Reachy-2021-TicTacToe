#!/usr/bin/env python3
"""
Script de calibration du plateau TicTacToe (complet)

Ce script permet de calibrer:
1. La zone globale du plateau dans l'image de la caméra
2. Les coordonnées précises de chaque case du morpion

Les résultats sont automatiquement sauvegardés dans le fichier
de configuration centralisé (reachy_tictactoe/config.py)

⚠️ Ce script doit être exécuté SUR REACHY (pas sur votre PC de dev)
   car il a besoin d'accéder à la caméra du robot.

Usage:
    # Sur Reachy - Calibration complète
    python scripts/calibration/calibrate_board.py --host localhost
    
    # Test avec une image existante (développement)
    python scripts/calibration/calibrate_board.py --image test_board.jpg
    
    # Calibrer uniquement le plateau (zone globale)
    python scripts/calibration/calibrate_board.py --host localhost --board-only
    
    # Calibrer uniquement les cases
    python scripts/calibration/calibrate_board.py --host localhost --cases-only
"""

import os
import sys
import argparse
import numpy as np
import cv2 as cv
from pathlib import Path

# Ajouter le projet au path (3 niveaux: calibrate_board.py -> calibration -> scripts -> racine)
project_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_dir))


def capture_image_from_reachy(host='localhost'):
    """
    Capture une image depuis la caméra droite de Reachy
    
    Args:
        host: Adresse IP de Reachy
        
    Returns:
        numpy.ndarray: Image BGR
    """
    print(f"🔌 Connexion à Reachy ({host})...")
    
    try:
        from reachy_sdk import ReachySDK
        import time
        
        reachy = ReachySDK(host=host)
        
        # Activer la tête pour le look_at
        print("🎥 Activation de la caméra...")
        reachy.turn_on('head')
        time.sleep(0.5)
        
        # Position pour voir le plateau (à ajuster selon votre setup)
        print("👀 Orientation de la tête vers le plateau...")
        reachy.head.look_at(x=0.5, y=0, z=-0.6, duration=1.0)
        time.sleep(1.5)
        
        # Capturer l'image
        print("📸 Capture de l'image...")
        time.sleep(0.5)
        img = reachy.right_camera.last_frame
        
        if img is None or len(img) == 0:
            print("❌ Impossible de capturer une image depuis la caméra")
            return None
        
        print(f"✓ Image capturée: {img.shape}")
        
        # Sauvegarder l'image pour référence
        cv.imwrite('/tmp/calibration_capture.jpg', img)
        print("✓ Image sauvegardée: /tmp/calibration_capture.jpg")
        
        return img
        
    except Exception as e:
        print(f"❌ Erreur lors de la capture: {e}")
        return None


def load_image_from_file(filepath):
    """
    Charge une image depuis un fichier
    
    Args:
        filepath: Chemin vers l'image
        
    Returns:
        numpy.ndarray: Image BGR
    """
    if not os.path.exists(filepath):
        print(f"❌ Fichier introuvable: {filepath}")
        return None
    
    img = cv.imread(filepath)
    if img is None:
        print(f"❌ Impossible de charger l'image: {filepath}")
        return None
    
    print(f"✓ Image chargée: {img.shape}")
    return img


class BoardZoneCalibrator:
    """Interface interactive pour calibrer la zone globale du plateau"""
    
    def __init__(self, image):
        """
        Initialise le calibrateur de zone globale
        
        Args:
            image: Image numpy array (BGR)
        """
        self.original_image = image.copy()
        self.display_image = image.copy()
        self.board_zone = None
        self.temp_rect = None
        self.drawing = False
        self.start_point = None
        
    def mouse_callback(self, event, x, y, flags, param):
        """Callback pour les événements de souris"""
        
        if event == cv.EVENT_LBUTTONDOWN:
            # Début du tracé
            self.drawing = True
            self.start_point = (x, y)
            
        elif event == cv.EVENT_MOUSEMOVE and self.drawing:
            # Mise à jour du rectangle temporaire
            self.temp_rect = (self.start_point, (x, y))
            self.update_display()
            
        elif event == cv.EVENT_LBUTTONUP:
            # Fin du tracé
            self.drawing = False
            end_point = (x, y)
            
            # Calculer les coordonnées du rectangle
            x1, y1 = self.start_point
            x2, y2 = end_point
            
            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)
            bottom = max(y1, y2)
            
            # Enregistrer la zone
            self.board_zone = (left, right, top, bottom)
            
            print(f"✓ Zone du plateau: left={left}, right={right}, top={top}, bottom={bottom}")
            
            self.temp_rect = None
            self.update_display()
            
    def update_display(self):
        """Met à jour l'affichage"""
        self.display_image = self.original_image.copy()
        
        # Dessiner la zone du plateau si définie
        if self.board_zone:
            left, right, top, bottom = self.board_zone
            cv.rectangle(self.display_image, (left, top), (right, bottom), (0, 255, 0), 3)
            cv.putText(self.display_image, "PLATEAU", 
                      (left + 10, top + 30), 
                      cv.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        
        # Dessiner le rectangle en cours de tracé
        if self.temp_rect:
            start, end = self.temp_rect
            cv.rectangle(self.display_image, start, end, (255, 0, 0), 2)
        
        # Afficher les instructions
        if self.board_zone is None:
            instructions = "Tracez un rectangle autour du PLATEAU ENTIER"
            color = (0, 0, 255)
        else:
            instructions = "Appuyez sur 's' pour sauvegarder, 'r' pour recommencer, 'q' pour quitter"
            color = (0, 255, 0)
        
        cv.putText(self.display_image, instructions, (10, 30), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        cv.imshow('Calibration - Zone du Plateau', self.display_image)
        
    def run(self):
        """Lance l'interface de calibration"""
        cv.namedWindow('Calibration - Zone du Plateau')
        cv.setMouseCallback('Calibration - Zone du Plateau', self.mouse_callback)
        
        print()
        print("="*70)
        print("📐 CALIBRATION DE LA ZONE DU PLATEAU")
        print("="*70)
        print()
        print("Instructions:")
        print("  1. Tracez un rectangle autour du PLATEAU ENTIER")
        print("  2. Incluez tout le plateau mais pas trop de marge")
        print("  3. Appuyez sur 's' pour sauvegarder")
        print("  4. Appuyez sur 'r' pour recommencer")
        print("  5. Appuyez sur 'q' pour quitter sans sauvegarder")
        print()
        
        self.update_display()
        
        while True:
            key = cv.waitKey(1) & 0xFF
            
            if key == ord('q'):
                # Quitter
                print("❌ Calibration annulée")
                cv.destroyAllWindows()
                return None
                
            elif key == ord('r'):
                # Recommencer
                print("🔄 Recommencer la calibration...")
                self.board_zone = None
                self.update_display()
                
            elif key == ord('s'):
                # Sauvegarder
                if self.board_zone is not None:
                    cv.destroyAllWindows()
                    return self.board_zone
                else:
                    print(f"⚠️  Veuillez d'abord tracer la zone du plateau")


class BoardCalibrator:
    """Interface interactive pour calibrer les coordonnées des cases"""
    
    def __init__(self, image, board_zone=None):
        """
        Initialise le calibrateur
        
        Args:
            image: Image numpy array (BGR) - image complète ou zone du plateau
            board_zone: tuple (left, right, top, bottom) si on travaille sur zone extraite
        """
        self.original_image = image.copy()
        self.display_image = image.copy()
        self.board_zone = board_zone
        self.current_box = 0
        self.boxes = {}
        self.temp_rect = None
        self.drawing = False
        self.start_point = None
        
        # Noms des cases
        self.box_names = [
            (0, 0), (0, 1), (0, 2),
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2),
        ]
        
    def mouse_callback(self, event, x, y, flags, param):
        """Callback pour les événements de souris"""
        
        if event == cv.EVENT_LBUTTONDOWN:
            # Début du tracé
            self.drawing = True
            self.start_point = (x, y)
            
        elif event == cv.EVENT_MOUSEMOVE and self.drawing:
            # Mise à jour du rectangle temporaire
            self.temp_rect = (self.start_point, (x, y))
            self.update_display()
            
        elif event == cv.EVENT_LBUTTONUP:
            # Fin du tracé
            self.drawing = False
            end_point = (x, y)
            
            # Calculer les coordonnées du rectangle
            x1, y1 = self.start_point
            x2, y2 = end_point
            
            left = min(x1, x2)
            right = max(x1, x2)
            top = min(y1, y2)
            bottom = max(y1, y2)
            
            # Enregistrer la case
            box_name = self.box_names[self.current_box]
            self.boxes[box_name] = (left, right, top, bottom)
            
            print(f"✓ Case {box_name}: ({left}, {right}, {top}, {bottom})")
            
            # Passer à la case suivante
            self.current_box += 1
            self.temp_rect = None
            self.update_display()
            
    def update_display(self):
        """Met à jour l'affichage"""
        self.display_image = self.original_image.copy()
        
        # Dessiner les cases déjà calibrées
        for box_name, coords in self.boxes.items():
            left, right, top, bottom = coords
            cv.rectangle(self.display_image, (left, top), (right, bottom), (0, 255, 0), 2)
            
            # Ajouter le numéro de la case
            center_x = (left + right) // 2
            center_y = (top + bottom) // 2
            label = f"{box_name[0]},{box_name[1]}"
            cv.putText(self.display_image, label, (center_x - 20, center_y), 
                      cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Dessiner le rectangle en cours de tracé
        if self.temp_rect:
            start, end = self.temp_rect
            cv.rectangle(self.display_image, start, end, (255, 0, 0), 2)
        
        # Afficher les instructions
        if self.current_box < len(self.box_names):
            box_name = self.box_names[self.current_box]
            instructions = f"Tracez la case {box_name} ({self.current_box + 1}/{len(self.box_names)})"
        else:
            instructions = "Calibration terminee ! Appuyez sur 's' pour sauvegarder, 'q' pour quitter"
        
        cv.putText(self.display_image, instructions, (10, 30), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Grille de référence
        cv.putText(self.display_image, "Ordre: (0,0) (0,1) (0,2)", (10, 60), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv.putText(self.display_image, "       (1,0) (1,1) (1,2)", (10, 80), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv.putText(self.display_image, "       (2,0) (2,1) (2,2)", (10, 100), 
                  cv.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        cv.imshow('Calibration', self.display_image)
        
    def run(self):
        """Lance l'interface de calibration"""
        cv.namedWindow('Calibration')
        cv.setMouseCallback('Calibration', self.mouse_callback)
        
        print()
        print("="*70)
        print("📐 CALIBRATION DES CASES DU PLATEAU")
        print("="*70)
        print()
        print("Instructions:")
        print("  1. Cliquez et glissez pour tracer un rectangle autour de chaque case")
        print("  2. Suivez l'ordre indiqué: (0,0) -> (0,1) -> ... -> (2,2)")
        print("  3. Appuyez sur 's' pour sauvegarder les coordonnées")
        print("  4. Appuyez sur 'r' pour recommencer")
        print("  5. Appuyez sur 'q' pour quitter sans sauvegarder")
        print()
        print("  Layout du plateau (vu depuis Reachy):")
        print("     (0,0) | (0,1) | (0,2)")
        print("     ------|-------|------")
        print("     (1,0) | (1,1) | (1,2)")
        print("     ------|-------|------")
        print("     (2,0) | (2,1) | (2,2)")
        print()
        
        self.update_display()
        
        while True:
            key = cv.waitKey(1) & 0xFF
            
            if key == ord('q'):
                # Quitter
                print("❌ Calibration annulée")
                cv.destroyAllWindows()
                return None
                
            elif key == ord('r'):
                # Recommencer
                print("🔄 Recommencer la calibration...")
                self.current_box = 0
                self.boxes = {}
                self.update_display()
                
            elif key == ord('s'):
                # Sauvegarder
                if len(self.boxes) == 9:
                    cv.destroyAllWindows()
                    return self.boxes
                else:
                    print(f"⚠️  Calibration incomplète ({len(self.boxes)}/9 cases)")
                    
    def generate_code(self):
        """Génère le code Python pour vision.py"""
        if len(self.boxes) != 9:
            print("❌ Calibration incomplète")
            return None
        
        # Organiser les coordonnées par ligne
        code = "board_cases = np.array((\n"
        for row in range(3):
            code += "    ("
            for col in range(3):
                box_name = (row, col)
                left, right, top, bottom = self.boxes[box_name]
                code += f"({left}, {right}, {top}, {bottom})"
                if col < 2:
                    code += ", "
            code += ")"
            if row < 2:
                code += ","
            code += f"  # Ligne {row}\n"
        code += "))"
        
        return code


def save_calibration(board_zone=None, boxes=None):
    """
    Sauvegarde les coordonnées calibrées dans le fichier config.py
    
    Args:
        board_zone: tuple (left, right, top, bottom) pour la zone du plateau
        boxes: Dictionnaire des coordonnées des cases
    """
    try:
        # Importer directement config.py sans charger tout le package
        # (évite les dépendances comme sklearn, tflite, etc.)
        import importlib.util
        config_path = project_dir / 'reachy_tictactoe' / 'config.py'
        spec = importlib.util.spec_from_file_location("config", config_path)
        config = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(config)
        
        # Préparer les données
        board_position = None
        board_cases = None
        
        if board_zone is not None:
            left, right, top, bottom = board_zone
            board_position = {
                'left_x': left,
                'right_x': right,
                'top_y': top,
                'bottom_y': bottom,
            }
        
        if boxes is not None:
            # Convertir le dictionnaire en numpy array
            board_cases = np.zeros((3, 3, 4), dtype=np.int32)
            for (row, col), coords in boxes.items():
                board_cases[row, col] = coords
        
        # Sauvegarder dans config.py
        config.save_calibration(board_position, board_cases)
        
        print()
        print("="*70)
        print("✅ CALIBRATION SAUVEGARDÉE")
        print("="*70)
        print(f"📄 Fichier: {Path(config.__file__).absolute()}")
        print()
        
        if board_position:
            print("📐 Zone du plateau:")
            for key, value in board_position.items():
                print(f"   {key}: {value}")
            print()
        
        if boxes:
            print("📦 Cases calibrées: 9/9")
            print()
        
        print("✅ La configuration est maintenant utilisée par tous les scripts!")
        print("   Vous pouvez redémarrer le jeu pour appliquer les changements.")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Calibration complète du plateau TicTacToe'
    )
    
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        '--host',
        default='localhost',
        help='Adresse IP de Reachy (défaut: localhost)'
    )
    group.add_argument(
        '--image',
        help='Chemin vers une image existante (pour test)'
    )
    
    parser.add_argument(
        '--board-only',
        action='store_true',
        help='Calibrer uniquement la zone du plateau (pas les cases)'
    )
    
    parser.add_argument(
        '--cases-only',
        action='store_true',
        help='Calibrer uniquement les cases (utilise la zone actuelle du config)'
    )
    
    args = parser.parse_args()
    
    print()
    print("="*70)
    print("🎯 CALIBRATION DU PLATEAU TICTACTOE")
    print("="*70)
    print()
    
    # Obtenir l'image
    if args.image:
        print(f"📁 Mode test avec image: {args.image}")
        image = load_image_from_file(args.image)
    else:
        print(f"🤖 Mode Reachy: connexion à {args.host}")
        image = capture_image_from_reachy(args.host)
    
    if image is None:
        print("❌ Impossible d'obtenir une image")
        return 1
    
    board_zone = None
    boxes = None
    
    # Calibration de la zone du plateau
    if not args.cases_only:
        print()
        print("📍 ÉTAPE 1/2 : Calibration de la zone du plateau")
        print()
        
        zone_calibrator = BoardZoneCalibrator(image)
        board_zone = zone_calibrator.run()
        
        if board_zone is None:
            print("❌ Calibration de la zone annulée")
            return 1
        
        # Sauvegarder la zone immédiatement
        if args.board_only:
            if save_calibration(board_zone=board_zone):
                return 0
            else:
                return 1
        
        # Extraire la zone du plateau pour calibrer les cases
        left, right, top, bottom = board_zone
        board_image = image[top:bottom, left:right]
    else:
        # Utiliser la zone actuelle du config
        try:
            from reachy_tictactoe import config
            left, right, top, bottom = config.get_board_position()
            board_zone = (left, right, top, bottom)
            board_image = image[top:bottom, left:right]
            print(f"✓ Utilisation de la zone du config: {board_zone}")
        except Exception as e:
            print(f"❌ Impossible de charger la zone du config: {e}")
            print("   Utilisez --board-only d'abord ou enlevez --cases-only")
            return 1
    
    # Calibration des cases
    if not args.board_only:
        print()
        print("📍 ÉTAPE 2/2 : Calibration des cases")
        print()
        
        calibrator = BoardCalibrator(board_image, board_zone)
        boxes = calibrator.run()
        
        if boxes is None:
            print("❌ Calibration des cases annulée")
            return 1
    
    # Sauvegarder les résultats
    if save_calibration(board_zone=board_zone, boxes=boxes):
        return 0
    else:
        return 1


if __name__ == '__main__':
    sys.exit(main())

