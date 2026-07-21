import pandas as pd
import unicodedata
from pathlib import Path

import logging
logger = logging.getLogger(__name__)

# Validar estrutura esperada 
COLUNAS_ESPERADAS_PERSONAGENS = {"id", "nome_personagem", "solicitado_por", "prioridade", "observacao"}
COLUNAS_ESPERADAS_VENDAS = {"id", "nome_personagem", "produto", "unidades_vendidas", "receita_reais", "mes_referencia"}

# Correção de erros de digitação conhecidos
ALIASES_PERSONAGENS = {
    "han sollo": "han solo",
    "chewbaca": "chewbacca",
    "leia organna": "leia organa",
    "dart vader": "darth vader"
}


# Nomes como serão pesquisados na API
# .title() alteraria C-3PO para C-3Po
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
    "yoda": "Yoda",
    "kylo ren": "Kylo Ren"
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

######################################################################################################

def ler_vendas_bronze(caminho_arquivo: Path) -> pd.DataFrame:
    """
    Lê a planilha de vendas na camada bronze.
    """

    if not caminho_arquivo.is_file():
        raise FileNotFoundError(f"Arquivo de vendas não encontrado: {caminho_arquivo}")
    
    df = pd.read_csv(caminho_arquivo, encoding="utf-8-sig", dtype="string") # inicialmente para ler como string

    colunas_ausentes = (COLUNAS_ESPERADAS_VENDAS - set(df.columns))

    if colunas_ausentes:
        raise ValueError("Colunas obrigatórias ausentes em vendas.")
    
    logger.info("Arquivo de vendas lido: %s linhas", len(df))

    return df

def normalizar_nomes_vendas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes dos personagens nas vendas.
    Usa as mesmas regras aplicadas nas solicitações.
    """

    df = df.copy()

    # Preserva o valor exato como veio da fonte
    df["nome_personagem_original"] = df["nome_personagem"]

    # Cria chave normalizada antes de tentar utilizá-la
    df["nome_chave_original"] = df["nome_personagem"].apply(normalizar_chave_nome)

    # Corrige os erros conhecidos de digitação
    df["nome_chave"] = df["nome_chave_original"].replace(ALIASES_PERSONAGENS)

    # Converte a chave para o nome canonico
    df["nome_personagem_canonico"] = df["nome_chave"].map(NOME_CANONICOS)

    df["nome_valido"] = df["nome_chave"].notna()

    logger.info("Nomes válidos nas vendas: %s", df["nome_valido"].sum())

    return df

def obter_nomes_unicos_vendas(df: pd.DataFrame) -> list:
    """
    Retorna os nomes canonicos únicos na planilha vendas.
    """

    nomes_unicos = (df.loc[df["nome_valido"],"nome_personagem_canonico"].drop_duplicates().sort_values().tolist())

    logger.info("Personagens únicos encontrados nas vendas: %s", len(nomes_unicos))

    return nomes_unicos

### Fila única para API
def criar_fila_api(nomes_solicitados: list, nomes_vendas: list) -> pd.DataFrame:
    """
    Cria uma lista única de personagens para consulta na SWAPI,
    registrando em quais fontes cada nome estava presente.
    """

    conjunto_solicitacoes = set(nomes_solicitados)
    conjunto_vendas = set(nomes_vendas)

    nomes_unicos = sorted(conjunto_solicitacoes | conjunto_vendas) # | representa união dos conjuntos sem repetir

    registros = []

    for nome in nomes_unicos:
        presente_solicitacoes = (nome in conjunto_solicitacoes)
        
        presente_vendas = (nome in conjunto_vendas)

        if presente_solicitacoes and presente_vendas:
            origem = "solicitacoes_vendas"

        elif presente_solicitacoes:
            origem = "solicitacoes"

        else:
            origem = "vendas"

        registros.append(
            {
            "nome_personagem_canonico": nome,
            "presente_solicitacoes": presente_solicitacoes,
            "presente_vendas": presente_vendas,
            "origem_personagem": origem 
        })

    df_consultas = pd.DataFrame(registros)
    
    logger.info("Total de personagens únicos para consulta na API: %s", len(df_consultas))

    return df_consultas
