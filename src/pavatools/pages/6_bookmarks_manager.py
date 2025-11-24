import streamlit as st
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse
import pandas as pd
from navigation import create_hierarchical_sidebar, set_page_context

# --- Configuração da Página ---
st.set_page_config(
    page_title="Gerenciador de Favoritos",
    page_icon="🔗",
    layout="wide",
    initial_sidebar_state="auto"
)

# Definir contexto da página atual
set_page_context("6_bookmarks_manager.py")

# Criar navegação hierárquica na sidebar
create_hierarchical_sidebar()

# --- Constantes ---
BOOKMARKS_FILE = "bookmarks.json"
DEFAULT_CATEGORIES = ["Ferramentas AWS", "DevOps", "Programação", "APIs", "Documentação"]

# --- Funções Auxiliares ---
def validate_url(url):
    """Valida se a URL está em formato correto."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except:
        return False

def load_bookmarks():
    """Carrega os favoritos do arquivo JSON ou retorna dados padrão se não existir."""
    if os.path.exists(BOOKMARKS_FILE):
        try:
            with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Erro ao carregar favoritos: {e}")
            return create_default_bookmarks()
    else:
        return create_default_bookmarks()

def save_bookmarks(bookmarks):
    """Salva os favoritos no arquivo JSON."""
    try:
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar favoritos: {e}")
        return False

def create_default_bookmarks():
    """Cria bookmarks padrão com 10 exemplos."""
    default_bookmarks = [
        {
            "id": 1,
            "title": "AWS Console",
            "url": "https://console.aws.amazon.com",
            "category": "Ferramentas AWS",
            "description": "Console principal da AWS para gerenciar recursos",
            "created_at": "2024-01-15T10:30:00",
            "tags": ["aws", "console", "cloud"]
        },
        {
            "id": 2,
            "title": "Docker Hub",
            "url": "https://hub.docker.com",
            "category": "DevOps",
            "description": "Repositório oficial de imagens Docker",
            "created_at": "2024-02-01T14:20:00",
            "tags": ["docker", "containers", "devops"]
        },
        {
            "id": 3,
            "title": "GitHub",
            "url": "https://github.com",
            "category": "Programação",
            "description": "Plataforma de hospedagem de código-fonte",
            "created_at": "2024-01-20T09:15:00",
            "tags": ["git", "versionamento", "colaboração"]
        },
        {
            "id": 4,
            "title": "REST API Tutorial",
            "url": "https://restfulapi.net",
            "category": "APIs",
            "description": "Tutorial completo sobre APIs REST",
            "created_at": "2024-01-25T16:45:00",
            "tags": ["rest", "api", "web"]
        },
        {
            "id": 5,
            "title": "Python Documentation",
            "url": "https://docs.python.org/3",
            "category": "Documentação",
            "description": "Documentação oficial do Python",
            "created_at": "2024-02-05T11:00:00",
            "tags": ["python", "docs", "programming"]
        },
        {
            "id": 6,
            "title": "AWS CLI Reference",
            "url": "https://docs.aws.amazon.com/cli/",
            "category": "Documentação",
            "description": "Documentação da interface de linha de comando da AWS",
            "created_at": "2024-02-10T13:30:00",
            "tags": ["aws", "cli", "documentation"]
        },
        {
            "id": 7,
            "title": "Kubernetes",
            "url": "https://kubernetes.io",
            "category": "DevOps",
            "description": "Plataforma de orquestração de contêineres",
            "created_at": "2024-02-12T15:20:00",
            "tags": ["kubernetes", "orchestration", "containers"]
        },
        {
            "id": 8,
            "title": "Stack Overflow",
            "url": "https://stackoverflow.com",
            "category": "Programação",
            "description": "Comunidade para desenvolvedores tirarem dúvidas",
            "created_at": "2024-02-15T10:45:00",
            "tags": ["community", "help", "programming"]
        },
        {
            "id": 9,
            "title": "Postman",
            "url": "https://postman.com",
            "category": "APIs",
            "description": "Ferramenta para testar APIs REST",
            "created_at": "2024-02-18T14:10:00",
            "tags": ["postman", "api", "testing"]
        },
        {
            "id": 10,
            "title": "AWS Lambda Console",
            "url": "https://console.aws.amazon.com/lambda",
            "category": "Ferramentas AWS",
            "description": "Console para gerenciar funções Lambda",
            "created_at": "2024-02-20T12:00:00",
            "tags": ["lambda", "serverless", "aws"]
        }
    ]
    save_bookmarks(default_bookmarks)
    return default_bookmarks

def add_bookmark(title, url, category, description, tags):
    """Adiciona um novo favorito."""
    bookmarks = load_bookmarks()
    new_id = max([b['id'] for b in bookmarks], default=0) + 1
    
    bookmark = {
        "id": new_id,
        "title": title,
        "url": url,
        "category": category,
        "description": description,
        "created_at": datetime.now().isoformat(),
        "tags": [tag.strip() for tag in tags.split(',') if tag.strip()]
    }
    
    bookmarks.append(bookmark)
    if save_bookmarks(bookmarks):
        st.success("Favorito adicionado com sucesso!")
        return True
    return False

def update_bookmark(bookmark_id, title, url, category, description, tags):
    """Atualiza um favorito existente."""
    bookmarks = load_bookmarks()
    
    for bookmark in bookmarks:
        if bookmark['id'] == bookmark_id:
            bookmark['title'] = title
            bookmark['url'] = url
            bookmark['category'] = category
            bookmark['description'] = description
            bookmark['tags'] = [tag.strip() for tag in tags.split(',') if tag.strip()]
            break
    
    if save_bookmarks(bookmarks):
        st.success("Favorito atualizado com sucesso!")
        return True
    return False

def delete_bookmark(bookmark_id):
    """Remove um favorito."""
    bookmarks = load_bookmarks()
    bookmarks = [b for b in bookmarks if b['id'] != bookmark_id]
    
    if save_bookmarks(bookmarks):
        st.success("Favorito removido com sucesso!")
        return True
    return False

def export_bookmarks():
    """Exporta todos os favoritos para download."""
    bookmarks = load_bookmarks()
    df = pd.DataFrame(bookmarks)
    csv = df.to_csv(index=False, encoding='utf-8')
    return csv

def import_bookmarks(file):
    """Importa favoritos de um arquivo CSV."""
    try:
        df = pd.read_csv(file)
        bookmarks = df.to_dict('records')
        
        # Adiciona IDs sequenciais se não existirem
        current_bookmarks = load_bookmarks()
        max_id = max([b['id'] for b in current_bookmarks], default=0)
        
        for i, bookmark in enumerate(bookmarks):
            if 'id' not in bookmark:
                bookmark['id'] = max_id + i + 1
            if 'created_at' not in bookmark:
                bookmark['created_at'] = datetime.now().isoformat()
            if 'tags' not in bookmark or bookmark['tags'] == '':
                bookmark['tags'] = []
            elif isinstance(bookmark['tags'], str):
                bookmark['tags'] = [tag.strip() for tag in bookmark['tags'].split(',')]
        
        all_bookmarks = current_bookmarks + bookmarks
        if save_bookmarks(all_bookmarks):
            st.success(f"{len(bookmarks)} favoritos importados com sucesso!")
            return True
    except Exception as e:
        st.error(f"Erro ao importar favoritos: {e}")
        return False

# --- Interface Principal ---
st.title("🔗 Gerenciador de Favoritos")

st.markdown("""
Gerencie seus favoritos de forma organizada por categorias. Adicione, edite, exclua e pesquise 
links úteis organizados em categorias específicas para ferramentas AWS, DevOps, Programação, 
APIs e Documentação.
""")

# --- Controles na Área Principal ---
bookmarks_data = load_bookmarks()
categories = list(set(DEFAULT_CATEGORIES + [b['category'] for b in bookmarks_data]))
categories.sort()

col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    selected_category = st.selectbox(
        "Filtrar por Categoria:",
        options=["Todas"] + categories,
        index=0
    )

with col2:
    search_term = st.text_input("🔍 Buscar favoritos:", placeholder="Digite o título, descrição ou tags...")

with col3:
    st.write("")
    if st.button("➕ Novo Favorito", use_container_width=True):
        st.session_state.show_add_form = True

# Botões de importação/exportação
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("📤 Exportar", use_container_width=True):
        csv_data = export_bookmarks()
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name=f"bookmarks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

with col2:
    uploaded_file = st.file_uploader("📥 Importar CSV", type=['csv'])
    
with col3:
    if uploaded_file is not None and st.button("Processar Import", use_container_width=True):
        import_bookmarks(uploaded_file)
        st.rerun()

# --- Formulário de Adicionar/Editar Favorito ---
if 'show_add_form' not in st.session_state:
    st.session_state.show_add_form = False

if 'editing_bookmark' not in st.session_state:
    st.session_state.editing_bookmark = None

if st.session_state.show_add_form or st.session_state.editing_bookmark:
    with st.expander("📝 Formulário de Favorito", expanded=True):
        # Preencher dados se estiver editando
        if st.session_state.editing_bookmark:
            current = next(b for b in bookmarks_data if b['id'] == st.session_state.editing_bookmark)
            title = st.text_input("Título:", value=current['title'], key="edit_title")
            url = st.text_input("URL:", value=current['url'], key="edit_url")
            category = st.selectbox(
                "Categoria:",
                options=DEFAULT_CATEGORIES,
                index=DEFAULT_CATEGORIES.index(current['category']) if current['category'] in DEFAULT_CATEGORIES else 0,
                key="edit_category"
            )
            description = st.text_area("Descrição:", value=current['description'], key="edit_description")
            tags = st.text_input(
                "Tags (separadas por vírgula):",
                value=", ".join(current['tags']) if current['tags'] else "",
                key="edit_tags"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Salvar Alterações", use_container_width=True):
                    if title and url and validate_url(url):
                        update_bookmark(
                            st.session_state.editing_bookmark,
                            title, url, category, description, tags
                        )
                        st.session_state.show_add_form = False
                        st.session_state.editing_bookmark = None
                        st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios com uma URL válida.")
            
            with col2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.show_add_form = False
                    st.session_state.editing_bookmark = None
                    st.rerun()
        else:
            # Formulário para novo favorito
            title = st.text_input("Título:", placeholder="Ex: AWS Console", key="new_title")
            url = st.text_input("URL:", placeholder="https://exemplo.com", key="new_url")
            category = st.selectbox(
                "Categoria:",
                options=DEFAULT_CATEGORIES,
                key="new_category"
            )
            description = st.text_area("Descrição:", placeholder="Breve descrição do que é este link...", key="new_description")
            tags = st.text_input(
                "Tags (separadas por vírgula):",
                placeholder="aws, cloud, console",
                key="new_tags"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ Adicionar Favorito", use_container_width=True):
                    if title and url and validate_url(url):
                        add_bookmark(title, url, category, description, tags)
                        st.session_state.show_add_form = False
                        st.rerun()
                    else:
                        st.error("Por favor, preencha todos os campos obrigatórios com uma URL válida.")
            
            with col2:
                if st.button("❌ Cancelar", use_container_width=True):
                    st.session_state.show_add_form = False
                    st.rerun()

# --- Exibição dos Favoritos ---
st.markdown("---")

# Filtrar favoritos
filtered_bookmarks = bookmarks_data

if selected_category != "Todas":
    filtered_bookmarks = [b for b in filtered_bookmarks if b['category'] == selected_category]

if search_term:
    search_term_lower = search_term.lower()
    filtered_bookmarks = [
        b for b in filtered_bookmarks 
        if search_term_lower in b['title'].lower() or
           search_term_lower in b['description'].lower() or
           any(search_term_lower in tag.lower() for tag in b.get('tags', []))
    ]

# Exibir favoritos
if filtered_bookmarks:
    st.subheader(f"📚 Favoritos ({len(filtered_bookmarks)})")
    
    # Agrupar por categoria
    bookmarks_by_category = {}
    for bookmark in filtered_bookmarks:
        cat = bookmark['category']
        if cat not in bookmarks_by_category:
            bookmarks_by_category[cat] = []
        bookmarks_by_category[cat].append(bookmark)
    
    # Mostrar cada categoria
    for category, bookmarks in bookmarks_by_category.items():
        with st.expander(f"🏷️ {category} ({len(bookmarks)})", expanded=True):
            for bookmark in bookmarks:
                col1, col2, col3, col4 = st.columns([4, 1, 1, 1])
                
                with col1:
                    st.markdown(f"**{bookmark['title']}**")
                    st.markdown(f"🔗 [{bookmark['url']}]({bookmark['url']})")
                    st.markdown(f"*{bookmark['description']}*")
                    if bookmark['tags']:
                        tags_str = " ".join([f"#{tag}" for tag in bookmark['tags']])
                        st.markdown(f"🏷️ {tags_str}")
                    st.markdown(f"📅 Criado em: {bookmark['created_at'][:10]}")
                
                with col2:
                    if st.button("✏️", key=f"edit_{bookmark['id']}", help="Editar"):
                        st.session_state.editing_bookmark = bookmark['id']
                        st.session_state.show_add_form = True
                        st.rerun()
                
                with col3:
                    if st.button("🔗", key=f"open_{bookmark['id']}", help="Abrir link"):
                        st.markdown(f'<meta http-equiv="refresh" content="0; url={bookmark["url"]}">', unsafe_allow_html=True)
                
                with col4:
                    if st.button("🗑️", key=f"delete_{bookmark['id']}", help="Excluir"):
                        delete_bookmark(bookmark['id'])
                        st.rerun()
                
                st.markdown("---")
else:
    st.info("Nenhum favorito encontrado. Adicione seu primeiro favorito!")

# --- Estatísticas ---
st.markdown("---")
st.subheader("📊 Estatísticas")

if bookmarks_data:
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Favoritos", len(bookmarks_data))
    
    with col2:
        categories_count = len(set(b['category'] for b in bookmarks_data))
        st.metric("Categorias", categories_count)
    
    with col3:
        recent_bookmarks = len([b for b in bookmarks_data 
                               if b['created_at'] >= (datetime.now() - pd.Timedelta(days=30)).isoformat()])
        st.metric("Últimos 30 dias", recent_bookmarks)
    
    with col4:
        total_tags = len(set(tag for b in bookmarks_data for tag in b.get('tags', [])))
        st.metric("Tags Únicas", total_tags)
    
    # Gráfico de favoritos por categoria
    category_counts = {}
    for bookmark in bookmarks_data:
        category = bookmark['category']
        category_counts[category] = category_counts.get(category, 0) + 1
    
    if category_counts:
        st.bar_chart(category_counts)

# --- Rodapé ---
st.markdown("---")
st.write("Desenvolvido com ❤️ usando Python e Streamlit.")