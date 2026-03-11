import os
import re
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

memoria_nota = {"produtos": [], "ativa": False}

@app.route('/')
def index():
    return "Servidor Online - Busca por UN Ativa"

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
                linhas = texto.split('\n')
                
                for linha in linhas:
                    # 1. Procura o EAN (13 dígitos)
                    ean_match = re.search(r'(\d{13})', linha)
                    
                    if ean_match:
                        ean = ean_match.group(1)
                        
                        # 2. Procura por UN, UND, PC ou CX seguido de um número (Quantidade)
                        # O padrão busca: Sigla + Espaço(s) + Números (aceita vírgula decimal)
                        qtd_match = re.search(r'(?:UN|UND|PC|CX)\s+(\d+[\d,.]*)', linha, re.IGNORECASE)
                        
                        if qtd_match:
                            # Pega o número, remove pontos de milhar e troca vírgula por ponto
                            qtd_str = qtd_match.group(1).replace('.', '').replace(',', '.')
                            qtd = int(float(qtd_str))
                        else:
                            qtd = 1 # Caso não ache a sigla, assume 1
                            
                        # 3. Tenta extrair o nome (texto entre o EAN e a sigla UN)
                        nome = "PRODUTO " + ean
                        partes = re.split(r'\d{13}', linha)
                        if len(partes) > 1:
                            nome_bruto = partes[1].split('UN')[0].strip()
                            if len(nome_bruto) > 5:
                                nome = nome_bruto

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
