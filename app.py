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
    return "Servidor Online - Extrator de Tabela Ativo"

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
                # Extrai as tabelas da página
                tabelas = page.extract_tables()
                for tabela in tabelas:
                    for linha in tabela:
                        # Pula o cabeçalho ou linhas vazias
                        if not linha or "DESCRIÇÃO" in str(linha[1]).upper():
                            continue
                        
                        try:
                            # Conforme o seu PDF:
                            # Coluna 1 (índice 1): Descrição e Código de Barras
                            # Coluna 2 (índice 2): Quantidade (QTD)
                            
                            descricao_completa = str(linha[1])
                            qtd_bruta = str(linha[2])

                            # 1. Extrai o EAN (13 dígitos) de dentro da descrição
                            ean_match = re.search(r'(\d{13})', descricao_completa)
                            ean = ean_match.group(1) if ean_match else "0000000000000"

                            # 2. Extrai apenas o Nome (remove a parte do "Cód. Barras")
                            nome = descricao_completa.split("Cód.")[0].strip()
                            nome = nome.replace('\n', ' ') # Remove quebras de linha

                            # 3. Limpa a Quantidade (converte "40" ou "40,00" para 40)
                            qtd_limpa = qtd_bruta.replace('.', '').replace(',', '.')
                            qtd = int(float(qtd_limpa))

                            if ean != "0000000000000":
                                lista.append({
                                    "e": ean, 
                                    "n": nome[:50].upper(), 
                                    "q": qtd, 
                                    "c": 0
                                })
                        except:
                            continue # Pula linhas que não seguem o padrão
        
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
