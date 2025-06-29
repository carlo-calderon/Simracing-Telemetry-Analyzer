import irsdk
import pandas as pd

class TelemetrySession:
    def __init__(self, ibt_path: str):
        self.ibt_path = ibt_path
        self.dataframe = pd.DataFrame()
        self._load_telemetry()

    def _load_telemetry(self):
        ibt = irsdk.IBT()
        try:
            ibt.open(self.ibt_path)
            telemetry_data = {}
            for var_name in ibt.var_headers_names:
                telemetry_data[var_name] = ibt.get_all(var_name)
            self.dataframe = pd.DataFrame(telemetry_data)
            print(f"INFO: ¡Lectura completa! Se encontraron {len(self.dataframe)} muestras (ticks) de telemetría.")
        except Exception as e:
            print(f"ERROR: Ocurrió un error inesperado al procesar el archivo: {e}")
        finally:
            ibt.close()
            print("INFO: Archivo .ibt cerrado.")

    def resumen(self):
        if not self.dataframe.empty:
            print("\n--- RESUMEN DEL DATAFRAME CARGADO ---")
            self.dataframe.info(verbose=False)
            print("\n--- PRIMERAS 10 MUESTRAS DE DATOS RELEVANTES ---")
            columnas_relevantes = [
                'SessionTime', 'Lap', 'LapDistPct', 'Speed', 'RPM', 'Throttle', 'Brake', 'Steer',
                'Lat', 'Lon', 'Alt',  # Agrega las coordenadas
                'X', 'Y', 'Z'         # Otras posibles variables de posición
            ]
            columnas_existentes = [col for col in columnas_relevantes if col in self.dataframe.columns]
            print(f"INFO: Columnas encontradas: {self.dataframe.columns.tolist()}")
            print(self.dataframe[columnas_existentes].head(10).to_string())

    def guardar_csv(self, ruta_csv: str):
        """
        Guarda el DataFrame de telemetría en un archivo CSV.
        :param ruta_csv: Ruta donde se guardará el archivo CSV.
        """
        if not self.dataframe.empty:
            self.dataframe.to_csv(ruta_csv, index=False)
            print(f"INFO: DataFrame guardado exitosamente en '{ruta_csv}'.")
        else:
            print("ADVERTENCIA: El DataFrame está vacío. No se guardó ningún archivo.")