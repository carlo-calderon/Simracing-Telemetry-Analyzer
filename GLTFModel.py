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
import os
from PIL import Image

# ... (Los diccionarios de mapeo no cambian) ...
GLTF_COMPONENT_TYPE_TO_NUMPY = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
GLTF_TYPE_TO_NUM_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}

class GLTFModel:
    def __init__(self):
        self.primitives = []
        self.vertices_all = []
        self.base_rotation_xyz = (0, 0, 0)
        self.base_scale = 1.0
        self.textures = []

    def load(self, filename, rotation_xyz_degrees=(0, 0, 0), base_scale=1.0):
        self.base_rotation_xyz = rotation_xyz_degrees
        self.base_scale = base_scale
        try:
            print(f"INFO: Cargando modelo 3D desde '{filename}'...")
            gltf = GLTF2.load(filename)
            binary_blob = gltf.binary_blob()
            if not binary_blob: gltf.load_buffers(); binary_blob = gltf.binary_blob()
            if not binary_blob: raise ValueError("No se pudo cargar el buffer binario.")

            # --- Cargar las imágenes de las texturas (con la corrección) ---
            model_dir = os.path.dirname(filename)
            for img_info in gltf.images:
                # --- COMPROBACIÓN AÑADIDA ---
                if not img_info.uri:
                    print("ADVERTENCIA: Se encontró una imagen sin URI en el GLTF, se omitirá.")
                    self.textures.append(None) # Añadimos None para mantener la consistencia de los índices
                    continue # Pasamos a la siguiente imagen

                try:
                    # Reemplazamos los espacios codificados en la ruta
                    img_path = os.path.join(model_dir, img_info.uri.replace('%20', ' '))
                    img = Image.open(img_path).convert("RGBA")
                    self.textures.append(img)
                    print(f"INFO: Textura '{img_info.uri}' cargada.")
                except Exception as e:
                    print(f"ERROR al cargar la textura {img_info.uri}: {e}")
                    self.textures.append(None)
            
            for mesh in gltf.meshes:
                for primitive in mesh.primitives:
                    new_primitive = {}
                    # ... (el resto de la lógica de carga de vértices, índices y materiales no cambia) ...
                    indices_accessor = gltf.accessors[primitive.indices]
                    buffer_view = gltf.bufferViews[indices_accessor.bufferView]
                    indices_data = np.frombuffer(binary_blob, dtype=GLTF_COMPONENT_TYPE_TO_NUMPY[indices_accessor.componentType], count=indices_accessor.count, offset=(buffer_view.byteOffset or 0) + (indices_accessor.byteOffset or 0))
                    new_primitive['indices'] = np.copy(indices_data).astype(np.uint32)
                    new_primitive['indices_count'] = indices_accessor.count
                    
                    pos_accessor = gltf.accessors[primitive.attributes.POSITION]
                    buffer_view = gltf.bufferViews[pos_accessor.bufferView]
                    vertices_data = np.frombuffer(binary_blob, dtype=GLTF_COMPONENT_TYPE_TO_NUMPY[pos_accessor.componentType], count=pos_accessor.count * GLTF_TYPE_TO_NUM_COMPONENTS[pos_accessor.type], offset=(buffer_view.byteOffset or 0) + (pos_accessor.byteOffset or 0))
                    vertices_copy = np.copy(vertices_data).reshape(pos_accessor.count, GLTF_TYPE_TO_NUM_COMPONENTS[pos_accessor.type])
                    new_primitive['vertices'] = vertices_copy
                    self.vertices_all.append(vertices_copy)
                    
                    new_primitive['texcoords'] = None
                    if hasattr(primitive.attributes, 'TEXCOORD_0') and primitive.attributes.TEXCOORD_0 is not None:
                        tex_accessor = gltf.accessors[primitive.attributes.TEXCOORD_0]
                        buffer_view = gltf.bufferViews[tex_accessor.bufferView]
                        tex_data = np.frombuffer(binary_blob, dtype=GLTF_COMPONENT_TYPE_TO_NUMPY[tex_accessor.componentType], count=tex_accessor.count * GLTF_TYPE_TO_NUM_COMPONENTS[tex_accessor.type], offset=(buffer_view.byteOffset or 0) + (tex_accessor.byteOffset or 0))
                        new_primitive['texcoords'] = np.copy(tex_data).reshape(tex_accessor.count, GLTF_TYPE_TO_NUM_COMPONENTS[tex_accessor.type])

                    new_primitive['material_info'] = {'base_color': [1,1,1,1], 'texture_id': None}
                    if primitive.material is not None:
                        material = gltf.materials[primitive.material]
                        if material.pbrMetallicRoughness:
                            if material.pbrMetallicRoughness.baseColorFactor:
                                new_primitive['material_info']['base_color'] = material.pbrMetallicRoughness.baseColorFactor
                            if material.pbrMetallicRoughness.baseColorTexture:
                                new_primitive['material_info']['texture_id'] = material.pbrMetallicRoughness.baseColorTexture.index
                    
                    self.primitives.append(new_primitive)
            
            # ... (código de normalización no cambia) ...
            if not self.vertices_all: return False
            all_vertices_np = np.concatenate(self.vertices_all)
            min_coords, max_coords = all_vertices_np.min(axis=0), all_vertices_np.max(axis=0)
            center = (min_coords + max_coords) / 2.0
            scale_factor = (max_coords - min_coords).max()
            if scale_factor == 0: scale_factor = 1
            for primitive in self.primitives:
                primitive['vertices'] -= center
                primitive['vertices'] /= scale_factor
            return True
        except Exception as e:
            print(f"ERROR: No se pudo cargar el modelo 3D '{filename}': {e}")
            return False

    def initGL(self):
        # ... (esta función no cambia) ...
        if not self.primitives: return
        gl_textures = []
        if self.textures:
            for img in self.textures:
                if img:
                    img_data = np.array(list(img.getdata()), np.uint8)
                    texture_id = glGenTextures(1)
                    glBindTexture(GL_TEXTURE_2D, texture_id)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
                    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
                    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
                    glGenerateMipmap(GL_TEXTURE_2D)
                    gl_textures.append(texture_id)
                else:
                    gl_textures.append(None)
        self.textures = gl_textures

        for primitive in self.primitives:
            primitive['vbo'] = glGenBuffers(1)
            glBindBuffer(GL_ARRAY_BUFFER, primitive['vbo'])
            glBufferData(GL_ARRAY_BUFFER, primitive['vertices'].astype(np.float32).nbytes, primitive['vertices'].astype(np.float32), GL_STATIC_DRAW)
            primitive['ebo'] = glGenBuffers(1)
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, primitive['ebo'])
            glBufferData(GL_ELEMENT_ARRAY_BUFFER, primitive['indices'].nbytes, primitive['indices'], GL_STATIC_DRAW)
            primitive['texcoord_vbo'] = None
            if primitive['texcoords'] is not None:
                primitive['texcoord_vbo'] = glGenBuffers(1)
                glBindBuffer(GL_ARRAY_BUFFER, primitive['texcoord_vbo'])
                glBufferData(GL_ARRAY_BUFFER, primitive['texcoords'].astype(np.float32).nbytes, primitive['texcoords'].astype(np.float32), GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

    def draw(self):
        # ... (esta función no cambia) ...
        if not self.primitives: return
        glPushMatrix()
        glScalef(self.base_scale, self.base_scale, self.base_scale)
        rx, ry, rz = self.base_rotation_xyz
        glRotatef(rx, 1, 0, 0); glRotatef(ry, 0, 1, 0); glRotatef(rz, 0, 0, 1)

        glEnable(GL_COLOR_MATERIAL)
        glEnableClientState(GL_VERTEX_ARRAY)

        for primitive in self.primitives:
            glBindBuffer(GL_ARRAY_BUFFER, primitive['vbo'])
            glVertexPointer(3, GL_FLOAT, 0, None)
            material_info = primitive['material_info']
            base_color = material_info['base_color']
            texture_id = material_info['texture_id']
            glColor4f(*base_color)

            if texture_id is not None and primitive['texcoord_vbo'] and self.textures[texture_id] is not None:
                glEnable(GL_TEXTURE_2D)
                glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                glBindTexture(GL_TEXTURE_2D, self.textures[texture_id])
                glBindBuffer(GL_ARRAY_BUFFER, primitive['texcoord_vbo'])
                glTexCoordPointer(2, GL_FLOAT, 0, None)
            else:
                glDisable(GL_TEXTURE_2D)
                glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            
            glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, primitive['ebo'])
            glDrawElements(GL_TRIANGLES, primitive['indices_count'], GL_UNSIGNED_INT, None)

        glDisableClientState(GL_VERTEX_ARRAY)
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)
        glDisable(GL_TEXTURE_2D)
        glPopMatrix()