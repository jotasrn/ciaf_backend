from flask import Blueprint, request, jsonify, send_file
from app.decorators.auth_decorators import role_required, admin_required
from app.services import aula_service, export_service
from app import mongo, timezone
from bson import ObjectId, json_util
from flask_jwt_extended import get_jwt_identity, get_jwt
import json
from flask import Blueprint, request, jsonify
import traceback
from flask_jwt_extended import get_jwt
from datetime import datetime


# Garante que o Blueprint está definido corretamente
aula_bp = Blueprint('aula_bp', __name__)

@aula_bp.before_request
def handle_aula_preflight():
    """
    Responde às requisições OPTIONS (CORS pre-flight) antes que elas
    cheguem aos decorators, evitando o erro de autenticação.
    """
    if request.method.upper() == 'OPTIONS':
        # Retorna uma resposta vazia e bem-sucedida.
        # O flask-cors cuidará de adicionar os cabeçalhos necessários.
        return '', 204
    
def _verificar_permissao_professor(turma_id):
    """
    Verifica se o usuário logado é o professor da turma ou um admin.
    Versão com LOGS DE DIAGNÓSTICO para depuração.
    """
    print("\n--- INICIANDO VERIFICAÇÃO DE PERMISSÃO ---")
    claims = get_jwt()
    
    if claims.get("perfil") == "admin":
        print("[DEBUG] Usuário é ADMIN. Permissão concedida.")
        print("--- FIM DA VERIFICAÇÃO ---")
        return True

    try:
        turma_obj_id = ObjectId(turma_id)
        print(f"[DEBUG] ID da Turma a ser verificado: {turma_obj_id}")
    except Exception:
        print(f"[ERRO] ID da Turma '{turma_id}' é inválido.")
        print("--- FIM DA VERIFICAÇÃO ---")
        return False

    turma = mongo.db.turmas.find_one({"_id": turma_obj_id})
    if not turma:
        print(f"[ERRO] Turma com ID '{turma_obj_id}' não encontrada no banco de dados.")
        print("--- FIM DA VERIFICAÇÃO ---")
        return False
        
    id_professor_logado = get_jwt_identity()
    print(f"[DEBUG] ID do Professor logado (do token JWT): {id_professor_logado}")

    id_professor_na_turma = None
    
    # Tentativa 1: Busca pelo campo novo e correto 'professor_id'
    if 'professor_id' in turma:
        id_professor_na_turma = turma.get('professor_id')
        print(f"[DEBUG] Encontrado campo 'professor_id': {id_professor_na_turma}")
    
    # Tentativa 2: Busca pelo formato antigo aninhado 'professor._id'
    elif 'professor' in turma and isinstance(turma.get('professor'), dict):
        id_professor_na_turma = turma.get('professor', {}).get('_id')
        print(f"[DEBUG] Encontrado campo aninhado 'professor._id': {id_professor_na_turma}")

    if not id_professor_na_turma:
        print("[ERRO] Não foi possível encontrar a referência do professor na turma (nem 'professor_id', nem 'professor._id').")
        print("--- FIM DA VERIFICAÇÃO ---")
        return False
    
    print(f"[DEBUG] ID do Professor na Turma (do banco): {id_professor_na_turma}")
    
    # Comparação final
    permissao_concedida = str(id_professor_na_turma) == id_professor_logado
    if permissao_concedida:
        print("[DEBUG] IDs correspondem. Permissão concedida.")
    else:
        print(f"[ERRO] IDs NÃO correspondem: Logado='{id_professor_logado}', Na Turma='{id_professor_na_turma}'. Acesso negado.")
    
    print("--- FIM DA VERIFICAÇÃO ---")
    return permissao_concedida


@aula_bp.route('/<string:aula_id>/presencas', methods=['POST'])
@role_required(roles=['admin', 'professor'])
def registrar_presencas(aula_id):
    aula = mongo.db.aulas.find_one({"_id": ObjectId(aula_id)})
    if not aula:
        return jsonify({"mensagem": "Aula não encontrada."}), 404

    claims = get_jwt()
    user_role = claims.get("perfil")

    if aula.get('status', '').lower() == 'realizada' and user_role != 'admin':
        return jsonify({"mensagem": "Esta chamada já foi finalizada."}), 403

    # A verificação de segurança agora nos dará logs detalhados
    if not _verificar_permissao_professor(str(aula.get('turma_id'))):
        return jsonify({"mensagem": "Acesso negado: você não é o professor desta turma."}), 403 

    lista_presencas = request.get_json()
    if not isinstance(lista_presencas, list):
        return jsonify({"mensagem": "O corpo da requisição deve ser uma lista."}), 400

    try:
        total_modificado = aula_service.marcar_presenca_lote(aula_id, lista_presencas)
        return jsonify({"mensagem": f"Presença registrada para {total_modificado} aluno(s).", "aula_status": "Realizada"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"mensagem": "Erro interno ao registrar presença.", "detalhes": str(e)}), 500

@aula_bp.route('/', methods=['POST'])
@role_required(roles=['admin', 'professor'])
def agendar_aula():
    dados = request.get_json()
    if not dados or not all(k in dados for k in ('turma_id', 'data')):
        return jsonify({"mensagem": "turma_id e data são obrigatórios."}), 400

    if not _verificar_permissao_professor(dados['turma_id']):
        return jsonify({"mensagem": "Acesso negado: você não é o professor desta turma."}), 403

    try:
        aula_id = aula_service.criar_aula(dados)
        return jsonify({"mensagem": "Aula agendada com sucesso!", "aula_id": aula_id}), 201
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400

@aula_bp.route('/turma/<string:turma_id>', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def get_aulas_por_turma(turma_id):
    if not _verificar_permissao_professor(turma_id):
        return jsonify({"mensagem": "Acesso negado."}), 403
    
    aulas = aula_service.listar_aulas_por_turma(turma_id)
    return json.loads(json_util.dumps(aulas)), 200


@aula_bp.route('/<string:aula_id>/detalhes', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def get_detalhes_aula(aula_id):
    aula = mongo.db.aulas.find_one({"_id": ObjectId(aula_id)})
    if not aula:
        return jsonify({"mensagem": "Aula não encontrada."}), 404

    if not _verificar_permissao_professor(str(aula.get('turma_id'))):
        return jsonify({"mensagem": "Acesso negado."}), 403
        
    detalhes = aula_service.buscar_detalhes_aula(aula_id)
    return json.loads(json_util.dumps(detalhes)), 200

@aula_bp.route('/por-data', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def get_aulas_do_dia():
    """
    [ADMIN, PROFESSOR] Retorna as aulas de um dia específico.
    """
    data_str = request.args.get('data')
    data_filtro = None
    
    if data_str:
        try:
            data_filtro = datetime.strptime(data_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"mensagem": "Formato de data inválido. Use AAAA-MM-DD."}), 400
    else:
        data_filtro = datetime.now()

    aulas = aula_service.listar_aulas_por_data(data_filtro)
    return json.loads(json_util.dumps(aulas)), 200

@aula_bp.route('/<string:aula_id>/exportar', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def exportar_presenca(aula_id):
    """
    [ADMIN, PROFESSOR] Endpoint para exportar a lista de presença.
    Use o parâmetro de query ?formato=xlsx ou ?formato=pdf
    """
    aula = mongo.db.aulas.find_one({"_id": ObjectId(aula_id)})
    if not aula:
        return jsonify({"mensagem": "Aula não encontrada."}), 404
    
    if not _verificar_permissao_professor(str(aula.get('turma_id'))):
        return jsonify({"mensagem": "Acesso negado: você não tem permissão para esta turma."}), 403

    formato = request.args.get('formato', 'pdf').lower()

    try:
        if formato == 'xlsx':
            file_stream, nome_arquivo = export_service.gerar_planilha_presenca_aula(aula_id)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        elif formato == 'pdf':
            file_stream, nome_arquivo = export_service.gerar_pdf_presenca_aula(aula_id)
            mimetype = 'application/pdf'
        else:
            return jsonify({"mensagem": "Formato de exportação inválido. Use 'xlsx' ou 'pdf'."}), 400

        if not file_stream:
            return jsonify({"mensagem": "Aula não encontrada ou sem dados para exportar."}), 404

        return send_file(
            file_stream,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype=mimetype
        )
    except Exception as e:
        print(f"Erro ao gerar arquivo para aula {aula_id}: {e}")
        return jsonify({"mensagem": "Ocorreu um erro interno ao gerar o arquivo."}), 500
@aula_bp.route('/turma/<string:turma_id>/agendar', methods=['POST', 'OPTIONS'])
@admin_required()
def agendar_novas_aulas(turma_id):
    """
    [ADMIN] Agenda aulas para uma turma para o próximo mês.
    """
    try:
        total = aula_service.agendar_aulas_para_turma(turma_id)
        return jsonify({"mensagem": f"{total} novas aulas foram agendadas com sucesso!"}), 201
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        # Este bloco irá capturar e imprimir o erro detalhado no terminal
        print("!!!!!!!!!! ERRO AO AGENDAR AULAS !!!!!!!!!!")
        traceback.print_exc() # Imprime o traceback completo
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return jsonify({"mensagem": "Erro interno ao agendar aulas.", "detalhes": str(e)}), 500

@aula_bp.route('/historico', methods=['GET'])
@role_required(roles=['admin', 'professor'])
def get_historico_aulas():
    """
    [ADMIN, PROFESSOR] Retorna o histórico de aulas realizadas.
    """
    data_str = request.args.get('data')
    nome_turma = request.args.get('turma')
    
    data_filtro = None
    if data_str:
        try:
            data_filtro = datetime.strptime(data_str, '%Y-%m-%d')
        except ValueError:
            return jsonify({"mensagem": "Formato de data inválido. Use AAAA-MM-DD."}), 400
    aulas = aula_service.listar_historico_aulas(data_filtro, nome_turma)
    
    return json.loads(json_util.dumps(aulas)), 200

@aula_bp.route('/get-or-create', methods=['POST'])
@role_required(roles=['admin', 'professor'])
def get_or_create_aula():
    dados = request.get_json()
    if not dados or 'turma_id' not in dados or 'data' not in dados:
        return jsonify({"mensagem": "turma_id e data são obrigatórios."}), 400

    try:
        data_aula = datetime.fromisoformat(dados['data'].split('T')[0])
        aula = aula_service.buscar_ou_criar_aula_por_data(dados['turma_id'], data_aula)
        
        if not aula:
            # Esta é a resposta correta se não houver aula agendada para o dia
            return jsonify({"mensagem": "Não há aula programada para esta turma no dia selecionado."}), 404

        return json.loads(json_util.dumps(aula)), 200
    except ValueError as e:
        return jsonify({"mensagem": str(e)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({"mensagem": "Erro interno ao buscar ou criar aula."}), 500
    
