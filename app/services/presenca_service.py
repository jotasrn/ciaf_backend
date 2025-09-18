from bson import ObjectId
from app import mongo
from datetime import datetime
from flask import current_app

def marcar_presenca(aula_id, aluno_id, status):
    """
    Registra ou atualiza a presença de um aluno em uma aula específica.
    Também atualiza o status da aula para 'Realizada'.
    """
    try:
        aula_obj_id = ObjectId(aula_id)
        aluno_obj_id = ObjectId(aluno_id)
    except Exception as e:
        current_app.logger.error(f"Erro de conversão de ID ao marcar presença: {e}")
        raise ValueError("ID de aula ou aluno inválido.")

    # Verifica se a aula e o aluno existem e se o aluno pertence à turma da aula
    aula = mongo.db.aulas.find_one({"_id": aula_obj_id})
    if not aula:
        raise ValueError("Aula não encontrada.")

    turma = mongo.db.turmas.find_one({"_id": aula.get('turma_id')})
    if not turma:
        raise ValueError("Turma associada à aula não foi encontrada.")

    if aluno_obj_id not in turma.get('alunos_ids', []):
        raise ValueError("O aluno não pertence à turma desta aula.")

    # Atualiza ou insere o registro de presença
    filtro = {"aula_id": aula_obj_id, "aluno_id": aluno_obj_id}
    dados_atualizacao = {
        "$set": {
            "status": status,
            "data_modificacao": datetime.utcnow()
        },
        "$setOnInsert": {
            "aula_id": aula_obj_id,
            "aluno_id": aluno_obj_id,
            "turma_id": aula.get('turma_id')
        }
    }
    
    resultado = mongo.db.presencas.update_one(filtro, dados_atualizacao, upsert=True)
    
    mongo.db.aulas.update_one(
        {"_id": aula_obj_id},
        {"$set": {"status": "Realizada"}}
    )

    current_app.logger.info(f"Presença marcada para aluno {aluno_id} na aula {aula_id} com status '{status}'. Status da aula atualizado para 'Realizada'.")
    
    return resultado.modified_count > 0 or resultado.upserted_id is not None

def obter_presencas_por_aula(aula_id):
    """
    Obtém a lista de alunos e seus status de presença para uma aula específica.
    """
    try:
        aula_obj_id = ObjectId(aula_id)
    except Exception:
        raise ValueError("ID de aula inválido.")

    pipeline = [
        {"$match": {"_id": aula_obj_id}},
        {"$lookup": {
            "from": "turmas",
            "localField": "turma_id",
            "foreignField": "_id",
            "as": "turma_info"
        }},
        {"$unwind": "$turma_info"},
        {"$lookup": {
            "from": "usuarios",
            "localField": "turma_info.alunos_ids",
            "foreignField": "_id",
            "as": "alunos"
        }},
        {"$unwind": "$alunos"},
        {"$lookup": {
            "from": "presencas",
            "let": {"aluno_id": "$alunos._id", "aula_id": "$_id"},
            "pipeline": [
                {"$match": {
                    "$expr": {
                        "$and": [
                            {"$eq": ["$aluno_id", "$$aluno_id"]},
                            {"$eq": ["$aula_id", "$$aula_id"]}
                        ]
                    }
                }}
            ],
            "as": "presenca_info"
        }},
        {"$project": {
            "_id": 0,
            "id_aluno": "$alunos._id",
            "nome_aluno": "$alunos.nome_completo",
            "status": {"$ifNull": [{"$arrayElemAt": ["$presenca_info.status", 0]}, "pendente"]}
        }}
    ]

    alunos_chamada = list(mongo.db.aulas.aggregate(pipeline))
    return alunos_chamada