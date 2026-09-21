"""Le JavaScript de la page doit au moins être syntaxiquement valide.

⚠️ Leçon du 2026-09-21. Deux erreurs de syntaxe ont été introduites d'un
coup dans le script en ligne de ``index.html`` : une fin de ligne réelle
au milieu d'une chaîne, et une apostrophe non échappée. La page contient
**un seul** bloc ``<script>`` : une erreur de syntaxe n'en casse pas une
partie, elle rend TOUT inerte — plus de SSE, plus de boutons, plus de
caméra, et surtout plus de « Réparer ». La page s'affiche pourtant
normalement, ce qui rend la panne particulièrement trompeuse.

Rien dans la suite ne lisait ce fichier. Ce test comble ce trou.
"""
import os
import re
import shutil
import subprocess

import pytest


RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(RACINE, 'reachy_tictactoe', 'webapp', 'static',
                    'index.html')


def _scripts_en_ligne():
    with open(PAGE, encoding='utf-8') as f:
        html = f.read()
    return re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',
                      html, re.DOTALL)


def _node():
    """Chemin de node, ou None.

    ⚠️ En intégration continue, son absence est une ERREUR et non une
    raison de sauter : un test silencieusement sauté ne protège de rien —
    c'est exactement ainsi que toute la suite web est restée ignorée
    pendant des mois.
    """
    chemin = shutil.which('node')
    if chemin is None and os.environ.get('CI'):
        pytest.fail("node est requis en CI pour vérifier le JavaScript "
                    'de la page')
    return chemin


def test_la_page_contient_bien_un_script():
    """Garde-fou du garde-fou : si l'extraction cassait, le test suivant
    passerait en ne vérifiant rien du tout."""
    scripts = _scripts_en_ligne()
    assert scripts, 'aucun script en ligne trouvé dans index.html'
    assert any('applyControls' in s for s in scripts), (
        "l'extraction ne retrouve pas le script principal"
    )


def test_le_javascript_de_la_page_est_syntaxiquement_valide(tmp_path):
    node = _node()
    if node is None:
        pytest.skip('node absent (vérification faite en CI)')

    for numero, script in enumerate(_scripts_en_ligne()):
        fichier = tmp_path / f'script_{numero}.js'
        fichier.write_text(script, encoding='utf-8')

        resultat = subprocess.run([node, '--check', str(fichier)],
                                  capture_output=True, text=True, timeout=30)

        assert resultat.returncode == 0, (
            f'Erreur de syntaxe dans le script en ligne n°{numero} '
            f"d'index.html — la page entière serait inerte :\n"
            f'{resultat.stderr}'
        )
