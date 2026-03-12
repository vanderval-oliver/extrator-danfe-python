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

        # Chamada ao Groq
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Responda APENAS com um array JSON puro. Não use markdown nem textos explicativos."},
                {"role": "user", "content": f"Extraia EAN(e), Nome(n), Qtd(q) em JSON: {texto_bruto[:6000]}"}
            ],
            model="llama3-8b-8192",
            temperature=0,
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
