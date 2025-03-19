import streamlit as st
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import base64
import os
from datetime import datetime
import requests
from io import BytesIO

# Add Unsplash API credentials
UNSPLASH_ACCESS_KEY = "BY4XWv6ftfctGaEYU86fUs-RI1Kyfunpxj9mR2g4JAo"

def search_unsplash_images(query, per_page=10):
    """Search for images on Unsplash."""
    try:
        url = f"https://api.unsplash.com/search/photos"
        headers = {
            "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}",
            "Accept-Version": "v1"
        }
        params = {
            "query": query,
            "per_page": per_page
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
    except Exception as e:
        st.error(f"Error searching images: {str(e)}")
        return []

def load_image(image_file):
    img = Image.open(image_file)
    return img

def apply_filters(image, brightness=1.0, contrast=1.0, exposure=1.0, blur=0, sharpness=1.0, noise=0, hue=0, saturation=1.0, value=1.0):
    """Apply filters using PIL instead of OpenCV."""
    # Convert PIL Image to numpy array
    img_array = np.array(image)
    
    # Apply brightness, contrast, and exposure
    img = Image.fromarray(img_array)
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    
    # Apply blur
    if blur > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))
    
    # Apply sharpness
    if sharpness > 1.0:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)
    
    # Apply noise
    if noise > 0:
        noise_array = np.random.normal(0, noise, img_array.shape).astype(np.uint8)
        img_array = np.clip(img_array + noise_array, 0, 255)
        img = Image.fromarray(img_array)
    
    # Apply color adjustments
    img = ImageEnhance.Color(img).enhance(saturation)
    
    # Convert to HSV-like color space and adjust hue
    if hue != 0:
        img_array = np.array(img)
        hsv = rgb_to_hsv(img_array)
        hsv[:, :, 0] = (hsv[:, :, 0] + hue/180) % 1.0
        img_array = hsv_to_rgb(hsv)
        img = Image.fromarray(img_array.astype(np.uint8))
    
    # Apply value (brightness in HSV)
    if value != 1.0:
        img_array = np.array(img)
        hsv = rgb_to_hsv(img_array)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * value, 0, 1)
        img_array = hsv_to_rgb(hsv)
        img = Image.fromarray(img_array.astype(np.uint8))
    
    return img

def rgb_to_hsv(rgb):
    """Convert RGB to HSV color space."""
    rgb = rgb.astype(np.float32) / 255.0
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    
    max_rgb = np.maximum(np.maximum(r, g), b)
    min_rgb = np.minimum(np.minimum(r, g), b)
    diff = max_rgb - min_rgb
    
    h = np.zeros_like(r)
    s = np.zeros_like(r)
    v = max_rgb
    
    # Calculate hue
    mask = diff != 0
    h[mask] = np.where(max_rgb[mask] == r[mask],
                      (60 * ((g[mask] - b[mask]) / diff[mask]) + 360) % 360,
                      np.where(max_rgb[mask] == g[mask],
                              (60 * ((b[mask] - r[mask]) / diff[mask]) + 120) % 360,
                              (60 * ((r[mask] - g[mask]) / diff[mask]) + 240) % 360))
    
    # Calculate saturation
    s = np.where(max_rgb != 0, diff / max_rgb, 0)
    
    return np.stack([h/360, s, v], axis=-1)

def hsv_to_rgb(hsv):
    """Convert HSV to RGB color space."""
    h, s, v = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
    h = h * 360
    
    c = v * s
    x = c * (1 - np.abs((h / 60) % 2 - 1))
    m = v - c
    r = np.zeros_like(h)
    g = np.zeros_like(h)
    b = np.zeros_like(h)
    
    mask = (h >= 0) & (h < 60)
    r[mask] = c[mask]
    g[mask] = x[mask]
    b[mask] = 0
    
    mask = (h >= 60) & (h < 120)
    r[mask] = x[mask]
    g[mask] = c[mask]
    b[mask] = 0
    
    mask = (h >= 120) & (h < 180)
    r[mask] = 0
    g[mask] = c[mask]
    b[mask] = x[mask]
    
    mask = (h >= 180) & (h < 240)
    r[mask] = 0
    g[mask] = x[mask]
    b[mask] = c[mask]
    
    mask = (h >= 240) & (h < 300)
    r[mask] = x[mask]
    g[mask] = 0
    b[mask] = c[mask]
    
    mask = (h >= 300) & (h < 360)
    r[mask] = c[mask]
    g[mask] = 0
    b[mask] = x[mask]
    
    rgb = np.stack([r, g, b], axis=-1)
    rgb = (rgb + m[:, :, np.newaxis]) * 255
    return np.clip(rgb, 0, 255)

def delete_work(original_file, edited_file):
    """Delete a pair of original and edited images."""
    try:
        os.remove(f"user_works/{original_file}")
        os.remove(f"user_works/{edited_file}")
        return True
    except Exception as e:
        print(f"Error deleting files: {e}")
        return False

def get_image_comparison_html(original_path, edited_path, author_name="John Doe", file_id=None):
    return f"""
    <div class="image-comparison-container">
        <div class="image-column">
            <div class="image-wrapper">
                <img src="data:image/png;base64,{base64.b64encode(open(original_path, 'rb').read()).decode()}" 
                     class="comparison-image">
            </div>
            <div class="image-caption">Original Image</div>
        </div>
        <div class="image-column">
            <div class="image-wrapper">
                <img src="data:image/png;base64,{base64.b64encode(open(edited_path, 'rb').read()).decode()}" 
                     class="comparison-image">
            </div>
            <div class="image-caption">Edited Image</div>
        </div>
    </div>
    """

def save_user_work(original_image, edited_image):
    # Create user_works directory if it doesn't exist
    if not os.path.exists("user_works"):
        os.makedirs("user_works")
    
    # Generate unique filename using timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    original_path = f"user_works/original_{timestamp}.png"
    edited_path = f"user_works/edited_{timestamp}.png"
    
    # Save both original and edited images
    original_image.save(original_path)
    edited_image.save(edited_path)
    
    return original_path, edited_path

def home_page():
    st.markdown("""
        <style>
            .stApp {
                background-color: #000000;
                color: #FFFFFF;
            }
            .stTitle {
                color: #FFFFFF !important;
                font-family: 'Helvetica Neue', sans-serif;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            .stMarkdown {
                color: #FFFFFF !important;
                font-family: 'Helvetica Neue', sans-serif;
            }
            .image-comparison-container {
                display: flex;
                justify-content: space-between;
                margin-bottom: 40px;
                width: 100%;
                gap: 30px;
                background-color: rgba(128, 128, 128, 0.05);
                padding: 20px;
                border-radius: 15px;
                border: 1px solid rgba(128, 128, 128, 0.2);
            }
            .image-column {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .image-wrapper {
                position: relative;
                width: 100%;
                padding-top: 100%;
                overflow: hidden;
                margin-bottom: 15px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(26, 174, 130, 0.8);
            }
            .comparison-image {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: cover;
                transition: transform 0.3s ease;
            }
            .image-wrapper:hover .comparison-image {
                transform: scale(1.05);
            }
            .image-caption {
                color: #808080;
                font-size: 1.2em;
                margin-bottom: 8px;
                font-weight: 500;
            }
            .author-name {
                color: #808080;
                font-size: 1.3em;
                font-weight: 600;
                margin: 15px 0;
                padding: 5px 15px;
                background-color: rgba(128, 128, 128, 0.1);
                border-radius: 20px;
            }
            .like-button {
                background: rgba(128, 128, 128, 0.2);
                border: 2px solid #808080;
                color: #808080;
                padding: 10px 20px;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
                font-weight: 500;
            }
            .like-button:hover {
                background: rgba(0, 255, 0, 0.4);
                transform: translateY(-2px);
            }
            .like-button.liked {
                background: #00ff00;
                color: #000000;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.title("Welcome to Online Photo Editor")
    st.markdown("""
        <div style='background-color: rgba(26, 174, 130, 0.8); padding: 20px; border-radius: 10px; margin: 20px 0;'>
            <p style='color: #ffffff; font-size: 1.1em; line-height: 1.6;'>
                Edit your images with ease using our powerful tools inspired by Lightroom. 
                Create stunning visuals with professional-grade editing capabilities.
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("Works Done in Lightroom")
    
    # Use placeholder images from Unsplash for the homepage
    placeholder_images = [
        ("https://images.unsplash.com/photo-1506744038136-46273834b3fb", "Nature Photography"),
        ("https://images.unsplash.com/photo-1516035069371-29a1b244cc32", "Portrait Photography"),
        ("https://images.unsplash.com/photo-1492691527719-9d1e07e534b4", "Street Photography"),
        ("https://images.unsplash.com/photo-1501785888041-af3ef285b470", "Landscape Photography"),
        ("https://images.unsplash.com/photo-1511379938547-c1f69419868d", "Architecture Photography"),
        ("https://images.unsplash.com/photo-1516035069371-29a1b244cc32", "Fashion Photography")
    ]
    
    # Display each pair of images
    for i, (url, title) in enumerate(placeholder_images, 1):
        try:
            # Load the image from URL
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            
            # Create a slightly edited version for comparison
            edited_img = apply_filters(img, 
                                    brightness=1.1,
                                    contrast=1.1,
                                    sharpness=1.1,
                                    saturation=1.1)
            
            # Save temporarily
            temp_original = f"temp_original_{i}.png"
            temp_edited = f"temp_edited_{i}.png"
            img.save(temp_original)
            edited_img.save(temp_edited)
            
            # Display the comparison
            st.markdown(get_image_comparison_html(
                temp_original, 
                temp_edited,
                title
            ), unsafe_allow_html=True)
            
            # Clean up temporary files
            os.remove(temp_original)
            os.remove(temp_edited)
            
        except Exception as e:
            st.warning(f"Could not load image {i}. Please try refreshing the page.")
            continue

def load_image_from_url(url):
    """Load an image from a URL."""
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        return img
    except Exception as e:
        st.error(f"Error loading image from URL: {str(e)}")
        return None

def editor_page():
    st.markdown("""
        <style>
            .editor-container {
                background-color: rgba(26, 174, 130, 0.8);
                border-radius: 15px;
                padding: 20px;
                margin-bottom: 20px;
                border: 1px solid rgba(0, 255, 0, 0.2);
            }
            .editor-section {
                margin-bottom: 30px;
                background-color: rgba(0, 255, 0, 0.05);
                border-radius: 10px;
                padding: 15px;
                border: 1px solid rgba(0, 255, 0, 0.2);
            }
            .editor-section-title {
                color: #00ff00;
                font-size: 1.2em;
                font-weight: 600;
                margin-bottom: 15px;
                padding-bottom: 8px;
                border-bottom: 2px solid rgba(0, 255, 0, 0.2);
            }
            .stSlider > div > div > div {
                background-color: transparent;
            }
            .stSlider > div > div > div > div {
                background-color: transparent;
            }
            .stSlider > div > div > div > div > div {
                background-color: transparent;
            }
            .preview-container {
                display: flex;
                gap: 20px;
                margin: 20px 0;
            }
            .preview-column {
                flex: 1;
                text-align: center;
            }
            .preview-image {
                width: 100%;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 255, 0, 0.2);
            }
            .preview-caption {
                color: #00ff00;
                margin-top: 10px;
                font-weight: 500;
            }
            .slider-container {
                margin-bottom: 15px;
            }
            .slider-label {
                color: #808080;
                font-size: 0.9em;
                margin-bottom: 5px;
            }
            .dropdown-container {
                margin-bottom: 15px;
            }
            .dropdown-label {
                color: #808080;
                font-size: 0.9em;
                margin-bottom: 5px;
            }
            .stSelectbox > div > div {
                background-color: rgba(0, 255, 0, 0.1);
                border: 1px solid rgba(0, 255, 0, 0.2);
                border-radius: 5px;
            }
            .stSelectbox > div > div:hover {
                border-color: #00ff00;
            }
            .url-input-container {
                background-color: rgba(0, 255, 0, 0.05);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 20px;
                border: 1px solid rgba(0, 255, 0, 0.2);
            }
            .url-input-label {
                color: #00ff00;
                font-size: 1.1em;
                margin-bottom: 10px;
            }
            .stTextInput > div > div > input {
                background-color: rgba(0, 255, 0, 0.1);
                border: 1px solid rgba(0, 255, 0, 0.2);
                color: #00ff00;
            }
            .stTextInput > div > div > input:focus {
                border-color: #00ff00;
            }
            .search-container {
                background-color: rgba(0, 255, 0, 0.05);
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 20px;
                border: 1px solid rgba(0, 255, 0, 0.2);
            }
            .search-label {
                color: #00ff00;
                font-size: 1.1em;
                margin-bottom: 10px;
            }
            .image-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .search-result-image {
                width: 100%;
                height: 200px;
                object-fit: cover;
                border-radius: 8px;
                cursor: pointer;
                transition: transform 0.3s ease;
            }
            .search-result-image:hover {
                transform: scale(1.05);
            }
            .image-credit {
                color: #808080;
                font-size: 0.8em;
                margin-top: 5px;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='color: rgba(26, 174, 130, 0.8);'>Online Photo Editor</h1>", unsafe_allow_html=True)
    st.write("Upload an image or enter an image URL to enhance it using our professional editing tools.")
    
    # Search Section
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    st.markdown('<div class="search-label">Search Online Images</div>', unsafe_allow_html=True)
    search_query = st.text_input("", placeholder="Search for images...", key="search_input")
    
    if search_query:
        with st.spinner("Searching for images..."):
            photos = search_unsplash_images(search_query)
            
            if photos:
                # Create a grid of 3 columns
                cols = st.columns(3)
                
                # Display images in groups of 3
                for i in range(0, len(photos), 3):
                    # Get up to 3 photos for this row
                    row_photos = photos[i:i+3]
                    
                    # Create columns for this row
                    for j, photo in enumerate(row_photos):
                        with cols[j]:
                            st.image(photo["urls"]["regular"], 
                                   caption=f"By {photo['user']['name']}", 
                                   use_container_width=True)
                            if st.button("Edit This Image", key=f"edit_{photo['id']}"):
                                image = load_image_from_url(photo["urls"]["regular"])
                                if image:
                                    st.session_state.current_image = image
                                    st.session_state.image_source = "search"
                                    st.rerun()
            else:
                st.warning("No images found. Try a different search term.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Or upload your own image
    st.write("Or upload your own image:")
    uploaded_file = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png"])
    
    # Load image from either search or upload
    image = None
    if 'current_image' in st.session_state and st.session_state.image_source == "search":
        image = st.session_state.current_image
    elif uploaded_file is not None:
        image = load_image(uploaded_file)
        st.session_state.image_source = "upload"
    
    if image is not None:
        # Initialize session state for filters if not exists
        if 'filters' not in st.session_state:
            st.session_state.filters = {
                'brightness': 1.0,
                'contrast': 1.0,
                'exposure': 1.0,
                'blur': 0,
                'sharpness': 1.0,
                'noise': 0,
                'hue': 0,
                'saturation': 1.0,
                'value': 1.0
            }
        
        # Display original and edited images
        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption='Original Image', use_container_width=True)
        
        # Create three columns for the editing sections
        detail_col, color_col, light_col = st.columns(3)
        
        # Detail Section
        with detail_col:
            st.markdown('<div class="editor-section-title">Detail Adjustments</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="dropdown-container">', unsafe_allow_html=True)
            st.markdown('<div class="dropdown-label">Select Detail Adjustment</div>', unsafe_allow_html=True)
            detail_option = st.selectbox("", ["Sharpness", "Blur", "Noise"], key="detail_dropdown")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if detail_option == "Sharpness":
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Sharpness</div>', unsafe_allow_html=True)
                st.session_state.filters['sharpness'] = st.slider("", 0.0, 2.0, st.session_state.filters['sharpness'], 0.1, key="sharpness_slider")
                st.markdown('</div>', unsafe_allow_html=True)
            elif detail_option == "Blur":
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Blur</div>', unsafe_allow_html=True)
                st.session_state.filters['blur'] = st.slider("", 0, 10, st.session_state.filters['blur'], 1, key="blur_slider")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Noise</div>', unsafe_allow_html=True)
                st.session_state.filters['noise'] = st.slider("", 0, 50, st.session_state.filters['noise'], 1, key="noise_slider")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Color Section
        with color_col:
            st.markdown('<div class="editor-section-title">Color Adjustments</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="dropdown-container">', unsafe_allow_html=True)
            st.markdown('<div class="dropdown-label">Select Color Adjustment</div>', unsafe_allow_html=True)
            color_option = st.selectbox("", ["Hue", "Saturation", "Value"], key="color_dropdown")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if color_option == "Hue":
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Hue</div>', unsafe_allow_html=True)
                st.session_state.filters['hue'] = st.slider("", -50, 50, st.session_state.filters['hue'], 1, key="hue_slider")
                st.markdown('</div>', unsafe_allow_html=True)
            elif color_option == "Saturation":
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Saturation</div>', unsafe_allow_html=True)
                st.session_state.filters['saturation'] = st.slider("", 0.0, 2.0, st.session_state.filters['saturation'], 0.1, key="saturation_slider")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Value</div>', unsafe_allow_html=True)
                st.session_state.filters['value'] = st.slider("", 0.0, 2.0, st.session_state.filters['value'], 0.1, key="value_slider")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Light Section
        with light_col:
            st.markdown('<div class="editor-section-title">Light Adjustments</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="dropdown-container">', unsafe_allow_html=True)
            st.markdown('<div class="dropdown-label">Select Light Adjustment</div>', unsafe_allow_html=True)
            light_option = st.selectbox("", ["Brightness", "Contrast", "Exposure"], key="light_dropdown")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if light_option == "Brightness":
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Brightness</div>', unsafe_allow_html=True)
                st.session_state.filters['brightness'] = st.slider("", 0.0, 2.0, st.session_state.filters['brightness'], 0.1, key="brightness_slider")
                st.markdown('</div>', unsafe_allow_html=True)
            elif light_option == "Contrast":
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Contrast</div>', unsafe_allow_html=True)
                st.session_state.filters['contrast'] = st.slider("", 0.5, 3.0, st.session_state.filters['contrast'], 0.1, key="contrast_slider")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="slider-container">', unsafe_allow_html=True)
                st.markdown('<div class="slider-label">Exposure</div>', unsafe_allow_html=True)
                st.session_state.filters['exposure'] = st.slider("", 0.0, 2.0, st.session_state.filters['exposure'], 0.1, key="exposure_slider")
                st.markdown('</div>', unsafe_allow_html=True)
        
        # Apply filters and show result
        edited_image = apply_filters(
            image,
            brightness=st.session_state.filters['brightness'],
            contrast=st.session_state.filters['contrast'],
            exposure=st.session_state.filters['exposure'],
            blur=st.session_state.filters['blur'],
            sharpness=st.session_state.filters['sharpness'],
            noise=st.session_state.filters['noise'],
            hue=st.session_state.filters['hue'],
            saturation=st.session_state.filters['saturation'],
            value=st.session_state.filters['value']
        )
        
        with col2:
            st.image(edited_image, caption='Edited Image', use_container_width=True)
        
        # Action buttons
        col3, col4 = st.columns(2)
        with col3:
            if st.button("Save Work", type="primary", key="save_work_button"):
                original_path, edited_path = save_user_work(image, edited_image)
                st.success("Your work has been saved!")
        
        with col4:
            edited_image.save("edited_image.png")
            with open("edited_image.png", "rb") as file:
                st.download_button(label="Download Edited Image", data=file, file_name="edited_image.png", mime="image/png", key="download_button")

def your_works_page():
    st.markdown("<h1 style='color: rgba(26, 174, 130, 0.8);'>Your Works</h1>", unsafe_allow_html=True)
    st.write("View all your previously edited images.")
    
    st.markdown("""
        <style>
            .image-comparison-container {
                display: flex;
                justify-content: space-between;
                margin-bottom: 30px;
                width: 100%;
                gap: 20px;
                position: relative;
            }
            .image-column {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
            }
            .image-wrapper {
                position: relative;
                width: 100%;
                padding-top: 100%;
                overflow: hidden;
                margin-bottom: 10px;
            }
            .comparison-image {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .image-caption {
                color: #00ff00;
                font-size: 1.1em;
                margin-bottom: 5px;
            }
            .author-name {
                color: #00ff00;
                font-size: 1.2em;
                font-weight: bold;
                margin: 10px 0;
            }
            .delete-button {
                background-color: #ff3b3b;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 20px;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
                font-weight: 500;
                width: 100%;
                text-align: center;
            }
            .delete-button:hover {
                background-color: #ff0000;
                transform: translateY(-2px);
            }
            .delete-container {
                width: 100%;
                display: flex;
                justify-content: center;
                margin-top: 10px;
            }
        </style>
    """, unsafe_allow_html=True)
    
    if os.path.exists("user_works"):
        # Get all user work files
        files = os.listdir("user_works")
        original_files = [f for f in files if f.startswith("original_")]
        edited_files = [f for f in files if f.startswith("edited_")]
        
        # Sort files by timestamp
        original_files.sort(reverse=True)
        edited_files.sort(reverse=True)
        
        # Display each pair of images with delete button
        for i in range(len(original_files)):
            # Display images
            st.markdown(get_image_comparison_html(
                f"user_works/{original_files[i]}", 
                f"user_works/{edited_files[i]}"
            ), unsafe_allow_html=True)
            
            # Add delete button
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🗑️ Delete", key=f"delete_{i}", type="primary"):
                    if delete_work(original_files[i], edited_files[i]):
                        st.success("Images deleted successfully!")
                        st.rerun()
                    else:
                        st.error("Error deleting images. Please try again.")
            
            # Add separator
            st.markdown("<hr style='border: 1px solid rgba(26, 174, 130, 0.3); margin: 30px 0;'>", unsafe_allow_html=True)
    else:
        st.write("No works saved yet. Start editing images in the Create page!")

def contacts_page():
    st.title("Contact Us")
    st.write("For any inquiries, reach out to us at: support@photoeditor.com")

def main():
    st.markdown("""
        <style>
            /* Main App Styling */
            .stApp {
                background-color: #000000;
                color: #00ff00;
            }
            .stTitle {
                color: #FFFFFF !important;
                font-family: 'Helvetica Neue', sans-serif;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            .stMarkdown {
                color: #FFFFFF !important;
                font-family: 'Helvetica Neue', sans-serif;
            }
            
            /* Sidebar Styling */
            .css-1d391kg {
                background-color: #000000 !important;
            }
            .sidebar .sidebar-content {
                background-color: #000000 !important;
                padding: 2rem 1rem;
            }
            .sidebar .sidebar-content .element-container {
                color: #00ff00;
                margin-bottom: 1.5rem;
            }
            .sidebar .sidebar-content .stRadio > div {
                background-color: #000000;
                border-radius: 10px;
                padding: 0.5rem;
            }
            .sidebar .sidebar-content .stRadio > div > div {
                background-color: #000000;
            }
            .sidebar .sidebar-content .stRadio > div > div > div {
                background-color: rgba(0, 255, 0, 0.1);
                border-radius: 8px;
                padding: 0.8rem 1.2rem;
                margin: 0.25rem;
                transition: all 0.3s ease;
                border: 1px solid rgba(0, 255, 0, 0.2);
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .sidebar .sidebar-content .stRadio > div > div > div:hover {
                background-color: rgba(0, 255, 0, 0.2);
                transform: translateX(5px);
                border-color: #00ff00;
            }
            .sidebar .sidebar-content .stRadio > div > div > div[data-testid="stRadio"] {
                background-color: rgba(0, 255, 0, 0.3);
                color: #00ff00;
                font-weight: 600;
                border-color: #00ff00;
            }
            .sidebar .sidebar-content .stRadio > div > div > div[data-testid="stRadio"]:before {
                content: '';
                display: inline-block;
                width: 20px;
                height: 20px;
                background-color: #00ff00;
                border-radius: 50%;
                margin-right: 10px;
            }
            
            /* Logo Styling */
            .logo-container {
                text-align: center;
                padding: 1rem 0;
                margin-bottom: 2rem;
                border-bottom: 1px solid rgba(0, 255, 0, 0.2);
            }
            .logo-circle {
                width: 80px;
                height: 80px;
                background: linear-gradient(135deg, rgba(0, 255, 0, 0.2), rgba(0, 255, 0, 0.1));
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 1rem;
                border: 2px solid rgba(0, 255, 0, 0.3);
            }
            .logo-icon {
                font-size: 2.5rem;
                color: #00ff00;
            }
            .logo-text {
                font-size: 1.5rem;
                font-weight: 600;
                color: rgba(26, 174, 130, 0.8);
                margin-bottom: 0.5rem;
                letter-spacing: 1px;
            }
            .logo-tagline {
                font-size: 0.9rem;
                color: rgba(0, 255, 0, 0.7);
                letter-spacing: 0.5px;
            }
            
            /* Slider Styling */
            .stSlider > div > div > div {
                background-color: #00ff00;
            }
            .stSlider > div > div > div > div {
                background-color: #00ff00;
            }
            .stSlider > div > div > div > div > div {
                background-color: #00ff00;
            }
            
            /* Button Styling */
            .stButton > button {
                background-color: rgba(26, 174, 130, 0.8);
                color: #000000;
                border: none;
                padding: 0.75rem 1.5rem;
                border-radius: 25px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(26, 174, 130, 0.8);
            }
            .stButton > button:hover {
                background-color: #00cc00;
                transform: translateY(-2px);
                box-shadow: 0 6px 8px rgba(0, 255, 0, 0.3);
            }
            
            /* File Uploader Styling */
            .stFileUploader > div {
                border: 2px dashed #00ff00;
                border-radius: 10px;
                padding: 1rem;
                background-color:rgba(26, 174, 130, 0.8);
            }
            .stFileUploader > div:hover {
                border-color: #00cc00;
                background-color: rgba(0, 255, 0, 0.1);
            }
            
            /* Success Message Styling */
            .stSuccess {
                background-color: rgba(26, 174, 130, 0.8);
                border-radius: 10px;
                padding: 1rem;
                border: 1px solid #00ff00;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Add Logo Section
    st.sidebar.markdown("""
        <div class="logo-container">
            <div class="logo-circle">
                <div class="logo-icon">📸</div>
            </div>
            <div class="logo-text">Photo Editor</div>
            <div class="logo-tagline" style="color: #FFFFFF;">Professional Image Editing</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Navigation Menu with Icons
    st.sidebar.markdown("""
        <style>
            .nav-item {
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 12px 15px;
                margin: 5px 0;
                border-radius: 8px;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .nav-item:hover {
                background-color:rgba(26, 174, 130, 0.8);
            }
            .nav-item.active {
                background-color: rgba(26, 174, 130, 0.8);
                border-left: 3px solid #00ff00;
            }
            .nav-icon {
                font-size: 1.2em;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Navigation Menu
    page = st.sidebar.radio("", ["Home", "Create", "Your Works", "Contacts"])
    
    if page == "Home":
        home_page()
    elif page == "Create":
        editor_page()
    elif page == "Your Works":
        your_works_page()
    elif page == "Contacts":
        contacts_page()

if __name__ == "__main__":
    main()
