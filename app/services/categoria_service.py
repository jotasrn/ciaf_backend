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
    resultado = mongo.db.categorias.insert_one(nova_categoria)
    return resultado.inserted_id

def atualizar_categoria(categoria_id, dados):
    """Atualiza o nome de uma categoria."""
    novo_nome = dados.get('nome')
    if not novo_nome:
        raise ValueError("O novo nome é obrigatório.")
    
    mongo.db.categorias.update_one(
        {"_id": ObjectId(categoria_id)},
        {"$set": {"nome": novo_nome}}
    )
    return True

def deletar_categoria(categoria_id):
    """Deleta uma categoria, mas apenas se não estiver em uso por uma turma."""
    obj_id = ObjectId(categoria_id)
    
    # Regra de negócio: não permitir apagar uma categoria em uso.
    turma_associada = mongo.db.turmas.find_one({"categoria_id": obj_id}) # Assumindo que você vai refatorar para usar categoria_id
    # Verificação por nome, como está hoje:
    categoria = mongo.db.categorias.find_one({"_id": obj_id})
    turma_associada_por_nome = mongo.db.turmas.find_one({"categoria": categoria.get('nome')})

    if turma_associada_por_nome:
        raise ValueError("Não é possível deletar esta categoria, pois existem turmas associadas a ela.")

    mongo.db.categorias.delete_one({"_id": obj_id})
    return True

def listar_todas_categorias():
    """
    Lista todas as categorias, agregando o nome do esporte ao qual pertencem.
    """
    pipeline = [
        {
            "$lookup": {
                "from": "esportes",
                "localField": "esporte_id",
                "foreignField": "_id",
                "as": "esporte_info"
            }
        },
        {"$unwind": "$esporte_info"},
        {
            "$project": {
                "nome": 1,
                "esporte_id": 1,
                "esporte_nome": "$esporte_info.nome"
            }
        },
        {"$sort": {"esporte_nome": 1, "nome": 1}}
    ]
    return list(mongo.db.categorias.aggregate(pipeline))