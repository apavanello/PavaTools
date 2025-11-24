import streamlit as st
import boto3
import pandas as pd
import io
from botocore.exceptions import ClientError, SSOTokenLoadError
import subprocess
import shutil
from datetime import datetime, timezone
from navigation import create_hierarchical_sidebar, set_page_context

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Relatório de Uso de Lambdas",
    layout="wide"
)

# Definir contexto da página atual
set_page_context("7_lambda_usage_report.py")

# Criar navegação hierárquica na sidebar
create_hierarchical_sidebar()

# --- FUNÇÕES REUTILIZÁVEIS DA AWS ---

@st.cache_data(ttl=3600)
def get_aws_profiles():
    """Usa boto3 para listar todos os perfis disponíveis."""
    try:
        return boto3.Session().available_profiles
    except Exception:
        return []

def handle_sso_login(profile_name):
    """Executa 'aws sso login' e exibe as instruções no Streamlit."""
    if not shutil.which("aws"):
        st.error("AWS CLI não encontrada no ambiente do contêiner.")
        return False

    st.warning(f"O token SSO para o perfil '{profile_name}' está expirado. Siga as instruções para renovar.")
    command = ["aws", "sso", "login", "--profile", profile_name]
    output_placeholder = st.empty()
    output_markdown = "```\n"

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in iter(process.stdout.readline, ''):
            output_markdown += line
            if "https://device.sso" in line:
                url = line.strip()
                st.markdown(f"**➡️ Abra este link no seu navegador:** [{url}]({url})")
            output_placeholder.markdown(output_markdown + "\n```")
        
        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            st.success("Token SSO renovado com sucesso!")
            return True
        else:
            st.error(f"O comando 'aws sso login' falhou.")
            return False
    except Exception as e:
        st.error(f"Ocorreu um erro ao tentar renovar o token SSO: {e}")
        return False

# --- FUNÇÃO PRINCIPAL DE LÓGICA ---

def get_lambda_last_execution(logs_client, function_name):
    """
    Busca a data da última execução de uma função Lambda através do CloudWatch Logs.

    Retorna:
        dict: Dicionário com 'Last_Execution_Date' e 'Days_Without_Use'.
    """
    log_group_name = f"/aws/lambda/{function_name}"
    
    try:
        # Busca o último stream de log ordenado por tempo
        response = logs_client.describe_log_streams(
            logGroupName=log_group_name,
            orderBy='LastEventTime',
            descending=True,
            limit=1
        )
        
        streams = response.get('logStreams', [])
        
        if not streams:
            return {
                "Last_Execution_Date": "Sem Logs (Nunca executou ou logs desativados)",
                "Days_Without_Use": "N/A"
            }
            
        last_event_timestamp = streams[0].get('lastEventTimestamp')
        
        if not last_event_timestamp:
             return {
                "Last_Execution_Date": "Stream vazio",
                "Days_Without_Use": "N/A"
            }

        # Converte timestamp (ms) para datetime
        last_execution_dt = datetime.fromtimestamp(last_event_timestamp / 1000.0, tz=timezone.utc)
        now = datetime.now(timezone.utc)
        
        days_without_use = (now - last_execution_dt).days
        
        return {
            "Last_Execution_Date": last_execution_dt.strftime('%Y-%m-%d %H:%M:%S UTC'),
            "Days_Without_Use": days_without_use
        }

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return {
                "Last_Execution_Date": "Log Group não encontrado",
                "Days_Without_Use": "N/A"
            }
        else:
            return {
                "Last_Execution_Date": f"Erro: {e.response['Error']['Code']}",
                "Days_Without_Use": "Erro"
            }
    except Exception as e:
        return {
            "Last_Execution_Date": f"Erro Inesperado: {str(e)}",
            "Days_Without_Use": "Erro"
        }

# --- INTERFACE DO USUÁRIO ---

st.title("🕒 Relatório de Uso de Lambdas (Last Execution)")
st.markdown("Faça o upload de um arquivo CSV contendo nomes de funções Lambda para calcular o tempo desde a última execução.")

# Limpar resultados anteriores se um novo arquivo for carregado
if 'last_uploaded_file_usage' not in st.session_state:
    st.session_state.last_uploaded_file_usage = None

# --- BARRA LATERAL DE CONFIGURAÇÃO ---

st.header("⚙️ Configurações")

profiles = get_aws_profiles()
if not profiles:
    st.error("Nenhum perfil AWS encontrado. Monte sua pasta `~/.aws`.")
    selected_profile = None
else:
    selected_profile = st.selectbox("1. Selecione o Perfil AWS:", options=profiles)

uploaded_file = st.file_uploader("2. Faça o upload do arquivo CSV", type=["csv"])

# Se o arquivo mudou, reseta os resultados
if uploaded_file and uploaded_file.name != st.session_state.last_uploaded_file_usage:
    st.session_state.last_uploaded_file_usage = uploaded_file.name
    if 'processed_usage_df' in st.session_state:
        del st.session_state.processed_usage_df

selected_column = None
if uploaded_file:
    try:
        # Lê apenas as primeiras linhas para obter os cabeçalhos rapidamente
        df_columns = pd.read_csv(uploaded_file, nrows=0).columns.tolist()
        selected_column = st.selectbox("3. Selecione a coluna com os nomes das Lambdas:", options=df_columns)
    except Exception as e:
        st.error(f"Não foi possível ler o arquivo CSV: {e}")

run_report = st.button("🚀 Gerar Relatório", disabled=(not all([selected_profile, uploaded_file, selected_column])))

# --- ÁREA PRINCIPAL E LÓGICA DE PROCESSAMENTO ---
if run_report:
    try:
        # Validação do token SSO e criação da sessão
        session = boto3.Session(profile_name=selected_profile)
        sts_client = session.client('sts')
        sts_client.get_caller_identity()
        logs_client = session.client('logs') # Precisamos do cliente de Logs, não Lambda

        # Lê o CSV completo para processamento
        df = pd.read_csv(uploaded_file)
        
        st.info(f"Processando {len(df)} linhas do arquivo CSV...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results_list = []
        # Itera sobre o dataframe
        for index, row in df.iterrows():
            lambda_name = row[selected_column]
            status_text.text(f"Verificando logs para: {lambda_name}")
            
            result = get_lambda_last_execution(logs_client, lambda_name)
            results_list.append(result)
            
            progress_bar.progress((index + 1) / len(df))
            
        # Adiciona as novas colunas com os resultados
        results_df = pd.DataFrame(results_list)
        df = pd.concat([df, results_df], axis=1)
        
        st.session_state.processed_usage_df = df # Salva no estado da sessão
        
        status_text.empty()
        progress_bar.empty()
        st.success("Relatório gerado com sucesso!")

    except SSOTokenLoadError:
        success = handle_sso_login(selected_profile)
        if success:
            st.info("Token renovado! Clique em 'Gerar Relatório' novamente para continuar.")
    except ClientError as e:
        st.error(f"Erro de permissão com o perfil '{selected_profile}': {e.response['Error']['Message']}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

# Exibe os resultados se eles existirem no estado da sessão
if 'processed_usage_df' in st.session_state:
    st.header("📊 Resultado")
    st.dataframe(st.session_state.processed_usage_df, use_container_width=True)
    
    # Converte o dataframe para CSV em memória para o download
    csv_output = st.session_state.processed_usage_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Baixar Relatório (CSV)",
        data=csv_output,
        file_name=f"lambda_usage_report.csv",
        mime='text/csv'
    )
elif not run_report:
     st.info("Configure as opções na barra lateral e clique em 'Gerar Relatório'.")
