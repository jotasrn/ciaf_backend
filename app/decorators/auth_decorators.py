from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

def role_required(roles):
    """
    Decorator customizado que verifica o perfil do usuário.
    Esta versão é robusta e lida corretamente com as requisições OPTIONS do CORS.
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            # 1. Verifica se um token JWT válido está presente na requisição.
            # Esta função é inteligente e não gera erro para requisições OPTIONS.
            verify_jwt_in_request()
            
            # 2. Se a verificação passou, pega os dados (claims) do token.
            claims = get_jwt()
            
            # 3. Verifica se o perfil do usuário está na lista de perfis permitidos.
            user_role = claims.get("perfil")
            if user_role not in roles:
                return jsonify({"mensagem": f"Acesso restrito. Perfis permitidos: {', '.join(roles)}."}), 403
            
            # 4. Se tudo estiver OK, executa a função da rota original.
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def admin_required():
    """Um atalho para role_required(['admin'])"""
    return role_required(roles=['admin'])
    