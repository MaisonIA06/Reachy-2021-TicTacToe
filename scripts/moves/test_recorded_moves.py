#!/usr/bin/env python3
"""
Script pour tester les mouvements enregistrés du robot Reachy

Usage:
    # Tester un mouvement spécifique
    python scripts/moves/test_recorded_moves.py --name grab_1 --host localhost
    
    # Tester tous les mouvements
    python scripts/moves/test_recorded_moves.py --all --host localhost
    
    # Mode interactif
    python scripts/moves/test_recorded_moves.py --interactive --host localhost
"""

import argparse
import numpy as np
import time
import os
import glob
from reachy_sdk import ReachySDK
from reachy_sdk.trajectory import goto
from reachy_sdk.trajectory.interpolation import InterpolationMode


class MoveTester:
    """Testeur de mouvements pour Reachy"""
    
    def __init__(self, host='localhost'):
        """
        Initialise la connexion avec Reachy
        
        Args:
            host: Adresse IP du robot
        """
        print(f"🔌 Connexion au robot Reachy ({host})...")
        self.reachy = ReachySDK(host=host)
        print("✅ Connecté au robot\n")
        
    def load_move(self, filepath):
        """
        Charge un mouvement depuis un fichier .npz
        
        Args:
            filepath: Chemin vers le fichier .npz
            
        Returns:
            dict: Données du mouvement ou None si erreur
        """
        try:
            data = np.load(filepath)
            return {key: data[key] for key in data.files}
        except Exception as e:
            print(f"❌ Erreur lors du chargement de {filepath} : {e}")
            return None
    
    
    def get_joint_object(self, joint_name):
        """
        Récupère l'objet Joint correspondant au nom
        
        Args:
            joint_name: Nom du joint (format SDK 2021, ex: 'r_arm.r_shoulder_pitch')
            
        Returns:
            Joint: Objet joint ou None
        """
        try:
            parts = joint_name.split('.')
            if len(parts) == 2:
                part_name, joint_short_name = parts
                
                if part_name == 'r_arm' and hasattr(self.reachy, 'r_arm'):
                    if hasattr(self.reachy.r_arm, joint_short_name):
                        return getattr(self.reachy.r_arm, joint_short_name)
                elif part_name == 'l_arm' and hasattr(self.reachy, 'l_arm'):
                    if hasattr(self.reachy.l_arm, joint_short_name):
                        return getattr(self.reachy.l_arm, joint_short_name)
                elif part_name == 'head' and hasattr(self.reachy, 'head'):
                    if hasattr(self.reachy.head, joint_short_name):
                        return getattr(self.reachy.head, joint_short_name)
        except Exception as e:
            print(f"⚠️  Impossible d'accéder au joint {joint_name}: {e}")
        
        return None
    
    def is_trajectory(self, move_data):
        """
        Détermine si le mouvement est une trajectoire ou une position simple
        
        Args:
            move_data: Données du mouvement
            
        Returns:
            bool: True si trajectoire, False si position simple
        """
        # Vérifier la première valeur
        first_value = list(move_data.values())[0]
        
        # Si c'est un array avec plus d'un élément, c'est une trajectoire
        if isinstance(first_value, np.ndarray):
            # Vérifier la forme plutôt que len() pour éviter les erreurs avec les scalaires
            if first_value.ndim == 0:  # Scalaire numpy
                return False
            elif first_value.ndim >= 1 and first_value.shape[0] > 1:
                return True
        
        return False
    
    def play_position(self, move_data, duration=2.0):
        """
        Joue une position simple
        
        Args:
            move_data: dict {joint_name: position_value}
            duration: Durée du mouvement
        """
        # Créer le dictionnaire de positions
        goal_positions = {}
        
        for joint_name, value in move_data.items():
            # Récupérer l'objet Joint (les noms sont déjà au format SDK 2021)
            joint_obj = self.get_joint_object(joint_name)
            
            if joint_obj is not None:
                # Convertir degrés en radians si nécessaire
                if isinstance(value, np.ndarray):
                    value = float(value)
                
                goal_positions[joint_obj] = value
        
        if not goal_positions:
            print("❌ Aucun joint valide trouvé dans le mouvement")
            return False
        
        # Exécuter le mouvement
        try:
            goto(
                goal_positions=goal_positions,
                duration=duration,
                interpolation_mode=InterpolationMode.MINIMUM_JERK,
            )
            time.sleep(duration)
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution : {e}")
            return False
    
    def play_trajectory(self, move_data):
        """
        Joue une trajectoire complète en utilisant goal_position natif du SDK
        
        Args:
            move_data: dict {joint_name: array_of_positions}
        """
        # Créer le dictionnaire de trajectoires
        trajectory = {}
        
        for joint_name, values in move_data.items():
            # Récupérer l'objet Joint (les noms sont déjà au format SDK 2021)
            joint_obj = self.get_joint_object(joint_name)
            
            if joint_obj is not None:
                trajectory[joint_obj] = values
        
        if not trajectory:
            print("❌ Aucun joint valide trouvé dans la trajectoire")
            return False
        
        # Jouer la trajectoire en définissant goal_position directement
        num_points = len(list(trajectory.values())[0])
        print(f"▶️  Lecture de la trajectoire ({num_points} points à 100 Hz = {num_points/100:.1f}s)")
        
        try:
            start_time = time.time()
            
            for i in range(num_points):
                # Définir goal_position pour chaque joint
                for joint_obj, traj in trajectory.items():
                    joint_obj.goal_position = traj[i]
                
                # Attendre 10ms pour maintenir 100 Hz
                time.sleep(0.01)
                
                # Afficher la progression tous les 10 points
                if i % 10 == 0:
                    progress = int((i / num_points) * 40)
                    bar = "█" * progress + "░" * (40 - progress)
                    elapsed = time.time() - start_time
                    print(f"\r   [{bar}] {i}/{num_points} points ({elapsed:.1f}s)", end='', flush=True)
            
            elapsed = time.time() - start_time
            print(f"\r   [{'█' * 40}] {num_points}/{num_points} points ({elapsed:.1f}s)")
            return True
            
        except Exception as e:
            print(f"\n❌ Erreur lors de l'exécution : {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_move(self, name, moves_dir='reachy_tictactoe/moves'):
        """
        Test un mouvement spécifique
        
        Args:
            name: Nom du mouvement (sans extension)
            moves_dir: Dossier contenant les mouvements
        """
        print("=" * 70)
        print(f"🧪 TEST DU MOUVEMENT : {name}")
        print("=" * 70)
        
        filepath = os.path.join(moves_dir, f'{name}.npz')
        
        if not os.path.exists(filepath):
            print(f"❌ Fichier non trouvé : {filepath}\n")
            return False
        
        # Charger le mouvement
        print(f"📂 Chargement depuis : {filepath}")
        move_data = self.load_move(filepath)
        
        if move_data is None:
            return False
        
        # Déterminer le type
        is_traj = self.is_trajectory(move_data)
        move_type = "trajectoire" if is_traj else "position simple"
        
        print(f"📊 Type : {move_type}")
        print(f"📊 Joints : {len(move_data)} joints")
        
        if is_traj:
            num_points = len(list(move_data.values())[0])
            duration = num_points * 0.01
            print(f"📊 Points : {num_points} ({duration:.2f}s)")
        
        print(f"\n📋 Joints concernés :")
        for joint_name in move_data.keys():
            print(f"  • {joint_name}")
        
        # Demander confirmation
        print("\n⚠️  Le bras va se déplacer !")
        confirm = input("   Continuer ? (o/n) : ")
        
        if confirm.lower() not in ['o', 'y', 'yes', 'oui']:
            print("❌ Test annulé\n")
            return False
        
        # Activer le bras
        print("\n🔌 Activation du bras droit...")
        self.reachy.turn_on('r_arm')
        time.sleep(0.5)
        
        # Jouer le mouvement
        print(f"▶️  Exécution du mouvement...")
        
        if is_traj:
            success = self.play_trajectory(move_data)
        else:
            success = self.play_position(move_data)
        
        if success:
            print("✅ Mouvement exécuté avec succès !")
        else:
            print("❌ Échec de l'exécution")
        
        print("=" * 70)
        print()
        
        return success
    
    def list_available_moves(self, moves_dir='reachy_tictactoe/moves'):
        """
        Liste tous les mouvements disponibles
        
        Args:
            moves_dir: Dossier contenant les mouvements
            
        Returns:
            list: Liste des noms de mouvements (sans extension)
        """
        pattern = os.path.join(moves_dir, '*.npz')
        files = glob.glob(pattern)
        
        moves = [
            os.path.splitext(os.path.basename(f))[0]
            for f in files
        ]
        
        return sorted(moves)
    
    def test_all_moves(self, moves_dir='reachy_tictactoe/moves'):
        """
        Test tous les mouvements disponibles
        
        Args:
            moves_dir: Dossier contenant les mouvements
        """
        moves = self.list_available_moves(moves_dir)
        
        if not moves:
            print(f"❌ Aucun mouvement trouvé dans {moves_dir}\n")
            return
        
        print("\n" + "=" * 70)
        print(f"🧪 TEST DE TOUS LES MOUVEMENTS ({len(moves)} mouvements)")
        print("=" * 70)
        
        print(f"\nMouvements à tester :")
        for i, move in enumerate(moves, 1):
            print(f"  {i:2d}. {move}")
        
        confirm = input(f"\n⚠️  Tester tous ces mouvements ? (o/n) : ")
        
        if confirm.lower() not in ['o', 'y', 'yes', 'oui']:
            print("❌ Tests annulés\n")
            return
        
        results = []
        
        for i, move in enumerate(moves, 1):
            print(f"\n\n{'=' * 70}")
            print(f"MOUVEMENT {i}/{len(moves)}")
            print('=' * 70)
            
            success = self.test_move(move, moves_dir)
            results.append((move, success))
            
            if i < len(moves):
                print("\n⏸️  Pause de 2 secondes avant le prochain mouvement...")
                time.sleep(2)
        
        # Résumé
        print("\n\n" + "=" * 70)
        print("📊 RÉSUMÉ DES TESTS")
        print("=" * 70)
        
        success_count = sum(1 for _, success in results if success)
        fail_count = len(results) - success_count
        
        print(f"\n✅ Réussis : {success_count}/{len(results)}")
        print(f"❌ Échoués : {fail_count}/{len(results)}")
        
        if fail_count > 0:
            print(f"\n❌ Mouvements en échec :")
            for move, success in results:
                if not success:
                    print(f"  • {move}")
        
        print("=" * 70)
        print()
    
    def interactive_mode(self, moves_dir='reachy_tictactoe/moves'):
        """Mode interactif"""
        moves = self.list_available_moves(moves_dir)
        
        print("\n" + "=" * 70)
        print("🎯 MODE INTERACTIF - TEST DES MOUVEMENTS")
        print("=" * 70)
        
        if not moves:
            print(f"❌ Aucun mouvement trouvé dans {moves_dir}\n")
            return
        
        while True:
            print(f"\n{'=' * 70}")
            print(f"Mouvements disponibles ({len(moves)}) :")
            print('=' * 70)
            
            for i, move in enumerate(moves, 1):
                print(f"  {i:2d}. {move}")
            
            print("\nCommandes :")
            print("  • Numéro : Tester un mouvement")
            print("  • 'all'  : Tester tous les mouvements")
            print("  • 'q'    : Quitter")
            
            choice = input("\n➡️  Votre choix : ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'all':
                self.test_all_moves(moves_dir)
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(moves):
                        self.test_move(moves[idx], moves_dir)
                    else:
                        print("❌ Numéro invalide")
                except ValueError:
                    print("❌ Entrée invalide")
    
    def close(self):
        """Ferme proprement la connexion"""
        print("\n🔒 Désactivation des moteurs...")
        self.reachy.turn_off_smoothly('reachy')
        print("✅ Terminé !\n")


def main():
    parser = argparse.ArgumentParser(
        description="Teste les mouvements enregistrés du robot Reachy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :

  # Tester un mouvement spécifique
  python scripts/moves/test_recorded_moves.py --name grab_1
  
  # Tester tous les mouvements
  python scripts/moves/test_recorded_moves.py --all
  
  # Mode interactif (recommandé)
  python scripts/moves/test_recorded_moves.py --interactive
  
  # Avec un autre robot
  python scripts/moves/test_recorded_moves.py --interactive --host 192.168.1.42
        """
    )
    
    parser.add_argument('--name', type=str, help='Nom du mouvement à tester')
    parser.add_argument('--all', action='store_true', help='Tester tous les mouvements')
    parser.add_argument('--interactive', action='store_true', help='Mode interactif')
    parser.add_argument('--host', type=str, default='localhost',
                       help='Adresse IP du robot (défaut: localhost)')
    parser.add_argument('--moves-dir', type=str, default='reachy_tictactoe/moves',
                       help='Dossier des mouvements (défaut: reachy_tictactoe/moves)')
    
    args = parser.parse_args()
    
    # Créer le testeur
    try:
        tester = MoveTester(host=args.host)
    except Exception as e:
        print(f"❌ Erreur de connexion au robot : {e}")
        print("   Vérifiez que le robot est allumé et accessible")
        return 1
    
    try:
        if args.interactive:
            tester.interactive_mode(args.moves_dir)
        elif args.all:
            tester.test_all_moves(args.moves_dir)
        elif args.name:
            success = tester.test_move(args.name, args.moves_dir)
            if not success:
                return 1
        else:
            print("❌ Erreur : utilisez --name, --all ou --interactive")
            parser.print_help()
            return 1
    
    finally:
        tester.close()
    
    return 0


if __name__ == '__main__':
    exit(main())

