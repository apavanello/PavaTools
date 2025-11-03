import streamlit as st
import pandas as pd
import json

# --- Configuração da Página ---
st.set_page_config(
    page_title="Conversor de JSON para CSV",
    page_icon="🔄",
    layout="centered",
    initial_sidebar_state="auto"
)

# --- Funções Auxiliares ---

@st.cache_data
def convert_df_to_csv(df):
    """
    Converte um DataFrame do Pandas para uma string CSV,
    codificada em UTF-8 e sem o índice.
    """
    return df.to_csv(index=False, encoding='utf-8')

# --- Interface da Aplicação ---

st.title("Conversor de JSON para CSV 🔄")

st.markdown("""
Esta aplicação permite que você converta facilmente um array de objetos JSON para o formato CSV.

**Como usar:**
1.  **Faça o upload** do seu arquivo JSON no campo abaixo.
2.  Aguarde a aplicação processar o arquivo.
3.  **Clique no botão de download** para baixar o seu arquivo CSV.
""")

# --- Upload do Arquivo JSON ---
uploaded_file = st.file_uploader(
    "Escolha um arquivo JSON",
    type="json"
)

if uploaded_file is not None:
    try:
        # Lendo e decodificando o arquivo JSON
        json_data = json.load(uploaded_file)

        # Verificando se o JSON é uma lista de objetos (array)
        if isinstance(json_data, list) and all(isinstance(item, dict) for item in json_data):

            st.success("Arquivo JSON carregado com sucesso!")

            # Convertendo o JSON para um DataFrame do Pandas
            df = pd.DataFrame(json_data)

            st.subheader("Pré-visualização dos Dados")
            st.dataframe(df.head())

            # Convertendo o DataFrame para CSV
            csv_data = convert_df_to_csv(df)

            # --- Botão de Download ---
            st.download_button(
               label="📥 Baixar Arquivo CSV",
               data=csv_data,
               file_name="dados_convertidos.csv",
               mime="text/csv",
            )
        else:
            st.error("Erro: O arquivo JSON não parece ser um array de objetos. Por favor, verifique o formato do seu arquivo.")

    except json.JSONDecodeError:
        st.error("Erro: O arquivo enviado não é um JSON válido. Por favor, verifique o conteúdo do arquivo.")
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado: {e}")

# --- Rodapé ---
st.markdown("---")
st.write("Desenvolvido com ❤️ usando Python e Streamlit.")