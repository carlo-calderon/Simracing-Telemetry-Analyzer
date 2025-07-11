import irsdk
import pandas as pd

class TelemetrySession:
    def __init__(self, ibt_path: str = None):
        self.ibt_path = ibt_path
        self.dataframe = pd.DataFrame() # DataFrame con todas las columnas
        self.laps_df = pd.DataFrame()   # DataFrame con el resumen de vueltas

        if not ibt_path is None:
            self.load_telemetry(ibt_path)
            self.laps_df = self.times_by_laps()

    def load_telemetry(self, ibt_path: str):
        self.ibt_path = ibt_path
        self.dataframe = pd.DataFrame()

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

            # Imprimir mínimos y máximos de las columnas relevantes
            print("\n--- MÍNIMOS Y MÁXIMOS DE COLUMNAS RELEVANTES ---")
            for col in columnas_existentes:
                min_val = self.dataframe[col].min()
                max_val = self.dataframe[col].max()
                mean_val = self.dataframe[col].mean()
                print(f"{col}: min={min_val}, max={max_val}, mean={mean_val:.2f}")
    
    def remove_problematic_rows(self):
        if self.dataframe.empty:
            return 
        
        # Imprimir las primeras 10 filas problemáticas: Lat o Lon < promedio o < 10000
        if 'Lat' in self.dataframe.columns and 'Lon' in self.dataframe.columns:
            mask = (
                ((self.dataframe['Lat'] < 0.01) & (self.dataframe['Lat'] > -0.01) &
                (self.dataframe['Lon'] < 0.01) & (self.dataframe['Lon'] > -0.01)) 
            )
            problematic = self.dataframe[mask]
            print("\n--- PRIMERAS 10 FILAS PROBLEMÁTICAS (Lat o Lon < promedio o < 10000) ---")
            print(problematic.head(10).to_string(index=False))

            self.dataframe = self.dataframe[~mask]
            print(f"INFO: Se eliminaron {len(problematic)} filas problemáticas.")
        else:
            print("INFO: Las columnas 'Lat' o 'Lon' no están presentes para la eliminación de filas problemáticas.")


    def analyze_lockup(self, lockup_threshold=1.0):
        """
        Analiza el DataFrame para crear nuevas columnas para bloqueo y patinaje.
        """
        if self.dataframe.empty:
            return

        print("INFO: Analizando bloqueo de frenos...")
        df = self.dataframe
        # --- Análisis de Bloqueo de Ruedas ---
        # Definimos una velocidad mínima para considerar un bloqueo
        speed_threshold_mps = 5.0 # m/s (equivalente a 18 km/h)
        # Creamos una columna booleana para cada rueda
        # Una rueda está bloqueada si su velocidad es casi cero mientras el coche se mueve y se está frenando.
        if all(k in df for k in ['Brake', 'Speed', 'LFspeed']):
            df['LF_Lockup'] = ((df['Brake'] > 0.1) & (df['Speed'] > speed_threshold_mps) & (df['LFspeed'] < lockup_threshold)).astype('uint8')
        if all(k in df for k in ['Brake', 'Speed', 'RFspeed']):
            df['RF_Lockup'] = ((df['Brake'] > 0.1) & (df['Speed'] > speed_threshold_mps) & (df['RFspeed'] < lockup_threshold)).astype('uint8')
        if all(k in df for k in ['Brake', 'Speed', 'LRspeed']):
            df['LR_Lockup'] = ((df['Brake'] > 0.1) & (df['Speed'] > speed_threshold_mps) & (df['LRspeed'] < lockup_threshold)).astype('uint8')
        if all(k in df for k in ['Brake', 'Speed', 'RRspeed']):
            df['RR_Lockup'] = ((df['Brake'] > 0.1) & (df['Speed'] > speed_threshold_mps) & (df['RRspeed'] < lockup_threshold)).astype('uint8')

        self.dataframe = df
        print("INFO: Análisis bloqueo completado. Nuevas columnas añadidas.")

    def analyze_spin(self, spin_threshold_pct=15.0):
        if self.dataframe.empty:
            return

        print("INFO: Patinaje de Ruedas (asumiendo Tracción Trasera)...")
        df = self.dataframe

        # --- Análisis de Patinaje de Ruedas (asumiendo Tracción Trasera) ---
        if all(k in df for k in ['Throttle', 'LRspeed', 'RRspeed', 'LFspeed', 'RFspeed']):
            # Calculamos la velocidad media de cada eje
            driven_wheel_speed = (df['LRspeed'] + df['RRspeed']) / 2
            free_wheel_speed = (df['LFspeed'] + df['RFspeed']) / 2
            # Hay patinaje si la velocidad de las ruedas motrices supera a las libres en un %
            # y estamos acelerando. Sumamos un valor pequeño para evitar división por cero.
            speed_diff_pct = ((driven_wheel_speed - free_wheel_speed) / (free_wheel_speed + 0.01)) * 100
            df['WheelSpin'] = ((df['Throttle'] > 0.1) & (speed_diff_pct > spin_threshold_pct)).astype('uint8')
        
        self.dataframe = df
        print("INFO: Análisis completado. Nuevas columnas añadidas.")

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
            
    def filter_driving_columns(self, analyze_lockup=True, analyze_spin=True):
        if analyze_lockup:
            self.analyze_lockup()
        if analyze_spin:
            self.analyze_spin()

        required_columns = [
            'SessionTime', 'Lap', 'Speed', 'RPM', 'Throttle', 'Brake', 'Gear',
            'Lat', 'Lon', 'Alt',      # Position
            'SteeringWheelAngle',     # Steering wheel angle
            'Yaw', 'Pitch', 'Roll',   # Car rotation
            'YawRate',  # Slippage indicators (if available)
            'LapDistPct', 'LapDist',
            # Columnas de Temperatura
            'LFtempL', 'LFtempM', 'LFtempR', 'RFtempL', 'RFtempM', 'RFtempR',
            'LRtempL', 'LRtempM', 'LRtempR', 'RRtempL', 'RRtempM', 'RRtempR',
            # Columnas creadas en analyze_driving_inputs
            'LF_Lockup', 'RF_Lockup', 'LR_Lockup', 'RR_Lockup', 'WheelSpin',
            'LatAccel', 'LongAccel', 'VertAccel'
        ]
        existing_columns = [col for col in required_columns if col in self.dataframe.columns]
        missing_columns = [col for col in required_columns if col not in self.dataframe.columns]
        self.dataframe = self.dataframe[existing_columns]
        print(f"INFO: DataFrame filtered. Current columns: {self.dataframe.columns.tolist()}")
        if missing_columns:
            print(f"WARNING: The following required columns were not found in the DataFrame: {', '.join(missing_columns)}")
    
    def times_by_laps(self, sector_percents=[0.25, 0.5, 0.75]):
        """
        Calcula los tiempos de vuelta y de sectores para cada vuelta.
        sector_percents: lista de porcentajes (ejemplo: [0.25, 0.5, 0.75])
        Devuelve un DataFrame con columnas: Lap, Time, S1, S2, ..., Sn
        """
        if self.dataframe is None or self.dataframe.empty:
            print("No hay datos de telemetría cargados.")
            return pd.DataFrame()

        df = self.dataframe
        if 'Lap' not in df.columns or 'SessionTime' not in df.columns or 'LapDistPct' not in df.columns:
            print("Faltan columnas necesarias: Lap, SessionTime o LapDistPct.")
            return pd.DataFrame()

        laps = []
        for lap_num in sorted(df['Lap'].unique()):
            lap_df = df[df['Lap'] == lap_num]
            if lap_df.empty:
                continue

            # Tiempos de inicio y fin de la vuelta
            t0 = lap_df['SessionTime'].iloc[0]
            t1 = lap_df['SessionTime'].iloc[-1]
            lap_time = t1 - t0

            # Calcular tiempos de sectores
            sector_times = []
            prev_pct = 0.0
            prev_time = t0
            for i, pct in enumerate(sector_percents):
                # Buscar el primer índice donde LapDistPct >= pct
                sector_df = lap_df[lap_df['LapDistPct'] >= pct]
                if not sector_df.empty:
                    sector_time = sector_df['SessionTime'].iloc[0]
                else:
                    sector_time = t1  # Si no hay, usar fin de vuelta
                sector_times.append(sector_time - prev_time)
                prev_time = sector_time
                prev_pct = pct
            # Último sector: desde el último porcentaje hasta el final de la vuelta
            sector_times.append(t1 - prev_time)

            # Construir fila
            row = {'Lap': lap_num, 'Time': lap_time}
            for i, st in enumerate(sector_times):
                row[f'S{i+1}'] = st
            laps.append(row)

        laps_df = pd.DataFrame(laps)
        return laps_df