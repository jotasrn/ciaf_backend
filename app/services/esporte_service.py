from app import mongo
from bson import ObjectId

def criar_esporte(dados):
    """Cria um novo esporte, garantindo que o nome seja único."""
    if mongo.db.esportes.find_one({"nome": dados['nome']}):
        raise ValueError("Já existe um esporte com este nome.")
    
    novo_esporte = {
        "nome": dados['nome'],
        "descricao": dados.get('descricao', '')
    }
    resultado = mongo.db.esportes.insert_one(novo_esporte)
    return str(resultado.inserted_id)

def listar_esportes():
    return list(mongo.db.esportes.find())

def encontrar_esporte_por_id(esporte_id):
    try:
        return mongo.db.esportes.find_one({"_id": ObjectId(esporte_id)})
    except Exception:
        return None

def atualizar_esporte(esporte_id, dados):
    # (Opcional) Adicionar verificação de nome único se o nome estiver sendo alterado
    resultado = mongo.db.esportes.update_one(
        {"_id": ObjectId(esporte_id)},
        {"$set": dados}
    )
    return resultado.modified_count

def deletar_esporte(esporte_id):
    """Deleta um esporte, mas somente se nenhuma turma estiver associada a ele."""
    obj_id = ObjectId(esporte_id)
    
    # Decisão pragmática de segurança: não permitir apagar um esporte em uso.
    turma_associada = mongo.db.turmas.find_one({"esporte_id": obj_id})
    if turma_associada:
        raise ValueError("Não é possível deletar este esporte, pois existem turmas associadas a ele.")

    resultado = mongo.db.esportes.delete_one({"_id": obj_id})
    return resultado.deleted_count