import itk
import itk.itkBinaryThresholdImageFilterPython
import matplotlib.pyplot as plt
import os

folder_path = "X:/Piotrek/Studia Magisterka/SEMESTR 2/Przetwarzanie Obrazow Medycznych w Jezykach Obiektowych/BT/BT/KARY1/A/A/A/D"

dicom_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]

dicom_files.sort()

current_index = 0

lower_threshold = 1100
upper_threshold = 1979
outside_value = 0       
inside_value = 1

PixelType = itk.US
Dimension = 2

ImageType = itk.Image[PixelType, Dimension]

def show_image(index):
    reader = itk.ImageFileReader[ImageType].New()
    reader.SetFileName(dicom_files[index])

    thresholdFilter = itk.BinaryThresholdImageFilter[ImageType, ImageType].New()
    thresholdFilter.SetInput(reader.GetOutput())
    thresholdFilter.SetLowerThreshold(lower_threshold)
    thresholdFilter.SetUpperThreshold(upper_threshold)
    thresholdFilter.SetOutsideValue(outside_value)
    thresholdFilter.SetInsideValue(inside_value)
    thresholdFilter.Update()

    binary_image_data = itk.GetArrayFromImage(thresholdFilter.GetOutput())

    plt.imshow(binary_image_data, cmap="gray")
    plt.axis("off")
    plt.title(f"Obraz {index + 1}/{len(dicom_files)} - Binarizacja")
    plt.draw()

def on_key(event):
    global current_index
    if event.key == 'right':
        current_index = (current_index + 1) % len(dicom_files)
    elif event.key == 'left':
        current_index = (current_index - 1) % len(dicom_files)

    plt.clf()  
    show_image(current_index)

fig, ax = plt.subplots()
show_image(current_index)
fig.canvas.mpl_connect('key_press_event', on_key)
plt.show()