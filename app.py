import os
import re
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Banco de dados temporário na memória
memoria_nota = {"produtos": [], "ativa": False}

@app.route('/')
def index():
    return "Servidor DANFE Online"

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
                # Extração por tabela é mais precisa para Nomes e Qtd
                tabelas = page.extract_tables()
                for tabela in tabelas:
                    for linha in tabela:
                        # Limpa valores nulos
                        dados = [str(c).strip() for c in linha if c]
                        texto_linha = " ".join(dados)
                        
                        # Busca EAN (13 dígitos)
                        ean_match = re.search(r'(\d{13})', texto_linha)
                        if ean_match:
                            ean = ean_match.group(1)
                            
                            # O Nome costuma ser a célula mais longa da linha
                            nome = max(dados, key=len) if dados else f"Item {ean}"
                            if len(nome) < 5: nome = f"Produto {ean}"
                            
                            # Busca Quantidade (número isolado pequeno)
                            qtd = 1
                            for d in dados:
                                d_limpo = d.replace(',', '.')
                                if re.match(r'^\d+(\.\d+)?$', d_limpo):
                                    val = float(d_limpo)
                                    if 0 < val < 500: # Filtro para não pegar o EAN/NCM
                                        qtd = int(val)
                                        break

                            lista.append({
                                "e": ean, 
                                "n": nome[:40].upper(), 
                                "q": qtd, 
                                "c": 0
                            })
        
        memoria_nota = {"produtos": lista, "ativa": True}
        return jsonify(lista)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

@app.route('/obter-lista', methods=['GET'])
def obter_lista():
    return jsonify(memoria_nota)

@app.route('/limpar', methods=['POST'])
def limpar():
    global memoria_nota
    memoria_nota = {"produtos": [], "ativa": False}
    return jsonify({"status": "limpo"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
