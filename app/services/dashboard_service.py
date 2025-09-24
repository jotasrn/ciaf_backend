# app/services/dashboard_service.py

from app import mongo
import traceback

def get_summary_data():
    """
    Busca dados resumidos para o dashboard do admin, com logs para depuração.
    """
    try:
        # --- INÍCIO DA DEPURAÇÃO ---
        print("\n=============================================")
        print("===== INICIANDO DEPURAÇÃO DO DASHBOARD =====")

        # 1. Contagem de Alunos
        query_alunos = {"perfil": "aluno", "ativo": True}
        total_alunos = mongo.db.usuarios.count_documents(query_alunos)
        print(f"[DEBUG] Query Alunos: {query_alunos}")
        print(f"[DEBUG] Resultado - Total de Alunos: {total_alunos}")

        # 2. Contagem de Turmas
        query_turmas = {}
        total_turmas = mongo.db.turmas.count_documents(query_turmas)
        print(f"[DEBUG] Query Turmas: {query_turmas}")
        print(f"[DEBUG] Resultado - Total de Turmas: {total_turmas}")

        # 3. Contagem de Inadimplentes
        query_inadimplentes = {
            "perfil": "aluno",
            "ativo": True,
            "status_pagamento.status": {"$ne": "pago"}
        }
        total_inadimplentes = mongo.db.usuarios.count_documents(query_inadimplentes)
        print(f"[DEBUG] Query Inadimplentes: {query_inadimplentes}")
        print(f"[DEBUG] Resultado - Total de Inadimplentes: {total_inadimplentes}")

        # Verificação extra para garantir que a correção anterior foi aplicada
        alunos_com_status_pagamento = mongo.db.usuarios.count_documents(
            {"perfil": "aluno", "status_pagamento": {"$exists": True}}
        )
        print(f"[DEBUG] Verificação Extra - Alunos com campo 'status_pagamento': {alunos_com_status_pagamento}")
        
        print("===== FIM DA DEPURAÇÃO DO DASHBOARD =====")
        print("=============================================\n")
        # --- FIM DA DEPURAÇÃO ---

        summary = {
            "total_alunos": total_alunos,
            "total_turmas": total_turmas,
            "total_inadimplentes": total_inadimplentes
        }
        return summary
    except Exception as e:
        print(f"!!!!!! ERRO CRÍTICO NO SERVIÇO DO DASHBOARD !!!!!!")
        traceback.print_exc()
        return None