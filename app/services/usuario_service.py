from app import mongo
import bcrypt
import datetime
from bson import ObjectId
from dateutil.relativedelta import relativedelta

def _adicionar_aluno_a_turma(aluno_id, turma_id):
    """Função auxiliar para adicionar/mover um aluno para uma turma."""
    if not turma_id or turma_id == 'Nenhuma': # 'Nenhuma' pode ser um valor enviado pelo frontend
        return

    aluno_obj_id = ObjectId(aluno_id)
    turma_obj_id = ObjectId(turma_id)

    # Primeiro, remove o aluno de qualquer outra turma em que ele possa estar,
    # garantindo que um aluno pertença a apenas uma turma.
    mongo.db.turmas.update_many(
        {"alunos_ids": aluno_obj_id},
        {"$pull": {"alunos_ids": aluno_obj_id}}
    )

    # Adiciona o aluno à nova turma selecionada
    mongo.db.turmas.update_one(
        {"_id": turma_obj_id},
        {"$addToSet": {"alunos_ids": aluno_obj_id}} # $addToSet previne duplicatas
    )

def _vincular_professor_a_turmas(professor_id, turmas_ids):
    """Função auxiliar para vincular um professor a uma ou mais turmas."""
    prof_obj_id = ObjectId(professor_id)
    
    # Remove este professor de QUALQUER turma para começar do zero.
    # Isso garante que se o admin desmarcar uma turma, o professor seja removido dela.
    mongo.db.turmas.update_many(
        {"professor_id": prof_obj_id},
        {"$unset": {"professor_id": ""}}
    )

    # Se uma lista de turmas foi enviada, vincula o professor a elas.
    if turmas_ids:
        mongo.db.turmas.update_many(
            {"_id": {"$in": [ObjectId(tid) for tid in turmas_ids]}},
            {"$set": {"professor_id": prof_obj_id}}
        )

def criar_usuario(dados_usuario):
    """
    Cria um novo usuário e inicializa campos padrão dependendo do perfil.
    """
    if mongo.db.usuarios.find_one({"email": dados_usuario['email']}):
        raise ValueError("O e-mail informado já está em uso.")
    
    senha_hash = bcrypt.hashpw(dados_usuario['senha'].encode('utf-8'), bcrypt.gensalt())
    
    novo_usuario = {
        "nome_completo": dados_usuario['nome_completo'],
        "email": dados_usuario['email'],
        "senha_hash": senha_hash, # Salva como bytes, é mais seguro
        "perfil": dados_usuario.get('perfil'),
        "ativo": True,
        "data_criacao": datetime.datetime.utcnow(),
    }

    if novo_usuario['perfil'] == 'aluno':
        if 'data_nascimento' in dados_usuario and dados_usuario['data_nascimento']:
            novo_usuario['data_nascimento'] = datetime.datetime.fromisoformat(dados_usuario['data_nascimento'])
        
        # Inicializa o status de pagamento para todo novo aluno
        novo_usuario['status_pagamento'] = {
            'status': 'pendente',
            'data_vencimento': None,
            'data_ultimo_pagamento': None
        }
        novo_usuario['telefone'] = dados_usuario.get('telefone')
        novo_usuario['responsavel'] = dados_usuario.get('responsavel')

    resultado = mongo.db.usuarios.insert_one(novo_usuario)
    return str(resultado.inserted_id)

def atualizar_usuario(usuario_id, dados_atualizacao):
    """
    Atualiza os dados de um usuário e o move para a turma correta, se informado.
    """
    obj_id = ObjectId(usuario_id)
    update_fields = {}
    
    campos_permitidos = [
        'nome_completo', 'email', 'perfil', 'ativo',
        'contato_responsavel'
    ]
    for campo in campos_permitidos:
        if campo in dados_atualizacao:
            update_fields[campo] = dados_atualizacao[campo]
            
    # Converte as strings de data para objetos ISODate de forma segura
    if 'data_nascimento' in dados_atualizacao and dados_atualizacao['data_nascimento']:
         update_fields['data_nascimento'] = datetime.datetime.fromisoformat(dados_atualizacao['data_nascimento'])
    if 'data_matricula' in dados_atualizacao and dados_atualizacao['data_matricula']:
         update_fields['data_matricula'] = datetime.datetime.fromisoformat(dados_atualizacao['data_matricula'])

    if 'senha' in dados_atualizacao and dados_atualizacao['senha']:
        senha_texto_puro = dados_atualizacao['senha'].encode('utf-8')
        update_fields['senha_hash'] = bcrypt.hashpw(senha_texto_puro, bcrypt.gensalt()).decode('utf-8')

    if update_fields:
        mongo.db.usuarios.update_one({"_id": obj_id}, {"$set": update_fields})
    
    # Lógica de vínculo com a turma
    perfil_atual = dados_atualizacao.get('perfil') or mongo.db.usuarios.find_one({"_id": obj_id}).get('perfil')
    
    if perfil_atual == 'aluno':
        turma_id = dados_atualizacao.get('turma_id')
        if turma_id is not None: # Permite desvincular passando turma_id nulo
            _adicionar_aluno_a_turma(usuario_id, turma_id)
    
    elif perfil_atual == 'professor':
        turmas_ids = dados_atualizacao.get('turmas_ids')
        if turmas_ids is not None:
            _vincular_professor_a_turmas(usuario_id, turmas_ids)
    
    return True # Retorna sucesso

def listar_usuarios(filtros=None):
    """
    Retorna uma lista de usuários, com suporte a filtros.
    """
    query = { 'ativo': True } # Por padrão, sempre busca usuários ativos
    if filtros:
        if 'perfil' in filtros:
            query['perfil'] = filtros['perfil']
        if 'perfil_ne' in filtros: # 'ne' significa 'Not Equal' (diferente de)
            query['perfil'] = {"$ne": filtros['perfil_ne']}
        if 'status_pagamento' in filtros:
             query['status_pagamento.status'] = filtros['status_pagamento']
            
    return list(mongo.db.usuarios.find(query, {"senha_hash": 0}))

def encontrar_usuario_por_email(email):
    """Busca um usuário pelo seu e-mail."""
    return mongo.db.usuarios.find_one({"email": email})

def verificar_senha(senha_hash, senha_fornecida):
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return bcrypt.checkpw(senha_fornecida.encode('utf-8'), senha_hash.encode('utf-8'))

def deletar_usuario(usuario_id):
    """Realiza um 'soft delete', marcando o usuário como inativo."""
    try:
        obj_id = ObjectId(usuario_id)
        # Além de desativar, também remove o aluno de qualquer turma
        mongo.db.turmas.update_many(
            {"alunos_ids": obj_id},
            {"$pull": {"alunos_ids": obj_id}}
        )
        # E desvincula o professor
        mongo.db.turmas.update_many(
            {"professor_id": obj_id},
            {"$unset": {"professor_id": ""}}
        )
        
        resultado = mongo.db.usuarios.update_one(
            {"_id": obj_id},
            {"$set": {"ativo": False}}
        )
        return resultado.modified_count
    except Exception:
        return 0

def atualizar_status_pagamento(usuario_id, dados_pagamento):
    """
    Atualiza o status de pagamento de um usuário.
    Se o novo status for 'pago', calcula a data do próximo vencimento.
    """
    obj_id = ObjectId(usuario_id)
    status = dados_pagamento.get('status')
    if status not in ['pendente', 'pago', 'atrasado']:
        raise ValueError("Status de pagamento inválido.")
        
    update_fields = {"status_pagamento.status": status}
    
    # Lógica de vencimento
    if status == 'pago':
        aluno = mongo.db.usuarios.find_one({"_id": obj_id})
        # Usa a data de matrícula como base para o dia do vencimento
        data_matricula = aluno.get('data_matricula', datetime.datetime.utcnow())
        hoje = datetime.datetime.utcnow()
        
        # Calcula o próximo vencimento
        proximo_vencimento = data_matricula.replace(year=hoje.year, month=hoje.month)
        if proximo_vencimento < hoje:
            proximo_vencimento += relativedelta(months=1)
            
        update_fields['status_pagamento.data_ultimo_pagamento'] = hoje
        update_fields['status_pagamento.data_vencimento'] = proximo_vencimento
    
    resultado = mongo.db.usuarios.update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )
    return resultado.modified_count

def verificar_e_atualizar_vencimentos():
    """
    Varre todos os alunos e atualiza o status de pagamento para 'pendente'
    se a data de vencimento já passou e o status ainda é 'pago'.
    """
    hoje = datetime.datetime.utcnow()
    resultado = mongo.db.usuarios.update_many(
        {
            "perfil": "aluno",
            "ativo": True,
            "status_pagamento.status": "pago",
            "status_pagamento.data_vencimento": {"$lt": hoje}
        },
        {"$set": {"status_pagamento.status": "pendente"}}
    )
    return resultado.modified_count