import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re

app = Flask(__name__)
CORS(app)

# Memória para o celular buscar (sincronização)
memoria_nota = {"produtos": [], "ativa": False}

@app.route('/')
def home():
    return "Servidor de Extracao DANFE Online!"

@app.route('/extrair', methods=['POST'])
def extrair():
    global memoria_nota
    if 'file' not in request.files:
        return jsonify({"erro": "Sem arquivo"}), 400
    
    file = request.files['file']
    produtos = []
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # Extração por tabela resolve o problema da quantidade e nome
            tabela = page.extract_table()
            if not tabela:
                continue
                
            for linha in tabela:
                # Pula cabeçalhos ou linhas vazias
                if not linha or "DESCRIÇÃO" in str(linha[1]).upper():
                    continue
                
                try:
                    descricao_bruta = str(linha[1]) # Coluna 2: Descrição e EAN
                    qtd_bruta = str(linha[2])       # Coluna 3: Quantidade
                    
                    # 1. Busca o EAN (13 dígitos)
                    ean_match = re.search(r'(\d{13})', descricao_bruta)
                    if ean_match:
                        ean = ean_match.group(1)
                        
                        # 2. Pega o Nome real (tudo antes de "Cód. Barras")
                        nome = descricao_bruta.split("Cód.")[0].split("C\xf3d.")[0].strip()
                        nome = nome.replace('\n', ' ').upper()
                        
                        # 3. Pega a Quantidade exata da coluna QTD
                        # Remove pontos de milhar e converte vírgula em ponto
                        val_limpo = qtd_bruta.replace('.', '').replace(',', '.')
                        qtd = int(float(val_limpo))
                        
                        produtos.append({
                            "e": ean,
                            "n": nome[:50],
                            "q": qtd,
                            "c": 0
                        })
                except Exception as e:
                    continue

    if produtos:
        memoria_nota = {"produtos": produtos, "ativa": True}
        return jsonify(produtos)
    
    return jsonify({"erro": "Nenhum produto encontrado"}), 404

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
