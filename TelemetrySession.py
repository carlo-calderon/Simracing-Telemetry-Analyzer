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

    def save_to_csv(self, ruta_csv: str):
        """
        Guarda el DataFrame de telemetría en un archivo CSV con formato personalizado.
        :param ruta_csv: Ruta donde se guardará el archivo CSV.
        """
        if not self.dataframe.empty:
            df = self.dataframe.copy()
            # Formateo de columnas según lo solicitado
            if 'SessionTime' in df.columns:
                df['SessionTime'] = df['SessionTime'].map(lambda x: f"{x:.3f}")
            if 'RPM' in df.columns:
                df['RPM'] = df['RPM'].map(lambda x: f"{int(round(x))}")
            if 'Speed' in df.columns:
                df['Speed'] = df['Speed'].map(lambda x: f"{x:.2f}")
            if 'Brake' in df.columns:
                df['Brake'] = df['Brake'].map(lambda x: f"{x:.4f}")
            if 'Throttle' in df.columns:
                df['Throttle'] = df['Throttle'].map(lambda x: f"{x:.4f}")
            if 'SteeringWheelAngle' in df.columns:
                df['SteeringWheelAngle'] = df['SteeringWheelAngle'].map(lambda x: f"{x:.4f}")
            if 'Yaw' in df.columns:
                df['Yaw'] = df['Yaw'].map(lambda x: f"{x:.5f}")
            if 'Pitch' in df.columns:
                df['Pitch'] = df['Pitch'].map(lambda x: f"{x:.5f}")
            if 'Roll' in df.columns:
                df['Roll'] = df['Roll'].map(lambda x: f"{x:.5f}")
            if 'Lat' in df.columns:
                df['Lat'] = df['Lat'].map(lambda x: f"{x:.7f}")
            if 'Lon' in df.columns:
                df['Lon'] = df['Lon'].map(lambda x: f"{x:.7f}")
            if 'Alt' in df.columns:
                df['Alt'] = df['Alt'].map(lambda x: f"{x:.7f}")
            df.to_csv(ruta_csv, index=False)
            print(f"INFO: DataFrame guardado exitosamente en '{ruta_csv}' con formato personalizado.")
        else:
            print("ADVERTENCIA: El DataFrame está vacío. No se guardó ningún archivo.")
            
    def filter_driving_columns(self):
        """
        Keep only the columns necessary for driving analysis in the DataFrame.
        Columns: SessionTime, Lap, Speed, RPM, Throttle, Brake, Lat, Lon, Alt, Steer, Yaw, Pitch, Roll,
        SteeringWheelAngle, SlipAngle, YawRate, WheelSlip (if available)
        """
        required_columns = [
            'SessionTime', 'Lap', 'Speed', 'RPM', 'Throttle', 'Brake',
            'Lat', 'Lon', 'Alt',      # Position
            'SteeringWheelAngle',     # Steering wheel angle
            'Yaw', 'Pitch', 'Roll',   # Car rotation
            'YawRate'  # Slippage indicators (if available)
        ]
        existing_columns = [col for col in required_columns if col in self.dataframe.columns]
        missing_columns = [col for col in required_columns if col not in self.dataframe.columns]
        self.dataframe = self.dataframe[existing_columns]
        print(f"INFO: DataFrame filtered. Current columns: {self.dataframe.columns.tolist()}")
        if missing_columns:
            print(f"WARNING: The following required columns were not found in the DataFrame: {', '.join(missing_columns)}")