import numpy as np
import networkx as nx
from typing import Dict, Any, Optional, Tuple

# Constantes físicas aproximadas (valores típicos para simulación educativa)
ATM_PRESSURE = 1.01325          # bar
DEFAULT_AREA = 5.0              # cm² (área pistón simplificada)
DEFAULT_MASS = 2.0              # kg (masa efectiva del émbolo + carga)
FRICTION_COEFF = 0.05           # coeficiente de fricción viscosa simplificado
GRAVITY = 9.81                  # m/s² (si hay carga vertical)

class Port:
    """Representa un puerto de conexión en un componente (entrada o salida)."""
    def __init__(self, name: str, type: str = "fluid", direction: str = "in"):
        self.name = name
        self.type = type          # "fluid", "electric", "logic", etc.
        self.direction = direction  # "in" o "out"
        # Para futura GUI: coordenadas relativas dentro del símbolo del componente
        self.rel_pos: Tuple[float, float] = (0.0, 0.0)  # (x, y) en % del bounding box


class Component:
    """
    Clase base para todos los componentes del sistema (neumáticos, hidráulicos, eléctricos).
    Preparada para futura integración gráfica.
    """
    def __init__(self, name: str, x: float = 0.0, y: float = 0.0):
        self.name = name
        self.position = (x, y)              # Coordenadas en el lienzo (para GUI futura)
        self.inputs: Dict[str, Any] = {}    # Valores recibidos en cada puerto de entrada
        self.outputs: Dict[str, Any] = {}   # Valores que este componente entrega
        self.state: Dict[str, Any] = {}     # Estado interno persistente
        self.ports: Dict[str, Port] = {}    # Todos los puertos (in + out)

    def define_port(self, name: str, type: str = "fluid", direction: str = "in",
                    rel_x: float = 0.0, rel_y: float = 0.0):
        """Define un puerto y su posición relativa para dibujo futuro."""
        port = Port(name, type, direction)
        port.rel_pos = (rel_x, rel_y)
        self.ports[name] = port
        if direction == "in":
            self.inputs[name] = 0.0 if type == "fluid" else False
        else:
            self.outputs[name] = 0.0 if type == "fluid" else False

    def get_visual_state(self) -> Dict[str, Any]:
        """Devuelve información clave para dibujar/animar el componente."""
        return {
            "name": self.name,
            "position": self.position,
            "state": self.state.copy(),
            "inputs": self.inputs.copy(),
            "outputs": self.outputs.copy()
        }

    def update(self, dt: float):
        """Método que deben implementar las subclases."""
        raise NotImplementedError


class DirectionalValve_4_2(Component):
    """
    Válvula direccional 4/2 accionada por solenoide (típica en electroneumática).
    Posiciones: reposo (cerrada) y activada.
    """
    def __init__(self, name: str, x: float = 0.0, y: float = 0.0):
        super().__init__(name, x, y)
        # Definimos puertos con posiciones relativas aproximadas para dibujo
        self.define_port("P", "fluid", "in",   0.0, 0.5)     # Presión
        self.define_port("T", "fluid", "out",  1.0, 0.5)     # Tanque
        self.define_port("A", "fluid", "out",  0.3, 0.2)
        self.define_port("B", "fluid", "out",  0.7, 0.2)
        self.define_port("sol1", "electric", "in",  0.1, 0.9)  # Solenoide 1
        self.define_port("sol2", "electric", "in",  0.9, 0.9)  # Solenoide 2 (opcional)

        self.state["position"] = "neutral"   # "neutral", "A+", "B+"

    def update(self, dt: float):
        sol1 = self.inputs.get("sol1", False)
        sol2 = self.inputs.get("sol2", False)

        if sol1 and not sol2:
            self.state["position"] = "A+"
            # P → A, B → T
            self.outputs["A"] = self.inputs.get("P", 0.0) * 0.95
            self.outputs["B"] = 0.0
            self.outputs["T"] = self.inputs.get("B", 0.0) + self.inputs.get("A", 0.0) * 0.05
        elif sol2 and not sol1:
            self.state["position"] = "B+"
            # P → B, A → T
            self.outputs["B"] = self.inputs.get("P", 0.0) * 0.95
            self.outputs["A"] = 0.0
            self.outputs["T"] = self.inputs.get("A", 0.0) + self.inputs.get("B", 0.0) * 0.05
        else:
            self.state["position"] = "neutral"
            # Todo cerrado o centro cerrado (según modelo)
            self.outputs["A"] = 0.0
            self.outputs["B"] = 0.0
            self.outputs["T"] = 0.0


class DoubleActingCylinder(Component):
    """Cilindro de doble efecto con modelo físico más realista."""
    def __init__(self, name: str, stroke: float = 200.0, x: float = 0.0, y: float = 0.0):
        super().__init__(name, x, y)
        self.define_port("A", "fluid", "in",  0.0, 0.3)
        self.define_port("B", "fluid", "in",  1.0, 0.3)

        self.stroke = stroke            # mm
        self.area_a = DEFAULT_AREA      # cm² lado A
        self.area_b = DEFAULT_AREA * 0.9  # Lado B (menor por vástago)
        self.state["position"] = 0.0    # mm (0 = retraído, stroke = extendido)
        self.state["velocity"] = 0.0    # mm/s

    def update(self, dt: float):
        p_a = self.inputs.get("A", ATM_PRESSURE)
        p_b = self.inputs.get("B", ATM_PRESSURE)

        # Fuerza neta (en N) → convertimos áreas a m²
        f_a = (p_a - ATM_PRESSURE) * self.area_a * 1e4  # bar → Pa * cm² → N
        f_b = (p_b - ATM_PRESSURE) * self.area_b * 1e4
        force_net = f_a - f_b

        # Aceleración (m/s²)
        accel = force_net / DEFAULT_MASS - FRICTION_COEFF * self.state["velocity"]

        # Integración Euler simple
        self.state["velocity"] += accel * dt * 1000  # a mm/s
        self.state["position"] += self.state["velocity"] * dt

        # Límites físicos
        if self.state["position"] < 0:
            self.state["position"] = 0
            self.state["velocity"] = max(0, self.state["velocity"])
        if self.state["position"] > self.stroke:
            self.state["position"] = self.stroke
            self.state["velocity"] = min(0, self.state["velocity"])


class Simulator:
    """Motor principal de simulación temporal discreta."""
    def __init__(self, dt: float = 0.005):
        self.graph = nx.DiGraph()
        self.components: Dict[str, Component] = {}
        self.dt = dt                  # Paso de tiempo en segundos (5 ms recomendado)
        self.time = 0.0

    def add_component(self, comp: Component):
        self.components[comp.name] = comp
        self.graph.add_node(comp.name)

    def connect(self, from_comp: str, from_port: str,
                to_comp: str, to_port: str):
        """Conecta la salida de un componente con la entrada de otro."""
        if from_comp not in self.components or to_comp not in self.components:
            raise ValueError("Componente no existe")
        if from_port not in self.components[from_comp].outputs:
            raise ValueError(f"Puerto {from_port} no es salida en {from_comp}")
        if to_port not in self.components[to_comp].inputs:
            raise ValueError(f"Puerto {to_port} no es entrada en {to_comp}")

        self.graph.add_edge(
            from_comp, to_comp,
            from_port=from_port,
            to_port=to_port
        )

    def simulate_step(self):
        """Propaga señales y actualiza todos los componentes en orden topológico."""
        try:
            for node in nx.topological_sort(self.graph):
                comp = self.components[node]

                # Limpiar entradas antiguas (evitar valores residuales)
                for port in comp.inputs:
                    comp.inputs[port] = 0.0 if comp.ports[port].type == "fluid" else False

                # Transferir valores desde predecesores
                for pred in list(self.graph.predecessors(node)):
                    edge = self.graph.get_edge_data(pred, node)
                    value = self.components[pred].outputs[edge["from_port"]]
                    comp.inputs[edge["to_port"]] = value

                # Actualizar componente
                comp.update(self.dt)

            self.time += self.dt

        except nx.NetworkXUnfeasible:
            print("¡Error! Hay un ciclo en el grafo de conexiones.")

    def run(self, duration: float, print_interval: float = 0.2):
        steps = int(duration / self.dt)
        last_print = 0.0

        for i in range(steps):
            self.simulate_step()

            # Impresión de progreso opcional
            if self.time - last_print >= print_interval:
                print(f"t = {self.time:.2f} s")
                last_print = self.time

        print(f"Simulación finalizada → t = {self.time:.3f} s")


# ────────────────────────────────────────────────────────────────
# Ejemplo de uso: circuito electroneumático básico
# ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sim = Simulator(dt=0.005)

    # Componentes con posiciones aproximadas (para futura GUI)
    valve = DirectionalValve_4_2("Válvula1", x=200, y=150)
    cylinder = DoubleActingCylinder("Cilindro1", stroke=300, x=450, y=150)

    sim.add_component(valve)
    sim.add_component(cylinder)

    # Conexiones
    sim.connect("Válvula1", "A", "Cilindro1", "A")
    sim.connect("Válvula1", "B", "Cilindro1", "B")

    # Condiciones iniciales
    valve.inputs["P"] = 6.0          # 6 bar
    valve.inputs["T"] = 0.0
    valve.inputs["sol1"] = True      # Activar solenoide → extensión

    # Simular 3 segundos
    sim.run(duration=3.0, print_interval=0.5)

    # Resultado final
    print("\nEstado final:")
    print(cylinder.get_visual_state())