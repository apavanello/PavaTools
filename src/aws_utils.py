# aws_utils.py (ou no topo do seu script)
import streamlit as st
import subprocess
import shutil

def handle_sso_login(profile_name):
    """
    Tenta executar 'aws sso login' para o perfil especificado e exibe as 
    instruções interativas no Streamlit.

    Retorna:
        bool: True se o comando foi executado com sucesso, False caso contrário.
    """
    # Verifica se a AWS CLI está instalada no ambiente
    if not shutil.which("aws"):
        st.error("AWS CLI não encontrada no ambiente do contêiner. Por favor, instale-a para usar a renovação de token SSO.")
        return False

    st.warning(f"O token SSO para o perfil '{profile_name}' está expirado. Siga as instruções abaixo para renová-lo.")
    
    command = ["aws", "sso", "login", "--profile", profile_name]
    
    # Usa um placeholder para exibir a saída do comando em tempo real
    output_placeholder = st.empty()
    output_markdown = "```\n"

    try:
        # Usamos Popen para capturar a saída em tempo real
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        # Lê a saída linha por linha
        for line in iter(process.stdout.readline, ''):
            output_markdown += line
            # A URL de login geralmente não contém "https://", então adicionamos para o link funcionar
            if "https://" in line:
                url = line.strip()
                st.markdown(f"**➡️ Abra este link no seu navegador:** [{url}]({url})")
            
            output_placeholder.markdown(output_markdown + "\n```")
        
        process.stdout.close()
        return_code = process.wait()

        if return_code == 0:
            st.success("Token SSO renovado com sucesso!")
            return True
        else:
            st.error(f"O comando 'aws sso login' falhou com o código de saída {return_code}.")
            return False

    except FileNotFoundError:
        st.error("Comando 'aws' não encontrado. Verifique se a AWS CLI está instalada e no PATH do sistema.")
        return False
    except Exception as e:
        st.error(f"Ocorreu um erro inesperado ao tentar renovar o token SSO: {e}")
        return False