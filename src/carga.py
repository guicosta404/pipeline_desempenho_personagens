import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def salvar_df_csv(df: pd.DataFrame, caminho_destino: Path) -> Path:
    """
    Salva um dataframe como csv sem duplicar.
    """

    caminho_destino.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(caminho_destino, index=False)

    logger.info("Arquivo salvo.")

    return caminho_destino

