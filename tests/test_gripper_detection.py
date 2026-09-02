"""Détection de la prise du cube, et prise systématique sur `grab_1`.

**Détection.** `play_pawn` alertait quand `present_load` tombait sous 80.
Les mesures sur le robot (2026-09-02) montrent que ce seuil ne discrimine
rien : la charge vaut 2 aussi bien pince vide que cube serré. La **position
de blocage**, elle, sépare franchement les deux cas :

- pince fermée à vide : **-7,7°** (3 mesures sur 3, cible `GRIPPER_CLOSED`
  = -6° jamais tout à fait atteinte) ;
- pince bloquée sur un cube : **-10,6° à -19,6°** (10 prises en partie).

Le seuil retenu, -9°, tombe dans l'intervalle vide avec ~1,3° de marge d'un
côté et ~1,6° de l'autre. Rappel de convention : plus négatif = plus ouvert.

**grab_1.** Il n'y a pas la place d'aligner cinq cubes à côté du plateau :
l'humain redépose un cube au même endroit à chaque tour, donc le robot doit
toujours saisir en `grab_1`.
"""
from unittest.mock import MagicMock

import numpy as np
import pytest

from reachy_tictactoe import config
from reachy_tictactoe.motors import is_holding_pawn, wait_until_settled
from reachy_tictactoe.tictactoe_playground import PawnNotGrabbed


EMPTY = np.zeros(9, dtype=np.uint8)


class TestDetectionDeLaPrise:

    # Positions mesurées sur le robot, pince bloquée par un cube.
    @pytest.mark.parametrize('position', [-10.6, -11.6, -16.0, -17.2, -19.6])
    def test_un_cube_bloque_la_pince_avant_la_fermeture_complete(self, position):
        assert is_holding_pawn(position)

    # Position mesurée pince vide (3 essais identiques), et la cible théorique.
    @pytest.mark.parametrize('position', [-7.7, -6.0, -5.0])
    def test_sans_cube_la_pince_se_ferme_presque_entierement(self, position):
        assert not is_holding_pawn(position)

    def test_le_seuil_est_entre_la_mesure_a_vide_et_la_plus_petite_prise(self):
        # Garde-fou : si quelqu'un déplace le seuil hors de cet intervalle,
        # la détection redevient inutilisable.
        assert (config.GRIPPER_SMALLEST_HOLD
                < config.GRIPPER_HOLDING_THRESHOLD
                < config.GRIPPER_EMPTY_POSITION)

    def test_la_mesure_a_vide_reste_coherente_avec_la_consigne_de_fermeture(self):
        """La position à vide vaut environ GRIPPER_CLOSED - 1,7°.

        Durcir GRIPPER_CLOSED sans remesurer ferait passer la fermeture à
        vide sous le seuil : la détection dirait « cube tenu » en toutes
        circonstances, sans que rien ne le signale.
        """
        ecart = config.GRIPPER_CLOSED - config.GRIPPER_EMPTY_POSITION

        assert 0 < ecart < 4, (
            'GRIPPER_CLOSED a bougé sans que GRIPPER_EMPTY_POSITION soit '
            'remesurée sur le robot'
        )

    def test_seuil_explicite_possible(self):
        # Utile pour recalibrer sans toucher au réglage global.
        assert is_holding_pawn(-8.0, threshold=-7.9)
        assert not is_holding_pawn(-8.0, threshold=-8.1)


class TestAttenteDeStabilisation:
    """Sans cube, la pince est ENCORE EN MOUVEMENT quand on la lisait.

    ``close_gripper`` laissait 0,3 s après un ``goto`` de 0,5 s pour
    parcourir 37° : mesuré à -12,0° en transit, alors que la pince finit à
    -7,7° une fois immobile. -12,0° passait pour « cube tenu » : la
    détection était donc toujours positive, y compris à vide (constaté sur
    le robot le 2026-09-02). Avec un cube la pince est bloquée, donc déjà
    stable — ces mesures-là étaient justes.
    """

    def test_attend_que_la_position_cesse_de_bouger(self):
        lectures = iter([-42.9, -30.0, -18.0, -12.0, -8.0, -7.7, -7.7, -7.7])

        position = wait_until_settled(lambda: next(lectures), period=0)

        assert position == pytest.approx(-7.7)

    def test_le_ralentissement_de_fin_de_course_ne_trompe_pas(self):
        """Cas réel : -9,1° a été pris pour une position finale.

        En fin de course le servo avance encore, mais lentement. Une seule
        comparaison sous tolérance suffisait à conclure — d'où une pince
        vide lue à -9,1° puis classée « cube tenu » (seuil -9).
        """
        lectures = iter([-9.5, -9.3, -9.1, -8.9, -8.4, -8.0, -7.8,
                         -7.7, -7.7, -7.7])

        position = wait_until_settled(lambda: next(lectures), period=0)

        assert position == pytest.approx(-7.7)
        assert not is_holding_pawn(position)

    def test_rend_la_main_des_que_la_pince_est_bloquee(self):
        """Cube saisi : la pince s'immobilise vite, on ne doit pas attendre."""
        appels = []

        def lire():
            appels.append(1)
            return -17.2

        position = wait_until_settled(lire, period=0)

        assert position == pytest.approx(-17.2)
        assert len(appels) <= 5, 'ne pas attendre inutilement sur une prise nette'

    def test_renonce_au_bout_du_temps_imparti(self):
        """Une pince qui vibre sans fin ne doit pas bloquer le jeu."""
        oscillation = iter([-10.0, -20.0] * 100)

        position = wait_until_settled(
            lambda: next(oscillation), period=0, timeout=0.0)

        assert position is not None

    def test_une_lecture_absente_n_arrete_pas_tout(self):
        lectures = iter([None, None, -7.7, -7.7, -7.7])

        position = wait_until_settled(lambda: next(lectures), period=0)

        assert position == pytest.approx(-7.7)


class TestPriseToujoursSurGrab1:

    def test_le_premier_pion_est_pris_en_grab_1(self, playground, monkeypatch):
        monkeypatch.setattr(playground, 'play_pawn', MagicMock())

        playground.play(4, EMPTY.copy())

        playground.play_pawn.assert_called_once_with(grab_index=1, box_index=5)

    def test_les_pions_suivants_aussi(self, playground, monkeypatch):
        """Sans place pour aligner 5 cubes, l'humain en redépose un en grab_1."""
        monkeypatch.setattr(playground, 'play_pawn', MagicMock())

        board = EMPTY.copy()
        for action in (0, 1, 2, 3):
            board = playground.play(action, board)

        assert playground.pawn_played == 4
        indices = [
            appel.kwargs['grab_index']
            for appel in playground.play_pawn.call_args_list
        ]
        assert indices == [1, 1, 1, 1], (
            'tous les cubes sont pris au même endroit (grab_1)'
        )


class TestPriseAVide:
    """L'humain redépose le cube à la main : l'oubli devient un cas COURANT.

    Sans traitement, la pince se ferme dans le vide, ``play()`` marque
    quand même la case, et la vision voit un plateau différent : le jeu
    accuse l'humain de tricher et annule la partie. Il faut donc réessayer,
    puis renoncer proprement sans corrompre le plateau.
    """

    @staticmethod
    def _simule_fermetures(playground, monkeypatch, positions):
        """close_gripper() renvoie tour à tour les positions données.

        La dernière valeur persiste si close_gripper est appelée davantage.
        Retourne le mock, pour compter les tentatives.
        """
        gripper = playground.reachy.r_arm.r_gripper
        gripper.present_load = 5.0
        gripper.present_position = positions[0]
        restantes = list(positions)

        def _fermer():
            position = restantes.pop(0) if len(restantes) > 1 else restantes[0]
            gripper.present_position = position
            return position

        mock = MagicMock(side_effect=_fermer)
        monkeypatch.setattr(playground, 'close_gripper', mock)
        monkeypatch.setattr(playground, 'play_trajectory', MagicMock())
        # Sans cela, chaque réessai attendrait vraiment 2 s : la suite doit
        # rester sous la seconde.
        monkeypatch.setattr(
            'reachy_tictactoe.tictactoe_playground.GRAB_RETRY_DELAY', 0)
        # L'alerte sonore du réessai passe par l'executor audio partagé :
        # sans ce stub, la suite joue vraiment du mpg123 et monopolise
        # l'unique worker, ce qui fait échouer les tests de sons.
        monkeypatch.setattr(
            'reachy_tictactoe.behavior.play_sound_background', MagicMock())
        return mock

    def test_une_prise_ratee_est_retentee_et_reussit(
            self, playground, monkeypatch):
        # 1re fermeture à vide (-7,7°), 2e bloquée par un cube (-16°)
        fermer = self._simule_fermetures(playground, monkeypatch, [-7.7, -16.0])

        playground.play_pawn(grab_index=1, box_index=5)

        assert fermer.call_count == 2, 'la prise doit être retentée une fois'

    def test_une_prise_reussie_du_premier_coup_ne_reessaye_pas(
            self, playground, monkeypatch):
        fermer = self._simule_fermetures(playground, monkeypatch, [-16.0])

        playground.play_pawn(grab_index=1, box_index=5)

        assert fermer.call_count == 1

    def test_renonce_apres_plusieurs_echecs(self, playground, monkeypatch):
        fermer = self._simule_fermetures(playground, monkeypatch, [-7.7])

        with pytest.raises(PawnNotGrabbed):
            playground.play_pawn(grab_index=1, box_index=5)

        assert fermer.call_count > 1, 'il faut avoir réessayé avant de renoncer'

    def test_le_plateau_n_est_pas_marque_si_le_cube_manque(
            self, playground, monkeypatch):
        """C'est ce qui déclenchait la fausse accusation de triche."""
        monkeypatch.setattr(
            playground, 'play_pawn',
            MagicMock(side_effect=PawnNotGrabbed('pince vide')))

        board = EMPTY.copy()
        with pytest.raises(PawnNotGrabbed):
            playground.play(4, board)

        assert np.all(board == 0), 'le plateau ne doit pas être modifié'
        assert playground.pawn_played == 0, 'le compteur ne doit pas avancer'
