# app/services/aula_service.py

from app import mongo, timezone
from bson import ObjectId
from datetime import datetime, time
import calendar
from pymongo import UpdateOne
from flask import current_app

# --- FUNÇÕES DE LÓGICA DE NEGÓCIO ---

def agendar_aulas_para_turma(turma_id):
    """
    Gera as aulas para o mês corrente com base nos horários de uma turma.
    Esta função é IDEMPOTENTE: ela verifica se a aula já existe antes de criá-la.
    """
    try:
        turma_obj_id = ObjectId(turma_id)
        turma = mongo.db.turmas.find_one({"_id": turma_obj_id})
        if not turma or not turma.get('horarios'):
            current_app.logger.warning(f"Turma {turma_id} não encontrada ou sem horários.")
            return 0

        dias_semana_map = {
            'segunda': 0, 'terca': 1, 'quarta': 2, 'quinta': 3, 
            'sexta': 4, 'sabado': 5, 'domingo': 6
        }
        
        hoje = datetime.now(timezone)
        ano, mes = hoje.year, hoje.month
        num_dias = calendar.monthrange(ano, mes)[1]
        
        operacoes = []
        for dia in range(1, num_dias + 1):
            data_atual = datetime(ano, mes, dia)
            dia_da_semana_num = data_atual.weekday()

            for horario in turma.get('horarios', []):
                dia_semana_str = horario.get('dia_semana')
                if dias_semana_map.get(dia_semana_str) == dia_da_semana_num:
                    try:
                        hora_inicio_str = horario.get('hora_inicio')
                        if not hora_inicio_str: continue

                        hora, minuto = map(int, hora_inicio_str.split(':'))
                        data_aula = timezone.localize(data_atual.replace(hour=hora, minute=minuto))

                        # Prepara a operação para ser idempotente
                        filtro = {"turma_id": turma_obj_id, "data": data_aula}
                        update = {
                            "$setOnInsert": {
                                "turma_id": turma_obj_id,
                                "data": data_aula,
                                "status": "agendada", # Padronizando para minúsculas
                                "data_criacao": datetime.now(timezone)
                            }
                        }
                        operacoes.append(UpdateOne(filtro, update, upsert=True))
                    except (ValueError, TypeError) as e:
                        current_app.logger.error(f"Erro ao processar horário para turma {turma_id}: {e}")
                        continue
        
        if not operacoes:
            return 0
            
        resultado = mongo.db.aulas.bulk_write(operacoes)
        aulas_criadas = resultado.upserted_count
        current_app.logger.info(f"{aulas_criadas} nova(s) aula(s) agendada(s) para a turma {turma_id}.")
        return aulas_criadas
        
    except Exception as e:
        current_app.logger.error(f"Erro geral ao agendar aulas para turma {turma_id}: {e}")
        raise

def buscar_ou_criar_aula_por_data(turma_id, data_aula):
    """
    Busca uma aula para uma turma em uma data específica. Se não existir, cria dinamicamente.
    Versão robusta e independente de idioma.
    """
    turma_obj_id = ObjectId(turma_id)
    
    data_inicio_dia = timezone.localize(datetime.combine(data_aula.date(), time.min))
    data_fim_dia = timezone.localize(datetime.combine(data_aula.date(), time.max))

    filtro = { "turma_id": turma_obj_id, "data": {"$gte": data_inicio_dia, "$lt": data_fim_dia} }
    aula_existente = mongo.db.aulas.find_one(filtro)

    if aula_existente:
        return aula_existente

    # Se não existe, cria a aula
    turma = mongo.db.turmas.find_one({"_id": turma_obj_id})
    if not turma:
        raise ValueError("Turma não encontrada para criar a aula.")
    
    dias_map = { 0: 'segunda', 1: 'terca', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sabado', 6: 'domingo' }
    dia_semana_texto = dias_map.get(data_aula.weekday())

    hora_inicio_str = None
    for horario in turma.get('horarios', []):
        if horario and horario.get('dia_semana') == dia_semana_texto:
            hora_inicio_str = horario.get('hora_inicio')
            break
    
    if not hora_inicio_str:
        raise ValueError(f"A turma não tem horário definido para este dia da semana ({dia_semana_texto}).")

    try:
        hora, minuto = map(int, hora_inicio_str.split(':'))
        data_aula_com_hora = data_inicio_dia.replace(hour=hora, minute=minuto)
    except (ValueError, TypeError):
        raise ValueError(f"Formato de hora inválido ('{hora_inicio_str}') na turma {turma_id}.")

    nova_aula = {
        "turma_id": turma_obj_id,
        "data": data_aula_com_hora,
        "status": "agendada",
        "data_criacao": datetime.now(timezone)
    }
    resultado = mongo.db.aulas.insert_one(nova_aula)
    
    return mongo.db.aulas.find_one({"_id": resultado.inserted_id})


def marcar_presenca_lote(aula_id, lista_presencas):
    """Cria ou atualiza múltiplos registros de presença para uma aula."""
    aula_obj_id = ObjectId(aula_id)
    agora = datetime.now(timezone)
    
    operacoes = []
    for p in lista_presencas:
        if not p.get('aluno_id') or not p.get('status'):
            continue  # Ignora entradas inválidas

        operacao = UpdateOne(
            {"aula_id": aula_obj_id, "aluno_id": ObjectId(p['aluno_id'])},
            {
                "$set": {
                    "status": p['status'], 
                    "data_modificacao": agora
                },
                "$setOnInsert": {
                    "data_registro": agora
                }
            },
            upsert=True
        )
        operacoes.append(operacao)
        

    if not operacoes:
        return 0

    resultado = mongo.db.presencas.bulk_write(operacoes)
    
    mongo.db.aulas.update_one(
        {"_id": aula_obj_id},
        {"$set": {"status": "realizada", "data_modificacao": agora}}
    )
    
    return resultado.upserted_count + resultado.modified_count

# --- FUNÇÕES DE CONSULTA ---

def listar_aulas_por_turma(turma_id):
    """Lista todas as aulas de uma turma, ordenadas pela data mais recente."""
    return list(mongo.db.aulas.find({"turma_id": ObjectId(turma_id)}).sort("data", -1))

def listar_aulas_por_data(data_filtro):
    """Lista todas as aulas de uma data específica com dados agregados."""
    inicio_dia = timezone.localize(datetime.combine(data_filtro.date(), time.min))
    fim_dia = timezone.localize(datetime.combine(data_filtro.date(), time.max))
    pipeline = [
        {"$match": {"data": {"$gte": inicio_dia, "$lte": fim_dia}}},
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma"}},
        {"$unwind": "$turma"},
        {"$lookup": {"from": "esportes", "localField": "turma.esporte_id", "foreignField": "_id", "as": "esporte"}},
        {"$unwind": "$esporte"},
        {"$lookup": {"from": "presencas", "localField": "_id", "foreignField": "aula_id", "as": "presencas"}},
        {
            "$project": {
                "data": 1, "status": 1, "turma_nome": "$turma.nome", "esporte_nome": "$esporte.nome",
                "total_alunos_na_turma": {"$size": "$turma.alunos_ids"},
                "total_presentes": {"$size": {"$filter": {"input": "$presencas", "as": "p", "cond": {"$eq": ["$$p.status", "presente"]}}}}
            }
        }
    ]
    return list(mongo.db.aulas.aggregate(pipeline))

def buscar_detalhes_aula(aula_id):
    """
    Busca uma aula e popula todos os dados necessários para exibição ou exportação.
    Esta é a versão definitiva e mais robusta.
    """
    pipeline = [
        {"$match": {"_id": ObjectId(aula_id)}},
        # Join com Turmas
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma_info"}},
        {"$unwind": "$turma_info"},
        # Join com Esportes a partir da turma
        {"$lookup": {"from": "esportes", "localField": "turma_info.esporte_id", "foreignField": "_id", "as": "esporte_info"}},
        {"$unwind": {"path": "$esporte_info", "preserveNullAndEmptyArrays": True}},
        # Join com Professor a partir da turma
        {"$lookup": {"from": "usuarios", "localField": "turma_info.professor_id", "foreignField": "_id", "as": "professor_info"}},
        {"$unwind": {"path": "$professor_info", "preserveNullAndEmptyArrays": True}},
        # Join com os Alunos da turma
        {"$lookup": {"from": "usuarios", "localField": "turma_info.alunos_ids", "foreignField": "_id", "as": "alunos_info"}},
        # Projeta os campos necessários no formato final
        {
            "$project": {
                "data": 1,
                "status": 1,
                "turma_id": 1,
                "turma_nome": "$turma_info.nome",
                "esporte": "$esporte_info.nome",
                "categoria": "$turma_info.categoria",
                "professor": "$professor_info.nome_completo",
                "alunos": {
                    "$map": {
                        "input": "$alunos_info",
                        "as": "aluno",
                        "in": {
                            "_id": "$$aluno._id",
                            "nome_completo": "$$aluno.nome_completo",
                            "presenca": {
                                "$let": {
                                    "vars": {
                                        "presenca_aluno": {
                                            "$filter": {
                                                "input": "$presencas",
                                                "as": "p",
                                                "cond": {"$eq": ["$$p.aluno_id", "$$aluno._id"]}
                                            }
                                        }
                                    },
                                    "in": {"$arrayElemAt": ["$$presenca_aluno", 0]}
                                }
                            }
                        }
                    }
                }
            }
        },
        {"$lookup": {"from": "presencas", "localField": "_id", "foreignField": "aula_id", "as": "presencas_gerais"}},
        {
            "$addFields": {
                "alunos": {
                    "$map": {
                        "input": "$alunos",
                        "as": "aluno",
                        "in": {
                            "_id": "$$aluno._id",
                            "nome_completo": "$$aluno.nome_completo",
                            "presenca": {
                                "$let": {
                                    "vars": {
                                        "presenca_aluno": {
                                            "$filter": {
                                                "input": "$presencas_gerais",
                                                "as": "p",
                                                "cond": {"$eq": ["$$p.aluno_id", "$$aluno._id"]}
                                            }
                                        }
                                    },
                                    "in": {"$arrayElemAt": ["$$presenca_aluno", 0]}
                                }
                            }
                        }
                    }
                }
            }
        }
    ]
    resultado = list(mongo.db.aulas.aggregate(pipeline))
    return resultado[0] if resultado else None
def listar_historico_aulas(data_filtro=None, nome_turma=None):
    """
    Busca no banco de dados um histórico de aulas com base nos filtros.
    Esta função agora está no lugar correto.
    """
    pipeline = []
    
    # Inicia a busca com um filtro base
    match_stage = {}
    if data_filtro:
        inicio_dia = timezone.localize(datetime.combine(data_filtro.date(), time.min))
        fim_dia = timezone.localize(datetime.combine(data_filtro.date(), time.max))
        match_stage['data'] = {'$gte': inicio_dia, '$lte': fim_dia}
    
    if match_stage:
        pipeline.append({"$match": match_stage})

    # Adiciona a junção com a coleção de turmas para obter o nome
    pipeline.extend([
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma_info"}},
        {"$unwind": "$turma_info"}
    ])

    if nome_turma:
        pipeline.append({
            "$match": {
                "turma_info.nome": {"$regex": nome_turma, "$options": "i"}
            }
        })
        
    pipeline.extend([
        {"$lookup": {"from": "presencas", "localField": "_id", "foreignField": "aula_id", "as": "presencas"}},
        {
            "$project": {
                "_id": 1,
                "data": "$data",
                "status": "$status",
                "turmaNome": "$turma_info.nome",
                "esporteNome": "$turma_info.esporte.nome",
                "totalAlunosNaTurma": {"$size": "$turma_info.alunos_ids"},
                "totalPresentes": {
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