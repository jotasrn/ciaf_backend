from app import mongo
import bcrypt
import datetime
from bson import ObjectId

def _adicionar_aluno_a_turma(aluno_id, turma_id):
    """Função auxiliar para adicionar um aluno a uma turma."""
    if not turma_id:
        return

    # Primeiro, remove o aluno de qualquer outra turma em que ele possa estar
    mongo.db.turmas.update_many(
        {"alunos_ids": ObjectId(aluno_id)},
        {"$pull": {"alunos_ids": ObjectId(aluno_id)}}
    )

    # Adiciona o aluno à nova turma
    mongo.db.turmas.update_one(
        {"_id": ObjectId(turma_id)},
        {"$addToSet": {"alunos_ids": ObjectId(aluno_id)}} # $addToSet previne duplicatas
    )

def criar_usuario(dados_usuario):
    """
    Cria um novo usuário e, se for um aluno com turma_id,
    o adiciona à turma.
    """
    usuarios_collection = mongo.db.usuarios
    if usuarios_collection.find_one({"email": dados_usuario['email']}):
        raise ValueError("O e-mail informado já está em uso.")

    senha_texto_puro = dados_usuario.get('senha', 'senhaPadrao123').encode('utf-8')
    senha_hash = bcrypt.hashpw(senha_texto_puro, bcrypt.gensalt())

    novo_usuario = {
        "nome_completo": dados_usuario['nome_completo'],
        "email": dados_usuario['email'],
        "senha_hash": senha_hash.decode('utf-8'),
        "perfil": "aluno", # Garante que seja sempre aluno
        "data_nascimento": datetime.datetime.fromisoformat(dados_usuario['data_nascimento']),
        "ativo": True,
        "data_criacao": datetime.datetime.utcnow(),
        "data_matricula": datetime.datetime.fromisoformat(dados_usuario.get('data_matricula')),
        "contato_responsavel": dados_usuario.get('contato_responsavel', {})
    }
    
    resultado = usuarios_collection.insert_one(novo_usuario)
    aluno_id = resultado.inserted_id

    # Lógica de vínculo com a turma
    turma_id = dados_usuario.get('turma_id')
    if turma_id:
        _adicionar_aluno_a_turma(aluno_id, turma_id)

    return str(aluno_id)

def atualizar_usuario(usuario_id, dados_atualizacao):
    """
    Atualiza os dados de um usuário e o move para a turma correta, se informado.
    """
    try:
        obj_id = ObjectId(usuario_id)
    except Exception:
        raise ValueError("ID de usuário inválido.")

    update_fields = {}
    
    campos_permitidos = [
        'nome_completo', 'email', 'perfil', 'ativo',
        'contato_responsavel', 'data_nascimento', 'data_matricula'
    ]
    for campo in campos_permitidos:
        if campo in dados_atualizacao:
            # Converte as strings de data para objetos ISODate
            if campo in ['data_nascimento', 'data_matricula'] and dados_atualizacao[campo]:
                update_fields[campo] = datetime.datetime.fromisoformat(dados_atualizacao[campo])
            else:
                update_fields[campo] = dados_atualizacao[campo]

    if 'senha' in dados_atualizacao and dados_atualizacao['senha']:
        senha_texto_puro = dados_atualizacao['senha'].encode('utf-8')
        update_fields['senha_hash'] = bcrypt.hashpw(senha_texto_puro, bcrypt.gensalt()).decode('utf-8')

    if update_fields:
        resultado = mongo.db.usuarios.update_one(
            {"_id": obj_id},
            {"$set": update_fields}
        )
    
    # Lógica de vínculo com a turma
    turma_id = dados_atualizacao.get('turma_id')
    if turma_id:
        _adicionar_aluno_a_turma(usuario_id, turma_id)

    if not update_fields and not turma_id:
        return 0

    return resultado.modified_count if 'resultado' in locals() else 0

def encontrar_usuario_por_email(email):
    return mongo.db.usuarios.find_one({"email": email})

def verificar_senha(senha_hash, senha_fornecida):
    return bcrypt.checkpw(senha_fornecida.encode('utf-8'), senha_hash.encode('utf-8'))

def listar_usuarios(filtros=None):
    query = {'ativo': True}
    if filtros:
        if 'perfil' in filtros:
            query['perfil'] = filtros['perfil']
        if 'perfil_ne' in filtros:
            query['perfil'] = {'$ne': filtros['perfil_ne']}
        if 'status_pagamento' in filtros:
            query['status_pagamento.status'] = filtros['status_pagamento']
    
    return list(mongo.db.usuarios.find(query, {"senha_hash": 0}))

def encontrar_usuario_por_id(usuario_id):
    try:
        obj_id = ObjectId(usuario_id)
        return mongo.db.usuarios.find_one({"_id": obj_id}, {"senha_hash": 0})
    except Exception:
        return None

def deletar_usuario(usuario_id):
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
    try:
        obj_id = ObjectId(usuario_id)
    except Exception:
        raise ValueError("ID de usuário inválido.")

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

