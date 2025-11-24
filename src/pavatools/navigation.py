import streamlit as st
import os

def create_hierarchical_sidebar():
    """
    Cria uma sidebar com navegação hierárquica por categorias.
    Baseado na estrutura de arquivos da aplicação.
    """
    
    # Estrutura hierárquica de navegação
    navigation_structure = {
        "🏠 Início": {
            "icon": "🏠",
            "pages": [
                {"name": "Home", "file": "1_Home.py", "url": "/"}
            ]
        },
        "📊 AWS Reports": {
            "icon": "📊", 
            "pages": [
                {"name": "FinOps Lambda", "file": "3_finops_lambda_report.py", "url": "/3_finops_lambda_report"},
                {"name": "Análise EBS", "file": "4_finops_ebs_report.py", "url": "/4_finops_ebs_report"},
                {"name": "Tags Lambda", "file": "5_lambda_tags_retrival.py", "url": "/5_lambda_tags_retrival"},
                {"name": "Relatório de Uso", "file": "7_lambda_usage_report.py", "url": "/7_lambda_usage_report"}
            ]
        },
        "🔧 Utilitários": {
            "icon": "🔧",
            "pages": [
                {"name": "JSON → CSV", "file": "2_tools_json_to_csv.py", "url": "/2_tools_json_to_csv"}
            ]
        },
        "🔗 Gerenciadores": {
            "icon": "🔗",
            "pages": [
                {"name": "Favoritos", "file": "6_bookmarks_manager.py", "url": "/6_bookmarks_manager"}
            ]
        }
    }
    
    # Título da sidebar
    st.sidebar.markdown("# 🧭 Navegação")
    st.sidebar.markdown("---")
    
    # Verificar página atual para destacar
    current_page = st.session_state.get('current_page', '1_Home.py')
    
    # Navegar pelas categorias
    for category, info in navigation_structure.items():
        icon = info["icon"]
        
        # Header da categoria (sempre visível)
        if st.sidebar.button(f"{icon} **{category}**", key=f"category_{category}"):
            # Toggle category expansion - mantido para compatibilidade futura
            pass
        
        st.sidebar.markdown(f"  *{icon} {category}*")
        
        # Páginas da categoria
        for page in info["pages"]:
            file_name = page["file"]
            page_name = page["name"]
            page_url = page["url"]
            
            # Determinar se é a página atual
            is_current = current_page == file_name
            
            # Botão da página com indicação visual da página atual
            if is_current:
                button_text = f"▶️ {page_name}"
                button_style = "primary"
            else:
                button_text = f"   📄 {page_name}"
                button_style = "secondary"
            
            if st.sidebar.button(button_text, key=f"nav_{file_name}", use_container_width=True):
                if not is_current:
                    # Atualizar sessão e navegar
                    st.session_state['current_page'] = file_name
                    st.session_state['navigation_target'] = page_url
                    st.rerun()
    
    # Separador
    st.sidebar.markdown("---")
    
    # Status da aplicação
    st.sidebar.markdown("### 📊 Status")
    
    # Contar páginas por categoria
    total_pages = sum(len(info["pages"]) for info in navigation_structure.values())
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("📄 Páginas", total_pages)
    with col2:
        st.metric("📁 Categorias", len(navigation_structure))
    
    # Informações do sistema
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ℹ️ Sistema")
    
    # Verificar arquivos que existem
    missing_files = []
    for category_info in navigation_structure.values():
        for page in category_info["pages"]:
            file_path = f"src/pages/{page['file']}"
            if not os.path.exists(file_path):
                missing_files.append(page['file'])
    
    if missing_files:
        st.sidebar.warning(f"⚠️ {len(missing_files)} arquivo(s) não encontrado(s)")
    else:
        st.sidebar.success("✅ Todos os arquivos encontrados")

def get_current_page_info():
    """
    Retorna informações sobre a página atual.
    """
    current_page = st.session_state.get('current_page', '1_Home.py')
    
    # Estrutura reversa para encontrar página atual
    navigation_structure = {
        "1_Home.py": {"category": "🏠 Início", "name": "Home"},
        "2_tools_json_to_csv.py": {"category": "🔧 Utilitários", "name": "JSON → CSV"},
        "3_finops_lambda_report.py": {"category": "📊 AWS Reports", "name": "FinOps Lambda"},
        "4_finops_ebs_report.py": {"category": "📊 AWS Reports", "name": "Análise EBS"},
        "5_lambda_tags_retrival.py": {"category": "📊 AWS Reports", "name": "Tags Lambda"},
        "7_lambda_usage_report.py": {"category": "📊 AWS Reports", "name": "Relatório de Uso"},
        "6_bookmarks_manager.py": {"category": "🔗 Gerenciadores", "name": "Favoritos"}
    }
    
    return navigation_structure.get(current_page, {"category": "Desconhecido", "name": "Página Atual"})

def set_page_context(page_filename):
    """
    Define o contexto da página atual.
    """
    st.session_state['current_page'] = page_filename
    
    # Se há um target de navegação, processar
    if 'navigation_target' in st.session_state:
        target = st.session_state['navigation_target']
        del st.session_state['navigation_target']
        
        # Navegar para o target
        try:
            st.experimental_set_query_params(page=target.replace('/', ''))
        except:
            pass