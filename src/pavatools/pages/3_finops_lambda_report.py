import streamlit as st
from aws_utils import handle_sso_login
import boto3
import pandas as pd
from datetime import datetime, timedelta, date
import io
from botocore.exceptions import ClientError
from botocore.exceptions import ClientError, SSOTokenLoadError
from navigation import create_hierarchical_sidebar, set_page_context

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(
    page_title="Analisador de Lambdas AWS",
    layout="wide"
)

# Definir contexto da página atual
set_page_context("3_finops_lambda_report.py")

# Criar navegação hierárquica na sidebar
create_hierarchical_sidebar()

# --- FUNÇÕES AUXILIARES ---

@st.cache_data(ttl=3600) # Cache para não ler o arquivo toda hora
def get_aws_profiles():
    """Usa boto3 para listar todos os perfis disponíveis nos arquivos de config/credentials."""
    try:
        return boto3.Session().available_profiles
    except Exception:
        return []

@st.cache_data(ttl=3600)
def list_all_lambda_functions(session):
    """Busca e retorna um dicionário com todas as funções Lambda usando a sessão fornecida."""
    try:
        lambda_client = session.client('lambda')
        paginator = lambda_client.get_paginator('list_functions')
        pages = paginator.paginate()
        all_functions = {func['FunctionName']: func['FunctionArn'] for page in pages for func in page['Functions']}
        return all_functions
    except ClientError as e:
        st.error(f"ERRO ao listar as funções Lambda: {e.response['Error']['Message']}. Verifique as permissões do perfil.")
        return None
    except Exception as e:
        st.error(f"ERRO ao listar as funções Lambda: {e}")
        return None

def get_lambda_cost(cost_explorer_client, function_arn, start_date, end_date):
    """Busca o custo de uma função Lambda específica usando o Cost Explorer."""
    try:
        clean_arn = ':'.join(function_arn.split(':')[:7])
        response = cost_explorer_client.get_cost_and_usage(
            TimePeriod={'Start': start_date, 'End': end_date},
            Granularity='MONTHLY',
            Filter={"Dimensions": {"Key": "RESOURCE_ID", "Values": [clean_arn.split(':')[-1]]}},
            Metrics=['UnblendedCost']
        )
        cost = response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
        unit = response['ResultsByTime'][0]['Total']['UnblendedCost']['Unit']
        return f"{float(cost):.4f} {unit}"
    except Exception:
        return "N/A"

# --- LAYOUT DA PÁGINA E CONTROLES ---
left_column, right_column = st.columns([2, 1])

with left_column:
    st.title("🔎 Analisador de Métricas e Custos de AWS Lambda")
    st.markdown("Esta ferramenta analisa as funções Lambda para identificar as ociosas e as com alta taxa de falha, buscando também uma estimativa de custo para estas últimas.")

with right_column:
    st.header("⚙️ Configurações da Análise")
    
    # Seletor de Perfil AWS
    profiles = get_aws_profiles()
    if not profiles:
        st.error("Nenhum perfil AWS encontrado! Verifique se sua pasta `~/.aws` está montada no contêiner.")
        selected_profile = None
    else:
        selected_profile = st.selectbox("Selecione o Perfil AWS:", options=profiles)

    # Outros controles
    periodo_dias = st.slider("Período de Análise (dias)", 1, 90, 30)
    taxa_falha_alvo = st.slider("Taxa de Falha Alvo (%)", 1, 100, 95)
    limite_teste = st.number_input("Limite de funções para testar (0 para todas)", min_value=0, value=10, step=10)
    
    st.write("")
    run_analysis = st.button("🚀 Iniciar Análise", use_container_width=True, disabled=(selected_profile is None))

st.divider()

# --- LÓGICA PRINCIPAL DA APLICAÇÃO ---
if run_analysis:
    if 'df_ociosas' in st.session_state: del st.session_state.df_ociosas
    if 'df_falhas' in st.session_state: del st.session_state.df_falhas

    if not selected_profile:
        st.warning("Um perfil AWS deve ser selecionado para iniciar a análise.")
        st.stop()

    try:
        st.info(f"Iniciando sessão com o perfil AWS: '{selected_profile}'...")
        session = boto3.Session(profile_name=selected_profile)

        sts_client = session.client('sts')
        sts_client.get_caller_identity()
        
        st.success("Sessão AWS iniciada e validada com sucesso.")

        # Inicializa os clientes necessários a partir da sessão
        sts_client = session.client('sts')
        cloudwatch = session.client('cloudwatch')
        cost_explorer = session.client('ce')
        st.success("Sessão AWS iniciada com sucesso.")

    # --- BLOCO DE CAPTURA DO TOKEN EXPIRADO ---
    except SSOTokenLoadError:
        # Chama nossa nova função
        success = handle_sso_login(selected_profile)
        if success:
            # Instrui o usuário a rodar novamente, pois o estado mudou
            st.info("Token renovado! Por favor, clique em 'Iniciar Análise' novamente para continuar.")
        st.stop() # Interrompe a execução atual
        
    except ClientError as e:
        st.error(f"Erro de permissão ou configuração com o perfil '{selected_profile}'. Detalhe: {e.response['Error']['Message']}")
        st.stop()
    except Exception as e:
        st.error(f"Falha ao iniciar a sessão Boto3 com o perfil '{selected_profile}'. Erro: {e}")
        st.stop()

    with st.spinner("Buscando a lista de todas as funções Lambda..."):
        all_functions = list_all_lambda_functions(session)
    
    if not all_functions:
        st.warning("Não foi possível continuar a análise.")
        st.stop()

    function_names = list(all_functions.keys())
    function_names_to_scan = function_names[:limite_teste] if limite_teste > 0 else function_names
    total_to_scan = len(function_names_to_scan)

    st.info(f"Analisando métricas de {total_to_scan} de {len(function_names)} funções encontradas...")

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    lambdas_ociosas = []
    lambdas_com_alta_falha = []
    
    end_time_cw = datetime.utcnow()
    start_time_cw = end_time_cw - timedelta(days=periodo_dias)
    end_date_ce = date.today().strftime("%Y-%m-%d")
    start_date_ce = (date.today() - timedelta(days=periodo_dias)).strftime("%Y-%m-%d")

    # Análise de Métricas
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
            failure_rate = (total_errors / total_invocations) * 100 if total_invocations > 0 else 0
            if failure_rate > taxa_falha_alvo:
                lambdas_com_alta_falha.append({
                    'FunctionName': name, 'FunctionArn': all_functions[name],
                    'FailureRate(%)': round(failure_rate, 2),
                    'Invocations': int(total_invocations), 'Errors': int(total_errors)
                })
    
    status_text.text("Análise de métricas concluída. Buscando custos...")

    # Busca de Custos
    if lambdas_com_alta_falha:
        total_falhas = len(lambdas_com_alta_falha)
        for i, item in enumerate(lambdas_com_alta_falha):
            status_text.text(f"Buscando custo [{i+1}/{total_falhas}]: {item['FunctionName']}")
            progress_bar.progress((i + 1) / total_falhas)
            cost = get_lambda_cost(cost_explorer, item['FunctionArn'], start_date_ce, end_date_ce)
            item['EstimatedCost'] = cost
            del item['FunctionArn']

    status_text.success("✅ Análise concluída!")
    progress_bar.empty()

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