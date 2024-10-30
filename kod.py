import itk
import numpy as np
import matplotlib.pyplot as plt

itk_image = itk.imread("MRBRAIN.DCM")

array_copy = itk.array_from_image(itk_image)

array_copy = np.squeeze(array_copy)

plt.imshow(array_copy, cmap='Greys')
plt.axis('off')
plt.show()