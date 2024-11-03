from fpdf import FPDF
import pandas as pd
from sqlalchemy import create_engine

def gerar_conserto_por_id_conserto(id_conserto: int):
    # Defina suas credenciais e informações do banco de dados
    username = 'rm556448'
    password = 'fiap24'
    host = 'oracle.fiap.com.br'
    port = 1521
    service_name = 'orcl'

    # Crie a string de conexão usando o driver oracledb
    engine = create_engine(f'oracle+oracledb://{username}:{password}@{host}:{port}/?service_name={service_name}')

    # Crie a consulta SQL selecionando apenas os campos necessários
    query = f'''
    SELECT ds_conserto, dt_conserto, vl_conserto
    FROM t_securecar_conserto
    WHERE id_conserto = {id_conserto}
    '''

    # Execute a consulta e armazene o resultado em um DataFrame
    df = pd.read_sql(query, con=engine)

    # Verifique se o DataFrame não está vazio
    if df.empty:
        print(f"Não foram encontrados registros para o id_conserto {id_conserto}.")
        return

    # Inicialize o PDF com margens ajustadas
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(left=15, top=15, right=15)
    pdf.add_page()

    # Adicione o cabeçalho ajustado
    pdf.set_font('Arial', 'B', 20)
    pdf.cell(0, 20, 'SecureCar', 0, 1, 'L')
    pdf.set_font('Arial', '', 20)
    pdf.cell(0, 10, 'Essa é a sua ficha para conserto', 0, 1, 'L')
    pdf.ln(10)  # Espaçamento após o cabeçalho

    pdf.set_font(family='Arial', size=12)

    # Formatar e adicionar os dados ao PDF
    for index, row in df.iterrows():
        ds_conserto = str(row['ds_conserto']) if pd.notnull(row['ds_conserto']) else 'Descrição não disponível'
        dt_conserto = row['dt_conserto']
        vl_conserto = row['vl_conserto']

        # Formate a data se necessário
        if not pd.isnull(dt_conserto):
            dt_conserto = pd.to_datetime(dt_conserto).strftime('%d/%m/%Y')
        else:
            dt_conserto = 'Data não disponível'

        # Adicione as informações ao PDF com quebra de linha automática
        pdf.set_font(family='Arial', style='B', size=12)
        pdf.cell(0, 10, txt=f"Data: {dt_conserto}", ln=True)
        pdf.set_font(family='Arial', size=12)
        pdf.multi_cell(0, 10, txt=f"Descrição do Conserto: {ds_conserto}", align='L')
        pdf.cell(0, 10, txt=f"Valor médio do Conserto: R$ {vl_conserto}", ln=True)
        pdf.ln(5)  # Espaçamento entre os registros

    # Salve o PDF
    pdf.output(f'resultado.pdf')

# Exemplo de uso da função