from flask import Blueprint, request, jsonify
from app.services import usuario_service
from app import mongo
from flask_jwt_extended import create_access_token
import datetime

auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/registrar-admin', methods=['POST'])
def registrar_admin():
    """
    Endpoint para registrar o primeiro usuário administrador.
    Suposição pragmática: Este endpoint só funciona se não houver nenhum admin no sistema.
    """
    # Verifica se já existe um admin
    if mongo.db.usuarios.find_one({"perfil": "admin"}):
        return jsonify({"mensagem": "Um administrador já foi configurado."}), 409 # Conflict

    dados = request.get_json()
    if not dados or not all(k in dados for k in ('nome_completo', 'email', 'senha', 'data_nascimento')):
        return jsonify({"mensagem": "Dados incompletos."}), 400

    dados['perfil'] = 'admin' # Força o perfil a ser admin

    try:
        usuario_id = usuario_service.criar_usuario(dados)
        return jsonify({
            "mensagem": "Usuário administrador criado com sucesso!",
            "usuario_id": usuario_id
        }), 201
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        return jsonify({"mensagem": "Erro interno ao criar administrador.", "erro": str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Autentica um usuário e retorna um token de acesso JWT.
    """
    dados = request.get_json()
    if not dados or 'email' not in dados or 'senha' not in dados:
        return jsonify({"mensagem": "E-mail e senha são obrigatórios."}), 400

    email = dados['email']
    senha = dados['senha']

    usuario = usuario_service.encontrar_usuario_por_email(email)

    if not usuario or not usuario_service.verificar_senha(usuario['senha_hash'], senha):
        return jsonify({"mensagem": "Credenciais inválidas."}), 401 # Unauthorized

    if not usuario['ativo']:
        return jsonify({"mensagem": "Este usuário está inativo."}), 403 # Forbidden

    # Informações que queremos incluir no token (payload)
    # A identidade do token será o ID do usuário (convertido para string)
    # Também incluiremos o perfil (role) para controle de acesso nas rotas
    identidade = str(usuario['_id'])
    claims_adicionais = {
    "perfil": usuario['perfil'],
    "nome_completo": usuario['nome_completo'] # <--- GARANTA QUE ESTA LINHA EXISTA E ESTEJA CORRETA
}
    
    token_de_acesso = create_access_token(
        identity=identidade, 
        additional_claims=claims_adicionais
    )

    return jsonify(access_token=token_de_acesso), 200