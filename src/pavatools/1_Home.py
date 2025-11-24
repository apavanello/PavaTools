import streamlit as st
from navigation import create_hierarchical_sidebar, set_page_context

# Configura o título que aparece na aba do navegador
st.set_page_config(
    page_title="Minha Caixa de Ferramentas",
    page_icon="🧰",
)

# Definir contexto da página atual
set_page_context("1_Home.py")

# Criar navegação hierárquica na sidebar
create_hierarchical_sidebar()

# Título principal da página
st.title("🧰 Minha Caixa de Ferramentas Pessoal")

st.write("Bem-vindo ao meu painel de ferramentas!")
st.write("Use o menu na barra lateral à esquerda para navegar entre as ferramentas.")

# Seção de recursos disponíveis
st.markdown("### 🚀 Recursos Disponíveis:")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **📊 Análise AWS:**
    - 📡 Relatórios de Lambdas
    - 🏷️ Tags do Lambda
    - 💰 Análise FinOps EBS
    
    **🔧 Utilitários:**
    - 🔄 Conversor JSON para CSV
    """)

with col2:
    st.markdown("""
    **🔗 Gerenciador de Favoritos:**
    - Organize links por categorias
    - Ferramentas AWS, DevOps, Programação
    - Importação/Exportação
    - Sistema de tags e busca
    """)

st.markdown("---")
# --- Rodapé ---
st.markdown("---")
st.write("Desenvolvido com ❤️ usando Python e Streamlit.")