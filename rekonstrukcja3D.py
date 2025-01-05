import os
import sys
import itk
import matplotlib.pyplot as plt
import argparse
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

class NoOutput(itk.OutputWindow):
    def DisplayText(self, text):
        pass

itk.OutputWindow.SetGlobalWarningDisplay(False)
no_output = NoOutput.New()
itk.OutputWindow.SetInstance(no_output)

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

# Przetwarzanie folderów
for root, dirs, files in os.walk(main_dir):
    namesGenerator = itk.GDCMSeriesFileNames.New()
    namesGenerator.SetUseSeriesDetails(True)
    namesGenerator.SetDirectory(root)

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

        patient_name = metadata[patient_name_tag] if metadata.HasKey(patient_name_tag) else "Unknown Patient"
        series_desc = metadata[series_desc_tag] if metadata.HasKey(series_desc_tag) else "Unknown Series"

        if patient_name not in patients:
            patients[patient_name] = {}
        patients[patient_name][series_id] = file_names
        series_descriptions[series_id] = series_desc

if not patients:
    print("Nie znaleziono pacjentów.")
    sys.exit(1)

print("Dostępni pacjenci:")
for i, patient in enumerate(patients.keys(), start=1):
    print(f"{i}. {patient}")

selected_patient = list(patients.keys())[int(input("Wybierz numer pacjenta: ")) - 1]

print(f"\nSerie pacjenta: '{selected_patient}':")
for i, (series_id, desc) in enumerate(patients[selected_patient].items(), start=1):
    print(f"{i}. {series_descriptions.get(series_id, 'Unknown Series')}")

selected_series_uid = list(patients[selected_patient].keys())[int(input("Wybierz serię do wyświetlania: ")) - 1]
selected_files = sorted(patients[selected_patient][selected_series_uid])

PixelType2D = itk.US
Dimension2D = 2
ImageType2D = itk.Image[PixelType2D, Dimension2D]

# Rozrost regionu dla całej objętości 3D
def region_growing_3d(image_files, seed):
    intensity_threshold = 500
    
    # Wczytaj całą serię jako obraz 3D
    reader = itk.ImageSeriesReader[ImageType].New()
    reader.SetFileNames(image_files)
    reader.Update()

    image_3d = reader.GetOutput()
    image_array = itk.GetArrayFromImage(image_3d)

    intensity = image_array[seed[2], seed[1], seed[0]]
    lower_threshold = np.int16(max(-1024, intensity - intensity_threshold))
    upper_threshold = np.int16(min(3071, intensity + intensity_threshold))

    region_grow = itk.ConnectedThresholdImageFilter[ImageType, ImageType].New()
    region_grow.SetInput(image_3d)
    region_grow.SetSeed(seed)
    region_grow.SetLower(int(lower_threshold))
    region_grow.SetUpper(int(upper_threshold))
    region_grow.Update()

    mask_3d = itk.GetArrayFromImage(region_grow.GetOutput()) > 0

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.voxels(mask_3d, edgecolor='k')
    plt.title("Segmentacja 3D")
    plt.show()

current_index = 0

fig, ax = plt.subplots()
reader = itk.ImageFileReader[ImageType2D].New()
reader.SetFileName(selected_files[current_index])
reader.Update()
image_data = itk.GetArrayFromImage(reader.GetOutput())
ax.imshow(image_data, cmap="gray")
ax.axis("off")

def on_click(event):
    if event.xdata and event.ydata:
        x, y = int(event.xdata), int(event.ydata)
        region_growing_3d(selected_files, seed=(x, y, current_index))

def on_key(event):
    global current_index
    if event.key == 'right':
        current_index = (current_index + 1) % len(selected_files)
    elif event.key == 'left':
        current_index = (current_index - 1) % len(selected_files)
    reader.SetFileName(selected_files[current_index])
    reader.Update()
    ax.imshow(itk.GetArrayFromImage(reader.GetOutput()), cmap="gray")
    fig.canvas.draw()

fig.canvas.mpl_connect('key_press_event', on_key)
fig.canvas.mpl_connect('button_press_event', on_click)
plt.show()