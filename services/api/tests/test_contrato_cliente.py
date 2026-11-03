"""Contrato versionado em packages/api-client/ em dia com o app.main (issue #68, ADR 0004 item 6).

Se algum teste daqui falhar, o schema ou a resposta mudou sem regerar. Para regerar:
    uv run python services/api/scripts/exportar_openapi.py && (cd packages/api-client && npm run gerar)
"""

import importlib.util
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location("exportar_openapi", RAIZ / "services/api/scripts/exportar_openapi.py")
exportar = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(exportar)

COMANDO = exportar.COMANDO


def _msg(o_que: str) -> str:
    return f"{o_que} desatualizado em relação ao app.main. Regere com: {COMANDO}"


def test_openapi_json_em_dia():
    assert exportar.OPENAPI.read_text(encoding="utf-8") == exportar.texto_openapi(), _msg("packages/api-client/openapi.json")


def test_exemplo_de_contrato_em_dia():
    assert exportar.EXEMPLO.read_text(encoding="utf-8") == exportar.texto_exemplo(), _msg(
        "packages/api-client/exemplos/evolucao-tiros-1km.json"
    )


def test_tipos_gerados_do_openapi_atual():
    """`schema.d.ts` leva o sha256 do openapi.json de onde saiu (carimbo do `npm run gerar`)."""
    primeira = exportar.TIPOS.read_text(encoding="utf-8").splitlines()[0]
    m = re.fullmatch(r"// openapi-sha256: ([0-9a-f]{64})", primeira)
    assert m, _msg("packages/api-client/src/schema.d.ts (sem carimbo)")
    assert m.group(1) == exportar.hash_openapi(exportar.texto_openapi()), _msg("packages/api-client/src/schema.d.ts")


def test_exemplo_so_tem_dado_das_fixtures():
    import json

    j = json.loads(exportar.EXEMPLO.read_text(encoding="utf-8"))
    assert j["atleta_id"] == 1 and [s["data"] for s in j["sessoes"]] == ["2025-03-04", "2025-03-11"]
    assert "Ficticio" not in exportar.EXEMPLO.read_text(encoding="utf-8")  # nem o nome do atleta vai no JSON
