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

GLTF_COMPONENT_TYPE_TO_NUMPY = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
GLTF_TYPE_TO_NUM_COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}

class GLTFModel:
    def __init__(self):
        self.primitives_by_mesh = {}
        self.textures = []
        self.gltf = None
        self.base_rotation_xyz = (0, 0, 0)
        self.base_scale = 1.0

    def load(self, filename, rotation_xyz_degrees=(0, 0, 0), base_scale=1.0):
        self.base_rotation_xyz = rotation_xyz_degrees
        self.base_scale = base_scale
        try:
            print(f"INFO: Cargando modelo 3D desde '{filename}'...")
            self.gltf = GLTF2.load(filename)
            binary_blob = self.gltf.binary_blob()
            if not binary_blob: self.gltf.load_buffers(); binary_blob = self.gltf.binary_blob()
            if not binary_blob: raise ValueError("No se pudo cargar el buffer binario.")

            model_dir = os.path.dirname(filename)
            for img_info in self.gltf.images:
                if not img_info.uri:
                    self.textures.append(None); continue
                try:
                    img_path = os.path.join(model_dir, img_info.uri.replace('%20', ' '))
                    img = Image.open(img_path).convert("RGBA")
                    self.textures.append(img)
                except Exception as e:
                    print(f"ERROR al cargar la textura {img_info.uri}: {e}")
                    self.textures.append(None)

            all_vertices_list = []
            for i, mesh in enumerate(self.gltf.meshes):
                self.primitives_by_mesh[i] = []
                for primitive in mesh.primitives:
                    new_primitive = {}
                    pos_accessor = self.gltf.accessors[primitive.attributes.POSITION]
                    buffer_view = self.gltf.bufferViews[pos_accessor.bufferView]
                    vertices = np.frombuffer(binary_blob, dtype=GLTF_COMPONENT_TYPE_TO_NUMPY[pos_accessor.componentType], count=pos_accessor.count * GLTF_TYPE_TO_NUM_COMPONENTS[pos_accessor.type], offset=(buffer_view.byteOffset or 0) + (pos_accessor.byteOffset or 0))
                    new_primitive['vertices'] = np.copy(vertices).reshape(pos_accessor.count, GLTF_TYPE_TO_NUM_COMPONENTS[pos_accessor.type])
                    all_vertices_list.append(new_primitive['vertices'])

                    indices_accessor = self.gltf.accessors[primitive.indices]
                    buffer_view = self.gltf.bufferViews[indices_accessor.bufferView]
                    indices = np.frombuffer(binary_blob, dtype=GLTF_COMPONENT_TYPE_TO_NUMPY[indices_accessor.componentType], count=indices_accessor.count, offset=(buffer_view.byteOffset or 0) + (indices_accessor.byteOffset or 0))
                    new_primitive['indices'] = np.copy(indices).astype(np.uint32)
                    new_primitive['indices_count'] = indices_accessor.count
                    
                    new_primitive['texcoords'] = None
                    if hasattr(primitive.attributes, 'TEXCOORD_0') and primitive.attributes.TEXCOORD_0 is not None:
                        tex_accessor = self.gltf.accessors[primitive.attributes.TEXCOORD_0]
                        buffer_view = self.gltf.bufferViews[tex_accessor.bufferView]
                        tex_data = np.frombuffer(binary_blob, dtype=GLTF_COMPONENT_TYPE_TO_NUMPY[tex_accessor.componentType], count=tex_accessor.count * GLTF_TYPE_TO_NUM_COMPONENTS[tex_accessor.type], offset=(buffer_view.byteOffset or 0) + (tex_accessor.byteOffset or 0))
                        new_primitive['texcoords'] = np.copy(tex_data).reshape(tex_accessor.count, GLTF_TYPE_TO_NUM_COMPONENTS[tex_accessor.type])

                    new_primitive['material'] = self.gltf.materials[primitive.material] if primitive.material is not None else None
                    self.primitives_by_mesh[i].append(new_primitive)

            if not all_vertices_list: return False
            all_vertices_np = np.concatenate(all_vertices_list)
            center = (all_vertices_np.min(axis=0) + all_vertices_np.max(axis=0)) / 2.0
            scale_factor = (all_vertices_np.max(axis=0) - all_vertices_np.min(axis=0)).max()
            if scale_factor == 0: scale_factor = 1
            for mesh_primitives in self.primitives_by_mesh.values():
                for primitive in mesh_primitives:
                    primitive['vertices'] -= center
                    primitive['vertices'] /= scale_factor
            return True
        except Exception as e:
            print(f"ERROR: No se pudo cargar el modelo 3D '{filename}': {e}")
            return False

    def initGL(self):
        if not self.primitives_by_mesh: return
        
        gl_textures = []
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

        for mesh_primitives in self.primitives_by_mesh.values():
            for primitive in mesh_primitives:
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
        if not self.gltf: return
        glPushMatrix()
        glScalef(self.base_scale, self.base_scale, self.base_scale)
        rx, ry, rz = self.base_rotation_xyz
        glRotatef(rx, 1, 0, 0); glRotatef(ry, 0, 1, 0); glRotatef(rz, 0, 0, 1)

        root_nodes = self.gltf.scenes[self.gltf.scene].nodes
        for node_index in root_nodes:
            self._draw_node(self.gltf.nodes[node_index])
        glPopMatrix()

    def _draw_node(self, node):
        glPushMatrix()
        if node.matrix: glMultMatrixf(np.array(node.matrix).T)
        
        if node.mesh is not None:
            for primitive in self.primitives_by_mesh.get(node.mesh, []):
                material = primitive.get('material')
                base_color = [1.0, 1.0, 1.0, 1.0]
                texture_id = None
                
                if material and material.pbrMetallicRoughness:
                    if material.pbrMetallicRoughness.baseColorFactor:
                        base_color = material.pbrMetallicRoughness.baseColorFactor
                    if material.pbrMetallicRoughness.baseColorTexture:
                        texture_id = self.textures[material.pbrMetallicRoughness.baseColorTexture.index]

                glColor4f(*base_color)
                
                if texture_id and primitive['texcoord_vbo']:
                    glEnable(GL_TEXTURE_2D)
                    glBindTexture(GL_TEXTURE_2D, texture_id)
                    glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                    glBindBuffer(GL_ARRAY_BUFFER, primitive['texcoord_vbo'])
                    glTexCoordPointer(2, GL_FLOAT, 0, None)
                else:
                    glDisable(GL_TEXTURE_2D)
                
                glEnableClientState(GL_VERTEX_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, primitive['vbo'])
                glVertexPointer(3, GL_FLOAT, 0, None)
                glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, primitive['ebo'])
                glDrawElements(GL_TRIANGLES, primitive['indices_count'], GL_UNSIGNED_INT, None)
        
        if node.children:
            for child_index in node.children:
                self._draw_node(self.gltf.nodes[child_index])

        glPopMatrix()