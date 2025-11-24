#!/usr/bin/env python3
"""
Script de teste para verificar a navegação hierárquica.
"""

import sys
import os

# Adicionar src ao path
sys.path.insert(0, 'src')

def test_navigation_module():
    """Testa se o módulo de navegação funciona corretamente."""
    try:
        from navigation import create_hierarchical_sidebar, set_page_context, get_current_page_info
        print("✅ Módulo de navegação importado com sucesso")
        
        # Testar função get_current_page_info
        info = get_current_page_info()
        print(f"✅ Função get_current_page_info funciona: {info}")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao importar módulo de navegação: {e}")
        return False

def test_page_files():
    """Testa se os arquivos das páginas podem ser importados."""
    page_files = [
        "1_Home.py",
        "pages/2_tools_json_to_csv.py", 
        "pages/3_finops_lambda_report.py",
        "pages/4_finops_ebs_report.py",
        "pages/5_lambda_tags_retrival.py",
        "pages/6_bookmarks_manager.py"
    ]
    
    all_ok = True
    for file_path in page_files:
        full_path = f"src/{file_path}"
        if os.path.exists(full_path):
            print(f"✅ Arquivo encontrado: {file_path}")
        else:
            print(f"❌ Arquivo não encontrado: {file_path}")
            all_ok = False
    
    return all_ok

def test_import_statements():
    """Testa se os imports de navegação estão corretos nos arquivos."""
    import_tests = [
        ("src/1_Home.py", "from navigation import create_hierarchical_sidebar, set_page_context"),
        ("src/pages/2_tools_json_to_csv.py", "from navigation import create_hierarchical_sidebar, set_page_context"),
        ("src/pages/3_finops_lambda_report.py", "from navigation import create_hierarchical_sidebar, set_page_context"),
        ("src/pages/4_finops_ebs_report.py", "from navigation import create_hierarchical_sidebar, set_page_context"),
        ("src/pages/5_lambda_tags_retrival.py", "from navigation import create_hierarchical_sidebar, set_page_context"),
        ("src/pages/6_bookmarks_manager.py", "from navigation import create_hierarchical_sidebar, set_page_context")
    ]
    
    all_ok = True
    for file_path, import_statement in import_tests:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if import_statement in content:
                    print(f"✅ Import correto em: {file_path}")
                else:
                    print(f"❌ Import não encontrado em: {file_path}")
                    all_ok = False
        except Exception as e:
            print(f"❌ Erro ao ler {file_path}: {e}")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    print("🧪 Testando sistema de navegação hierárquica...")
    print("=" * 50)
    
    # Executar testes
    test1 = test_navigation_module()
    print()
    
    test2 = test_page_files()
    print()
    
    test3 = test_import_statements()
    print()
    
    # Resultado final
    if test1 and test2 and test3:
        print("🎉 Todos os testes passaram! Sistema de navegação implementado com sucesso.")
    else:
        print("⚠️ Alguns testes falharam. Verifique a implementação.")
    
    print("=" * 50)