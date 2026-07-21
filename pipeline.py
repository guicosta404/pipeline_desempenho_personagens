import logging
from pathlib import Path
from src.extracao import ingerir_csv

logging.basicConfig(level=logging.INFO,  format="%(asctime)s - %(levelname)s - %(message)s")

DIRETORIO_RAIZ = Path(__file__).resolve().parent # file: caminho do pipeline.py - transforma em um caminho absoluto
                                                 # e pega a pasta onde o arquivo esta 

DIRETORIO_ORIGEM = DIRETORIO_RAIZ / "data" / "source"
DIRETORIO_BRONZE_CSV = DIRETORIO_RAIZ / "data" / "bronze" / "csv"
DIRETORIO_METADADOS = DIRETORIO_RAIZ / "data" / "bronze" / "metadata"

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

def executar_pipeline() -> None:
    """
    Orquestra as etapas do pipeline.
    """

    logging.info("Iniciando pipeline.")

    logging.info("ETAPA 1: ingestão dos arquivos csv")
    executar_ingestao_csv()

    logging.info("Pipeline finalizado com sucesso")

if __name__ == "__main__":
    executar_pipeline()    