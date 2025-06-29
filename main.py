import os
from TelemetrySession import TelemetrySession

if __name__ == "__main__":
    RUTA_A_TU_ARCHIVO_IBT = r"H:\Mi unidad\SimRacing\Telemetry\IRacing\formulair04_suzuka grandprix 2024-06-02 21-10-09.ibt"

    print("--- INICIO DEL SCRIPT DE ANÁLISIS DE TELEMETRÍA ---")

    if not os.path.exists(RUTA_A_TU_ARCHIVO_IBT):
        print(f"\nERROR: El archivo no se encontró en la ruta especificada.")
        print(f"Por favor, asegúrate de que la ruta '{RUTA_A_TU_ARCHIVO_IBT}' es correcta.")
    else:
        session = TelemetrySession(RUTA_A_TU_ARCHIVO_IBT)
        session.resumen()
        session.guardar_csv("telemetry_data.csv")

    print("\n--- FIN DEL SCRIPT ---")
    print("Gracias por usar este script de análisis de telemetría. ¡Hasta la próxima!")
