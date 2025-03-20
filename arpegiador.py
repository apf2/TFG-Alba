import random

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


# Convertimos las notas a valores midi
def convert_note_to_midi(current_notes_set):
    midi_notes = []
    for note in current_notes_set:
        if note in dict_notes:
            midi_notes.append(dict_notes[note])
    return midi_notes


# Nos calcula el tiempo que debe haber entre notas viendo el compás y tempo
def calculate_time_between_notes(tempo, compas):
    # Obtenemos los valores de tempo y compas
    tempo_value = tempo.get()
    compas_value = compas.get()

    time_per_beat = 60 / tempo_value

    # Definimos las notas por compás
    beats_per_measure = int(compas_value.split("/")[0])
    note_value = int(compas_value.split("/")[1])
    time_between_notes = time_per_beat * (beats_per_measure / note_value)

    return time_between_notes


# Extiende las notas la octava que se haya marcado
def extend_octave(notes_to_play, octave):
    extended_notes = []

    for midi_note in notes_to_play:
        for i in range(octave.get()):
            extended_notes.append(midi_note + i * 12)

    return sorted(list(extended_notes))


# Ordena las notas según el modo en el que estemos
def order_arpeggio_notes(midi_notes, type):
    if type == "up":
        # Ordenar de menor a mayor
        midi_notes.sort()
    elif type == "down":
        # Ordenar de mayor a menor
        midi_notes.sort(reverse=True)
    elif type == "random":
        # Orden aleatorio
        random.shuffle(midi_notes)

    return midi_notes


# Obtiene las notas ordenadas que deben sonar
def get_arpeggio_notes(selected_shapes, triangle_ids, compas, octave, mode):
    compas_value = compas.get()

    notes_to_play = []
    for shape_id, shape_type in selected_shapes.items():
        if shape_type == "triangle":
            notes = triangle_ids[shape_id]["notes"]
            notes_to_play.extend(notes)

    unique_notes = set(notes_to_play)
    midi_notes = convert_note_to_midi(unique_notes)

    compas_value.split('/')
    # Si el compás necesita 4 notas por compás repetimos la primera
    if int(compas_value[0]) % 3 != 0:
        if midi_notes:
            midi_notes.append(midi_notes[0])

    extended_notes = extend_octave(midi_notes, octave)
    ordered_notes = order_arpeggio_notes(extended_notes, mode)

    return ordered_notes