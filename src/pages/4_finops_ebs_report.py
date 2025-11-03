import streamlit as st
import boto3
import pandas as pd
import io
from botocore.exceptions import ClientError

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(
    page_title="Analisador de Volumes EBS Órfãos",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- DADOS E FUNÇÕES AUXILIARES ---

# Dicionário de preços. Em uma aplicação real, isso poderia vir de um arquivo de configuração.
EBS_PRICING_PER_GB_MONTH = {
    'sa-east-1': {'gp3': 0.096, 'gp2': 0.12, 'io1': 0.138, 'io2': 0.138, 'st1': 0.054, 'sc1': 0.018, 'standard': 0.06},
    'us-east-1': {'gp3': 0.08, 'gp2': 0.10, 'io1': 0.125, 'io2': 0.125, 'st1': 0.045, 'sc1': 0.015, 'standard': 0.05},
    'us-east-2': {'gp3': 0.08, 'gp2': 0.10, 'io1': 0.125, 'io2': 0.125, 'st1': 0.045, 'sc1': 0.025, 'standard': 0.05},
    'us-west-1': {'gp3': 0.096, 'gp2': 0.12, 'io1': 0.138, 'io2': 0.138, 'st1': 0.054, 'sc1': 0.028, 'standard': 0.06},
    'us-west-2': {'gp3': 0.08, 'gp2': 0.10, 'io1': 0.125, 'io2': 0.125, 'st1': 0.045, 'sc1': 0.023, 'standard': 0.05}
    # Adicione outras regiões e preços conforme necessário
}

@st.cache_data(ttl=3600)
def get_aws_profiles():
    """Usa boto3 para listar todos os perfis disponíveis nos arquivos de config/credentials."""
    try:
        return boto3.Session().available_profiles
    except Exception:
        return []

@st.cache_data(ttl=86400)
def get_aws_regions(session):
    """Busca a lista de todas as regiões EC2 disponíveis usando a sessão fornecida."""
    try:
        return session.get_available_regions('ec2')
    except ClientError:
        st.warning("Credenciais inválidas ou sem permissão para listar regiões. Usando uma lista padrão.")
        return ['us-east-1', 'us-east-2', 'us-west-1', 'us-west-2', 'sa-east-1']

def format_tags(tags_list):
    """Formata a lista de tags em uma string legível."""
    if not tags_list:
        return "N/A"
    return "; ".join([f"{tag['Key']}={tag['Value']}" for tag in tags_list])

def analyze_orphaned_volumes(session, regions_to_check):
    """
    Busca por volumes EBS órfãos nas regiões especificadas e retorna um DataFrame.
    """
    all_orphaned_volumes = []
    
    status_placeholder = st.empty()
    progress_bar = st.progress(0)

    for i, region in enumerate(regions_to_check):
        status_placeholder.info(f"🔎 Verificando a região: {region}...")
        progress_bar.progress((i + 1) / len(regions_to_check))
        
        try:
            ec2_client = session.client('ec2', region_name=region)
            paginator = ec2_client.get_paginator('describe_volumes')
            # Filtra volumes cujo estado é 'available' (disponível/não anexado)
            pages = paginator.paginate(Filters=[{'Name': 'status', 'Values': ['available']}])

            for page in pages:
                for volume in page['Volumes']:
                    volume_type = volume['VolumeType']
                    size_gb = volume['Size']
                    
                    # Estimar o custo mensal
                    region_pricing = EBS_PRICING_PER_GB_MONTH.get(region, {})
                    price_per_gb = region_pricing.get(volume_type, 0)
                    estimated_cost = round(size_gb * price_per_gb, 2)
                    
                    volume_details = {
                        'ID do Volume': volume['VolumeId'],
                        'Região': region,
                        'Tamanho (GB)': size_gb,
                        'Tipo': volume_type,
                        'Custo Mensal Estimado (USD)': estimated_cost,
                        'Data de Criação': volume['CreateTime'].strftime('%Y-%m-%d %H:%M:%S'),
                        'Tags': format_tags(volume.get('Tags', []))
                    }
                    all_orphaned_volumes.append(volume_details)
                    
        except ClientError as e:
            st.error(f"Erro de permissão ou de API na região {region}: {e.response['Error']['Message']}. Pulando...")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado na região {region}: {e}. Pulando...")

    status_placeholder.empty()
    progress_bar.empty()
    return pd.DataFrame(all_orphaned_volumes)

# --- INTERFACE DO USUÁRIO ---

st.title("💸 Analisador de Volumes EBS Órfãos")
st.markdown("Esta ferramenta verifica as regiões AWS selecionadas em busca de volumes EBS não anexados (órfãos) e estima o custo mensal associado a eles.")


st.header("⚙️ Configurações")

profiles = get_aws_profiles()

if not profiles:
    st.error(
        "Nenhum perfil AWS encontrado! "
        "Certifique-se de que sua pasta `~/.aws` está montada corretamente no contêiner."
    )
    selected_profile = None
else:
    selected_profile = st.selectbox(
        "Selecione o Perfil AWS:",
        options=profiles
    )

if selected_profile:
    temp_session = boto3.Session(profile_name=selected_profile)
    available_regions = get_aws_regions(temp_session)
    
    selected_regions = st.multiselect(
        "Selecione as regiões da AWS para analisar:",
        options=available_regions,
        default=['us-east-1', 'sa-east-1']
    )
else:
    selected_regions = []

run_analysis = st.button("🚀 Buscar Volumes Órfãos", disabled=(selected_profile is None))

# --- LÓGICA PRINCIPAL E EXIBIÇÃO DE RESULTADOS ---

if run_analysis:
    if not selected_regions:
        st.warning("Por favor, selecione pelo menos uma região para analisar.")
    else:
        try:
            session = boto3.Session(profile_name=selected_profile)
            df_orphaned = analyze_orphaned_volumes(session, selected_regions)
            
            st.header("📊 Resultados da Análise")
            
            if df_orphaned.empty:
                st.success("✅ Nenhum volume EBS órfão encontrado nas regiões selecionadas. Bom trabalho!")
            else:
                total_volumes = len(df_orphaned)
                total_cost = df_orphaned['Custo Mensal Estimado (USD)'].sum()
                
                # Exibir métricas de resumo
                col1, col2 = st.columns(2)
                col1.metric("Volumes Órfãos Encontrados", f"{total_volumes}")
                col2.metric("Custo Mensal Total Estimado", f"$ {total_cost:.2f}")
                
                st.markdown("### Detalhes dos Volumes")
                st.dataframe(df_orphaned, use_container_width=True)
                
                # --- Funcionalidade de Download ---
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_orphaned.to_excel(writer, index=False, sheet_name='Volumes_Orfaos')
                
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Baixar Relatório em Excel",
                    data=excel_data,
                    file_name='relatorio_volumes_ebs_orfaos.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )

        except ClientError as e:
            st.error(f"Erro de credenciais ou permissão com o perfil '{selected_profile}'. Verifique se o perfil é válido e tem as permissões necessárias. Detalhe: {e.response['Error']['Message']}")
        except Exception as e:
            st.error(f"Ocorreu um erro inesperado: {e}")

else:
    st.info("Selecione um perfil e as regiões na barra lateral e clique em 'Buscar Volumes Órfãos' para iniciar a análise.")