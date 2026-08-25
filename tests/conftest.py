"""Socle de tests : stubs des dépendances matérielles.

Les tests tournent sans robot ni accélérateur : on injecte dans
``sys.modules`` des faux modules pour ``reachy_sdk`` (le robot),
``tflite_runtime`` (l'inférence), ``sklearn`` (détection de grille,
inutilisée dans les tests) et ``zzlog`` (logging du launcher),
AVANT tout import de ``reachy_tictactoe``.

L'injection est inconditionnelle : même si les vrais modules sont
installés (cas du NUC du robot), la suite ne doit JAMAIS ouvrir de
connexion gRPC vers un robot.

Les fichiers ``.npz`` (mouvements, Q-table) du dépôt sont réellement
chargés par les tests. Les modèles ``.tflite`` en revanche ne sont
vérifiés qu'en PRÉSENCE (le stub n'ouvre pas le fichier) — leur format
reste validé sur le robot uniquement.
"""
import sys
import types
from unittest.mock import MagicMock

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Stub reachy_sdk (le robot)
# ---------------------------------------------------------------------------

reachy_sdk = types.ModuleType('reachy_sdk')
reachy_sdk.ReachySDK = MagicMock(name='ReachySDK')

trajectory = types.ModuleType('reachy_sdk.trajectory')
trajectory.goto = MagicMock(name='goto')

interpolation = types.ModuleType('reachy_sdk.trajectory.interpolation')


class _FakeInterpolationMode:
    MINIMUM_JERK = 'minimum_jerk'
    LINEAR = 'linear'


interpolation.InterpolationMode = _FakeInterpolationMode
reachy_sdk.trajectory = trajectory
trajectory.interpolation = interpolation

sys.modules['reachy_sdk'] = reachy_sdk
sys.modules['reachy_sdk.trajectory'] = trajectory
sys.modules['reachy_sdk.trajectory.interpolation'] = interpolation


# ---------------------------------------------------------------------------
# Stub tflite_runtime (inférence CPU)
# ---------------------------------------------------------------------------

class _FakeInterpreter:
    """Imite l'API tflite.Interpreter utilisée par TFLiteClassifier.

    Reproduit le contrat des VRAIS modèles du dépôt : entrée float32
    normalisée (x - 127.5) / 127.5, sortie softmax float32 dans [0, 1]
    (voir scripts/training/convert_to_tflite.py — modèles non quantifiés).
    """

    def __init__(self, model_path=None):
        self.model_path = model_path

    def allocate_tensors(self):
        pass

    def get_input_details(self):
        return [{'shape': np.array([1, 224, 224, 3]),
                 'dtype': np.float32, 'index': 0}]

    def get_output_details(self):
        return [{'index': 0}]

    def set_tensor(self, index, data):
        self._input = data

    def invoke(self):
        pass

    def get_tensor(self, index):
        # Sortie neutre : classe 0 ("vide") avec un score plausible.
        return np.array([[0.9, 0.05, 0.05]], dtype=np.float32)


tflite_runtime = types.ModuleType('tflite_runtime')
tflite_interpreter = types.ModuleType('tflite_runtime.interpreter')
tflite_interpreter.Interpreter = _FakeInterpreter
tflite_runtime.interpreter = tflite_interpreter

sys.modules['tflite_runtime'] = tflite_runtime
sys.modules['tflite_runtime.interpreter'] = tflite_interpreter


# ---------------------------------------------------------------------------
# Stubs sklearn (detect_board) et zzlog (game_launcher)
# ---------------------------------------------------------------------------

sklearn = types.ModuleType('sklearn')
sklearn_cluster = types.ModuleType('sklearn.cluster')
sklearn_cluster.KMeans = MagicMock(name='KMeans')
sklearn.cluster = sklearn_cluster

sys.modules['sklearn'] = sklearn
sys.modules['sklearn.cluster'] = sklearn_cluster

zzlog = types.ModuleType('zzlog')
zzlog.setup = MagicMock(name='zzlog.setup')
sys.modules['zzlog'] = zzlog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_hardware_mocks():
    """Isole chaque test : robot et historique d'appels repartent de zéro."""
    reachy_sdk.ReachySDK.reset_mock(return_value=True, side_effect=True)
    trajectory.goto.reset_mock(return_value=True, side_effect=True)
    yield


@pytest.fixture
def playground():
    """TictactoePlayground branché sur un robot factice (MagicMock)."""
    from reachy_tictactoe import TictactoePlayground
    return TictactoePlayground(host='fake-robot')
