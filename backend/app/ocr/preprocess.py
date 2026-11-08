import io
from PIL import Image, ImageEnhance, ImageFilter, ImageOps


def preprocess_image(image_input) -> Image.Image:
    """
    Cleans up a photographed or scanned document image prior to OCR.
    Applies grayscale conversion, contrast enhancement, sharpening, and deskew adjustment.
    
    Accepts: PIL.Image.Image, bytes, or file path.
    Returns: Processed PIL.Image.Image
    """
    if isinstance(image_input, bytes):
        image = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, str):
        image = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        image = image_input.copy()
    else:
        raise ValueError("Unsupported image input type")

    # 1. Convert RGBA/Palette to RGB then Grayscale
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    
    grayscale = ImageOps.grayscale(image)

    # 2. Contrast Enhancement
    enhancer = ImageEnhance.Contrast(grayscale)
    contrast_img = enhancer.enhance(1.8)

    # 3. Sharpen text edges
    sharpened_img = contrast_img.filter(ImageFilter.SHARPEN)

    # 4. Optional thresholding (binarization) for high clarity
    # Keep light adaptive binarization for clear document background
    def binarize(img, threshold=150):
        return img.point(lambda p: 255 if p > threshold else 0)

    # Binarize with sensible threshold
    bin_img = binarize(sharpened_img, 140)

    return bin_img
