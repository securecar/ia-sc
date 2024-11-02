

# %%
import oracledb as db
from flask import Flask, request, jsonify
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
        print(f"Possíveis causas para '{
              problema_input}' com quilometragem '{quilometragem_input}':")
        for causa in causas_previstas[0]:
            print(f"- {causa}")
        return f"Possíveis causas para {str(problema_input).lower()} com quilometragem {quilometragem_input} são: {', '.join(causas_previstas[0])} "
    else:
        return f"Nenhuma causa prevista para '{problema_input}' com quilometragem '{quilometragem_input}'."
        # print(f"Nenhuma causa prevista para '{problema_input}' com quilometragem '{quilometragem_input}'.")


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
    sql = "select id_usuario, nm_usuario from t_securecar_usuario where nr_cpf like :cpf"

    with get_conexao() as con:
        with con.cursor() as cur:
            cur.execute(sql, {"cpf": cpf})
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

def inserir_conserto(resultado, pecas, user_id):
    sql = f"insert into t_securecar_conserto(dt_conserto, ds_conserto, vl_conserto, id_usuario) values (to_date(SYSDATE, 'DD-MM-YYYY'), :resultado, 0, :user_id) returning id_conserto into :id"

    input = {
        "resultado" : resultado,
        "user_id" : user_id
    }
    with get_conexao() as con:
        with con.cursor() as cur:
            cur.execute(sql, input)
        con.commit()
    return input['id']
        

def inserir_peca_conserto(id_conserto, pecas_encontradas: dict):
    sql = "insert into t_securecar_peca_conserto(id_conserto, id_peca) values(:id_conserto, :id_peca)"
    dados = []
    for id_peca, quantidade in pecas_encontradas.items():
        for _ in range(quantidade):
            dados.append({"id_conserto": id_conserto, "id_peca": id_peca})

    with get_conexao() as con:
        with con.cursor() as cur:
            cur.executemany(sql, dados)
        con.commit()


app = Flask(__name__)


@app.route('/prever', methods=['POST'])
def prever():
    data = request.get_json()

    if str(data.get('type', '')).strip() == 'cpf':
        cpf = str(data.get('cpf', '')).strip()
        cpf_cleaned = re.sub(r'[-./]', '', cpf)
        user = buscaCPF(cpf_cleaned)
        if not user:
            return jsonify({"error": "Usuário não encontrado para o CPF fornecido."}), 404
        return jsonify({
            "id": user[0],
            "username": user[1]
        })
    else:
        problema = str(data.get('problema', '')).strip()
        quilometragem = str(data.get('quilometragem', '')).strip()
        id_usuario = int(data.get('user', ''))
        if not problema or not quilometragem:
            return jsonify({"error": "Os campos 'problema' e 'quilometragem' são obrigatórios quando fornecidos."}), 400

        quilometragem_km = quilometragem + 'km'
        resultado = prever_causas(problema, quilometragem_km)
        lista_pecas = pecas()
        pecas_encontradas = montar_dicionario_pecas(resultado, lista_pecas)
        id_conserto = inserir_conserto(resultado=resultado, pecas=pecas, user_id=id_usuario)
        inserir_peca_conserto(id_conserto=id_conserto, pecas_encontradas=pecas_encontradas)
        
        print(pecas_encontradas)
        
        return jsonify({
            "text": resultado,
        })

   

if __name__ == "__main__":
    app.run()

# Exemplo de uso com valores presentes no dataset
# problema = 'Barulho no motor'
# quilometragem = '50.000km'
