import os
import re
import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return "Servidor DANFE Ativo"

@app.route('/extrair', methods=['POST'])
def extrair():
    if 'file' not in request.files:
        return jsonify([]), 400
    
    file = request.files['file']
    lista_produtos = []
    
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                # Extrai as tabelas da página
                tabelas = page.extract_tables()
                for tabela in tabelas:
                    for linha in tabela:
                        # Filtra linhas que parecem ter um EAN (13 dígitos)
                        # Geralmente o EAN e a Descrição estão nas primeiras colunas
                        texto_linha = " ".join([str(item) for item in linha if item])
                        ean_match = re.search(r'(\d{13})', texto_linha)
                        
                        if ean_match:
                            ean = ean_match.group(1)
                            # O nome costuma ser o item mais longo da linha
                            nome = max(linha, key=lambda x: len(str(x)) if x else 0)
                            
                            # Tenta achar a quantidade (procura números isolados na linha)
                            # Filtramos apenas números que não sejam o EAN ou NCM
                            qtd = 1
                            for celula in linha:
                                if celula and re.match(r'^\d+(?:,\d+)?$', str(celula)):
                                    val = float(str(celula).replace(',', '.'))
                                    if 0 < val < 1000: # Filtro simples para não pegar o EAN
                                        qtd = int(val)
                                        break

                            lista_produtos.append({
                                "e": ean,
                                "n": str(nome).strip()[:40].upper(),
                                "q": qtd,
                                "c": 0
                            })
        
        # Se a extração por tabela falhar, ele usa o modo texto como backup
        return jsonify(lista_produtos)
    except Exception as e:
        return jsonify({"erro": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
