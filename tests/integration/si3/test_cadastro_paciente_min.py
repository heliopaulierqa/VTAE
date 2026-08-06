def test_cadastro_paciente_min(si3):
    resultado = si3.executar("flows/si3/cadastro_min.yaml")
    assert resultado.success