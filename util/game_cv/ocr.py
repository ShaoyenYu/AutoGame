import cv2
import pytesseract


def ocr_preprocess(img, k_size=(3, 3)):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, k_size, 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Morph open to remove noise
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, k_size)
    final = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    return final


def ocr_int(img, config, lang="eng", preprocess=None):
    if preprocess is not None:
        img = ocr_preprocess(img)
    data = pytesseract.image_to_string(img, lang=lang, config=config)
    return data
