import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2 # copia o arquivo sem abrir e regravar. Importante para preservar o arquivo original para bronze

logger = logging.getLogger(__name__)

def criar_diretório(caminho: Path) -> None:
    """
    Cria um diretório caso ainda não exista.
    """

    caminho.mkdir(parents=True, exist_ok=True)  # Cria também diretórios superios se necessário e 
                                                # não gera erro se a pasta existir

def copiar_csv_para_bronze(caminho_origem: Path, diretorio_destino: Path) -> Path:
    """
    Copia o arquivo csv para camada bronze.
    Retorna o caminho do arquivo criado na bronze.
    """    
    if not caminho_origem.is_file(): # Verificação para validar o caminho
        raise FileNotFoundError(f"Caminho não encontrado. {caminho_origem}")
    
    criar_diretório(diretorio_destino)

    caminho_destino = diretorio_destino / caminho_origem.name

    copy2(caminho_origem, caminho_destino)

    logger.info("Arquivo copiado para a bronze: %s", caminho_destino)

    return caminho_destino

def salvar_metadados_ingestao(caminho_origem: Path, caminho_destino: Path, diretorio_metadados: Path) -> Path:
    """
    Salva os metadados referentes a ingestão do csv.
    """    

    criar_diretório(diretorio_metadados)

    metadados = {
        "nome_arquivo" : caminho_origem.name,
        "fonte" : "local",
        "destino": f"data/source/{caminho_destino.name}",
        "data_hora" : datetime.now(timezone.utc).isoformat(), # Mantem o padrão de horário independente do ambiente de exec.
        "tamanho_bytes" : caminho_destino.stat().st_size,
        "status" : "sucesso"
    }

    nome_metadados = f"{caminho_origem.stem}_metadata.json"

    caminho_metadados = diretorio_metadados / nome_metadados

    with caminho_metadados.open(mode="w", encoding="utf-8") as arquivo:
        json.dump(metadados, arquivo, ensure_ascii=False, indent=4) # Dict -> json : mantem caracter ç e deixa o arq legivel.

        logger.info("Metadados salvos em %s", caminho_metadados)
        
        return caminho_metadados
    
def ingerir_csv(caminho_origem: Path, diretorio_bronze_csv: Path, diretorio_metadados: Path) -> None:
    """
    Executa a ingestão completa do csv para a camada bronze.
    """    

    caminho_destino = copiar_csv_para_bronze(caminho_origem = caminho_origem, diretorio_destino = diretorio_bronze_csv)

    salvar_metadados_ingestao(
        caminho_origem = caminho_destino,
        caminho_destino = caminho_destino,
        diretorio_metadados=diretorio_metadados)
