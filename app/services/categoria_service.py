from app import mongo
from bson import ObjectId

def listar_categorias_por_esporte(esporte_id):
    return list(mongo.db.categorias.find({"esporte_id": ObjectId(esporte_id)}).sort("nome"))

def criar_categoria(dados):
    if mongo.db.categorias.find_one({"nome": dados['nome'], "esporte_id": ObjectId(dados['esporte_id'])}):
        raise ValueError("Esta categoria já existe para este esporte.")

    nova_categoria = {
        "nome": dados['nome'],
        "esporte_id": ObjectId(dados['esporte_id'])
    }
    mongo.db.categorias.insert_one(nova_categoria)
    return True # Simplesmente retornamos sucesso

# TODO: Implementar update_categoria e delete_categoria