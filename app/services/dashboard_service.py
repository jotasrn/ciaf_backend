# app/services/dashboard_service.py

from app import mongo

def get_summary_data():
    """
    Busca dados resumidos para o dashboard do admin.
    """
    try:
        total_alunos = mongo.db.usuarios.count_documents({"perfil": "aluno", "ativo": True})
        total_turmas = mongo.db.turmas.count_documents({})
        
        # CORREÇÃO APLICADA AQUI: O nome da chave foi alinhado com o frontend.
        total_inadimplentes = mongo.db.usuarios.count_documents({
            "perfil": "aluno",
            "ativo": True,
            "status_pagamento.status": {"$ne": "pago"}
        })
        
        summary = {
            "total_alunos": total_alunos,
            "total_turmas": total_turmas,
            "total_inadimplentes": total_inadimplentes
        }
        return summary
    except Exception as e:
        # Em um app real, logaríamos o erro
        print(f"Erro ao buscar dados do dashboard: {e}")
        return None