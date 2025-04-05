#!/usr/bin/env python3

import math
import mido
import threading
from tkinter import *
from tkinter import ttk
import tkinter as tk
import time
import importlib
import yaml
import os
import arpegiador
import functools
"""
Para que el programa funcione hay que instalar las librería mido y tkinter 
'pip install mido'
'pip install tk'
'pip install PyYAML'
Además para algunas funciones de mido se necesita instalar en el terminal
'pip install python-rtmidi'
esto es para las funciones mido.get_input_names() y mido.open_input()
"""

ROWS = 5
COLUMNS = 14
R_CIRCLE = 20
C_MIDI = 60
MAX_CHORD_INTERVAL = 0.5
TRIANGLE = 115
CONFIG_PATH = "config.yml"
DURATION = 1500

# Diccionario de configuración
config = {
    "size_factor": 1.0,
    "port_in": "no-midi",
    "port_out": "no-midi",
    "dark_mode": False,
}

# Lista de notas para el orden gráfico
notes_in_order = [
    "Bb",
    "Db",
    "Gb",
    "F",
    "Ab",
    "C",
    "Eb",
    "G",
    "Bb",
    "D",
    "F",
    "A",
    "C",
    "E",
    "G",
    "B",
    "A",
    "E",
    "B",
    "Gb",
    "Db",
    "Ab",
    "Eb",
    "Bb",
    "C",
    "F",
    "G",
    "D",
    "A",
    "E",
    "B",
    "Gb",
    "Ab",
    "Eb",
    "Bb",
    "F",
    "C",
    "G",
    "D",
    "A",
    "B",
    "E",
    "Gb",
    "Db",
    "Ab",
    "Eb",
    "Bb",
    "F",
]

# Diccionario de notas con sus valores MIDI correspondientes
dict_notes = {
    "C": 60,
    "Db": 61,
    "D": 62,
    "Eb": 63,
    "E": 64,
    "F": 65,
    "Gb": 66,
    "G": 67,
    "Ab": 68,
    "A": 69,
    "Bb": 70,
    "B": 71,
}

# Diccionario donde guardaremos las notas que estén activas
active_notes = {}
selected_shapes = {}
previous_notes = []
arpeggiator_mode = "up"
arpeggiator_active = False
note_times = {}
circle_ids = {}
last_chord = {}
last_velocity = 64
moving_triangle = False

stop_event = None
detect_note_thread = None
midi_in_stop_event = None
midi_in_thread = None
arpeggiator_thread = None
arpeggiator_stop_event = None
nav_thread = None
nav_stop_event = None

hold_on = False

navigation_thread_active = threading.Event()
arpeggiator_thread_active = threading.Event()

screen_window = None
dark_mode = False


# Función de ChatGPT para comprobar las dependencias
def check_dependences(dependencies):
    missing_dependencies = []
    for dependency in dependencies:
        try:
            importlib.import_module(dependency)
        except ImportError:
            missing_dependencies.append(dependency)

    if not missing_dependencies:
        message = "ok"
        return message
    else:
        message = "Missing dependencies: {}\n".format(
            ", ".join(missing_dependencies))
        message += "To install dependencies, run:\n"
        message += "pip install --user {}\n".format(
            " ".join(missing_dependencies))
        return message


# Función de ChatGPT para simular mido.open_output() para cuando no hay puerto MIDI
# La función general de ChatGPT la modificamos y separamos en dos funciones
def simulated_notes(message):
    global active_notes

    if message.type == "note_on":
        simulated_note_on(message)
    elif message.type == "note_off":
        simulated_note_off(message)

    return simulated_note_on, simulated_note_off


# Simula mensaje MIDI note_on
def simulated_note_on(message):
    global active_notes

    active_notes.append(message.note)


# Simula mensaje MIDI note_off
def simulated_note_off(message):
    global active_notes

    if message.note in active_notes:
        active_notes.remove(message.note)


# Si existe el fichero de configuración carga el puerto anteriormente seleccionado y no hace falta seleccionarlo
def load_config_port():
    global config

    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as config_file:
            config = yaml.safe_load(config_file)
            selected_port_in = config.get("port_in", "no-midi")
            # Leemos el puerto de entrada
            if selected_port_in == "no-midi":
                selected_port_in = "No hay puertos MIDI"
            # Leemos el puerto de salida
            selected_port_out = config.get("port_out", "no-midi")
            if selected_port_out == "no-midi":
                selected_port_out = "No hay puertos MIDI"
            return {"port_in": selected_port_in, "port_out": selected_port_out}

    return {"port_in": "No hay puertos MIDI", "port_out": "No hay puertos MIDI"}


# Cargamos el fichero de configuración
def load_config_file():
    global config
    # Abrimos el fichero en modo lectura en caso de que exista
    try:
        with open(CONFIG_PATH, "r") as config_file:
            config = yaml.safe_load(config_file)

    # Si no existe el fichero llamamos a save_config_file para que lo cree
    except FileNotFoundError:
        save_config_file()


# Guardamos el fichero de configuración
def save_config_file():
    with open(CONFIG_PATH, "w") as config_file:
        # dump nos sirve para convertir un diccionario a yaml
        yaml.dump(config, config_file)


# Evento de click en un circulo
def click_circle(c, circle, text, note):
    # Tocamos una nota con el ratón ya sea clicando el círculo o en el texto
    c.tag_bind(circle,
               "<Button-1>",
               lambda event, note_value=note: mark_notes(c, note))
    c.tag_bind(text,
               "<Button-1>",
               lambda event, note_value=note: mark_notes(c, note))


# Evento de soltar el clic en un círculo
def unclick_circle(window, c, circle, text, note):
    # Dejamos de tocar la nota con el ratón
    c.tag_bind(circle,
               "<ButtonRelease-1>",
               lambda event, note_value=note: unmark_notes(window, c, note))
    c.tag_bind(text,
               "<ButtonRelease-1>",
               lambda event, note_value=note: unmark_notes(window, c, note))


# Función para manejar los eventos del ratón para los círculos
def click_circle_events(window, c, circle, text, note):
    try:
        click_circle(c, circle, text, note)
        unclick_circle(window, c, circle, text, note)
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Función para manejar los eventos del ratón para los triángulos
def click_triangle_events(
    window,
    c,
    notes,
    triangle_ids,
    triangle_id,
):
    try:
        # Marca el triángulo al hacer clic con el ratón en este
        c.tag_bind(triangle_id,
                   "<Button-1>",
                   lambda event, notes_value=notes, tid=triangle_id:
                   handle_triangle_click(window, c, notes, triangle_ids))
        # Desmarca el triángulo al dejar de hacer clic
        c.tag_bind(triangle_id,
                   "<ButtonRelease-1>",
                   lambda event, notes_value=notes: handle_triangle_unclick(
                       window, c, notes, triangle_ids))
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Controlamos cuando el triángulo está clicado
def handle_triangle_click(window, canvas, notes, triangle_ids):
    global last_chord, hold_on, selected_shapes
    # Si hay un triángulo marcado y es distinto del actual desmarcamos
    if last_chord and set(notes) != set(last_chord):
        # Desmarcamos de la selección anterior
        unmark_triangles(window, canvas, last_chord, triangle_ids)
    # Ahora marcamos el triángulo actual
    mark_triangles(window, canvas, notes, triangle_ids)
    # Actualizamos last_chord con las notas del triángulo actual
    last_chord = notes


# Controlamos cuando el triángulo deja de estar clicado
def handle_triangle_unclick(window, canvas, notes, triangle_ids):
    global hold_on
    # Si no estamos en modo hold_on, desmarcamos al soltar el botón
    if not hold_on:
        unmark_triangles(window, canvas, notes, triangle_ids)


# Comprobamos las notas asociadas a los triángulos
def check_triangle_notes(painted_coords, triangle_ids):
    for coord, coord_info in painted_coords.items():
        note = coord_info["note"]  # Obtenemos la nota asociada a esa coordenada
        for triangle_id, triangle_data in triangle_ids.items():
            # Verificamos si alguna coordenada de painted_coords coincide con las coordenadas del triángulo
            if any(
                    round(coord[0], 2) == round(triangle_coord[0], 2)
                    and round(coord[1], 2) == round(triangle_coord[1], 2)
                    for triangle_coord in triangle_data["coords"]):
                # Si la nota no está ya en las notas del triángulo, la añadimos
                if note not in triangle_data["notes"]:
                    triangle_data["notes"].append(note)


# Función que añade los círculos con su nota correspondiente
def draw_circles(
    window,
    c,
    circle_coords,
    triangle_ids,
    size_factor,
):
    global circle_ids, notes_in_order
    i = 0
    # Guardamos las coordenadas donde se ha pintado una nota ya
    painted_coords = {}
    size_factor_value = float(size_factor.get())

    # Guardamos una versión visual de las notas con "♭", pero sin modificar las originales
    notes_visual = [note.replace("b", "♭") for note in notes_in_order]

    for triangle_coord in circle_coords:
        for coords in triangle_coord:
            x, y = coords
            # Redondeamos las coordenadas a dos decimales por si no son exactas
            rounded_coords = (round(x, 2), round(y, 2))
            # Vemos si las coordenadas redondeadas están o no en painted_coords
            if rounded_coords not in painted_coords:
                note = notes_in_order[i]
                note_visual = notes_visual[i]
                if dark_mode:
                    # Imprimimos el círculo
                    circle = c.create_oval(
                        x - R_CIRCLE * size_factor_value,
                        y - R_CIRCLE * size_factor_value,
                        x + R_CIRCLE * size_factor_value,
                        y + R_CIRCLE * size_factor_value,
                        fill=window.cget("bg"),
                        outline="white",
                    )
                    # Imprimimos la nota
                    text = c.create_text(x, y, text=note_visual, fill="white")
                else:
                    # Imprimimos el círculo
                    circle = c.create_oval(
                        x - R_CIRCLE * size_factor_value,
                        y - R_CIRCLE * size_factor_value,
                        x + R_CIRCLE * size_factor_value,
                        y + R_CIRCLE * size_factor_value,
                        fill="white",
                    )
                    # Imprimimos la nota
                    text = c.create_text(x, y, text=note_visual, fill="black")

                # Añadimos esta coordenada al diccionario con la nota que le corresponde
                painted_coords[rounded_coords] = {
                    "note": note,
                    "circle_id": circle,
                    "text_id": text,
                }
                circle_ids[circle] = {"coords": (x, y), "note": note}
                click_circle_events(window, c, circle, text, note)

                i += 1

    # Comprobamos las notas asociadas
    check_triangle_notes(painted_coords, triangle_ids)

    return painted_coords, circle_ids, triangle_ids


# Genera la nota que hemos clicado
def play_midi(selected_port_out):
    global active_notes, last_velocity

    if hasattr(selected_port_out, "get") and isinstance(selected_port_out,
                                                        tk.StringVar):
        selected_port_out = selected_port_out.get()

    if selected_port_out == "no-midi" or selected_port_out == "No hay puertos MIDI":
        for note in active_notes:
            simulated_notes(mido.Message("note_on", note=note))
        return

    try:
        with mido.open_output(selected_port_out) as port:
            if selected_port_out and active_notes:
                for note in active_notes:
                    msg = mido.Message('note_on',
                                       note=note,
                                       velocity=last_velocity)
                    port.send(msg)

    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Dejamos de generar la nota que habíamos generado
def stop_midi(selected_port_out, control=False):
    global active_notes

    if hasattr(selected_port_out, "get") and isinstance(selected_port_out,
                                                        tk.StringVar):
        selected_port_out = selected_port_out.get()

    if selected_port_out == "no-midi" or selected_port_out == "No hay puertos MIDI":
        for note in active_notes:
            simulated_notes(mido.Message("note_off", note=note))
        active_notes.clear()
        return

    try:
        with mido.open_output(selected_port_out) as port:
            if selected_port_out and active_notes:
                for note in active_notes:
                    if control:
                        msg = mido.Message('control_change',
                                           channel=0,
                                           control=123,
                                           value=0)
                    else:
                        msg = mido.Message('note_off', note=note)
                    port.send(msg)

        active_notes.clear()
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Marca la nota si ha sido detectada por MIDI
def mark_notes(canvas, note):
    global selected_shapes, circle_ids
    try:
        # Iterar sobre circle_ids, que es más simple que painted_coords
        for circle_id, info in circle_ids.items():
            if info["note"] == note:
                if circle_id not in selected_shapes:
                    selected_shapes[circle_id] = "circle"
                # Cambiar el color del círculo seleccionado
                canvas.itemconfig(circle_id, fill="#fcc035")

    except tk.TclError:
        pass


# Desmarca la nota cuando ya no es detectada
def unmark_notes(window, canvas, note):
    global selected_shapes, circle_ids
    try:
        for circle_id, info in circle_ids.items():
            if info["note"] == note:
                if circle_id in selected_shapes:
                    selected_shapes.pop(circle_id, None)
                # Restablece el color del círculo a blanco
                canvas.itemconfig(circle_id, fill=window.cget("bg"))

    except tk.TclError:
        pass


# Marca el triángulo si ha sido clicado con el ratón
def mark_triangles(
    window,
    canvas,
    notes,
    triangle_ids,
):
    global selected_shapes, circle_ids, last_chord
    try:
        # Iterar sobre los triángulos y verificar si coincide con las coordenadas proporcionadas
        for triangle_id, info in triangle_ids.items():
            # En caso de que exista last_chord ponemos sin color los triángulos antes de marcar los nuevos
            if set(last_chord) == set(info["notes"]):
                canvas.itemconfig(triangle_id, fill=window.cget("bg"))
            if set(notes).issubset(set(
                    info["notes"])):  # Ponemos set para que no importe el orden
                if triangle_id not in selected_shapes:
                    selected_shapes[triangle_id] = "triangle"
                    # Cambiar el color del triángulo para marcarlo como seleccionado
                    canvas.itemconfig(triangle_id, fill="#7699d4")
                for note in notes:
                    mark_notes(canvas, note)

    except tk.TclError:
        pass


# Desmarca el triángulo si deja de ser tocado
def unmark_triangles(window, canvas, notes, triangle_ids):
    global selected_shapes, last_chord, hold_on

    try:
        for triangle_id, info in triangle_ids.items():
            if set(info["notes"]).issubset(set(notes)):
                if triangle_id in selected_shapes:
                    # Cambiar el color del triángulo para marcarlo como seleccionado
                    canvas.itemconfig(triangle_id, fill="grey")
                    selected_shapes.pop(triangle_id, None)
                    last_chord = info["notes"]

                for note in notes:
                    unmark_notes(window, canvas, note)

    except tk.TclError:
        pass


# Desmarcamos tanto círculos como triángulos
def unmark_shapes(window, canvas, selected_port_out):
    global selected_shapes

    shape_ids = list(selected_shapes.keys())
    # Verificar si hay alguna forma seleccionada
    if selected_shapes:
        # Iterar sobre todos los ID de las formas seleccionadas
        for shape_id in shape_ids:
            # Cambiar el color de todas las formas seleccionadas a blanco
            canvas.itemconfig(shape_id, fill=window.cget("bg"))
            selected_shapes.pop(shape_id, None)

        # Limpiar la selección después de desmarcar todas las formas
        stop_midi(selected_port_out, control=True)
        selected_shapes.clear()
        active_notes.clear()


# Crea los triángulos
def triangles(window, c, size_factor):
    global circle_ids

    size_factor_value = float(size_factor.get())
    triangle_side = TRIANGLE * size_factor_value
    triangle_height = triangle_side * math.sqrt(3) / 2

    circle_coords = []
    triangle_ids = {}

    for row in range(ROWS):
        for col in range(COLUMNS):
            # Definimos las coordenadas x e y
            if row % 2 == 0:
                x = (col * triangle_side / 2 +
                     (1 - row % 2) * triangle_side / 2 + 100)
            else:
                x = (col * triangle_side / 2 +
                     (1 - row % 2) * triangle_side / 2 + 100 +
                     triangle_side * 0.5)
            y = row * triangle_height + 200

            # Fila par
            if row % 2 == 0:
                # Columna par
                if col % 2 == 0:
                    triangle_coords = [
                        (x, y),
                        (x + triangle_side / 2, y + triangle_height),
                        (x - triangle_side / 2, y + triangle_height),
                    ]
                # Columna impar
                else:
                    triangle_coords = [
                        (x, y + triangle_height),
                        (x - triangle_side / 2, y),
                        (x + triangle_side / 2, y),
                    ]
            # Fila impar
            else:
                # Columna par
                if col % 2 == 0:
                    triangle_coords = [
                        (x, y + triangle_height),
                        (x - triangle_side / 2, y),
                        (x + triangle_side / 2, y),
                    ]
                # Columna impar
                else:
                    triangle_coords = [
                        (x, y),
                        (x + triangle_side / 2, y + triangle_height),
                        (x - triangle_side / 2, y + triangle_height),
                    ]

            if dark_mode:
                # Dibujamos el triángulo
                triangle_id = c.create_polygon(triangle_coords,
                                               fill=window.cget("bg"),
                                               outline="white")
            else:
                triangle_id = c.create_polygon(triangle_coords,
                                               fill=window.cget("bg"),
                                               outline="black")

            # Añadimos las coordenadas a nuestra lista
            circle_coords.append(triangle_coords)
            triangle_ids[triangle_id] = {"coords": triangle_coords, "notes": []}
            notes = triangle_ids[triangle_id]["notes"]

            click_triangle_events(
                window,
                c,
                notes,
                triangle_ids,
                triangle_id,
            )

    # Mostramos los círculos con sus notas
    painted_coords, circle_ids, triangle_ids = draw_circles(
        window,
        c,
        circle_coords,
        triangle_ids,
        size_factor,
    )

    return (
        painted_coords,
        triangle_ids,
        circle_coords,
    )


# Función para ver si detectamos un acorde desde un puerto MIDI IN
def detect_chord(window, canvas, note, triangle_ids):
    current_time = time.time()

    # Si la nota aún no está en las notas activas la añadimos con su tiempo de activación
    if note not in note_times:
        note_times[note] = current_time

    chord_notes = []
    # Recorremos las notas activas para filtrar las que superaron el tiempo
    for note, activation_time in list(note_times.items()):
        if current_time - activation_time <= MAX_CHORD_INTERVAL:
            chord_notes.append(note)
        else:
            del note_times[note]

    # Si el número de notas activas es múltiplo de 3 y mayor que 0, consideramos que es un acorde
    if len(chord_notes) >= 3:
        # Pintamos los triángulos asociados al acorde
        mark_triangles(window, canvas, chord_notes, triangle_ids)
        if any(shape_type == "triangle"
               for shape_type in selected_shapes.values()):
            return True

    return False


# Convertir el MIDI a el nombre de la nota
def convert_midi_to_note(message):
    midi_note = message % 12 + C_MIDI
    note_name = None

    # Recorremos el diccionario para buscar la nota correspondiente al valor MIDI
    for note, value in dict_notes.items():
        if value == midi_note:
            note_name = note
            break

    return note_name


def get_midi_in(window, canvas, selected_port_out, selected_port_in,
                triangle_ids):
    global last_chord, last_velocity, moving_triangle

    notes = []
    chord = False
    # Si no hay un puerto MIDI in seleccionado, salimos
    if selected_port_in == "no-midi":
        print("No hay puerto MIDI in seleccionado.")
        return

    try:
        with mido.open_input(selected_port_in) as port:
            print(f"Abierto puerto MIDI in: {selected_port_in}")
            while not midi_in_stop_event.is_set():
                # Procesamos todos los mensajes pendientes
                for msg in port.iter_pending():
                    # La función hasattr nos dice si el mensaje contiene 'note'
                    if hasattr(msg, "note"):
                        note_name = convert_midi_to_note(msg.note)
                    if msg.type == "note_on":
                        if moving_triangle:
                            unmark_shapes(window, canvas, selected_port_out)
                        last_velocity = msg.velocity
                        if hold_on and chord:
                            stop_midi(selected_port_out, control=True)
                            unmark_shapes(window, canvas, selected_port_out)
                            notes = []

                        chord = detect_chord(window, canvas, note_name,
                                             triangle_ids)
                        notes.append(note_name)
                        mark_notes(canvas, note_name)

                    elif msg.type == "note_off":
                        if chord:
                            if len(set(notes)) >= 3:
                                if not hold_on:
                                    unmark_triangles(window, canvas, notes,
                                                     triangle_ids)
                                    notes = []
                                else:
                                    last_chord = notes
                                    notes = []

                        else:
                            unmark_notes(window, canvas, note_name)
                            if note_name in notes:
                                notes.remove(note_name)
                    else:
                        continue

                time.sleep(0.001)
    except OSError as e:
        print("Error al abrir el puerto MIDI in:", e)


def get_midi_out(selected_port_out, triangle_ids):
    global selected_shapes, active_notes, stop_event, circle_ids

    previous_active_notes = []
    print(f"Abierto puerto MIDI out: {selected_port_out}")
    while not stop_event.is_set():
        new_active_notes = []

        # Si no hay figuras seleccionadas, y había notas sonando, mandamos note_off
        if not selected_shapes:
            if previous_active_notes:
                stop_midi(selected_port_out, control=True)
                previous_active_notes = []
        else:
            # Si hay triángulos seleccionados, obtenemos el acorde de uno de ellos
            if any(shape_type == "triangle"
                   for shape_type in selected_shapes.values()):
                for shape_id, shape_type in selected_shapes.items():
                    if shape_type == "triangle":
                        notes = triangle_ids[shape_id]["notes"]
                        new_active_notes = arpegiador.convert_note_to_midi(
                            notes)
                        break
            else:
                # Si solo hay círculos, obtenemos la nota asociada
                for shape_id, shape_type in selected_shapes.items():
                    if shape_type == "circle":
                        note = circle_ids[shape_id]["note"]
                        new_active_notes = arpegiador.convert_note_to_midi(
                            [note])
                        break

            # Si el nuevo acorde es diferente del que ya estaba sonando
            if set(new_active_notes) != set(previous_active_notes):
                if previous_active_notes:
                    stop_midi(selected_port_out)
                active_notes = new_active_notes
                if not arpeggiator_active:
                    play_midi(selected_port_out)
                previous_active_notes = new_active_notes.copy()

        time.sleep(0.001)


# Función que se ejecuta después de DURATION
def handle_unmark_and_stop_moving(window, canvas, notes, triangle_ids):
    global moving_triangle

    unmark_triangles(window, canvas, notes, triangle_ids)
    moving_triangle = False


# Función para mover los triángulos
def move_triangles(window, canvas, triangle_ids, shapes_to_update):
    global moving_triangle

    # Movemos los triángulos seleccionados
    for old_id, new_id in shapes_to_update["triangle"].items():
        old_notes = triangle_ids[old_id]["notes"]
        new_notes = triangle_ids[new_id]["notes"]

        # Desmarcamos el triángulo actual y sus notas
        unmark_triangles(window, canvas, old_notes, triangle_ids)

        # Marcamos el nuevo triángulo y sus notas
        mark_triangles(window, canvas, new_notes, triangle_ids)

        if not hold_on:
            moving_triangle = True
            window.after(
                DURATION, lambda: handle_unmark_and_stop_moving(
                    window, canvas, new_notes, triangle_ids))


# Manejamos el movimiento en modo navegación
def handle_key(
    window,
    event,
    canvas,
    triangle_ids,
):
    global selected_shapes, last_chord

    shapes_to_update = {"triangle": {}, "circle": {}}
    selected_triangle_ids = []

    # Obtenemos todos los triángulos seleccionados
    for triangle_id, info in triangle_ids.items():
        if set(info["notes"]) == set(last_chord):
            selected_triangle_ids.append(triangle_id)

    # Manejamos los triángulos
    if last_chord:
        new_triangle_ids = []
        # Obtenemos todos los triángulos seleccionados
        for current_triangle_id in selected_triangle_ids:

            # Calcula el nuevo id basándose en la dirección de la tecla
            if event.keysym == "Left":
                # Movernos a la izquierda
                new_triangle_id = (
                    current_triangle_id -
                    1) if current_triangle_id > 1 else COLUMNS * ROWS

            elif event.keysym == "Right":
                # Movernos a la derecha
                new_triangle_id = (
                    current_triangle_id +
                    1) if current_triangle_id < COLUMNS * ROWS else 1

            elif event.keysym == "Up":
                # Movernos hacia arriba
                new_triangle_id = (current_triangle_id - COLUMNS if
                                   (current_triangle_id -
                                    COLUMNS) >= 1 else current_triangle_id +
                                   (ROWS - 1) * COLUMNS)

            elif event.keysym == "Down":
                # Movernos hacia abajo
                new_triangle_id = (current_triangle_id + COLUMNS if
                                   (current_triangle_id +
                                    COLUMNS) <= COLUMNS * ROWS else
                                   (current_triangle_id - (ROWS - 1) * COLUMNS))

            else:
                continue

            if new_triangle_id in triangle_ids and len(
                    set(last_chord)
                    & set(triangle_ids[new_triangle_id]["notes"])) >= 2:
                new_triangle_ids.append(new_triangle_id)
                # Actualizamos la estructura de shapes_to_update
                shapes_to_update["triangle"][
                    current_triangle_id] = new_triangle_id

        move_triangles(window, canvas, triangle_ids, shapes_to_update)

        # Actualizamos last_chord con las notas del último triángulo
        if new_triangle_ids:
            last_chord = triangle_ids[new_triangle_ids[-1]]["notes"]


# Controlamos los eventos de las flechas del teclado
def nav_with_arrow_keys(
    window,
    canvas,
    triangle_ids,
):
    global nav_stop_event

    window.bind("<Up>",
                lambda event: handle_key(window, event, canvas, triangle_ids))
    window.bind("<Down>",
                lambda event: handle_key(window, event, canvas, triangle_ids))
    window.bind("<Left>",
                lambda event: handle_key(window, event, canvas, triangle_ids))
    window.bind("<Right>",
                lambda event: handle_key(window, event, canvas, triangle_ids))

    while not nav_stop_event.is_set():
        time.sleep(0.001)


# Función que ejecuta el bucle del arpegiador
def arpeggiator_loop(selected_port_out, triangle_ids, tempo, compas, octave):
    global arpeggiator_mode, selected_shapes, active_notes

    next_note_time = time.perf_counter()

    while not arpeggiator_stop_event.is_set():
        # Calculamos el tiempo entre notas
        time_between_notes = arpegiador.calculate_time_between_notes(
            tempo, compas)
        # Obtenemos las notas ordenadas del arpegiador
        notes = arpegiador.get_arpeggio_notes(selected_shapes, triangle_ids,
                                              compas, octave, arpeggiator_mode)

        if not notes:
            stop_midi(selected_port_out, control=True)

        for note in notes:
            if arpeggiator_stop_event.is_set():
                break

            active_notes = [note]
            # Tocamos la nota
            play_midi(selected_port_out)

            # Controlamos de tiempo exacto para soltar la nota
            while time.perf_counter() < next_note_time:
                pass

            # Soltamos la nota
            stop_midi(selected_port_out)

            # Actualizamos el tiempo de inicio para la siguiente nota
            next_note_time += time_between_notes

        time.sleep(0.0001)


# Función para encender o apagar el arpegiador y habilitar los botones up, sown y random
def toggle_arpeggiator(
    start_arpeggiator_button,
    start_hold_button,
    window,
    canvas,
    selected_port_out,
    triangle_ids,
    tempo,
    compas,
    octave,
):
    global arpeggiator_active, arpeggiator_thread, hold_on
    arpeggiator_active = not arpeggiator_active

    up_button = window.up_button
    down_button = window.down_button
    random_button = window.random_button

    if arpeggiator_active:
        start_arpeggiator_button.config(text="Arpegiador on")
        print("Arpegiador encendido")

        start_arpeggiator_thread(selected_port_out, triangle_ids, tempo, compas,
                                 octave)

        # Habilitar los botones up, down y random
        up_button.state(["!disabled"])
        down_button.state(["!disabled"])
        random_button.state(["!disabled"])
        start_hold_button.state(["!disabled"])

        if start_hold_button.cget("text") == "Hold on":
            hold_on = True
            start_hold_button.config(text="Hold on")
        else:
            start_hold_button.config(text="Hold off")

    else:
        start_arpeggiator_button.config(text="Arpegiador off")
        print("Arpegiador apagado")
        arpeggiator_active = False
        hold_on = False

        if arpeggiator_stop_event is not None:
            arpeggiator_stop_event.set()

        # Desmarcar todas las notas al apagar el arpegiador
        stop_midi(selected_port_out, control=True)

        # Deshabilitar los botones up, down y random
        up_button.state(["disabled"])
        down_button.state(["disabled"])
        random_button.state(["disabled"])
        start_hold_button.state(["disabled"])

        window.after(DURATION,
                     lambda: unmark_shapes(window, canvas, selected_port_out))


# Función para controlar el modo hold on
def toggle_hold_mode(window, canvas, start_hold_button, selected_port_out):
    global hold_on
    hold_on = not hold_on
    if hold_on:
        start_hold_button.config(text="Hold on")
    else:
        start_hold_button.config(text="Hold off")
        # Desmarcar todas las notas al apagar el arpegiador
        stop_midi(selected_port_out, control=True)
        window.after(DURATION,
                     lambda: unmark_shapes(window, canvas, selected_port_out))


# Función para definir el estado del arpegiador
def set_arpeggiator_mode(mode):
    global arpeggiator_mode
    if arpeggiator_active:
        arpeggiator_mode = mode
        print(f"Modo del arpegiador cambiado a {mode}")


# Función que inicia el hilo de navegación
def start_nav_thread(
    window,
    canvas,
    triangle_ids,
):
    global nav_thread, nav_stop_event

    nav_stop_event = threading.Event()
    nav_thread = threading.Thread(
        target=nav_with_arrow_keys,
        args=(
            window,
            canvas,
            triangle_ids,
        ),
        daemon=True,
    )
    nav_thread.start()


# Hilo para iniciar el control de puertos MIDI in
def start_midi_in_thread(window, canvas, selected_port_out, selected_port_in,
                         triangle_ids):
    global midi_in_thread, midi_in_stop_event, circle_ids

    if isinstance(selected_port_in, tk.StringVar):
        selected_port_in = selected_port_in.get()

    if selected_port_in == "No hay puertos MIDI":
        selected_port_in = "no-midi"

    # Si ya existe un hilo, se le pide detenerse
    if midi_in_stop_event is not None:
        midi_in_stop_event.set()
    if midi_in_thread is not None:
        # Esperamos un máximo de 2 segundos a que se detenga
        midi_in_thread.join(timeout=2)

    # Se crea un nuevo evento de parada
    midi_in_stop_event = threading.Event()

    # Se inicia el nuevo hilo con el puerto actualizado
    midi_in_thread = threading.Thread(target=get_midi_in,
                                      args=(window, canvas, selected_port_out,
                                            selected_port_in, triangle_ids),
                                      daemon=True)
    midi_in_thread.start()


# Hilo de ejecución para la detección de notas de MIDI out
def start_midi_out_thread(
    selected_port_out,
    triangle_ids,
):
    global detect_note_thread, stop_event
    """Vamos a crear un hilo para que la ejecución de la detección de notas esté
    en paralelo a la ventana con la imagen Ponemos daemon=True para que se
    termine la ejecución de la función al cerrar el programa En selected_port
    vamos a poner .get() debido a que se trata de un StringVar esto va a hacer
    que se nos devuelva el valor marcado en el menu de opciones."""
    # Si tiene el método get lo obtenemos
    if isinstance(selected_port_out, tk.StringVar):
        selected_port_out = selected_port_out.get()

    # Convertimos 'No hay puertos MIDI' a 'no-midi'
    if selected_port_out == "No hay puertos MIDI":
        selected_port_out = "no-midi"

    if stop_event is not None:
        stop_event.set()
    if detect_note_thread is not None:
        detect_note_thread.join(timeout=2)

    # Se crea un nuevo evento de parada para el nuevo hilo.
    stop_event = threading.Event()

    detect_note_thread = threading.Thread(
        target=get_midi_out,
        args=(
            selected_port_out,
            triangle_ids,
        ),
        daemon=True,
    )
    detect_note_thread.start()


# Hilo para la ejecución del arpegiador
def start_arpeggiator_thread(selected_port_out, triangle_ids, tempo, compas,
                             octave):
    global arpeggiator_thread, arpeggiator_stop_event

    if isinstance(selected_port_out, tk.StringVar):
        selected_port_out = selected_port_out.get()

    # Convertimos "No hay puertos MIDI" a "no-midi"
    if selected_port_out == "No hay puertos MIDI":
        selected_port_out = "no-midi"

    # Si ya existe un hilo, se le pide detenerse
    if arpeggiator_stop_event is not None:
        arpeggiator_stop_event.set()
    if arpeggiator_thread is not None:
        arpeggiator_thread.join(timeout=2)

    # Crear un nuevo evento de parada
    arpeggiator_stop_event = threading.Event()

    # Iniciar el nuevo hilo con el tempo actualizado
    arpeggiator_thread = threading.Thread(target=arpeggiator_loop,
                                          args=(selected_port_out, triangle_ids,
                                                tempo, compas, octave),
                                          daemon=True)
    arpeggiator_thread.start()


# Actualiza en el fichero config el nuevo tamaño
def update_size_factor(size_factor):
    config["size_factor"] = size_factor
    save_config_file()


# Actualiza en el fichero config el nuevo puerto in
def update_selected_port_in(selected_port_in):
    selected_port_in = selected_port_in.get()
    # Verificamos si el puerto seleccionado es "No hay puertos MIDI" para guardar 'no-midi'
    if selected_port_in == "No hay puertos MIDI":
        config["port_in"] = "no-midi"
    else:
        # Si es un puerto MIDI válido, lo guardamos tal cual
        config["port_in"] = selected_port_in

    save_config_file()


# Actualiza en el fichero config el nuevo puerto out
def update_selected_port_out(selected_port_out):
    selected_port_out = selected_port_out.get()
    # Verificamos si el puerto seleccionado es "No hay puertos MIDI" para guardar 'no-midi'
    if selected_port_out == "No hay puertos MIDI":
        config["port_out"] = "no-midi"
    else:
        # Si es un puerto MIDI válido, lo guardamos tal cual
        config["port_out"] = selected_port_out

    save_config_file()


# Función para ajustar la posición del frame
def update_position(arpeggiator_frame, window):
    window_width = window.winfo_width()

    # Calcular la nueva posición
    x_position = window_width - 400
    y_position = 100

    # Colocar el frame
    arpeggiator_frame.place(x=x_position, y=y_position, width=380, height=350)


# Función para crear un marco que contenga los botones
def create_arpeggiator_frame(
    window,
    selected_port_out,
    triangle_ids,
):
    # Crear el frame del arpegiador
    arpeggiator_frame = tk.Frame(window,
                                 bd=2,
                                 relief=tk.RIDGE,
                                 bg=window.cget("bg"))

    # Llamar a la función de actualización de posición al crear el frame
    update_position(arpeggiator_frame, window)

    # Asignar la función de actualización a la configuración de la ventana
    window.bind("<Configure>",
                lambda event: update_position(arpeggiator_frame, window))

    if dark_mode:
        # Agregar un título al marco
        title_label = tk.Label(
            arpeggiator_frame,
            text="Arpegiador",
            font=("Arial", 12, "bold"),
            bg=window.cget("bg"),
            fg="white",
        )
    else:
        title_label = tk.Label(
            arpeggiator_frame,
            text="Arpegiador",
            font=("Arial", 12, "bold"),
            bg=window.cget("bg"),
        )

    title_label.pack(pady=5)

    start_hold_button = button_hold(
        arpeggiator_frame,
        c,
        selected_port_out,
    )

    # Crear un frame solo para los botones para organizar su disposición
    button_frame = tk.Frame(arpeggiator_frame, bg=window.cget("bg"))
    button_frame.pack(pady=5)

    # Creamos un frame para los controles de compás y tempo
    control_frame = tk.Frame(arpeggiator_frame, bg=window.cget("bg"))
    control_frame.pack(pady=5)

    # Creamos un sub-frame para agrupar el compás y tempo en la misma fila
    controls_subframe = tk.Frame(control_frame, bg=window.cget("bg"))
    controls_subframe.pack()

    compas = choose_compas(controls_subframe)
    tempo = choose_tempo(controls_subframe)

    octave = choose_octave(arpeggiator_frame)

    button_arpeggiator(
        button_frame,
        c,
        start_hold_button,
        selected_port_out,
        triangle_ids,
        tempo,
        compas,
        octave,
    )

    # Creamos los botones up, down y random
    up_button = button_arpeggiator_up(button_frame)
    down_button = button_arpeggiator_down(button_frame)
    random_button = button_arpeggiator_random(button_frame)

    # Deshabilitar inicialmente los botones
    up_button.state(["disabled"])
    down_button.state(["disabled"])
    random_button.state(["disabled"])
    start_hold_button.state(["disabled"])

    # Guardamos los botones en el marco para acceder a ellos después
    button_frame.up_button = up_button
    button_frame.down_button = down_button
    button_frame.random_button = random_button

    return compas, tempo


# Botón para activar el arpegiador de mayor a menor
def button_arpeggiator_up(window):
    up_image = tk.PhotoImage(file="imagenes/up.png")
    start_arpeggiator_button_up = ttk.Button(
        window,
        image=up_image,
        command=lambda: (set_arpeggiator_mode("up")),
    )

    # Mantiene una referencia a la imagen para evitar que se recoja por el garbage collector
    start_arpeggiator_button_up.image = up_image

    start_arpeggiator_button_up.pack(side=tk.LEFT, padx=5)

    return start_arpeggiator_button_up


# Botón para activar el arpegiador de menor a mayor
def button_arpeggiator_down(window):
    down_image = tk.PhotoImage(file="imagenes/down.png")
    start_arpeggiator_button_down = ttk.Button(
        window,
        image=down_image,
        command=lambda: (set_arpeggiator_mode("down")),
    )

    start_arpeggiator_button_down.image = down_image
    start_arpeggiator_button_down.pack(side=tk.LEFT, padx=5)

    return start_arpeggiator_button_down


# Botón para activar el arpegiador de manera aleatoria
def button_arpeggiator_random(window):
    random_image = tk.PhotoImage(file="imagenes/random.png")
    start_arpeggiator_button_random = ttk.Button(
        window,
        image=random_image,
        command=lambda: (set_arpeggiator_mode("random")),
    )

    start_arpeggiator_button_random.image = random_image
    start_arpeggiator_button_random.pack(side=tk.LEFT, padx=5)

    return start_arpeggiator_button_random


# Botón para activar el arpegiador
def button_arpeggiator(
    window,
    canvas,
    start_hold_button,
    selected_port_out,
    triangle_ids,
    tempo,
    compas,
    octave,
):
    start_arpeggiator_button = ttk.Button(
        window,
        text="Arpegiador off",
        command=lambda: (toggle_arpeggiator(
            start_arpeggiator_button, start_hold_button, window, canvas,
            selected_port_out, triangle_ids, tempo, compas, octave)),
    )

    start_arpeggiator_button.pack(side=tk.LEFT, pady=10)


# Botón para activar el hold on
def button_hold(
    window,
    canvas,
    selected_port_out,
):
    start_hold_button = ttk.Button(
        window,
        text="Hold off",
        command=lambda: (toggle_hold_mode(window, canvas, start_hold_button,
                                          selected_port_out)),
    )

    start_hold_button.pack(side=tk.TOP, pady=10)

    return start_hold_button


# Función para cerrar el Combobox al hacer clic en una opción
def close_combobox(event, window):
    window.after_idle(lambda: window.focus_set())


# Botón para aumentar el tempo
def increase_tempo(tempo):
    current_tempo = tempo.get()
    if current_tempo < 180:
        tempo.set(current_tempo + 1)


# Botón para disminuir el tempo
def decrease_tempo(tempo):
    current_tempo = tempo.get()
    if current_tempo > 20:
        tempo.set(current_tempo - 1)


# Función para validar el tempo en el Entry
def validate_tempo(tempo):
    current_tempo = tempo.get()
    if current_tempo < 20:
        tempo.set(20)
    elif current_tempo > 180:
        tempo.set(180)


# Función para elegir el tempo
def choose_tempo(window):
    tempo_frame = tk.Frame(window, bg=window.cget("bg"))
    tempo_frame.pack(side=tk.LEFT, padx=5)

    tempo = tk.IntVar(window)
    tempo.set(120)

    # Botones de incremento y decremento
    decrease_button = ttk.Button(window,
                                 text="-",
                                 command=lambda: decrease_tempo(tempo),
                                 width=2)
    decrease_button.pack(side=tk.LEFT)

    tempo_entry = ttk.Entry(window, textvariable=tempo, width=5)
    tempo_entry.pack(side=tk.LEFT)

    increase_button = ttk.Button(window,
                                 text="+",
                                 command=lambda: increase_tempo(tempo),
                                 width=2)
    increase_button.pack(side=tk.LEFT)

    tempo_entry.bind("<Return>", lambda e: validate_tempo(tempo))

    return tempo


# Función para elegir el compás
def choose_compas(window):
    compas_frame = tk.Frame(window, bg=window.cget("bg"))
    compas_frame.pack(side=tk.LEFT, padx=5)

    compases = ["2/4", "3/4", "4/4"]

    compas = tk.StringVar(window)
    # Compás por defecto
    compas.set("4/4")

    compas_menu = ttk.Combobox(
        compas_frame,
        textvariable=compas,
        values=compases,
        state="readonly",
        width=3,
    )

    compas_menu.pack(side=tk.LEFT, padx=5)

    compas_menu.bind("<<ComboboxSelected>>",
                     lambda event: close_combobox(event, window))

    return compas


# Función para elegir la octava
def choose_octave(window):
    octave_frame = tk.Frame(window, bg=window.cget("bg"))
    octave_frame.pack(side=tk.LEFT, padx=10)

    if dark_mode:
        label = tk.Label(
            octave_frame,
            text="Extensión por:",
            bg=window.cget("bg"),
            fg="white",
        )
    else:
        label = tk.Label(octave_frame,
                         text="Extensión por:",
                         bg=window.cget("bg"))

    label.pack(side=tk.LEFT)
    octaves = [1, 2, 3]

    octave = tk.IntVar(window)
    # Octava por defecto
    octave.set(1)

    octaves_menu = ttk.Combobox(
        octave_frame,
        textvariable=octave,
        values=octaves,
        state="readonly",
        width=2,
    )
    octaves_menu.pack(side=tk.LEFT, padx=5)

    if dark_mode:
        label = tk.Label(octave_frame,
                         text="octava",
                         bg=window.cget("bg"),
                         fg="white")
    else:
        label = tk.Label(octave_frame, text="octava", bg=window.cget("bg"))

    label.pack(side=tk.LEFT)

    octaves_menu.bind("<<ComboboxSelected>>",
                      lambda event: close_combobox(event, window))

    return octave


# Obtenemos el botón para la selección del puerto MIDI
def button_select_midi_in(
    canvas,
    window,
    frame,
    selected_port_out,
    selected_port_in,
    midi_ports_in,
    triangle_ids,
):
    port_menu = ttk.Combobox(
        frame,
        textvariable=selected_port_in,
        values=midi_ports_in,
        state="readonly",
    )
    port_menu.pack(padx=5, pady=5)
    # Botón para seleccionar el puerto elegido
    # Ponemos lambda para que nos permita pasar la función con el argumento
    select_midi_button = ttk.Button(
        frame,
        text="Seleccionar",
        command=lambda: (
            update_selected_port_in(selected_port_in),
            start_midi_in_thread(window, canvas, selected_port_out,
                                 selected_port_in, triangle_ids),
        ),
    )
    select_midi_button.pack(padx=5, pady=5)


# Obtenemos el botón para la selección del puerto MIDI
def button_select_midi_out(
    frame,
    selected_port_out,
    midi_ports_out,
    triangle_ids,
):
    port_menu = ttk.Combobox(
        frame,
        textvariable=selected_port_out,
        values=midi_ports_out,
        state="readonly",
    )
    port_menu.pack(padx=5, pady=5)
    # Botón para seleccionar el puerto elegido
    # Ponemos lambda para que nos permita pasar la función con el argumento
    select_midi_button = ttk.Button(
        frame,
        text="Seleccionar",
        command=lambda: (
            update_selected_port_out(selected_port_out),
            start_midi_out_thread(selected_port_out, triangle_ids),
        ),
    )
    select_midi_button.pack(padx=5, pady=5)


# Menu de selección del puerto MIDI
def midi_in_port_selection(window):
    midi_in_ports = mido.get_input_names()

    # Si no hay puertos midi mostramos la opción de que no hay puertos
    midi_in_ports = ["No hay puertos MIDI"] + midi_in_ports

    # Creamos el menu para las opciones de puertos midi
    selected_port_in = tk.StringVar(window)
    # Seleccionamos el primero por defecto
    if config["port_in"] == "no-midi":
        selected_port_in.set("No hay puertos MIDI")
    else:
        selected_port_in.set(config["port_in"])

    return selected_port_in, midi_in_ports


# Menu de selección del puerto MIDI
def midi_out_port_selection(window):
    midi_out_ports = mido.get_output_names()

    # Si no hay puertos midi mostramos la opción de que no hay puertos
    midi_out_ports = ["No hay puertos MIDI"] + midi_out_ports

    # Creamos el menu para las opciones de puertos MIDI
    selected_port_out = tk.StringVar(window)
    # Seleccionamos el primero por defecto
    if config["port_out"] == "no-midi":
        selected_port_out.set("No hay puertos MIDI")
    else:
        selected_port_out.set(config["port_out"])

    return selected_port_out, midi_out_ports


def get_midi_ports(window, selected_port_in_from_config,
                   selected_port_out_from_config):
    # Seleccionamos el puerto MIDI de entrada y salida
    selected_port_in, midi_ports_in = midi_in_port_selection(window)
    if selected_port_in_from_config:
        selected_port_in.set(selected_port_in_from_config)

    selected_port_out, midi_ports_out = midi_out_port_selection(window)
    if selected_port_out_from_config:
        selected_port_out.set(selected_port_out_from_config)

    return selected_port_in, selected_port_out, midi_ports_in, midi_ports_out


# Obtenemos el botón para seleccionar el tamaño de la ventana
def button_size_factor(
    window,
    frame,
    size_factors,
    selected_port_in,
    selected_port_out,
    midi_ports_in,
    midi_ports_out,
):
    # Mostramos el menu de tamaños
    size_factor_menu = ttk.Combobox(frame,
                                    textvariable=size_factor,
                                    values=size_factors,
                                    state="readonly")
    size_factor_menu.pack(padx=5, pady=5)

    # Botón para seleccionar el tamaño
    select_size_button = ttk.Button(
        frame,
        text="Seleccionar",
        command=lambda: (
            update_size_factor(size_factor.get()),
            create_canvas(
                window,
                size_factor,
                selected_port_in,
                selected_port_out,
                midi_ports_in,
                midi_ports_out,
            ),
        ),
    )
    select_size_button.pack(padx=5, pady=5)


# Función para seleccionar el tamaño de la ventana
def choose_size_factor(window):
    global size_factor

    size_factors = [0.5, 1, 1.5, 2]
    # Creamos el menu para las opciones de tamaño
    size_factor = tk.StringVar(window)
    # Seleccionamos el valor 1 por defecto
    size_factor.set(config["size_factor"])

    return size_factor, size_factors


# Manejamos el modo oscuro
def toggle_dark_mode(window, screen_window, frame):
    global dark_mode

    dark_mode = not dark_mode

    config["dark_mode"] = dark_mode
    save_config_file()
    if dark_mode:
        window.config(bg="#404040")
        screen_window.config(bg="#404040")
        frame.config(bg="#404040")
    else:
        window.config(bg="white")
        screen_window.config(bg="white")
        frame.config(bg="white")


# Botón para seleccionar el modo oscuro
def choose_dark_mode(
    window,
    screen_window,
    frame,
    size_factor,
    selected_port_in,
    selected_port_out,
    midi_ports_in,
    midi_ports_out,
):
    select_dark_mode = ttk.Button(
        frame,
        text="Modo oscuro",
        command=lambda: (
            toggle_dark_mode(window, screen_window, frame),
            create_canvas(
                window,
                size_factor,
                selected_port_in,
                selected_port_out,
                midi_ports_in,
                midi_ports_out,
            ),
        ),
        style="TButton",
    )
    # Si le damos al botón el texto se pone gris (para mostrar gráficamente que ha sido marcado)
    select_dark_mode.pack(padx=5, pady=5)


# Creamos el scrollbar para las configuraciones
def create_scrollbar(window):
    # Creamos un frame para el contenido desplazable
    container = tk.Frame(screen_window)
    container.pack(fill="both", expand=True)

    # Canvas con el scrollbar
    canvas = tk.Canvas(container, bg=window.cget("bg"))
    scrollbar = ttk.Scrollbar(container,
                              orient="vertical",
                              command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg=window.cget("bg"))

    # Configuramos el scrollbar
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    return scrollable_frame


# Establecemos la configuración de la pantalla
def screen_settings(
    window,
    selected_port_in,
    selected_port_out,
    size_factor,
    midi_ports_in,
    midi_ports_out,
):
    global screen_window
    # Si ya existe una ventana de configuración de audio la cerramos
    if screen_window is not None and screen_window.winfo_exists():
        screen_window.destroy()

    # Crear una nueva ventana para la configuración de pantalla
    screen_window = tk.Toplevel(window, bg=window.cget("bg"))
    screen_window.title("Configuración de Pantalla")

    screen_position(window, screen_window, size_factor)

    scrollable_frame = create_scrollbar(window)

    if dark_mode:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del tamaño de la ventana",
            bg=window.cget("bg"),
            fg="white",
        )
    else:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del tamaño de la ventana",
            bg=window.cget("bg"),
        )
    label_size_selection.pack(pady=5)

    # Agregar el menú de selección de tamaño
    size_factor, size_factors = choose_size_factor(screen_window)
    button_size_factor(
        window,
        scrollable_frame,
        size_factors,
        selected_port_in,
        selected_port_out,
        midi_ports_in,
        midi_ports_out,
    )

    separator = ttk.Separator(scrollable_frame, orient="horizontal")
    separator.pack(fill="x", pady=10)

    choose_dark_mode(
        window,
        screen_window,
        scrollable_frame,
        size_factor,
        selected_port_in,
        selected_port_out,
        midi_ports_in,
        midi_ports_out,
    )

    separator = ttk.Separator(scrollable_frame, orient="horizontal")
    separator.pack(fill="x", pady=10)


def audio_settings(
    window,
    selected_port_in,
    selected_port_out,
    size_factor,
    midi_ports_in,
    midi_ports_out,
    triangle_ids,
):
    global screen_window
    # Si ya existe una ventana de configuración de pantalla la cerramos
    if screen_window is not None and screen_window.winfo_exists():
        screen_window.destroy()

    # Crear una nueva ventana para la configuración del audio
    screen_window = tk.Toplevel(window, bg=window.cget("bg"))
    screen_window.title("Configuración MIDI")

    screen_position(window, screen_window, size_factor)

    scrollable_frame = create_scrollbar(window)

    if dark_mode:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto MIDI de entrada",
            bg=window.cget("bg"),
            fg="white",
        )
    else:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto Midi de entrada",
            bg=window.cget("bg"),
        )
    label_size_selection.pack(pady=5)

    # Botón para seleccionar el puerto de entrada
    midi_in_port_selection(window)
    button_select_midi_in(
        c,
        window,
        scrollable_frame,
        selected_port_out,
        selected_port_in,
        midi_ports_in,
        triangle_ids,
    )

    separator = ttk.Separator(scrollable_frame, orient="horizontal")
    separator.pack(fill="x", pady=10)

    if dark_mode:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto MIDI de salida",
            bg=window.cget("bg"),
            fg="white",
        )
    else:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto MIDI de salida",
            bg=window.cget("bg"),
        )
    label_size_selection.pack(pady=5)

    # Botón para seleccionar el puerto de salida
    midi_out_port_selection(window)
    button_select_midi_out(scrollable_frame, selected_port_out, midi_ports_out,
                           triangle_ids)

    separator = ttk.Separator(scrollable_frame, orient="horizontal")
    separator.pack(fill="x", pady=10)


def screen_position(window, screen_window, size_factor):
    size_factor = float(size_factor.get())

    # Obtenemos el tamaño de la ventana secundaria de configuración
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    config_width = int(600 * size_factor)
    config_height = int(300 * size_factor)
    x = int((screen_width - config_width) // 2)
    y = int((screen_height - config_height) // 2)
    screen_window.geometry(f"{config_width}x{config_height}+{x}+{y}")


# Función para cerrar el programa
def exit_program(window, selected_port_out):
    # Paramos el MIDI
    stop_midi(selected_port_out)
    # Cerramos la ventana
    window.quit()


# Obtenemos el menubar
def menu(
    window,
    selected_port_in,
    selected_port_out,
    size_factor,
    midi_ports_in,
    midi_ports_out,
    triangle_ids,
):
    menubar = tk.Menu(window)
    window.config(menu=menubar)

    # Opciones del menu
    filemenu = tk.Menu(menubar, tearoff=0)
    filemenu.add_command(
        label="Configuración de Pantalla",
        command=lambda: screen_settings(
            window,
            selected_port_in,
            selected_port_out,
            size_factor,
            midi_ports_in,
            midi_ports_out,
        ),
    )
    filemenu.add_command(
        label="Configuración MIDI",
        command=lambda: audio_settings(
            window,
            selected_port_in,
            selected_port_out,
            size_factor,
            midi_ports_in,
            midi_ports_out,
            triangle_ids,
        ),
    )
    filemenu.add_separator()
    filemenu.add_command(
        label="Salir", command=lambda: exit_program(window, selected_port_out))
    menubar.add_cascade(label="Opciones", menu=filemenu)


# Función para pintar el rectángulo
def paint_rectangle(circle_coords):
    global dark_mode

    # Obtener las coordenadas extremas de los triángulos
    min_x = float("inf")
    max_x = float("-inf")
    min_y = float("inf")
    max_y = float("-inf")

    # Obtenemos las coordenadas mínimas para representar el rectángulo
    for triangle_coords in circle_coords:
        for x, y in triangle_coords:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

    # Pintamos el rectángulo
    rectangle_coords = (min_x, min_y, max_x, max_y)

    if dark_mode:
        rectangle = c.create_rectangle(rectangle_coords,
                                       width=4,
                                       outline="white")
    else:
        rectangle = c.create_rectangle(rectangle_coords,
                                       width=4,
                                       outline="black")

    c.lower(rectangle)


# Crea la ventana del programa
def create_canvas(
    window,
    size_factor,
    selected_port_in,
    selected_port_out,
    midi_ports_in,
    midi_ports_out,
):
    global c, frame

    try:
        save_config_file()

        if "c" in globals() and c.winfo_exists():
            c.delete("all")
            c.destroy()
        if "frame" in globals() and frame.winfo_exists():
            frame.destroy()

        frame = tk.Frame(window)
        frame.pack(fill=tk.BOTH, expand=True)

        if dark_mode:
            window.config(bg="#404040")
        else:
            window.config(bg="white")

        # Aquí podemos modificar el tamaño de la pantalla y el color de fondo
        c = tk.Canvas(
            frame,
            width=window.winfo_screenwidth(),
            height=window.winfo_screenheight(),
            bg=window.cget("bg"),
        )
        c.pack(fill=tk.BOTH, expand=True)

        # Creamos los triángulos
        (
            painted_coords,
            triangle_ids,
            circle_coords,
        ) = triangles(window, c, size_factor)

        start_nav_thread(
            window,
            c,
            triangle_ids,
        )

        start_midi_out_thread(selected_port_out, triangle_ids)

        start_midi_in_thread(window, c, selected_port_out, selected_port_in,
                             triangle_ids)

        create_arpeggiator_frame(window, selected_port_out, triangle_ids)

        menu(
            window,
            selected_port_in,
            selected_port_out,
            size_factor,
            midi_ports_in,
            midi_ports_out,
            triangle_ids,
        )

        paint_rectangle(circle_coords)

    except TclError:
        pass

    return c


# Diseño de los botones y desplegables
def buttons_design():
    # Crear estilo
    style = ttk.Style()
    style.theme_use("clam")

    # Configuración del estilo de los desplegables
    style.configure(
        "TCombobox",
        padding=5,
        relief="flat",
        background="white",
        foreground="black",
    )

    style.map(
        "TCombobox",
        background=[("readonly", "white"), ("focus", "light grey")],
        foreground=[("readonly", "black"), ("focus", "grey")],
    )

    # Configuración del estilo de los botones
    style.configure(
        "TButton",
        padding=10,
        relief="flat",
        background="#e3e3e3",
        foreground="black",
        font=("Arial", 10),
    )

    style.map("TButton",
              background=[("active", "#0056b3"), ("pressed", "#004085")])


def main():
    global dark_mode

    # Comprobamos que estén todas las librerías necesarias para que funcione el programa
    dependencies = [
        "math",
        "mido",
        "threading",
        "tkinter",
        "rtmidi",
        "time",
        "yaml",
    ]
    print(check_dependences(dependencies))

    # Cargamos el fichero configuración y el puerto
    load_config_file()
    selected_ports = load_config_port()

    selected_port_in_from_config = selected_ports["port_in"]
    selected_port_out_from_config = selected_ports["port_out"]

    dark_mode = config["dark_mode"]

    # Creamos la ventana y le ponemos un título
    window = tk.Tk()
    window.title("Diagrama de Tonnetz")

    selected_port_in, selected_port_out, midi_ports_in, midi_ports_out = (
        get_midi_ports(window, selected_port_in_from_config,
                       selected_port_out_from_config))

    # Nos permite guardar la función con argumentos en otra sin argumentos
    exit_with_args = functools.partial(exit_program, window, selected_port_out)

    # Protocolo para cerrar la ventana
    window.protocol("WM_DELETE_WINDOW", exit_with_args)

    # Elegimos el factor
    size_factor, size_factors = choose_size_factor(window)

    buttons_design()

    # Muestra la imagen
    create_canvas(
        window,
        size_factor,
        selected_port_in,
        selected_port_out,
        midi_ports_in,
        midi_ports_out,
    )

    # Muestra la ventana
    window.mainloop()


main()
