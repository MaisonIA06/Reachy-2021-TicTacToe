#!/usr/bin/env python3
"""
Script de diagnostic pour tester la lecture des positions des joints
"""
from reachy_sdk import ReachySDK
import time
import argparse

from reachy_tictactoe.motors import safe_turn_on

def test_joint_positions(host='localhost'):
    """Test de lecture des positions avec diagnostic détaillé"""
    print("🔌 Connexion à Reachy...")
    reachy = ReachySDK(host=host)
    print("✅ Connecté")
    print("ℹ️  Note: Reachy SDK retourne les positions directement en degrés\n")
    
    try:
        # Activer puis désactiver pour mode compliant
        print("🔄 Initialisation des moteurs (sans à-coup)...")
        safe_turn_on(reachy, 'r_arm')
        time.sleep(1.0)
        
        print("🔓 Passage en mode compliant...")
        reachy.turn_off('r_arm')
        time.sleep(0.5)
        print("✅ Mode compliant activé\n")
        
        print("=" * 70)
        print("📊 TEST DE LECTURE DES POSITIONS")
        print("=" * 70)
        print("\nDéplacez légèrement le bras et observez les valeurs...")
        input("Appuyez sur ENTRÉE pour commencer les mesures...")
        
        # Lire les positions
        joints_to_test = [
            'r_shoulder_pitch',
            'r_shoulder_roll',
            'r_arm_yaw',
            'r_elbow_pitch',
            'r_forearm_yaw',
            'r_wrist_pitch',
            'r_wrist_roll',
            'r_gripper'
        ]
        
        print("\n" + "=" * 70)
        for joint_name in joints_to_test:
            joint = getattr(reachy.r_arm, joint_name)
            # Les valeurs sont déjà en degrés dans Reachy SDK
            position_deg = joint.present_position
            
            print(f"\n{joint_name}:")
            print(f"  Position actuelle     : {position_deg:.2f}°")
            
            # Diagnostic
            if abs(position_deg) > 360:
                print(f"  ⚠️  ATTENTION: Valeur > 360° (encodeur multi-tours)")
            elif abs(position_deg) > 180:
                print(f"  ⚠️  Valeur hors plage standard [-180, 180]°")
            else:
                print(f"  ✅ Valeur dans la plage normale")
        
        print("\n" + "=" * 70)
        print("\n💡 ANALYSE:")
        print("  ✅ Les valeurs de present_position sont DÉJÀ en degrés")
        print("  ✅ Aucune conversion nécessaire (pas de rad2deg)")
        print("  ✅ Ces valeurs peuvent être utilisées directement pour l'enregistrement")
        print("\n  Note: Reachy SDK retourne directement les positions en degrés")
        
    finally:
        print("\n🔒 Désactivation des moteurs...")
        reachy.turn_off_smoothly('reachy')
        print("✅ Terminé!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test de diagnostic des positions')
    parser.add_argument('--host', default='localhost', help='Adresse IP de Reachy')
    args = parser.parse_args()
    
    test_joint_positions(args.host)

