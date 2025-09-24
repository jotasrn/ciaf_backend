import io
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment
from flask import render_template
from weasyprint import HTML
from app.services import aula_service

def _ajustar_largura_colunas(sheet):
    """
    Função utilitária para ajustar a largura das colunas de uma planilha
    com base no conteúdo da célula mais longa.
    """
    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

def gerar_planilha_presenca_aula(aula_id):
    """
    Gera uma planilha Excel (.xlsx) da lista de presença de uma aula com dados completos.
    """
    # 1. Usa a função de busca de dados robusta que já implementamos
    dados_aula = aula_service.buscar_detalhes_aula(aula_id)
    if not dados_aula:
        return None, None

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Lista de Presença"

    # 3. Adiciona um cabeçalho informativo completo ao relatório
    sheet['A1'] = 'Relatório de Presença'
    sheet['A1'].font = Font(bold=True, size=16)
    
    sheet['A3'] = 'Turma:'
    sheet['B3'] = dados_aula.get('turma_nome', 'N/A')
    sheet['A4'] = 'Data da Aula:'
    sheet['B4'] = dados_aula.get('data').strftime('%d/%m/%Y') if dados_aula.get('data') else 'N/A'
    sheet['A5'] = 'Esporte:'
    sheet['B5'] = dados_aula.get('esporte', 'N/A')
    sheet['A6'] = 'Categoria:'
    sheet['B6'] = dados_aula.get('categoria', 'N/A')
    sheet['A7'] = 'Professor:'
    sheet['B7'] = dados_aula.get('professor', 'N/A')

    for cell_coord in ['A3', 'A4', 'A5', 'A6', 'A7']:
        sheet[cell_coord].font = Font(bold=True)

    # 4. Adiciona os cabeçalhos da tabela de dados
    sheet.append([]) # Linha em branco para espaçamento
    headers = ['Nome do Aluno', 'Status da Presença', 'Observação']
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
    for aluno in sorted(alunos, key=lambda x: x.get('nome_completo', '')):
        status = aluno.get('presenca', {}).get('status', 'pendente')
        observacao = aluno.get('presenca', {}).get('observacao', '') or ''
        
        row = [
            aluno.get('nome_completo', 'N/A'),
            status_map.get(status, status),
            observacao
        ]
        sheet.append(row)

    # 6. Estilo final
    _ajustar_largura_colunas(sheet)

    # 7. Salva o arquivo em memória
    file_stream = io.BytesIO()
    workbook.save(file_stream)
    file_stream.seek(0)

    nome_turma_safe = "".join(c for c in dados_aula.get('turma_nome', 'Turma') if c.isalnum() or c in (' ', '-')).rstrip()
    data_safe = dados_aula.get('data').strftime('%Y-%m-%d') if dados_aula.get('data') else ''
    nome_arquivo = f"Presenca_{nome_turma_safe}_{data_safe}.xlsx"

    return file_stream, nome_arquivo

def gerar_pdf_presenca_aula(aula_id):
    """
    Gera um relatório PDF da lista de presença de uma aula.
    """
    # 1. Usa a mesma função de busca de dados robusta
    dados_aula = aula_service.buscar_detalhes_aula(aula_id)
    if not dados_aula:
        return None, None
        
    # 2. Renderiza o template HTML (ele já espera os dados completos)
    html_renderizado = render_template(
        'relatorios/relatorio_presenca.html',
        dados=dados_aula,
        data_geracao=datetime.datetime.now()
    )

    # 3. Converte para PDF
    pdf_bytes = HTML(string=html_renderizado).write_pdf()
    file_stream = io.BytesIO(pdf_bytes)

    # 4. Gera o nome do arquivo
    nome_turma_safe = "".join(c for c in dados_aula.get('turma_nome', 'Turma') if c.isalnum() or c in (' ', '-')).rstrip()
    data_safe = dados_aula.get('data').strftime('%Y-%m-%d') if dados_aula.get('data') else ''
    nome_arquivo = f"Presenca_{nome_turma_safe}_{data_safe}.pdf"

    return file_stream, nome_arquivo