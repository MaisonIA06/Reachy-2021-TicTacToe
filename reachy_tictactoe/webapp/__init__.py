"""Interface web de pilotage du TicTacToe Reachy.

``controller`` sérialise les actions du robot (une seule à la fois),
``server`` expose l'API et la page. Le serveur ne connaît du robot que la
``GameSession`` et le contrôleur : il ne parle jamais au SDK directement.
"""
