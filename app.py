from flask import Flask, request, jsonify
from flask_cors import CORS
import pdfplumber
import os
import json
import re
from datetime import datetime
from groq import Groq

app = Flask(__name__)
CORS(app)

# --- CONFIGURAÇÃO DE SEGURANÇA ---
# No Render, vá em 'Environment' e adicione GROQ_API_KEY com seu token gsk_...
GROQ_KEY = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=GROQ_KEY)

# Estrutura de memória para o coletor
memoria_nota = {
    "produtos": [], 
    "ativa": False,
    "timestamp": None,
    "nome_arquivo": None
}

@app.route('/')
def home():
    return "API DANFE Online - Coletor Cloud Pro (Groq Powered)"

@app.route('/extrair', methods=['POST'])
def extrair():
    global memoria_nota
    
    if 'file' not in request.files:
        return jsonify({"erro": "Sem arquivo"}), 400
    
    file = request.files['file']
    texto_bruto = ""
    
    print(f"Lendo PDF: {file.filename}")
    
    try:
        # 1. Extração de texto simplificada (extrai palavras, ignora a estrutura da tabela)
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                texto_extraido = page.extract_text()
                if texto_extraido:
                    texto_bruto += texto_extraido + "\n"
                    
        if not texto_bruto.strip():
            return jsonify({"erro": "O PDF parece ser uma imagem. Use PDFs digitais."}), 400

        # 2. Chamada à IA do Groq para organizar os dados
        # Usamos o modelo Llama 3 8B que é gratuito, rápido e preciso para JSON
        prompt_ia = f"""
        Extraia os produtos deste texto de Nota Fiscal e retorne APENAS um array JSON.
        Cada objeto do array deve ter:
        "e": Código de barras (EAN/GTIN) - apenas os números.
        "n": Nome do produto (em letras maiúsculas, remova códigos internos).
        "q": Quantidade total (apenas número).
        "c": 0 (valor padrão para conferência).

        Texto da nota:
        {texto_bruto[:7000]}
        """

        completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system", 
                    "content": "Você é um assistente logístico que extrai dados de DANFE. Responda apenas com o JSON puro, sem textos extras ou explicações."
                },
                {"role": "user", "content": prompt_ia}
            ],
            model="llama3-8b-8192",
            temperature=0, # Garante que a IA não invente dados
        )
        
        # Limpeza da resposta da IA (caso venha com blocos de código markdown)
        resposta_ia = completion.choices[0].message.content.strip()
        resposta_ia = re.sub(r'```json|```', '', resposta_ia).strip()
        
        # 3. Converter texto da IA em lista Python
        lista_produtos = json.loads(resposta_ia)
        
        if lista_produtos:
            memoria_nota = {
                "produtos": lista_produtos,
                "ativa": True,
                "timestamp": datetime.now().isoformat(),
                "nome_arquivo": file.filename
            }
            print(f"Sucesso! {len(lista_produtos)} itens carregados.")
            return jsonify({
                "status": "sucesso", 
                "quantidade": len(lista_produtos),
                "produtos": lista_produtos
            })
        
        return jsonify({"erro": "A IA não encontrou produtos no texto."}), 404

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({"erro": "Falha ao processar a nota."}), 500

@app.route('/obter-lista', methods=['GET'])
def obter_lista():
    """Endpoint que o celular consulta para baixar a lista de conferência"""
    return jsonify({
        "produtos": memoria_nota["produtos"],
        "ativa": memoria_nota["ativa"]
    })

@app.route('/limpar', methods=['POST'])
def limpar():
    """Apaga a nota atual da memória"""
    global memoria_nota
    memoria_nota = {
        "produtos": [], 
        "ativa": False,
        "timestamp": None,
        "nome_arquivo": None
    }
    return jsonify({"status": "limpo"})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "ativa": memoria_nota["ativa"],
        "arquivo": memoria_nota["nome_arquivo"],
        "total_itens": len(memoria_nota["produtos"])
    })

if __name__ == '__main__':
    # Configuração para rodar no Render (lendo a porta da variável de ambiente)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
