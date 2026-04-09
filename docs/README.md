# Testes de Integração

Estes testes requerem uma tela real e o sistema alvo em execução.

## Como rodar

```bash
pytest vtae/tests/integration/ -v
```

## Pré-requisitos

- Sistema SisLab acessível
- Runner real configurado (não mock)
- Variáveis de ambiente: `VTAE_USER`, `VTAE_PASSWORD`

## Estrutura esperada

```
integration/
├── test_login_real.py       ← login real no sistema
├── test_admissao_real.py    ← fluxo real de admissão
└── test_suprimentos_real.py ← fluxo real de suprimentos
```
