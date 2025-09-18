import requests
import json

# Altere se a sua URL for diferente
URL_API_TURMAS = "http://127.0.0.1:5000/api/turmas/"

# PREENCHA COM UM TOKEN JWT VÁLIDO GERADO PELO SEU LOGIN
# Exemplo: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
TOKEN_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc1ODE1NjI2OCwianRpIjoiZTdlZjIyNjctNjQ0MC00NDA5LWI2MGQtZWQxOGRlNWM2MjIxIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjY4YjhkZWE1NGIyNDNjOWFhMTMxMWZiNSIsIm5iZiI6MTc1ODE1NjI2OCwiY3NyZiI6ImJiOTUxNDI1LTEwNmUtNDY2NC1hOTVjLTE3MmNiMGExYWQ0YSIsImV4cCI6MTc1ODE1NzE2OCwicGVyZmlsIjoiYWRtaW4iLCJub21lX2NvbXBsZXRvIjoiQWRtaW5pc3RyYWRvciBkbyBTaXN0ZW1hIn0.ix9RyrTrCGSV0C8D_1ebZDUmv8BOCpvkHfNmJCVk4pc"

def verificar_endpoint_turmas():
    """
    Função para fazer uma requisição GET autenticada e imprimir a resposta JSON.
    """
    if not TOKEN_JWT:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!! ERRO: Por favor, insira um TOKEN_JWT válido na      !!")
        print("!! variável TOKEN_JWT antes de executar o script.      !!")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        return

    headers = {
        "Authorization": f"Bearer {TOKEN_JWT}"
    }

    print(f">>> Fazendo requisição para {URL_API_TURMAS}...")

    try:
        response = requests.get(URL_API_TURMAS, headers=headers)
        response.raise_for_status()  # Levanta um erro para códigos de status ruins (4xx ou 5xx)

        print(">>> Resposta recebida com sucesso! Código de Status:", response.status_code)
        print("\n" + "="*80)
        print(" DADOS JSON RECEBIDOS DA API:")
        print("="*80)

        # Imprime o JSON formatado
        dados_json = response.json()
        print(json.dumps(dados_json, indent=2, ensure_ascii=False))

        print("\n" + "="*80)
        print(">>> Verificação concluída.")
        print("="*80)


    except requests.exceptions.HTTPError as http_err:
        print(f"!! ERRO HTTP OCORREU: {http_err}")
        print(f"!! Conteúdo da resposta: {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"!! ERRO DE REQUISIÇÃO OCORREU: {req_err}")
    except json.JSONDecodeError:
        print("!! ERRO: A resposta não é um JSON válido. Conteúdo recebido:")
        print(response.text)

if __name__ == "__main__":
    verificar_endpoint_turmas()