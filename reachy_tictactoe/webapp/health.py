"""Surveillance du contrôleur moteur.

Panne vécue le 2026-09-04 : ``ros2_control_node`` (le nœud qui parle aux
moteurs) tué au démarrage par un recalage NTP. Le SDK répondait, la
caméra fonctionnait, les positions se lisaient — mais elles étaient
figées et aucune consigne n'aboutissait. Rien ne le signalait ; il a
fallu lire les journaux systemd.

⚠️ **Piste abandonnée, à ne pas refaire.** On a d'abord voulu déduire la
panne de l'immobilité des positions : pendant l'incident la variation
valait 0,00° sur les 8 joints, contre ~0,09° en marche normale. Mesure
faite ensuite sur le robot : ces 0,09° ne sont pas du bruit mais **un
seul pas d'encodeur** — 2 valeurs distinctes sur 400 lectures, écart
0,0900 ≈ 360/4096 sur les Dynamixel MX. Un bras immobile peut donc rester
sur un pas unique et afficher 0,00° : la détection aurait annoncé une
panne inexistante, éventuellement devant du public.

On vérifie donc **la présence du processus**, c'est-à-dire exactement ce
qui échoue. C'est déterministe, et le coût est négligeable (un parcours
de ``/proc`` toutes les quelques secondes, mis en cache).
"""
import logging
import os
import time

logger = logging.getLogger('reachy.tictactoe.webapp')

#: Motif cherché dans les lignes de commande de /proc.
CONTROLLER_PATTERN = 'ros2_control_node'


def controller_alive(proc_root='/proc', pattern=CONTROLLER_PATTERN):
    """Le nœud qui pilote les moteurs tourne-t-il ?

    Args:
        proc_root: racine de /proc (paramétrable pour les tests).
        pattern: motif cherché dans ``/proc/<pid>/cmdline``.

    Returns:
        True si un processus correspond.

    Raises:
        OSError: si ``proc_root`` est illisible — au niveau supérieur de
            décider si cela vaut 'unknown'.
    """
    for entree in os.listdir(proc_root):
        if not entree.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, entree, 'cmdline'), 'rb') as f:
                ligne = f.read().decode('utf-8', 'replace')
        except OSError:
            # Le processus a disparu pendant le parcours : cas normal.
            continue
        if pattern in ligne:
            return True
    return False


class MotorHealth:
    """Verdict sur l'état du contrôleur moteur, mis en cache.

    Args:
        proc_root: racine de /proc.
        local: le serveur tourne-t-il SUR le robot ? Lire /proc n'a de
            sens que dans ce cas ; piloter un robot distant observerait
            les processus du mauvais ordinateur.
        cache_seconds: durée de validité du verdict. Le flux d'état
            interroge plusieurs fois par seconde : sans cache, on
            parcourrait /proc pour rien.
    """

    def __init__(self, proc_root='/proc', local=True, cache_seconds=5.0):
        self._proc_root = proc_root
        self._local = local
        self._cache_seconds = cache_seconds
        self._verdict = 'unknown'
        self._mesure_a = 0.0

    @property
    def status(self):
        """'ok', 'frozen' (contrôleur absent) ou 'unknown'."""
        if not self._local:
            return 'unknown'

        maintenant = time.monotonic()
        if maintenant - self._mesure_a < self._cache_seconds:
            return self._verdict

        try:
            vivant = controller_alive(self._proc_root)
        except OSError as e:
            # Mieux vaut se taire qu'annoncer une panne inexistante.
            logger.debug(f'Surveillance du contrôleur indisponible : {e}')
            self._verdict = 'unknown'
        else:
            nouveau = 'ok' if vivant else 'frozen'
            if nouveau != self._verdict and nouveau == 'frozen':
                logger.error(
                    'Contrôleur moteur absent : le robot ne répondra plus '
                    'aux consignes (voir CLAUDE.md).')
            self._verdict = nouveau

        self._mesure_a = maintenant
        return self._verdict
