from app import mongo
import bcrypt
import datetime
from bson import ObjectId

def criar_usuario(dados_usuario):
    """
    Cria um novo usuário no banco de dados.
    Verifica se o e-mail já existe e faz o hash da senha.
    """
    usuarios_collection = mongo.db.usuarios

    # 1. Validação: Verificar se o e-mail já está em uso
    usuario_existente = usuarios_collection.find_one({"email": dados_usuario['email']})
    if usuario_existente:
        # Lançar uma exceção é uma boa prática para a camada de serviço
        raise ValueError("O e-mail informado já está em uso.")

    # 2. Segurança: Gerar o hash da senha com bcrypt
    senha_texto_puro = dados_usuario['senha'].encode('utf-8')
    senha_hash = bcrypt.hashpw(senha_texto_puro, bcrypt.gensalt())

    # 3. Preparar o documento para inserção
    novo_usuario = {
        "nome_completo": dados_usuario['nome_completo'],
        "email": dados_usuario['email'],
        "senha_hash": senha_hash.decode('utf-8'), # Armazenar como string
        "perfil": dados_usuario.get('perfil', 'aluno'), # Padrão é 'aluno'
        "data_nascimento": datetime.datetime.fromisoformat(dados_usuario['data_nascimento']),
        "ativo": True,
        "data_criacao": datetime.datetime.utcnow()
    }
    
    # Adiciona dados do responsável se o perfil for 'aluno'
    if novo_usuario['perfil'] == 'aluno' and 'contato_responsavel' in dados_usuario:
        novo_usuario['contato_responsavel'] = dados_usuario['contato_responsavel']

    # 4. Inserir no banco de dados
    resultado = usuarios_collection.insert_one(novo_usuario)
    
    return str(resultado.inserted_id)

def encontrar_usuario_por_email(email):
    """
    Busca um usuário pelo seu e-mail.
    """
    return mongo.db.usuarios.find_one({"email": email})

def verificar_senha(senha_hash, senha_fornecida):
    """
    Verifica se a senha fornecida corresponde ao hash armazenado.
    """
    return bcrypt.checkpw(senha_fornecida.encode('utf-8'), senha_hash.encode('utf-8'))

def listar_usuarios(filtros=None):
    """
    Retorna uma lista de todos os usuários, com suporte a filtros.
    Sem o hash da senha.
    """
    query = {'ativo': True}
    if filtros:
        if 'perfil' in filtros:
            query['perfil'] = filtros['perfil']
        
        # Adiciona a lógica para o novo filtro de status de pagamento.
        # Note que acessamos o campo aninhado com a "dot notation" do MongoDB.
        if 'status_pagamento' in filtros:
            query['status_pagamento.status'] = filtros['status_pagamento']
    
    return list(mongo.db.usuarios.find(query, {"senha_hash": 0}))

def encontrar_usuario_por_id(usuario_id):
    """
    Busca um usuário específico pelo seu ID.
    """
    try:
        # Valida e converte a string para ObjectId
        obj_id = ObjectId(usuario_id)
        return mongo.db.usuarios.find_one({"_id": obj_id}, {"senha_hash": 0})
    except Exception:
        return None # Retorna None se o ID for inválido

def atualizar_usuario(usuario_id, dados_atualizacao):
    """
    Atualiza os dados de um usuário.
    Se uma nova senha for fornecida, ela será hasheada.
    """
    try:
        obj_id = ObjectId(usuario_id)
    except Exception:
        raise ValueError("ID de usuário inválido.")

    update_fields = {}
    
    # Adiciona campos permitidos para atualização
    for campo in ['nome_completo', 'email', 'data_nascimento', 'perfil', 'ativo', 'contato_responsavel']:
        if campo in dados_atualizacao:
            update_fields[campo] = dados_atualizacao[campo]

    # Tratamento especial para a senha
    if 'senha' in dados_atualizacao and dados_atualizacao['senha']:
        senha_texto_puro = dados_atualizacao['senha'].encode('utf-8')
        update_fields['senha_hash'] = bcrypt.hashpw(senha_texto_puro, bcrypt.gensalt()).decode('utf-8')

    if not update_fields:
        return 0 # Nada para atualizar

    resultado = mongo.db.usuarios.update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )
    return resultado.modified_count

def deletar_usuario(usuario_id):
    """
    Realiza um "soft delete", marcando o usuário como inativo.
    Decisão pragmática: Não apagamos dados para manter a integridade
    histórica. Por exemplo, a presença de um aluno em uma aula antiga
    continuará válida mesmo que o aluno seja "deletado".
    """
    try:
        obj_id = ObjectId(usuario_id)
        resultado = mongo.db.usuarios.update_one(
            {"_id": obj_id},
            {"$set": {"ativo": False}}
        )
        return resultado.modified_count
    except Exception:
        return 0

def atualizar_status_pagamento(usuario_id, dados_pagamento):
    """Atualiza o status de pagamento de um usuário."""
    try:
        obj_id = ObjectId(usuario_id)
    except Exception:
        raise ValueError("ID de usuário inválido.")

    # Validação simples dos dados de entrada
    status = dados_pagamento.get('status')
    if status not in ['pendente', 'pago', 'atrasado']:
        raise ValueError("Status de pagamento inválido.")
        
    update_fields = {"status_pagamento.status": status}
    
    if 'data_vencimento' in dados_pagamento:
        update_fields['status_pagamento.data_vencimento'] = datetime.datetime.fromisoformat(dados_pagamento['data_vencimento'])

    resultado = mongo.db.usuarios.update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )
    return resultado.modified_count

