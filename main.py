# main.py
import sys
from PySide6.QtWidgets import QApplication
from TrackAnalizer import MainWindow # Importamos nuestra ventana principal

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

# API_KEY = "AIzaSyBwn0dzu6ae97g4W3ArNRAHLr-cqOvlrUQ"  # Reemplaza con tu clave de API de Google Maps


# import os
# from TelemetrySession import TelemetrySession

# if __name__ == "__main__":
#     RUTA_A_TU_ARCHIVO_IBT = r"H:\Mi unidad\SimRacing\Telemetry\IRacing\porsche992rgt3_oschersleben gp 2025-06-28 20-46-35.ibt"

#     print("--- INICIO DEL SCRIPT DE ANÁLISIS DE TELEMETRÍA ---")

#     if not os.path.exists(RUTA_A_TU_ARCHIVO_IBT):
#         print(f"\nERROR: El archivo no se encontró en la ruta especificada.")
#         print(f"Por favor, asegúrate de que la ruta '{RUTA_A_TU_ARCHIVO_IBT}' es correcta.")
#     else:
#         session = TelemetrySession(RUTA_A_TU_ARCHIVO_IBT)
#         session.resumen()
#         session.filter_driving_columns()
#         session.save_to_csv("telemetry_data.csv")

#     print("\n--- FIN DEL SCRIPT ---")
#     print("Gracias por usar este script de análisis de telemetría. ¡Hasta la próxima!")
