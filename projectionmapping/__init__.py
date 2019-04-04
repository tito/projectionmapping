"""
Projection mapping
==================

.. author:: Mathieu Virbel <mat@meltingrocks.com>

Grid-based Inverse Bilinear Projection
"""

from kivy.factory import Factory as F
from kivy.properties import StringProperty, BooleanProperty
from kivy.graphics import (
    Fbo, Rectangle, Color, Mesh, PushMatrix, PopMatrix, Scale,
    Canvas, RenderContext, Translate)
from kivy.graphics.transformation import Matrix
from kivy.lang import Builder
from kivy.vector import Vector
import json

FS = '''
#ifdef GL_ES
    precision highp float;
#endif

/* Outputs from the vertex shader */
varying vec4 frag_color;
varying vec2 q, q0, b1, b2, b3, vsize;

/* uniform texture samplers */
uniform sampler2D texture0;
uniform mat4 frag_modelview_mat;

float Wedge2D(vec2 v, vec2 w) {
    return v.x * w.y - v.y * w.x;
}

void main (void){
    // Set up quadratic formula
    float A = Wedge2D(b2, b3);
    float B = Wedge2D(b3, q) - Wedge2D(b1, b2);
    float C = Wedge2D(b1, q);

    // Solve for v
    vec2 uv;
    if (abs(A) < 0.001) {
        // Linear form
        uv.y = -C / B;
    } else {
        // Quadratic form. Take positive root for CCW winding with V-up
        float discrim = B * B - 4. * A *C;
        uv.y = 0.5 * (-B + sqrt(discrim)) / A;
    }

    // Solve for u, using largest-magnitude component
    vec2 denom = b1 + uv.y * b3;
    if (abs(denom.x) > abs(denom.y))
        uv.x = (q.x - b2.x * uv.y) / denom.x;
    else
        uv.x = (q.y - b2.y * uv.y) / denom.y;

    uv.x /= vsize.y;
    uv.y /= vsize.x;
    uv.x += q0.y;
    uv.y += q0.x;

    gl_FragColor = frag_color * texture2D(texture0, vec2(uv.y, uv.x));
}
'''

VS = '''
#ifdef GL_ES
    precision highp float;
#endif

/* Outputs to the fragment shader */
varying vec4 frag_color;
varying vec2 q;
varying vec2 q0;
varying vec2 b1;
varying vec2 b2;
varying vec2 b3;
varying vec2 vsize;

/* vertex attributes */
attribute vec2     vPosition;
attribute vec2     vQuad0;
attribute vec2     vQuad1;
attribute vec2     vQuad2;
attribute vec2     vQuad3;
attribute vec2     vTex0;
attribute vec2     vSize;

/* uniform variables */
uniform mat4       modelview_mat;
uniform mat4       projection_mat;
uniform vec4       color;
uniform float      opacity;

void main (void) {
  q = vPosition - vQuad0;
  q0 = vTex0;
  b1 = vQuad1 - vQuad0;
  b2 = vQuad2 - vQuad0;
  b3 = vQuad0 - vQuad1 - vQuad2 + vQuad3;
  vsize = vSize;
  frag_color = color * vec4(1.0, 1.0, 1.0, opacity);
  gl_Position = projection_mat * modelview_mat * vec4(vPosition.xy, 0.0, 1.0);
}
'''



Builder.load_string("""
<ProjectionMappingCalibration>:
    Label:
        size_hint: None, None
        size: self.texture_size[0] + dp(20), self.texture_size[1] + dp(20)
        text: root.informations
        markup: True
        opacity: int(root.show_help)
        font_name: "data/fonts/RobotoMono-Regular.ttf"
        canvas.before:
            Color:
                rgba: 0, 0, 0, 0.7
            Rectangle:
                pos: self.pos
                size: self.size

<ProjectionMapping>:
    ProjectionMappingGrid:
        id: container
    ProjectionMappingCalibration:
        id: calibration
""")


class ProjectionMappingGrid(F.RelativeLayout):

    def __init__(self, **kwargs):
        self.cols = self.rows = 2
        self.canvas = RenderContext(
            fs=FS, vs=VS,
            use_parent_projection=True,
            use_parent_modelview=True)
        super(ProjectionMappingGrid, self).__init__(**kwargs)
        self.build_mapping()
        self.init_fbo()
        self.bind(size=self.rebuild_fbo)

    def add_widget(self, widget):
        if widget not in self.children:
            self.children.append(widget)
            self.g_fbo.add(widget.canvas)

    def remove_widget(self, widget):
        if widget in self.children:
            self.children.remove(widget)
            self.g_fbo.remove(widget.canvas)

    def init_fbo(self):
        with self.canvas:
            Color(1, 1, 1)
            self.g_fbo = Fbo(size=self.size)
            self.g_fbo_texture = self.g_fbo.texture
            Color(1, 1, 1, 1)
            PushMatrix()
            self.g_scale = Scale(self.width / 2, self.height / 2, 1.)
            self.build_grid()
            PopMatrix()

    def rebuild_fbo(self, *largs):
        asp = self.width / float(self.height)
        self.g_fbo.size = self.size
        self.g_fbo_texture = self.g_fbo.texture
        self.update_grid()

    def build_mapping(self, calibration=None):
        rows = self.rows
        cols = self.cols
        line_vertices = []
        line_indices = []
        ncols = float(cols)
        nrows = float(rows)
        i = 0
        for row in range(rows + 1):
            for col in range(cols + 1):
                if calibration:
                    i = 2 * (col + row * (cols + 1))
                    line_vertices += calibration[i:i + 2]
                    line_vertices += [0, 0]
                else:
                    line_vertices += [col / ncols, row / nrows, 0, 0]
        for row in range(rows):
            for col in range(cols):
                i = col + row * (cols + 1)
                line_indices += [i, i + 1]
                line_indices += [i, i + (cols + 1)]
        self.line_vertices = line_vertices
        self.line_indices = line_indices

    def get_calibration(self):
        calibration = []
        v = self.line_vertices
        for i in range(0, len(v), 4):
            calibration += v[i:i + 2]
        return calibration

    def build_grid(self):
        rows = self.rows
        cols = self.cols
        vertices = []
        indices = []

        dx = 1. / float(cols)
        dy = 1. / float(rows)
        for col in range(cols):
            x = col / float(cols)
            for row in range(rows):
                y = row / float(rows)

                # use line
                corners = []
                i = 4 * (col + row * (cols + 1))
                corners += self.line_vertices[i:i + 2]
                i = 4 * (col + (row + 1) * (cols + 1))
                corners += self.line_vertices[i:i + 2]
                i = 4 * (1 + col + row * (cols + 1))
                corners += self.line_vertices[i:i + 2]
                i = 4 * (1 + col + (row + 1) * (cols + 1))
                corners += self.line_vertices[i:i + 2]

                data = [
                    x, y, cols, rows
                ]

                vertices.extend(corners[0:2])
                vertices.extend(corners)
                vertices.extend(data)
                vertices.extend(corners[2:4])
                vertices.extend(corners)
                vertices.extend(data)
                vertices.extend(corners[4:6])
                vertices.extend(corners)
                vertices.extend(data)
                vertices.extend(corners[6:8])
                vertices.extend(corners)
                vertices.extend(data)

        i = 0
        for col in range(cols):
            for row in range(rows):
                indices.extend((
                    i, i + 3, i + 1,
                    i, i + 2, i + 3))
                i += 4

        self.indices = indices
        self.vertices = vertices
        fmt = [
            (b'vPosition', 2, 'float'),
            (b'vQuad0', 2, 'float'),
            (b'vQuad1', 2, 'float'),
            (b'vQuad2', 2, 'float'),
            (b'vQuad3', 2, 'float'),
            (b'vTex0', 2, 'float'),
            (b'vSize', 2, 'float')
        ]
        fmtsize = 14

        if not hasattr(self, "g_mesh"):
            self.g_mesh = Mesh(
                indices=indices, vertices=vertices, mode="triangles",
                texture=self.g_fbo_texture,
                fmt=fmt
            )
        else:
            self.g_mesh.indices = indices
            self.g_mesh.vertices = vertices

    def update_grid(self):
        self.g_scale.x = self.width
        self.g_scale.y = self.height
        self.g_mesh.texture = self.g_fbo_texture

    def set_vertice(self, i, sx, sy):
        line_vertices = self.line_vertices
        line_vertices[i * 4] = sx
        line_vertices[i * 4 + 1] = sy
        self.build_grid()


class ProjectionMappingCalibration(F.RelativeLayout):
    informations = StringProperty()
    show_help = BooleanProperty(True)

    def __init__(self, **kwargs):
        super(ProjectionMappingCalibration, self).__init__(**kwargs)
        self.g_canvas = None

    def rebuild_informations(self):
        self.informations = "\n".join([
            "[b]Projection Mapping[/b]",
            "Cols: {} - Rows: {}",
            "",
            "[b]Help[/b]",
            "F2: Toggle calibration",
            "space: Toggle help",
            "r: Reset the calibration grid",
            "s: Save the current calibration",
            "l: Load latest calibration",
            "x/c: Remove/add a column (current calibration is lost)",
            "v/b: Remove/add a row (current calibration is lost)"
        ]).format(
            self.grid.cols,
            self.grid.rows)

    def show_lines(self):
        indices = []
        grid = self.grid
        cols = grid.cols
        rows = grid.rows
        for col in range(grid.cols + 1):
            indices.extend((
                col * (rows + 1), col * (rows + 1) + rows,
            ))
        for row in range(grid.rows + 1):
            indices.extend((
                row, row + (cols * (rows + 1)),
            ))

        with self.canvas:
            self.g_canvas = Canvas()

        with self.g_canvas:
            Color(1, 0, 0, 0.5)
            PushMatrix()
            Scale(self.width, self.height, 1.)
            self.g_mesh = Mesh(
                vertices=self.grid.line_vertices,
                indices=self.grid.line_indices,
                mode="lines",
                source="projectionmapping/data/white.png")
            PopMatrix()

        self.rebuild_informations()

    def hide_lines(self):
        if self.g_canvas:
            self.canvas.remove(self.g_canvas)
        self.g_canvas = None

    def update_mesh(self):
        self.hide_lines()
        self.show_lines()

    def on_touch_down(self, touch):
        cols = self.grid.cols
        rows = self.grid.rows

        # select the nearest point
        v = self.grid.line_vertices
        vt = Vector(touch.sx, touch.sy)
        min_i = -1
        min_dist = float("inf")
        for i4 in range(0, len(v), 4):
            d = Vector(v[i4:i4 + 2]).distance(vt)
            if min_dist > d:
                min_dist = d
                min_i = i4 / 4
        touch.ud["i"] = int(min_i)
        touch.grab(self)
        return super(ProjectionMappingCalibration, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            self.grid.set_vertice(touch.ud["i"], touch.sx, touch.sy)
            self.update_mesh()
            return True
        return super(ProjectionMappingCalibration, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            self.grid.set_vertice(touch.ud["i"], touch.sx, touch.sy)
            self.update_mesh()
            return True
        return super(ProjectionMappingCalibration, self).on_touch_up(touch)


class ProjectionMapping(F.RelativeLayout):
    def __init__(self, **kwargs):
        self.wid_container = self.wid_calibration = None
        self.filename = kwargs.pop("filename", "calibration.json")
        super(ProjectionMapping, self).__init__(**kwargs)
        self.wid_container = self.ids.container.__self__
        self.wid_calibration = self.ids.calibration.__self__
        self.remove_widget(self.wid_calibration)
        self.bind_keyboard()
        self.load_calibration()

    def save_calibration(self):
        data = {
            "rows": self.wid_container.rows,
            "cols": self.wid_container.cols,
            "calibration": self.wid_container.get_calibration()
        }
        with open(self.filename, "w") as fd:
            json.dump(data, fd)
        print("Calibration saved to {}".format(self.filename))

    def load_calibration(self):
        try:
            with open(self.filename, "r") as fd:
                data = json.load(fd)
        except Exception as e:
            print("ERROR: Unable to load {}: {!r}".format(
                self.filename, e))
            return
        self.wid_container.rows = data["rows"]
        self.wid_container.cols = data["cols"]
        self.wid_container.build_mapping(calibration=data["calibration"])
        self.wid_container.build_grid()
        if self.wid_calibration.parent:
            self.hide_projection()
            self.show_projection()

    def add_widget(self, widget):
        if self.wid_container:
            return self.wid_container.add_widget(widget)
        return super(ProjectionMapping, self).add_widget(widget)

    def remove_widget(self, widget):
        if widget in self.wid_container.children:
            return self.wid_container.remove_widget(widget)
        return super(ProjectionMapping, self).remove_widget(widget)

    def bind_keyboard(self):
        from kivy.core.window import Window

        def on_key_down(window, scancode, *largs):
            if scancode == 283:
                self.toggle_projection()
                return True
            if not self.wid_calibration.parent:
                return
            if scancode == 32:  # space
                self.wid_calibration.show_help = not self.wid_calibration.show_help
                return True
            elif scancode in (120, 99, 118, 98, 114):  # x, c, v, b, r
                if scancode == 120:
                    self.wid_container.rows = max(1, self.wid_container.rows - 1)
                elif scancode == 99:
                    self.wid_container.rows = self.wid_container.rows + 1
                elif scancode == 118:
                    self.wid_container.cols = max(1, self.wid_container.cols - 1)
                elif scancode == 98:
                    self.wid_container.cols = self.wid_container.cols + 1
                self.wid_container.build_mapping()
                self.wid_container.build_grid()
                self.hide_projection()
                self.show_projection()
                return True
            elif scancode == 115:
                self.save_calibration()
                return True
            elif scancode == 108:
                self.load_calibration()
                return True

        Window.bind(on_key_down=on_key_down)

    def toggle_projection(self):
        if self.wid_calibration.parent:
            self.hide_projection()
        else:
            self.show_projection()

    def hide_projection(self):
        super(ProjectionMapping, self).remove_widget(self.wid_calibration)
        self.wid_calibration.hide_lines()

    def show_projection(self):
        super(ProjectionMapping, self).add_widget(self.wid_calibration)
        self.wid_calibration.grid = self.wid_container
        self.wid_calibration.size = self.size
        self.wid_calibration.show_lines()