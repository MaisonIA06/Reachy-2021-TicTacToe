"""Supervision des ventilateurs par TOUS les moteurs de chaque zone.

⚠️ Pourquoi ce module existe (2026-09-29). Le contrôleur de ventilateurs
de Pollen (``fans_controller``, dans ``reachy_sdk_server``) allume un
ventilateur quand *son* moteur atteint 45 °C et l'éteint sous 43 °C. Mais
il ne surveille que les moteurs ``*_pitch`` et les antennes — littéralement
``motor.split('_pitch')``. ``wrist_roll`` et les pinces, les deux moteurs
qui travaillent le plus au TicTacToe (la pince serre le cube à couple
maximal pendant tout le transport, le roulis porte la dépose), ne sont
**jamais** ventilés : le poignet droit à 48 °C, ventilateur éteint, a été
constaté sur le robot. Les ventilateurs eux-mêmes fonctionnent — vérifié à
la main en forçant ``r_wrist_fan`` par le SDK.

On ne modifie pas le code de Pollen. On pilote les mêmes ventilateurs
depuis le jeu, avec les mêmes seuils, mais en regardant le moteur le plus
chaud de la zone. Les deux logiques cohabitent sans conflit :

- Pollen n'**éteint** que ce que *lui* a allumé (il garde son propre état
  en mémoire) : un ventilateur allumé par nous reste allumé pour lui.
- S'il éteint un ventilateur qu'il avait allumé alors que notre zone est
  encore chaude, le tick suivant le **rallume** — la consigne est
  réaffirmée à chaque passage, pas seulement sur transition.
- Nous n'éteignons que ce que **nous** avons allumé, et nous le faisons à
  l'arrêt (``release``) : Pollen croit ces ventilateurs éteints et ne les
  éteindrait jamais — ils tourneraient jusqu'au redémarrage du robot.

Les antennes sont volontairement absentes : Pollen les surveille bien.
"""
import logging
import math
import threading

from .config import FAN_OFF_TEMPERATURE, FAN_ON_TEMPERATURE

logger = logging.getLogger('reachy.tictactoe')

#: ventilateur → moteurs de sa zone (tous, pas seulement le *_pitch).
FAN_ZONES = {
    'r_shoulder_fan': ['r_shoulder_pitch', 'r_shoulder_roll', 'r_arm_yaw'],
    'r_elbow_fan': ['r_elbow_pitch', 'r_forearm_yaw'],
    'r_wrist_fan': ['r_wrist_pitch', 'r_wrist_roll', 'r_gripper'],
    'l_shoulder_fan': ['l_shoulder_pitch', 'l_shoulder_roll', 'l_arm_yaw'],
    'l_elbow_fan': ['l_elbow_pitch', 'l_forearm_yaw'],
    'l_wrist_fan': ['l_wrist_pitch', 'l_wrist_roll', 'l_gripper'],
}

#: Période du fil de supervision. Les températures sont des attributs mis
#: à jour par le flux du SDK (lecture locale, gratuite). ⚠️ En revanche
#: ``Fan.is_on`` est un appel gRPC ``GetFansState`` **sans délai maximal**
#: (reachy-sdk 0.7.0), comme ``on()`` / ``off()`` : on ne lit l'état que
#: pour une zone chaude, et ``states()`` sert un cache — jamais six
#: allers-retours par relevé de températures.
DEFAULT_PERIOD = 5.0


class FanSupervisor:
    """Allume un ventilateur dès qu'UN moteur de sa zone dépasse le seuil.

    Args:
        fans: objet exposant un attribut par ventilateur (``reachy.fans``),
            chacun avec ``is_on``, ``on()``, ``off()``.
        read_temperatures: fonction renvoyant ``{joint: °C ou None}``.
        zones: ventilateur → moteurs surveillés.
        on_temperature / off_temperature: hystérésis, celle de Pollen.
    """

    def __init__(self, fans, read_temperatures, zones=None,
                 on_temperature=FAN_ON_TEMPERATURE,
                 off_temperature=FAN_OFF_TEMPERATURE):
        self._fans = fans
        self._read = read_temperatures
        self._zones = dict(FAN_ZONES if zones is None else zones)
        self._on = on_temperature
        self._off = off_temperature
        self._owned = set()
        # Dernier état connu par ventilateur, alimenté par les ticks :
        # ``states()`` répond sans appel réseau.
        self._etats = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    # -- une passe ----------------------------------------------------------

    def tick(self):
        """Une décision par zone. Ne lève jamais.

        Returns:
            dict: ventilateur → 'on' / 'off' pour ceux qu'on a commandés.
        """
        try:
            temperatures = self._read()
        except Exception as erreur:
            logger.warning(f'Ventilateurs : températures illisibles ({erreur})')
            return {}

        decisions = {}
        for fan_name, joints in self._zones.items():
            fan = getattr(self._fans, fan_name, None)
            if fan is None:
                continue
            valeurs = [temperatures.get(j) for j in joints]
            valeurs = [v for v in valeurs
                       if isinstance(v, (int, float)) and math.isfinite(v)]
            if not valeurs:
                continue
            maximum = max(valeurs)

            try:
                with self._lock:
                    if maximum >= self._on:
                        # Lecture réseau, mais seulement pour une zone
                        # chaude. Réaffirmé à chaque tick : Pollen a pu
                        # l'éteindre parce que SON moteur est repassé sous
                        # 43 °C.
                        allume = bool(fan.is_on)
                        if not allume:
                            fan.on()
                            allume = True
                            # ⚠️ À nous SEULEMENT si c'est nous qui l'avons
                            # allumé. Un ventilateur déjà allumé est à
                            # Pollen : le relâcher à l'arrêt le couperait
                            # alors que Pollen le croit encore en marche.
                            self._owned.add(fan_name)
                            logger.info(f'Ventilateur {fan_name} allumé '
                                        f'(zone à {maximum:.0f} °C)')
                            decisions[fan_name] = 'on'
                        self._etats[fan_name] = allume
                    elif maximum < self._off and fan_name in self._owned:
                        fan.off()
                        self._owned.discard(fan_name)
                        self._etats[fan_name] = False
                        logger.info(f'Ventilateur {fan_name} éteint '
                                    f'(zone à {maximum:.0f} °C)')
                        decisions[fan_name] = 'off'
            except Exception as erreur:
                # Une zone en erreur ne doit pas priver les autres.
                logger.warning(f'Ventilateur {fan_name} : {erreur}')
        return decisions

    def states(self):
        """``{ventilateur: bool}`` — dernier état connu, SANS appel réseau.

        Un ventilateur jamais lu (zone restée froide) est donné éteint :
        s'il tourne, c'est Pollen qui l'a allumé, et ce n'est pas à nous
        de le dire.
        """
        return {fan_name: bool(self._etats.get(fan_name, False))
                for fan_name in self._zones
                if getattr(self._fans, fan_name, None) is not None}

    def release(self, timeout=2.0):
        """Éteint ce que NOUS avons allumé. À appeler à l'arrêt.

        ⚠️ Verrou borné : un tick figé dans un appel gRPC sans délai le
        garderait pour toujours. Mieux vaut renoncer à éteindre nos
        ventilateurs que d'empêcher ce qui suit — la coupure du couple.
        """
        if not self._lock.acquire(timeout=timeout):
            logger.warning('Ventilateurs : supervision figée, relâchement abandonné')
            return
        try:
            for fan_name in list(self._owned):
                fan = getattr(self._fans, fan_name, None)
                try:
                    if fan is not None:
                        fan.off()
                        self._etats[fan_name] = False
                except Exception as erreur:
                    logger.warning(f'Ventilateur {fan_name} : {erreur}')
            self._owned.clear()
        finally:
            self._lock.release()

    # -- fil de fond --------------------------------------------------------

    def start(self, period=DEFAULT_PERIOD):
        """Lance la supervision en tâche de fond (démon)."""
        self._stop.clear()

        def boucle():
            while True:
                self.tick()
                if self._stop.wait(period):
                    return

        self._thread = threading.Thread(target=boucle, name='fan-supervisor',
                                        daemon=True)
        self._thread.start()
        return self._thread

    def stop(self, timeout=5.0):
        """Arrête le fil et relâche les ventilateurs allumés par nous."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        self.release()
