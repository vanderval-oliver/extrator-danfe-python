import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app) # Isso permite que seu site no Netlify fale com esse Python

@app.route('/')
def home():
    return "Servidor de Extracao DANFE Online!"

@app.route('/extrair', methods=['POST'])
def extrair():
    if 'file' not in request.files:
        return jsonify({"erro": "Sem arquivo"}), 400
    
    file = request.files['file']
    produtos = []
    
    with pdfplumber.open(file) as pdf:
        texto = ""
        for page in pdf.pages:
            texto += page.extract_text() + "\n"

        # Regex flexível para capturar: EAN (13 digitos) + Nome + Qtd
        import re
        # Procura 13 dígitos, pula um espaço e pega o que vem antes da unidade (UN, PC, etc)
        linhas = texto.split('\n')
        for linha in linhas:
            ean_match = re.search(r'(\d{13})', linha)
            if ean_match:
                ean = ean_match.group(1)
                # Tenta pegar a quantidade (procura um número com vírgula ou ponto no final da linha)
                qtd_match = re.findall(r'(\d+(?:,\d+)?)', linha)
                qtd = 1
                if len(qtd_match) > 1:
                    # Geralmente a quantidade é um dos últimos números da linha na DANFE
                    val = qtd_match[-2].replace(',', '.')
                    qtd = int(float(val)) if float(val) > 0 else 1

                produtos.append({
                    "e": ean,
                    "n": "Item " + ean,
                    "q": qtd,
                    "c": 0
                })

    return jsonify(produtos)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
