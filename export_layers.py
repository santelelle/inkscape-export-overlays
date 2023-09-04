#! /usr/bin/env python
""" link in this folder the /usr/share/inkscape/extensions to make pycharm able to reference inkex
(right click in the folder in the pycharm explorer -> Mark directory as -> source """
from __future__ import annotations
import sys
from dataclasses import dataclass, field
from typing import List, Union, Dict, Tuple
from pathlib import Path
import inkex
from enum import Enum
from inkex import EffectExtension, Layer
import os
import subprocess
import tempfile
import copy
import re
import argparse

TOKEN_SEPARATOR = ','
FRAME_SEPARATOR = ':'
EXCLUDE_SYMBOL = '!'
MARK_SYMBOL = '#'
SELECT_MARK_SYMBOL = '*'

class Property(Enum):
    PERSISTENT = 0
    SKIP = 1


# ? redefine the Layer __repr__ to make the debugging of the code easier
Layer.__repr__ = lambda self: self.label


@dataclass
class LayerWithHierarchy:
    layer: Layer
    depth: int

    parent: Union[LayerWithHierarchy, None] = None
    childs: List[LayerWithHierarchy] = field(default_factory=list)

    tag: str = None
    label: str = None
    tokens_properties: List[str] = field(default_factory=list)
    tokens_frames: List[str] = field(default_factory=list)
    tokens_selections: List[str] = field(default_factory=list)
    tokens_exclusions: List[str] = field(default_factory=list)

    marker: str = None
    selections: List[str] = field(default_factory=list)

    properties: List = field(default_factory=list)

    def __post_init__(self):
        tags = re.findall(r'\[(.*?)\]', self.layer.label)
        if len(tags) > 1:
            raise ValueError(f'please specify only one tag per layer, got multiple ones on {self.layer.label}')
        self.tag = tags[0] if tags else None
        self.label = self.layer.label.replace(f'[{self.tag}]', '')
        tokens = self.tag.split(TOKEN_SEPARATOR) if self.tag else []
        self.parse_tokens(tokens)

    def parse_tokens(self, tokens: List[str]) -> None:
        for token in tokens:
            if token in {'p', 's'}:
                self.tokens_properties.append(token)
                if token == 'p':
                    self.properties.append(Property.PERSISTENT)
                    continue
                if token == 's':
                    self.properties.append(Property.SKIP)
                    continue
            if token.startswith(EXCLUDE_SYMBOL):
                self.tokens_exclusions.append(token[1:])
                continue

            if token.startswith(MARK_SYMBOL):
                self.marker = token[1:]
                continue

            if token.startswith('i'):
                self.tokens_selections.append(token)
                self.selections.append(token[1:])
                continue

            self.tokens_frames.append(token)

    def __repr__(self):
        depth = f'd:{self.depth} '
        childs = f'c:{len(self.childs)} '
        return   f'{depth}{childs}{self.layer.label}'


# noinspection PyShadowingBuiltins
def print(a):
    """ redefine the print to be able to show them in inkscape """
    if RUNNING_IN_INKSCAPE:
        sys.stderr.write(f'{a}\n')
    else:
        sys.stdout.write(f'{a}\n')


def get_layer_depth(layer: Layer, max_depth: int = 10) -> int:
    for depth in range(max_depth):
        if not isinstance(layer.getparent(), Layer):
            return depth
        layer = layer.getparent()
    return -1


def relative_or_absolute_token_to_index(token: str, current_idx: int, n_layers: int) -> int:
    if token[0] == '@':
        idx = int(token[1:])
        if idx < 0:
            idx += n_layers
        return idx

    idx = int(token) + current_idx
    return idx


def get_frames_idxs(layer_h: LayerWithHierarchy, layers_h: List[LayerWithHierarchy], current_idx: int):
    n_layers = len(layers_h)
    selected_idxs = []
    for token in layer_h.tokens_frames:
        if token.startswith(SELECT_MARK_SYMBOL):
            # ? select layer/layers by mark
            selected_idxs.extend([i for i, l_h in enumerate(layers_h) if l_h.marker == token[1:]])
            continue

        if FRAME_SEPARATOR not in token:
            # ? [number] select the specified layer with relative (absolute if preceded by @) position
            selected_idxs.append(relative_or_absolute_token_to_index(token, current_idx, n_layers))
            continue

        boundaries = token.split(FRAME_SEPARATOR)
        if len(boundaries) > 2:
            raise ValueError(f'invalid token {token} in {layer_h.layer.label}')

        start_str, end_str = token.split(FRAME_SEPARATOR)
        # ? [/] or [number/] or [/number] select the specified layers range with relative (absolute if preceded by @) position
        # ?     where the empty position is the min or max layer number
        # ? [number/number] select the specified layers range with relative (absolute if preceded by @) position

        if start_str == '':
            start = 0
        else:
            start = relative_or_absolute_token_to_index(start_str, current_idx, n_layers)
        if end_str == '':
            end = n_layers
        else:
            end = relative_or_absolute_token_to_index(end_str, current_idx, n_layers)

        selected_idxs.extend(range(min(start, end), max(start, end) + 1))

    return sorted(set(selected_idxs))


class ExportLayers(EffectExtension):
    def __init__(self):
        """init the effect library and get options from gui"""
        super().__init__()
        # ? all the parsed arguments will be available in self.options
        self.arg_parser.add_argument('--tab')  # ? dummy args just for inkscape
        self.arg_parser.add_argument('--path', action='store', dest='path', default='~/', help='')
        self.arg_parser.add_argument('--filename_prefix', action='store', dest='filename_prefix', default='', help='')
        self.arg_parser.add_argument('--filename_postfix', action='store', dest='filename_postfix', default='', help='')
        self.arg_parser.add_argument('-f', '--filetype', action='store', dest='filetype', default='png', help='Exported file type')
        self.arg_parser.add_argument('--dpi', action="store", type=int, dest='dpi', default=300)

    def effect(self) -> None:
        output_dir = Path(self.options.path)
        layers, export_groups = self.get_layers_and_export_groups()

        if not os.path.exists(os.path.join(output_dir)):
            os.makedirs(os.path.join(output_dir))

        # ? we make a copy to not modify the original document
        document_supp = copy.deepcopy(self.document)
        images = self.document.xpath('//svg:image', namespaces=inkex.NSS)

        if not RUNNING_IN_INKSCAPE:
            for image in images:
                image_path: str = image.attrib[f'{{{image.nsmap["xlink"]}}}href']
                abs_path = Path(self.svg.base).parent / image_path
                image.attrib[f'{{{image.nsmap["xlink"]}}}href'] = str(abs_path)

        tempfile_path = Path(tempfile.gettempdir()) / f'export_layers_tmp.svg'
        document_supp.write(str(tempfile_path))

        for name, indexes in export_groups.items():
            self.change_file_visibilities(document_supp, tempfile_path, indexes)

            filename = f'{self.options.filename_prefix}{name}{self.options.filename_postfix}'

            if self.options.filetype == 'png':
                output_path = output_dir / (filename + '.png')
                self.export_to_png(tempfile_path, output_path)
                continue
            if self.options.filetype == "pdf":
                output_path = output_dir / (filename + '.pdf')
                self.export_to_pdf(tempfile_path, output_path)
                continue
            if self.options.filetype == "latex":
                output_path = output_dir / (filename + '.latex')
                self.export_to_latex(tempfile_path, output_path)
                continue

    def get_layers(self, document) -> List[LayerWithHierarchy]:
        # ? the layers are imported starting from the bottom one and with name stored in .label
        layers: List = document.xpath('//svg:g[@inkscape:groupmode="layer"]', namespaces=inkex.NSS)
        # ? reorganize everything using the nested layers
        layers_with_hierarchy = self.get_layers_with_hierarchy(layers)
        return layers_with_hierarchy

    def get_layers_and_export_groups(self) -> Tuple[List[LayerWithHierarchy], Dict[str, List[int]]]:
        layers_with_hierarchy = self.get_layers(self.document)
        n_layers = len(layers_with_hierarchy)

        export_groups = {}
        for i, layer_h in enumerate(layers_with_hierarchy):
            label = layer_h.label

            if not layer_h.tokens_frames:
                continue

            # ? indexes coming from the frames
            frame_idxs = get_frames_idxs(layer_h, layers_with_hierarchy, i)

            # ? indexes coming from the selections
            if layer_h.selections:
                raise NotImplementedError('selections not implemented yet')

            # ? indexes coming from the properties
            for j, layer_h_supp in enumerate(layers_with_hierarchy):
                if Property.SKIP in layer_h_supp.properties:
                    continue
                if Property.PERSISTENT in layer_h_supp.properties:
                    if j not in frame_idxs:
                        frame_idxs.append(j)

            # ? apply the exclusions
            for token in layer_h.tokens_exclusions:
                idx = relative_or_absolute_token_to_index(token, i, n_layers)
                if idx in frame_idxs:
                    frame_idxs.remove(idx)

            # ? assign the name to the export group
            if frame_idxs:
                if label not in export_groups:
                    export_groups[label] = sorted(set(frame_idxs))
                    continue

                for n in range(999999):
                    incremental_label = f'{label}_{n}'
                    if incremental_label not in export_groups:
                        export_groups[incremental_label] = sorted(set(frame_idxs))
                        break

        return layers_with_hierarchy, export_groups

    @staticmethod
    def get_layers_with_hierarchy(layers: List[Layer], max_depth: int = 10) -> List[LayerWithHierarchy]:
        # ? revers the order of the layers such that the first one is the topmost in the inkscape layer view
        layers = layers[::-1]

        # ? subdivide the layers by depth
        layers_at_depth: List[List[LayerWithHierarchy]] = []
        for depth in range(max_depth):
            layers_at_this_depth = [LayerWithHierarchy(layer, depth) for layer in layers if get_layer_depth(layer) == depth]
            if not layers_at_this_depth:
                max_depth = depth - 1
                break
            layers_at_depth.append(layers_at_this_depth)

        if len(layers_at_depth) == 1:
            return layers_at_depth[0]

        for depth in range(max_depth, 0, -1):
            layers_at_this_depth = layers_at_depth[depth]
            layers_at_previous_depth = layers_at_depth[depth - 1]
            for layer_with_hierarchy in layers_at_this_depth:
                parent = layer_with_hierarchy.layer.getparent()
                parent_idx = [i for i, layer_h in enumerate(layers_at_previous_depth) if layer_h.layer == parent][0]
                layers_at_previous_depth[parent_idx].childs.append(layer_with_hierarchy)
        layers_with_hierarchy = layers_at_depth[0]
        return layers_with_hierarchy

    def change_file_visibilities(self, document_supp, output_file: Path, indexes: List[int]) -> None:
        layers_with_hierarchy = self.get_layers(document_supp)
        for i, layer_h in enumerate(layers_with_hierarchy):
            layer_h.layer.attrib['style'] = 'display:inline' if i in indexes else 'display:none'
        document_supp.write(str(output_file))

    def export_to_png(self, svg_path: Path, output_path: Path) -> None:
        area_param = '-C'
        command = f'inkscape {area_param} -d {self.options.dpi} -o "{output_path}" "{svg_path}" --export-background="#FFFFFF" --export-background-opacity=0'

        # ? set the environment varialbe SELF_CALL to 1. This is needed to fix a bug with inkscape
        os.environ['SELF_CALL'] = '1'

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            return_code = p.wait()
            # print(f'inkscape return code: {return_code}')
            stdout, stderr = p.communicate()
            # print(f'inkscape stdout: {stdout}')
            # print(f'inkscape stderr: {stderr}')
            p.kill()

    def export_to_pdf(self, svg_path: Path, output_path: Path) -> None:
        area_param = '-C'
        command = f'inkscape {area_param} -d {self.options.dpi} -o "{output_path}" "{svg_path}" --export-background="#FFFFFF" --export-background-opacity=0'

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()

    def export_to_latex(self, svg_path: Path, output_path: Path) -> None:
        area_param = '-C'
        # command = "inkscape %s -d %s -o \"%s\" --export-latex \"%s\"" % (area_param, self.options.dpi, output_path, svg_path)
        command = f'inkscape {area_param} -d {self.options.dpi} -o "{output_path}" --export-latex "{svg_path}" --export-background="#FFFFFF" --export-background-opacity=0'

        with subprocess.Popen(command.encode("utf-8"), shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
            p.wait()
            p.kill()


if __name__ == "__main__":
    # ? all these arguments are meant to be used by pycharm only
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    parser.add_argument("--svg_path", type=Path, help='the .svg path', default='example.svg')
    parser.add_argument("--output_path", type=Path, help='the output path', default='example_output')

    args, other_args = parser.parse_known_args()

    if args.debug:
        RUNNING_IN_INKSCAPE = False
        print('running in pycharm')
        ExportLayers().run([str(args.svg_path.absolute()), '--path', str(args.output_path.absolute()), '--dpi', '300'])
        # ExportLayers().run([input_file, '--output=' + output_file])
    else:
        RUNNING_IN_INKSCAPE = True
        # print('running in inkscape')
        ExportLayers().run()
