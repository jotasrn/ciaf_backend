from bson import ObjectId
from pymongo.errors import WriteError
from flask import current_app
from app import mongo
from app.services import aula_service

def _validar_campos_obrigatorios(dados, campos):
    """
    Verifica se os campos obrigatórios estão presentes nos dados.
    É mais flexível para permitir listas vazias e strings vazias em contextos específicos.
    """
    campos_faltando = []
    for campo in campos:
        # Permite que 'horarios' e 'alunos_ids' sejam listas vazias, mas a chave deve existir
        if campo in ['horarios', 'alunos_ids']:
            if campo not in dados:
                campos_faltando.append(campo)
            continue # Pula para o próximo campo

        # Para outros campos, não permite valor vazio ou nulo
        if campo not in dados or dados[campo] == '' or dados[campo] is None:
            # Exceção para horários, onde hora_inicio e hora_fim podem ser vazios
            if campo in ['hora_inicio', 'hora_fim']:
                continue
            campos_faltando.append(campo)
    
    if campos_faltando:
        raise ValueError(f"Campos obrigatórios ausentes: {', '.join(campos_faltando)}")


def _converter_para_objectid(id_string, nome_campo):
    """Converte uma string para ObjectId, levantando erro se inválida."""
    if not id_string:
        raise ValueError(f"O campo '{nome_campo}' não pode ser vazio.")
    try:
        return ObjectId(id_string)
    except Exception:
        raise ValueError(f"O formato do '{nome_campo}' é inválido: {id_string}")

def _validar_dados_turma(dados):
    """Valida a estrutura e os tipos de dados para criar/atualizar uma turma."""
    campos_obrigatorios = ['nome', 'esporte_id', 'categoria', 'professor_id', 'alunos_ids', 'horarios']
    _validar_campos_obrigatorios(dados, campos_obrigatorios)

    if not isinstance(dados.get('horarios'), list) or not all(isinstance(h, dict) for h in dados.get('horarios', [])):
        raise ValueError("O campo 'horarios' deve ser uma lista de objetos (dicionários).")

    for horario in dados.get('horarios', []):
        # Para cada horário, 'dia_semana' é o único campo estritamente obrigatório
        _validar_campos_obrigatorios(horario, ['dia_semana'])


def _preparar_documento_turma(dados):
    """Prepara o dicionário de dados para inserção ou atualização no MongoDB."""
    documento = {
        'nome': dados['nome'],
        'categoria': dados['categoria'],
        'horarios': dados['horarios'],
        'esporte_id': _converter_para_objectid(dados['esporte_id'], 'esporte_id'),
        'professor_id': _converter_para_objectid(dados['professor_id'], 'professor_id'),
        'alunos_ids': [_converter_para_objectid(aluno_id, 'aluno_id') for aluno_id in dados.get('alunos_ids', [])]
    }
    return documento

# --- Lógica de Negócio ---

def criar_turma(dados):
    try:
        _validar_dados_turma(dados)
        dados_turma_para_inserir = _preparar_documento_turma(dados)
        resultado = mongo.db.turmas.insert_one(dados_turma_para_inserir)
        nova_turma_id = resultado.inserted_id
        current_app.logger.info(f"Turma '{dados['nome']}' criada com sucesso. ID: {nova_turma_id}")

        # Vinculações
        professor_id = str(dados_turma_para_inserir['professor_id'])
        alunos_ids = [str(aluno_id) for aluno_id in dados_turma_para_inserir['alunos_ids']]
        _vincular_professor_a_turmas(professor_id, [str(nova_turma_id)])
        _vincular_alunos_a_turma(alunos_ids, str(nova_turma_id))
        
        # ✅ LÓGICA AUTOMÁTICA ADICIONADA
        # Gera as aulas para o mês corrente assim que a turma é criada.
        aula_service.agendar_aulas_do_mes(str(nova_turma_id))

        return str(nova_turma_id)
    except Exception as e:
        current_app.logger.error(f"!!!!!!!!!! ERRO AO CRIAR TURMA !!!!!!!!!!\n{e}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise e
    except Exception as e:
        current_app.logger.error(f"!!!!!!!!!! ERRO INESPERADO AO CRIAR TURMA !!!!!!!!!!\n{e}\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise Exception(f"Ocorreu um erro inesperado: {e}")


def listar_turmas():
    """Lista todas as turmas com informações agregadas de esporte, professor e alunos."""
    pipeline = [
        {'$lookup': {'from': 'esportes', 'localField': 'esporte_id', 'foreignField': '_id', 'as': 'esporte'}},
        {'$lookup': {'from': 'usuarios', 'localField': 'professor_id', 'foreignField': '_id', 'as': 'professor'}},
        {'$lookup': {'from': 'usuarios', 'localField': 'alunos_ids', 'foreignField': '_id', 'as': 'alunos'}},
        {'$unwind': {'path': '$esporte', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$professor', 'preserveNullAndEmptyArrays': True}},
        {
            '$project': {
                'nome': 1, 'categoria': 1, 'horarios': 1,
                'esporte': {'_id': '$esporte._id', 'nome': '$esporte.nome'},
                'professor': {'_id': '$professor._id', 'nome_completo': '$professor.nome_completo'},
                'alunos': '$alunos',
                'total_alunos': {'$size': '$alunos_ids'}
            }
        }
    ]
    return list(mongo.db.turmas.aggregate(pipeline))

def buscar_turma_por_id(turma_id):
    """Busca uma turma específica pelo seu ID com dados agregados."""
    object_id = _converter_para_objectid(turma_id, "ID da Turma")
    pipeline = [
        {'$match': {'_id': object_id}},
        {'$lookup': {'from': 'esportes', 'localField': 'esporte_id', 'foreignField': '_id', 'as': 'esporte'}},
        {'$lookup': {'from': 'usuarios', 'localField': 'professor_id', 'foreignField': '_id', 'as': 'professor'}},
        {'$lookup': {'from': 'usuarios', 'localField': 'alunos_ids', 'foreignField': '_id', 'as': 'alunos'}},
        {'$unwind': {'path': '$esporte', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$professor', 'preserveNullAndEmptyArrays': True}},
        {
            '$project': {
                'nome': 1, 'categoria': 1, 'horarios': 1,
                'esporte': {'_id': '$esporte._id', 'nome': '$esporte.nome'},
                'professor': {'_id': '$professor._id', 'nome_completo': '$professor.nome_completo', 'email': '$professor.email'},
                'alunos': '$alunos'
            }
        }
    ]
    turmas = list(mongo.db.turmas.aggregate(pipeline))
    if not turmas:
        return None
    return turmas[0]

def atualizar_turma(turma_id, dados):
    """Atualiza os dados de uma turma."""
    object_id = _converter_para_objectid(turma_id, "ID da Turma")
    turma_antiga = mongo.db.turmas.find_one({'_id': object_id})
    if not turma_antiga:
        raise ValueError("Turma não encontrada.")

    # Mescla os dados antigos com os novos para não perder campos
    dados_completos = turma_antiga.copy()
    dados_completos.update(dados)
    
    # Converte os IDs de volta para string para validação, se necessário
    dados_completos['esporte_id'] = str(dados_completos['esporte_id'])
    dados_completos['professor_id'] = str(dados_completos['professor_id'])
    dados_completos['alunos_ids'] = [str(aid) for aid in dados_completos.get('alunos_ids', [])]


    _validar_dados_turma(dados_completos)
    dados_para_atualizar = _preparar_documento_turma(dados_completos)

    mongo.db.turmas.update_one({'_id': object_id}, {'$set': dados_para_atualizar})

    # Lógica de desvincular/vincular professor e alunos
    prof_antigo_id = str(turma_antiga.get('professor_id'))
    prof_novo_id = dados_completos.get('professor_id')
    if prof_antigo_id != prof_novo_id:
        if prof_antigo_id:
            _desvincular_professor_de_turmas(prof_antigo_id, [turma_id])
        if prof_novo_id:
            _vincular_professor_a_turmas(prof_novo_id, [turma_id])
            
    alunos_antigos_ids = {str(aid) for aid in turma_antiga.get('alunos_ids', [])}
    alunos_novos_ids = set(dados_completos.get('alunos_ids', []))

    alunos_a_remover = list(alunos_antigos_ids - alunos_novos_ids)
    alunos_a_adicionar = list(alunos_novos_ids - alunos_antigos_ids)

    if alunos_a_remover:
        _desvincular_alunos_de_turma(alunos_a_remover, turma_id)
    if alunos_a_adicionar:
        _vincular_alunos_a_turma(alunos_a_adicionar, turma_id)

    current_app.logger.info(f"Turma ID {turma_id} atualizada com sucesso.")
    return True

def deletar_turma(turma_id):
    object_id = _converter_para_objectid(turma_id, "ID da Turma")
    turma_deletada = mongo.db.turmas.find_one_and_delete({'_id': object_id})
    if not turma_deletada:
        raise ValueError("Turma não encontrada para deletar.")

    professor_id = str(turma_deletada.get('professor_id'))
    alunos_ids = [str(aid) for aid in turma_deletada.get('alunos_ids', [])]

    if professor_id:
        _desvincular_professor_de_turmas(professor_id, [turma_id])
    if alunos_ids:
        _desvincular_alunos_de_turma(alunos_ids, turma_id)

    current_app.logger.info(f"Turma ID {turma_id} e suas referências foram deletadas.")
    return True

# --- Funções de Vinculação ---
# (As funções de vinculação permanecem as mesmas)

def _vincular_professor_a_turmas(prof_id_str, turmas_ids_str):
    if not prof_id_str or not turmas_ids_str: return
    prof_obj_id = _converter_para_objectid(prof_id_str, "ID do Professor")
    turmas_obj_ids = [_converter_para_objectid(tid, "ID da Turma") for tid in turmas_ids_str]
    mongo.db.usuarios.update_one(
        {'_id': prof_obj_id},
        {'$addToSet': {'turmas_ids': {'$each': turmas_obj_ids}}}
    )

def _desvincular_professor_de_turmas(prof_id_str, turmas_ids_str):
    if not prof_id_str or not turmas_ids_str: return
    prof_obj_id = _converter_para_objectid(prof_id_str, "ID do Professor")
    turmas_obj_ids = [_converter_para_objectid(tid, "ID da Turma") for tid in turmas_ids_str]
    mongo.db.usuarios.update_one(
        {'_id': prof_obj_id},
        {'$pullAll': {'turmas_ids': turmas_obj_ids}}
    )

def _vincular_alunos_a_turma(alunos_ids_str, turma_id_str):
    if not alunos_ids_str or not turma_id_str: return
    alunos_obj_ids = [_converter_para_objectid(aid, "ID do Aluno") for aid in alunos_ids_str]
    turma_obj_id = _converter_para_objectid(turma_id_str, "ID da Turma")
    mongo.db.usuarios.update_many(
        {'_id': {'$in': alunos_obj_ids}},
        {'$addToSet': {'turma_id': turma_obj_id}} # Assume que um aluno só pode estar em uma turma por vez
    )

def _desvincular_alunos_de_turma(alunos_ids_str, turma_id_str):
    if not alunos_ids_str or not turma_id_str: return
    alunos_obj_ids = [_converter_para_objectid(aid, "ID do Aluno") for aid in alunos_ids_str]
    turma_obj_id = _converter_para_objectid(turma_id_str, "ID da Turma")
    mongo.db.usuarios.update_many(
        {'_id': {'$in': alunos_obj_ids}},
        {'$pull': {'turma_id': turma_obj_id}}
    )

def listar_turmas_por_professor(professor_id_str):
    """
    Lista as turmas de um professor específico com informações agregadas.
    """
    try:
        professor_obj_id = _converter_para_objectid(professor_id_str, "ID do Professor")
    except ValueError as e:
        current_app.logger.error(f"ID de professor inválido ao listar turmas: {e}")
        return []

    pipeline = [
        {'$match': {'professor_id': professor_obj_id}},  # Filtro principal
        {'$lookup': {
            'from': 'esportes', 
            'localField': 'esporte_id', 
            'foreignField': '_id', 
            'as': 'esporte'
        }},
        {'$lookup': {
            'from': 'usuarios', 
            'localField': 'professor_id', 
            'foreignField': '_id', 
            'as': 'professor'
        }},
        {'$lookup': {
            'from': 'usuarios', 
            'localField': 'alunos_ids', 
            'foreignField': '_id', 
            'as': 'alunos'
        }},
        {'$unwind': {'path': '$esporte', 'preserveNullAndEmptyArrays': True}},
        {'$unwind': {'path': '$professor', 'preserveNullAndEmptyArrays': True}},
        {
            '$project': {
                'nome': 1, 'categoria': 1, 'horarios': 1,
                'esporte': {'_id': '$esporte._id', 'nome': '$esporte.nome'},
                'professor': {'_id': '$professor._id', 'nome_completo': '$professor.nome_completo'},
                'alunos': {
                    '$map': {
                        'input': '$alunos',
                        'as': 'aluno',
                        'in': {'_id': '$$aluno._id', 'nome_completo': '$$aluno.nome_completo'}
                    }
                },
                'total_alunos': {'$size': '$alunos_ids'}
            }
        }
    ]
    
    turmas = list(mongo.db.turmas.aggregate(pipeline))
    current_app.logger.info(f"Encontradas {len(turmas)} turmas para o professor ID {professor_id_str}")
    return turmas