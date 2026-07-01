# Automated-Face-Detection-and-Smoothing
An automated face detecting and smoothing pipeline

## Algorithm Outline
Step 1. Use OpenCV ResNet-10 face detector to detect all faces in the image

Step 2. Crop every detected face

Step 3: Select 4 locations on the face to estimate skin pixel value

Step 4: Convert face to HSV space, estimate skin color range and detect skin region mask (The hue value is within a small range which is easier for skin detection compared to working in BGR color space)

Step 5: Apply Gaussian filter and bilateral filter on the face crop (in BGR space) to smooth face

Step 6: Apply non-skin region pixel values back to the face

Step 7: Put the skin smoothed face back to the original image

## Input: image containing faces
![alt text](https://github.com/yyhz76/Automated-Face-Detection-and-Smoothing/blob/main/original_faces.png)  

## Output: automated face detection and smoothing
![alt text](https://github.com/yyhz76/Automated-Face-Detection-and-Smoothing/blob/main/smoothed_faces.png)
