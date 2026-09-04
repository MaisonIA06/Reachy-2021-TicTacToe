"""Détection d'un contrôleur moteur planté.

Panne vécue le 2026-09-04 : ``ros2_control_node`` tué par un recalage NTP
au démarrage. Le SDK répondait, la caméra fonctionnait, les positions se
lisaient — mais elles étaient figées et aucune consigne n'aboutissait.

⚠️ **Piste abandonnée, et pourquoi.** On a d'abord voulu déduire la panne
de l'immobilité des positions : pendant l'incident la variation était de
0,00° sur les 8 joints, contre ~0,09° en fonctionnement. Mesure faite
ensuite sur le robot : ces 0,09° ne sont PAS du bruit mais **un seul pas
d'encodeur** (2 valeurs distinctes sur 400 lectures, écart 0,0900 ≈
360/4096). Un bras immobile peut donc rester sur un pas unique et
afficher 0,00° — la détection aurait crié à la panne sans raison.

On vérifie donc directement ce qui échoue : la présence du processus.
"""
import pytest

from reachy_tictactoe.webapp.health import MotorHealth, controller_alive


@pytest.fixture
def faux_proc(tmp_path):
    """Construit une arborescence /proc factice."""
    def creer(*cmdlines):
        for i, cmd in enumerate(cmdlines, start=100):
            d = tmp_path / str(i)
            d.mkdir()
            (d / 'cmdline').write_bytes(cmd.encode() + b'\x00')
        # Bruit : entrées non numériques, comme dans un vrai /proc
        (tmp_path / 'meminfo').write_text('...')
        return tmp_path
    return creer


class TestPresenceDuControleur:

    def test_controleur_present(self, faux_proc):
        racine = faux_proc(
            '/usr/bin/python3\x00autre',
            '/opt/ros/humble/lib/controller_manager/ros2_control_node\x00--ros-args')

        assert controller_alive(proc_root=racine) is True

    def test_controleur_absent(self, faux_proc):
        """C'est exactement l'état constaté pendant la panne."""
        racine = faux_proc('/usr/bin/python3\x00camera_server',
                           '/usr/bin/bash\x00launch.bash')

        assert controller_alive(proc_root=racine) is False

    def test_un_proc_illisible_ne_fait_pas_echouer(self, faux_proc, tmp_path):
        """Les processus meurent pendant qu'on parcourt /proc."""
        racine = faux_proc('/bin/sh')
        (racine / '999').mkdir()          # dossier sans cmdline lisible

        assert controller_alive(proc_root=racine) is False

    def test_proc_inexistant_leve_pour_etre_traite_plus_haut(self):
        with pytest.raises(OSError):
            controller_alive(proc_root='/chemin/qui/nexiste/pas')


class TestMoniteur:

    def test_verdict_ok_quand_le_controleur_tourne(self, faux_proc):
        racine = faux_proc('.../ros2_control_node\x00--ros-args')

        assert MotorHealth(proc_root=racine).status == 'ok'

    def test_verdict_frozen_quand_il_a_disparu(self, faux_proc):
        racine = faux_proc('/usr/bin/python3\x00camera_server')

        assert MotorHealth(proc_root=racine).status == 'frozen'

    def test_pas_de_verdict_pour_un_robot_distant(self, faux_proc):
        """Lire /proc n'a de sens que si l'on tourne SUR le robot :
        sinon on observerait les processus du mauvais ordinateur."""
        racine = faux_proc('/usr/bin/python3')

        moniteur = MotorHealth(proc_root=racine, local=False)

        assert moniteur.status == 'unknown'

    def test_une_erreur_de_lecture_donne_inconnu_pas_une_alerte(self):
        """Mieux vaut se taire qu'annoncer une panne inexistante."""
        moniteur = MotorHealth(proc_root='/chemin/absent')

        assert moniteur.status == 'unknown'

    def test_la_premiere_mesure_a_lieu_meme_au_demarrage(self, faux_proc,
                                                         monkeypatch):
        """Régression : ``time.monotonic()`` compte depuis le démarrage de
        la machine. Avec un horodatage initial à 0, sur un système démarré
        depuis moins que la durée du cache, l'écart paraissait inférieur au
        cache et la première mesure n'avait jamais lieu — le verdict
        restait 'unknown'. Invisible sur une machine allumée depuis des
        heures ; c'est le CI, sur un runner neuf, qui l'a révélé.
        """
        from reachy_tictactoe.webapp import health

        # Machine démarrée il y a 12 secondes.
        monkeypatch.setattr(health.time, 'monotonic', lambda: 12.0)
        racine = faux_proc('.../ros2_control_node')

        assert MotorHealth(proc_root=racine, cache_seconds=60).status == 'ok'

    def test_le_verdict_est_mis_en_cache(self, faux_proc):
        """Parcourir /proc à chaque requête HTTP serait du gaspillage :
        le flux d'état interroge plusieurs fois par seconde."""
        racine = faux_proc('.../ros2_control_node')
        moniteur = MotorHealth(proc_root=racine, cache_seconds=60)

        assert moniteur.status == 'ok'
        # Le contrôleur disparaît, mais le cache n'a pas expiré.
        (racine / '100').rename(racine / 'disparu')
        assert moniteur.status == 'ok'

    def test_le_cache_expire(self, faux_proc):
        racine = faux_proc('.../ros2_control_node')
        moniteur = MotorHealth(proc_root=racine, cache_seconds=0)

        assert moniteur.status == 'ok'
        (racine / '100').rename(racine / 'disparu')
        assert moniteur.status == 'frozen'
