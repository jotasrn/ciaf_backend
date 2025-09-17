from flask import Blueprint, request, jsonify
from app.services import esporte_service
from app.decorators.auth_decorators import admin_required, role_required
from bson import json_util
import json

# Cria o Blueprint para as rotas de esporte
esporte_bp = Blueprint('esporte_bp', __name__)

@esporte_bp.before_request
def handle_esporte_preflight():
    """
    Responde às requisições OPTIONS (CORS pre-flight) antes que elas
    cheguem aos decorators, evitando erros de autenticação.
    """
    if request.method.upper() == 'OPTIONS':
        return '', 204
    
@esporte_bp.before_request
def handle_esporte_preflight():
    if request.method.upper() == 'OPTIONS':
        return '', 204

def bson_response(data, status_code=200):
    """
    Cria uma resposta Flask a partir de dados que podem conter tipos BSON,
    convertendo-os para JSON padrão.
    """
    return jsonify(json_util.loads(json_util.dumps(data))), status_code

@esporte_bp.route('/', methods=['POST'])
@admin_required()
def criar_novo_esporte():
    """
    [ADMIN] Endpoint para criar um novo esporte.
    """
    dados = request.get_json()
    if not dados or 'nome' not in dados or not dados['nome'].strip():
        return jsonify({"mensagem": "O campo 'nome' é obrigatório e não pode ser vazio."}), 400
    
    try:
        esporte_id = esporte_service.criar_esporte(dados)
        return jsonify({"mensagem": "Esporte criado com sucesso!", "esporte_id": esporte_id}), 201
    except ValueError as e:
        # Erro de nome duplicado vindo do service
        return jsonify({"mensagem": str(e)}), 409 # Conflict

@esporte_bp.route('/', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def obter_todos_esportes():
    """
    [ADMIN, PROFESSOR] Endpoint para listar todos os esportes.
    """
    esportes = esporte_service.listar_esportes()
    return bson_response(esportes)

@esporte_bp.route('/<string:esporte_id>', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def obter_esporte_por_id(esporte_id):
    """
    [ADMIN, PROFESSOR] Endpoint para obter detalhes de um esporte específico.
    """
    esporte = esporte_service.encontrar_esporte_por_id(esporte_id)
    if not esporte:
        return jsonify({"mensagem": "Esporte não encontrado."}), 404
    return bson_response(esporte)

@esporte_bp.route('/<string:esporte_id>', methods=['PUT'])
@admin_required()
def atualizar_esporte_existente(esporte_id):
    """
    [ADMIN] Endpoint para atualizar os dados de um esporte.
    """
    dados = request.get_json()
    if not dados:
        return jsonify({"mensagem": "Corpo da requisição não pode ser vazio."}), 400

    try:
        modificados = esporte_service.atualizar_esporte(esporte_id, dados)
        if modificados > 0:
            return jsonify({"mensagem": "Esporte atualizado com sucesso."}), 200
        else:
            return jsonify({"mensagem": "Nenhuma alteração realizada ou esporte não encontrado."}), 304 # Not Modified
    except ValueError as e: # Captura erro de nome duplicado na atualização
        return jsonify({"mensagem": str(e)}), 409
    except Exception:
        return jsonify({"mensagem": "Esporte não encontrado."}), 404

@esporte_bp.route('/<string:esporte_id>', methods=['DELETE'])
@admin_required()
def deletar_esporte_existente(esporte_id):
    """
    [ADMIN] Endpoint para deletar um esporte.
    """
    try:
        deletados = esporte_service.deletar_esporte(esporte_id)
        if deletados > 0:
            return '', 204 # No Content, sucesso
        else:
            return jsonify({"mensagem": "Esporte não encontrado."}), 404
    except ValueError as e:
        # Captura o erro do service que impede a exclusão de esporte em uso
        return jsonify({"mensagem": str(e)}), 400
  
@esporte_bp.route('/com-categorias', methods=['GET'])
@admin_required()
def get_esportes_com_categorias():
    """
    Retorna uma lista de todos os esportes, cada um com uma sub-lista
    de suas categorias cadastradas.
    """
    try:
        pipeline = [
            {
                "$lookup": {
                    "from": "categorias",
                    "localField": "_id",
                    "foreignField": "esporte_id",
                    "as": "categorias"
                }
            },
            {
                "$project": {
                    "nome": 1,
                    "categorias.nome": 1,
                    "categorias._id": 1
                }
            }
        ]
        esportes = list(mongo.db.esportes.aggregate(pipeline))
        return json.loads(json_util.dumps(esportes)), 200
    except Exception as e:
        print("!!!!!!!!!! ERRO AO BUSCAR ESPORTES COM CATEGORIAS !!!!!!!!!!")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return jsonify({"mensagem": "Erro interno ao buscar esportes com categorias.", "detalhes": str(e)}), 500
