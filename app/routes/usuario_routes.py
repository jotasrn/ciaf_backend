from flask import Blueprint, jsonify, request
from app.decorators.auth_decorators import admin_required
from app.services import usuario_service
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
    usuario = usuario_service.encontrar_usuario_por_id(usuario_id_atual)
    if not usuario:
        return jsonify({"mensagem": "Usuário não encontrado."}), 404
    return jsonify(formatar_usuario(usuario)), 200


# --- Rotas de Gerenciamento (Apenas para Admins) ---

@usuario_bp.route('/', methods=['POST'])
@admin_required()
def criar_novo_usuario():
    """
    [ADMIN] Cria um novo usuário (professor, aluno, etc.).
    """
    dados = request.get_json()
    if not dados or not all(k in dados for k in ('nome_completo', 'email', 'senha', 'data_nascimento', 'perfil')):
        return jsonify({"mensagem": "Dados incompletos."}), 400

    if dados['perfil'] == 'admin':
        return jsonify({"mensagem": "Não é permitido criar outro admin por esta rota."}), 403

    try:
        usuario_id = usuario_service.criar_usuario(dados)
        return jsonify({
            "mensagem": "Usuário criado com sucesso!",
            "usuario_id": usuario_id
        }), 201
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        return jsonify({"mensagem": "Erro interno.", "erro": str(e)}), 500


@usuario_bp.route('/', methods=['GET'])
@admin_required()
def obter_todos_usuarios():
    """
    [ADMIN] Lista todos os usuários do sistema.
    """
    usuarios = usuario_service.listar_usuarios()
    usuarios_formatados = [formatar_usuario(u) for u in usuarios]
    return jsonify(usuarios_formatados), 200


@usuario_bp.route('/<string:usuario_id>', methods=['GET'])
@admin_required()
def obter_usuario_por_id(usuario_id):
    """
    [ADMIN] Obtém os detalhes de um usuário específico.
    """
    usuario = usuario_service.encontrar_usuario_por_id(usuario_id)
    if not usuario:
        return jsonify({"mensagem": "Usuário não encontrado."}), 404
    return jsonify(formatar_usuario(usuario)), 200


@usuario_bp.route('/<string:usuario_id>', methods=['PUT'])
@admin_required()
def atualizar_usuario_existente(usuario_id):
    """
    [ADMIN] Atualiza os dados de um usuário.
    """
    dados = request.get_json()
    try:
        if usuario_service.atualizar_usuario(usuario_id, dados) > 0:
            return jsonify({"mensagem": "Usuário atualizado com sucesso."}), 200
        else:
            return jsonify({"mensagem": "Nenhuma alteração realizada ou usuário não encontrado."}), 404
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400


@usuario_bp.route('/<string:usuario_id>', methods=['DELETE'])
@admin_required()
def deletar_usuario_existente(usuario_id):
    """
    [ADMIN] Desativa (soft delete) um usuário.
    """
    if usuario_service.deletar_usuario(usuario_id) > 0:
        return '', 204 # No Content, sucesso
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
