import streamlit as st

# Configura o título que aparece na aba do navegador
st.set_page_config(
    page_title="Minha Caixa de Ferramentas",
    page_icon="🧰",
)

# Título principal da página
st.title("🧰 Minha Caixa de Ferramentas Pessoal")

st.write("Bem-vindo ao meu painel de ferramentas!")
st.write("Use o menu na barra lateral à esquerda para navegar entre as ferramentas.")

st.sidebar.success("Selecione uma ferramenta acima.")
# --- Rodapé ---
st.markdown("---")
st.write("Desenvolvido com ❤️ usando Python e Streamlit.")