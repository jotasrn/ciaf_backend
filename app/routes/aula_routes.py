from flask import Blueprint, request, jsonify, send_file
from app.decorators.auth_decorators import role_required, admin_required
from app.services import aula_service, export_service
from app import mongo, timezone
from bson import ObjectId, json_util
from flask_jwt_extended import get_jwt_identity, get_jwt
import datetime
import json


# Garante que o Blueprint está definido corretamente
aula_bp = Blueprint('aula_bp', __name__)

def _verificar_permissao_professor(turma_id):
    """
    Verifica se o usuário logado é o professor da turma ou um admin.
    Retorna True se tiver permissão, False caso contrário.
    """
    claims = get_jwt()
    if claims.get("perfil") == "admin":
        return True

    turma = mongo.db.turmas.find_one({"_id": ObjectId(turma_id)})
    if not turma:
        return False
        
    id_professor_logado = get_jwt_identity()
    return str(turma.get('professor_id')) == id_professor_logado


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


@aula_bp.route('/<string:aula_id>/presencas', methods=['POST'])
@role_required(roles=['admin', 'professor'])
def registrar_presencas(aula_id):
    aula = mongo.db.aulas.find_one({"_id": ObjectId(aula_id)})
    if not aula:
        return jsonify({"mensagem": "Aula não encontrada."}), 404

    if aula.get('status') == 'realizada':
        return jsonify({"mensagem": "Esta chamada já foi finalizada e não pode ser alterada."}), 403 # Forbidden

    if not _verificar_permissao_professor(str(aula.get('turma_id'))):
        return jsonify({"mensagem": "Acesso negado: você não pode registrar presenças para esta turma."}), 403

    lista_presencas = request.get_json()
    if not isinstance(lista_presencas, list):
        return jsonify({"mensagem": "O corpo da requisição deve ser uma lista de presenças."}), 400

    try:
        total_modificado = aula_service.marcar_presenca_lote(aula_id, lista_presencas)
        return jsonify({"mensagem": f"Presença registrada para {total_modificado} aluno(s).", "aula_status": "realizada"}), 200
    except Exception as e:
        return jsonify({"mensagem": "Erro ao registrar presença.", "detalhes": str(e)}), 500

@aula_bp.route('/por-data', methods=['GET'])
@role_required(roles=['admin', 'professor']) # <-- CORREÇÃO AQUI
def get_aulas_do_dia():
    """
    [ADMIN, PROFESSOR] Retorna as aulas de um dia específico.
    """
    data_str = request.args.get('data')
    
    if data_str:
        try:
            data_filtro = datetime.datetime.fromisoformat(data_str)
        except ValueError:
            return jsonify({"mensagem": "Formato de data inválido. Use AAAA-MM-DD."}), 400
    else:
        data_filtro = datetime.datetime.now(timezone)

    aulas = aula_service.listar_aulas_por_data(data_filtro)
    return json.loads(json_util.dumps(aulas)), 200


@aula_bp.route('/<string:aula_id>/exportar', methods=['GET'])
@admin_required()
def exportar_presenca(aula_id):
    """
    [ADMIN] Endpoint para exportar a lista de presença.
    Use o parâmetro de query ?formato=xlsx ou ?formato=pdf
    """
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
        # Em um sistema de produção, registraríamos esse erro em um sistema de log.
        print(f"Erro ao gerar planilha para aula {aula_id}: {e}")
        return jsonify({"mensagem": "Ocorreu um erro interno ao gerar a planilha."}), 500

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
        return jsonify({"mensagem": "Erro interno ao agendar aulas.", "detalhes": str(e)}), 500