from app import mongo
from bson import ObjectId
import datetime
from pymongo import UpdateOne
from dateutil.relativedelta import relativedelta

def criar_aula(dados_aula):
    """Cria uma nova aula para uma turma em uma data específica."""
    turma_id = ObjectId(dados_aula['turma_id'])
    
    # Valida se a turma existe
    turma = mongo.db.turmas.find_one({"_id": turma_id})
    if not turma:
        raise ValueError("Turma não encontrada.")

    nova_aula = {
        "turma_id": turma_id,
        "data": datetime.datetime.fromisoformat(dados_aula['data']),
        "status": "agendada",
        "observacoes": dados_aula.get("observacoes", ""),
        "data_criacao": datetime.datetime.utcnow()
    }
    resultado = mongo.db.aulas.insert_one(nova_aula)
    return str(resultado.inserted_id)

def listar_aulas_por_turma(turma_id):
    """Lista todas as aulas de uma turma específica."""
    return list(mongo.db.aulas.find({"turma_id": ObjectId(turma_id)}).sort("data", -1))

def buscar_detalhes_aula(aula_id):
    """
    Busca uma aula e popula os dados da turma, alunos e suas presenças.
    Esta é uma query complexa, mas entrega tudo que o frontend precisa de uma vez.
    """
    pipeline = [
        {"$match": {"_id": ObjectId(aula_id)}},
        # 1. Obter dados da Turma
        {"$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma"}},
        {"$unwind": "$turma"},
        # 2. Obter a lista de alunos da Turma
        {"$lookup": {"from": "usuarios", "localField": "turma.alunos_ids", "foreignField": "_id", "as": "alunos"}},
        # 3. Obter os registros de presença para esta aula
        {"$lookup": {"from": "presencas", "localField": "_id", "foreignField": "aula_id", "as": "registros_presenca"}},
        # 4. Projetar e mesclar os dados
        {
            "$project": {
                "data": 1, "status": 1, "observacoes": 1, "turma_id": 1,
                "turma_nome": "$turma.nome",
                "alunos": {
                    "$map": {
                        "input": "$alunos",
                        "as": "aluno",
                        "in": {
                            "_id": "$$aluno._id",
                            "nome_completo": "$$aluno.nome_completo",
                            # Encontra a presença do aluno atual
                            "presenca": {
                                "$let": {
                                    "vars": {
                                        "presenca_rec": {"$arrayElemAt": [
                                            {"$filter": {"input": "$registros_presenca", "as": "rp", "cond": {"$eq": ["$$rp.aluno_id", "$$aluno._id"]}}},
                                            0
                                        ]}
                                    },
                                    "in": { # Retorna o objeto de presença completo
                                        "presenca_id": "$$presenca_rec._id",
                                        "status": {"$ifNull": ["$$presenca_rec.status", "pendente"]},
                                        "observacao": "$$presenca_rec.observacao"
                                    }
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

def marcar_presenca_lote(aula_id, lista_presencas):
    """
    Cria ou atualiza múltiplos registros de presença para uma aula de forma eficiente.
    """
    aula_obj_id = ObjectId(aula_id)
    agora = datetime.datetime.utcnow()
    
    # Prepara uma lista de operações de 'update' com 'upsert=True'
    # Upsert: se o registro existir, atualiza; se não, cria.
    operacoes = []
    for presenca in lista_presencas:
        aluno_obj_id = ObjectId(presenca['aluno_id'])
        operacoes.append(
            UpdateOne(
                {"aula_id": aula_obj_id, "aluno_id": aluno_obj_id},
                {
                    "$set": {
                        "status": presenca['status'],
                        "data_registro": agora
                    }
                },
                upsert=True
            )
        )

    if not operacoes:
        return 0

    resultado = mongo.db.presencas.bulk_write(operacoes)
    
    # Também atualizamos o status da aula para "realizada"
    mongo.db.aulas.update_one({"_id": aula_obj_id}, {"$set": {"status": "realizada"}})
    
    return resultado.upserted_count + resultado.modified_count

def listar_aulas_por_data(data_filtro):
    """
    Lista todas as aulas de uma data específica com dados agregados da turma e presença.
    """
    # Define o início e o fim do dia para a consulta
    inicio_dia = datetime.datetime.combine(data_filtro.date(), datetime.time.min)
    fim_dia = datetime.datetime.combine(data_filtro.date(), datetime.time.max)

    pipeline = [
        {
            "$match": {
                "data": {"$gte": inicio_dia, "$lte": fim_dia}
            }
        },
        {
            "$lookup": {"from": "turmas", "localField": "turma_id", "foreignField": "_id", "as": "turma"}
        },
        {"$unwind": "$turma"},
        {
            "$lookup": {"from": "esportes", "localField": "turma.esporte_id", "foreignField": "_id", "as": "esporte"}
        },
        {"$unwind": "$esporte"},
        {
            "$lookup": {
                "from": "presencas",
                "localField": "_id",
                "foreignField": "aula_id",
                "as": "presencas"
            }
        },
        {
            "$project": {
                "data": 1,
                "status": 1,
                "turma_nome": "$turma.nome",
                "esporte_nome": "$esporte.nome",
                "total_alunos_na_turma": {"$size": "$turma.alunos_ids"},
                "total_presentes": {
                    "$size": {
                        "$filter": {
                            "input": "$presencas",
                            "as": "presenca",
                            "cond": {"$eq": ["$$presenca.status", "presente"]}
                        }
                    }
                }
            }
        }
    ]
    return list(mongo.db.aulas.aggregate(pipeline))

def listar_turmas_filtradas(filtros):
    """
    Lista turmas com base em filtros de esporte e categoria.
    """
    query = {}
    if 'esporte_id' in filtros:
        query['esporte_id'] = ObjectId(filtros['esporte_id'])
    if 'categoria' in filtros:
        query['categoria'] = filtros['categoria']
        
    # Usamos o pipeline para popular os dados do professor, como na listagem geral
    pipeline = [
        {"$match": query},
        # Adicione os estágios de $lookup e $project do _get_aggregation_pipeline aqui
        # para retornar os dados completos da turma.
        # (Para ser breve, omitido aqui, mas copie os estágios de _get_aggregation_pipeline)
    ]

    # Temporariamente, uma busca mais simples para validar a lógica:
    turmas = list(mongo.db.turmas.find(query))
    return turmas

def agendar_aulas_para_turma(turma_id):
    """
    Gera as aulas para uma turma para o próximo mês,
    com base nos horários cadastrados na turma.
    """
    turma = mongo.db.turmas.find_one({"_id": ObjectId(turma_id)})
    if not turma or not turma.get('horarios'):
        raise ValueError("Turma não encontrada ou não possui horários cadastrados.")

    hoje = datetime.date.today()
    data_inicio = hoje
    data_fim = hoje + relativedelta(months=1)
    
    aulas_criadas = 0
    dias_semana_map = {
        "segunda": 0, "terca": 1, "quarta": 2, "quinta": 3, "sexta": 4, "sabado": 5, "domingo": 6
    }

    # Itera por cada dia no próximo mês
    data_atual = data_inicio
    while data_atual <= data_fim:
        dia_da_semana_numero = data_atual.weekday()
        
        for horario in turma['horarios']:
            dia_semana_turma = horario.get('dia_semana')
            hora_inicio_str = horario.get('hora_inicio')

            # ======================= CORREÇÃO PRINCIPAL AQUI =======================
            # 1. Pula este horário se o dia ou a hora de início não estiverem definidos
            if not dia_semana_turma or not hora_inicio_str:
                continue

            # 2. Verifica se o dia da semana corresponde
            if dia_da_semana_numero == dias_semana_map.get(dia_semana_turma):
                try:
                    # 3. Converte a hora de forma segura
                    hora, minuto = map(int, hora_inicio_str.split(':'))
                    data_hora_aula = datetime.datetime.combine(data_atual, datetime.time(hour=hora, minute=minuto))
                except (ValueError, TypeError):
                    # Pula se o formato da hora for inválido (ex: '')
                    continue

                # Verifica se uma aula para esta turma neste dia e hora já existe
                aula_existente = mongo.db.aulas.find_one({
                    "turma_id": ObjectId(turma_id),
                    "data": data_hora_aula
                })

                if not aula_existente:
                    nova_aula = {
                        "turma_id": ObjectId(turma_id),
                        "data": data_hora_aula,
                        "status": "agendada",
                        "observacoes": ""
                    }
                    mongo.db.aulas.insert_one(nova_aula)
                    aulas_criadas += 1
        
        data_atual += datetime.timedelta(days=1)
        
    return aulas_criadas