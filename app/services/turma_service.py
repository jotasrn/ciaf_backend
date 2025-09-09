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
    if professor_id:
        _validar_ids_usuarios(professor_id, alunos_ids)

    nova_turma = {
        "nome": dados_turma['nome'],
        "esporte_id": esporte_id,
        "categoria": dados_turma.get('categoria', 'Geral'),
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
        pipeline.append({"$match": {"_id": ObjectId(turma_id)}})

    pipeline.extend([
        {
            "$lookup": {
                "from": "esportes",
                "localField": "esporte_id",
                "foreignField": "_id",
                "as": "esporte_info"
            }
        },
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "professor_id",
                "foreignField": "_id",
                "as": "professor_info"
            }
        },
        {
            "$lookup": {
                "from": "usuarios",
                "localField": "alunos_ids",
                "foreignField": "_id",
                "as": "alunos_info"
            }
        },
        {
            "$project": {
                "nome": 1,
                "descricao": 1,
                "horarios": 1,
                "categoria": 1,
                "esporte": {"$arrayElemAt": ["$esporte_info", 0]},
                "professor": {"$arrayElemAt": ["$professor_info", 0]},
                "alunos": "$alunos_info"
            }
        },
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
    
    # Lista de campos que podem ser atualizados
    campos_permitidos = ['nome', 'descricao', 'horarios', 'categoria', 'alunos_ids']
    for campo in campos_permitidos:
        if campo in dados_atualizacao:
            if campo == 'alunos_ids':
                # Garante que os IDs dos alunos sejam convertidos para ObjectId
                update_fields[campo] = [ObjectId(aid) for aid in dados_atualizacao[campo]]
            else:
                update_fields[campo] = dados_atualizacao[campo]

    # Valida o professor_id APENAS se ele for enviado nos dados de atualização
    if 'professor_id' in dados_atualizacao and dados_atualizacao['professor_id']:
        professor_id = dados_atualizacao['professor_id']
        _validar_ids_usuarios(professor_id, []) # Valida só o professor
        update_fields['professor_id'] = ObjectId(professor_id)

    if not update_fields:
        return 0

    resultado = mongo.db.turmas.update_one({"_id": obj_id}, {"$set": update_fields})
    return resultado.modified_count

def deletar_turma(turma_id):
    """
    Deleta uma turma permanentemente.
    """
    try:
        obj_id = ObjectId(turma_id)
        resultado = mongo.db.turmas.delete_one({"_id": obj_id})
        return resultado.deleted_count
    except Exception:
        return 0
        
def adicionar_aluno(turma_id, aluno_id):
    """Adiciona um aluno a uma turma, evitando duplicatas."""
    aluno = mongo.db.usuarios.find_one({"_id": ObjectId(aluno_id), "perfil": "aluno", "ativo": True})
    if not aluno:
        raise ValueError("Aluno não encontrado, inativo ou com perfil incorreto.")

    resultado = mongo.db.turmas.update_one(
        {"_id": ObjectId(turma_id)},
        {"$addToSet": {"alunos_ids": ObjectId(aluno_id)}}
    )
    return resultado.modified_count

def remover_aluno(turma_id, aluno_id):
    """Remove um aluno de uma turma."""
    resultado = mongo.db.turmas.update_one(
        {"_id": ObjectId(turma_id)},
        {"$pull": {"alunos_ids": ObjectId(aluno_id)}}
    )
    return resultado.modified_count

def listar_turmas_por_professor(professor_id):
    """
    Busca no banco todas as turmas de um professor específico,
    usando o pipeline de agregação para popular os dados.
    """
    # Reutilizamos a lógica do pipeline, adicionando um filtro ($match) no início
    pipeline = _get_aggregation_pipeline()
    pipeline.insert(0, {"$match": {"professor_id": ObjectId(professor_id)}})

    return list(mongo.db.turmas.aggregate(pipeline))