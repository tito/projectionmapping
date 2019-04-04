# Projection Mapping

Kivy widget that reproject its content according to a calibration grid.
It includes a calibration tool accessible from F2.

<img width="1072" alt="screenshot_projectionmapping" src="https://user-images.githubusercontent.com/37904/55543247-faa3d680-56c8-11e9-9054-dbc6cd2b8c21.png">

## Usage

```python
from kivy.app import App
from projectionmapping import ProjectionMapping
from kivy.uix.image import Image

class SimpleProjectionMapping(App):
    def build(self):
        self.root = ProjectionMapping(filename="calibration.json")
        self.root.add_widget(
            Image(source="projectionmapping/data/mirefullhd.jpg"))
```

## Keybinding

- F2: Toggle calibration
- space: Toggle help
- r: Reset the calibration grid
- s: Save the current calibration
- l: Load latest calibration
- x/c: Remove/add a column (current calibration is lost)
- v/b: Remove/add a row (current calibration is lost)

## Resources

- http://www.reedbeta.com/blog/quadrilateral-interpolation-part-2/
- http://iquilezles.org/www/articles/ibilinear/ibilinear.htm
