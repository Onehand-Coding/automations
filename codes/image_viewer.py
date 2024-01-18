import re
import time
import logging
import webbrowser
from datetime import date

import pyexiv2
from gmplot import gmplot
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from helper import get_folder_path, configure_logging, confirm, data_folder


class ImageFile:
    def __init__(self, image_path):
        self.image_path = image_path
        self.get_metadata()

    def get_metadata(self):
        with pyexiv2.Image(self.image_path) as image_info:
            self.metadata = image_info.read_exif()

    @property
    def device_model(self):
        return self.metadata.get('Exif.Image.Model')

    @property
    def device_make(self):
        return self.metadata.get('Exif.Image.Make')

    @property
    def date_taken(self):
        date_taken = self.metadata.get('Exif.Image.DateTime')
        if date_taken is None:
            return
        if not any(char.isalpha() for char in date_taken):
            try:
                date_taken = re.split(r'\s+|[:]', date_taken)
                year, month, day, *_ = [int(num) for num in date_taken]
                return date(year, month, day).strftime('%B %d, %Y')
            except ValueError:
                date_taken = int(date_taken[0]) / 1000
                return date.fromtimestamp(date_taken).strftime('%B %d, %Y')
        else:
            year, month, day, *_ = time.strptime(re.findall(r'\w+\s+\d+[,]\s+\d+', date_taken)[0], '%b %d, %Y')
            return date(year, month, day).strftime('%B %d, %Y')

    @property
    def coordinates(self):
        if 'Exif.GPSInfo.GPSLatitude' in self.metadata:
            latitude = self.metadata['Exif.GPSInfo.GPSLatitude']
            longitude = self.metadata['Exif.GPSInfo.GPSLongitude']

            latitude = [eval(values) for values in latitude.split()]
            latitude_deg = latitude[0] + latitude[1] / 60 + latitude[2] / 3600
            longitude = [eval(values) for values in longitude.split()]
            longitude_deg = longitude[0] + longitude[1] / 60 + longitude[2] / 3600

            return latitude_deg, longitude_deg

    @property
    def address(self):
        if self.coordinates:
            latitude, longitude = self.coordinates
            geolocator = Nominatim(user_agent="image_locator")
            try:
                location = geolocator.reverse((latitude, longitude), language='en')
                return location.address
            except GeocoderTimedOut:
                logging.error("Geocoding service timed out. Skipping address retrieval.")
                return None
            except GeocoderUnavailable:
                logging.error("Geocoding service unavailable. Skipping address retrieval.")
                return None
            except Exception as e:
                logging.error(f"Error during geocoding: {e}")
                return None
            finally:
                time.sleep(1)


def is_image(file):
    return file.is_file() and file.suffix.lower() in ('.jpg', 'jpeg', 'png')


def view_on_map(coordinates):
    lat, lon = coordinates
    gmap = gmplot.GoogleMapPlotter(lat, lon, 12)
    gmap.marker(lat, lon, 'cornflowerblue')
    gmap.draw(data_folder / 'location.html')

    webbrowser.open(str(data_folder) + 'location.html')


def get_from_folder(folder):
    image_files = [file for file in folder.rglob('*') if is_image(file)]
    for file in image_files:
        try:
            image = ImageFile(str(file))
            logging.info(f'Current image file: {file}')
            print(f'Date taken: {image.date_taken}')
            print(f'Device make: {image.device_make}')
            print(f'Device model: {image.device_model}')
            print(f'Coordinates: {image.coordinates}')
            print(f'address: {image.address}')
        except FileNotFoundError as e:
            logging.error(f'Skipping {file} error: {e}')
            continue
        except RuntimeError as e:
            logging.error(f'Skipping {file} error: {e}')
            continue


def get_from_file(image_file):
    if is_image(image_file):
        try:
            image = ImageFile(str(image_file))
            logging.info(f'Current image file: {image_file}')
            print(f'Date taken: {image.date_taken}')
            print(f'Device make: {image.device_make}')
            print(f'Device model: {image.device_model}')
            print(f'Coordinates: {image.coordinates}')
            print(f'address: {image.address}')
        except FileNotFoundError as e:
            logging.error(f'Error {image_file}: {e}')
        except RuntimeError as e:
            logging.error(f'Error {image_file}: {e}')

        if confirm('view location on map?'):
            view_on_map(image.coordinates)


def main():
    configure_logging()
    image_file = get_folder_path('file or folder you want to get image info.')

    if image_file.is_dir():
        get_from_folder(image_file)
    else:
        get_from_file(image_file)


# if __name__ == '__main__':
#     main()


from tkinter import Tk, Label, Button, filedialog
from PIL import Image, ImageTk

class ImageViewer:
    def __init__(self, master):
        self.master = master
        self.master.geometry('250x250')
        self.master.title("Image Viewer")

        self.image_path = None
        self.image = None
        self.image_label = Label(self.master)
        self.image_label.pack()

        self.load_button = Button(self.master, text="Open Image", command=self.load_image)
        self.load_button.pack()

    def load_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
        if file_path:
            self.image_path = file_path
            self.display_image()

    def display_image(self):
        if self.image_path:
            image = Image.open(self.image_path)
            # Resize the image to fit the window
            image = image.resize((400, 400), Image.Resampling.LANCZOS)
            self.image = ImageTk.PhotoImage(image)
            self.image_label.config(image=self.image)
            self.image_label.image = self.image


if __name__ == "__main__":
    root = Tk()
    app = ImageViewer(root)
    root.mainloop()
