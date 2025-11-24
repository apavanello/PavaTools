import streamlit as st
import boto3
import pandas as pd
import io
from botocore.exceptions import ClientError, SSOTokenLoadError
import subprocess
import shutil
from navigation import create_hierarchical_sidebar, set_page_context

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Enriquecedor de Tags Lambda",
    layout="wide"
)

# Definir contexto da página atual
set_page_context("5_lambda_tags_retrival.py")

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

def get_lambda_tags(lambda_client, function_name):
    """
    Busca as tags de uma função Lambda específica.

    Retorna:
        str: Uma string formatada com as tags ou uma mensagem de status.
    """
    try:
        # Precisamos do ARN para listar as tags
        response_config = lambda_client.get_function_configuration(FunctionName=function_name)
        function_arn = response_config['FunctionArn']
        
        # Agora buscamos as tags usando o ARN
        response_tags = lambda_client.list_tags(Resource=function_arn)
        
        tags = response_tags.get('Tags', {})
        if not tags:
            return "Sem Tags"
        
        # Formata o dicionário de tags em uma string legível
        return "; ".join([f"{key}={value}" for key, value in tags.items()])

    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return "Lambda Não Encontrada"
        else:
            # Retorna a mensagem de erro da API para depuração
            return f"Erro de Permissão: {e.response['Error']['Code']}"
    except Exception as e:
        return f"Erro Inesperado: {str(e)}"

# --- INTERFACE DO USUÁRIO ---

st.title("🏷️ Enriquecedor de CSV com Tags de Lambdas")
st.markdown("Faça o upload de um arquivo CSV contendo nomes de funções Lambda para adicionar uma coluna com suas respectivas tags da AWS.")

# Limpar resultados anteriores se um novo arquivo for carregado
if 'last_uploaded_file' not in st.session_state:
    st.session_state.last_uploaded_file = None

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
if uploaded_file and uploaded_file.name != st.session_state.last_uploaded_file:
    st.session_state.last_uploaded_file = uploaded_file.name
    if 'processed_df' in st.session_state:
        del st.session_state.processed_df

selected_column = None
if uploaded_file:
    try:
        # Lê apenas as primeiras linhas para obter os cabeçalhos rapidamente
        df_columns = pd.read_csv(uploaded_file, nrows=0).columns.tolist()
        selected_column = st.selectbox("3. Selecione a coluna com os nomes das Lambdas:", options=df_columns)
    except Exception as e:
        st.error(f"Não foi possível ler o arquivo CSV: {e}")

run_enrichment = st.button("🚀 Iniciar Processamento", disabled=(not all([selected_profile, uploaded_file, selected_column])))

# --- ÁREA PRINCIPAL E LÓGICA DE PROCESSAMENTO ---
if run_enrichment:
    try:
        # Validação do token SSO e criação da sessão
        session = boto3.Session(profile_name=selected_profile)
        sts_client = session.client('sts')
        sts_client.get_caller_identity()
        lambda_client = session.client('lambda')

        # Lê o CSV completo para processamento
        df = pd.read_csv(uploaded_file)
        
        st.info(f"Processando {len(df)} linhas do arquivo CSV...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        tags_list = []
        # Itera sobre o dataframe para buscar as tags de cada lambda
        for index, row in df.iterrows():
            lambda_name = row[selected_column]
            status_text.text(f"Buscando tags para: {lambda_name}")
            
            tags = get_lambda_tags(lambda_client, lambda_name)
            tags_list.append(tags)
            
            progress_bar.progress((index + 1) / len(df))
            
        # Adiciona a nova coluna com os resultados
        df['AWS_Tags'] = tags_list
        st.session_state.processed_df = df # Salva no estado da sessão
        
        status_text.empty()
        progress_bar.empty()
        st.success("Processamento concluído com sucesso!")

    except SSOTokenLoadError:
        success = handle_sso_login(selected_profile)
        if success:
            st.info("Token renovado! Clique em 'Iniciar Processamento' novamente para continuar.")
    except ClientError as e:
        st.error(f"Erro de permissão com o perfil '{selected_profile}': {e.response['Error']['Message']}")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

# Exibe os resultados se eles existirem no estado da sessão
if 'processed_df' in st.session_state:
    st.header("📊 Resultado")
    st.dataframe(st.session_state.processed_df, use_container_width=True)
    
    # Converte o dataframe para CSV em memória para o download
    csv_output = st.session_state.processed_df.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Baixar CSV com Tags",
        data=csv_output,
        file_name=f"lambdas_com_tags.csv",
        mime='text/csv'
    )
elif not run_enrichment:
     st.info("Configure as opções na barra lateral e clique em 'Iniciar Processamento'.")