import pdfplumber
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Estrutura exata que o frontend espera
memoria_nota = {
    "produtos": [], 
    "ativa": False,
    "timestamp": None,
    "nome_arquivo": None
}

@app.route('/')
def home():
    return "API DANFE Online - Coletor Cloud Pro"

@app.route('/extrair', methods=['POST'])
def extrair():
    global memoria_nota
    
    if 'file' not in request.files:
        return jsonify({"erro": "Sem arquivo"}), 400
    
    file = request.files['file']
    produtos = []
    
    print(f"Processando arquivo: {file.filename}")
    
    with pdfplumber.open(file) as pdf:
        for page_num, page in enumerate(pdf.pages):
            print(f"Processando página {page_num + 1}")
            
            # Extrai texto da página para debug
            texto = page.extract_text()
            if texto:
                print(f"Texto da página: {texto[:200]}...")
            
            # Tenta extrair tabelas
            tabelas = page.extract_tables()
            
            for tabela_idx, tabela in enumerate(tabelas):
                print(f"Tabela {tabela_idx + 1} encontrada")
                
                for linha_idx, linha in enumerate(tabela):
                    if not linha:
                        continue
                    
                    # Filtra linhas de cabeçalho
                    linha_texto = ' '.join([str(cell) for cell in linha if cell]).upper()
                    if any(palavra in linha_texto for palavra in ["DESCRIÇÃO", "DESCRICAO", "CÓDIGO", "CODIGO", "QTDE", "QUANT"]):
                        continue
                    
                    try:
                        # Procura por EAN (código de barras de 13 dígitos)
                        ean = None
                        for cell in linha:
                            cell_str = str(cell) if cell else ""
                            # Procura por padrões de EAN
                            codigos = re.findall(r'(\d{13})', cell_str)
                            if codigos:
                                ean = codigos[0]
                                print(f"EAN encontrado: {ean}")
                                break
                        
                        if not ean:
                            # Tenta no texto completo da linha
                            codigos = re.findall(r'(\d{13})', linha_texto)
                            if codigos:
                                ean = codigos[0]
                                print(f"EAN encontrado na linha: {ean}")
                        
                        # Procura por quantidade
                        quantidade = None
                        for cell in linha:
                            cell_str = str(cell) if cell else ""
                            # Remove pontos de milhar e converte vírgula
                            cell_clean = cell_str.replace('.', '').replace(',', '.').strip()
                            if cell_clean and cell_clean.replace('.', '').isdigit():
                                try:
                                    valor = float(cell_clean)
                                    if valor < 1000:  # Quantidade geralmente é um número pequeno
                                        quantidade = int(valor)
                                        print(f"Quantidade encontrada: {quantidade}")
                                        break
                                except:
                                    pass
                        
                        # Se encontrou EAN e quantidade, cria o produto
                        if ean and quantidade:
                            # Tenta extrair o nome do produto
                            nome = "PRODUTO"
                            for cell in linha:
                                cell_str = str(cell) if cell else ""
                                # Se a célula contém texto e não é número longo
                                if cell_str and len(cell_str) > 3 and not re.match(r'^[\d\s,.-]+$', cell_str):
                                    nome = cell_str.strip()
                                    break
                            
                            # Limita o tamanho do nome
                            nome = nome[:50].upper()
                            
                            # Verifica se já existe (evita duplicatas)
                            existe = False
                            for p in produtos:
                                if p['e'] == ean:
                                    existe = True
                                    break
                            
                            if not existe:
                                produtos.append({
                                    "e": ean,        # ean
                                    "n": nome,       # nome
                                    "q": quantidade, # quantidade
                                    "c": 0           # conferido (0 = não)
                                })
                                print(f"Produto adicionado: {nome} - {ean} - Qtd: {quantidade}")
                    
                    except Exception as e:
                        print(f"Erro ao processar linha: {e}")
                        continue
    
    # Se encontrou produtos, atualiza a memória
    if produtos:
        memoria_nota = {
            "produtos": produtos,
            "ativa": True,
            "timestamp": datetime.now().isoformat(),
            "nome_arquivo": file.filename
        }
        print(f"Total de {len(produtos)} produtos extraídos com sucesso!")
        return jsonify({
            "status": "sucesso",
            "quantidade": len(produtos),
            "produtos": produtos
        })
    
    print("Nenhum produto encontrado no PDF")
    return jsonify({"erro": "Nenhum produto encontrado"}), 404

@app.route('/obter-lista', methods=['GET'])
def obter_lista():
    """Endpoint que o frontend mobile consulta"""
    # Formato exato que o frontend espera
    return jsonify({
        "produtos": memoria_nota["produtos"],
        "ativa": memoria_nota["ativa"]
    })

@app.route('/limpar', methods=['POST'])
def limpar():
    """Limpa a memória da nota atual"""
    global memoria_nota
    memoria_nota = {
        "produtos": [], 
        "ativa": False,
        "timestamp": None,
        "nome_arquivo": None
    }
    print("Memória limpa!")
    return jsonify({"status": "limpo"})

# Endpoint extra para verificar status
@app.route('/status', methods=['GET'])
def status():
    """Retorna status atual da memória"""
    return jsonify({
        "memoria_ativa": memoria_nota["ativa"],
        "total_produtos": len(memoria_nota["produtos"]),
        "timestamp": memoria_nota["timestamp"],
        "arquivo": memoria_nota["nome_arquivo"]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Servidor iniciado na porta {port}")
    print(f"API URL: http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
