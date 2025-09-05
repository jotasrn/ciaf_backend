from app import criar_app

app = criar_app()

if __name__ == '__main__':
    # debug=True reinicia o servidor automaticamente a cada alteração de código
    # Em produção, usaremos um servidor WSGI como Gunicorn ou Waitress
    app.run(host='0.0.0.0', port=5000, debug=True)


#.\venv\Scripts\Activate.ps1
#pip install -r requirements.txt
#python run.py

# "email": "admin@escolinha.com",
# "senha": "senhaSuperForte123",

#erro de venv deactivate, rm -r venv, python -m venv venv, .\venv\Scripts\Activate.ps1, pip install -r requirements.txt, python run.py