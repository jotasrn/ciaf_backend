from flask import Blueprint, request, jsonify
from app.services import turma_service
from app.decorators.auth_decorators import admin_required
from bson import json_util # Para serializar corretamente a saída do MongoDB

# Cria o Blueprint para as rotas de turma
turma_bp = Blueprint('turma_bp', __name__)

def bson_response(data, status_code=200):
    """
    Cria uma resposta Flask a partir de dados que podem conter tipos BSON (como ObjectId),
    convertendo-os para JSON padrão.
    """
    # json_util.dumps converte BSON para uma string JSON
    # json_util.loads converte a string JSON de volta para objetos Python (dicts, lists)
    # jsonify então cria a resposta HTTP final
    return jsonify(json_util.loads(json_util.dumps(data))), status_code

@turma_bp.route('/', methods=['POST'])
@admin_required()
def criar_nova_turma():
    """
    [ADMIN] Endpoint para criar uma nova turma.
    Exige nome, ID do professor e ID do esporte.
    """
    dados = request.get_json()
    # Validação atualizada para incluir o esporte_id como obrigatório
    if not dados or not all(k in dados for k in ('nome', 'professor_id', 'esporte_id')):
        return jsonify({"mensagem": "Os campos nome, professor_id e esporte_id são obrigatórios."}), 400
    
    try:
        turma_id = turma_service.criar_turma(dados)
        return jsonify({"mensagem": "Turma criada com sucesso!", "turma_id": turma_id}), 201
    except ValueError as e:
        # Erros de validação do service (ex: ID não encontrado)
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        # Outros erros inesperados
        return jsonify({"mensagem": "Erro interno no servidor.", "detalhes": str(e)}), 500

@turma_bp.route('/', methods=['GET'])
@admin_required()
def obter_todas_turmas():
    """
    [ADMIN] Endpoint para listar todas as turmas com dados populados.
    """
    turmas = turma_service.listar_turmas()
    return bson_response(turmas)

@turma_bp.route('/<string:turma_id>', methods=['GET'])
@admin_required()
def obter_turma_por_id(turma_id):
    """
    [ADMIN] Endpoint para obter detalhes de uma turma específica.
    """
    turma = turma_service.encontrar_turma_por_id(turma_id)
    if not turma:
        return jsonify({"mensagem": "Turma não encontrada."}), 404
    return bson_response(turma)

@turma_bp.route('/<string:turma_id>', methods=['PUT'])
@admin_required()
def atualizar_turma_existente(turma_id):
    """
    [ADMIN] Endpoint para atualizar os dados de uma turma.
    """
    dados = request.get_json()
    if not dados:
        return jsonify({"mensagem": "Corpo da requisição não pode ser vazio."}), 400
        
    try:
        modificados = turma_service.atualizar_turma(turma_id, dados)
        if modificados > 0:
            return jsonify({"mensagem": "Turma atualizada com sucesso."}), 200
        else:
            # Se nada foi modificado, pode ser porque os dados são os mesmos ou a turma não foi encontrada.
            return jsonify({"mensagem": "Nenhuma alteração realizada ou turma não encontrada."}), 304 # Not Modified
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

@turma_bp.route('/<string:turma_id>', methods=['DELETE'])
@admin_required()
def deletar_turma_existente(turma_id):
    """
    [ADMIN] Endpoint para deletar uma turma.
    """
    deletados = turma_service.deletar_turma(turma_id)
    if deletados > 0:
        return '', 204 # No Content, indica sucesso na exclusão
    else:
        return jsonify({"mensagem": "Turma não encontrada."}), 404

# --- Rotas específicas para gerenciar alunos em uma turma ---

@turma_bp.route('/<string:turma_id>/alunos', methods=['POST'])
@admin_required()
def adicionar_aluno_na_turma(turma_id):
    """
    [ADMIN] Endpoint para adicionar um aluno a uma turma.
    """
    dados = request.get_json()
    if not dados or 'aluno_id' not in dados:
        return jsonify({"mensagem": "O campo aluno_id é obrigatório."}), 400
    try:
        modificados = turma_service.adicionar_aluno(turma_id, dados['aluno_id'])
        if modificados > 0:
            return jsonify({"mensagem": "Aluno adicionado com sucesso."}), 200
        else:
            return jsonify({"mensagem": "Aluno já pertence à turma ou turma não encontrada."}), 304 # Not Modified
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 404 # Not Found (se o aluno não existir)

@turma_bp.route('/<string:turma_id>/alunos/<string:aluno_id>', methods=['DELETE'])
@admin_required()
def remover_aluno_da_turma(turma_id, aluno_id):
    """
    [ADMIN] Endpoint para remover um aluno de uma turma.
    """
    modificados = turma_service.remover_aluno(turma_id, aluno_id)
    if modificados > 0:
        return jsonify({"mensagem": "Aluno removido com sucesso."}), 200
    else:
        return jsonify({"mensagem": "Aluno não encontrado na turma ou turma não encontrada."}), 404
