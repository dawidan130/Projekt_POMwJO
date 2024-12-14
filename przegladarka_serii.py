import os
import sys
import itk
import matplotlib.pyplot as plt
import argparse
import numpy as np

class NoOutput(itk.OutputWindow):
    def DisplayText(self, text):
        pass

itk.OutputWindow.SetGlobalWarningDisplay(False)
no_output = NoOutput.New()
itk.OutputWindow.SetInstance(no_output)

#dane_obrazowe = "X:/Piotrek/Studia Magisterka/SEMESTR 2/Przetwarzanie Obrazow Medycznych w Jezykach Obiektowych/BT/BT"
dane_obrazowe = "G:/Edukacja/2020 Studia/Semestr 9/POMwJO/Projekt/BT"

parser = argparse.ArgumentParser(description="Read DICOM tags and visualize selected series.")
parser.add_argument(
    "dicom_directory",
    nargs="?",
    default=dane_obrazowe,
    help="If DicomDirectory is not specified, the current directory is used.",
)
args = parser.parse_args()

main_dir = args.dicom_directory

PixelType = itk.ctype("signed short")
Dimension = 3
ImageType = itk.Image[PixelType, Dimension]

patients = {}
series_descriptions = {}

def process_folder(dir_name):
    namesGenerator = itk.GDCMSeriesFileNames.New()
    namesGenerator.SetUseSeriesDetails(True)
    namesGenerator.SetDirectory(dir_name)

    series_ids = namesGenerator.GetSeriesUIDs()

    for series_id in series_ids:
        file_names = namesGenerator.GetFileNames(series_id)
        if not file_names:
            continue

        dicomIO = itk.GDCMImageIO.New()
        dicomIO.LoadPrivateTagsOn()

        reader = itk.ImageSeriesReader[ImageType].New()
        reader.SetImageIO(dicomIO)
        reader.SetFileNames(file_names)

        try:
            reader.Update()
        except Exception:
            continue

        metadata = dicomIO.GetMetaDataDictionary()

        patient_name_tag = "0010|0010"
        series_desc_tag = "0008|103e"

        if metadata.HasKey(patient_name_tag):
            patient_name = metadata[patient_name_tag]
            series_desc = metadata[series_desc_tag] if metadata.HasKey(series_desc_tag) else "Unknown Series"

            if patient_name not in patients:
                patients[patient_name] = {}
            if series_id not in patients[patient_name]:
                patients[patient_name][series_id] = []
            patients[patient_name][series_id].extend(file_names)

            series_descriptions[series_id] = series_desc

for root, dirs, files in os.walk(main_dir):
    process_folder(root)

def list_patients():
    print("Dostępni pacjenci:")
    for i, patient in enumerate(patients.keys(), start=1):
        print(f"{i}. {patient}")

if not patients:
    print("Nie znaleziono pacjentów.")
    sys.exit(1)

list_patients()

def select_patient():
    while True:
        try:
            choice = int(input("\nWybierz numer pacjenta: "))
            if 1 <= choice <= len(patients):
                return list(patients.keys())[choice - 1]
            else:
                print("Błąd. Wybierz poprawny numer.")
        except ValueError:
            print("Błąd wejścia. Proszę wpisz numer.")

selected_patient = select_patient()

def list_series(patient):
    print(f"\nSerie pacjenta: '{patient}':")
    for i, series_id in enumerate(patients[patient].keys(), start=1):
        series_desc = series_descriptions.get(series_id, "Unknown Series")
        print(f"{i}. {series_desc}")

list_series(selected_patient)

def select_series(patient):
    while True:
        try:
            choice = int(input("\nWybierz serię do wyświetlania: "))
            if 1 <= choice <= len(patients[patient]):
                selected_series_uid = list(patients[patient].keys())[choice - 1]
                return patients[patient][selected_series_uid]
            else:
                print("Błąd. Wybierz poprawny numer.")
        except ValueError:
            print("Błąd wejścia. Proszę wpisz numer.")

selected_files = select_series(selected_patient)

selected_files = sorted(set(selected_files))

PixelType2D = itk.US
Dimension2D = 2
ImageType2D = itk.Image[PixelType2D, Dimension2D]

current_index = 0

# Rozrost regionu (Region Growing)
def region_growing(image_file, seed):
    reader = itk.ImageFileReader[ImageType2D].New()
    reader.SetFileName(image_file)
    reader.Update()

    image = reader.GetOutput()
    image_array = itk.GetArrayFromImage(image)

    intensity_threshold = 500

    intensity = image_array[seed[1], seed[0]]  # Wartość intensywności w punkcie startowym
    lower_threshold = np.uint16(max(0, intensity - intensity_threshold))
    upper_threshold = np.uint16(min(65535, intensity + intensity_threshold))

    print(f"Rozrost regionu z punktu: {seed}, Intensywność: {intensity}, Zakres: [{lower_threshold}, {upper_threshold}]")

    region_grow = itk.ConnectedThresholdImageFilter[ImageType2D, ImageType2D].New()
    region_grow.SetInput(image)
    region_grow.SetSeed(seed)  # Współrzędne początkowe rozrostu
    region_grow.SetLower(int(lower_threshold))
    region_grow.SetUpper(int(upper_threshold))

    region_grow.Update()

    output_image = region_grow.GetOutput()
    result = itk.GetArrayFromImage(output_image)

    fig_seg, ax_seg = plt.subplots()
    ax_seg.imshow(result, cmap="gray")
    ax_seg.axis("off")
    ax_seg.set_title("Wynik segmentacji")
    fig_seg.canvas.draw()
    plt.show()

def show_image(index):
    reader = itk.ImageFileReader[ImageType2D].New()
    reader.SetFileName(selected_files[index])
    reader.Update()

    image_data = itk.GetArrayFromImage(reader.GetOutput())

    ax.clear()
    ax.imshow(image_data, cmap="gray")
    ax.axis("off")
    ax.set_title(f"Image {index + 1}/{len(selected_files)}")
    fig.canvas.draw()

def on_click(event):
    if event.xdata is not None and event.ydata is not None:
        x, y = int(event.xdata), int(event.ydata)
        print(f"Wybrano punkt: ({x}, {y})")
        region_growing(selected_files[current_index], seed=(x, y))

def on_key(event):
    global current_index
    if event.key == 'right':
        current_index = (current_index + 1) % len(selected_files)
    elif event.key == 'left':
        current_index = (current_index - 1) % len(selected_files)
    #ax.clf()
    show_image(current_index)

fig, ax = plt.subplots()
show_image(current_index)
fig.canvas.mpl_connect('key_press_event', on_key)
fig.canvas.mpl_connect('button_press_event', on_click)
plt.show()