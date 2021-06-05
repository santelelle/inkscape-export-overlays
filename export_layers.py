#! /usr/bin/env python

import sys
sys.path.append('/usr/share/inkscape/extensions')
import inkex
import os
import subprocess
import tempfile
import shutil
import copy
import re


class PNGExport(inkex.Effect):
    def __init__(self):
        """init the effetc library and get options from gui"""
        inkex.Effect.__init__(self)
        self.arg_parser.add_argument("--path", action="store", dest="path", default="~/", help="")
        self.arg_parser.add_argument("--filename_prefix", action="store", dest="filename_prefix", default="", help="")
        self.arg_parser.add_argument('-f', '--filetype', action='store', dest='filetype', default='jpeg', help='Exported file type')
        self.arg_parser.add_argument("--crop", action="store", type=bool, dest="crop", default=False)
        self.arg_parser.add_argument("--dpi", action="store", type=int, dest="dpi", default=90)

    def is_layer_in_range(self, layer, current):
        if isinstance(layer[2], tuple) and layer[2][0] == 'numbered':
            return layer[2][1] <= current and current <= layer[2][2]
        else:
            return false

    def effect(self):
        output_path = os.path.expanduser(self.options.path)
        curfile = self.options.input_file
        layers, maxlayer = self.get_layers(curfile)

        for counter in range(1, maxlayer+1):
            for (layer_id, layer_label, layer_type) in layers:
                if layer_type == "fixed":
                    continue

                show_layer_ids = [layer[0] for layer in layers if layer[2] == "fixed" or (layer[2] == "export" and layer[0] == layer_id) or self.is_layer_in_range(layer, counter)]

                if not os.path.exists(os.path.join(output_path)):
                    os.makedirs(os.path.join(output_path))

            with tempfile.NamedTemporaryFile() as fp_svg:
                layer_dest_svg_path = fp_svg.name
                self.export_layers(layer_dest_svg_path, show_layer_ids)
                filename = "%s%s" % (self.options.filename_prefix, str(counter).zfill(len(str(maxlayer))))

                if self.options.filetype == "jpeg":
                    with tempfile.NamedTemporaryFile() as fp_png:
                        self.exportToPng(layer_dest_svg_path, fp_png.name)
                        layer_dest_jpg_path = os.path.join(output_path, filename + ".jpg")
                        self.convertPngToJpg(fp_png.name, layer_dest_jpg_path)
                elif self.options.filetype == "png":
                    layer_dest_png_path = os.path.join(output_path, filename + ".png")
                    self.exportToPng(layer_dest_svg_path, layer_dest_png_path)
                elif self.options.filetype == "pdf":
                    layer_dest_pdf_path = os.path.join(output_path, filename + ".pdf")
                    self.exportToPdf(layer_dest_svg_path, layer_dest_pdf_path)
                elif self.options.filetype == "latex":
                    layer_dest_latex_path = os.path.join(output_path, filename + ".pdf")
                    self.exportToLatex(layer_dest_svg_path, layer_dest_latex_path)

    def export_layers(self, dest, show):
        """
        Export selected layers of SVG to the file `dest`.
        :arg  str   dest:  path to export SVG file.
        :arg  list  hide:  layers to hide. each element is a string.
        :arg  list  show:  layers to show. each element is a string.
        """
        doc = copy.deepcopy(self.document)
        for layer in doc.xpath('//svg:g[@inkscape:groupmode="layer"]', namespaces=inkex.NSS):
            layer.attrib['style'] = 'display:none'
            id = layer.attrib["id"]
            if id in show:
                layer.attrib['style'] = 'display:inline'

        doc.write(dest)

    def get_layers(self, src):
        svg_layers = self.document.xpath('//svg:g[@inkscape:groupmode="layer"]', namespaces=inkex.NSS)
        layers = []
        expr = re.compile('\[(\d*)-(\d*)\]\s*')
        maxlayer = 1

        for layer in svg_layers:
            label_attrib_name = "{%s}label" % layer.nsmap['inkscape']
            if label_attrib_name not in layer.attrib:
                continue

            layer_id = layer.attrib["id"]
            layer_label = layer.attrib[label_attrib_name]

            m = expr.match(layer_label)
            if m != None:
                begin = 1
                end = len(svg_layers)
                if m.group(1):
                    begin = int(m.group(1))
                    maxlayer = begin if begin > maxlayer else maxlayer
                if m.group(2):
                    end = int(m.group(2))
                    maxlayer = end if end > maxlayer else maxlayer
                layer_type = ("numbered", begin, end)
                layer_label = layer_label[len(m.group(0)):]
            elif layer_label.lower().startswith("[fixed] "):
                layer_type = "fixed"
                layer_label = layer_label[8:]
            elif layer_label.lower().startswith("[export] "):
                layer_type = "export"
                layer_label = layer_label[9:]
            else:
                continue

            layers.append([layer_id, layer_label, layer_type])

        return (layers, maxlayer)

    def exportToPng(self, svg_path, output_path):
        area_param = '-C' #'-D' if self.options.crop else '-C'
        command = "inkscape %s -d %s -e \"%s\" \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def exportToPdf(self, svg_path, output_path):
        area_param = '-C' #'-D' if self.options.crop else '-C'
        command = "inkscape %s -d %s --export-pdf \"%s\" \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def exportToLatex(self, svg_path, output_path):
        area_param = '-C' #'-D' if self.options.crop else '-C'
        command = "inkscape %s -d %s --export-filename \"%s\" --export-latex \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def convertPngToJpg(self, png_path, output_path):
        command = "convert \"%s\" \"%s\"" % (png_path, output_path)
        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()


def _main():
    e = PNGExport()
    e.run()
    exit()

if __name__ == "__main__":
    _main()
