#Para criar um teste novo seguir os passos abaixo:

1. Decidir a classificação do campo
Nome social é opcional no SI3 — o sistema salva sem ele. Logo: _verify_campo_opcional, não _verify_campo_obrigatorio. Se ficar vazio, o test avisa mas não para.


2. Adicionar o dado no config.yaml
Em dados_faker, acrescentar uma entrada com tipo: faker e gerador de nome (ou tipo: fixo se quiser valor controlado):
yamldados_faker:

  - campo: nome_social
    tipo: faker
    gerador: name


3. Adicionar a coordenada no config.yaml
Capturar com posicao_mouse.py o centro do campo Nome Social na tela do formulário e registrar em coordenadas:

yamlcoordenadas:
  campo_nome_social: { x: 0, y: 0 }  # capturar com posicao_mouse.py



4. Adicionar a região OCR no config.yaml
Calibrar com testar_regiao_ocr.py a região que cobre o campo Nome Social preenchido:

yamlregioes_ocr:
  campo_nome_social: { x1: 0, y1: 0, x2: 0, y2: 0 }  # bootstrap até calibrar


5. Criar o step no flow — entre CM04 e CM05
O step seria CM04b (ou renumerar para CM05 empurrando os demais). A lógica:
pythondef _step_cm04b_nome_social(self, ctx, dados, coords, observer=None):

    def fn():
        nome_social = self._dado(dados, 'nome_social', 'CM04b')
        x, y = self._coord(coords, 'campo_nome_social')
        pyautogui.click(x, y)
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'a')
        ctx.runner.type_text(nome_social)
        time.sleep(0.3)
        screenshot_path = ctx.runner.screenshot(
            f'{ctx.evidence_dir}CM04b_nome_social.png'
        )
        self._verify_campo_opcional(
            ctx, 'nome_social', 'CM04b',
            regiao_key='campo_nome_social',
            ocr_holder=step_result_holder
        )
        return screenshot_path
    return self._step('CM04b', 'preencher Nome Social', fn, observer, ctx=ctx)

    
6. Calibrar e validar
Rodar testar_regiao_ocr.py com a região do campo preenchido até o OCR ler o nome corretamente. Depois rodar o flow 3x para confirmar estabilidade.

Resumo dos artefatos que mudam:
ArtefatoO que mudaconfig.yamldados_faker + coordenadas + regioes_ocrcadastro_paciente_min_flow.pyNovo método _step_cm04b_nome_social + inserção no loop de execute()Nada maisBaseFlow, runner, observer — nenhum