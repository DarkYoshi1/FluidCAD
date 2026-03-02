import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import time
import threading

# Importa tu motor de simulación (ajusta el nombre si es diferente)
# from simulation_engine import Simulator, DirectionalValve_4_2, DoubleActingCylinder, Component

ctk.set_appearance_mode("System")  # "Light", "Dark" o "System"
ctk.set_default_color_theme("blue")  # "blue", "dark-blue", "green"


class FluidCADApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FluidCAD - Simulador GPL Neumático / Hidráulico")
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Simulador (descomenta cuando tengas simulation_engine.py listo)
        # self.sim = Simulator(dt=0.02)
        self.sim = None  # Placeholder por ahora
        self.is_running = False
        self.simulation_thread = None

        self._create_widgets()
        self._add_example_components()  # Para pruebas iniciales

    def _create_widgets(self):
        # Layout principal: sidebar izquierda + canvas central + panel derecho (propiedades)
        self.grid_columnconfigure(0, weight=0)   # sidebar
        self.grid_columnconfigure(1, weight=1)   # canvas
        self.grid_columnconfigure(2, weight=0)   # panel derecho
        self.grid_rowconfigure(0, weight=1)

        # ── Sidebar (paleta de componentes) ──
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="Componentes", font=("Segoe UI", 18, "bold")).pack(pady=20)

        components = [
            ("Válvula 4/2", self.add_valve),
            ("Cilindro doble efecto", self.add_cylinder),
            ("Solenoide", self.add_solenoid),  # placeholder
            ("Sensor fin carrera", self.add_sensor),
        ]

        for text, cmd in components:
            btn = ctk.CTkButton(self.sidebar, text=text, command=cmd, width=180)
            btn.pack(pady=8, padx=20)

        # Botones de control
        ctk.CTkButton(self.sidebar, text="Iniciar Simulación", command=self.toggle_simulation,
                      fg_color="green", hover_color="darkgreen").pack(pady=20, padx=20)
        ctk.CTkButton(self.sidebar, text="Detener", command=self.stop_simulation,
                      fg_color="red", hover_color="darkred").pack(pady=5, padx=20)

        # ── Canvas central (área de dibujo del circuito) ──
        self.canvas_frame = ctk.CTkFrame(self)
        self.canvas_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg="#f0f0f0", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Scrollbars
        vsb = ctk.CTkScrollbar(self.canvas_frame, orientation="vertical", command=self.canvas.yview)
        vsb.pack(side="right", fill="y")
        hsb = ctk.CTkScrollbar(self.canvas_frame, orientation="horizontal", command=self.canvas.xview)
        hsb.pack(side="bottom", fill="x")
        self.canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # Bind mouse wheel para zoom/pan futuro
        self.canvas.bind("<MouseWheel>", self._zoom)
        self.canvas.bind("<Button-2>", self._start_pan)
        self.canvas.bind("<B2-Motion>", self._pan)

        # ── Panel derecho (propiedades / info)
        self.props_panel = ctk.CTkFrame(self, width=250)
        self.props_panel.grid(row=0, column=2, sticky="nsew")
        ctk.CTkLabel(self.props_panel, text="Propiedades", font=("Segoe UI", 16, "bold")).pack(pady=15)

        self.props_text = ctk.CTkTextbox(self.props_panel, height=400)
        self.props_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.props_text.insert("end", "Selecciona un componente para ver/editar propiedades...\n")

    def _add_example_components(self):
        # Dibujo de prueba en canvas (luego se reemplazará con objetos arrastrables)
        self.canvas.create_rectangle(150, 150, 250, 250, fill="#4da6ff", tags="valve")
        self.canvas.create_text(200, 200, text="Válvula 4/2", fill="white")
        self.canvas.create_oval(300, 180, 400, 220, fill="#ff9999", tags="cylinder")
        self.canvas.create_text(350, 200, text="Cilindro", fill="black")
        # Línea de conexión de ejemplo
        self.canvas.create_line(250, 200, 300, 200, arrow=tk.LAST, width=3, fill="blue")

    def add_valve(self):
        # Placeholder: en futuro creará instancia lógica + objeto gráfico arrastrable
        messagebox.showinfo("Añadido", "Válvula 4/2 añadida (implementar drag & drop)")
        # Ejemplo futuro: self.sim.add_component(DirectionalValve_4_2(...))

    def add_cylinder(self):
        messagebox.showinfo("Añadido", "Cilindro doble efecto añadido")

    def add_solenoid(self):
        pass  # Implementar

    def add_sensor(self):
        pass

    def toggle_simulation(self):
        if self.is_running:
            self.stop_simulation()
        else:
            self.is_running = True
            self.simulation_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self.simulation_thread.start()
            messagebox.showinfo("Simulación", "Simulación iniciada (dt=20ms)")

    def stop_simulation(self):
        self.is_running = False
        if self.simulation_thread:
            self.simulation_thread.join(timeout=1.0)

    def _simulation_loop(self):
        while self.is_running:
            if self.sim:
                self.sim.simulate_step()
                # Actualizar visuales en canvas (en thread seguro)
                self.after(0, self._update_canvas_visuals)
            time.sleep(0.02)  # 50 Hz

    def _update_canvas_visuals(self):
        # Aquí actualizar colores, posiciones de pistones, etc. según estado del sim
        self.props_text.delete("1.0", "end")
        self.props_text.insert("end", f"t = {time.time():.2f} s\nEstado simulación...\n")
        # Ejemplo: self.canvas.itemconfig("cylinder", fill="green" if condicion else "red")

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


if __name__ == "__main__":
    app = FluidCADApp()
    app.mainloop()