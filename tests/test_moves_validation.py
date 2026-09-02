"""Validation des mouvements enregistrés (``reachy_tictactoe.moves_validation``).

Ces contrôles existent parce que deux sessions d'enregistrement entières ont
été perdues :

1. **Flux de positions gelé** (26/08) : le serveur renvoyait la même valeur
   en boucle ; 29 fichiers sur 36 étaient des copies figées, non détectables
   à l'œil — mais ``amplitude`` valait 0 et tous les fichiers étaient
   identiques entre eux.
2. **Dépassement des butées** : en mode compliant on pousse le bras au-delà
   des limites articulaires sans le sentir ; l'encodeur enregistre la vraie
   position, mais le contrôleur **écrête au rejeu** et la case est ratée.

La suite tourne sans robot : ce sont des fonctions numériques pures, plus un
filet de sécurité sur les vrais ``.npz`` du dépôt.
"""
import numpy as np
import pytest

from reachy_tictactoe.moves import moves
from reachy_tictactoe.moves_validation import (
    JOINT_LIMITS,
    amplitude,
    find_duplicates,
    is_frozen,
    limit_violations,
    unexpected_duplicates,
)


def _pose(**joints):
    """Pose 0-d (format goto_position)."""
    return {f'r_arm.{k}': np.array(float(v)) for k, v in joints.items()}


def _trajectoire(**joints):
    """Trajectoire 1-d (format play_trajectory)."""
    return {f'r_arm.{k}': np.asarray(v, dtype=float) for k, v in joints.items()}


# ---------------------------------------------------------------------------
# Limites articulaires
# ---------------------------------------------------------------------------

class TestLimitViolations:

    def test_une_pose_dans_les_limites_ne_remonte_rien(self):
        assert limit_violations(_pose(r_arm_yaw=45.0, r_elbow_pitch=-60.0)) == []

    def test_arm_yaw_au_dela_de_90_est_signale(self):
        """Le piège principal : le contrôleur écrête à 90° au rejeu."""
        violations = limit_violations(_pose(r_arm_yaw=107.5))

        assert len(violations) == 1
        joint, depassement = violations[0]
        assert joint == 'r_arm.r_arm_yaw'
        assert depassement == pytest.approx(17.5, abs=0.1)

    def test_le_depassement_est_detecte_dans_une_trajectoire(self):
        violations = limit_violations(
            _trajectoire(r_arm_yaw=[10.0, 50.0, 95.0, 60.0]))

        assert [j for j, _ in violations] == ['r_arm.r_arm_yaw']
        assert violations[0][1] == pytest.approx(5.0, abs=0.1)

    def test_le_depassement_par_le_bas_est_detecte(self):
        violations = limit_violations(_pose(r_elbow_pitch=-132.4))

        assert violations[0][0] == 'r_arm.r_elbow_pitch'
        assert violations[0][1] == pytest.approx(7.4, abs=0.1)

    def test_une_marge_de_tolerance_evite_les_faux_positifs(self):
        # 90,3° est dans le bruit de mesure : ne pas rejeter l'enregistrement.
        assert limit_violations(_pose(r_arm_yaw=90.3), margin=1.0) == []
        assert limit_violations(_pose(r_arm_yaw=90.3), margin=0.0) != []

    def test_un_joint_inconnu_est_ignore(self):
        assert limit_violations({'head.neck_roll': np.array(200.0)}) == []

    def test_les_limites_couvrent_tout_le_bras_droit(self):
        attendus = {
            'r_shoulder_pitch', 'r_shoulder_roll', 'r_arm_yaw', 'r_elbow_pitch',
            'r_forearm_yaw', 'r_wrist_pitch', 'r_wrist_roll', 'r_gripper',
        }
        assert {j.split('.')[-1] for j in JOINT_LIMITS} == attendus
        for lo, hi in JOINT_LIMITS.values():
            assert lo < hi


# ---------------------------------------------------------------------------
# Flux gelé / doublons (le désastre du 26 août)
# ---------------------------------------------------------------------------

class TestFluxGele:

    def test_une_trajectoire_immobile_est_detectee(self):
        fige = _trajectoire(r_arm_yaw=[42.0] * 300, r_elbow_pitch=[-60.0] * 300)

        assert is_frozen(fige)
        assert amplitude(fige) == pytest.approx(0.0)

    def test_un_vrai_geste_n_est_pas_signale(self):
        geste = _trajectoire(
            r_arm_yaw=np.linspace(10.0, 80.0, 300),
            r_elbow_pitch=np.linspace(-90.0, -60.0, 300),
        )

        assert not is_frozen(geste)
        assert amplitude(geste) == pytest.approx(70.0, abs=0.1)

    def test_le_bruit_de_mesure_seul_compte_comme_gele(self):
        # Un flux gelé n'est pas parfaitement constant : ±0,05° de bruit.
        rng = np.random.default_rng(0)
        presque_fige = _trajectoire(r_arm_yaw=42.0 + rng.normal(0, 0.05, 300))

        assert is_frozen(presque_fige)

    def test_une_pose_n_est_jamais_consideree_gelee(self):
        # Une pose 0-d est immobile par nature : le critère ne s'y applique pas.
        assert not is_frozen(_pose(r_arm_yaw=42.0))

    def test_les_fichiers_identiques_sont_regroupes(self):
        a = _trajectoire(r_arm_yaw=[1.0, 2.0, 3.0])
        catalogue = {
            'put_1': a,
            'put_2': _trajectoire(r_arm_yaw=[1.0, 2.0, 3.0]),
            'put_3': _trajectoire(r_arm_yaw=[9.0, 8.0, 7.0]),
        }

        groupes = find_duplicates(catalogue)

        assert groupes == [['put_1', 'put_2']]

    def test_aucun_doublon_ne_remonte_rien(self):
        catalogue = {
            'put_1': _trajectoire(r_arm_yaw=[1.0, 2.0]),
            'put_2': _trajectoire(r_arm_yaw=[3.0, 4.0]),
        }

        assert find_duplicates(catalogue) == []


class TestDoublonsAttendus:
    """``record_moves`` écrit put_N ET sa copie put_N_smooth_10_kp."""

    def test_la_copie_smooth_n_est_pas_signalee(self):
        geste = _trajectoire(r_arm_yaw=[1.0, 2.0, 3.0])
        catalogue = {'put_1': geste, 'put_1_smooth_10_kp': dict(geste)}

        assert find_duplicates(catalogue) == [['put_1', 'put_1_smooth_10_kp']]
        assert unexpected_duplicates(catalogue) == []

    def test_deux_deposes_differentes_identiques_restent_signalees(self):
        geste = _trajectoire(r_arm_yaw=[1.0, 2.0, 3.0])
        catalogue = {
            'put_1': geste,
            'put_1_smooth_10_kp': dict(geste),
            'put_2': dict(geste),
            'put_2_smooth_10_kp': dict(geste),
        }

        # put_1 et put_2 identiques = flux gelé : cela doit remonter.
        groupes = unexpected_duplicates(catalogue)

        assert len(groupes) == 1
        assert 'put_1' in groupes[0] and 'put_2' in groupes[0]


# ---------------------------------------------------------------------------
# Filet de sécurité sur les vrais mouvements du dépôt
# ---------------------------------------------------------------------------

class TestMouvementsDuDepot:
    """Ce que la session du 26 août aurait dû faire échouer immédiatement."""

    PUT_MOVES = [f'put_{i}_smooth_10_kp' for i in range(1, 10)]
    BACK_MOVES = [f'back_{i}_upright' for i in range(1, 10)]

    @pytest.mark.parametrize('name', PUT_MOVES + ['my-turn', 'your-turn',
                                                  'shuffle-board'])
    def test_aucune_trajectoire_du_depot_n_est_gelee(self, name):
        assert not is_frozen(dict(moves[name])), (
            f'{name}.npz est figé : flux de positions gelé à l\'enregistrement'
        )

    def test_les_neuf_deposes_sont_distinctes(self):
        catalogue = {n: dict(moves[n]) for n in self.PUT_MOVES}

        assert find_duplicates(catalogue) == [], (
            'des trajectoires de dépose sont identiques entre elles'
        )

    def test_les_neuf_retraits_sont_distincts(self):
        catalogue = {n: dict(moves[n]) for n in self.BACK_MOVES}

        assert find_duplicates(catalogue) == [], (
            'des poses de retrait sont identiques entre elles'
        )
