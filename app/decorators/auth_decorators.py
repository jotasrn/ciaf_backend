from functools import wraps
from flask import jsonify
from flask_jwt_extended import jwt_required, get_jwt

def role_required(roles):
    """
    Decorator customizado que verifica se o perfil do usuário está na lista de perfis permitidos.
    Ele já inclui a verificação do @jwt_required.
    
    :param roles: Uma lista de strings de perfis permitidos (ex: ['admin', 'professor'])
    """
    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def decorator(*args, **kwargs):
            claims = get_jwt()
            user_role = claims.get("perfil")
            if user_role not in roles:
                return jsonify({"mensagem": f"Acesso restrito. Perfis permitidos: {', '.join(roles)}."}), 403 # Forbidden
            return fn(*args, **kwargs)
        return decorator
    return wrapper

# O decorator antigo pode ser removido ou reescrito usando o novo:
def admin_required():
    return role_required(roles=['admin'])