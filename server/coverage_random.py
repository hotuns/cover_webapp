import pandas as pd
import numpy as np
import os
import joblib
from PIL import Image


def image_to_dataframe(image_path):
    img = Image.open(image_path)
    img_rgb = img.convert("RGB")
    r, g, b = img_rgb.split()
    r_array = np.array(r)
    g_array = np.array(g)
    b_array = np.array(b)
    df = pd.DataFrame({'R': r_array.flatten(), 'G': g_array.flatten(), 'B': b_array.flatten()})
    return df


def calculate_new_columns(df):
    epsilon = 1e-10
    df['R'] = df['R'].replace(0, epsilon)
    df['G'] = df['G'].replace(0, epsilon)
    df['B'] = df['B'].replace(0, epsilon)
    df['R'] = df['R'].astype(float)
    df['G'] = df['G'].astype(float)
    df['B'] = df['B'].astype(float)

    df['rr'] = 3 * df['R'] / (df['R'] + df['G'] + df['B'])
    df['rg'] = 3 * df['G'] / (df['R'] + df['G'] + df['B'])
    df['rb'] = 3 * df['B'] / (df['R'] + df['G'] + df['B'])
    df['gr_ratio'] = df['G'] / df['R']
    df['gb_ratio'] = df['G'] / df['B']
    df['br_ratio'] = df['B'] / df['R']
    return df


def predict_with_rf(df, model_path='random_forest_model.joblib'):
    loaded_rf = joblib.load(model_path)
    feature_columns = ['R', 'G', 'B', 'rr', 'rg', 'rb', 'gr_ratio', 'gb_ratio', 'br_ratio']
    X = df[feature_columns]
    predictions = loaded_rf.predict(X)
    df['predicted_class'] = predictions
    return df


def colorize_and_reconstruct(df, shape):
    predicted_class = df['predicted_class'].values.reshape(shape)
    colored_image = np.zeros((shape[0], shape[1], 3), dtype=np.uint8)
    colored_image[predicted_class == 'veg'] = [0, 255, 0]
    colored_image[predicted_class == 'non_veg'] = [255, 255, 0]
    result_image = Image.fromarray(colored_image)
    return result_image


def calculate_veg_ratio(df, shape):
    predicted_class = df['predicted_class'].values.reshape(shape)
    veg_pixels = np.sum(predicted_class == 'veg')
    total_pixels = predicted_class.size
    veg_ratio = veg_pixels / total_pixels
    print(f"Veg ratio for image: {veg_ratio}")
    return veg_ratio


def process_directory(input_dir, output_dir, model_path='random_forest_model.joblib', endmembers=None):
    results = []
    csv_path = os.path.join(output_dir, 'veg_proportions.csv')
    if os.path.exists(csv_path):
        os.remove(csv_path)

    for image_name in os.listdir(input_dir):
        if image_name.endswith(('.jpg', '.png', '.jpeg')):
            image_path = os.path.join(input_dir, image_name)
            img = Image.open(image_path)
            img_rgb = img.convert("RGB")
            r, g, b = img_rgb.split()
            r_array = np.array(r)
            g_array = np.array(g)
            b_array = np.array(b)
            df = pd.DataFrame({'R': r_array.flatten(), 'G': g_array.flatten(), 'B': b_array.flatten()})
            df = calculate_new_columns(df)
            df = predict_with_rf(df, model_path)

            shape = img_rgb.size[::-1]
            colored_image = colorize_and_reconstruct(df, shape)
            colored_image.save(os.path.join(output_dir, f'colored_{image_name}'))

            veg_ratio = calculate_veg_ratio(df, shape)
            results.append({'image': image_name, 'result': veg_ratio})

            results_df = pd.DataFrame(results)
            results_df.to_csv(csv_path, index=False)


input_directory = r"C:\Users\jiayu\Desktop\test"
output_directory = r"C:\Users\jiayu\Desktop\result"

process_directory(input_directory, output_directory)
