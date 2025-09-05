from flask import Blueprint, request, jsonify
from app.services import usuario_service
from app import mongo
from flask_jwt_extended import create_access_token
import datetime

# Cria o Blueprint para agrupar as rotas de autenticação
auth_bp = Blueprint('auth_bp', __name__)

@auth_bp.route('/registrar-admin', methods=['POST'])
def registrar_admin():
    """
    Endpoint para registrar o primeiro usuário administrador.
    A verificação se um admin já existe é feita aqui dentro para garantir
    que a consulta ao banco de dados ocorra no contexto correto da requisição.
    """
    # A consulta ao banco de dados acontece aqui, quando a rota é chamada.
    if mongo.db.usuarios.find_one({"perfil": "admin"}):
        return jsonify({"mensagem": "Um administrador já foi configurado."}), 409 # Conflict

    dados = request.get_json()
    # Validação dos dados de entrada
    if not dados or not all(k in dados for k in ('nome_completo', 'email', 'senha', 'data_nascimento')):
        return jsonify({"mensagem": "Dados incompletos. 'nome_completo', 'email', 'senha' e 'data_nascimento' são obrigatórios."}), 400

    # Força o perfil a ser 'admin' para esta rota específica
    dados['perfil'] = 'admin'

    try:
        usuario_id = usuario_service.criar_usuario(dados)
        return jsonify({
            "mensagem": "Usuário administrador criado com sucesso!",
            "usuario_id": usuario_id
        }), 201
    except ValueError as e:
        # Captura erros de validação do service (ex: e-mail duplicado)
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        # Captura outros erros inesperados
        return jsonify({"mensagem": "Erro interno ao criar administrador.", "erro": str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Autentica um usuário (admin, professor ou aluno) e retorna um token de acesso JWT.
    """
    dados = request.get_json()
    if not dados or 'email' not in dados or 'senha' not in dados:
        return jsonify({"mensagem": "E-mail e senha são obrigatórios."}), 400

    email = dados['email']
    senha = dados['senha']

    usuario = usuario_service.encontrar_usuario_por_email(email)

    # Verifica se o usuário existe e se a senha está correta
    if not usuario or not usuario_service.verificar_senha(usuario['senha_hash'], senha):
        return jsonify({"mensagem": "Credenciais inválidas."}), 401 # Unauthorized

    # Verifica se o usuário está ativo no sistema
    if not usuario.get('ativo', True):
        return jsonify({"mensagem": "Este usuário está inativo."}), 403 # Forbidden

    # Define as informações que serão incluídas no payload do token JWT
    identidade = str(usuario['_id'])
    claims_adicionais = {
        "perfil": usuario['perfil'],
        "nome_completo": usuario['nome_completo']
    }
    
    # Cria o token de acesso
    token_de_acesso = create_access_token(
        identity=identidade, 
        additional_claims=claims_adicionais
    )

    return jsonify(access_token=token_de_acesso), 200