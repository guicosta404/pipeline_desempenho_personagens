import pandas as pd
import unicodedata
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

COLUNAS_ESPERADAS_PERSONAGENS = {"id", "nome_personagem", "solicitado_por", "prioridade", "observacao"}

# Correção de erros de digitação conhecidos
ALIASES_PERSONAGENS = {
    "han sollo": "han solo",
    "chewbaca": "chewbacca",
    "leia organna": "leia organa",
    "dart vader": "darth vader"
}


# Nomes como serão pesquisados na API
# .title() alteraria c-3po para C-3Po
NOME_CANONICOS = {
    "ahsoka tano": "Ahsoka Tano",
    "boba fett": "Boba Fett",
    "c-3po": "C-3PO",
    "chewbacca": "Chewbacca",
    "darth vader": "Darth Vader",
    "din djarin": "Din Djarin",
    "grogu": "Grogu",
    "han solo": "Han Solo",
    "lando calrissian": "Lando Calrissian",
    "leia organa": "Leia Organa",
    "luke skywalker": "Luke Skywalker",
    "obi-wan kenobi": "Obi-Wan Kenobi",
    "palpatine": "Palpatine",
    "r2-d2": "R2-D2",
    "rey skywalker": "Rey Skywalker",
    "yoda": "Yoda"
}

def ler_personagem_bronze(caminho_arquivo: Path) -> pd.DataFrame:
    """
    Lê a planilha de personagens na camada bronze.
    """
    if not caminho_arquivo.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado {caminho_arquivo}")
    
    df = pd.read_csv(caminho_arquivo, dtype="string", encoding="utf-8-sig") # Lê as  colunas como texto

    colunas_ausentes = (COLUNAS_ESPERADAS_PERSONAGENS - set(df.columns))

    if colunas_ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes {sorted(colunas_ausentes)}")
    
    logger.info("Arquivo lido: %s linhas", len(df))

    return df

def normalizar_chave_nome(valor) -> str:
    """
    Normaliza um nome para comparação.
    - trata valores ausentes
    - remove espaços repetidos, no início e no final
    - remove acentos
    - converte para letras minúsculas
    """

    if pd.isna(valor):
        return None
    
    texto = str(valor).strip()

    if not texto:
        return None
    
    texto = " ".join(texto.split())

    texto_final = unicodedata.normalize("NFKD", texto) # remove os acentos

    texto_final = "".join(caractere for caractere in texto_final if not unicodedata.combining(caractere)) # Revisar lógica4


    return texto_final.lower() # testar com casefold()

def normalizar_personagens(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria as colunas utilizadas para identificação.
    """

    df = df.copy()

    df["nome_personagem_original"] = df["nome_personagem"]

    df["nome_chave_original"] = df["nome_personagem"].apply(normalizar_chave_nome)

    df["nome_chave"] = df["nome_chave_original"].replace(ALIASES_PERSONAGENS)

    df["nome_personagem_canonico"] = df["nome_chave"].map(NOME_CANONICOS)

    df["nome_valido"] = df["nome_personagem_canonico"].notna()

    logger.info("Nomes válidos para pesquisa.")

    return df

def obter_nomes_unicos_api(df: pd.DataFrame) -> list:
    """
    Retorna lista de nomes únicos para consulta na API
    """   

    nomes_unicos =  df.loc[df["nome_valido"],"nome_personagem_canonico"].drop_duplicates().sort_values().tolist()

    logger.info("Total de nomes únicos para consulta: %s",len(nomes_unicos))

    return nomes_unicos