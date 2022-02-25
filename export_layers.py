#! /usr/bin/env python
""" link in this folder the /usr/share/inkscape/extensions to make pycharm able to reference inkex
(right click in the folder in the pycharm explorer -> Mark directory as -> source """
import sys
import types
from typing import List, NamedTuple
# sys.path.insert(0, '/usr/share/inkscape/extensions')
from pathlib import Path
import inkex
from inkex import EffectExtension
import os
import subprocess
import tempfile
import shutil
import copy
import re
import time
import argparse


RUNNING_IN_INKSCAPE = True
VALID_ACTIONS = ['s', 'p']


class ExportGroup(NamedTuple):
    name: str
    indexes: List[int]


def print(a):
    """ redefine the print to be able to show them in inkscape """
    if RUNNING_IN_INKSCAPE:
        sys.stderr.write(f'{a}\n')
    else:
        sys.stdout.write(f'{a}\n')


class PNGExport(EffectExtension):
    def __init__(self):
        """init the effect library and get options from gui"""
        super().__init__()
        # ? all the parsed arguments will be available in self.options
        self.arg_parser.add_argument("--tab")  # ? dummy args just for inkscape
        self.arg_parser.add_argument("--path", action="store", dest="path", default="~/", help="")
        self.arg_parser.add_argument("--filename_prefix", action="store", dest="filename_prefix", default="", help="")
        self.arg_parser.add_argument('-f', '--filetype', action='store', dest='filetype', default='png',
                                     help='Exported file type')
        self.arg_parser.add_argument("--dpi", action="store", type=int, dest="dpi", default=300)

    def export_layers(self, output_file, indexes):
        """
        Export selected layers of SVG to the file
        """
        doc = copy.deepcopy(self.document)
        images = doc.xpath('//svg:image', namespaces=inkex.NSS)

        for image in images:
            image_path: str = image.attrib[f'{{{image.nsmap["xlink"]}}}href']
            # ? skip the path correction if the image was embedded
            if image_path.startswith('data:'):
                continue
            else:
                if RUNNING_IN_INKSCAPE:
                    abs_path = image_path
                else:
                    abs_path = Path(self.svg.base).parent / image_path
                image.attrib[f'{{{image.nsmap["xlink"]}}}href'] = str(abs_path)

        layers: List = doc.xpath('//svg:g[@inkscape:groupmode="layer"]', namespaces=inkex.NSS)
        for i, layer in enumerate(layers):
            layer.attrib['style'] = 'display:none'
            if i in indexes:
                layer.attrib['style'] = 'display:inline'
        doc.write(str(output_file))

    def get_layers_and_export_groups(self):
        # ? the layers are imported starting from the bottom one and with name stored in .label
        layers: List = self.document.xpath('//svg:g[@inkscape:groupmode="layer"]', namespaces=inkex.NSS)
        for layer in layers:
            # ? some weird check that was copied from somewhere
            label_attrib_name = f'{{{layer.nsmap["inkscape"]}}}label'
            if label_attrib_name not in layer.attrib:
                raise AttributeError

        n_layers = len(layers)
        reg = re.compile('\[((-?\d*\/-?\d*|[a-z]|-?\d+)(,-?\d*\/-?\d*|,[a-z]|,-?\d+)*)\]')

        # ? the actions give a specific function to the specific layer, for example [s] always skip the layer
        layers_actions = []
        # ? the frames select a relative interval (or multiple relative interval) of layer to make visible before
        # ? exporting
        layers_frames = []
        try:
            # ? read all the layers tags
            for i, layer in enumerate(layers):
                label = layer.label

                actions = []
                frames = []
                m = reg.match(label)
                if m is not None:
                    actions_and_frames = m.group(1).split(',')
                    for action_or_frame in actions_and_frames:
                        boundaries = action_or_frame.split('/')
                        # ? specifier can be of multiple types
                        # ? [number] select the specified layer with relative position
                        # ? [number/number] select the specified layers range with relative position
                        # ? [/] or [number/] or [/number] select the specified layers range with relative position
                        # ?     where the empty position is the min or max layer number
                        if len(boundaries) == 1:
                            if boundaries[0].isnumeric():
                                start = int(boundaries[0]) + i
                                end = int(boundaries[0]) + 1 + i
                                if start < 0 or end > n_layers:
                                    raise ValueError(f'invalid tag {boundaries[0]} on layer {label}')
                                frames.append([start, end])
                            else:
                                if boundaries[0] not in VALID_ACTIONS:
                                    raise ValueError(f'invalid tag {boundaries[0]} on layer {label}')
                                actions.append(boundaries[0])
                        elif len(boundaries) == 2:
                            # ? if the start or the end are not specified, use the max range
                            start = int(boundaries[0]) if boundaries[0] != '' else 0 + i
                            end = int(boundaries[1]) + 1 if boundaries[1] != '' else n_layers + i
                            if start < 0 or end > n_layers:
                                raise ValueError(f'exceeding layers range {boundaries[0]} on layer {label}')
                            frames.append([start, end])
                        else:
                            raise ValueError(f'empty tag is not valid on layer {label}')
                layers_actions.append(actions)
                layers_frames.append(frames)
        except ValueError as e:
            print(f'provided specifier are invalid: {e}')

        # ? each export group includes the index of all the layers
        export_groups = []
        # ? handle actions
        for i, (layer, layer_frames, layer_actions) in enumerate(zip(layers, layers_frames, layers_actions)):
            id = layer.attrib['id']
            label_clean = reg.sub('', layer.label)

            export_index = []
            for j, src_layer_actions in enumerate(layers_actions):
                # ? check if the current index must be skipped
                if 's' in src_layer_actions:
                    continue
                # ? check if the current index is persistent
                if 'p' in src_layer_actions and layer_frames:
                    export_index.append(j)
                # ? check if the current layer is inside any frame
                for start, end in layer_frames:
                    if start <= j < end:
                        export_index.append(j)
                        break

            if export_index:
                export_groups.append(ExportGroup(label_clean, export_index))

        return layers, export_groups

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
        command = "inkscape %s -d %s -o \"%s\" --export-latex \"%s\"" % (
            area_param, self.options.dpi, output_path, svg_path)

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def effect(self):
        output_dir = Path(self.options.path)
        layers, export_groups = self.get_layers_and_export_groups()

        if not os.path.exists(os.path.join(output_dir)):
            os.makedirs(os.path.join(output_dir))

        for export_group in export_groups:
            filename = f'{self.options.filename_prefix}{export_group.name}'

            with tempfile.NamedTemporaryFile() as fp_svg:
                dummy_path = Path(fp_svg.name)
                self.export_layers(dummy_path, export_group.indexes)

                if self.options.filetype == 'png':
                    output_path = output_dir / (filename + '.png')
                    self.exportToPng(dummy_path, output_path)
                elif self.options.filetype == "pdf":
                    output_path = output_dir / (filename + '.pdf')
                    self.exportToPdf(dummy_path, output_path)
                elif self.options.filetype == "latex":
                    output_path = output_dir / (filename + '.latex')
                    self.exportToLatex(dummy_path, output_path)


if __name__ == "__main__":
    # ? all these arguments are meant to be used by pycharm only
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument("--svg_path", type=Path, help='the .svg path')
    parser.add_argument("--path", type=Path, help='the output path')

    args, other_args = parser.parse_known_args()

    if args.debug:
        RUNNING_IN_INKSCAPE = False
        print('running in pycharm')
        input_file = '/home/lele/drive/Tablescope/pinata/Deck/pinata_template.svg'
        PNGExport().run([input_file, '--path', str(args.path)])
        # PNGExport().run([input_file, '--output=' + output_file])
    else:
        # print('running in inkscape')
        PNGExport().run()
