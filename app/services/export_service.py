import io
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment
from flask import render_template
from weasyprint import HTML

# Importamos os outros services dos quais este depende para buscar dados
from app.services import aula_service
from app.services import turma_service # Usado como fallback caso 'professor' não venha nos dados da aula


def _ajustar_largura_colunas(sheet):
    """
    Função utilitária para ajustar a largura das colunas de uma planilha
    com base no conteúdo da célula mais longa.
    """
    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter # Pega a letra da coluna (A, B, C...)
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        # Adiciona um pouco de espaço extra para não ficar muito apertado
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width


def gerar_planilha_presenca_aula(aula_id):
    """
    Gera uma planilha Excel (.xlsx) da lista de presença de uma aula.
    Retorna um stream de bytes em memória e o nome do arquivo sugerido.
    """
    # 1. Reutilizamos nosso service para buscar todos os dados necessários de uma vez
    dados_aula = aula_service.buscar_detalhes_aula(aula_id)
    if not dados_aula:
        return None, None

    # 2. Criação da planilha em memória
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Lista de Presença"

    # 3. Adiciona um cabeçalho informativo ao relatório
    sheet['A1'] = 'Relatório de Presença'
    sheet['A1'].font = Font(bold=True, size=16)
    
    sheet['A3'] = 'Turma:'
    sheet['B3'] = dados_aula.get('turma_nome', 'N/A')
    sheet['A4'] = 'Data da Aula:'
    sheet['B4'] = dados_aula.get('data').strftime('%d/%m/%Y') if dados_aula.get('data') else 'N/A'
    sheet['A3'].font = Font(bold=True)
    sheet['A4'].font = Font(bold=True)

    # 4. Adiciona os cabeçalhos da tabela de dados
    headers = ['Nome do Aluno', 'Status da Presença', 'Observação']
    sheet.append([]) # Adiciona uma linha em branco para espaçamento
    sheet.append(headers)
    header_row = sheet.max_row
    for cell in sheet[header_row]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')

    # 5. Preenche os dados dos alunos
    status_map = {
        'presente': 'Presente',
        'ausente': 'Ausente',
        'justificado': 'Justificado',
        'pendente': 'Pendente'
    }
    
    alunos = dados_aula.get('alunos', [])
    # Ordena a lista de alunos por nome para um relatório mais organizado
    for aluno in sorted(alunos, key=lambda x: x['nome_completo']):
        status = aluno.get('presenca', {}).get('status', 'pendente')
        observacao = aluno.get('presenca', {}).get('observacao', '') or ''
        
        row = [
            aluno.get('nome_completo', 'N/A'),
            status_map.get(status, status),
            observacao
        ]
        sheet.append(row)

    # 6. Aplica estilo final, como o ajuste de colunas
    _ajustar_largura_colunas(sheet)

    # 7. Salva o arquivo em um stream de bytes na memória
    file_stream = io.BytesIO()
    workbook.save(file_stream)
    file_stream.seek(0) # Essencial: move o cursor para o início do stream para a leitura

    # 8. Gera um nome de arquivo dinâmico e seguro
    nome_turma_safe = "".join(c for c in dados_aula.get('turma_nome', 'Turma') if c.isalnum() or c in (' ', '-')).rstrip()
    data_safe = dados_aula.get('data').strftime('%Y-%m-%d')
    nome_arquivo = f"Presenca_{nome_turma_safe}_{data_safe}.xlsx"

    return file_stream, nome_arquivo


def gerar_pdf_presenca_aula(aula_id):
    """
    Gera um relatório PDF da lista de presença de uma aula.
    Retorna um stream de bytes em memória e o nome do arquivo sugerido.
    """
    # 1. Reutilizamos o mesmo service para buscar os dados
    dados_aula = aula_service.buscar_detalhes_aula(aula_id)
    if not dados_aula:
        return None, None
        
    # O pipeline de agregação já nos traz o professor, mas garantimos aqui
    if 'professor' not in dados_aula:
        turma_completa = turma_service.encontrar_turma_por_id(dados_aula['turma_id'])
        dados_aula['professor'] = turma_completa.get('professor', {}) if turma_completa else {}

    # 2. Renderiza o template HTML com os dados
    html_renderizado = render_template(
        'relatorios/relatorio_presenca.html',
        dados=dados_aula,
        data_geracao=datetime.datetime.now()
    )

    # 3. Converte o HTML para PDF em memória usando WeasyPrint
    pdf_bytes = HTML(string=html_renderizado).write_pdf()
    file_stream = io.BytesIO(pdf_bytes)

    # 4. Gera um nome de arquivo dinâmico e seguro
    nome_turma_safe = "".join(c for c in dados_aula.get('turma_nome', 'Turma') if c.isalnum() or c in (' ', '-')).rstrip()
    data_safe = dados_aula.get('data').strftime('%Y-%m-%d')
    nome_arquivo = f"Presenca_{nome_turma_safe}_{data_safe}.pdf"

    return file_stream, nome_arquivo