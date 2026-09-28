"""Tension de la batterie, relevée à la demande.

La sécurité batterie de Pollen (``zuuu_hal.check_battery``, dans le HAL de
la base mobile) freine les roues sous 23,1 V et prévient sous 24,5 V —
mais **uniquement dans le journal système**. Le tableau de bord Pollen qui
affichait la tension est désactivé : personne ne verrait l'alerte avant
que les roues ne se bloquent. Ce module expose la tension à l'interface,
avec les **mêmes seuils** que Pollen.

⚠️ **Lecture ponctuelle et découplée.** On n'ouvre pas la base mobile dans
le ``ReachySDK`` du jeu (``with_mobile_base=True``) : le service de la base
mobile peut être arrêté depuis le panneau Options, et le jeu ne doit pas
en dépendre. On ouvre un canal gRPC le temps d'un appel, **avec délai
maximal**, puis on le referme — un relevé toutes les 30 s pendant des
heures ne doit fuir aucune connexion.
"""
import logging
import math

from ..config import BATTERY_MIN_VOLTAGE, BATTERY_WARN_VOLTAGE

logger = logging.getLogger('reachy.tictactoe.webapp')

#: Port gRPC du serveur SDK de la base mobile (``mobile_base_sdk_server``).
MOBILE_BASE_PORT = 50061

#: Délai maximal d'un relevé. Sans lui, une base mobile qui ne répond pas
#: figerait la requête HTTP, et l'interface avec.
CALL_TIMEOUT = 2.0


class BatteryUnavailable(RuntimeError):
    """La base mobile ne répond pas — typiquement, son service est arrêté."""


def verdict(voltage):
    """'ok', 'low', 'critical' ou 'unknown', selon les seuils de Pollen.

    Comparaisons **strictes**, comme dans ``zuuu_hal.check_battery`` :
    ``voltage < min`` freine, ``voltage < warn`` prévient. À exactement
    24,5 V le HAL de Pollen dit encore « OK » — nous aussi, pour ne jamais
    afficher une alerte que la sécurité elle-même ne déclencherait pas.

    ⚠️ Toute valeur non finie est 'unknown' : ``NaN < seuil`` vaut False
    et ferait passer une batterie muette pour une batterie pleine.
    """
    if (voltage is None or not isinstance(voltage, (int, float))
            or not math.isfinite(voltage)):
        return 'unknown'
    if voltage < BATTERY_MIN_VOLTAGE:
        return 'critical'
    if voltage < BATTERY_WARN_VOLTAGE:
        return 'low'
    return 'ok'


def _open_stub(host, port):
    """Canal gRPC vers la base mobile.

    Renvoie ``(stub, requete_vide, fermer)``. Tout ce qui touche au SDK est
    importé ICI et non en tête de module : ``grpc``, ``reachy_sdk_api`` et
    ``protobuf`` n'existent que sur le robot, et l'interface doit rester
    importable (et testable) sans eux. Regrouper les trois imports au même
    endroit garantit qu'une dépendance manquante échoue de la même façon
    explicite, quelle qu'elle soit.
    """
    import grpc
    from google.protobuf.empty_pb2 import Empty
    from reachy_sdk_api import mobile_platform_reachy_pb2_grpc as mobile_grpc

    channel = grpc.insecure_channel(f'{host}:{port}')
    return mobile_grpc.MobilityServiceStub(channel), Empty(), channel.close


def read_voltage(host, port=MOBILE_BASE_PORT, timeout=CALL_TIMEOUT):
    """Tension de la batterie en volts, arrondie au dixième.

    Raises:
        BatteryUnavailable: base mobile injoignable, muette, ou SDK absent
            de ce poste — toujours une indisponibilité explicite, jamais
            une exception brute qui ferait répondre 500 à l'API.
    """
    fermer = None
    try:
        stub, requete, fermer = _open_stub(host, port)
        reponse = stub.GetBatteryLevel(requete, timeout=timeout)
        return round(float(reponse.level.value), 1)
    except Exception as erreur:
        raise BatteryUnavailable(str(erreur)) from erreur
    finally:
        if fermer is not None:
            fermer()
