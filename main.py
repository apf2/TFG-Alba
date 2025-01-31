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
import random

"""
Para que el programa funcione hay que installar las librería mido y tkinter 
'pip install mido'
'pip install tk'
'pip install PyYAML'
Además para algunas fuciones de mido se necesita instalar en el terminal
'pip install python-rtmidi'
esto es para las funciones mido.get_input_names() y mido.open_input()
"""

ROWS = 5
COLUMNS = 14
R_CIRCLE = 20
C_MIDI = 60
MAX_CHORD_INTERVAL = 0.25
TRIANGLE = 115
CONFIG_PATH = "config.yml"

# Diccionario de configuración
config = {
    "size_factor": 1.0,
    "port_in": "no-midi",
    "port_out": "no-midi",
    "dark_mode": False,
}

# Lista de notas para el orden gráfico
notes = [
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

# Diccionario de notas con sus valores midi correspondientes
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

# Diccionario donde guardaremos las notas que esten activas
active_notes = {}
navigation_mode = False
selected_shape = {}
previous_notes = []
up_arpeggiator = "up"
arpeggiator_mode = None
arpeggiator_active = False
note_times = {}

navigation_thread_active = threading.Event()
arpeggiator_thread_active = threading.Event()

screen_window = None
dark_mode = False


# Función de ChatGPT para comprobar las dependencias
def check_dependences(dependencies):
    missing_dependencies = []
    for dependency in dependencies:
        try:
            imported_module = importlib.import_module(dependency)
        except ImportError as e:
            missing_dependencies.append(dependency)

    if not missing_dependencies:
        return "ok"
    else:
        message = "Missing dependencies: {}\n".format(
            ", ".join(missing_dependencies)
        )
        message += "To install dependencies, run:\n"
        message += "pip install --user {}\n".format(
            " ".join(missing_dependencies)
        )
        return message


# Función de ChatGPT para simular mido.open_output() para cuando no hay puerto midi
def open_output_simulated():
    active_notes = set()

    def send(message):
        nonlocal active_notes
        if message.type == "note_on":
            active_notes.add(message.note)
            print(f"Simulando nota ON: {message.note}")
        elif message.type == "note_off":
            if message.note in active_notes:
                active_notes.remove(message.note)
                print(f"Simulando nota OFF: {message.note}")

    def close():
        print("Cerrando puerto simulado")

    return send, close


# Si existe el fichero de configuracion carga el puerto anteriormente seleccionado y no hace falta seleccionarlo
def load_config_port():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as config_file:
            config = yaml.safe_load(config_file)
            selected_port_in = config.get("port_in", "no-midi")
            # Leemos el puerto de entrada
            if selected_port_in == "no-midi":
                selected_port_in = "No hay puertos midi"
            # Leemos el puerto de salida
            selected_port_out = config.get("port_out", "no-midi")
            if selected_port_out == "no-midi":
                selected_port_out = "No hay puertos midi"
            return {"port_in": selected_port_in, "port_out": selected_port_out}

    return {"port_in": "No hay puertos midi", "port_out": "No hay puertos midi"}


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
def click_circle(c, circle, text, note, selected_port_in, selected_port_out):
    # Tocamos una nota con el ratón ya sea clicando el el círculo o en el texto
    c.tag_bind(
        circle,
        "<Button-1>",
        lambda event, note_value=note: play_note(
            note, selected_port_in, selected_port_out
        ),
    )
    c.tag_bind(
        text,
        "<Button-1>",
        lambda event, note_value=note: play_note(
            note, selected_port_in, selected_port_out
        ),
    )


# Evento de soltar el click en un circulo
def unclick_circle(c, circle, text, note, selected_port_in, selected_port_out):
    # Dejamos de tocar la nota con el ratón
    c.tag_bind(
        circle,
        "<ButtonRelease-1>",
        lambda event, note_value=note: stop_note(
            note, selected_port_in, selected_port_out
        ),
    )
    c.tag_bind(
        text,
        "<ButtonRelease-1>",
        lambda event, note_value=note: stop_note(
            note, selected_port_in, selected_port_out
        ),
    )


# Función para manejar los eventos del ratón para los círculos
def click_circle_events(
    c, circle, text, note, selected_port_in, selected_port_out
):
    try:
        click_circle(c, circle, text, note, selected_port_in, selected_port_out)
        unclick_circle(
            c, circle, text, note, selected_port_in, selected_port_out
        )
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Función para manejar los eventos del ratón para los triángulos
def click_triangle_events(
    window,
    c,
    triangle_ids,
    triangle_coords,
    triangle_notes,
    triangle_id,
    selected_port_in,
    selected_port_out,
):
    try:
        # Marca el triángulo al hacer clic con el ratón en este
        c.tag_bind(
            triangle_id,
            "<Button-1>",
            lambda event, coords=triangle_coords: handle_click_triangle(
                window,
                c,
                triangle_ids,
                triangle_coords,
                triangle_notes,
                selected_port_in,
                selected_port_out,
            ),
        )
        # Desmarca el triángulo al dejar de hacer clic
        c.tag_bind(
            triangle_id,
            "<ButtonRelease-1>",
            lambda event, coords=triangle_coords: stop_chord(
                coords, triangle_notes, selected_port_in, selected_port_out
            ),
        )
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


def handle_click_triangle(
    window,
    canvas,
    triangle_ids,
    triangle_coords,
    triangle_notes,
    selected_port_in,
    selected_port_out,
):
    global selected_shape

    # Detenemos los acordes que estén sonando
    for triangle_id in list(selected_shape.keys()):
        if selected_shape[triangle_id] == "triangle":
            triangle_coords_to_stop = tuple(triangle_ids[triangle_id])
            stop_chord(
                triangle_coords_to_stop,
                triangle_notes,
                selected_port_in,
                selected_port_out,
            )

    # Desmarcamos las formas y limpiamos la lista de selected_shape
    unmark_shapes(window, canvas)
    selected_shape.clear()

    # Actualizamos selected_shape con los nuevos triángulos
    new_triangle_id = None
    for tid, coords in triangle_ids.items():
        if tuple(coords) == triangle_coords:
            new_triangle_id = tid
            break

    if new_triangle_id:
        selected_shape[new_triangle_id] = "triangle"

    # Tocamos el acorde nuevo
    play_chord(
        triangle_coords, triangle_notes, selected_port_in, selected_port_out
    )


# Comprobamos las notas asociadas a los triángulos
def check_triangle_notes(painted_coords, triangle_notes):
    for coords in painted_coords.keys():
        for triangle_coords, notes_for_triangle in triangle_notes.items():
            for coord in triangle_coords:
                # Verificamos si alguna de las coordenadas redondeadas está en las coordenadas del triángulo
                if (
                    round(coord[0], 2) == coords[0]
                    and round(coord[1], 2) == coords[1]
                ):
                    # Si encontramos una coincidencia añadimos las notas asociadas a ese triángulo
                    note = painted_coords[coords]["note"]
                    # Si esa nota no está en la lista se añade
                    if note not in notes_for_triangle:
                        notes_for_triangle.append(note)

    # Ahora verificamos y eliminamos los duplicados en las notas de cada triángulo
    for triangle_coords, notes_for_triangle in triangle_notes.items():
        unique_notes = []
        for note in notes_for_triangle:
            # Si la nota no se encuentra en la lista unique_notes se añade
            if note not in unique_notes:
                unique_notes.append(note)
        triangle_notes[triangle_coords] = unique_notes
    return


# Función que añade los círculos con su nota correspondiente
def add_notes(
    c,
    circle_coords,
    triangle_notes,
    notes,
    selected_port_in,
    selected_port_out,
    size_factor,
):
    i = 0
    # Guardamos las coordenadas donde se ha pintado una nota ya
    painted_coords = {}
    circle_ids = {}
    size_factor_value = float(size_factor.get())

    for triangle_coord in circle_coords:
        for coords in triangle_coord:
            x, y = coords
            # Redondeamos las coordenadas a dos decimales por si no son exactas
            rounded_coords = (round(x, 2), round(y, 2))
            # Vemos si las coordenadas redondeadas están o no en painted_coords
            if rounded_coords not in painted_coords:
                note = notes[i]
                if dark_mode:
                    # Imprimimos el círculo
                    circle = c.create_oval(
                        x - R_CIRCLE * size_factor_value,
                        y - R_CIRCLE * size_factor_value,
                        x + R_CIRCLE * size_factor_value,
                        y + R_CIRCLE * size_factor_value,
                        fill="white",
                        outline="white",
                    )
                    # Imprimimos la nota
                    text = c.create_text(x, y, text=note, fill="white")
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
                    text = c.create_text(x, y, text=note, fill="black")

                # Añadimos esta coordenada a el diccionario con la nota que le corresponde
                painted_coords[rounded_coords] = {
                    "note": note,
                    "circle_id": circle,
                    "text_id": text,
                }
                circle_ids[circle] = {"coords": (x, y), "note": note}
                click_circle_events(
                    c, circle, text, note, selected_port_in, selected_port_out
                )

                i += 1

    # Comprobamos las notas asociadas
    check_triangle_notes(painted_coords, triangle_notes)

    return painted_coords, circle_ids, triangle_notes


# Genera la nota que hemos clicado
def play_note(note, selected_port_in, selected_port_out):
    global active_notes

    selected_port_in = selected_port_in.get()
    selected_port_out = selected_port_out.get()
    try:
        if note in dict_notes:
            midi_value = dict_notes[note]
            if note not in active_notes:
                active_notes[note] = midi_value
                # Si no hay puerto midi usamos nuestra función simulada
                if (
                    selected_port_out == "No hay puertos midi"
                    or selected_port_in == "No hay puertos midi"
                ):
                    send, close = open_output_simulated()
                    send(mido.Message("note_on", note=midi_value))
                else:
                    # Si hay puerto midi simulamos la nota
                    with mido.open_output(selected_port_out) as port:
                        port.send(mido.Message("note_on", note=midi_value))
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Dejamos de generar la nota que habiamos generado
def stop_note(note, selected_port_in, selected_port_out):
    selected_port_in = selected_port_in.get()
    selected_port_out = selected_port_out.get()
    try:
        if note in dict_notes:
            midi_value = dict_notes[note]
            if note in active_notes:
                # Si no hay puerto midi mandamos note_off con nuestra función simulada y cerramos
                if (
                    selected_port_out == "No hay puertos midi"
                    or selected_port_in == "No hay puertos midi"
                ):
                    send, close = open_output_simulated()
                    send(mido.Message("note_off", note=midi_value))
                    close()
                else:
                    # Si hay puerto midi simulamos la nota
                    with mido.open_output(selected_port_out) as port:
                        port.send(mido.Message("note_off", note=midi_value))
                active_notes.pop(note, None)
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Función para tocar un acorde, es decir, las 3 notas asociadas al triángulo
def play_chord(
    triangle_coords, triangle_notes, selected_port_in, selected_port_out
):
    try:
        chord_notes = triangle_notes[tuple(triangle_coords)]

        for note in chord_notes:
            if note in dict_notes:
                midi_value = dict_notes[note]
                if note not in active_notes:
                    active_notes[note] = midi_value
                if hasattr(selected_port_in, "get"):
                    selected_port_in = selected_port_in.get()
                if hasattr(selected_port_out, "get"):
                    selected_port_out = selected_port_out.get()
                if (
                    selected_port_out == "No hay puertos midi"
                    or selected_port_in == "No hay puertos midi"
                ):
                    send, close = open_output_simulated()
                    send(mido.Message("note_on", note=midi_value))
                else:
                    with mido.open_output(selected_port_out) as port:
                        port.send(mido.Message("note_on", note=midi_value))
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Función para que pare el acorde
def stop_chord(
    triangle_coords, triangle_notes, selected_port_in, selected_port_out
):
    try:
        chord_notes = triangle_notes[tuple(triangle_coords)]
        for note in chord_notes:
            if note in dict_notes:
                midi_value = dict_notes[note]
                if note in active_notes:
                    if hasattr(selected_port_in, "get"):
                        selected_port_in = selected_port_in.get()
                    if hasattr(selected_port_out, "get"):
                        selected_port_out = selected_port_out.get()
                    if (
                        selected_port_out == "No hay puertos midi"
                        or selected_port_in == "No hay puertos midi"
                    ):
                        send, close = open_output_simulated()
                        send(mido.Message("note_off", note=midi_value))
                        close()
                    else:
                        with mido.open_output(selected_port_out) as port:
                            port.send(mido.Message("note_off", note=midi_value))
                    active_notes.pop(note, None)
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


# Desmarcamos tantp circulos como triángulos
def unmark_shapes(window, canvas):
    global selected_shape

    shape_ids = list(selected_shape.keys())
    # Verificar si hay alguna forma seleccionada
    if selected_shape:
        # Iterar sobre todos los IDs de las formas seleccionadas
        for shape_id in shape_ids:
            # Cambiar el color de todas las formas seleccionadas a blanco
            canvas.itemconfig(shape_id, fill=window.cget("bg"))
            selected_shape.pop(shape_id, None)

        # Limpiar la selección después de desmarcar todas las formas
        selected_shape.clear()
        active_notes.clear()


# Marca la nota si ha sido detectada por midi
def mark_notes(canvas, note, circle_ids):
    global selected_shape
    try:
        # Iterar sobre circle_ids, que es más simple que painted_coords
        for circle_id, info in circle_ids.items():
            if info["note"] == note:
                if navigation_mode and circle_id not in selected_shape:
                    selected_shape[circle_id] = "circle"
                # Cambiar el color del círculo seleccionado
                canvas.itemconfig(circle_id, fill="#fcc035")

    except tk.TclError:
        pass


# Desmarca la nota cuando ya no es detectada
def unmark_notes(window, canvas, note, circle_ids):
    global selected_shape
    try:
        for circle_id, info in circle_ids.items():
            if info["note"] == note:
                # Restablece el color del círculo a blanco
                canvas.itemconfig(circle_id, fill=window.cget("bg"))

    except tk.TclError:
        pass


# Relacionamos los ids de los triángulos con sus notas asociadas
def relate_id_note(triangle_notes, triangle_ids):
    id_to_notes = {}
    for triangle_id, coords in triangle_ids.items():
        coords_tuple = tuple(coords)
        if coords_tuple in triangle_notes:
            id_to_notes[triangle_id] = triangle_notes[coords_tuple]

    return id_to_notes


# Obtenemos las notas actuales y las previas
def get_prev_and_new_notes(
    window,
    canvas,
    id_to_notes,
    triangle_id,
):
    # Obtener la nota actual del triángulo
    if triangle_id in id_to_notes:
        new_note = id_to_notes[triangle_id]

        if previous_notes:
            prev_note = previous_notes[-1]
            # Comparar las notas previas con las nuevas
            if set(prev_note) != set(new_note):
                # Si son diferentes, llamar a unmark_shapes
                unmark_shapes(window, canvas)

        previous_notes.clear()
        previous_notes.append(new_note)


# Marca el triángulo si ha sido clicado con el ratón
def mark_triangles(
    window,
    canvas,
    triangle_coords,
    triangle_ids,
    triangle_notes,
):
    global selected_shape, previous_notes

    try:
        # Crear un diccionario que relacione IDs de triángulos con sus notas
        id_to_notes = relate_id_note(triangle_notes, triangle_ids)

        # Iterar sobre los triángulos y verificar si coincide con las coordenadas proporcionadas
        for triangle_id, coords in triangle_ids.items():
            if list(coords) == list(triangle_coords):
                if navigation_mode:
                    get_prev_and_new_notes(
                        window,
                        canvas,
                        id_to_notes,
                        triangle_id,
                    )

                # Cambiar el color del triángulo
                canvas.itemconfig(triangle_id, fill="#7699d4")

    except tk.TclError:
        pass


# Desmarca el triángulo si deja de ser tocado
def unmark_triangles(window, canvas, triangle_coords, triangle_ids):
    global selected_shape

    try:
        for triangle_id, coords in triangle_ids.items():
            if list(coords) == list(triangle_coords):
                canvas.itemconfig(triangle_id, fill=window.cget("bg"))
    except tk.TclError:
        pass


# Crea los triángulos
def triangles(window, c, size_factor, selected_port_in, selected_port_out):
    global circle_coords

    size_factor_value = float(size_factor.get())
    triangle_side = TRIANGLE * size_factor_value
    triangle_height = triangle_side * math.sqrt(3) / 2

    circle_coords = []
    triangle_notes = {}
    triangle_ids = {}

    for row in range(ROWS):
        for col in range(COLUMNS):
            # Definimos las coordenadas x e y
            if row % 2 == 0:
                x = (
                    col * triangle_side / 2
                    + (1 - row % 2) * triangle_side / 2
                    + 100
                )
            else:
                x = (
                    col * triangle_side / 2
                    + (1 - row % 2) * triangle_side / 2
                    + 100
                    + triangle_side * 0.5
                )
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
                triangle_id = c.create_polygon(
                    triangle_coords, fill=window.cget("bg"), outline="white"
                )
            else:
                triangle_id = c.create_polygon(
                    triangle_coords, fill=window.cget("bg"), outline="black"
                )
            click_triangle_events(
                window,
                c,
                triangle_ids,
                triangle_coords,
                triangle_notes,
                triangle_id,
                selected_port_in,
                selected_port_out,
            )

            # Añadimos las coordenadas a nuestra lista
            circle_coords.append(triangle_coords)
            triangle_ids[triangle_id] = triangle_coords

            # Añadimos las notas a este triángulo
            triangle_notes[tuple(triangle_coords)] = []

    # Mostramos los círculos con sus notas
    painted_coords, circle_ids, triangle_notes = add_notes(
        c,
        circle_coords,
        triangle_notes,
        notes,
        selected_port_in,
        selected_port_out,
        size_factor,
    )

    return (
        painted_coords,
        triangle_notes,
        triangle_ids,
        circle_ids,
        circle_coords,
    )


# Detectamos que la nota está siendo tocada
def detect_note_on(
    window,
    canvas,
    note_midi,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_out,
):
    global selected_shape, active_notes

    for note, midi in dict_notes.items():
        # Comprueba si el valor midi coincide
        if midi == note_midi:
            musical_note = note
            # Comprobamos si la nota se encuentra en la lista de notas que pintamos
            if musical_note in notes:
                # Guardamos el círculo en selected_shape
                for circle_id, circle_note in circle_ids.items():
                    circle_note = circle_note.get("note")
                    if circle_note == musical_note:
                        selected_shape[circle_id] = "circle"
                # Marcamos la nota
                mark_notes(canvas, musical_note, circle_ids)

                # Buscamos el triángulo asociado a la nota y lo marcamos
                for coords, notes_for_triangle in triangle_notes.items():
                    if musical_note in notes_for_triangle:
                        if all(
                            note in active_notes for note in notes_for_triangle
                        ):
                            # Guardamos el triángulo a selected_shape
                            for (
                                triangle_id,
                                triangle_coords,
                            ) in triangle_ids.items():
                                if set(triangle_coords) == set(coords):
                                    selected_shape[triangle_id] = "triangle"
                            # Marcamos el triángulo
                            mark_triangles(
                                window,
                                canvas,
                                coords,
                                triangle_ids,
                                triangle_notes,
                            )
                try:
                    if selected_port_out != "no-midi":
                        with mido.open_output(selected_port_out) as port_out:
                            port_out.send(
                                mido.Message("note_on", note=note_midi)
                            )
                        # Registrar la nueva nota como activa
                        if note not in active_notes:
                            active_notes[note_midi] = note
                except OSError as e:
                    print(f"Error al abrir el puerto MIDI: {e}")
                except Exception as e:
                    print(f"Ocurrió un error inesperado: {e}")
    return


# Detectamos que la nota se ha apagado
def detect_note_off(
    window,
    canvas,
    note_midi,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_out,
):
    for note, midi in dict_notes.items():
        # Comprueba si el valor midi coincide
        if midi == note_midi:
            musical_note = note
            # Comprobamos si la nota se encuentra en la lista de notas
            if musical_note in notes:
                if not navigation_mode:
                    # Elimina los círculos de selected_shape
                    for circle_id, circle_note in circle_ids.items():
                        circle_note = circle_note.get("note")
                        if circle_note == musical_note:
                            selected_shape.pop(circle_id, None)

                    # Desmarcamos la nota
                    unmark_notes(window, canvas, musical_note, circle_ids)

                for coords, notes_for_triangle in triangle_notes.items():
                    if musical_note in notes_for_triangle:
                        all_notes_off = all(
                            midi not in active_notes.values()
                            for midi in notes_for_triangle
                        )
                        if all_notes_off:
                            if not navigation_mode:
                                # Elimina el triángulo de selected_shape
                                for (
                                    triangle_id,
                                    triangle_coords,
                                ) in triangle_ids.items():
                                    if set(triangle_coords) == set(coords):
                                        selected_shape.pop(triangle_id, None)

                                # Si están todas las nptas apagadas desmarcamos el triángulo
                                unmark_triangles(
                                    window, canvas, coords, triangle_ids
                                )
                # Enviamos la nota apagada al sintetizador
                try:
                    if selected_port_out != "no-midi":
                        with mido.open_output(selected_port_out) as port_out:
                            port_out.send(
                                mido.Message("note_off", note=note_midi)
                            )
                except OSError as e:
                    print(f"Error al abrir el puerto MIDI: {e}")
                except Exception as e:
                    print(f"Ocurrió un error inesperado: {e}")
    return


# Pinta los triángulos cuando se produce un acorde
def paint_triangles_in_chord(window, canvas, chord_notes, triangle_notes, triangle_ids):
    # Lista para almacenar las coordenadas de los triángulos que contienen las notas del acorde
    triangles_to_paint = []

    for coords, notes in triangle_notes.items():
        if all(note in notes for note in chord_notes):
            triangles_to_paint.append(coords)

    for coords in triangles_to_paint:
        mark_triangles(window, canvas, coords, triangle_ids, triangle_notes)
    return


# Nos detecta las notas cuando no hay puerto midi
def detect_note_without_midi(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    stop_event,
    selected_port_out,
):
    global active_notes

    print("Detectando notas")
    while not stop_event.is_set():
        try:
            for midi_note in dict_notes.values():
                # Verifica si la nota está activa
                if midi_note in list(active_notes.values()):
                    detect_note_on(
                        window,
                        canvas,
                        midi_note,
                        triangle_notes,
                        triangle_ids,
                        circle_ids,
                        selected_port_out,
                    )
                else:
                    detect_note_off(
                        window,
                        canvas,
                        midi_note,
                        triangle_notes,
                        triangle_ids,
                        circle_ids,
                        selected_port_out,
                    )
        except Exception:
            pass
        # Añado tiempo entre iteración para que no consuma mucha CPU
        time.sleep(0.01)


# Funcion por si el mensaje es 'note'
def detect_chord(window, canvas, note_midi, triangle_notes, triangle_ids):
    current_time = time.time()
    note = midi_to_note_name(note_midi)

    # Si la nota aún no está en las notas activas la añadimos con su tiempo de activación
    if note not in note_times:
        note_times[note] = current_time

    chord_notes = []
    for note in list(note_times):
        if current_time - note_times[note] <= MAX_CHORD_INTERVAL:
            chord_notes.append(note)
        else:
            note_times.pop(note, None)

    # Si hay exactamente 3 notas activas en ese intervalo de tiempo, consideramos que es un acorde
    if len(chord_notes) == 3:
        # Pintamos los triángulos asociados al acorde
        paint_triangles_in_chord(window, canvas, chord_notes, triangle_notes, triangle_ids)

    return chord_notes


# Detección de notas midi (con o sin puerto)
def detect_notes(
    window,
    selected_port_in,
    selected_port_out,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
):
    global active_notes
    try:
        # En caso de que se abra el programa sin puertos midi lo manejaremos con un bucle
        # para ir controlando las notas activas que generamos con open_output_simulated()
        if selected_port_in == "no-midi":
            detect_note_without_midi(
                window,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
                stop_event,
                selected_port_out,
            )
        else:
            # Abre el dispositivo midi
            with mido.open_input(selected_port_in) as port:
                print("Detectando notas")
                # Iteración de los mensajes midi
                for message in port:
                    # La función hasattr nos dice si el mensaje contiene 'note'
                    if hasattr(message, "note"):
                        # Nos ajusta la nota a los valores midi que manejamos en el diccionario
                        note_midi = message.note % 12 + C_MIDI
                        # Verifica si el mensaje es una nota activa
                        if message.type == "note_on":
                            detect_chord(
                                window, canvas, note_midi, triangle_notes, triangle_ids
                            )
                            detect_note_on(
                                window,
                                canvas,
                                note_midi,
                                triangle_notes,
                                triangle_ids,
                                circle_ids,
                                selected_port_out,
                            )
                        # Verifica si la nota ya no está activa
                        elif message.type == "note_off":
                            if note_midi in active_notes:
                                active_notes.pop(note_midi)
                            detect_note_off(
                                window,
                                canvas,
                                note_midi,
                                triangle_notes,
                                triangle_ids,
                                circle_ids,
                                selected_port_out,
                            )
                    # En caso de que no sea un mensaje tipo note lo ignoramos
                    elif message.type == "aftertouch":
                        pass
    except OSError as e:
        print("Error al abrir el puerto MIDI:", e)
    return


def monitor_active_notes(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_out,
):

    while stop_event is not None and not stop_event.is_set():
        if active_notes == {}:
            unmark_shapes(window, canvas)
        for midi_note in dict_notes.values():
            # Verifica si la nota está activa
            if midi_note in list(active_notes.values()):
                detect_note_on(
                    window,
                    canvas,
                    midi_note,
                    triangle_notes,
                    triangle_ids,
                    circle_ids,
                    selected_port_out,
                )
            else:
                detect_note_off(
                    window,
                    canvas,
                    midi_note,
                    triangle_notes,
                    triangle_ids,
                    circle_ids,
                    selected_port_out,
                )

        time.sleep(0.01)


# Añadir los nuevos triángulos en selected_shape
def get_triangle_in_selected_shape(shapes_to_update, triangle_ids, circle_ids):
    new_selected_shape = {}
    for shape_type, shape_updates in shapes_to_update.items():
        for old_id in shape_updates.keys():
            new_coords = shape_updates[old_id][1]
            new_shape_id = None
            for tid, coords in (
                triangle_ids if shape_type == "triangle" else circle_ids
            ).items():
                if tuple(coords) == new_coords:
                    new_shape_id = tid
                    break
            if new_shape_id is not None:
                new_selected_shape[new_shape_id] = shape_type
    return new_selected_shape


# Añadir circle_ids en selected_shape
def get_circle_in_selected_shape(
    new_selected_shape, triangle_notes, triangle_ids, circle_ids
):
    new_notes_to_check = list(new_selected_shape.keys())
    for triangle_id in new_notes_to_check:
        coords = tuple(triangle_ids[triangle_id])
        new_notes = triangle_notes.get(coords, [])

        for note in new_notes:
            for circle_id, circle_info in circle_ids.items():
                if circle_info["note"] == note:
                    new_selected_shape[circle_id] = "circle"


# Mover los triángulos en el canvas
def move_triangles(
    window,
    canvas,
    shapes_to_update,
    triangle_notes,
    triangle_ids,
    circle_ids,
):
    for old_coords, new_coords in shapes_to_update["triangle"].values():
        if old_coords != new_coords:
            # Recolectar notas antiguas y nuevas
            old_notes = triangle_notes.get(old_coords, [])
            new_notes = triangle_notes.get(new_coords, [])

            # Desmarcar las notas antiguas que ya no están asociadas
            if isinstance(old_notes, list):
                for old_note in old_notes:
                    if old_note not in new_notes:
                        unmark_notes(window, canvas, old_note, circle_ids)

            # Marcar las nuevas notas
            if isinstance(new_notes, list):
                for note in new_notes:
                    mark_notes(canvas, note, circle_ids)

            # Marcar el nuevo triángulo y desmarcar el anterior
            mark_triangles(
                window,
                canvas,
                new_coords,
                triangle_ids,
                triangle_notes,
            )
            unmark_triangles(window, canvas, old_coords, triangle_ids)

        else:
            # Solo marcar las nuevas notas si las coordenadas no cambiaron
            new_notes = triangle_notes.get(new_coords, [])
            if isinstance(new_notes, list):
                for note in new_notes:
                    mark_notes(canvas, note, circle_ids)


# Verificamos que sea válido
def verify_triangle_id(
    shapes_to_update,
    new_triangle_id,
    triangle_id,
    triangle_notes,
    triangle_ids,
    valid_move,
):
    if new_triangle_id in triangle_ids:
        old_coords = tuple(triangle_ids[triangle_id])
        new_coords = tuple(triangle_ids[new_triangle_id])
        # Obtener notas antiguas y nuevas
        old_notes = triangle_notes.get(old_coords, [])
        new_notes = triangle_notes.get(new_coords, [])

        # Verifica si el triángulo destino tiene al menos dos notas en común con el triángulo actual
        if have_two_common_notes(old_notes, new_notes):
            shapes_to_update["triangle"][triangle_id] = (old_coords, new_coords)
            valid_move = True

        # Almacena las coordenadas para la actualización
        shapes_to_update["triangle"][triangle_id] = (old_coords, new_coords)

    return valid_move


# Verifica si al menos dos notas son comunes entre las listas old_notes y new_notes
def have_two_common_notes(old_notes, new_notes):
    common_count = 0
    for old_note in old_notes:
        if old_note in new_notes:
            common_count += 1
        if common_count >= 2:
            return True
    return False


def mark_all(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
):
    # Usamos un conjunto para evitar duplicados
    all_notes = set()

    # Marcar triángulos y reproducir acordes
    for triangle_id, shape_type in selected_shape.items():
        if shape_type == "triangle":
            # Obtenemos las coordenadas del triángulo
            coords = tuple(triangle_ids[triangle_id])
            # Obtenemos las notas asociadas
            notes = triangle_notes.get(coords, [])
            # Añadimos las notas al conjunto
            all_notes.update(notes)

            # Marcamos cada nota en el canvas
            for note in notes:
                mark_notes(canvas, note, circle_ids)

    # Obtener la nota actual y las anteriores
    current_triangle_id = [
        triangle_id
        for triangle_id in selected_shape
        if selected_shape[triangle_id] == "triangle"
    ]
    if current_triangle_id:
        id_to_notes = relate_id_note(triangle_notes, triangle_ids)
        get_prev_and_new_notes(
            window, canvas, id_to_notes, current_triangle_id[0]
        )

    # Desmarcar triángulos no deseados
    for triangle_id, coords in triangle_ids.items():
        coords_tuple = tuple(coords)
        notes = triangle_notes.get(coords_tuple, [])

        # Verificar si todas las notas en all_notes están en las notas del triángulo actual
        if not all(note in notes for note in all_notes):
            unmark_triangles(window, canvas, coords_tuple, triangle_ids)


# Función para detener los acordes anteriores
def stop_chord_of_selected_triangles(
    selected_port_in, selected_port_out, triangle_notes, triangle_ids
):
    # Antes de mover el triángulo, detener el acorde actual
    for triangle_id in selected_shape:
        if selected_shape[triangle_id] == "triangle":
            triangle_coords = tuple(triangle_ids[triangle_id])
            stop_chord(
                triangle_coords,
                triangle_notes,
                selected_port_in,
                selected_port_out,
            )


# Manejamos el movimiento en modo navegación
def handle_key(
    window,
    event,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
):
    global selected_shape

    if navigation_mode:
        valid_move = False
        # Creamos un diccionario para almacenar las coordenadas antiguas y nuevas
        shapes_to_update = {"triangle": {}, "circle": {}}

        # Manejamos los triángulos
        if "triangle" in selected_shape.values():
            print("Manejando triángulos...")

            # Obtenemos todos los triángulos seleccionados
            for triangle_id, shape_type in list(selected_shape.items()):
                if shape_type == "triangle":
                    # Aseguramos de que triangle_id es un entero
                    if isinstance(triangle_id, tuple):
                        # Si triangle_id es una tupla usamos el primer elemento como el id
                        triangle_id = triangle_id[0]

                    # Calcula el nuevo id basado en la dirección de la tecla
                    if event.keysym == "Left":
                        new_triangle_id = triangle_id - 1
                        if (
                            new_triangle_id < 1
                            or (new_triangle_id - 1) % COLUMNS == COLUMNS - 1
                        ):
                            continue

                    elif event.keysym == "Right":
                        new_triangle_id = triangle_id + 1
                        if (
                            new_triangle_id > COLUMNS * ROWS
                            or new_triangle_id % COLUMNS == 1
                        ):
                            continue

                    elif event.keysym == "Up":
                        new_triangle_id = triangle_id - COLUMNS
                        if new_triangle_id < 1:
                            continue

                    elif event.keysym == "Down":
                        new_triangle_id = triangle_id + COLUMNS
                        if new_triangle_id > COLUMNS * ROWS:
                            continue

                    else:
                        continue

                    # Verifica si el nuevo id es válido
                    valid_move = verify_triangle_id(
                        shapes_to_update,
                        new_triangle_id,
                        triangle_id,
                        triangle_notes,
                        triangle_ids,
                        valid_move,
                    )

                    stop_chord_of_selected_triangles(
                        selected_port_in,
                        selected_port_out,
                        triangle_notes,
                        triangle_ids,
                    )

        if valid_move:
            move_triangles(
                window,
                canvas,
                shapes_to_update,
                triangle_notes,
                triangle_ids,
                circle_ids,
            )

            # Actualizar la selección actual
            new_selected_shape = get_triangle_in_selected_shape(
                shapes_to_update, triangle_ids, circle_ids
            )
            get_circle_in_selected_shape(
                new_selected_shape, triangle_notes, triangle_ids, circle_ids
            )

            selected_shape = new_selected_shape

            # Marcar notas después de mover triángulos
            mark_all(
                window,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
            )

            # Reproducir el acorde del nuevo triángulo seleccionado
            for triangle_id in selected_shape:
                if selected_shape[triangle_id] == "triangle":
                    triangle_coords = tuple(triangle_ids[triangle_id])
                    # Desmarcar triángulos previamente marcados
                    unmark_triangles(
                        window, canvas, triangle_notes, triangle_ids
                    )
                    # Marcar el triángulo seleccionado y tocar el acorde
                    mark_triangles(
                        window,
                        canvas,
                        triangle_coords,
                        triangle_ids,
                        triangle_notes,
                    )
                    play_chord(
                        triangle_coords,
                        triangle_notes,
                        selected_port_in,
                        selected_port_out,
                    )


# Controlamos los eventos de las flechas del teclado
def nav_with_arrow_keys(
    window,
    canvas,
    start_nav_button,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
):
    global navigation_mode, navigation_thread_active

    print(navigation_mode)

    while True:
        if navigation_mode:
            start_nav_button.config(text="Hold on")
            window.focus_set()

            window.bind(
                "<Up>",
                lambda event: handle_key(
                    window,
                    event,
                    canvas,
                    triangle_notes,
                    triangle_ids,
                    circle_ids,
                    selected_port_in,
                    selected_port_out,
                ),
            )
            window.bind(
                "<Down>",
                lambda event: handle_key(
                    window,
                    event,
                    canvas,
                    triangle_notes,
                    triangle_ids,
                    circle_ids,
                    selected_port_in,
                    selected_port_out,
                ),
            )
            window.bind(
                "<Left>",
                lambda event: handle_key(
                    window,
                    event,
                    canvas,
                    triangle_notes,
                    triangle_ids,
                    circle_ids,
                    selected_port_in,
                    selected_port_out,
                ),
            )
            window.bind(
                "<Right>",
                lambda event: handle_key(
                    window,
                    event,
                    canvas,
                    triangle_notes,
                    triangle_ids,
                    circle_ids,
                    selected_port_in,
                    selected_port_out,
                ),
            )
            navigation_thread_active.set()
        else:
            unmark_shapes(window, canvas)
            for note in list(active_notes.keys()):
                stop_note(note, selected_port_in, selected_port_out)

            start_nav_button.config(text="Hold off")
            # Desvincular los eventos de teclado
            window.unbind("<Up>")
            window.unbind("<Down>")
            window.unbind("<Left>")
            window.unbind("<Right>")

            navigation_thread_active.clear()
            break

        time.sleep(0.01)


# Función para alternar el modo de navegación
def toggle_navigation_mode(
    window,
    canvas,
    start_nav_button,
    triangle_notes,
    triangle_ids,
    circles_ids,
    selected_port_in,
    selected_port_out,
):
    global navigation_mode

    navigation_mode = not navigation_mode

    if navigation_mode:
        start_nav_button.config(text="Hold on")
        window.focus_set()

        # Iniciamos el hilo para el modo de navegación
        start_nav_thread(
            window,
            canvas,
            start_nav_button,
            triangle_notes,
            triangle_ids,
            circles_ids,
            selected_port_in,
            selected_port_out,
        )
    else:
        start_nav_button.config(text="Hold off")

    # Navigation_thread_active se encargará de controlar la activación y desactivación del hilo
    if not navigation_mode:
        # Cuando el modo de navegación se apaga, se asegura de que el hilo de navegación también se desactiva
        navigation_thread_active.clear()


# Función que inicia el hilo de navegación
def start_nav_thread(
    window,
    canvas,
    start_nav_button,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
):
    nav_thread = threading.Thread(
        target=nav_with_arrow_keys,
        args=(
            window,
            canvas,
            start_nav_button,
            triangle_notes,
            triangle_ids,
            circle_ids,
            selected_port_in,
            selected_port_out,
        ),
        daemon=True,
    )
    nav_thread.start()


# Desmarcar círculos no asociados a las notas tocadas
def unmark_unused_circles(
    window, canvas, circle_ids, current_notes_set, previous_notes_set
):
    for circle_id, circle_info in circle_ids.items():
        if (
            circle_info["note"] not in current_notes_set
            and circle_info["note"] in previous_notes_set
        ):
            # Llamar a unmark_notes para desmarcar la nota y el círculo
            unmark_notes(window, canvas, circle_info["note"], circle_ids)


def midi_to_note_name(midi_note):
    note_index = midi_note % 12
    # Buscar el nombre de la nota correspondiente al midi_note
    for note, midi in dict_notes.items():
        if midi == note_index + 60:
            return note

    return None


# Tocamos las notas del arpegio
def play_arpeggio_notes(
    midi_notes, selected_port_in, selected_port_out, tempo, compas
):
    tempo = tempo.get()
    compas = compas.get()

    print("tempo-> ", tempo)
    print("compas-> ", compas)
    time_per_beat = 60 / tempo

    # Definir las notas por compás según el compás
    beats_per_measure = int(compas.split("/")[0])
    note_value = int(compas.split("/")[1])

    time_between_notes = time_per_beat * (beats_per_measure / note_value)

    start_time = time.perf_counter()

    for midi_note in midi_notes:
        note_name = midi_to_note_name(midi_note)
        stop_note(note_name, selected_port_in, selected_port_out)
        print(f"Tocando nota: {note_name} (midi: {midi_note})")

        play_note(note_name, selected_port_in, selected_port_out)
        # Esperamos un tiempo entre notas calculado con el tempo y el compás
        next_note_time = start_time + time_between_notes
        current_time = time.perf_counter()

        while current_time < next_note_time:
            time.sleep(max(0.001, next_note_time - current_time))
            current_time = time.perf_counter()

        # Detenemos la nota
        stop_note(note_name, selected_port_in, selected_port_out)
        start_time = next_note_time


# Convertir las notas a valores midi
def convert_note_to_midi(current_notes_set):
    midi_notes = []
    for note in current_notes_set:
        if note in dict_notes:
            midi_notes.append(dict_notes[note])
    return midi_notes


# Extener octava
def extend_octave(notes_to_play, octave):
    octave = octave.get()
    extended_notes = set()

    # Convertir las notas a valores MIDI
    midi_notes = convert_note_to_midi(notes_to_play)

    # Añadimos las octavas correspondientes
    for midi_note in midi_notes:
        for i in range(octave):
            extended_notes.add(midi_note + i * 12)

    return extended_notes


# Tocamos el arpegiador dependiendo del modo
def play_arpeggio(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    type,
    tempo,
    compas,
    octave,
):
    global up_arpeggiator, arpeggiator_active
    previous_notes_set = set()

    while arpeggiator_active:
        if up_arpeggiator != type:
            # Si el tipo de arpegiador cambia, salimos del ciclo para reiniciar el hilo
            break

        window.update()

        for note in list(active_notes):
            stop_note(note, selected_port_in, selected_port_out)
            print(active_notes)
        current_shape = selected_shape.copy()

        # Procesarmos los triángulos y tocamos las notas correspondientes
        notes_to_play = []

        for triangle_id, shape_type in current_shape.items():
            if shape_type == "triangle":
                triangle_coords = tuple(triangle_ids.get(triangle_id, []))
                chord_notes = triangle_notes.get(triangle_coords, [])

                notes_to_play.extend(chord_notes)

        # Convertir notes_to_play a un conjunto para optimizar la búsqueda
        current_notes_set = set(notes_to_play)

        extended_notes_set = extend_octave(current_notes_set, octave)

        # Si hay notas para tocar reproducirlas
        if extended_notes_set:
            midi_notes = sorted(extended_notes_set)

            if type == "up":
                # Ordenar de menor a mayor
                midi_notes.sort()
            elif type == "down":
                # Ordenar de mayor a menor
                midi_notes.sort(reverse=True)
            elif type == "random":
                # Orden aleatorio
                random.shuffle(midi_notes)

            play_arpeggio_notes(
                midi_notes, selected_port_in, selected_port_out, tempo, compas
            )
            unmark_unused_circles(
                window,
                canvas,
                circle_ids,
                current_notes_set,
                previous_notes_set,
            )

        # Actualizar el conjunto de notas previamente tocadas
        previous_notes_set = current_notes_set

        # Añado tiempo entre iteración para que no consuma mucha CPU
        time.sleep(0.01)


# Manejo del arpegiador dinámico
def handle_arpeggiator(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    type,
    tempo,
    compas,
    octave,
):
    global up_arpeggiator

    try:
        if up_arpeggiator:
            print("Arpegiador activado")
            # Llamada continua a play_arpeggio para reproducir las notas dinámicamente
            play_arpeggio(
                window,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
                type,
                tempo,
                compas,
                octave,
            )

        else:
            print("Arpegiador desactivado")
    except TypeError as te:
        print(f"Error de tipo en el arpegiador: {te}")


# Función para encender o apagar el arpegiador y habilitar los botones up, sown y random
def toggle_arpeggiator(
    arpeggiator_on_button,
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    tempo,
    compas,
    octave,
):
    global arpeggiator_active, arpeggiator_event, arpeggiator_thread, up_arpeggiator
    arpeggiator_active = not arpeggiator_active

    up_button = window.up_button
    down_button = window.down_button
    random_button = window.random_button

    if arpeggiator_active:
        arpeggiator_on_button.config(text="Arpegiador on")
        print("Arpegiador encendido")

        start_arpeggiator(
            window,
            canvas,
            arpeggiator_on_button,
            triangle_notes,
            triangle_ids,
            circle_ids,
            selected_port_in,
            selected_port_out,
            "up",
            tempo,
            compas,
            octave,
        )

        # Habilitar los botones up, down y random
        up_button.state(["!disabled"])
        down_button.state(["!disabled"])
        random_button.state(["!disabled"])

        arpeggiator_thread_active.set()
    else:
        arpeggiator_on_button.config(text="Arpegiador off")
        print("Arpegiador apagado")
        arpeggiator_active = False
        up_arpeggiator = None
        arpeggiator_event.set()
        # Deshabilitar los botones up, down y random
        up_button.state(["disabled"])
        down_button.state(["disabled"])
        random_button.state(["disabled"])

        arpeggiator_thread_active.clear()


# Función para iniciaar el hilo del arpegiador
def start_arpeggiator(
    window,
    canvas,
    start_arpeggiator_button,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    type,
    tempo,
    compas,
    octave,
):
    global arpeggiator_event, arpeggiator_mode, arpeggiator_thread, up_arpeggiator
    arpeggiator_thread = None

    if up_arpeggiator != type:
        up_arpeggiator = type
        if arpeggiator_thread and arpeggiator_thread.is_alive():
            arpeggiator_event.set()
            arpeggiator_thread.join()
            arpeggiator_thread = None

    if not arpeggiator_thread:
        arpeggiator_event = threading.Event()
        arpeggiator_thread = threading.Thread(
            target=handle_arpeggiator,
            args=(
                window,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
                type,
                tempo,
                compas,
                octave,
            ),
            daemon=True,
        )
        arpeggiator_thread.start()

    arpeggiator_mode = start_arpeggiator_button


# Función para iniciar el hilo de detección de notas sin puerto MIDI
def start_detect_note_without_midi(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_out,
):
    global stop_event

    stop_event = threading.Event()
    detect_note_thread = threading.Thread(
        target=detect_note_without_midi,
        args=(
            window,
            canvas,
            triangle_notes,
            triangle_ids,
            circle_ids,
            stop_event,
            selected_port_out,
        ),
        daemon=True,
    )
    detect_note_thread.start()
    return


# Hilo de ejecución para la detección de notas
def start_thread(
    window,
    selected_port_in,
    selected_port_out,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
):
    global detect_note_thread, stop_event, monitor_notes_thread
    stop_event = None
    """Vamos a crear un hilo para que la ejecución de la detección de notas esté
    en paralelo a la ventana con la imagen Ponemos daemon=True para que se
    termine la ejecución de la función al cerrar el programa En selected_port
    vamos a poner .get() debido a que se trata de un StringVar esto va a hacer
    que se nos devuelva el valor marcado en el menu de opciones."""
    # Si tiene el método get lo obtenemos
    selected_port_in = selected_port_in.get()
    selected_port_out = selected_port_out.get()

    # Convertimos 'No hay puertos midi' a 'no-midi'
    if selected_port_in == "No hay puertos midi":
        selected_port_in = "no-midi"
    if selected_port_out == "No hay puertos midi":
        selected_port_out = "no-midi"

    if stop_event and not stop_event.is_set():
        stop_event.set()
    elif not stop_event:
        stop_event = threading.Event()

    # Hilo para el monitoreo de active_notes
    monitor_notes_thread = threading.Thread(
        target=monitor_active_notes,
        args=(
            window,
            canvas,
            triangle_notes,
            triangle_ids,
            circle_ids,
            selected_port_out,
        ),
        daemon=True,
    )
    monitor_notes_thread.start()

    if selected_port_out == "no-midi":
        stop_event = start_detect_note_without_midi(
            window,
            canvas,
            triangle_notes,
            triangle_ids,
            circle_ids,
            selected_port_out,
        )
    else:
        detect_note_thread = threading.Thread(
            target=detect_notes,
            args=(
                window,
                selected_port_in,
                selected_port_out,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
            ),
            daemon=True,
        )
        detect_note_thread.start()


# Actualiza en el fichero config el nuevo tamaño
def update_size_factor(size_factor):
    config["size_factor"] = size_factor
    save_config_file()


# Actualiza en el fichero config el nuevo puerto in
def update_selected_port_in(selected_port_in):
    selected_port_in = selected_port_in.get()
    # Verificamos si el puerto seleccionado es "No hay puertos MIDI" para guardar 'no-midi'
    if selected_port_in == "No hay puertos midi":
        config["port_in"] = "no-midi"
    else:
        # Si es un puerto MIDI válido, lo guardamos tal cual
        config["port_in"] = selected_port_in

    save_config_file()


# Actualiza en el fichero config el nuevo puerto out
def update_selected_port_out(selected_port_out):
    selected_port_out = selected_port_out.get()
    # Verificamos si el puerto seleccionado es "No hay puertos MIDI" para guardar 'no-midi'
    if selected_port_out == "No hay puertos midi":
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
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
):
    # Crear el frame del arpegiador
    arpeggiator_frame = tk.Frame(
        window, bd=2, relief=tk.RIDGE, bg=window.cget("bg")
    )

    # Llamar a la función de actualización de posición al crear el frame
    update_position(arpeggiator_frame, window)

    # Asignar la función de actualización a la configuración de la ventana
    window.bind(
        "<Configure>", lambda event: update_position(arpeggiator_frame, window)
    )

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

    button_nav(
        arpeggiator_frame,
        c,
        triangle_notes,
        triangle_ids,
        circle_ids,
        selected_port_in,
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
        canvas,
        triangle_notes,
        triangle_ids,
        circle_ids,
        selected_port_in,
        selected_port_out,
        tempo,
        compas,
        octave,
    )

    # Creamos los botones up, down y random
    up_button = button_arpeggiator_up(
        button_frame,
        canvas,
        triangle_notes,
        triangle_ids,
        circle_ids,
        selected_port_in,
        selected_port_out,
        tempo,
        compas,
        octave,
    )
    down_button = button_arpeggiator_down(
        button_frame,
        canvas,
        triangle_notes,
        triangle_ids,
        circle_ids,
        selected_port_in,
        selected_port_out,
        tempo,
        compas,
        octave,
    )
    random_button = button_arpeggiator_random(
        button_frame,
        canvas,
        triangle_notes,
        triangle_ids,
        circle_ids,
        selected_port_in,
        selected_port_out,
        tempo,
        compas,
        octave,
    )

    # Deshabilitar inicialmente los botones
    up_button.state(["disabled"])
    down_button.state(["disabled"])
    random_button.state(["disabled"])

    # Guardamos los botones en el marco para acceder a ellos después
    button_frame.up_button = up_button
    button_frame.down_button = down_button
    button_frame.random_button = random_button

    return compas, tempo


# Botón para activar el arpegiador de mayor a menor
def button_arpeggiator_up(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    tempo,
    compas,
    octave,
):
    up_image = tk.PhotoImage(file="imagenes/up.png")
    start_arpeggiator_button_up = ttk.Button(
        window,
        image=up_image,
        command=lambda: (
            start_arpeggiator(
                window,
                canvas,
                start_arpeggiator_button_up,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
                "up",
                tempo,
                compas,
                octave,
            )
        ),
    )

    # Mantiene una referencia a la imagen para evitar que se recoja por el garbage collector
    start_arpeggiator_button_up.image = up_image

    start_arpeggiator_button_up.pack(side=tk.LEFT, padx=5)

    return start_arpeggiator_button_up


# Botón para activar el arpegiador de menor a mayor
def button_arpeggiator_down(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    tempo,
    compas,
    octave,
):
    down_image = tk.PhotoImage(file="imagenes/down.png")
    start_arpeggiator_button_down = ttk.Button(
        window,
        image=down_image,
        command=lambda: (
            start_arpeggiator(
                window,
                canvas,
                start_arpeggiator_button_down,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
                "down",
                tempo,
                compas,
                octave,
            )
        ),
    )

    start_arpeggiator_button_down.image = down_image
    start_arpeggiator_button_down.pack(side=tk.LEFT, padx=5)

    return start_arpeggiator_button_down


# Botón para activar el arpegiador de manera aleatoria
def button_arpeggiator_random(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    tempo,
    compas,
    octave,
):
    random_image = tk.PhotoImage(file="imagenes/random.png")
    start_arpeggiator_button_random = ttk.Button(
        window,
        image=random_image,
        command=lambda: (
            start_arpeggiator(
                window,
                canvas,
                start_arpeggiator_button_random,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
                "random",
                tempo,
                compas,
                octave,
            )
        ),
    )

    start_arpeggiator_button_random.image = random_image
    start_arpeggiator_button_random.pack(side=tk.LEFT, padx=5)

    return start_arpeggiator_button_random


# Botón para activar el arpegiador
def button_arpeggiator(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circle_ids,
    selected_port_in,
    selected_port_out,
    tempo,
    compas,
    octave,
):
    start_arpeggiator_button = ttk.Button(
        window,
        text="Arpegiador off",
        command=lambda: (
            toggle_arpeggiator(
                start_arpeggiator_button,
                window,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
                selected_port_in,
                selected_port_out,
                tempo,
                compas,
                octave,
            )
        ),
    )

    start_arpeggiator_button.pack(side=tk.LEFT, pady=10)


# Botón para cambiar al modo navegar con las flechas
def button_nav(
    window,
    canvas,
    triangle_notes,
    triangle_ids,
    circles_ids,
    selected_port_in,
    selected_port_out,
):
    start_nav_button = ttk.Button(
        window,
        text="Hold off",
        command=lambda: (
            toggle_navigation_mode(
                window,
                canvas,
                start_nav_button,
                triangle_notes,
                triangle_ids,
                circles_ids,
                selected_port_in,
                selected_port_out,
            )
        ),
    )

    start_nav_button.pack(side=tk.TOP, pady=10)


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
    decrease_button = ttk.Button(
        window, text="-", command=lambda: decrease_tempo(tempo), width=2
    )
    decrease_button.pack(side=tk.LEFT)

    tempo_entry = ttk.Entry(window, textvariable=tempo, width=5)
    tempo_entry.pack(side=tk.LEFT)

    increase_button = ttk.Button(
        window, text="+", command=lambda: increase_tempo(tempo), width=2
    )
    increase_button.pack(side=tk.LEFT)

    tempo_entry.bind("<Return>", lambda e: validate_tempo(tempo))

    return tempo


# Función para elegir el compás
def choose_compas(window):
    compas_frame = tk.Frame(window, bg=window.cget("bg"))
    compas_frame.pack(side=tk.LEFT, padx=5)

    compases = ["2/4", "3/4", "4/4", "6/8"]

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
        label = tk.Label(
            octave_frame, text="Extensión por:", bg=window.cget("bg")
        )

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
        label = tk.Label(
            octave_frame, text="octava", bg=window.cget("bg"), fg="white"
        )
    else:
        label = tk.Label(octave_frame, text="octava", bg=window.cget("bg"))

    label.pack(side=tk.LEFT)

    return octave


# Obtenemos el boton para la seleccion del puerto midi
def button_select_midi_in(
    canvas,
    window,
    frame,
    selected_port_in,
    selected_port_out,
    midi_ports_in,
    triangle_notes,
    triangle_ids,
    circle_ids,
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
            start_thread(
                window,
                selected_port_in,
                selected_port_out,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
            ),
        ),
    )
    select_midi_button.pack(padx=5, pady=5)


# Obtenemos el boton para la seleccion del puerto midi
def button_select_midi_out(
    canvas,
    window,
    frame,
    selected_port_in,
    selected_port_out,
    midi_ports_out,
    painted_coords,
    triangle_notes,
    triangle_ids,
    circle_ids,
):
    port_menu = ttk.Combobox(
        frame,
        textvariable=selected_port_out,
        values=midi_ports_out,
        state="readonly",
    )
    port_menu.pack(padx=5, pady=5)
    # Boóon para seleccionar el puerto elegido
    # Ponemos lambda para que nos permita pasar la función con el argumento
    select_midi_button = ttk.Button(
        frame,
        text="Seleccionar",
        command=lambda: (
            update_selected_port_out(selected_port_out),
            start_thread(
                window,
                selected_port_in,
                selected_port_out,
                canvas,
                triangle_notes,
                triangle_ids,
                circle_ids,
            ),
        ),
    )
    select_midi_button.pack(padx=5, pady=5)


# Menu de selección del puerto midi
def midi_in_port_selection(window):
    midi_in_ports = mido.get_input_names()

    # Si no hay puertos midi mostramos la opcion de que no hay puertos
    midi_in_ports = ["No hay puertos midi"] + midi_in_ports

    # Creamos el menu para las opciones de puertos midi
    selected_port_in = tk.StringVar(window)
    # Seleccionamos el primero por defecto
    if config["port_in"] == "no-midi":
        selected_port_in.set("No hay puertos midi")
    else:
        selected_port_in.set(config["port_in"])

    return selected_port_in, midi_in_ports


# Menu de selección del puerto midi
def midi_out_port_selection(window):
    midi_out_ports = mido.get_output_names()

    # Si no hay puertos midi mostramos la opcion de que no hay puertos
    midi_out_ports = ["No hay puertos midi"] + midi_out_ports

    # Creamos el menu para las opciones de puertos midi
    selected_port_out = tk.StringVar(window)
    # Seleccionamos el primero por defecto
    if config["port_out"] == "no-midi":
        selected_port_out.set("No hay puertos midi")
    else:
        selected_port_out.set(config["port_out"])

    return selected_port_out, midi_out_ports


def get_midi_ports(
    window, selected_port_in_from_config, selected_port_out_from_config
):
    # Seleccionamos el puerto midi de entrada y salida
    selected_port_in, midi_ports_in = midi_in_port_selection(window)
    if selected_port_in_from_config:
        selected_port_in.set(selected_port_in_from_config)

    selected_port_out, midi_ports_out = midi_out_port_selection(window)
    if selected_port_out_from_config:
        selected_port_out.set(selected_port_out_from_config)

    return selected_port_in, selected_port_out, midi_ports_in, midi_ports_out


# Obtenemos el boton para seleccionar el tamaño de la ventana
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
    size_factor_menu = ttk.Combobox(
        frame, textvariable=size_factor, values=size_factors, state="readonly"
    )
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


# Funcion para seleccionar el tamaño de la ventana
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
    # Si le damos al botón el texto se pone gris (para mostrar graficamebte que ha sido marcado)
    select_dark_mode.pack(padx=5, pady=5)


# Creamos el scrollbar para las configuraciones
def create_scrollbar(window):
    # Creamos un frame para el contenido desplazable
    container = tk.Frame(screen_window)
    container.pack(fill="both", expand=True)

    # Canvas con el scrollbar
    canvas = tk.Canvas(container, bg=window.cget("bg"))
    scrollbar = ttk.Scrollbar(
        container, orient="vertical", command=canvas.yview
    )
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
    painted_coords,
    triangle_notes,
    triangle_ids,
    circle_ids,
):
    global screen_window
    # Si ya existe una ventana de configuración de pantalla la cerramos
    if screen_window is not None and screen_window.winfo_exists():
        screen_window.destroy()

    # Crear una nueva ventana para la configuración del audio
    screen_window = tk.Toplevel(window, bg=window.cget("bg"))
    screen_window.title("Configuración Midi")

    screen_position(window, screen_window, size_factor)

    scrollable_frame = create_scrollbar(window)

    if dark_mode:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto Midi de entrada",
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
        selected_port_in,
        selected_port_out,
        midi_ports_in,
        triangle_notes,
        triangle_ids,
        circle_ids,
    )

    separator = ttk.Separator(scrollable_frame, orient="horizontal")
    separator.pack(fill="x", pady=10)

    if dark_mode:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto Midi de salida",
            bg=window.cget("bg"),
            fg="white",
        )
    else:
        label_size_selection = tk.Label(
            scrollable_frame,
            text="Selección del puerto Midi de salida",
            bg=window.cget("bg"),
        )
    label_size_selection.pack(pady=5)

    # Botón para seleccionar el puerto de salida
    midi_out_port_selection(window)
    button_select_midi_out(
        c,
        window,
        scrollable_frame,
        selected_port_in,
        selected_port_out,
        midi_ports_out,
        painted_coords,
        triangle_notes,
        triangle_ids,
        circle_ids,
    )

    separator = ttk.Separator(scrollable_frame, orient="horizontal")
    separator.pack(fill="x", pady=10)


def screen_position(window, screen_window, size_factor):
    size_factor = float(size_factor.get())

    # Obtenemos el tamaño de la ventana secundaria de configuracion
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    config_width = int(600 * size_factor)
    config_height = int(300 * size_factor)
    x = int((screen_width - config_width) // 2)
    y = int((screen_height - config_height) // 2)
    screen_window.geometry(f"{config_width}x{config_height}+{x}+{y}")


# Obtenemos el menubar
def menu(
    window,
    selected_port_in,
    selected_port_out,
    size_factor,
    midi_ports_in,
    midi_ports_out,
    painted_coords,
    triangle_notes,
    triangle_ids,
    circle_ids,
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
        label="Configuración Midi",
        command=lambda: audio_settings(
            window,
            selected_port_in,
            selected_port_out,
            size_factor,
            midi_ports_in,
            midi_ports_out,
            painted_coords,
            triangle_notes,
            triangle_ids,
            circle_ids,
        ),
    )
    filemenu.add_separator()
    filemenu.add_command(label="Salir", command=window.quit)
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

    # Pintamos el rectangulo
    rectangle_coords = (min_x, min_y, max_x, max_y)

    if dark_mode:
        rectangle = c.create_rectangle(
            rectangle_coords, width=4, outline="white"
        )
    else:
        rectangle = c.create_rectangle(
            rectangle_coords, width=4, outline="black"
        )

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

        # Aqui podemos modificar el tamaño de la pantalla y el color de fondo
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
            triangle_notes,
            triangle_ids,
            circle_ids,
            circle_coords,
        ) = triangles(
            window, c, size_factor, selected_port_in, selected_port_out
        )

        create_arpeggiator_frame(
            window,
            c,
            triangle_notes,
            triangle_ids,
            circle_ids,
            selected_port_in,
            selected_port_out,
        )

        menu(
            window,
            selected_port_in,
            selected_port_out,
            size_factor,
            midi_ports_in,
            midi_ports_out,
            painted_coords,
            triangle_notes,
            triangle_ids,
            circle_ids,
        )

        paint_rectangle(circle_coords)

        start_thread(
            window,
            selected_port_in,
            selected_port_out,
            c,
            triangle_notes,
            triangle_ids,
            circle_ids,
        )

    except TclError:
        pass

    return c


# Diseño de los botones y desplegables
def buttons_desing():
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

    style.map(
        "TButton", background=[("active", "#0056b3"), ("pressed", "#004085")]
    )


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
        get_midi_ports(
            window, selected_port_in_from_config, selected_port_out_from_config
        )
    )

    # Elegimos el factor
    size_factor, size_factors = choose_size_factor(window)

    buttons_desing()

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
