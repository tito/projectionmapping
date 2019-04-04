import sys
sys.path += ["."]
from kivy.app import App
from projectionmapping import ProjectionMapping
from kivy.uix.image import Image


class SimpleProjectionMapping(App):
    def build(self):
        self.root = ProjectionMapping(filename="calibration.json")
        self.root.add_widget(
            Image(source="projectionmapping/data/mirefullhd.jpg"))

if __name__ == "__main__":
    SimpleProjectionMapping().run()