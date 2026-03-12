from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import os
import json
import re
from datetime import datetime
from groq import Groq

# 1. PRIMEIRO criamos o app e configuramos o CORS
app = Flask(__name__)
CORS(app)

# 2. Configuramos a IA (Groq)
GROQ_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_KEY)

# Estrutura de memória
memoria_nota = {
    "produtos": [], 
    "ativa": False,
    "timestamp": None,
    "nome_arquivo": None
}

# 3. AGORA sim definimos as rotas
@app.route('/')
def home():
    return "API DANFE Online - Groq v3.3"

@app.route('/extrair', methods=['POST'])
def extrair():
    global memoria_nota
    
    if 'file' not in request.files:
        return jsonify({"erro": "Sem arquivo"}), 400
    
    file = request.files['file']
    texto_bruto = ""
    
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                texto_extraido = page.extract_text()
                if texto_extraido:
                    texto_bruto += texto_extraido + "\n"
                    
        if not texto_bruto.strip():
            return jsonify({"erro": "PDF sem texto legível"}), 400

        # Chamada ao modelo ATUALIZADO (Llama 3.3)
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Extraia dados de DANFE. Retorne APENAS um array JSON puro com campos: e (EAN), n (Nome), q (Quantidade)."},
                {"role": "user", "content": texto_bruto[:7000]}
            ],
            model="llama-3.3-70b-versatile", # Modelo novo que substitui o antigo
            temperature=0,
        )
        
        resposta_ia = completion.choices[0].message.content.strip()
        
        # Filtro para pegar apenas o JSON
        inicio = resposta_ia.find('[')
        fim = resposta_ia.rfind(']') + 1
        if inicio != -1 and fim != 0:
            resposta_ia = resposta_ia[inicio:fim]

        lista_produtos = json.loads(resposta_ia)
        
        # Adiciona campo de conferência
        for item in lista_produtos:
            item['c'] = 0
        
        memoria_nota = {
            "produtos": lista_produtos,
            "ativa": True,
            "timestamp": datetime.now().isoformat(),
            "nome_arquivo": file.filename
        }
        return jsonify({"status": "sucesso", "quantidade": len(lista_produtos)})
        
    except Exception as e:
        print(f"ERRO: {str(e)}")
        return jsonify({"erro": str(e)}), 500

@app.route('/obter-lista', methods=['GET'])
def obter_lista():
    return jsonify(memoria_nota)

@app.route('/limpar', methods=['POST'])
def limpar():
    global memoria_nota
    memoria_nota = {"produtos": [], "ativa": False, "timestamp": None, "nome_arquivo": None}
    return jsonify({"status": "limpo"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
