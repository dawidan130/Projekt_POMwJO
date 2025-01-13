import os
import sys
import itk
import vtk
import matplotlib.pyplot as plt
import argparse
import numpy as np

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

masks = []

# Rozrost regionu dynamiczny
def dynamic_region_growing(seed, image_files, dynamic_threshold=300):
    global masks
    masks = []

    for file in image_files:
        reader = itk.ImageFileReader[ImageType2D].New()
        reader.SetFileName(file)
        reader.Update()

        image = reader.GetOutput()
        image_array = itk.GetArrayFromImage(image)

        # Intensywność w punkcie początkowym (seed)
        intensity = image_array[seed[1], seed[0]]

        # Zakres globalny
        global_lower_threshold = 1000
        global_upper_threshold = 2000

        # Sprawdzamy, czy intensywność mieści się w zakresie globalnym
        if intensity < global_lower_threshold or intensity > global_upper_threshold:
            print(f"Intensywność {intensity} poza globalnym zakresem {global_lower_threshold}-{global_upper_threshold}. Rozrost pominięty.")
            masks.append(np.zeros_like(image_array))  # Dodajemy pustą maskę dla tego obrazu
            continue

        # Zakres dynamiczny
        dynamic_lower_threshold = max(0, intensity - dynamic_threshold)
        dynamic_upper_threshold = intensity + dynamic_threshold

        # Rozrost regionu w zakresie dynamicznym
        region_grow = itk.ConnectedThresholdImageFilter[ImageType2D, ImageType2D].New()
        region_grow.SetInput(image)
        region_grow.SetSeed(seed)
        region_grow.SetLower(int(dynamic_lower_threshold))
        region_grow.SetUpper(int(dynamic_upper_threshold))
        region_grow.Update()

        # Uzyskanie maski
        output_image = region_grow.GetOutput()
        output_array = itk.GetArrayFromImage(output_image)

        masks.append(output_array)  # Dodanie maski do wyników

# Zapis masek
def save_masks(output_dir="output_masks"):
    os.makedirs(output_dir, exist_ok=True)
    for i, mask in enumerate(masks):
        output_path = os.path.join(output_dir, f"mask_{i+1}.png")
        plt.imsave(output_path, mask, cmap="gray")

def get_voxel_spacing(dicom_file):
    dicomIO = itk.GDCMImageIO.New()
    reader = itk.ImageFileReader[ImageType2D].New()
    reader.SetFileName(dicom_file)
    reader.SetImageIO(dicomIO)
    reader.Update()

    # Pobranie spacing dla każdego wymiaru (0: X, 1: Y, 2: Z)
    spacing = tuple(dicomIO.GetSpacing(i) for i in range(3))

    return spacing

# Wizualizacja 3D VTK
def visualize_3d_vtk(selected_files, tumor_masks, voxel_spacing):
    # Wczytanie danych DICOM do vtkImageData
    dicom_reader = vtk.vtkImageData()
    dicom_reader.SetDimensions(len(selected_files), tumor_masks[0].shape[0], tumor_masks[0].shape[1])  # Z, Y, X order
    dicom_reader.SetSpacing(voxel_spacing)
    dicom_reader.AllocateScalars(vtk.VTK_UNSIGNED_SHORT, 1)

    for z, dicom_file in enumerate(selected_files):
        reader = itk.ImageFileReader[ImageType2D].New()
        reader.SetFileName(dicom_file)
        reader.Update()
        image_slice = itk.GetArrayFromImage(reader.GetOutput())

        # Przenoszenie danych pikseli do vtkImageData
        for y in range(image_slice.shape[0]):
            for x in range(image_slice.shape[1]):
                dicom_reader.SetScalarComponentFromDouble(x, y, z, 0, image_slice[y, x])

    # Wczytanie masek do vtkImageData
    tumor_image = vtk.vtkImageData()
    tumor_image.SetDimensions(dicom_reader.GetDimensions())
    tumor_image.SetSpacing(voxel_spacing)
    tumor_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)  # Binary mask

    for z, mask in enumerate(tumor_masks):
        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                value = 255 if mask[y, x] > 0 else 0
                tumor_image.SetScalarComponentFromDouble(x, y, z, 0, value)

    # Ekstrakcja powierzchni guza
    tumor_surface_extractor = vtk.vtkMarchingCubes()
    tumor_surface_extractor.SetInputData(tumor_image)
    tumor_surface_extractor.SetValue(0, 127)  # Prog dla binarnej maski
    tumor_surface_extractor.Update()

    tumor_mapper = vtk.vtkPolyDataMapper()
    tumor_mapper.SetInputConnection(tumor_surface_extractor.GetOutputPort())
    tumor_mapper.ScalarVisibilityOff()

    tumor_actor = vtk.vtkActor()
    tumor_actor.SetMapper(tumor_mapper)
    tumor_actor.GetProperty().SetColor(1.0, 0.0, 0.0)  # Czerwony
    tumor_actor.GetProperty().SetOpacity(1.0)

    # Ekstrakcja powierzchni ciała pacjenta
    body_surface_extractor = vtk.vtkMarchingCubes()
    body_surface_extractor.SetInputData(dicom_reader)
    body_surface_extractor.SetValue(0, 500)  # Próg dla powierzchni ciała (do regulacji)
    body_surface_extractor.Update()

    body_mapper = vtk.vtkPolyDataMapper()
    body_mapper.SetInputConnection(body_surface_extractor.GetOutputPort())
    body_mapper.ScalarVisibilityOff()

    body_actor = vtk.vtkActor()
    body_actor.SetMapper(body_mapper)
    body_actor.GetProperty().SetColor(0.8, 0.8, 0.8)  # Szary
    body_actor.GetProperty().SetOpacity(0.3)  # Półprzezroczysty

    # Renderer i interaktor
    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)

    render_interactor = vtk.vtkRenderWindowInteractor()
    render_interactor.SetRenderWindow(render_window)

    # Dodawanie aktorów do renderera
    renderer.AddActor(tumor_actor)
    renderer.AddActor(body_actor)
    renderer.SetBackground(0.1, 0.1, 0.1)  # Ciemnoszare tło

    # Ustawienia okna renderowania
    render_window.SetSize(800, 800)
    render_window.SetWindowName("3D Tumor Visualization")

    # Uruchamianie renderowania
    renderer.ResetCamera()
    render_window.Render()
    render_interactor.Start()

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
        
        # Wywołanie dynamicznego rozrostu regionu
        dynamic_region_growing(seed=(x, y), image_files=selected_files)
        
        # Zapisanie masek
        save_masks()

        # Pobranie voxel spacing
        #voxel_spacing = get_voxel_spacing(selected_files[0])

        # Wywołanie wizualizacji 3D z poprawnymi argumentami
        #visualize_3d_vtk(selected_files, masks, voxel_spacing)

def on_key(event):
    global current_index
    if event.key == 'right':
        current_index = (current_index + 1) % len(selected_files)
    elif event.key == 'left':
        current_index = (current_index - 1) % len(selected_files)
    show_image(current_index)

fig, ax = plt.subplots()
show_image(current_index)
fig.canvas.mpl_connect('key_press_event', on_key)
fig.canvas.mpl_connect('button_press_event', on_click)
plt.show()
