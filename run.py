from app import criar_app

app = criar_app()

if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5000, debug=True)


#.\venv\Scripts\Activate.ps1
#pip install -r requirements.txt
#python run.py

# "email": "admin@escolinha.com",
# "senha": "senhaSuperForte123", km

#venv deactivate, rm -r venv, python -m venv venv, .\venv\Scripts\Activate.ps1, pip install -r requirements.txt, python run.py