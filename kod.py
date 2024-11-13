import matplotlib.pyplot as plt
import pydicom as dicom
import os

folder_path = 'G:/Edukacja/2020 Studia/Semestr 9/POMwJO/Projekt/BT/KARY1/A/A/A/D'
dicom_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
dicom_files.sort()

current_index = 0

def show_image(index):
    file_path = os.path.join(folder_path, dicom_files[index])
    dicom_image = dicom.dcmread(file_path)
    image_data = dicom_image.pixel_array

    plt.imshow(image_data, cmap="gray")
    plt.axis("off")
    plt.title(f"Obraz {index + 1}/{len(dicom_files)}")
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