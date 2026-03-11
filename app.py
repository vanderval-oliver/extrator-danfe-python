import os
import re
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Esta variável vai guardar a última nota processada na memória do servidor
memoria_nota = {
    "produtos": [],
    "ativa": False
}

@app.route('/')
def index():
    return "Servidor DANFE com Memória Ativo"

@app.route('/extrair', methods=['POST'])
def extrair():
    global memoria_nota
    if 'file' not in request.files:
        return jsonify([]), 400
    
    file = request.files['file']
    lista = []
    
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                texto = page.extract_text()
                # Busca EAN (13 dígitos)
                matches = re.finditer(r'(\d{13})', texto)
                for m in matches:
                    ean = m.group(1)
                    # Busca quantidade simples após o EAN
                    trecho = texto[m.end():m.end()+40]
                    qtd_match = re.search(r'(\d+)', trecho)
                    qtd = int(qtd_match.group(1)) if qtd_match else 1
                    
                    lista.append({"e": ean, "n": f"Item {ean}", "q": qtd, "c": 0})
        
        # SALVA NA MEMÓRIA PARA O CELULAR PEGAR DEPOIS
        memoria_nota["produtos"] = lista
        memoria_nota["ativa"] = True
        return jsonify(lista)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

# ROTA NOVA: O Celular vai chamar isso aqui para baixar a lista do PC
@app.route('/obter-lista', methods=['GET'])
def obter_lista():
    return jsonify(memoria_nota)

# ROTA NOVA: Para limpar a conferência
@app.route('/limpar', methods=['POST'])
def limpar():
    global memoria_nota
    memoria_nota = {"produtos": [], "ativa": False}
    return jsonify({"status": "limpo"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
