import streamlit as st
import boto3
import pandas as pd
from datetime import datetime, timedelta, date
import io # Necessário para gerar o arquivo Excel em memória

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(
    page_title="Analisador de Lambdas AWS",
    layout="wide"
)

st.title("🔎 Analisador de Métricas e Custos de AWS Lambda")
st.markdown("Esta ferramenta analisa as funções Lambda para identificar as ociosas e as que possuem uma alta taxa de falha, buscando também uma estimativa de custo para estas últimas.")

# --- FUNÇÕES AUXILIARES ---

@st.cache_data(ttl=3600) # Cache por 1 hora para não buscar a lista de lambdas toda hora
def list_all_lambda_functions(_session):
    """Busca e retorna um dicionário com todas as funções Lambda na conta."""
    try:
        lambda_client = _session.client('lambda')
        paginator = lambda_client.get_paginator('list_functions')
        pages = paginator.paginate()
        # Armazenamos o ARN completo, que será útil para a API de custos
        all_functions = {func['FunctionName']: func['FunctionArn'] for page in pages for func in page['Functions']}
        return all_functions
    except Exception as e:
        st.error(f"ERRO ao listar as funções Lambda: {e}")
        return None

def get_lambda_cost(cost_explorer_client, function_arn, start_date, end_date):
    """Busca o custo de uma função Lambda específica usando o Cost Explorer."""
    try:
        # O ARN para o Cost Explorer não deve ter o alias/versão no final
        clean_arn = ':'.join(function_arn.split(':')[:7])
        
        response = cost_explorer_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Filter={
                "Dimensions": {
                    "Key": "RESOURCE_ID",
                    "Values": [ clean_arn.split(':')[-1] ] # Filtra pelo nome da função
                }
            },
            Metrics=['UnblendedCost']
        )
        cost = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
        unit = response['ResultsByTime'][0]['Total']['UnblendedCost']['Unit']
        return f"{float(cost):.4f} {unit}"
    except Exception:
        # Pode falhar por permissão ou se a função não teve custo no período
        return "N/A"



st.header("⚙️ Configurações da Análise")

aws_profile_name = st.text_input("Perfil AWS (profile_name)", value='prod-readonly')
periodo_dias = st.slider("Período de Análise (dias)", 1, 90, 30)
taxa_falha_alvo = st.slider("Taxa de Falha Alvo (%)", 1, 100, 95)
limite_teste = st.number_input("Limite de funções para testar (0 para todas)", min_value=0, value=10, step=10)

run_analysis = st.button("🚀 Iniciar Análise")

if run_analysis:
    # Limpa resultados antigos do estado da sessão
    if 'df_ociosas' in st.session_state:
        del st.session_state.df_ociosas
    if 'df_falhas' in st.session_state:
        del st.session_state.df_falhas

    try:
        st.info(f"Iniciando sessão com o perfil AWS: '{aws_profile_name}'...")
        session = boto3.Session(profile_name=aws_profile_name)
        # Inicializa todos os clientes necessários
        cloudwatch = session.client('cloudwatch')
        cost_explorer = session.client('ce')
        st.success("Sessão AWS iniciada com sucesso.")
    except Exception as e:
        st.error(f"Falha ao iniciar a sessão Boto3. Verifique a configuração do seu perfil. Erro: {e}")
        st.stop() # Interrompe a execução se não conseguir conectar

    with st.spinner("Buscando a lista de todas as funções Lambda..."):
        all_functions = list_all_lambda_functions(session)
    
    if not all_functions:
        st.warning("Nenhuma função Lambda encontrada ou ocorreu um erro.")
        st.stop()

    function_names = list(all_functions.keys())
    function_names_to_scan = function_names[:limite_teste] if limite_teste > 0 else function_names
    total_to_scan = len(function_names_to_scan)

    st.info(f"Analisando métricas de {total_to_scan} de {len(function_names)} funções encontradas...")

    # Placeholders para a barra de progresso e texto de status
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    lambdas_ociosas = []
    lambdas_com_alta_falha = []
    
    # Define os períodos de tempo
    end_time_cw = datetime.utcnow()
    start_time_cw = end_time_cw - timedelta(days=periodo_dias)
    end_date_ce = date.today().strftime("%Y-%m-%d")
    start_date_ce = (date.today() - timedelta(days=periodo_dias)).strftime("%Y-%m-%d")

    # --- FASE 1: Análise de Métricas (Invocations e Errors) ---
    for i, name in enumerate(function_names_to_scan):
        status_text.text(f"Analisando métricas [{i+1}/{total_to_scan}]: {name}")
        progress_bar.progress((i + 1) / total_to_scan)
        
        response = cloudwatch.get_metric_data(
            MetricDataQueries=[
                {'Id': 'invocations', 'MetricStat': {'Metric': {'Namespace': 'AWS/Lambda', 'MetricName': 'Invocations', 'Dimensions': [{'Name': 'FunctionName', 'Value': name}]}, 'Period': periodo_dias * 86400, 'Stat': 'Sum'}},
                {'Id': 'errors', 'MetricStat': {'Metric': {'Namespace': 'AWS/Lambda', 'MetricName': 'Errors', 'Dimensions': [{'Name': 'FunctionName', 'Value': name}]}, 'Period': periodo_dias * 86400, 'Stat': 'Sum'}}
            ],
            StartTime=start_time_cw, EndTime=end_time_cw
        )
        total_invocations = sum(response['MetricDataResults'][0]['Values'])
        total_errors = sum(response['MetricDataResults'][1]['Values'])

        if total_invocations == 0:
            lambdas_ociosas.append({'FunctionName': name})
        else:
            failure_rate = (total_errors / total_invocations) * 100
            if failure_rate > taxa_falha_alvo:
                lambdas_com_alta_falha.append({
                    'FunctionName': name,
                    'FunctionArn': all_functions[name],
                    'FailureRate(%)': round(failure_rate, 2),
                    'Invocations': int(total_invocations),
                    'Errors': int(total_errors)
                })
    
    status_text.text("Análise de métricas concluída. Buscando custos...")

    # --- FASE 2: Busca de Custos (apenas para as com falha) ---
    if lambdas_com_alta_falha:
        total_falhas = len(lambdas_com_alta_falha)
        for i, item in enumerate(lambdas_com_alta_falha):
            status_text.text(f"Buscando custo [{i+1}/{total_falhas}]: {item['FunctionName']}")
            progress_bar.progress((i + 1) / total_falhas)
            cost = get_lambda_cost(cost_explorer, item['FunctionArn'], start_date_ce, end_date_ce)
            item['EstimatedCost'] = cost
            del item['FunctionArn'] # Remove o ARN do relatório final

    status_text.success("✅ Análise concluída!")
    progress_bar.empty()

    # Salva os dataframes no estado da sessão para persistência
    st.session_state.df_ociosas = pd.DataFrame(lambdas_ociosas)
    st.session_state.df_falhas = pd.DataFrame(lambdas_com_alta_falha)

# --- EXIBIÇÃO DOS RESULTADOS ---
if 'df_ociosas' in st.session_state and 'df_falhas' in st.session_state:
    st.header("📊 Resultados da Análise")
    
    tab1, tab2 = st.tabs([f"Lambdas com Alta Falha ({len(st.session_state.df_falhas)})", f"Lambdas Ociosas ({len(st.session_state.df_ociosas)})"])
    
    with tab1:
        st.dataframe(st.session_state.df_falhas, use_container_width=True)

    with tab2:
        st.dataframe(st.session_state.df_ociosas, use_container_width=True)
    
    # --- GERAÇÃO E DOWNLOAD DO EXCEL ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        st.session_state.df_ociosas.to_excel(writer, sheet_name='Ociosas', index=False)
        st.session_state.df_falhas.to_excel(writer, sheet_name='Com Alta Falha e Custo', index=False)
    
    excel_data = output.getvalue()

    st.download_button(
        label="📥 Baixar Relatório em Excel",
        data=excel_data,
        file_name=f'relatorio_lambdas_{date.today()}.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )