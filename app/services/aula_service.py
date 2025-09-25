from app import mongo
from bson import ObjectId
from datetime import datetime, time, timedelta
import calendar
from pymongo import UpdateOne
from flask import current_app
from datetime import datetime, time

# Funções relacionadas à criação e agendamento de aulas
def criar_aula(dados_aula):
    """Cria uma nova aula para uma turma em uma data específica."""
    turma_id = ObjectId(dados_aula['turma_id'])
    
    turma = mongo.db.turmas.find_one({"_id": turma_id})
    if not turma:
        raise ValueError("Turma não encontrada.")

    nova_aula = {
        "turma_id": turma_id,
        "data": datetime.fromisoformat(dados_aula['data']),
        "status": "Agendada",
        "observacoes": dados_aula.get("observacoes", ""),
        "data_criacao": datetime.utcnow()
    }
    resultado = mongo.db.aulas.insert_one(nova_aula)
    return str(resultado.inserted_id)

def agendar_aulas_do_mes(turma_id):
    """
    Gera as aulas para o mês corrente com base nos horários de uma turma.
    Esta função é IDEMPOTENTE: ela verifica se a aula já existe antes de criá-la.
    """
    try:
        turma_obj_id = ObjectId(turma_id)
        turma = mongo.db.turmas.find_one({"_id": turma_obj_id})
        if not turma or not turma.get('horarios'):
            current_app.logger.warning(f"Turma {turma_id} não encontrada ou sem horários para agendamento.")
            return 0

        dias_semana_map = {
            'segunda': 0, 'terca': 1, 'quarta': 2, 'quinta': 3, 'sexta': 4, 'sabado': 5, 'domingo': 6
        }

        hoje = datetime.now()
        ano, mes = hoje.year, hoje.month
        num_dias = calendar.monthrange(ano, mes)[1]
        
        aulas_criadas = 0
        for dia in range(1, num_dias + 1):
            data_atual = datetime(ano, mes, dia)
            dia_da_semana_num = data_atual.weekday()

            for horario in turma['horarios']:
                dia_semana_str = horario.get('dia_semana')
                if dias_semana_map.get(dia_semana_str) == dia_da_semana_num:
                    try:
                        hora_inicio_str = horario.get('hora_inicio')
                        if not hora_inicio_str: continue

                        hora, minuto = map(int, hora_inicio_str.split(':'))
                        data_aula = data_atual.replace(hour=hora, minute=minuto, second=0, microsecond=0)

                        aula_existente = mongo.db.aulas.find_one({
                            "turma_id": turma_obj_id,
                            "data": data_aula
                        })

                        if not aula_existente:
                            nova_aula = {
                                "turma_id": turma_obj_id,
                                "data": data_aula,
                                "status": "Agendada",
                                "alunos_presentes": []
                            }
                            mongo.db.aulas.insert_one(nova_aula)
                            aulas_criadas += 1
                    except (ValueError, TypeError) as e:
                        current_app.logger.error(f"Erro ao processar horário para turma {turma_id}: {e}")
                        continue
        
        current_app.logger.info(f"{aulas_criadas} nova(s) aula(s) criada(s) para a turma {turma_id} no mês {mes}/{ano}.")
        return aulas_criadas
    except Exception as e:
        current_app.logger.error(f"Erro geral ao agendar aulas para turma {turma_id}: {e}")
        raise

# Funções relacionadas à busca de aulas
def listar_aulas_por_turma(turma_id):
    """Lista todas as aulas de uma turma específica, ordenadas pela data mais recente."""
    return list(mongo.db.aulas.find({"turma_id": ObjectId(turma_id)}).sort("data", -1))

def listar_aulas_por_data(data_filtro):
    """Lista todas as aulas de uma data específica com dados agregados."""
    inicio_dia = datetime.combine(data_filtro.date(), time.min)
    fim_dia = datetime.combine(data_filtro.date(), time.max)
    pipeline = [
        {"$match": {"data": {"$gte": inicio_dia, "$lte": fim_dia}}},
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma"}},
        {"$unwind": "$turma"},
        {"$lookup": {"from": "esportes", "localField": "turma.esporte_id", "foreignField": "_id", "as": "esporte"}},
        {"$unwind": "$esporte"},
        {"$lookup": {"from": "presencas", "localField": "_id", "foreignField": "aula_id", "as": "presencas"}},
        {
            "$project": {
                "data": 1, "status": 1,
                "turma_nome": "$turma.nome",
                "esporte_nome": "$esporte.nome",
                "total_alunos_na_turma": {"$size": "$turma.alunos_ids"},
                "total_presentes": {
                    "$size": {
                        "$filter": {
                            "input": "$presencas", "as": "p", "cond": {"$eq": ["$$p.status", "presente"]}
                        }
                    }
                }
            }
        }
    ]
    return list(mongo.db.aulas.aggregate(pipeline))

def buscar_detalhes_aula(aula_id):
    """
    Busca uma aula e popula TODOS os dados necessários para relatórios e visualização.
    Esta é uma query de agregação robusta que lida com todos os relacionamentos.
    """
    try:
        aula_obj_id = ObjectId(aula_id)
    except Exception:
        raise ValueError("ID de aula inválido.")

    pipeline = [
        # 1. Encontra a aula específica
        {"$match": {"_id": aula_obj_id}},
        
        # 2. Junta os dados da Turma
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma_info"}},
        {"$unwind": "$turma_info"},

        # 3. Junta os dados do Esporte (a partir da turma)
        {"$lookup": {"from": "esportes", "localField": "turma_info.esporte_id", "foreignField": "_id", "as": "esporte_info"}},
        {"$unwind": {"path": "$esporte_info", "preserveNullAndEmptyArrays": True}},

        # 4. Junta os dados do Professor (a partir da turma)
        {"$lookup": {"from": "usuarios", "localField": "turma_info.professor_id", "foreignField": "_id", "as": "professor_info"}},
        {"$unwind": {"path": "$professor_info", "preserveNullAndEmptyArrays": True}},
        
        # 5. Desagrupa os IDs dos alunos para processar um por um
        {"$unwind": {"path": "$turma_info.alunos_ids", "preserveNullAndEmptyArrays": True}},
        
        # 6. Junta os dados de cada Aluno
        {"$lookup": {"from": "usuarios", "localField": "turma_info.alunos_ids", "foreignField": "_id", "as": "aluno_info"}},
        {"$unwind": {"path": "$aluno_info", "preserveNullAndEmptyArrays": True}},
        
        # 7. Junta o registro de Presença para cada aluno nesta aula
        {"$lookup": {
            "from": "presencas",
            "let": {"aluno_id": "$aluno_info._id", "aula_id": "$_id"},
            "pipeline": [
                {"$match": {"$expr": {"$and": [{"$eq": ["$aluno_id", "$$aluno_id"]}, {"$eq": ["$aula_id", "$$aula_id"]}]}}},
                {"$limit": 1}
            ],
            "as": "presenca_info"
        }},
        {"$unwind": {"path": "$presenca_info", "preserveNullAndEmptyArrays": True}},
        
        # 8. Agrupa tudo de volta, criando uma lista de alunos com seus status
        {"$group": {
            "_id": "$_id",
            "data": {"$first": "$data"},
            "status": {"$first": "$status"},
            "turma_nome": {"$first": "$turma_info.nome"},
            "categoria": {"$first": "$turma_info.categoria"},
            "esporte": {"$first": "$esporte_info.nome"},
            "professor": {"$first": "$professor_info.nome_completo"},
            "alunos": {
                "$push": {
                    "nome_completo": "$aluno_info.nome_completo",
                    "presenca": {
                        "status": {"$ifNull": ["$presenca_info.status", "pendente"]},
                        "observacao": {"$ifNull": ["$presenca_info.observacao", ""]}
                    }
                }
            }
        }}
    ]
    
    resultado = list(mongo.db.aulas.aggregate(pipeline))
    return resultado[0] if resultado else None

# Funções relacionadas à presença
def marcar_presenca_lote(aula_id, lista_presencas):
    """
    Cria ou atualiza múltiplos registros de presença para uma aula de forma robusta.
    """
    try:
        aula_obj_id = ObjectId(aula_id)
    except Exception:
        raise ValueError(f"ID da aula inválido: {aula_id}")

    aula = mongo.db.aulas.find_one({"_id": aula_obj_id}, {"turma_id": 1})
    if not aula:
        raise ValueError(f"Aula com ID {aula_id} não foi encontrada.")
    turma_id = aula.get('turma_id')
    if not turma_id:
        raise ValueError(f"A aula {aula_id} não está vinculada a nenhuma turma.")

    agora = datetime.utcnow()
    operacoes = []

    for presenca in lista_presencas:
        aluno_id_str = presenca.get('aluno_id')
        status = presenca.get('status')
        if not aluno_id_str or not status:
            current_app.logger.warning(f"Registro de presença ignorado: {presenca}")
            continue
        
        try:
            aluno_obj_id = ObjectId(aluno_id_str)
        except Exception:
            current_app.logger.warning(f"ID de aluno inválido ignorado: {aluno_id_str}")
            continue

        operacao = UpdateOne(
            {"aula_id": aula_obj_id, "aluno_id": aluno_obj_id},
            {
                "$set": {
                    "status": status,
                    "data_modificacao": agora
                },
                "$setOnInsert": {
                    "turma_id": turma_id,
                    "data_criacao": agora
                }
            },
            upsert=True
        )
        operacoes.append(operacao)

    if not operacoes:
        return 0

    resultado = mongo.db.presencas.bulk_write(operacoes)
    
    # --- CORREÇÃO APLICADA AQUI ---
    # O status agora é enviado em minúsculas para corresponder à regra do banco.
    mongo.db.aulas.update_one(
        {"_id": aula_obj_id},
        {"$set": {"status": "realizada", "data_modificacao": agora}}
    )
    
    return resultado.upserted_count + resultado.modified_count

def listar_historico_aulas(data_filtro=None, nome_turma_filtro=None):
    """
    Busca um histórico de aulas já realizadas, com filtros.
    """
    pipeline = []

    match_stage = {"status": "realizada"}

    if data_filtro:
        inicio_dia = datetime.combine(data_filtro.date(), time.min)
        fim_dia = datetime.combine(data_filtro.date(), time.max)
        match_stage['data'] = {"$gte": inicio_dia, "$lte": fim_dia}
    
    pipeline.append({"$match": match_stage})

    pipeline.extend([
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma"}},
        {"$unwind": "$turma"},
    ])

    if nome_turma_filtro:
        pipeline.append({"$match": {"turma.nome": {"$regex": nome_turma_filtro, "$options": "i"}}})

    pipeline.extend([
        {"$lookup": {"from": "esportes", "localField": "turma.esporte_id", "foreignField": "_id", "as": "esporte"}},
        {"$unwind": "$esporte"},
        {"$lookup": {"from": "presencas", "localField": "_id", "foreignField": "aula_id", "as": "presencas"}},
        {
            "$project": {
                "data": 1, "status": 1,
                "turma_nome": "$turma.nome",
                "esporte_nome": "$esporte.nome",
                "total_alunos_na_turma": {"$size": "$turma.alunos_ids"},
                "total_presentes": {
                    "$size": {
                        "$filter": {
                            "input": "$presencas", "as": "p", "cond": {"$eq": ["$$p.status", "presente"]}
                        }
                    }
                }
            }
        },
        {"$sort": {"data": -1}} 
    ])

    return list(mongo.db.aulas.aggregate(pipeline))