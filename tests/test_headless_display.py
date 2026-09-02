"""L'affichage OpenCV ne doit jamais faire échouer une partie.

``display_board`` ouvre une fenêtre highgui (``cv.imshow``). Depuis que
l'interface web joue les parties dans un thread de fond, cet appel casse
dans deux cas courants :

- **sans écran** (serveur lancé en SSH, opencv-headless) : ``cv2.error``
  « The function is not implemented » ;
- **hors thread principal** : highgui n'y est pas supporté.

Une fenêtre de confort ne doit pas interrompre la partie : l'affichage se
désactive tout seul au premier échec.
"""
from unittest.mock import MagicMock

import numpy as np
import pytest

from helpers import empty_board


class TestAffichageJamaisTente:
    """Qt ne lève pas d'exception : il ABORT le processus.

    Constaté en production le 2026-09-02 : une partie lancée depuis
    l'interface web a tué le serveur avec
    « qt.qpa.xcb: could not connect to display ». Un ``try/except`` autour
    de ``cv.imshow`` ne protège de rien — il faut ne pas l'appeler.
    """

    def test_pas_d_imshow_sans_variable_display(self, playground, monkeypatch):
        import reachy_tictactoe.tictactoe_playground as module

        faux_cv = MagicMock()
        monkeypatch.setattr(module, 'cv', faux_cv)
        monkeypatch.setattr(module.sys, 'platform', 'linux')
        monkeypatch.delenv('DISPLAY', raising=False)

        playground.display_board(empty_board())

        faux_cv.imshow.assert_not_called()

    def test_pas_d_imshow_hors_du_thread_principal(self, playground, monkeypatch):
        """highgui n'est pas supporté hors thread principal ; or l'interface
        web joue les parties dans un thread de fond."""
        import threading

        import reachy_tictactoe.tictactoe_playground as module

        faux_cv = MagicMock()
        monkeypatch.setattr(module, 'cv', faux_cv)
        monkeypatch.setenv('DISPLAY', ':0')

        erreurs = []

        def dans_un_thread():
            try:
                playground.display_board(empty_board())
            except Exception as e:  # pragma: no cover
                erreurs.append(e)

        t = threading.Thread(target=dans_un_thread)
        t.start()
        t.join(timeout=5)

        assert not erreurs
        faux_cv.imshow.assert_not_called()

    def test_affichage_desactivable_par_variable_d_environnement(
            self, playground, monkeypatch):
        import reachy_tictactoe.tictactoe_playground as module

        faux_cv = MagicMock()
        monkeypatch.setattr(module, 'cv', faux_cv)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.setenv('REACHY_TTT_NO_DISPLAY', '1')

        playground.display_board(empty_board())

        faux_cv.imshow.assert_not_called()

    def test_imshow_est_appele_quand_tout_va_bien(self, playground, monkeypatch):
        import reachy_tictactoe.tictactoe_playground as module

        faux_cv = MagicMock()
        monkeypatch.setattr(module, 'cv', faux_cv)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.delenv('REACHY_TTT_NO_DISPLAY', raising=False)

        playground.display_board(empty_board())

        assert faux_cv.imshow.called


class TestAffichageDefaillant:

    @pytest.fixture
    def cv_qui_echoue(self, monkeypatch):
        """Écran disponible, mais imshow lève une exception Python."""
        import reachy_tictactoe.tictactoe_playground as module

        faux_cv = MagicMock()
        faux_cv.imshow.side_effect = RuntimeError('highgui indisponible')
        monkeypatch.setattr(module, 'cv', faux_cv)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.delenv('REACHY_TTT_NO_DISPLAY', raising=False)
        return faux_cv

    def test_une_erreur_d_affichage_n_interrompt_pas_la_partie(
            self, playground, cv_qui_echoue):
        # Ne doit pas lever.
        playground.display_board(empty_board(), current_player='robot')

    def test_l_affichage_ne_reessaie_pas_indefiniment(
            self, playground, cv_qui_echoue):
        """La boucle appelle display_board plusieurs fois par seconde :
        réessayer à chaque fois inonderait les logs."""
        for _ in range(5):
            playground.display_board(empty_board())

        assert cv_qui_echoue.imshow.call_count == 1, (
            'l\'affichage doit se désactiver après le premier échec'
        )


class TestParcoursDesCases:

    @pytest.fixture
    def prepare(self, playground, monkeypatch):
        monkeypatch.setattr(playground, 'play_trajectory', MagicMock())
        monkeypatch.setattr(playground, 'goto_position', MagicMock())
        monkeypatch.setattr(playground, 'goto_rest_position', MagicMock())
        monkeypatch.setattr(playground, 'goto_base_position', MagicMock())
        monkeypatch.setattr(playground, 'safe_turn_on', MagicMock())
        return playground

    def test_le_bras_est_alimente_avant_de_parcourir(self, prepare):
        """Après rest(), le bras est compliant : sans couple, il ne bouge pas."""
        prepare.run_moves_check()

        prepare.safe_turn_on.assert_any_call('r_arm')

    def test_le_parcours_passe_par_la_position_de_base(self, prepare):
        """play_pawn passe toujours par la base : ce chemin-là est éprouvé,
        aller directement de rest_pos à grab_1 ne l'est pas."""
        prepare.run_moves_check()

        assert prepare.goto_base_position.called

    def test_les_neuf_cases_sont_parcourues(self, prepare):
        vues = []
        prepare.run_moves_check(on_progress=lambda case, total: vues.append(case))

        assert vues == list(range(1, 10))

    def test_le_bras_est_repose_meme_en_cas_d_echec(self, prepare, monkeypatch):
        monkeypatch.setattr(prepare, 'play_trajectory',
                            MagicMock(side_effect=RuntimeError('butée')))

        with pytest.raises(RuntimeError):
            prepare.run_moves_check()

        prepare.goto_rest_position.assert_called_once()
        prepare.reachy.turn_off_smoothly.assert_called_once_with('reachy')
