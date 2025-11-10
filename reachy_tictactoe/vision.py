"""
Module de vision adapté pour Reachy SDK 2021
Utilise TensorFlow Lite Runtime au lieu de EdgeTPU
IMPORTANT: Les modèles doivent être compilés pour CPU (pas EdgeTPU)
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
    try:
        import tensorflow.lite as tflite
    except ImportError:
        raise ImportError(
            "Ni tflite_runtime ni tensorflow ne sont installés. "
            "Installez l'un des deux avec:\n"
            "  pip install tflite-runtime\n"
            "ou\n"
            "  pip install tensorflow"
        )

from .utils import piece2id
from .detect_board import get_board_cases
from . import config


logger = logging.getLogger('reachy.tictactoe')


dir_path = os.path.dirname(os.path.realpath(__file__))
model_path = os.path.join(dir_path, 'models')


class TFLiteClassifier:
    """Wrapper pour les modèles TensorFlow Lite (CPU uniquement)"""
    
    def __init__(self, model_path, label_path):
        """
        Initialise le classificateur TFLite
        
        Args:
            model_path: Chemin vers le modèle .tflite (DOIT être compilé pour CPU)
            label_path: Chemin vers le fichier de labels
        """
        logger.info(f'Loading TFLite model: {model_path}')
        
        # Vérifier que le modèle existe
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Le modèle {model_path} n'existe pas. "
                f"Consultez EDGE_TPU_CONVERSION.md pour créer des modèles compatibles CPU."
            )
        
        try:
            # Charger l'interpréteur TFLite (CPU uniquement)
            self.interpreter = tflite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            
        except RuntimeError as e:
            if 'edgetpu-custom-op' in str(e):
                raise RuntimeError(
                    f"\n\n{'='*70}\n"
                    f"ERREUR: Le modèle {os.path.basename(model_path)} est compilé pour EdgeTPU.\n"
                    f"Votre NUC n'a pas d'accélérateur EdgeTPU.\n\n"
                    f"SOLUTIONS:\n"
                    f"1. Reconvertir les modèles pour CPU (recommandé)\n"
                    f"   Consultez: EDGE_TPU_CONVERSION.md\n\n"
                    f"2. Utiliser un modèle de remplacement simple\n"
                    f"   Exécutez: python scripts/create_fallback_models.py\n\n"
                    f"3. Ajouter un accélérateur EdgeTPU USB à votre NUC\n"
                    f"{'='*70}\n"
                ) from e
            raise
        
        # Récupérer les détails des tenseurs d'entrée et de sortie
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Charger les labels
        self.labels = self._load_labels(label_path)
        
        logger.info(f'Model loaded successfully: {os.path.basename(model_path)}')
        
    def _load_labels(self, label_path):
        """Charge les labels depuis le fichier"""
        if not os.path.exists(label_path):
            logger.warning(f'Label file not found: {label_path}')
            return []
            
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
        
        # Normaliser si nécessaire (selon le type de données attendu)
        input_dtype = self.input_details[0]['dtype']
        if input_dtype == np.float32:
            input_data = (np.float32(input_data) - 127.5) / 127.5
        elif input_dtype == np.uint8:
            input_data = np.uint8(input_data)
            
        # Exécuter l'inférence
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        
        # Récupérer les résultats
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        results = np.squeeze(output_data)
        
        # Obtenir les top_k résultats
        top_indices = np.argsort(results)[-top_k:][::-1]
        
        return [(int(i), float(results[i])) for i in top_indices]


# Initialiser les classificateurs avec gestion d'erreur
try:
    boxes_classifier = TFLiteClassifier(
        os.path.join(model_path, 'ttt-boxes.tflite'),
        os.path.join(model_path, 'ttt-boxes.txt')
    )
    
    valid_classifier = TFLiteClassifier(
        os.path.join(model_path, 'ttt-valid-board.tflite'),
        os.path.join(model_path, 'ttt-valid-board.txt')
    )
    
    logger.info('Vision models loaded successfully')
    
except RuntimeError as e:
    logger.error(f'Failed to load vision models: {e}')
    raise
except FileNotFoundError as e:
    logger.error(f'Model files not found: {e}')
    raise


# Charger les coordonnées depuis la configuration
# Ces valeurs sont maintenant gérées dans config.py
# Vous pouvez les recalibrer avec: python scripts/calibrate_board.py --host localhost
board_cases = config.get_board_cases()
board_rect = np.array(config.get_board_position())


def get_board_configuration(img):
    """
    Analyse l'image pour déterminer l'état du plateau
    """
    board = np.zeros((3, 3), dtype=np.uint8)
    
    # AJOUT: Logger la taille de l'image
    logger.info(f'Image dimensions: {img.shape}')
    
    # ✅ CORRECTION CRITIQUE : Extraire d'abord la zone du plateau
    # Les coordonnées dans board_cases sont RELATIVES à cette zone
    lx_board, rx_board, ly_board, ry_board = board_rect
    board_img = img[ly_board:ry_board, lx_board:rx_board]
    logger.info(f'Board zone extracted: {board_img.shape} from position [{lx_board}:{rx_board}, {ly_board}:{ry_board}]')
    
    custom_board_cases = board_cases
    logger.debug("using static board coordinates")
        
    sanity_check = True
    
    # Analyser chaque case DANS LA ZONE DU PLATEAU
    for row in range(3):
        for col in range(3):
            lx, rx, ly, ry = custom_board_cases[row, col]
            
            # AJOUT: Vérifier les limites dans la zone du plateau (pas l'image complète!)
            img_h, img_w = board_img.shape[:2]  # ← board_img au lieu de img !
            if lx < 0 or rx > img_w or ly < 0 or ry > img_h:
                logger.error(
                    f'Case ({row},{col}) coordinates out of bounds: '
                    f'[{lx}:{rx}, {ly}:{ry}] vs board zone [{img_w}x{img_h}]'
                )
                piece, score = 0, 0.0
            elif (rx - lx) <= 0 or (ry - ly) <= 0:
                logger.error(
                    f'Case ({row},{col}) has invalid dimensions: '
                    f'width={rx-lx}, height={ry-ly}'
                )
                piece, score = 0, 0.0
            else:
                # AJOUT: Logger les coordonnées de la case
                logger.debug(
                    f'Extracting case ({row},{col}): '
                    f'[{lx}:{rx}, {ly}:{ry}] = {rx-lx}x{ry-ly}px'
                )
                # ✅ Extraire de board_img (zone du plateau), pas de img (image complète)
                box_img = board_img[ly:ry, lx:rx]
                piece, score = identify_box(box_img)
                
                # Logger le résultat de la détection
                logger.info(f'Case ({row},{col}): piece={piece}, score={score:.2f}')
            
            # Si le score de confiance est trop bas, considérer comme vide
            if score < 0.75:  # ← Réduit de 0.9 à 0.75 pour être moins strict
                logger.debug(f'Case ({row},{col}): score too low ({score:.2f} < 0.75), marking as empty')
                piece = 0
                
            # Inverser le plateau pour le présenter du point de vue de l'humain
            board[2 - row, 2 - col] = piece
            
    logger.info(f'Board state detected: {board}')
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
    try:
        # Convertir l'image en PIL
        pil_img = img_as_pil(box_img)
        
        # Classifier l'image
        res = boxes_classifier.classify_with_image(pil_img, top_k=1)
        
        if not res:
            return 0, 0.0
            
        label_id, score = res[0]
        
        return label_id, score
        
    except Exception as e:
        logger.error(f'Box identification failed: {e}')
        return 0, 0.0


def is_board_valid(img):
    """
    Vérifie si un plateau valide est présent dans l'image
    
    Args:
        img: Image numpy array (BGR)
        
    Returns:
        bool: True si un plateau valide est détecté
    """
    try:
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
        label = valid_classifier.labels[label_id] if label_id < len(valid_classifier.labels) else 'unknown'
        
        logger.info('Board validity check', extra={
            'label': label,
            'score': score,
        })
        
        return label_id == 1 and score > 0.65
        
    except Exception as e:
        logger.error(f'Board validation failed: {e}')
        return False


def img_as_pil(img):
    """
    Convertit une image OpenCV en image PIL
    
    Args:
        img: Image numpy array (BGR)
        
    Returns:
        PIL.Image: Image PIL (RGB)
    """
    return Image.fromarray(cv.cvtColor(img.copy(), cv.COLOR_BGR2RGB))
