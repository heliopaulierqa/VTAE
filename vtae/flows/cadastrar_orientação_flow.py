
# vtae/flows/cadastro_orientação_flow.py
import time
import pyautogui

from vtae.core.context import FlowContext
from vtae.core.result import FlowResult, StepResult
from vtae.core.apex_helper import ApexHelper


class CadastrarOrientacao:
    """
    Fluxo de cadastro para cadastrar orientação no MSI3.
    Pressupõe que o login já foi executado via LoginFlowMsi3.

    Melhorias com ApexHelper:
        FA01/02/03 — aguardar_spinner após navegação (substitui sleep implícito)
        FA05       — aguardar_spinner substitui time.sleep(2) fixo
        FA08       — verificar_sem_erro após inserir
        FA09       — verificar_sucesso após confirmar + inspecionar_pagina no except
        FA10       — mantém OpenCV como validação primária (template visual
                     é mais confiável que seletor no modal do MSI3)

    Ordem de execução:
        FA01 → Sistema de Pacientes
        FA02 → Cadastros Básicos
        FA03 → Orientação (OpenCV)
        FA04 → Cadastrae Nova Orientação (OpenCV)
        FA05 → Preencher codigo da orientação
        FA06 → Preencher orientação
        FA07 → Clicar em Salvar        
        
    """

FLOW_NAME = "CadastrarOrientaca"

def execute(self, ctx: FlowContext, dados: dict, observer=None) -> FlowResult:

