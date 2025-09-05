from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

def role_required(roles):
    """
    Decorator customizado que verifica se o perfil do usuário (lido a partir do token JWT)
    está na lista de perfis permitidos.

    Este decorator já inclui a verificação de um token válido (@jwt_required).
    
    :param roles: Uma lista de strings de perfis permitidos (ex: ['admin', 'professor'])
    """
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()  # Garante que um token JWT válido está presente na requisição
        def decorator(*args, **kwargs):
            # Pega as informações (claims) de dentro do token decodificado
            claims = get_jwt()
            user_role = claims.get("perfil")

            # Verifica se o perfil do usuário no token está na lista de perfis permitidos
            if user_role not in roles:
                return jsonify({"mensagem": f"Acesso restrito. Perfis permitidos: {', '.join(roles)}."}), 403 # HTTP 403 Forbidden
            
            # Se a verificação passar, executa a função da rota original
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def admin_required():
    """
    Um atalho (convenience decorator) para @role_required(roles=['admin']).
    Use @admin_required() para proteger rotas que só podem ser acessadas por administradores.
    """
    return role_required(roles=['admin'])