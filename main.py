

# %%
import pickle
import re


# Carregar o modelo e os transformadores aprimorados
with open('modelo_causas_aprimorado.pkl', 'rb') as f:
    data = pickle.load(f)
    model = data['model']
    vectorizer = data['vectorizer']
    mlb = data['mlb']

# Função para normalizar o texto
def normalizar_texto(texto):
    return texto.strip().lower()

# Função para fazer predições
def prever_causas(problema_input, quilometragem_input):
    # Normalizar entradas
    problema_input_norm = normalizar_texto(problema_input)
    quilometragem_input_norm = normalizar_texto(quilometragem_input)
    
    # Criar a entrada combinada
    entrada = problema_input_norm + ' ' + quilometragem_input_norm

    # Transformar a entrada
    X_novo = vectorizer.transform([entrada])

    # Fazer a previsão
    y_pred = model.predict(X_novo)

    # Decodificar as causas previstas
    causas_previstas = mlb.inverse_transform(y_pred)

    # Verificar se há causas previstas
    if causas_previstas and causas_previstas[0]:
        print(f"Possíveis causas para '{problema_input}' com quilometragem '{quilometragem_input}':")
        for causa in causas_previstas[0]:
            print(f"- {causa}")
        return f"Possíveis causas para {str(problema_input).lower()} com quilometragem {quilometragem_input} são: {', '.join(causas_previstas[0])} "
    else:
        return f"Nenhuma causa prevista para '{problema_input}' com quilometragem '{quilometragem_input}'."
        # print(f"Nenhuma causa prevista para '{problema_input}' com quilometragem '{quilometragem_input}'.")

import oracledb as db

# def inserir_conserto():
# fazer pdf

def get_conexao():
    LOGIN = "rm556448"
    PWD = "fiap24"
    return db.connect(user=LOGIN,
                            password=PWD, dsn='oracle.fiap.com.br/orcl')

def pecas():
    sql = "SELECT ds_peca, id_peca FROM t_securecar_peca"
    with get_conexao() as con:
        with con.cursor() as cur:
            cur.execute(sql)
            lista_pecas = cur.fetchall()
    # Converter a lista de tuplas para um dicionário com chave ds_peca e valor id_peca
    return {peca[0].lower(): peca[1] for peca in lista_pecas}


def buscaCPF(cpf):


    sql = "select id_usuario from t_securecar_usuario where cpf like :cpf"
    
    with get_conexao() as con:
        with con.cursor() as cur:
            cur.execute(sql, {"cpf" : cpf})
            user_id = cur.fetchone()
    return user_id

def montar_dicionario_pecas(resultado, pecas_dict):
    resultado_lower = resultado.lower()
    peca_counts = {}
    for peca_nome, peca_id in pecas_dict.items():
        # Usar regex para contagem precisa de palavras inteiras
        pattern = r'\b' + re.escape(peca_nome) + r'\b'
        matches = re.findall(pattern, resultado_lower)
        count = len(matches)
        if count > 0:
            peca_counts[peca_id] = count
    return peca_counts



from flask import Flask, request, jsonify

app = Flask(__name__)



@app.route('/prever', methods=['POST'])
def prever():
    data = request.get_json()
    
    # Verificar se os dados recebidos são um dicionário
    if not isinstance(data, dict):
        return jsonify({"error": "Dados inválidos. Envie um JSON válido."}), 400
    
    # Obter o campo 'cpf'
    cpf = str(data.get('cpf', '')).strip()
    
    # Validar se 'cpf' foi fornecido
    if not cpf:
        return jsonify({"error": "O campo 'cpf' é obrigatório."}), 400
    
    # Remover '-', '/', '.' do CPF
    cpf_cleaned = re.sub(r'[-./]', '', cpf)
    
    # Validar se CPF contém exatamente 11 dígitos
    if not re.fullmatch(r'\d{11}', cpf_cleaned):
        return jsonify({"error": "CPF inválido. Por favor, forneça um CPF com 11 dígitos."}), 400
    
    # Buscar id_usuario usando CPF limpo
    user_id = buscaCPF(cpf_cleaned)
    if not user_id:
        return jsonify({"error": "Usuário não encontrado para o CPF fornecido."}), 404
    
    # Verificar se apenas 'cpf' foi fornecido
    keys = data.keys()
    if len(keys) == 1:
        # Apenas 'cpf' foi fornecido, retornar apenas o 'user_id'
        return jsonify({
            "user_id": user_id[0]  # Assumindo que user_id é uma tupla e queremos o primeiro elemento
        })
    
    # Se mais campos forem fornecidos, verificar se 'problema' e 'quilometragem' estão presentes
    problema = str(data.get('problema', '')).strip()
    quilometragem = str(data.get('quilometragem', '')).strip()
    
    # Validar se 'problema' e 'quilometragem' foram fornecidos
    if not problema or not quilometragem:
        return jsonify({"error": "Os campos 'problema' e 'quilometragem' são obrigatórios quando fornecidos."}), 400
    
    # Adicionar 'km' à quilometragem
    quilometragem_km = quilometragem + 'km'
    
    # Fazer a previsão das causas
    resultado = prever_causas(problema, quilometragem_km)
    
    # Montar o dicionário de peças e suas quantidades (apenas as encontradas no resultado)
    pecas_encontradas = montar_dicionario_pecas(resultado, lista_pecas)
    
    return jsonify({
        "user_id": user_id[0],  # Assumindo que user_id é uma tupla e queremos o primeiro elemento
        "text": resultado,
        "pecas": pecas_encontradas
    })

if __name__ == "__main__":
    app.run()

# Exemplo de uso com valores presentes no dataset
# problema = 'Barulho no motor'
# quilometragem = '50.000km'



