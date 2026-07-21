import logging
from pathlib import Path
from src.extracao import ingerir_csv
from src.transformacao import ler_personagem_bronze, normalizar_personagens, obter_nomes_unicos_api
from src.carga import salvar_df_csv

logging.basicConfig(level=logging.INFO,  format="%(asctime)s - %(levelname)s - %(message)s")

DIRETORIO_RAIZ = Path(__file__).resolve().parent # file: caminho do pipeline.py - transforma em um caminho absoluto
                                                 # e pega a pasta onde o arquivo esta 

DIRETORIO_ORIGEM = DIRETORIO_RAIZ / "data" / "source"
DIRETORIO_BRONZE_CSV = DIRETORIO_RAIZ / "data" / "bronze" / "csv"
DIRETORIO_METADADOS = DIRETORIO_RAIZ / "data" / "bronze" / "metadata"

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

    logging.info("Personagens que serão consultados:")

    for nome in nomes_para_api:
        print(f"- {nome}")

    return nomes_para_api    

    
def executar_pipeline() -> None:
    """
    Orquestra as etapas do pipeline.
    """

    logging.info("Iniciando pipeline.")

    logging.info("ETAPA 1: ingestão dos arquivos csv")
    executar_ingestao_csv()

    logging.info("ETAPA 2: normalização nome dos personagens")
    executar_normalizacao_personagens()

    logging.info("Pipeline finalizado com sucesso")

if __name__ == "__main__":
    executar_pipeline()    