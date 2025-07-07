# -*- coding: utf-8 -*-
"""
File: GLTFModel.py
Created on 2025-07-06
@author: Carlo Calderón Becerra
@company: CarcaldeF1
"""
import numpy as np
from OpenGL.GL import *
from pygltflib import GLTF2

# ... (Los diccionarios de mapeo no cambian) ...
GLTF_COMPONENT_TYPE_TO_NUMPY = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
GLTF_TYPE_TO_NUM_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}

class GLTFModel:
    def __init__(self):
        # Ahora guardamos una lista de primitivas. Cada primitiva es un objeto dibujable.
        self.primitives = []
        self.vertices_all = [] # Para calcular el bounding box de todo el modelo
        self.base_rotation_xyz = (0, 0, 0)
        self.base_scale = 1.0  # Escala base del modelo, se puede ajustar si es necesario

    def load(self, filename, rotation_xyz_degrees=(0, 0, 0), base_scale=1.0):
        """
        Carga TODAS las mallas de un archivo gltf, cada una con sus datos.
        """
        try:
            self.base_rotation_xyz = rotation_xyz_degrees
            self.base_scale = base_scale

            print(f"INFO: Cargando modelo 3D desde '{filename}'...")
            gltf = GLTF2.load(filename)
            binary_blob = gltf.binary_blob()
            if not binary_blob:
                gltf.load_buffers()
                binary_blob = gltf.binary_blob()
            if not binary_blob: raise ValueError("No se pudo cargar el buffer binario.")

            # Iteramos sobre todas las mallas del archivo
            for mesh in gltf.meshes:
                # Y sobre todas las primitivas de cada malla
                for primitive in mesh.primitives:
                    new_primitive = {} # Diccionario para guardar los datos de esta parte del modelo

                    # --- Extraer Índices ---
                    indices_accessor = gltf.accessors[primitive.indices]
                    buffer_view = gltf.bufferViews[indices_accessor.bufferView]
                    dtype = GLTF_COMPONENT_TYPE_TO_NUMPY[indices_accessor.componentType]
                    indices_data = np.frombuffer(binary_blob, dtype=dtype, count=indices_accessor.count, offset=(buffer_view.byteOffset or 0) + (indices_accessor.byteOffset or 0))
                    new_primitive['indices'] = np.copy(indices_data).astype(np.uint32)
                    new_primitive['indices_count'] = indices_accessor.count
                    
                    # --- Extraer Vértices ---
                    pos_accessor = gltf.accessors[primitive.attributes.POSITION]
                    buffer_view = gltf.bufferViews[pos_accessor.bufferView]
                    num_components = GLTF_TYPE_TO_NUM_COMPONENTS[pos_accessor.type]
                    dtype = GLTF_COMPONENT_TYPE_TO_NUMPY[pos_accessor.componentType]
                    vertices_data = np.frombuffer(binary_blob, dtype=dtype, count=pos_accessor.count * num_components, offset=(buffer_view.byteOffset or 0) + (pos_accessor.byteOffset or 0))
                    vertices_copy = np.copy(vertices_data).reshape(pos_accessor.count, num_components)
                    new_primitive['vertices'] = vertices_copy.astype(np.float32)
                    self.vertices_all.append(vertices_copy)

                    # --- Extraer Colores de Vértice o Material ---
                    new_primitive['colors'] = None
                    new_primitive['base_color'] = None
                    if hasattr(primitive.attributes, 'COLOR_0') and primitive.attributes.COLOR_0 is not None:
                        color_accessor = gltf.accessors[primitive.attributes.COLOR_0]
                        buffer_view = gltf.bufferViews[color_accessor.bufferView]
                        num_components = GLTF_TYPE_TO_NUM_COMPONENTS[color_accessor.type]
                        dtype = GLTF_COMPONENT_TYPE_TO_NUMPY[color_accessor.componentType]
                        
                        color_data = np.frombuffer(binary_blob, dtype=dtype, count=color_accessor.count * num_components, offset=(buffer_view.byteOffset or 0) + (color_accessor.byteOffset or 0))
                        
                        # LA CORRECCIÓN: Usamos la variable 'color_data' que acabamos de crear
                        new_primitive['colors'] = np.copy(color_data).reshape(color_accessor.count, num_components).astype(np.float32)
                        print("INFO: Datos de color por vértice encontrados y cargados.")
                        
                    elif primitive.material is not None:
                        material = gltf.materials[primitive.material]
                        if material.pbrMetallicRoughness and material.pbrMetallicRoughness.baseColorFactor:
                            new_primitive['base_color'] = material.pbrMetallicRoughness.baseColorFactor
                            print(f"INFO: Usando color de material: {new_primitive['base_color']}")
                    
                    self.primitives.append(new_primitive)

            # --- Normalizar TODO el modelo junto ---
            if not self.vertices_all: return False
            
            all_vertices_np = np.concatenate(self.vertices_all)
            min_coords, max_coords = all_vertices_np.min(axis=0), all_vertices_np.max(axis=0)
            center = (min_coords + max_coords) / 2.0
            scale_factor = (max_coords - min_coords).max()
            if scale_factor == 0: scale_factor = 1

            for primitive in self.primitives:
                primitive['vertices'] -= center
                primitive['vertices'] /= scale_factor

            print(f"INFO: Modelo con {len(gltf.meshes)} mallas cargado y normalizado.")
            return True

        except Exception as e:
            print(f"ERROR: No se pudo cargar el modelo 3D '{filename}': {e}")
            return False
        
    def initGL(self):
        """ Prepara los buffers de OpenGL para CADA primitiva. """
        if not self.primitives: return

        for primitive in self.primitives:
            primitive['vbo'] = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, primitive['vbo'])
            glBufferData(GL_ARRAY_BUFFER, primitive['vertices'].nbytes, primitive['vertices'], GL_STATIC_DRAW)

            primitive['ebo'] = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, primitive['ebo'])
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, primitive['indices'].nbytes, primitive['indices'], GL_STATIC_DRAW)

            primitive['color_vbo'] = None
            if primitive['colors'] is not None:
                primitive['color_vbo'] = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, primitive['color_vbo'])
                glBufferData(GL_ARRAY_BUFFER, primitive['colors'].nbytes, primitive['colors'], GL_STATIC_DRAW)
        
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        print(f"INFO: Buffers de OpenGL para {len(self.primitives)} primitivas creados.")


    def draw(self):
        """ Dibuja cada primitiva del modelo con su propio color. """
        if not self.primitives:
            return
        
        model_scale = self.base_scale  # Usar la escala base del modelo
        glScalef(model_scale, model_scale, model_scale)
        
        rx, ry, rz = self.base_rotation_xyz
        glRotatef(rx, 1, 0, 0) # Rotación sobre X
        glRotatef(ry, 0, 1, 0) # Rotación sobre Y
        glRotatef(rz, 0, 0, 1) # Rotación sobre Z

        glEnable(GL_COLOR_MATERIAL)
        
        for primitive in self.primitives:
            # Activar y apuntar a los buffers de esta primitiva
            glEnableClientState(GL_VERTEX_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, primitive['vbo'])
            glVertexPointer(3, GL_FLOAT, 0, None)
            
            # Establecer el color para esta primitiva
            if primitive['color_vbo']:
                glEnableClientState(GL_COLOR_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, primitive['color_vbo'])
                glColorPointer(primitive['colors'].shape[1], GL_FLOAT, 0, None)
            elif primitive['base_color']:
                glDisableClientState(GL_COLOR_ARRAY)
                glColor4f(*primitive['base_color'])
            else:
                glDisableClientState(GL_COLOR_ARRAY)
                glColor4f(1.0, 1.0, 1.0, 1.0)
            
            # Dibujar
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, primitive['ebo'])
            glDrawElements(GL_TRIANGLES, primitive['indices_count'], GL_UNSIGNED_INT, None)

        # Limpiar el estado al final
        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_COLOR_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)