from app import mongo
from bson import ObjectId
import datetime
from pymongo import UpdateOne

def _validar_ids_usuarios(professor_id, alunos_ids):
    """
    Função auxiliar para validar se os IDs de usuários existem e têm os perfis corretos.
    Isso garante a integridade dos dados da turma.
    """
    # Valida professor
    professor = mongo.db.usuarios.find_one({
        "_id": ObjectId(professor_id),
        "perfil": "professor",
        "ativo": True
    })
    if not professor:
        raise ValueError(f"Professor com ID '{professor_id}' não encontrado, inativo ou não possui o perfil de professor.")

    # Valida alunos
    if alunos_ids:
        # Garante que a lista de IDs de alunos não contenha duplicatas antes de contar
        ids_unicos_alunos = list(set(alunos_ids))
        alunos_encontrados = mongo.db.usuarios.count_documents({
            "_id": {"$in": [ObjectId(aid) for aid in ids_unicos_alunos]},
            "perfil": "aluno",
            "ativo": True
        })
        if alunos_encontrados != len(ids_unicos_alunos):
            raise ValueError("Um ou mais IDs de alunos são inválidos, inativos ou não possuem o perfil de aluno.")
    return True

def criar_turma(dados_turma):
    """
    Cria uma nova turma após validar os IDs do esporte, professor e alunos.
    """
    esporte_id = ObjectId(dados_turma['esporte_id'])
    professor_id = dados_turma['professor_id']
    alunos_ids = dados_turma.get('alunos_ids', [])

    # Valida se o esporte existe
    if not mongo.db.esportes.find_one({"_id": esporte_id}):
        raise ValueError("Esporte com o ID fornecido não encontrado.")

    # Valida se os usuários (professor e alunos) são válidos
    _validar_ids_usuarios(professor_id, alunos_ids)

    nova_turma = {
        "nome": dados_turma['nome'],
        "esporte_id": esporte_id,
        "categoria": dados_turma.get('categoria', 'Geral'), # Adiciona o novo campo
        "descricao": dados_turma.get('descricao', ''),
        "professor_id": ObjectId(professor_id),
        "alunos_ids": [ObjectId(aid) for aid in alunos_ids],
        "horarios": dados_turma.get('horarios', [])
    }
    resultado = mongo.db.turmas.insert_one(nova_turma)
    return str(resultado.inserted_id)

def _get_aggregation_pipeline(turma_id=None):
    """
    Cria um pipeline de agregação para buscar turmas e popular os dados
    do esporte, professor e alunos, evitando múltiplas queries ao banco.
    """
    pipeline = []
    if turma_id:
        # Se um ID de turma específico é fornecido, começa filtrando por ele.
        pipeline.append({"$match": {"_id": ObjectId(turma_id)}})

    pipeline.extend([
        # Join com 'esportes' para buscar o esporte
        {
            "$lookup": {
                "from": "esportes",
                "localField": "esporte_id",
                "foreignField": "_id",
                "as": "esporte_info"
            }
        },
        # Join com 'usuarios' para buscar o professor
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "professor_id",
                "foreignField": "_id",
                "as": "professor_info"
            }
        },
        # Join com 'usuarios' para buscar os alunos
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "alunos_ids",
                "foreignField": "_id",
                "as": "alunos_info"
            }
        },
        # Formata a saída para ser mais amigável
        {
            "$project": {
                "nome": 1,
                "descricao": 1,
                "horarios": 1,
                "categoria": 1,
                # $arrayElemAt pega o primeiro (e único) elemento do array retornado pelo $lookup
                "esporte": {"$arrayElemAt": ["$esporte_info", 0]},
                "professor": {"$arrayElemAt": ["$professor_info", 0]},
                "alunos": "$alunos_info"
            }
        },
        # Projeta novamente para limpar os campos internos (como senha_hash) do professor e alunos
        {
            "$project": {
                "nome": 1,
                "descricao": 1,
                "horarios": 1,
                "categoria": 1,
                "esporte._id": 1,
                "esporte.nome": 1,
                "professor._id": 1,
                "professor.nome_completo": 1,
                "professor.email": 1,
                "alunos._id": 1,
                "alunos.nome_completo": 1,
                "alunos.email": 1
            }
        }
    ])
    return pipeline

def listar_turmas():
    """
    Lista todas as turmas com informações do esporte, professor e alunos populadas.
    """
    pipeline = _get_aggregation_pipeline()
    return list(mongo.db.turmas.aggregate(pipeline))

def listar_turmas_filtradas(filtros):
    """
    Lista turmas com base em filtros de esporte e categoria.
    """
    query = {}
    if 'esporte_id' in filtros:
        query['esporte_id'] = ObjectId(filtros['esporte_id'])
    if 'categoria' in filtros:
        query['categoria'] = filtros['categoria']
    
    # Simplesmente busca os documentos que correspondem ao filtro
    turmas = list(mongo.db.turmas.find(query))
    return turmas

def encontrar_turma_por_id(turma_id):
    """
    Encontra uma turma específica pelo ID, com dados populados.
    """
    try:
        pipeline = _get_aggregation_pipeline(turma_id)
        resultado = list(mongo.db.turmas.aggregate(pipeline))
        return resultado[0] if resultado else None
    except Exception:
        return None

def atualizar_turma(turma_id, dados_atualizacao):
    """
    Atualiza os dados de uma turma.
    """
    try:
        obj_id = ObjectId(turma_id)
    except Exception:
        raise ValueError("ID de turma inválido.")

    update_fields = {}
    
    # Adiciona campos permitidos para atualização
    campos_permitidos = ['nome', 'descricao', 'horarios', 'categoria']
    for campo in campos_permitidos:
        if campo in dados_atualizacao:
            update_fields[campo] = dados_atualizacao[campo]
            
    # Validação especial para professor_id e esporte_id
    if 'professor_id' in dados_atualizacao:
        _validar_ids_usuarios(dados_atualizacao['professor_id'], []) # Valida só o professor
        update_fields['professor_id'] = ObjectId(dados_atualizacao['professor_id'])
    if 'esporte_id' in dados_atualizacao:
        esporte_obj_id = ObjectId(dados_atualizacao['esporte_id'])
        if not mongo.db.esportes.find_one({"_id": esporte_obj_id}):
                raise ValueError("Esporte com o ID fornecido não encontrado.")
        update_fields['esporte_id'] = esporte_obj_id

    if not update_fields:
        return 0

    resultado = mongo.db.turmas.update_one({"_id": obj_id}, {"$set": update_fields})
    return resultado.modified_count

def deletar_turma(turma_id):
    """
    Deleta uma turma permanentemente.
    Aviso: Em um sistema de produção, verificaríamos se existem aulas ou outros
    dados associados antes de permitir a exclusão (regra de negócio).
    """
    try:
        obj_id = ObjectId(turma_id)
        resultado = mongo.db.turmas.delete_one({"_id": obj_id})
        return resultado.deleted_count
    except Exception:
        return 0
        
def adicionar_aluno(turma_id, aluno_id):
    """Adiciona um aluno a uma turma, evitando duplicatas."""
    # Valida se o aluno existe, está ativo e tem o perfil correto
    aluno = mongo.db.usuarios.find_one({"_id": ObjectId(aluno_id), "perfil": "aluno", "ativo": True})
    if not aluno:
        raise ValueError("Aluno não encontrado, inativo ou com perfil incorreto.")

    resultado = mongo.db.turmas.update_one(
        {"_id": ObjectId(turma_id)},
        {"$addToSet": {"alunos_ids": ObjectId(aluno_id)}} # $addToSet não adiciona se o ID já existir no array
    )
    return resultado.modified_count

def remover_aluno(turma_id, aluno_id):
    """Remove um aluno de uma turma."""
    resultado = mongo.db.turmas.update_one(
        {"_id": ObjectId(turma_id)},
        {"$pull": {"alunos_ids": ObjectId(aluno_id)}} # $pull remove a instância do item do array
    )
    return resultado.modified_count

