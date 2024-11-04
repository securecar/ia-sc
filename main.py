

# %%
import oracledb as db
from flask import Flask, request, jsonify, send_file
import pickle
import re
from criar_pdf import gerar_conserto_por_id_conserto


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
    sql = """
    insert into t_securecar_conserto(dt_conserto, ds_conserto, vl_conserto, id_usuario)
    values (SYSDATE, :resultado, 0, :user_id)
    returning id_conserto into :id
    """

    with get_conexao() as con:
        with con.cursor() as cur:
            id_conserto_var = cur.var(db.NUMBER)
            params = {
                "resultado": resultado,
                "user_id": user_id,
                "id": id_conserto_var
            }
            cur.execute(sql, params)
            con.commit()
            id_conserto = id_conserto_var.getvalue()
            print("Valor retornado de id_conserto:", id_conserto, type(id_conserto))
            if isinstance(id_conserto, (list, tuple)):
                id_conserto = id_conserto[0]
                print("id_conserto após extração:", id_conserto, type(id_conserto))
    return id_conserto

def inserir_peca_conserto(id_conserto, pecas_encontradas: dict):
    sql = "insert into t_securecar_peca_conserto(id_conserto, id_peca) values(:id_conserto, :id_peca)"

    with get_conexao() as con:
        with con.cursor() as cur:
            try:
                for id_peca, quantidade in pecas_encontradas.items():
                    for _ in range(quantidade):
                        params = {"id_conserto": id_conserto, "id_peca": id_peca}
                        print("Inserindo com params:", params)
                        cur.execute(sql, params)
                con.commit()
            except Exception as e:
                con.rollback()
                print(f"Erro ao inserir peças do conserto: {e}")

app = Flask(__name__)

def valor_total(id_conserto: int):
    """
    Calcula o valor total do conserto somando o valor de cada peça utilizada 
    sem considerar a quantidade e atualiza o campo vl_conserto na tabela t_securecar_conserto.
    
    :param id_conserto: ID do conserto a ser atualizado.
    :return: Valor total calculado ou None se ocorrer um erro.
    """
    try:
        with get_conexao() as con:
            with con.cursor() as cur:
                # Consulta para obter o valor de cada peça associada ao conserto
                sql = '''
                    SELECT p.vl_peca
                    FROM t_securecar_peca_conserto pc
                    JOIN t_securecar_peca p ON pc.id_peca = p.id_peca
                    WHERE pc.id_conserto = :id_conserto
                '''
                cur.execute(sql, id_conserto=id_conserto)
                resultados = cur.fetchall()
                
                if not resultados:
                    print(f"Nenhuma peça encontrada para o id_conserto {id_conserto}.")
                    return None
                
                # Calcula o valor total somando o valor de cada peça
                total = (sum(vl_peca for (vl_peca,) in resultados) / len(resultados)) * 1.15
                print(f"Valor total calculado para id_conserto {id_conserto}: R$ {total:.2f}")
                
                # Atualiza o valor total no conserto
                update_sql = '''
                    UPDATE t_securecar_conserto
                    SET vl_conserto = :total
                    WHERE id_conserto = :id_conserto
                '''
                cur.execute(update_sql, total=total, id_conserto=id_conserto)
                con.commit()
                
                # return total
    except db.DatabaseError as e:
        error, = e.args
        print(f"Erro ao calcular e atualizar o valor total do conserto: {error.message}")
        return None


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
        print(resultado)
        lista_pecas = pecas()
        pecas_encontradas = montar_dicionario_pecas(resultado, lista_pecas)
        id_conserto = inserir_conserto(resultado=resultado, pecas=pecas, user_id=id_usuario)
        
        if id_conserto:
            print(f"Conserto inserido com sucesso. ID: {id_conserto}")
            inserir_peca_conserto(id_conserto, pecas_encontradas)
            valor_total(id_conserto)
        else:
            print("Falha ao inserir o conserto.")
        
        # inserir_peca_conserto(id_conserto=id_conserto, pecas_encontradas=pecas_encontradas)
        
        print(pecas_encontradas)
        
        return jsonify({
            "text": resultado,
        })

@app.route('/pdf/<int:id_conserto>', methods=['GET'])
def enviar_pdf(id_conserto):
    gerar_conserto_por_id_conserto(id_conserto)
    return send_file('resultado.pdf', as_attachment=True)


   

if __name__ == "__main__":
    app.run()

# Exemplo de uso com valores presentes no dataset
# problema = 'Barulho no motor'
# quilometragem = '50.000km'
