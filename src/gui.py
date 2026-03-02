import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
import threading

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class FluidCADApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FluidCAD - Simulador GPL Neumático / Hidráulico")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.sim = None  # Placeholder para simulation_engine
        self.is_running = False
        self.simulation_thread = None

        # Almacenamiento
        self.components = {}          # item_id → {'rect': id, 'text': id, 'ports': [id1, id2,...], 'logic': None}
        self.connections = []         # lista de {'line': id, 'from_port': port_id, 'to_port': port_id}
        self.connection_mode = False  # True cuando estamos conectando
        self.temp_line = None         # línea temporal que sigue mouse
        self.start_port = None        # puerto de inicio de conexión

        self._create_widgets()
        self._bind_canvas_events()

    def _create_widgets(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Componentes", font=("Segoe UI", 18, "bold")).pack(pady=20)

        components = [
            ("Válvula 4/2", self.add_valve),
            ("Cilindro doble efecto", self.add_cylinder),
            # ("Solenoide", self.add_solenoid),
            # ("Sensor fin carrera", self.add_sensor),
        ]

        for text, cmd in components:
            btn = ctk.CTkButton(self.sidebar, text=text, command=cmd, width=180)
            btn.pack(pady=8, padx=20)

        ctk.CTkButton(self.sidebar, text="Iniciar Simulación", command=self.toggle_simulation,
                      fg_color="green", hover_color="darkgreen").pack(pady=20, padx=20)
        ctk.CTkButton(self.sidebar, text="Detener", command=self.stop_simulation,
                      fg_color="red", hover_color="darkred").pack(pady=5, padx=20)

        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#f8f9fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        vsb = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", command=self.canvas.yview)
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        hsb.pack(side="bottom", fill="x")
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.props_panel = ctk.CTkFrame(self, width=250)
        self.props_panel.grid(row=0, column=2, sticky="nsew")
        ctk.CTkLabel(self.props_panel, text="Propiedades", font=("Segoe UI", 16, "bold")).pack(pady=15)

        self.props_text = ctk.CTkTextbox(self.props_panel, height=400)
        self.props_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.props_text.insert("end", "Selecciona un componente o conexión...\n")

    def _bind_canvas_events(self):
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<Button-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._pan)
        self.canvas.bind("<Motion>", self._update_temp_line)  # Para seguir mouse en modo conexión
        self.canvas.bind("<Button-1>", self._canvas_click)     # Manejo general de clics

    def add_valve(self):
        x, y = 200, 200
        rect = self.canvas.create_rectangle(x, y, x+120, y+80, fill="#4da6ff", tags="component")
        text = self.canvas.create_text(x+60, y+40, text="Válvula 4/2", fill="white", tags="component_text")

        ports = []
        # Puertos de ejemplo: P (entrada), A/B (salidas), sol (eléctrico)
        p = self._create_port(x+10, y+40, "fluid", "in")   # P
        a = self._create_port(x+60, y+10, "fluid", "out")  # A
        b = self._create_port(x+60, y+70, "fluid", "out")  # B
        sol = self._create_port(x+110, y+40, "electric", "in")  # Solenoide
        ports.extend([p, a, b, sol])

        comp_id = rect
        self.components[comp_id] = {
            'rect': rect,
            'text': text,
            'ports': ports,
            'logic': None,  # Placeholder
            'type': 'valve'
        }

        self._bind_component_events(comp_id)
        messagebox.showinfo("Añadido", "Válvula 4/2 añadida. Haz clic en puertos para conectar.")

    def add_cylinder(self):
        x, y = 400, 200
        oval = self.canvas.create_oval(x, y, x+140, y+60, fill="#ff9999", tags="component")
        text = self.canvas.create_text(x+70, y+30, text="Cilindro", fill="black", tags="component_text")

        ports = []
        a = self._create_port(x+10, y+30, "fluid", "in")   # A
        b = self._create_port(x+130, y+30, "fluid", "in")  # B
        ports.extend([a, b])

        comp_id = oval
        self.components[comp_id] = {
            'rect': oval,
            'text': text,
            'ports': ports,
            'logic': None,
            'type': 'cylinder'
        }

        self._bind_component_events(comp_id)
        messagebox.showinfo("Añadido", "Cilindro añadido. Haz clic en puertos para conectar.")

    def _create_port(self, x, y, port_type="fluid", direction="in"):
        color = "blue" if port_type == "fluid" else "red"
        port_id = self.canvas.create_oval(x-6, y-6, x+6, y+6, fill=color, outline="black", width=2, tags=("port", port_type))
        return port_id

    def _bind_component_events(self, comp_id):
        for tag in ["component", "component_text"]:
            self.canvas.tag_bind(comp_id, "<Button-1>", self._start_drag)
            self.canvas.tag_bind(comp_id, "<B1-Motion>", self._drag)
            self.canvas.tag_bind(comp_id, "<ButtonRelease-1>", self._end_drag)

        # Puertos: clic inicia/termina conexión
        for port_id in self.components[comp_id]['ports']:
            self.canvas.tag_bind(port_id, "<Button-1>", lambda e, p=port_id: self._port_click(p))

    def _port_click(self, port_id):
        if not self.connection_mode:
            # Iniciar conexión
            self.connection_mode = True
            self.start_port = port_id
            self.temp_line = self.canvas.create_line(0,0,0,0, fill="purple", width=2, dash=(4,2), tags="temp_line")
            messagebox.showinfo("Conexión", "Modo conexión iniciado. Haz clic en otro puerto compatible.")
        else:
            # Terminar conexión
            if port_id != self.start_port:
                # Crear línea permanente
                x1, y1, _, _ = self.canvas.coords(self.start_port)
                x2, y2, _, _ = self.canvas.coords(port_id)
                line_id = self.canvas.create_line(x1+6, y1+6, x2+6, y2+6, fill="blue", width=3, arrow=tk.LAST)
                self.connections.append({
                    'line': line_id,
                    'from_port': self.start_port,
                    'to_port': port_id
                })
                # Futuro: validar compatibilidad (fluid-fluid, electric-electric, etc.)

            # Limpiar modo conexión
            self.canvas.delete("temp_line")
            self.temp_line = None
            self.connection_mode = False
            self.start_port = None

    def _update_temp_line(self, event):
        if self.connection_mode and self.temp_line:
            x1, y1, _, _ = self.canvas.coords(self.start_port)
            self.canvas.coords(self.temp_line, x1+6, y1+6, event.x, event.y)

    def _start_drag(self, event):
        item = self.canvas.find_closest(event.x, event.y)[0]
        if "port" in self.canvas.gettags(item):
            return  # Evitar drag si clic en puerto
        self.drag_data = {"x": event.x, "y": event.y, "item": item}

    def _drag(self, event):
        if not hasattr(self, 'drag_data') or not self.drag_data:
            return
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        item = self.drag_data["item"]
        self.canvas.move(item, dx, dy)

        # Mover texto asociado si es rect/oval
        tags = self.canvas.gettags(item)
        if "component" in tags:
            for cid, data in self.components.items():
                if data['rect'] == item or data['text'] == item:
                    # Mover puertos
                    for port in data['ports']:
                        self.canvas.move(port, dx, dy)
                    # Mover texto
                    self.canvas.move(data['text'], dx, dy)
                    # Mover líneas conectadas (simple: actualizar coords después)
                    break

        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def _end_drag(self, event):
        self.drag_data = None
        # Futuro: actualizar conexiones después de mover
        
    def _zoom(self, event):
        # Zoom simple con rueda (mejorar con factor)
        factor = 1.1 if event.delta > 0 else 0.9
        self.canvas.scale("all", event.x, event.y, factor, factor)

    def _start_pan(self, event):
        self.canvas.scan_mark(event.x, event.y)

    def _pan(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_closing(self):
        self.stop_simulation()
        self.destroy()
    def _simulation_loop(self):
        while self.is_running:
            if self.sim:
                self.sim.simulate_step()
                self.after(0, self._update_canvas_visuals)
            time.sleep(0.02)

    def _update_canvas_visuals(self):
        # Placeholder: cambia color de ítems según simulación
        for item_id in self.components:
            if "valve" in self.canvas.gettags(item_id):
                self.canvas.itemconfig(item_id, fill="green" if time.time() % 2 > 1 else "#4da6ff")

if __name__ == "__main__":
    app = FluidCADApp()
    app.mainloop()