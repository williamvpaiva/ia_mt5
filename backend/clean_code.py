import os
import re

def clean_text(text):
    # Substitui caracteres comuns de acentuação por suas versões simples
    # para evitar problemas de codec em qualquer ambiente
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i',
        'ó': 'o', 'ò': 'o', 'õ': 'o', 'ô': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u',
        'ç': 'c',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I',
        'Ó': 'O', 'Ò': 'O', 'Õ': 'O', 'Ô': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U',
        'Ç': 'C',
        'º': 'o', 'ª': 'a'
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remove qualquer caractere não-ascii remanescente (substitui por ?)
    return text.encode('ascii', 'replace').decode('ascii')

def process_directory(directory):
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                print(f"Limpando {file_path}...")
                
                # Tenta ler em diferentes encodings
                content = None
                for encoding in ['latin-1', 'cp1252', 'utf-8']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        break
                    except:
                        continue
                
                if content:
                    cleaned_content = clean_text(content)
                    with open(file_path, 'w', encoding='ascii') as f:
                        f.write(cleaned_content)

if __name__ == "__main__":
    process_directory('app')
