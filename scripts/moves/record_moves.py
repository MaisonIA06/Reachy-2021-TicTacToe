#!/usr/bin/env python3
"""
Script pour enregistrer les mouvements du robot Reachy en mode compliant

Usage:
    # Enregistrer une position simple
    python scripts/moves/record_moves.py --name grab_1 --type position --host localhost
    
    # Enregistrer une trajectoire
    python scripts/moves/record_moves.py --name put_1 --type trajectory --host localhost --duration 3.0
"""

import argparse
import numpy as np
import time
import os
from reachy_sdk import ReachySDK


class MoveRecorder:
    """Enregistreur de mouvements pour Reachy"""
    
    def __init__(self, host='localhost', debug=False):
        """
        Initialise la connexion avec Reachy
        
        Args:
            host: Adresse IP du robot
            debug: Active le mode debug avec affichage détaillé
        """
        print(f"🔌 Connexion au robot Reachy ({host})...")
        self.reachy = ReachySDK(host=host)
        self.debug = debug
        
        # Liste des joints du bras droit à enregistrer
        self.right_arm_joints = [
            'r_shoulder_pitch',
            'r_shoulder_roll',
            'r_arm_yaw',
            'r_elbow_pitch',
            'r_forearm_yaw',
            'r_wrist_pitch',
            'r_wrist_roll',
            'r_gripper',
        ]
        
        print("✅ Connecté au robot\n")
        
    def get_current_positions(self, debug=False):
        """
        Récupère les positions actuelles de tous les joints du bras droit
        
        Args:
            debug: Si True, affiche les valeurs brutes pour diagnostic
            
        Returns:
            dict: {joint_name: position_in_degrees}
        """
        positions = {}
        
        for joint_name in self.right_arm_joints:
            joint = getattr(self.reachy.r_arm, joint_name)
            # Les valeurs de present_position sont déjà en degrés dans Reachy SDK
            position_in_degrees = joint.present_position
            
            if debug:
                print(f"  DEBUG {joint_name}: position={position_in_degrees:.2f}°")
            
            # Utiliser directement le format SDK 2021: r_arm.r_<joint_name>
            positions[f'r_arm.{joint_name}'] = position_in_degrees
            
        return positions
    
    def enable_compliant_mode(self):
        """Active le mode compliant sur le bras droit"""
        print("🔄 Initialisation des moteurs du bras droit...")
        # D'abord activer pour réinitialiser les encodeurs
        self.reachy.turn_on('r_arm')
        time.sleep(1.0)
        
        print("🔓 Passage en mode compliant...")
        self.reachy.turn_off('r_arm')
        time.sleep(0.5)
        print("✅ Mode compliant activé - Vous pouvez maintenant déplacer le bras manuellement\n")
        
    def disable_compliant_mode(self):
        """Désactive le mode compliant sur le bras droit"""
        print("\n🔒 Désactivation du mode compliant...")
        self.reachy.turn_on('r_arm')
        time.sleep(0.5)
        print("✅ Moteurs activés\n")
        
    def record_position(self, name, output_dir='reachy_tictactoe/moves'):
        """
        Enregistre une position simple
        
        Args:
            name: Nom du mouvement (sans extension)
            output_dir: Dossier de sortie
        """
        print("=" * 70)
        print(f"📍 ENREGISTREMENT DE POSITION : {name}")
        print("=" * 70)
        print("\n📋 Instructions :")
        print("  1. Déplacez manuellement le bras à la position souhaitée")
        print("  2. Appuyez sur ENTRÉE pour enregistrer")
        print("  3. Ou tapez 'q' pour annuler\n")
        
        self.enable_compliant_mode()
        
        while True:
            user_input = input("➡️  Appuyez sur ENTRÉE pour enregistrer (ou 'q' pour quitter) : ")
            
            if user_input.lower() == 'q':
                print("❌ Enregistrement annulé\n")
                return False
            
            # Enregistrer la position actuelle
            if self.debug:
                print("\n🔍 DEBUG MODE - Valeurs détaillées:")
            positions = self.get_current_positions(debug=self.debug)
            
            print("\n📊 Positions enregistrées :")
            for joint, pos in positions.items():
                print(f"  {joint:35s} = {pos:7.2f}°")
            
            # Demander confirmation
            confirm = input("\n✅ Sauvegarder cette position ? (o/n) : ")
            if confirm.lower() in ['o', 'y', 'yes', 'oui']:
                break
            else:
                print("↩️  Repositionnez le bras et réessayez\n")
        
        # Sauvegarder au format .npz
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f'{name}.npz')
        
        np.savez(filepath, **positions)
        
        print(f"\n💾 Position sauvegardée : {filepath}")
        print("=" * 70)
        print()
        
        return True
    
    def record_trajectory(self, name, duration=3.0, frequency=100, output_dir='reachy_tictactoe/moves'):
        """
        Enregistre une trajectoire (séquence de positions)
        
        Args:
            name: Nom du mouvement (sans extension)
            duration: Durée d'enregistrement en secondes
            frequency: Fréquence d'échantillonnage en Hz
            output_dir: Dossier de sortie
        """
        print("=" * 70)
        print(f"🎬 ENREGISTREMENT DE TRAJECTOIRE : {name}")
        print("=" * 70)
        print(f"\n📋 Instructions :")
        print(f"  1. Préparez le mouvement")
        print(f"  2. Appuyez sur ENTRÉE pour démarrer l'enregistrement")
        print(f"  3. Vous aurez {duration} secondes pour effectuer le mouvement")
        print(f"  4. Le bras sera enregistré à {frequency} Hz\n")
        
        self.enable_compliant_mode()
        
        while True:
            user_input = input("➡️  Appuyez sur ENTRÉE pour démarrer (ou 'q' pour quitter) : ")
            
            if user_input.lower() == 'q':
                print("❌ Enregistrement annulé\n")
                return False
            
            # Compte à rebours
            print("\n🎬 Démarrage dans...")
            for i in range(3, 0, -1):
                print(f"   {i}...")
                time.sleep(1)
            
            print("🔴 ENREGISTREMENT EN COURS !")
            print(f"   Effectuez le mouvement maintenant ({duration}s)...\n")
            
            # Enregistrer la trajectoire
            trajectory = {joint: [] for joint in self.get_current_positions(debug=False).keys()}
            
            start_time = time.time()
            sample_interval = 1.0 / frequency
            next_sample_time = start_time
            
            while time.time() - start_time < duration:
                current_time = time.time()
                
                if current_time >= next_sample_time:
                    positions = self.get_current_positions(debug=False)
                    
                    for joint, pos in positions.items():
                        trajectory[joint].append(pos)
                    
                    next_sample_time += sample_interval
                    
                    # Afficher la progression
                    elapsed = current_time - start_time
                    progress = int((elapsed / duration) * 40)
                    bar = "█" * progress + "░" * (40 - progress)
                    print(f"\r   [{bar}] {elapsed:.1f}s / {duration:.1f}s", end='', flush=True)
                
                time.sleep(0.001)  # Petite pause pour ne pas surcharger le CPU
            
            print("\n\n✅ Enregistrement terminé !")
            print(f"   {len(trajectory[list(trajectory.keys())[0]])} points enregistrés")
            
            # Demander confirmation
            confirm = input("\n✅ Sauvegarder cette trajectoire ? (o/n) : ")
            if confirm.lower() in ['o', 'y', 'yes', 'oui']:
                break
            else:
                print("↩️  Repositionnez et réessayez\n")
        
        # Convertir les listes en arrays numpy
        trajectory_arrays = {
            joint: np.array(positions) 
            for joint, positions in trajectory.items()
        }
        
        # Sauvegarder au format .npz
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, f'{name}.npz')
        
        np.savez(filepath, **trajectory_arrays)
        
        print(f"\n💾 Trajectoire sauvegardée : {filepath}")
        
        # Pour les mouvements "put", créer aussi la version smooth
        if name.startswith('put_') and not name.endswith('_smooth_10_kp'):
            smooth_name = f"{name}_smooth_10_kp"
            smooth_filepath = os.path.join(output_dir, f'{smooth_name}.npz')
            np.savez(smooth_filepath, **trajectory_arrays)
            print(f"💾 Version smooth sauvegardée : {smooth_filepath}")
        
        print("=" * 70)
        print()
        
        return True
    
    def display_menu(self):
        """Affiche le menu interactif"""
        print("\n" + "=" * 70)
        print("🎯 REENREGISTREMENT DES MOUVEMENTS TICTACTOE")
        print("=" * 70)
        print("\nMouvements à enregistrer :\n")
        
        print("📍 POSITIONS SIMPLES :")
        print("  • grab_1, grab_2, grab_3, grab_4, grab_5  (attraper les pions)")
        print("  • lift                                     (lever le pion)")
        print("  • back_1_upright à back_9_upright          (retour après dépôt)")
        print("  • back_to_back                             (transition)")
        print("  • back_rest                                (vers repos)")
        
        print("\n🎬 TRAJECTOIRES :")
        print("  • put_1 à put_9                            (placer dans case 1-9)")
        print("  • shuffle-board                            (mélanger le plateau)")
        print("  • my-turn                                  (animation)")
        print("  • your-turn                                (animation)")
        
        print("\n💡 NOTE : Les positions rest_pos et base_pos sont définies")
        print("           dans moves/__init__.py et peuvent être mises à jour manuellement")
        
        print("\n" + "=" * 70)
    
    def close(self):
        """Ferme proprement la connexion"""
        print("\n🔒 Désactivation des moteurs...")
        self.reachy.turn_off_smoothly('reachy')
        print("✅ Terminé !\n")


def main():
    parser = argparse.ArgumentParser(
        description="Enregistre les mouvements du robot Reachy en mode compliant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :

  # Enregistrer une position simple
  python scripts/moves/record_moves.py --name grab_1 --type position
  
  # Enregistrer une trajectoire de 3 secondes
  python scripts/moves/record_moves.py --name put_1 --type trajectory --duration 3.0
  
  # Enregistrer avec le robot sur une autre IP
  python scripts/moves/record_moves.py --name lift --type position --host 192.168.1.42
  
  # Mode interactif (menu)
  python scripts/moves/record_moves.py --interactive
        """
    )
    
    parser.add_argument('--name', type=str, help='Nom du mouvement à enregistrer')
    parser.add_argument('--type', choices=['position', 'trajectory'], 
                       help='Type de mouvement (position simple ou trajectoire)')
    parser.add_argument('--duration', type=float, default=3.0,
                       help='Durée pour les trajectoires (défaut: 3.0s)')
    parser.add_argument('--frequency', type=int, default=100,
                       help='Fréquence échantillonnage en Hz (défaut: 100)')
    parser.add_argument('--host', type=str, default='localhost',
                       help='Adresse IP du robot (défaut: localhost)')
    parser.add_argument('--output-dir', type=str, default='reachy_tictactoe/moves',
                       help='Dossier de sortie (défaut: reachy_tictactoe/moves)')
    parser.add_argument('--interactive', action='store_true',
                       help='Mode interactif avec menu')
    parser.add_argument('--debug', action='store_true',
                       help='Affiche les valeurs brutes pour diagnostic')
    
    args = parser.parse_args()
    
    # Créer l'enregistreur
    try:
        recorder = MoveRecorder(host=args.host, debug=args.debug)
        
        if args.debug:
            print("🔍 MODE DEBUG ACTIVÉ - Les valeurs brutes seront affichées\n")
    except Exception as e:
        print(f"❌ Erreur de connexion au robot : {e}")
        print("   Vérifiez que le robot est allumé et accessible")
        return 1
    
    try:
        if args.interactive:
            # Mode interactif
            recorder.display_menu()
            
            while True:
                print("\n" + "-" * 70)
                name = input("📝 Nom du mouvement (ou 'q' pour quitter) : ").strip()
                
                if name.lower() == 'q':
                    break
                
                if not name:
                    print("❌ Nom invalide")
                    continue
                
                move_type = input("📝 Type (position/trajectory) : ").strip().lower()
                
                if move_type not in ['position', 'trajectory']:
                    print("❌ Type invalide (utilisez 'position' ou 'trajectory')")
                    continue
                
                if move_type == 'position':
                    recorder.record_position(name, args.output_dir)
                else:
                    duration = float(input(f"📝 Durée en secondes (défaut: {args.duration}) : ") or args.duration)
                    recorder.record_trajectory(name, duration, args.frequency, args.output_dir)
        
        else:
            # Mode ligne de commande
            if not args.name or not args.type:
                print("❌ Erreur : --name et --type sont requis (ou utilisez --interactive)")
                parser.print_help()
                return 1
            
            if args.type == 'position':
                success = recorder.record_position(args.name, args.output_dir)
            else:
                success = recorder.record_trajectory(
                    args.name, 
                    args.duration, 
                    args.frequency, 
                    args.output_dir
                )
            
            if not success:
                return 1
    
    finally:
        recorder.close()
    
    return 0


if __name__ == '__main__':
    exit(main())

