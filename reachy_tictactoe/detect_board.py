import cv2 as cv
import numpy as np

from sklearn.cluster import KMeans
from . import config


def find_board(board_img):
    edges = cv.Canny(cv.cvtColor(board_img, cv.COLOR_BGR2GRAY), 210, 256)

    rho = 1  # distance resolution in pixels of the Hough grid
    theta = np.pi / 180  # angular resolution in radians of the Hough grid
    # minimum number of votes (intersections in Hough grid cell)
    threshold = 15
    min_line_length = 150  # minimum number of pixels making up a line
    max_line_gap = 50  # maximum gap in pixels between connectable line segment

    # Run Hough on edge detected image
    # Output "lines" is an array containing endpoints of detected line segments
    lines = cv.HoughLinesP(edges, rho, theta, threshold, np.array([]),
                           min_line_length, max_line_gap)

    horizontal, vertical = [], []
    for line in lines:
        for x1, y1, x2, y2 in line:
            # Eviter la division par zéro
            dx = x2 - x1
            dy = y2 - y1

            #Ignorer les lignes de longueur nulle
            if dx == 0 or dy == 0:
                continue

            #Cas d'une ligne verticale parfaite (dx=0)
            if dx == 0:
                #Ligne verticale : utiliser une pente trés grande
                a = float('inf')
                b = x1 #pour calculer l'ordonnée à l'origine
                vertical.append((a, b))
            else:
                a = dy / dx
                b = y1 - a * x1

            if np.abs(a) < 0.1:
                horizontal.append((a, b))
            elif np.abs(a) > 2:
                vertical.append((a, b))

    vertical = np.array(vertical)
    V = np.array([(200 - b) / a for a, b in vertical]).reshape(-1, 1)
    kmeans = KMeans(n_clusters=4, random_state=0).fit(V)
    vertical = np.array(
        [vertical[np.where(kmeans.labels_ == i)[0]].mean(axis=0)
         for i in range(4)])

    horizontal = np.array(horizontal)
    H = np.array([200 * a + b for a, b in horizontal]).reshape(-1, 1)
    kmeans = KMeans(n_clusters=4, random_state=0).fit(H)
    horizontal = np.array(
        [horizontal[np.where(kmeans.labels_ == i)[0]].mean(axis=0)
         for i in range(4)])

    V = np.array([(200 - b) / a for a, b in vertical])
    vertical = vertical[V.argsort()]

    H = np.array([200 * a + b for a, b in horizontal])
    horizontal = horizontal[H.argsort()]

    return vertical.tolist(), horizontal.tolist()


def find_board_corners(board_img):
    v, h = find_board(board_img)

    corners = []

    for a1, b1 in v:
        for a2, b2 in h:
            x = (b2 - b1) / (a1 - a2)
            y = a1 * x + b1
            corners.append((x, y))

    return np.array(corners, dtype=np.int32)


def find_board_cases(board_img):
    corners = find_board_corners(board_img)
    (A, E, I, M,
     B, F, J, N,
     C, G, K, O,
     D, H, L, P) = corners

    board_cases = np.array((
        ((E[0], F[0], B[1], F[1]),
         (F[0], G[0], C[1], G[1]),
         (G[0], H[0], D[1], H[1]),),

        ((I[0], J[0], F[1], J[1]),
         (J[0], K[0], G[1], K[1]),
         (K[0], L[0], H[1], L[1]),),

        ((M[0], N[0], J[1], N[1]),
         (N[0], O[0], K[1], O[1]),
         (O[0], P[0], L[1], P[1]), ),
    ), dtype=np.int32)

    # AJOUT: Vérifier et corriger les coordonnées invalides
    for row in range(3):
        for col in range(3):
            lx, rx, ly, ry = board_cases[row, col]
            # Corriger si inversé
            if lx > rx:
                lx, rx = rx, lx
            if ly > ry:
                ly, ry = ry, ly
            board_cases[row, col] = (lx, rx, ly, ry)

    return board_cases


def get_board_cases(img):
    """
    Extrait les coordonnées des cases du plateau depuis l'image.
    Utilise la configuration centralisée (config.py) pour la zone du plateau.
    
    Args:
        img: Image complète de la caméra (numpy array BGR)
        
    Returns:
        numpy.ndarray: Array 3x3x4 avec les coordonnées absolues de chaque case
    """
    # Charger les coordonnées depuis la configuration
    lx, rx, ly, ry = config.get_board_position()
    
    # Extraire la zone du plateau
    img = img[ly:ry, lx:rx, :]

    # Détecter les cases dans la zone du plateau
    cases = find_board_cases(img)
    
    # Convertir les coordonnées relatives en coordonnées absolues
    for row in range(3):
        for col in range(3):
            cases[row, col] += (lx, lx, ly, ly)

    return cases
