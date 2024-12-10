import os
import sys
import itk
import matplotlib.pyplot as plt
import argparse

class NoOutput(itk.OutputWindow):
    def DisplayText(self, text):
        pass

itk.OutputWindow.SetGlobalWarningDisplay(False)
no_output = NoOutput.New()
itk.OutputWindow.SetInstance(no_output)

dane_obrazowe = "X:/Piotrek/Studia Magisterka/SEMESTR 2/Przetwarzanie Obrazow Medycznych w Jezykach Obiektowych/BT/BT/KARY1"

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
            if series_desc not in patients[patient_name]:
                patients[patient_name][series_desc] = []

            patients[patient_name][series_desc].extend(file_names)

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
    for i, series in enumerate(patients[patient].keys(), start=1):
        print(f"{i}. {series}")

list_series(selected_patient)

def select_series(patient):
    while True:
        try:
            choice = int(input("\nWybierz serię do wyświetlania: "))
            if 1 <= choice <= len(patients[patient]):
                return list(patients[patient].values())[choice - 1]
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

def show_image(index):
    reader = itk.ImageFileReader[ImageType2D].New()
    reader.SetFileName(selected_files[index])
    reader.Update()

    image_data = itk.GetArrayFromImage(reader.GetOutput())

    plt.imshow(image_data, cmap="gray")
    plt.axis("off")
    plt.title(f"Image {index + 1}/{len(selected_files)}")
    plt.draw()

def on_key(event):
    global current_index
    if event.key == 'right':
        current_index = (current_index + 1) % len(selected_files)
    elif event.key == 'left':
        current_index = (current_index - 1) % len(selected_files)

    plt.clf()
    show_image(current_index)

fig, ax = plt.subplots()
show_image(current_index)
fig.canvas.mpl_connect('key_press_event', on_key)
plt.show()