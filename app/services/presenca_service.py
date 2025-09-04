from app import mongo
from bson import ObjectId
import datetime

def atualizar_presenca(presenca_id, dados_atualizacao, admin_id):
    """
    Atualiza um único registro de presença.
    Apenas o status e a observação podem ser alterados.
    Registra qual admin fez a alteração.
    """
    try:
        obj_id = ObjectId(presenca_id)
        admin_obj_id = ObjectId(admin_id)
    except Exception:
        raise ValueError("ID de presença ou de administrador inválido.")

    campos_permitidos = ['status', 'observacao']
    update_fields = {}

    for campo in campos_permitidos:
        if campo in dados_atualizacao:
            update_fields[campo] = dados_atualizacao[campo]
            
    # Validação do status
    if 'status' in update_fields and update_fields['status'] not in ['presente', 'ausente', 'justificado']:
        raise ValueError("Status de presença inválido. Valores permitidos: presente, ausente, justificado.")

    if not update_fields:
        return 0

    # Adiciona os campos de auditoria
    update_fields['modificado_por'] = admin_obj_id
    update_fields['data_modificacao'] = datetime.datetime.utcnow()

    resultado = mongo.db.presencas.update_one(
        {"_id": obj_id},
        {"$set": update_fields}
    )
    
    return resultado.modified_count