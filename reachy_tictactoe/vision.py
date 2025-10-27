"""
Module de vision adapté pour Reachy SDK 2021
Utilise TensorFlow Lite Runtime au lieu de EdgeTPU
"""
import numpy as np
import cv2 as cv
import logging
import os

from PIL import Image

# Remplacer EdgeTPU par TensorFlow Lite Runtime
try:
    import tflite_runtime.interpreter as tflite
except ImportError:
    import tensorflow.lite as tflite

from .utils import piece2id
from .detect_board import get_board_cases


logger = logging.getLogger('reachy.tictactoe')


dir_path = os.path.dirname(os.path.realpath(__file__))
model_path = os.path.join(dir_path, 'models')


class TFLiteClassifier:
    """Wrapper pour les modèles TensorFlow Lite"""
    
    def __init__(self, model_path, label_path):
        """
        Initialise le classificateur TFLite
        
        Args:
            model_path: Chemin vers le modèle .tflite
            label_path: Chemin vers le fichier de labels
        """
        # Charger l'interpréteur TFLite
        self.interpreter = tflite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        
        # Récupérer les détails des tenseurs d'entrée et de sortie
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Charger les labels
        self.labels = self._load_labels(label_path)
        
    def _load_labels(self, label_path):
        """Charge les labels depuis le fichier"""
        with open(label_path, 'r') as f:
            labels = [line.strip() for line in f.readlines()]
        return labels
        
    def classify_with_image(self, img, top_k=1):
        """
        Classifie une image
        
        Args:
            img: Image PIL
            top_k: Nombre de résultats à retourner
            
        Returns:
            list: Liste de tuples (label_id, score)
        """
        # Préparer l'image
        input_shape = self.input_details[0]['shape']
        height = input_shape[1]
        width = input_shape[2]
        
        # Redimensionner l'image
        img = img.resize((width, height))
        
        # Convertir en array numpy
        input_data = np.expand_dims(img, axis=0)
        
        # Normaliser si nécessaire
        if self.input_details[0]['dtype'] == np.float32:
            input_data = (np.float32(input_data) - 127.5) / 127.5
            
        # Exécuter l'inférence
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        
        # Récupérer les résultats
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        results = np.squeeze(output_data)
        
        # Obtenir les top_k résultats
        top_indices = np.argsort(results)[-top_k:][::-1]
        
        return [(int(i), float(results[i])) for i in top_indices]


# Initialiser les classificateurs
boxes_classifier = TFLiteClassifier(
    os.path.join(model_path, 'ttt-boxes.tflite'),
    os.path.join(model_path, 'ttt-boxes.txt')
)

valid_classifier = TFLiteClassifier(
    os.path.join(model_path, 'ttt-valid-board.tflite'),
    os.path.join(model_path, 'ttt-valid-board.txt')
)


# Coordonnées des cases du plateau
board_cases = np.array((
    ((209, 316, 253, 346),  # Case (0,0) - coin supérieur gauche
     (316, 425, 253, 346),  # Case (0,1)
     (425, 529, 253, 346)),  # Case (0,2)
     
    ((189, 306, 346, 455),  # Case (1,0)
     (306, 428, 346, 455),  # Case (1,1)
     (428, 538, 346, 455)),  # Case (1,2)
     
    ((174, 299, 455, 580),  # Case (2,0)
     (299, 429, 455, 580),  # Case (2,1)
     (429, 551, 455, 580)),  # Case (2,2)
))

# Zone du plateau (left, right, top, bottom)
board_rect = np.array((250, 700, 350, 1000))


def get_board_configuration(img):
    """
    Analyse l'image pour déterminer l'état du plateau
    
    Args:
        img: Image numpy array (BGR)
        
    Returns:
        tuple: (board, sanity_check)
            - board: array 3x3 avec l'état de chaque case
            - sanity_check: bool indiquant si l'analyse est fiable
    """
    board = np.zeros((3, 3), dtype=np.uint8)
    
    # Essayer de détecter dynamiquement les cases
    # Si ça échoue, utiliser les coordonnées prédéfinies
    try:
        custom_board_cases = get_board_cases(img)
    except Exception as e:
        logger.warning('Board detection failed, using default coordinates', 
                      extra={'error': str(e)})
        custom_board_cases = board_cases
        
    sanity_check = True
    
    # Analyser chaque case
    for row in range(3):
        for col in range(3):
            lx, rx, ly, ry = custom_board_cases[row, col]
            piece, score = identify_box(img[ly:ry, lx:rx])
            
            # Si le score de confiance est trop bas, considérer comme vide
            if score < 0.9:
                piece = 0
                
            # Inverser le plateau pour le présenter du point de vue de l'humain
            board[2 - row, 2 - col] = piece
            
    return board, sanity_check


def identify_box(box_img):
    """
    Identifie le contenu d'une case
    
    Args:
        box_img: Image de la case (numpy array BGR)
        
    Returns:
        tuple: (label, score)
            - label: ID du type de pièce (0=vide, 1=cube, 2=cylindre)
            - score: Score de confiance (0-1)
    """
    # Convertir l'image en PIL
    pil_img = img_as_pil(box_img)
    
    # Classifier l'image
    res = boxes_classifier.classify_with_image(pil_img, top_k=1)
    
    if not res:
        return 0, 0.0
        
    label_id, score = res[0]
    
    return label_id, score


def is_board_valid(img):
    """
    Vérifie si un plateau valide est présent dans l'image
    
    Args:
        img: Image numpy array (BGR)
        
    Returns:
        bool: True si un plateau valide est détecté
    """
    # Extraire la zone du plateau
    lx, rx, ly, ry = board_rect
    board_img = img[ly:ry, lx:rx]
    
    # Convertir en PIL
    pil_img = img_as_pil(board_img)
    
    # Classifier
    res = valid_classifier.classify_with_image(pil_img, top_k=1)
    
    if not res:
        return False
        
    label_id, score = res[0]
    label = valid_classifier.labels[label_id]
    
    logger.info('Board validity check', extra={
        'label': label,
        'score': score,
    })
    
    return label == 'valid' and score > 0.65


def img_as_pil(img):
    """
    Convertit une image OpenCV en image PIL
    
    Args:
        img: Image numpy array (BGR)
        
    Returns:
        PIL.Image: Image PIL (RGB)
    """
    return Image.fromarray(cv.cvtColor(img.copy(), cv.COLOR_BGR2RGB))
