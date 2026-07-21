import logging
from pathlib import Path
from src.extracao import ingerir_csv, ingerir_personagens_api
from src.transformacao import criar_status_consultas_api,ler_personagem_bronze, normalizar_personagens, obter_nomes_unicos_api,criar_fila_api,ler_personagem_bronze,ler_vendas_bronze,normalizar_nomes_vendas,normalizar_personagens,obter_nomes_unicos_api,obter_nomes_unicos_vendas
from src.carga import salvar_df_csv

logging.basicConfig(level=logging.INFO,  format="%(asctime)s - %(levelname)s - %(message)s")

DIRETORIO_RAIZ = Path(__file__).resolve().parent # file: caminho do pipeline.py - transforma em um caminho absoluto
                                                 # e pega a pasta onde o arquivo esta 

DIRETORIO_ORIGEM = DIRETORIO_RAIZ / "data" / "source"

DIRETORIO_BRONZE_CSV = DIRETORIO_RAIZ / "data" / "bronze" / "csv"
DIRETORIO_BRONZE_API_PEOPLE = DIRETORIO_RAIZ / "data" / "bronze" / "api" / "people"

DIRETORIO_METADADOS = DIRETORIO_RAIZ / "data" / "bronze" / "metadata"
DIRETORIO_BRONZE_API_METADADA = DIRETORIO_RAIZ / "data" / "bronze" / "api" / "metadata"

DIRETORIO_SILVER = DIRETORIO_RAIZ / "data" / "silver"


ARQUIVOS_CSV = ["personagens_solicitados.csv","vendas_produtos.csv"]

def executar_ingestao_csv() -> None:
    """
    Executa a ingestão dos aquivos CSV para camada bronze.
    """

    for nome_arquivo in ARQUIVOS_CSV:
        caminho_origem = DIRETORIO_ORIGEM / nome_arquivo

        ingerir_csv(
            caminho_origem=caminho_origem,
            diretorio_bronze_csv=DIRETORIO_BRONZE_CSV,
            diretorio_metadados=DIRETORIO_METADADOS
        )

def executar_normalizacao_personagens() -> list:
    """
    Normaliza nomes para consulta na API
    """

    caminho_personagens_bronze= (DIRETORIO_BRONZE_CSV / "personagens_solicitados.csv")
    
    df_personagens = ler_personagem_bronze(caminho_personagens_bronze)

    df_normalizado = normalizar_personagens(df_personagens)

    caminho_saida = (DIRETORIO_SILVER / "personagens_normalizados.csv")

    salvar_df_csv(df=df_normalizado, caminho_destino=caminho_saida)

    nomes_para_api = obter_nomes_unicos_api(df_normalizado)

    return nomes_para_api    

def executar_normalizacao_nomes_vendas() -> list:
    """
    Normaliza nomes presentes nas vendas.
    """
    caminho_vendas_bronze = (DIRETORIO_BRONZE_CSV / "vendas_produtos.csv")

    df_vendas = ler_vendas_bronze(caminho_vendas_bronze)

    df_vendas_normalizado = normalizar_nomes_vendas(df_vendas)

    caminho_saida = (DIRETORIO_SILVER / "vendas_nomes_normalizados.csv")

    salvar_df_csv(df = df_vendas_normalizado,caminho_destino = caminho_saida)

    nomes_vendas = obter_nomes_unicos_vendas(df_vendas_normalizado)

    return nomes_vendas

def executar_criacao_fila_api(nomes_solicitados:list, nomes_vendas:list) -> list:
    """
    Cria e salva a lista única de personagens para consulta na API.
    """
    df_fila = criar_fila_api(nomes_solicitados, nomes_vendas)

    caminho_saida = (DIRETORIO_SILVER / "personagens_para_consulta.csv")

    salvar_df_csv(df = df_fila, caminho_destino=caminho_saida)

    nomes_para_consulta = df_fila["nome_personagem_canonico"].tolist()

    logging.info("Personagens para consultar na API:")
    for nome in nomes_para_consulta:
        print(f"- {nome}")

    return df_fila 

def executar_consulta_api(df_fila):
    """
    Consulta os personagens na SWAPI e salva o status na Silver.
    """
    nomes_personagens = df_fila["nome_personagem_canonico"].tolist()

    resultados_ingestao = ingerir_personagens_api(nomes_personagens=nomes_personagens, diretorio_resposta=DIRETORIO_BRONZE_API_PEOPLE, diretorio_metadados=DIRETORIO_BRONZE_API_METADADA)

    df_status = criar_status_consultas_api(df_fila=df_fila,resultados_ingestao=resultados_ingestao)
    
    caminho_saida = DIRETORIO_SILVER / "personagens_consulta_api.csv"

    salvar_df_csv(df= df_status, caminho_destino=caminho_saida)

    total_encontrados = df_status["encontrado_swapi"].sum()

    total_nao_encontrados = (df_status["status_consulta"] == "nao_encontrado").sum()

    total_erros = df_status["status_consulta"].isin(["erro_requicao","resposta_invalida"]).sum()

    logging.info("Resumo da consulta: %s encontrados,"
                "%s nao encontrados e %s erros.",total_encontrados, total_nao_encontrados, total_erros)      


def executar_pipeline() -> None:
    """
    Orquestra as etapas do pipeline.
    """

    logging.info("Iniciando pipeline.")

    logging.info("ETAPA 1: ingestão dos arquivos csv")
    executar_ingestao_csv()

    logging.info("ETAPA 2: normalização nome dos personagens")
    nomes_solicitados = executar_normalizacao_personagens()

    logging.info("ETAPA 3: normalização de nomes das vendas e criação de fila de consulta na SWAPI.")
    nomes_vendas = executar_normalizacao_nomes_vendas()

    df_fila = executar_criacao_fila_api(nomes_solicitados=nomes_solicitados, nomes_vendas=nomes_vendas)

    logging.info("ETAPA 4: consulta dos personagens na SWAPI")
    executar_consulta_api(df_fila)

    logging.info("Pipeline finalizado com sucesso")

if __name__ == "__main__":
    executar_pipeline()    