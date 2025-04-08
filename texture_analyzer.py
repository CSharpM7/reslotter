# Habilitar referencias adelantadas en anotaciones de tipo
from __future__ import annotations

import os
import re
import json
import struct
import shutil
import binascii
import importlib.util
import subprocess
import sys
import time
import tempfile
import glob
from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path
import logging
import argparse

# Global para indicar si ssbh_data_py está disponible
SSBH_DATA_PY_AVAILABLE = None

def install_ssbh_data_py() -> bool:
    """Instala la biblioteca ssbh_data_py si no está disponible"""
    try:
        import ssbh_data_py
        return True
    except ImportError:
        print("Instalando la biblioteca ssbh_data_py...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "ssbh_data_py"])
            return True
        except Exception as e:
            print(f"Error al instalar ssbh_data_py: {e}")
            return False

def check_ssbh_data_py_available() -> bool:
    """Comprueba si ssbh_data_py está disponible"""
    global SSBH_DATA_PY_AVAILABLE
    if SSBH_DATA_PY_AVAILABLE is None:
        try:
            import ssbh_data_py
            SSBH_DATA_PY_AVAILABLE = True
        except ImportError:
            SSBH_DATA_PY_AVAILABLE = False
    return SSBH_DATA_PY_AVAILABLE

def try_read_matl_with_ssbh(file_path: str) -> List[TextureReference]:
    """
    Intenta leer un archivo .numatb usando ssbh_data_py y devuelve una lista de referencias a texturas.
    """
    if not check_ssbh_data_py_available():
        return []
    
    try:
        import ssbh_data_py
        matl = ssbh_data_py.matl_data.read_matl(file_path)
        references = []
        
        for entry in matl.entries:
            material_label = entry.material_label
            
            for texture in entry.textures:
                # Convertir ParamId a string para mejor legibilidad
                param_id = str(texture.param_id)
                texture_path = texture.data
                
                ref = TextureReference(
                    texture_path=texture_path,
                    parameter_name=param_id,
                    material_label=material_label,
                    file_path=file_path
                )
                references.append(ref)
        
        return references
    except Exception as e:
        print(f"Error al leer {file_path} con ssbh_data_py: {e}")
        return []

def try_read_anim_with_ssbh(file_path: str) -> Dict[str, Any]:
    """
    Intenta leer un archivo .nuanmb usando ssbh_data_py y devuelve la información de animación.
    """
    if not check_ssbh_data_py_available():
        return {}
    
    try:
        import ssbh_data_py
        print(f"Leyendo archivo de animación: {file_path}")
        anim = ssbh_data_py.anim_data.read_anim(file_path)
        
        # Crear un diccionario con la información disponible
        anim_info = {
            "name": os.path.basename(file_path),
            "attributes": [],
            "file_path": file_path
        }
        
        # Listar todos los atributos disponibles en este objeto
        print(f"Extrayendo atributos de {os.path.basename(file_path)}...")
        for attr_name in dir(anim):
            if not attr_name.startswith("_"):  # Ignorar atributos privados
                try:
                    attr_value = getattr(anim, attr_name)
                    attr_type = type(attr_value).__name__
                    is_callable = callable(attr_value)
                    anim_info["attributes"].append(f"{attr_name}: {attr_type} {'(callable)' if is_callable else ''}")
                    
                    # Guardar valores simples directamente
                    if not is_callable and attr_type in ["int", "float", "str", "bool"]:
                        anim_info[attr_name] = attr_value
                        print(f"  - Atributo simple: {attr_name} = {attr_value}")
                except Exception as e:
                    print(f"  - Error al acceder a {attr_name}: {e}")
        
        # Examinar la estructura de los grupos
        if hasattr(anim, 'groups') and anim.groups:
            print(f"Encontrados {len(anim.groups)} grupos de animación")
            anim_info["groups"] = []
            
            for i, group in enumerate(anim.groups):
                group_info = {"index": i}
                
                # Intentar extraer información básica del grupo
                if hasattr(group, 'name'):
                    group_info["name"] = group.name
                
                # Buscar referencias a materiales o texturas
                materials_found = []
                if hasattr(group, 'nodes'):
                    group_info["nodes"] = []
                    for node in group.nodes:
                        node_info = {}
                        if hasattr(node, 'name'):
                            node_info["name"] = node.name
                        
                        # Buscar visibilidad de materiales
                        if hasattr(node, 'material_visibilities'):
                            node_info["material_visibilities"] = []
                            for mat_vis in node.material_visibilities:
                                if hasattr(mat_vis, 'material_name'):
                                    mat_name = mat_vis.material_name
                                    node_info["material_visibilities"].append(mat_name)
                                    materials_found.append(mat_name)
                        
                        group_info["nodes"].append(node_info)
                
                # Añadir información de texturas o materiales encontrados
                if materials_found:
                    group_info["materials_referenced"] = materials_found
                
                anim_info["groups"].append(group_info)
        
        # Examinar la estructura de los tracks o pistas
        if hasattr(anim, 'tracks') and anim.tracks:
            print(f"Encontrados {len(anim.tracks)} tracks de animación")
            anim_info["tracks"] = []
            
            for i, track in enumerate(anim.tracks):
                track_info = {"index": i}
                
                # Extraer atributos básicos del track
                if hasattr(track, 'name'):
                    track_info["name"] = track.name
                    print(f"  - Track: {track.name}")
                
                # Examinar visibilidad de materiales
                materials_found = []
                if hasattr(track, 'material_visibility_entries') and track.material_visibility_entries:
                    track_info["material_visibility_entries"] = []
                    print(f"  - Encontradas {len(track.material_visibility_entries)} entradas de visibilidad de materiales")
                    
                    for entry in track.material_visibility_entries:
                        entry_info = {}
                        if hasattr(entry, 'name'):
                            entry_info["name"] = entry.name
                            materials_found.append(entry.name)
                            print(f"    - Material: {entry.name}")
                        
                        # Intentar obtener frames de visibilidad si existen
                        if hasattr(entry, 'visibility_frames'):
                            entry_info["frame_count"] = len(entry.visibility_frames)
                        
                        track_info["material_visibility_entries"].append(entry_info)
                
                # Reunir los materiales encontrados para facilidad de uso
                if materials_found:
                    track_info["materials_referenced"] = materials_found
                
                anim_info["tracks"].append(track_info)
        
        return anim_info
    except Exception as e:
        print(f"Error al leer {file_path} con ssbh_data_py: {e}")
        
        # Intentar método alternativo
        try:
            print(f"Intentando método alternativo para {file_path}...")
            # Examinar el archivo binario para buscar nombres de materiales
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Buscar posibles cadenas que parezcan nombres de materiales
            material_pattern = re.compile(b'(def|mat)_[a-zA-Z0-9_]+')
            matches = material_pattern.findall(data)
            
            # Crear estructura simple
            anim_info = {
                "name": os.path.basename(file_path),
                "method": "binary_search",
                "possible_materials": [m.decode('utf-8', errors='ignore') for m in set(matches)]
            }
            return anim_info
        except Exception as fallback_error:
            print(f"Error también en método alternativo: {fallback_error}")
            return {}

def convert_numatb_to_json(file_path: str, output_dir: str) -> Optional[str]:
    """
    Convierte un archivo .numatb a JSON usando ssbh_data_py.
    
    Args:
        file_path: Ruta al archivo .numatb
        output_dir: Directorio donde guardar el archivo JSON
        
    Returns:
        Ruta al archivo JSON o None si hubo un error
    """
    if not check_ssbh_data_py_available():
        print("ssbh_data_py no está disponible, no se puede convertir a JSON")
        return None
    
    try:
        import ssbh_data_py
        matl = ssbh_data_py.matl_data.read_matl(file_path)
        
        materials = []
        for entry in matl.entries:
            material_info = {
                "material_label": entry.material_label,
                "shader_label": entry.shader_label,
                "textures": []
            }
            
            # Extraer texturas
            for texture in entry.textures:
                # Convertir ParamId a string para hacerlo serializable
                param_id_str = str(texture.param_id)
                texture_info = {
                    "param_id": param_id_str,
                    "texture_path": texture.data
                }
                material_info["textures"].append(texture_info)
            
            # Extraer otros parámetros si están disponibles
            if hasattr(entry, 'vectors') and entry.vectors:
                material_info["vectors"] = []
                for vector in entry.vectors:
                    material_info["vectors"].append({
                        "param_id": str(vector.param_id),
                        "data": [vector.data.x, vector.data.y, vector.data.z, vector.data.w] if hasattr(vector.data, 'x') else str(vector.data)
                    })
            
            if hasattr(entry, 'floats') and entry.floats:
                material_info["floats"] = []
                for float_param in entry.floats:
                    material_info["floats"].append({
                        "param_id": str(float_param.param_id),
                        "data": float_param.data
                    })
            
            if hasattr(entry, 'booleans') and entry.booleans:
                material_info["booleans"] = []
                for bool_param in entry.booleans:
                    material_info["booleans"].append({
                        "param_id": str(bool_param.param_id),
                        "data": bool_param.data
                    })
            
            # Agregar los samplers para análisis adicional
            if hasattr(entry, 'samplers') and entry.samplers:
                material_info["samplers"] = []
                for sampler in entry.samplers:
                    material_info["samplers"].append({
                        "param_id": str(sampler.param_id),
                        "data": {
                            "wrap_s": str(sampler.data.wraps) if hasattr(sampler.data, 'wraps') else None,
                            "wrap_t": str(sampler.data.wrapt) if hasattr(sampler.data, 'wrapt') else None,
                            "min_filter": str(sampler.data.min_filter) if hasattr(sampler.data, 'min_filter') else None,
                            "mag_filter": str(sampler.data.mag_filter) if hasattr(sampler.data, 'mag_filter') else None
                        }
                    })
            
            materials.append(material_info)
        
        # Crear nombre del archivo JSON basado en el original
        base_name = os.path.basename(file_path)
        json_name = f"{os.path.splitext(base_name)[0]}.json"
        json_path = os.path.join(output_dir, json_name)
        
        # Guardar en formato JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(materials, f, indent=2)
        
        print(f"Convertido {file_path} a JSON: {json_path}")
        return json_path
    except Exception as e:
        print(f"Error al convertir {file_path} a JSON: {e}")
        
        # Intentar método alternativo usando análisis binario
        try:
            print(f"Intentando método alternativo para {file_path}...")
            parser = MatlParser(file_path)
            texture_refs = parser.parse()
            
            # Crear estructura simple para guardar
            materials = []
            material_refs = {}
            
            for ref in texture_refs:
                if ref.material_label not in material_refs:
                    material_refs[ref.material_label] = {
                        "material_label": ref.material_label,
                        "textures": []
                    }
                
                material_refs[ref.material_label]["textures"].append({
                    "param_id": ref.parameter_name,
                    "texture_path": ref.texture_path
                })
            
            for material_label, material_data in material_refs.items():
                materials.append(material_data)
            
            # Crear nombre del archivo JSON basado en el original
            base_name = os.path.basename(file_path)
            json_name = f"{os.path.splitext(base_name)[0]}_fallback.json"
            json_path = os.path.join(output_dir, json_name)
            
            # Guardar en formato JSON
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(materials, f, indent=2)
            
            print(f"Convertido {file_path} a JSON usando método alternativo: {json_path}")
            return json_path
        except Exception as fallback_error:
            print(f"Error también en método alternativo: {fallback_error}")
            return None

def convert_nuanmb_to_text(file_path: str, output_dir: str) -> Optional[str]:
    """
    Convierte un archivo .nuanmb a texto usando ssbh_data_py.
    
    Args:
        file_path: Ruta al archivo .nuanmb
        output_dir: Directorio donde guardar el archivo de texto
        
    Returns:
        Ruta al archivo de texto o None si hubo un error
    """
    if not check_ssbh_data_py_available():
        print("ssbh_data_py no está disponible, no se puede convertir a texto")
        return None
    
    try:
        anim_info = try_read_anim_with_ssbh(file_path)
        if not anim_info:
            return None
            
        # Crear nombre del archivo de texto basado en el original
        base_name = os.path.basename(file_path)
        txt_name = f"{os.path.splitext(base_name)[0]}.txt"
        txt_path = os.path.join(output_dir, txt_name)
        
        # Generar texto formateado
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Archivo: {base_name}\n")
            f.write(f"Ruta: {file_path}\n\n")
            
            # Escribir información básica
            basic_keys = ['name', 'major_version', 'minor_version', 'frames']
            for key in basic_keys:
                if key in anim_info:
                    f.write(f"{key}: {anim_info[key]}\n")
            
            # Separador
            f.write("\n--- INFORMACIÓN DETALLADA ---\n\n")
            
            # Escribir información de los atributos disponibles
            f.write("Atributos disponibles:\n")
            for attr in anim_info.get("attributes", []):
                f.write(f"- {attr}\n")
            
            # Información detallada de los grupos
            if "groups" in anim_info and anim_info["groups"]:
                f.write(f"\nGrupos de animación ({len(anim_info['groups'])}):\n")
                for i, group in enumerate(anim_info["groups"]):
                    f.write(f"- Grupo {i+1}: {group.get('name', 'Sin nombre')}\n")
                    
                    # Listar materiales en este grupo
                    if "materials_referenced" in group and group["materials_referenced"]:
                        f.write(f"  Materiales referenciados en este grupo ({len(group['materials_referenced'])}):\n")
                        for material in group["materials_referenced"]:
                            f.write(f"  * {material}\n")
            
            # Información detallada de los tracks
            if "tracks" in anim_info and anim_info["tracks"]:
                f.write(f"\nPistas de animación ({len(anim_info['tracks'])}):\n")
                for i, track in enumerate(anim_info["tracks"]):
                    f.write(f"- Pista {i+1}: {track.get('name', 'Sin nombre')}\n")
                    
                    # Listar materiales con visibilidad animada en este track
                    if "materials_referenced" in track and track["materials_referenced"]:
                        f.write(f"  Materiales con visibilidad animada ({len(track['materials_referenced'])}):\n")
                        for material in track["materials_referenced"]:
                            f.write(f"  * {material}\n")
            
            # Si es método alternativo
            if "method" in anim_info and anim_info["method"] == "binary_search":
                f.write("\nMétodo alternativo - Posibles nombres de materiales encontrados:\n")
                for material in anim_info.get("possible_materials", []):
                    if material.startswith(("def_", "mat_")):
                        f.write(f"* {material}\n")
            
            # Intentar extraer todo lo posible como información adicional
            import json
            try:
                f.write("\nInformación completa (JSON):\n")
                # Eliminar atributos que pueden ser demasiado grandes
                info_copy = anim_info.copy()
                if "attributes" in info_copy:
                    del info_copy["attributes"]
                if "file_path" in info_copy:
                    del info_copy["file_path"]
                json_str = json.dumps(info_copy, indent=2, default=str)
                f.write(json_str)
            except Exception as e:
                f.write(f"Error al convertir a JSON: {e}")
            
        print(f"Generado archivo de texto: {txt_path}")
        return txt_path
    except Exception as e:
        print(f"Error al convertir {file_path} a texto: {e}")
        return None

def try_read_modl_with_ssbh(file_path: str) -> Dict[str, Any]:
    """
    Intenta leer un archivo .numdlb usando ssbh_data_py y devuelve la información del modelo.
    """
    if not check_ssbh_data_py_available():
        return {}
    
    try:
        import ssbh_data_py
        print(f"Leyendo archivo de modelo: {file_path}")
        modl = ssbh_data_py.modl_data.read_modl(file_path)
        
        # Crear un diccionario con la información disponible
        modl_info = {
            "name": os.path.basename(file_path),
            "attributes": [],
            "file_path": file_path
        }
        
        # Listar todos los atributos disponibles en este objeto
        print(f"Extrayendo atributos de {os.path.basename(file_path)}...")
        for attr_name in dir(modl):
            if not attr_name.startswith("_"):  # Ignorar atributos privados
                try:
                    attr_value = getattr(modl, attr_name)
                    attr_type = type(attr_value).__name__
                    is_callable = callable(attr_value)
                    modl_info["attributes"].append(f"{attr_name}: {attr_type} {'(callable)' if is_callable else ''}")
                    
                    # Guardar valores simples directamente
                    if not is_callable and attr_type in ["int", "float", "str", "bool"]:
                        modl_info[attr_name] = attr_value
                        print(f"  - Atributo simple: {attr_name} = {attr_value}")
                except Exception as e:
                    print(f"  - Error al acceder a {attr_name}: {e}")
        
        # Buscar referencias a materiales
        material_refs = []
        
        # Examinar mallas (meshes)
        if hasattr(modl, 'meshes') and modl.meshes:
            print(f"Encontradas {len(modl.meshes)} mallas")
            modl_info["meshes"] = []
            
            for i, mesh in enumerate(modl.meshes):
                mesh_info = {"index": i}
                
                # Extraer nombre si está disponible
                if hasattr(mesh, 'name'):
                    mesh_info["name"] = mesh.name
                
                # Extraer material si está disponible
                if hasattr(mesh, 'material_label'):
                    mesh_info["material_label"] = mesh.material_label
                    material_refs.append(mesh.material_label)
                
                # Extraer atributos adicionales
                if hasattr(mesh, 'bounding_radius'):
                    mesh_info["bounding_radius"] = mesh.bounding_radius
                
                modl_info["meshes"].append(mesh_info)
        
        # Examinar huesos (bones)
        if hasattr(modl, 'bones') and modl.bones:
            print(f"Encontrados {len(modl.bones)} huesos")
            modl_info["bones"] = []
            
            for i, bone in enumerate(modl.bones):
                bone_info = {"index": i}
                
                if hasattr(bone, 'name'):
                    bone_info["name"] = bone.name
                
                if hasattr(bone, 'parent_index'):
                    bone_info["parent_index"] = bone.parent_index
                
                modl_info["bones"].append(bone_info)
        
        # Añadir lista unificada de materiales
        if material_refs:
            modl_info["material_references"] = list(set(material_refs))
        
        return modl_info
    except Exception as e:
        print(f"Error al leer {file_path} con ssbh_data_py: {e}")
        
        # Intentar método alternativo
        try:
            print(f"Intentando método alternativo para {file_path}...")
            # Examinar el archivo binario para buscar nombres de materiales
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Buscar posibles cadenas que parezcan nombres de materiales
            material_pattern = re.compile(b'(def|mat)_[a-zA-Z0-9_]+')
            matches = material_pattern.findall(data)
            
            # Crear estructura simple
            modl_info = {
                "name": os.path.basename(file_path),
                "method": "binary_search",
                "possible_materials": [m.decode('utf-8', errors='ignore') for m in set(matches)]
            }
            return modl_info
        except Exception as fallback_error:
            print(f"Error también en método alternativo: {fallback_error}")
            return {}

def convert_numdlb_to_text(file_path: str, output_dir: str) -> Optional[str]:
    """
    Convierte un archivo .numdlb a texto usando ssbh_data_py.
    
    Args:
        file_path: Ruta al archivo .numdlb
        output_dir: Directorio donde guardar el archivo de texto
        
    Returns:
        Ruta al archivo de texto o None si hubo un error
    """
    if not check_ssbh_data_py_available():
        print("ssbh_data_py no está disponible, no se puede convertir a texto")
        return None
    
    try:
        modl_info = try_read_modl_with_ssbh(file_path)
        if not modl_info:
            return None
            
        # Crear nombre del archivo de texto basado en el original
        base_name = os.path.basename(file_path)
        txt_name = f"{os.path.splitext(base_name)[0]}_model.txt"
        txt_path = os.path.join(output_dir, txt_name)
        
        # Generar texto formateado
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"Archivo de modelo: {base_name}\n")
            f.write(f"Ruta: {file_path}\n\n")
            
            # Escribir información básica
            basic_keys = ['name', 'major_version', 'minor_version']
            for key in basic_keys:
                if key in modl_info:
                    f.write(f"{key}: {modl_info[key]}\n")
            
            # Separador
            f.write("\n--- INFORMACIÓN DETALLADA DEL MODELO ---\n\n")
            
            # Escribir información de los atributos disponibles
            f.write("Atributos disponibles:\n")
            for attr in modl_info.get("attributes", []):
                f.write(f"- {attr}\n")
            
            # Información de materiales
            if "material_references" in modl_info and modl_info["material_references"]:
                f.write(f"\nMateriales referenciados ({len(modl_info['material_references'])}):\n")
                for material in modl_info["material_references"]:
                    f.write(f"* {material}\n")
            
            # Información de mallas
            if "meshes" in modl_info and modl_info["meshes"]:
                f.write(f"\nMallas ({len(modl_info['meshes'])}):\n")
                for i, mesh in enumerate(modl_info["meshes"]):
                    f.write(f"- Malla {i+1}: {mesh.get('name', 'Sin nombre')}\n")
                    
                    if "material_label" in mesh:
                        f.write(f"  Material: {mesh['material_label']}\n")
                    
                    if "bounding_radius" in mesh:
                        f.write(f"  Radio de límite: {mesh['bounding_radius']}\n")
            
            # Información de huesos
            if "bones" in modl_info and modl_info["bones"]:
                f.write(f"\nHuesos ({len(modl_info['bones'])}):\n")
                for i, bone in enumerate(modl_info["bones"]):
                    parent_info = f", Padre: {bone['parent_index']}" if "parent_index" in bone else ""
                    f.write(f"- Hueso {i}: {bone.get('name', 'Sin nombre')}{parent_info}\n")
            
            # Si es método alternativo
            if "method" in modl_info and modl_info["method"] == "binary_search":
                f.write("\nMétodo alternativo - Posibles nombres de materiales encontrados:\n")
                for material in modl_info.get("possible_materials", []):
                    if material.startswith(("def_", "mat_")):
                        f.write(f"* {material}\n")
            
            # Intentar extraer todo lo posible como información adicional
            import json
            try:
                f.write("\nInformación completa (JSON):\n")
                # Eliminar atributos que pueden ser demasiado grandes
                info_copy = modl_info.copy()
                if "attributes" in info_copy:
                    del info_copy["attributes"]
                if "file_path" in info_copy:
                    del info_copy["file_path"]
                json_str = json.dumps(info_copy, indent=2, default=str)
                f.write(json_str)
            except Exception as e:
                f.write(f"Error al convertir a JSON: {e}")
            
        print(f"Generado archivo de texto para modelo: {txt_path}")
        return txt_path
    except Exception as e:
        print(f"Error al convertir {file_path} a texto: {e}")
        return None

class TextureReference:
    """Representa una referencia a una textura en un archivo de material"""
    
    def __init__(self, texture_path: str, parameter_name: str, material_label: str = "", file_path: str = ""):
        self.texture_path = texture_path         # Ruta del archivo de textura
        self.parameter_name = parameter_name     # Nombre del parámetro (ej: "Texture0")
        self.material_label = material_label     # Etiqueta del material al que pertenece
        self.file_path = file_path               # Ruta del archivo de material
    
    def __str__(self) -> str:
        return f"{self.material_label} -> {self.parameter_name}: {self.texture_path}"

class MatlHeader:
    """Encabezado de un archivo MATL de Smash Ultimate"""
    
    def __init__(self):
        self.magic = b''           # Marca de identificación del archivo (debe ser 'LTAM')
        self.version = 0           # Versión del formato
        self.entry_count = 0       # Número de entradas de materiales
        
    @classmethod
    def from_binary(cls, data: bytes) -> 'MatlHeader':
        """Crea un MatlHeader desde datos binarios"""
        header = cls()
        if len(data) >= 12:
            header.magic = data[0:4]
            header.version = int.from_bytes(data[4:8], byteorder='little')
            header.entry_count = int.from_bytes(data[8:12], byteorder='little')
        return header

class MatlEntryInfo:
    """Información básica sobre una entrada de material en un archivo MATL"""
    
    def __init__(self):
        self.material_label = ""    # Etiqueta del material
        self.shader_label = ""      # Etiqueta del shader utilizado

class MatlParser:
    """Parser simple para archivos NUMATB."""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
    
    def parse(self) -> List[TextureReference]:
        """
        Parsea un archivo .numatb y devuelve una lista de referencias a texturas.
        Este es un analizador de respaldo en caso de que ssbh_data_py no esté disponible.
        """
        references = []
        
        try:
            # Primero intentar con ssbh_data_py
            if check_ssbh_data_py_available():
                refs = try_read_matl_with_ssbh(self.filepath)
                if refs:
                    return refs
            
            # Si falla, intentar con análisis binario básico
            with open(self.filepath, 'rb') as f:
                data = f.read()
            
            # Buscar cadenas que parezcan nombres de materiales o texturas
            material_pattern = re.compile(b'(def|mat)_[a-zA-Z0-9_]+')
            texture_pattern = re.compile(b'[a-zA-Z0-9_/]+\.(bntx|nutexb)')
            
            materials = material_pattern.findall(data)
            textures = texture_pattern.findall(data)
            
            # Convertir a strings
            material_strs = [m.decode('utf-8', errors='ignore') for m in materials]
            texture_strs = [t.decode('utf-8', errors='ignore') for t in textures]
            
            # Filtrar duplicados
            material_strs = list(set(material_strs))
            texture_strs = list(set(texture_strs))
            
            # Si no se encontraron materiales explícitos, usar "default"
            if not material_strs:
                material_strs = ["default_material"]
            
            # Crear referencias para cada combinación material-textura
            for material in material_strs:
                for i, texture in enumerate(texture_strs):
                    ref = TextureReference(
                        texture_path=texture,
                        parameter_name=f"Texture{i}",
                        material_label=material,
                        file_path=self.filepath
                    )
                    references.append(ref)
        
        except Exception as e:
            print(f"Error al parsear {self.filepath}: {e}")
        
        return references

class TextureAnalyzer:
    """Analizador de archivos de texturas para Smash Ultimate"""
    
    def __init__(self, mod_directory: str, debug: bool = False):
        self.mod_directory = mod_directory
        self.junk_dir = os.path.join(mod_directory, "junk")
        self.temp_dir = None
        self.use_ssbh = check_ssbh_data_py_available()
        self.debug = debug
        
        if not self.use_ssbh:
            print("La biblioteca ssbh_data_py no está instalada.")
            print("Esta biblioteca permite una detección mucho más precisa de texturas.")
            self.use_ssbh = install_ssbh_data_py()
        
        # Crear carpeta junk si no existe
        if not os.path.exists(self.junk_dir):
            os.makedirs(self.junk_dir)
    
    def create_temp_dir(self):
        """Crea un directorio temporal para los archivos JSON"""
        if self.temp_dir is None:
            self.temp_dir = os.path.join(tempfile.gettempdir(), f"texture_analyzer_{int(time.time())}")
            os.makedirs(self.temp_dir, exist_ok=True)
        return self.temp_dir
    
    def cleanup_temp_dir(self):
        """Limpia el directorio temporal"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
            except Exception as e:
                print(f"Error al limpiar directorio temporal: {e}")
    
    def analyze_alt(self, fighter_name, model_paths, etc_paths, 
                analyze_numatb=True, analyze_nuanmb=False, analyze_numdlb=True,
                convert_to_json=None, convert_to_txt=None, 
                aggressive_mode=False, ultra_aggressive_mode=False):
        """
        Analiza archivos de un alt específico para encontrar referencias a texturas
        
        Args:
            fighter_name: Nombre del luchador (por ejemplo, "wolf")
            model_paths: Lista de rutas a archivos de modelo y material 
            etc_paths: Lista de rutas a otros archivos (animación, etc.)
            analyze_numatb: Si es True, analiza archivos de material (.numatb)
            analyze_nuanmb: Si es True, analiza archivos de animación (.nuanmb) - NO USADO
            analyze_numdlb: Si es True, analiza archivos de modelo (.numdlb)
            convert_to_json: Si se proporciona una ruta, convierte los resultados a JSON
            convert_to_txt: Si se proporciona una ruta, convierte los resultados a texto plano
            aggressive_mode: Si es True, usa reglas más agresivas para marcar texturas como no utilizadas
            ultra_aggressive_mode: Si es True, usa reglas extremadamente agresivas
            
        Returns:
            Tuple con dos listas: (referencias_texturas, archivos_textura_encontrados)
        """
        print(f"Analizando archivos para {fighter_name}...")
        
        # Si estamos en modo ultra agresivo, activar también el modo agresivo
        if ultra_aggressive_mode:
            aggressive_mode = True
        
        # Crear directorio temporal para los archivos procesados si es necesario
        temp_dir = None
        if convert_to_json or convert_to_txt:
            temp_dir = self.create_temp_dir()
        
        # Nombres de archivos de material principales a priorizar
        core_material_files = ["dark_model.numatb", "light_model.numatb", "model.numatb", "metamon_model.numatb"]
        
        # Lista de patrones para archivos que siempre se deben mantener
        always_keep_patterns = [
            "_eye_",            # Texturas de ojos
            "_eye.",            # Texturas de ojos
            "eye_",             # Texturas de ojos
            "expression",       # Expresiones faciales
        ]
        
        # Si no estamos en modo ultra agresivo, añadir más patrones a conservar
        if not ultra_aggressive_mode:
            always_keep_patterns.extend([
                "_brow_",           # Cejas
                "_face_",           # Caras
                "_head_",           # Cabeza
                "common/",          # Archivos comunes
                "ui/",              # Archivos de interfaz
                "preview_",         # Vistas previas
                "thumb_",           # Miniaturas
                "_icon_",           # Íconos
                "_stock_",          # Íconos de stock
            ])
        
        # Patrones adicionales para modo conservador (no agresivo)
        if not aggressive_mode:
            always_keep_patterns.extend([
                "_wp.",             # Armas
                "_weapon",          # Armas
                "light",            # Efectos de luz
                "aura",             # Auras
                "glow",             # Brillos
                "fire",             # Fuego
                "effect"            # Efectos
            ])
        
        # Lista de nombres base específicos que se deben tratar como no utilizados en modo agresivo
        potentially_unused_bases = set([
            "belt",             # Cinturones
            "bust",             # Bustos
            "pants",            # Pantalones
            "boots",            # Botas
            "necklace",         # Collares
            "jewelry",          # Joyería
            "cloth",            # Telas
            "skirt",            # Faldas
            "chain",            # Cadenas
            "accessory",        # Accesorios
            "scarf",            # Bufandas
            "emblem",           # Emblemas
            "badge",            # Insignias
            "armor",            # Armadura
            "metal",            # Metal
            "fur",              # Pelaje
            "cape",             # Capas
            "coat",             # Abrigos
            "hair",             # Pelo (en modo ultra agresivo)
            "hand",             # Manos (en modo ultra agresivo)
            "arm",              # Brazos (en modo ultra agresivo)
            "leg",              # Piernas (en modo ultra agresivo)
            "foot",             # Pies (en modo ultra agresivo)
            "body",             # Cuerpo (en modo ultra agresivo)
        ])

        # Separar los archivos por tipo
        material_files = []
        model_files = []
        
        for path in model_paths:
            if path.endswith('.numatb') and analyze_numatb:
                material_files.append(path)
            elif path.endswith('.numdlb') and analyze_numdlb:
                model_files.append(path)
        
        print(f"Encontrados {len(material_files)} archivos de material y {len(model_files)} modelos")
        
        # Crear un diccionario para acceder a los archivos por nombre
        material_files_by_name = {}
        for material_file in material_files:
            base_name = os.path.basename(material_file)
            material_files_by_name[base_name] = material_file
        
        # Encontrar todas las texturas disponibles
        all_textures = []
        fighter_dir = os.path.join(self.mod_directory, f"fighter/{fighter_name}")
        
        # Buscar en directorios de modelo para texturas
        for root, _, files in os.walk(os.path.join(fighter_dir, "model")):
            for file in files:
                if file.endswith(".nutexb"):
                    # Guardar la ruta relativa al mod_directory
                    rel_path = os.path.relpath(os.path.join(root, file), self.mod_directory)
                    all_textures.append(rel_path)
        
        print(f"Encontradas {len(all_textures)} texturas en total")
        
        # Extraer referencias a texturas de los archivos .numatb
        used_textures = set()
        all_texture_refs = []
        
        # Diccionario para rastrear texturas por nombre base (sin sufijos ni extensiones)
        base_name_to_textures = {}
        
        # Organizar las texturas por nombre base para facilitar la búsqueda de variantes
        for texture in all_textures:
            file_name = os.path.basename(texture)
            file_base, _ = os.path.splitext(file_name)
            
            # Eliminar sufijos comunes para obtener el nombre base más puro
            base_name = file_base
            for suffix in ['_col', '_nor', '_prm', '_emi', '_gao', '_inca', '_mask']:
                if base_name.lower().endswith(suffix):
                    base_name = base_name[:-len(suffix)]
                    break
            
            if base_name not in base_name_to_textures:
                base_name_to_textures[base_name] = []
            base_name_to_textures[base_name].append(texture)
        
        # Llevar conteo de las referencias encontradas por cada archivo principal
        core_file_refs = {file: 0 for file in core_material_files}
        
        # Asegurarse de procesar primero los archivos core para aumentar sus prioridades
        prioritized_material_files = []
        for core_file in core_material_files:
            if core_file in material_files_by_name:
                print(f"✓ Archivo principal encontrado: {core_file}")
                prioritized_material_files.append(material_files_by_name[core_file])
            else:
                print(f"✗ Archivo principal NO encontrado: {core_file}")
        
        # Agregar el resto de archivos de material
        for material_file in material_files:
            if material_file not in prioritized_material_files:
                prioritized_material_files.append(material_file)
        
        # Primero, convertir todos los archivos .numatb a JSON para un análisis más preciso
        json_files = []
        output_dir = convert_to_json if convert_to_json else temp_dir
        
        for material_file in prioritized_material_files:
            if output_dir:
                json_path = convert_numatb_to_json(material_file, output_dir)
                if json_path:
                    json_files.append((material_file, json_path))
        
        # Conteo de referencias a cada textura para detectar las que son realmente críticas
        texture_reference_count = {}
        
        # Conjunto para almacenar texturas directamente utilizadas por model.numatb
        model_direct_textures = set()
        
        # Ahora, analizar los archivos JSON para encontrar referencias a texturas
        for original_file, json_file in json_files:
            file_name = os.path.basename(original_file)
            print(f"Analizando archivo de material: {file_name}")
            
            is_core_file = file_name in core_material_files
            is_model_file = file_name == "model.numatb"  # Marcar específicamente model.numatb
            file_refs_count = 0
            
            try:
                with open(json_file, 'r') as f:
                    materials = json.load(f)
                
                print(f"  - Usando conversión JSON para análisis de precisión")
                for material in materials:
                    material_label = material["material_label"]
                    for texture in material["textures"]:
                        param_id = texture["param_id"]
                        texture_path = texture["texture_path"]
                        
                        # Crear objeto TextureReference
                        texture_ref = TextureReference(
                            texture_path=texture_path,
                            parameter_name=param_id,
                            material_label=material_label,
                            file_path=original_file
                        )
                        all_texture_refs.append(texture_ref)
                        
                        # Convertir la ruta de textura en una ruta relativa completa
                        resolved_path = self._resolve_texture_path(texture_path, os.path.dirname(original_file), 
                                                                 os.path.join(self.mod_directory, f"fighter/{fighter_name}"), 
                                                                 all_textures)
                        if resolved_path:
                            print(f"  - Textura en uso: {resolved_path} (ParamId.{param_id})")
                            file_refs_count += 1
                            
                            # Incrementar contador de referencias
                            if resolved_path not in texture_reference_count:
                                texture_reference_count[resolved_path] = 0
                            texture_reference_count[resolved_path] += 1
                            
                            # Si la textura es referenciada por model.numatb, la agregamos al conjunto especial
                            if is_model_file:
                                model_direct_textures.add(resolved_path)
                                print(f"  - Textura referenciada directamente por model.numatb: {resolved_path}")
                            
                            # Añadir a texturas usadas
                            used_textures.add(resolved_path)
                
                # Actualizar conteo para archivos core
                if is_core_file:
                    core_file_refs[file_name] = file_refs_count
                
            except Exception as e:
                print(f"Error al analizar JSON {json_file}: {e}")
                
                # Método alternativo usando análisis binario básico
                try:
                    parser = MatlParser(original_file)
                    texture_refs = parser.parse()
                    
                    print(f"  - Encontrados {len(texture_refs)} parámetros de textura")
                    file_refs_count = len(texture_refs)
                    
                    # Guardar todas las referencias
                    all_texture_refs.extend(texture_refs)
                    
                    for texture_ref in texture_refs:
                        # Convertir la ruta de textura en una ruta relativa completa
                        texture_path = self._resolve_texture_path(texture_ref.texture_path, os.path.dirname(original_file), None, all_textures)
                        if texture_path:
                            print(f"  - Textura en uso: {texture_path} ({texture_ref.parameter_name})")
                            
                            # Incrementar contador de referencias
                            if texture_path not in texture_reference_count:
                                texture_reference_count[texture_path] = 0
                            texture_reference_count[texture_path] += 1
                            
                            # Si la textura es referenciada por model.numatb, la agregamos al conjunto especial
                            if is_model_file:
                                model_direct_textures.add(texture_path)
                                print(f"  - Textura referenciada directamente por model.numatb: {texture_path}")
                            
                            # Añadir a texturas usadas
                            used_textures.add(texture_path)
                    
                    # Actualizar conteo para archivos core
                    if is_core_file:
                        core_file_refs[file_name] = file_refs_count
                        
                except Exception as e:
                    print(f"Error al analizar {original_file}: {e}")
        
        # Si se ha solicitado analizar archivos de modelo, hacerlo para extraer referencias a materiales
        if analyze_numdlb and model_files:
            print(f"\nAnalizando {len(model_files)} archivos de modelo (.numdlb)...")
            
            for model_file in model_files:
                print(f"Analizando modelo: {os.path.basename(model_file)}")
                
                # Convertir a texto si se solicita
                if convert_to_txt:
                    model_txt_path = convert_numdlb_to_text(model_file, output_dir)
                    if model_txt_path:
                        print(f"  - Modelo convertido a texto: {os.path.basename(model_txt_path)}")
                
                # Extraer información del modelo
                model_info = try_read_modl_with_ssbh(model_file)
                
                if model_info and "material_references" in model_info:
                    model_materials = model_info["material_references"]
                    print(f"  - Encontrados {len(model_materials)} materiales referenciados en el modelo")
                    
                    # Buscar texturas asociadas a estos materiales
                    for material_label in model_materials:
                        print(f"  - Material del modelo: {material_label}")
                        
                        # Buscar este material en las referencias de textura
                        for ref in all_texture_refs:
                            if ref.material_label == material_label:
                                # Resolver ruta completa
                                resolved_path = self._resolve_texture_path(ref.texture_path, os.path.dirname(ref.file_path), 
                                                                         os.path.join(self.mod_directory, f"fighter/{fighter_name}"), 
                                                                         all_textures)
                                if resolved_path:
                                    print(f"    - Textura usada por el material del modelo: {resolved_path}")
                                    used_textures.add(resolved_path)
        
        # Mostrar resumen de referencias encontradas en archivos principales
        print("\nResumen de referencias en archivos principales:")
        for file_name, ref_count in core_file_refs.items():
            if file_name in material_files_by_name:
                print(f"  - {file_name}: {ref_count} referencias")
            else:
                print(f"  - {file_name}: archivo no encontrado")
        
        # Determinar texturas no utilizadas
        used_textures_list = list(used_textures)
        unused_textures = [t for t in all_textures if t not in used_textures]
        
        print(f"Encontradas {len(used_textures_list)} texturas usadas y {len(unused_textures)} no usadas")
        
        return used_textures_list, unused_textures
    
    def _resolve_texture_path(self, base_texture_path, material_dir, fighter_dir, all_textures):
        """
        Intenta encontrar la ruta completa de una textura basándose en el nombre base.
        Si no se encuentra una coincidencia exacta, busca patrones comunes (de manera estricta).
        """
        # Primero, normalizar separadores en la ruta
        base_texture_path = base_texture_path.replace("\\", "/")
        
        # Buscar coincidencia exacta primero (con extensión .nutexb)
        texture_name = os.path.basename(base_texture_path)
        texture_name_with_ext = texture_name + ".nutexb" if not texture_name.endswith(".nutexb") else texture_name
        
        # Lista de sufijos conocidos para variantes relacionadas
        known_suffixes = ['_col', '_nor', '_prm', '_emi', '_gao', '_inca', '_mask']
        
        # Verificar coincidencia exacta en el directorio del material
        if material_dir:
            exact_path = os.path.join(material_dir, texture_name_with_ext).replace("\\", "/")
            if exact_path in all_textures:
                return exact_path
        
        # Verificar coincidencia exacta en el directorio del luchador
        if fighter_dir:
            exact_path = os.path.join(fighter_dir, texture_name_with_ext).replace("\\", "/")
            if exact_path in all_textures:
                return exact_path
        
        # Si no hay coincidencia exacta, buscar variantes por sufijo
        base_name, ext = os.path.splitext(texture_name)
        
        # Verificar si la textura tiene un sufijo conocido o buscar variantes con sufijos conocidos
        for texture in all_textures:
            texture_basename = os.path.basename(texture)
            texture_base, texture_ext = os.path.splitext(texture_basename)
            
            # Verificar si es una variante directa (mismo nombre base + sufijo conocido)
            for suffix in known_suffixes:
                # Caso 1: La referencia no tiene sufijo, pero la textura real sí
                if texture_base == base_name + suffix:
                    return texture
                
                # Caso 2: La referencia tiene sufijo, pero estamos buscando otra variante
                for ref_suffix in known_suffixes:
                    if base_name.endswith(ref_suffix):
                        base_without_suffix = base_name[:-len(ref_suffix)]
                        if texture_base == base_without_suffix + suffix:
                            return texture
        
        # Si llegamos aquí y el directorio del material tiene subcarpetas "textures" o "tex", intentar allí
        if material_dir:
            for subdir in ["textures", "tex"]:
                subdir_path = os.path.join(material_dir, subdir)
                if os.path.exists(subdir_path):
                    for texture in all_textures:
                        if subdir_path.replace("\\", "/") in texture.replace("\\", "/"):
                            texture_basename = os.path.basename(texture)
                            texture_base, texture_ext = os.path.splitext(texture_basename)
                            
                            # Verificar coincidencia exacta o por sufijo conocido
                            if texture_base == base_name:
                                return texture
                            
                            for suffix in known_suffixes:
                                if texture_base == base_name + suffix:
                                    return texture
        
        # Como último recurso, buscar en todo el conjunto de texturas por el nombre base
        for texture in all_textures:
            texture_basename = os.path.basename(texture)
            texture_base, texture_ext = os.path.splitext(texture_basename)
            
            # Solo considerar coincidencias exactas o con sufijos conocidos
            if texture_base == base_name:
                return texture
        
        # No se pudo resolver la textura
        return None
    
    def move_unused_textures_to_junk(self, textures: List[str]) -> int:
        """
        Mueve las texturas no utilizadas a la carpeta junk
        
        Args:
            textures: Lista de rutas de texturas no utilizadas (relativas a mod_directory)
            
        Returns:
            Número de archivos movidos
        """
        moved_count = 0
        
        for texture_path in textures:
            src_path = os.path.join(self.mod_directory, texture_path)
            dst_path = os.path.join(self.junk_dir, texture_path)
            
            # Crear la estructura de directorios en junk
            dst_dir = os.path.dirname(dst_path)
            if not os.path.exists(dst_dir):
                os.makedirs(dst_dir)
                
            # Mover la textura a junk
            try:
                if os.path.exists(src_path):
                    shutil.move(src_path, dst_path)
                    moved_count += 1
            except Exception as e:
                print(f"Error al mover {src_path}: {e}")
                
        return moved_count
    
    def update_config(self, fighter_name: str, alt: str, unused_textures: List[str]) -> bool:
        """
        Actualiza el archivo config.json para eliminar las referencias a las texturas no utilizadas
        
        Args:
            fighter_name: Nombre del luchador
            alt: Slot a actualizar
            unused_textures: Lista de texturas no utilizadas
            
        Returns:
            True si se actualizó correctamente, False en caso contrario
        """
        config_path = os.path.join(self.mod_directory, "config.json")
        if not os.path.exists(config_path):
            print(f"No se encontró el archivo config.json en {self.mod_directory}")
            return False
            
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Actualizar new-dir-files para eliminar referencias a texturas no utilizadas
            if "new-dir-files" in config:
                for dir_info, files_list in config["new-dir-files"].items():
                    if f"fighter/{fighter_name}/model" in dir_info and alt in dir_info:
                        # Filtrar archivos que estén en la lista de no utilizados
                        config["new-dir-files"][dir_info] = [
                            f for f in files_list 
                            if f not in unused_textures
                        ]
            
            # Guardar configuración actualizada
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error al actualizar config.json: {e}")
            return False
    
    def optimize_textures_for_alt(self, fighter_name: str, alt: str, aggressive_mode: bool = False, ultra_aggressive_mode: bool = False, protected_patterns: List[str] = None) -> Tuple[int, int]:
        """
        Optimiza las texturas para un alt específico:
        1. Analiza qué texturas se están utilizando
        2. Mueve las texturas no utilizadas a junk
        3. Actualiza config.json
        
        Args:
            fighter_name: Nombre del luchador
            alt: Slot a optimizar
            aggressive_mode: Si es True, usa reglas más agresivas para marcar texturas como no utilizadas
            ultra_aggressive_mode: Si es True, usa reglas extremadamente agresivas para marcar texturas como no utilizadas
            protected_patterns: Lista de patrones de nombres de archivo que nunca deben ser eliminados
            
        Returns:
            Tuple con (total_texturas, texturas_eliminadas)
        """
        # Si se solicita convertir a texto, crear directorio de salida si no existe
        if self.convert_to_text:
            if not self.text_output_dir:
                self.text_output_dir = os.path.join(self.mod_directory, "texture_analysis")
                os.makedirs(self.text_output_dir, exist_ok=True)
            
            # Crear subdirectorio para este luchador/alt
            alt_text_dir = os.path.join(self.text_output_dir, f"{fighter_name}/{alt}")
            os.makedirs(alt_text_dir, exist_ok=True)
            
            # Convertir archivos NUMATB a JSON
            material_dir = os.path.join(self.mod_directory, f"fighter/{fighter_name}/model")
            material_files = []
            anim_files = []
            
            for root, _, files in os.walk(material_dir):
                if alt in os.path.basename(root):
                    for file in files:
                        if file.endswith(".numatb"):
                            material_files.append(os.path.join(root, file))
                        elif file.endswith(".nuanmb") and self.analyze_nuanmb:
                            anim_files.append(os.path.join(root, file))
            
            # Convertir archivos
            for material_file in material_files:
                json_path = convert_numatb_to_json(material_file, alt_text_dir)
                if json_path:
                    print(f"Material convertido a JSON: {os.path.basename(json_path)}")
            
            # Convertir archivos de animación a texto
            if self.analyze_nuanmb:
                for anim_file in anim_files:
                    txt_path = convert_nuanmb_to_text(anim_file, alt_text_dir)
                    if txt_path:
                        print(f"Animación convertida a texto: {os.path.basename(txt_path)}")
        
        # Analizar alt para encontrar texturas utilizadas y no utilizadas
        used_textures, unused_textures = self.analyze_alt(fighter_name, alt, aggressive_mode=aggressive_mode, ultra_aggressive_mode=ultra_aggressive_mode)
        
        # Filtrar texturas protegidas
        if protected_patterns:
            protected_textures = []
            filtered_unused = []
            
            for texture in unused_textures:
                texture_name = os.path.basename(texture)
                is_protected = False
                
                # Comprobar si coincide con algún patrón protegido
                for pattern in protected_patterns:
                    if pattern.lower() in texture_name.lower():
                        is_protected = True
                        protected_textures.append(texture)
                        used_textures.append(texture)  # Añadir a texturas utilizadas
                        break
                
                if not is_protected:
                    filtered_unused.append(texture)
            
            if protected_textures:
                print(f"Se protegieron {len(protected_textures)} texturas en {fighter_name}/{alt} según patrones especificados:")
                for texture in protected_textures:
                    print(f"  - {os.path.basename(texture)}")
            
            unused_textures = filtered_unused
        
        # Mover texturas no utilizadas a junk
        moved_count = self.move_unused_textures_to_junk(unused_textures)
        
        # Actualizar config.json
        self.update_config(fighter_name, alt, unused_textures)
        
        total = len(used_textures) + len(unused_textures)
        
        print(f"Optimización de texturas para {fighter_name}/{alt} completada:")
        print(f"- {len(used_textures)} texturas utilizadas")
        print(f"- {moved_count} texturas no utilizadas movidas a junk")
        
        return total, moved_count

def detect_fighters_and_alts(mod_directory: str) -> Dict[str, List[str]]:
    """
    Detecta automáticamente los luchadores y alts disponibles en el mod
    
    Args:
        mod_directory: Directorio raíz del mod
        
    Returns:
        Diccionario con luchadores como claves y listas de alts como valores
    """
    fighters_alts = {}
    fighter_path = os.path.join(mod_directory, "fighter")
    
    if not os.path.exists(fighter_path):
        print(f"No se encontró el directorio fighter en {mod_directory}")
        return {}
    
    # Recorrer todos los luchadores
    for fighter in os.listdir(fighter_path):
        fighter_model_path = os.path.join(fighter_path, fighter, "model")
        if not os.path.exists(fighter_model_path):
            continue
            
        alts = set()
        
        # Buscar alts en directorios de modelos
        for root, dirs, _ in os.walk(fighter_model_path):
            for dir_name in dirs:
                if re.match(r'^c\d+$', dir_name):
                    alts.add(dir_name)
        
        if alts:
            fighters_alts[fighter] = sorted(list(alts), key=lambda x: int(x.strip('c')))
    
    return fighters_alts

def optimize_mod_textures(mod_dir, aggressive_mode=False, ultra_aggressive_mode=False, debug=False, 
                          simulate=False, protected_patterns=None, restore_from_junk=False):
    """
    Analyze textures in a mod and optimize by moving unused textures to a junk folder.
    
    Args:
        mod_dir: The root directory of the mod
        aggressive_mode: If True, analyze more aggressively
        ultra_aggressive_mode: If True, be even more aggressive in marking textures as unused
        debug: If True, print verbose debug info
        simulate: If True, don't actually move any files, just simulate the process
        protected_patterns: List of filename patterns to protect (never move to junk)
        restore_from_junk: If True, restore textures from junk folder
    """
    # Check if a config file exists in the mod directory
    config_file = os.path.join(mod_dir, "texture_analyzer_config.json")
    if protected_patterns is None:
        protected_patterns = []
    
    # Load protected patterns from config file if it exists
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
                if "protected_textures" in config:
                    protected_patterns.extend(config["protected_textures"])
        except Exception as e:
            print(f"Error loading config file: {e}")
    
    # Print out the protected patterns
    if protected_patterns:
        print("Texturas protegidas por el usuario:")
        for pattern in protected_patterns:
            print(f"  - {pattern}")
    
    # Create texture analyzer object
    analyzer = TextureAnalyzer(mod_dir, debug)
    
    # If restore mode is enabled, restore textures from junk folder
    if restore_from_junk:
        junk_folder = os.path.join(mod_dir, "_junk_textures")
        if os.path.exists(junk_folder):
            print(f"Restaurando texturas desde la carpeta junk...")
            # Iterate through all textures in junk folder
            for junk_file in glob.glob(os.path.join(junk_folder, "**", "*.nutexb"), recursive=True):
                # Determine original path
                rel_path = os.path.relpath(junk_file, junk_folder)
                target_path = os.path.join(mod_dir, rel_path)
                
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Move file back to original location
                if not simulate:
                    shutil.move(junk_file, target_path)
                print(f"Restaurada: {rel_path}")
            
            # Remove empty directories in junk folder
            if not simulate:
                for root, dirs, files in os.walk(junk_folder, topdown=False):
                    for dir in dirs:
                        try:
                            os.rmdir(os.path.join(root, dir))
                        except OSError:
                            pass  # Directory not empty
                try:
                    os.rmdir(junk_folder)
                except OSError:
                    pass  # Directory not empty
            
            print("Restauración completada!")
            return
    
    # Run the analysis
    results = analyzer.analyze_mod(aggressive_mode, ultra_aggressive_mode)
    
    # Process results for each fighter/slot
    for fighter_id, slots in results.items():
        for slot_id, slot_data in slots.items():
            print(f"Procesando {fighter_id}/{slot_id}...")
            
            if len(slot_data["unused_textures"]) == 0:
                print(f"Todos los archivos de textura en {fighter_id}/{slot_id} están en uso.")
                continue
            
            # Filter out textures matching protected patterns
            filtered_unused = []
            for tex in slot_data["unused_textures"]:
                # Check if texture matches any protected pattern
                is_protected = False
                for pattern in protected_patterns:
                    if pattern.lower() in os.path.basename(tex).lower():
                        print(f"  - Textura protegida (patrón usuario): {tex}")
                        is_protected = True
                        break
                
                if not is_protected:
                    filtered_unused.append(tex)
            
            junk_folder = os.path.join(mod_dir, "_junk_textures")
            
            if len(filtered_unused) > 0:
                print(f"Se moverían {len(filtered_unused)} texturas no utilizadas en {fighter_id}/{slot_id}:")
                for tex in filtered_unused:
                    print(f"  - {tex}")
                    
                    if not simulate:
                        # Create target directory
                        tex_path = os.path.join(mod_dir, tex)
                        target_dir = os.path.join(junk_folder, os.path.dirname(tex))
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # Move file to junk folder
                        try:
                            shutil.move(tex_path, os.path.join(junk_folder, tex))
                        except Exception as e:
                            print(f"Error moving {tex}: {e}")
            else:
                print(f"No hay texturas no utilizadas en {fighter_id}/{slot_id} (después de filtrar texturas protegidas).")
    
    # Update config file with the results
    try:
        config = {"protected_textures": protected_patterns}
        if not simulate:
            with open(config_file, "w") as f:
                json.dump(config, f, indent=2)
            print(f"Archivo de configuración actualizado: {config_file}")
    except Exception as e:
        print(f"Error saving config file: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Texture Analyzer for Smash Ultimate Mods")
    parser.add_argument("mod_directory", help="Path to the mod directory")
    parser.add_argument("--aggressive", action="store_true", help="Use aggressive analysis mode")
    parser.add_argument("--ultra-aggressive", action="store_true", help="Use ultra aggressive analysis mode")
    parser.add_argument("--debug", action="store_true", help="Print verbose debug information")
    parser.add_argument("--simulate", action="store_true", help="Simulate the optimization without moving files")
    parser.add_argument("--generate-config", action="store_true", help="Generate a sample config file")
    parser.add_argument("--protect", nargs="+", help="List of textures to protect (e.g. --protect belt bust pants)")
    parser.add_argument("--restore", action="store_true", help="Restore textures from junk folder")
    
    args = parser.parse_args()
    
    if args.generate_config:
        config_file = os.path.join(args.mod_directory, "texture_analyzer_config.json")
        sample_config = {
            "protected_textures": [
                "belt",
                "bust",
                "pants",
                "hair",
                "body"
            ]
        }
        with open(config_file, "w") as f:
            json.dump(sample_config, f, indent=2)
        print(f"Archivo de configuración de ejemplo generado en: {config_file}")
        print("Edite este archivo para especificar qué texturas desea proteger.")
        sys.exit(0)
    
    protected_patterns = args.protect if args.protect else []
    
    optimize_mod_textures(
        args.mod_directory, 
        aggressive_mode=args.aggressive or args.ultra_aggressive,
        ultra_aggressive_mode=args.ultra_aggressive,
        debug=args.debug,
        simulate=args.simulate,
        protected_patterns=protected_patterns,
        restore_from_junk=args.restore
    ) 