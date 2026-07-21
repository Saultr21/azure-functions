import pytest
from pydantic import ValidationError

from models import CampanaId, RegistroCliente


def test_campana_id_acepta_solo_valores_conocidos():
    assert CampanaId("3M") == CampanaId.TRES_MESES
    with pytest.raises(ValueError):
        CampanaId("no-existe")


def test_registro_cliente_requiere_matricula():
    with pytest.raises(ValidationError):
        RegistroCliente(matricula="", descripcion="NMAX", municipio="telde")
