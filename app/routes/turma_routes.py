from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity
from app.services import turma_service
from app.decorators.auth_decorators import admin_required
from bson import ObjectId, json_util
import json
import traceback
from app import mongo
from app.decorators.auth_decorators import admin_required, role_required

# Cria o Blueprint para as rotas de turma
turma_bp = Blueprint('turma_bp', __name__)

@turma_bp.before_request
def handle_turma_preflight():
    """
    Responde às requisições OPTIONS (CORS pre-flight) antes que elas
    cheguem aos decorators de autenticação, evitando o erro de JWT.
    """
    if request.method.upper() == 'OPTIONS':
        # O flask-cors adicionará os cabeçalhos corretos.
        # Nós apenas precisamos retornar uma resposta vazia e bem-sucedida.
        return '', 204


@turma_bp.route('/', methods=['POST'])
@admin_required()
def criar_nova_turma():
    """
    [ADMIN] Endpoint para criar uma nova turma.
    """
    dados = request.get_json()
    print(f"DEBUG: Dados recebidos para criar turma: {dados}")

    if not dados or not all(k in dados for k in ('nome', 'professor_id', 'esporte_id', 'categoria')):
        return jsonify({"mensagem": "Nome, professor_id, esporte_id e categoria são obrigatórios."}), 400
    
    try:
        turma_id = turma_service.criar_turma(dados)
        return jsonify({"mensagem": "Turma criada com sucesso!", "turma_id": str(turma_id)}), 201
    except Exception as e:
        print(f"!!!!!!!!!! ERRO AO CRIAR TURMA !!!!!!!!!!")
        print(e)
        traceback.print_exc()
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return jsonify({"mensagem": f"Erro interno no servidor: {e}"}), 500

@turma_bp.route('/', methods=['GET'])
@admin_required()
def obter_todas_turmas():
    """
    [ADMIN] Lista turmas. Suporta filtro por esporte_id e categoria.
    """
    filtros = {}
    esporte_id = request.args.get('esporte_id')
    categoria = request.args.get('categoria')

    if esporte_id:
        filtros['esporte_id'] = esporte_id
    if categoria:
        filtros['categoria'] = categoria

    if not filtros:
        turmas = turma_service.listar_turmas()
    else:
        turmas = turma_service.listar_turmas_filtradas(filtros)
        
    return json.loads(json_util.dumps(turmas)), 200

@turma_bp.route('/<string:turma_id>', methods=['GET'])
@admin_required()
def obter_turma_por_id(turma_id):
    """
    [ADMIN] Endpoint para obter detalhes de uma turma específica.
    """
    turma = turma_service.encontrar_turma_por_id(turma_id)
    if not turma:
        return jsonify({"mensagem": "Turma não encontrada."}), 404
    return json.loads(json_util.dumps(turma)), 200

@turma_bp.route('/<string:turma_id>', methods=['PUT'])
@admin_required()
def atualizar_turma_existente(turma_id):
    """
    [ADMIN] Endpoint para atualizar os dados de uma turma.
    """
    dados = request.get_json()
    try:
        modificados = turma_service.atualizar_turma(turma_id, dados)
        if modificados > 0:
            return jsonify({"mensagem": "Turma atualizada com sucesso."}), 200
        return jsonify({"mensagem": "Nenhuma alteração realizada ou turma não encontrada."}), 304
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

@turma_bp.route('/<string:turma_id>', methods=['DELETE'])
@admin_required()
def deletar_turma_existente(turma_id):
    deletados = turma_service.deletar_turma(turma_id)
    if deletados > 0:
        return '', 204
    return jsonify({"mensagem": "Turma não encontrada."}), 404

# --- Rotas específicas para gerenciar alunos em uma turma ---

@turma_bp.route('/<string:turma_id>/alunos', methods=['POST'])
@admin_required()
def adicionar_aluno_na_turma(turma_id):
    dados = request.get_json()
    if not dados or 'aluno_id' not in dados:
        return jsonify({"mensagem": "O campo aluno_id é obrigatório."}), 400
    try:
        modificados = turma_service.adicionar_aluno(turma_id, dados['aluno_id'])
        if modificados > 0:
            return jsonify({"mensagem": "Aluno adicionado com sucesso."}), 200
        return jsonify({"mensagem": "Aluno já pertence à turma ou turma não encontrada."}), 304
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 404

@turma_bp.route('/<string:turma_id>/alunos/<string:aluno_id>', methods=['DELETE'])
@admin_required()
def remover_aluno_da_turma(turma_id, aluno_id):
    modificados = turma_service.remover_aluno(turma_id, aluno_id)
    if modificados > 0:
        return jsonify({"mensagem": "Aluno removido com sucesso."}), 200
    return jsonify({"mensagem": "Aluno não encontrado na turma ou turma não encontrada."}), 404

@turma_bp.route('/professor/me', methods=['GET', 'OPTIONS'])
@role_required(roles=['professor', 'admin']) # Permite que admins também usem, se necessário
def get_minhas_turmas():
    """
    Retorna apenas as turmas associadas ao professor logado.
    """
    id_professor_logado = get_jwt_identity()
    turmas = turma_service.listar_turmas_por_professor(id_professor_logado)
    return json.loads(json_util.dumps(turmas)), 200