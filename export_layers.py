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
        self.arg_parser.add_argument("--dpi", action="store", type=int, dest="dpi", default=90)

    def is_layer_in_range(self, layer, current):
        if "show_on" in layer:
            return current in layer["show_on"]
        else:
            return false

    def effect(self):
        output_path = os.path.expanduser(self.options.path)
        curfile = self.options.input_file
        layers, maxlayer = self.get_layers(curfile)

        for counter in range(1, maxlayer+1):
            if not os.path.exists(os.path.join(output_path)):
                os.makedirs(os.path.join(output_path))
            show_layer_ids = [layer["id"] for layer in layers if self.is_layer_in_range(layer, counter)]
            with tempfile.NamedTemporaryFile() as fp_svg:
                layer_dest_svg_path = fp_svg.name
                self.export_layers(layer_dest_svg_path, show_layer_ids)
                filename = "%s%s" % (self.options.filename_prefix, str(counter).zfill(len(str(maxlayer))))

                if self.options.filetype == "png":
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
        expr = re.compile('\[(\d*-\d*(,\d*-\d*)*)\]')
        maxlayer = 1

        for svg_layer in svg_layers:
            svg_label_attrib_name = "{%s}label" % svg_layer.nsmap['inkscape']
            if svg_label_attrib_name not in svg_layer.attrib:
                continue
            svg_layer_id = svg_layer.attrib["id"]
            svg_layer_label = svg_layer.attrib[svg_label_attrib_name]

            layer_prop = { "id" : svg_layer_id }
            m = expr.match(svg_layer_label)
            if m != None:
                layer_visible = []
                all_frames = m.group(1).split(",")
                for frames in all_frames:
                    split_boundaries = frames.split("-")
                    if len(split_boundaries) != 2:
                        continue
                    boundaries = {}
                    if split_boundaries[0]:
                        boundaries["begin"] = int(split_boundaries[0])
                        maxlayer = max(maxlayer, boundaries["begin"])
                    if split_boundaries[1]:
                        boundaries["end"] = int(split_boundaries[1])
                        maxlayer = max(maxlayer, boundaries["end"])
                    layer_visible += [boundaries]
                layer_prop["show_intervals"] = layer_visible
                layer_prop["type"] = "numbered"
            elif svg_layer_label.lower().startswith("[fixed]"):
                layer_prop["type"] = "fixed"
            else:
                continue
            layers.append(layer_prop)
        
        for layer in layers:
            layer["show_on"] = []
            if layer["type"] == "fixed":
                layer["show_on"] += [*range(1, maxlayer+1)]
            elif layer["type"] == "numbered":
                layer["show_on"] = []
                for interval in layer["show_intervals"]:
                    begin = interval["begin"] if "begin" in interval else 1
                    end = interval["end"] if "end" in interval else maxlayer
                    layer["show_on"] += [*range(begin, end+1)]
            inkex.debug(layer)

        return (layers, maxlayer)

    def exportToPng(self, svg_path, output_path):
        area_param = '-C' 
        command = "inkscape %s -d %s -o \"%s\" \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def exportToPdf(self, svg_path, output_path):
        area_param = '-C'
        command = "inkscape %s -d %s -o \"%s\" \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def exportToLatex(self, svg_path, output_path):
        area_param = '-C'
        command = "inkscape %s -d %s -o \"%s\" --export-latex \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

def _main():
    e = PNGExport()
    e.run()
    exit()

if __name__ == "__main__":
    _main()
