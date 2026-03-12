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

        # Chamada ao Groqcompletion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "Você é um assistente logístico que extrai dados de DANFE. Responda apenas com o JSON puro, sem textos extras."},
        {"role": "user", "content": prompt_ia}
    ],
    model="llama-3.3-70b-versatile", # Atualizado aqui!
    temperature=0
)
        
        resposta_ia = completion.choices[0].message.content.strip()
        
        # --- FILTRO DE SEGURANÇA PARA O JSON ---
        # Procura o primeiro '[' e o último ']' para extrair apenas a lista
        inicio = resposta_ia.find('[')
        fim = resposta_ia.rfind(']') + 1
        if inicio != -1 and fim != 0:
            resposta_ia = resposta_ia[inicio:fim]

        lista_produtos = json.loads(resposta_ia)
        
        # Garante que todos os itens tenham o campo 'c': 0
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
        print(f"ERRO: {str(e)}") # Isso aparecerá nos LOGS do Render
        return jsonify({"erro": str(e)}), 500

