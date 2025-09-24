from flask import Blueprint, jsonify, request
from app.decorators.auth_decorators import admin_required
from app.services import usuario_service
from bson import json_util
import json
from bson import ObjectId
from flask_jwt_extended import jwt_required, get_jwt_identity


usuario_bp = Blueprint('usuario_bp', __name__)

def formatar_usuario(usuario):
    """Função utilitária para formatar a saída do usuário para JSON."""
    if not usuario:
        return None
    usuario['_id'] = str(usuario['_id'])
    if 'data_nascimento' in usuario and usuario['data_nascimento']:
        usuario['data_nascimento'] = usuario['data_nascimento'].strftime('%Y-%m-%d')
    if 'data_criacao' in usuario and usuario['data_criacao']:
        usuario['data_criacao'] = usuario['data_criacao'].isoformat()
    return usuario


# Rota para o próprio usuário ver seu perfil
@usuario_bp.route('/perfil', methods=['GET'])
@jwt_required()
def obter_perfil_pessoal():
    usuario_id_atual = get_jwt_identity()
    usuario = usuario_service.encontrar_usuario_por_id(usuario_id_atual) # Supondo que esta função exista
    if not usuario:
        return jsonify({"mensagem": "Usuário não encontrado."}), 404
    return json.loads(json_util.dumps(usuario)), 200


# --- Rotas de Gerenciamento (Apenas para Admins) ---

@usuario_bp.route('/', methods=['POST'])
@admin_required()
def criar_novo_usuario():
    dados = request.get_json()
    campos_obrigatorios_base = ['nome_completo', 'email', 'senha', 'perfil']
    if not dados or not all(k in dados for k in campos_obrigatorios_base):
        return jsonify({"mensagem": "Dados incompletos."}), 400
    if dados.get('perfil') == 'aluno' and 'data_nascimento' not in dados:
        return jsonify({"mensagem": "Para 'aluno', 'data_nascimento' é obrigatório."}), 400

    try:
        usuario_id = usuario_service.criar_usuario(dados)
        return jsonify({"mensagem": "Usuário criado com sucesso!", "usuario_id": usuario_id}), 201
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        return jsonify({"mensagem": "Erro interno.", "erro": str(e)}), 500


@usuario_bp.route('/', methods=['GET'])
@admin_required()
def obter_todos_usuarios():
    """
    [ADMIN] Lista todos os usuários do sistema, com suporte a filtros.
    """
    filtros = {}
    perfil_query = request.args.get('perfil')
    if perfil_query:
        filtros['perfil'] = perfil_query
    pagamento_query = request.args.get('status_pagamento')
    if pagamento_query:
        filtros['status_pagamento'] = pagamento_query

    usuarios = usuario_service.listar_usuarios(filtros)
    
    # --- CORREÇÃO PRINCIPAL APLICADA AQUI ---
    # Usamos json_util para serializar a lista inteira, preservando o formato do ObjectId
    return json.loads(json_util.dumps(usuarios)), 200


@usuario_bp.route('/<string:usuario_id>', methods=['GET'])
@admin_required()
def obter_usuario_por_id(usuario_id):
    usuario = usuario_service.encontrar_usuario_por_id(usuario_id) # Supondo que esta função exista
    if not usuario:
        return jsonify({"mensagem": "Usuário não encontrado."}), 404
    return json.loads(json_util.dumps(usuario)), 200


@usuario_bp.route('/<string:usuario_id>', methods=['PUT'])
@admin_required()
def atualizar_usuario_existente(usuario_id):
    dados = request.get_json()
    try:
        if usuario_service.atualizar_usuario(usuario_id, dados): # Assumindo que o serviço retorna True/False ou levanta exceção
            return jsonify({"mensagem": "Usuário atualizado com sucesso."}), 200
        else:
            return jsonify({"mensagem": "Nenhuma alteração realizada ou usuário não encontrado."}), 404
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400


@usuario_bp.route('/<string:usuario_id>', methods=['DELETE'])
@admin_required()
def deletar_usuario_existente(usuario_id):
    modificados = usuario_service.deletar_usuario(usuario_id) # Supondo que deletar retorna o nro de modificados
    if modificados > 0:
        return '', 204
    else:
        return jsonify({"mensagem": "Usuário não encontrado."}), 404

@usuario_bp.route('/<string:usuario_id>/pagamento', methods=['PUT'])
@admin_required()
def definir_status_pagamento(usuario_id):
    """[ADMIN] Define o status de pagamento de um usuário."""
    dados = request.get_json()
    if not dados or 'status' not in dados:
        return jsonify({"mensagem": "O campo 'status' é obrigatório."}), 400
    
    try:
        modificados = usuario_service.atualizar_status_pagamento(usuario_id, dados)
        if modificados > 0:
            return jsonify({"mensagem": "Status de pagamento atualizado."}), 200
        else:
            return jsonify({"mensagem": "Nenhuma alteração realizada ou usuário não encontrado."}), 404
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

@usuario_bp.route('/verificar-pagamentos', methods=['POST'])
@admin_required()
def verificar_pagamentos():
    """
    [ADMIN] Aciona a verificação de mensalidades vencidas.
    """
    try:
        modificados = usuario_service.verificar_e_atualizar_vencimentos()
        return jsonify({"mensagem": f"{modificados} aluno(s) atualizado(s) para 'pendente'."}), 200
    except Exception as e:
        return jsonify({"mensagem": "Erro ao verificar pagamentos.", "detalhes": str(e)}), 500