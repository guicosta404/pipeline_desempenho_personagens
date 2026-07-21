import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2 # copia o arquivo sem abrir e regravar. Importante para preservar o arquivo original para bronze
import re
import requests

logger = logging.getLogger(__name__)

URL_API_PEOPLE = "https://swapi.dev/api/people/"

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

def criar_identificador_arquivo(nome_personagem: str) -> str:
    """
    Cria um nome seguro para o arquivo de resposta da API.

    Exemplo:
        Luke Skywalker -> luke_skywalker
        C-3PO -> c_3po
    """

    identificador = nome_personagem.casefold()

    identificador = re.sub(pattern=r"[^a-z0-9]+",repl="_",string=identificador,)
    
    return identificador.strip("_")

def salvar_metadados_api(caminho_metadados: Path, metadados: dict) -> None:
    """
    Salva os metadados de consulta da API.
    """

    caminho_metadados.parent.mkdir(parents=True, exist_ok=True)

    with caminho_metadados.open(mode="w",encoding="utf-8") as arquivo:
        json.dump(metadados, arquivo, ensure_ascii=False, indent=4)

def consultar_personagem_api(nome_personagem: str, diretorio_resposta:Path, diretorio_metadados: Path) -> dict:
    """
    Consulta um personagem na SWAPI e salva a resposta crua na Bronze.

    Caso a resposta já exista, reutiliza o arquivo sem consultar
    novamente a API.
    """

    diretorio_resposta.mkdir(parents=True, exist_ok=True)

    diretorio_metadados.mkdir(parents=True, exist_ok=True)

    identificador = criar_identificador_arquivo(nome_personagem)

    caminho_resposta = diretorio_resposta / f"{identificador}.json"

    caminho_metadados = diretorio_metadados / f"{identificador}_metadada.json"

    # CACHE: evita consultar um personagem já ingerido
    if caminho_resposta.is_file():
        logger.info("Resposta API reutilizada: %s", nome_personagem)

        return {
            "nome_personagem_canonico": nome_personagem,
            "caminho_resposta": caminho_resposta,
            "resposta_reutilizada": True,
            "erro_consulta": None
        }
    
    data_hora_consulta = datetime.now(timezone.utc).isoformat()

    try:
        resposta = requests.get(URL_API_PEOPLE, params={"search": nome_personagem}, timeout=20)
        
        resposta.raise_for_status()

        caminho_resposta.write_bytes(resposta.content) # Sala os bytes recebidos, sem reformatar o json

        metadados = {
            "nome_consultado": nome_personagem,
            "fonte": URL_API_PEOPLE,
            "data_hora_ingestao": data_hora_consulta,
            "status_http": resposta.status_code,
            "content_type": resposta.headers.get("Content-Type"),
            "status_ingestao": "sucesso"
        }

        salvar_metadados_api(caminho_metadados=caminho_metadados, metadados=metadados)

        logger.info("Personagem consultado na APi: %s", nome_personagem)

        return {
            "nome_personagem_canonico": nome_personagem,
            "caminho_resposta": caminho_resposta,
            "resposta_reutilizada": False,
            "erro_consulta": None
        }
        
    except requests.RequestException as erro:
        metadados = {
            "nome_consultado": nome_personagem,
            "fonte": URL_API_PEOPLE,
            "data_hora_tentativa_utc": data_hora_consulta,
            "status_ingestao": "erro",
            "tipo_erro": type(erro).__name__,
            "mensagem_erro": str(erro)
        }
        
        salvar_metadados_api(caminho_metadados=caminho_metadados, metadados=metadados)

        logger.error("Erro ao consultar %s na API: %s", nome_personagem, erro)

def ingerir_personagens_api(nomes_personagens: list, diretorio_resposta: Path, diretorio_metadados: Path) -> list:
    """
    Consulta todos os personagens da fila da SWAPI.
    """

    resultados_ingestao = []

    for nome in nomes_personagens:
        resultado = consultar_personagem_api(nome_personagem=nome, diretorio_resposta=diretorio_resposta, diretorio_metadados=diretorio_metadados)

        resultados_ingestao.append(resultado)

    return resultados_ingestao    
