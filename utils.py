# -*- coding: utf-8 -*-
"""
File: utils.py
Created on 2025-07-11
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""
import sys
import os

def resource_path(relative_path):
    """
    Obtiene la ruta absoluta a un recurso, funciona tanto para el script
    como para el ejecutable de PyInstaller.
    """
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)