import json
import os
from typing import Dict, List, Any
from PyQt6.QtGui import QIcon
from simulation_engine import *  # Importa tus clases: DirectionalValve_4_2, etc.

COMPONENTS_DIR = os.path.join(os.path.dirname(__file__), "components")

class ComponentRegistry:
    def __init__(self):
        self.components: Dict[str, Dict[str, Any]] = {}  # id -> metadata
        self.load_all()

    def load_all(self):
        """Carga recursivamente todos los .json en components/"""
        for root, _, files in os.walk(COMPONENTS_DIR):
            for file in files:
                if file.endswith(".json"):
                    path = os.path.join(root, file)
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        comp_id = data.get("id", f"{data['family']}_{file[:-5]}")
                        self.components[comp_id] = data

    def get_metadata(self, comp_id: str) -> Dict:
        return self.components.get(comp_id, {})

    def create_instance(self, comp_id: str, name: str = None, **kwargs):
        """Crea componente lógico + gráfico a partir de ID"""
        meta = self.get_metadata(comp_id)
        if not meta:
            raise ValueError(f"Componente no encontrado: {comp_id}")

        logic_class_name = meta["logic_class"]
        logic_cls = globals().get(logic_class_name)
        if not logic_cls:
            raise ImportError(f"Clase lógica no encontrada: {logic_class_name}")

        # Crea instancia lógica
        logic = logic_cls(name or meta["name"], **kwargs)

        # Aplica parámetros default/variantes
        params = meta.get("default_parameters", {})
        for k, v in params.items():
            if hasattr(logic, k):
                setattr(logic, k, v)

        # Para GUI: instancia gráfica (similar a lo que ya tienes en add_component)
        graphic_class_name = meta.get("graphic_class")
        graphic_cls = globals().get(graphic_class_name)  # O importa dinámicamente
        graphic = graphic_cls(logic) if graphic_cls else None

        return logic, graphic, meta

    def get_toolbar_actions(self):
        """Genera acciones para la toolbar de la GUI"""
        actions = []
        for comp_id, meta in self.components.items():
            act = QAction(meta["name"])
            if "icon" in meta:
                act.setIcon(QIcon(os.path.join(COMPONENTS_DIR, meta["icon"])))
            act.setData(comp_id)  # Para saber cuál crear al click
            actions.append(act)
        return actions