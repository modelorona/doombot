#!/usr/bin/env python3

import struct
import re
import math
class Wad(object):
    """Encapsulates the data found inside a WAD file"""

    def __init__(self, wadFile):
        """Each WAD files contains definitions for global attributes as well as map level attributes"""
        self.levels = []
        self.wad_format = 'DOOM' #Assume DOOM format unless 'BEHAVIOR' 
        with open(wadFile, "rb") as f:
            header_size = 12
            self.wad_type = f.read(4)[0]
            self.num_lumps = struct.unpack("<I", f.read(4))[0]
            data = f.read(struct.unpack("<I", f.read(4))[0] - header_size)

            current_level = Level(None) #The first few records of a WAD are not associated with a level

            lump = f.read(16) #Each offset is is part of a packet 16 bytes
            while len(lump) == 16:
                filepos = struct.unpack("<I", lump[0:4])[0] - header_size
                size = struct.unpack("<I", lump[4:8])[0]
                name = lump[8:16].decode('UTF-8').rstrip('\0')
                print(name)
                if(re.match('E\dM\d|MAP\d\d', name)):
                    #Level nodes are named things like E1M1 or MAP01
                    if(current_level.is_valid()):
                        self.levels.append(current_level)
                    
                    current_level = Level(name)
                elif name == 'BEHAVIOR':
                    #This node only appears in Hexen formated WADs
                    self.wad_format = 'HEXEN'
                else:
                    current_level.lumps[name] = data[filepos:filepos+size]

                lump = f.read(16)
            if(current_level.is_valid()):
                self.levels.append(current_level)

        for level in self.levels:
            level.load(self.wad_format)

class Level(object):
    """Represents a level inside a WAD which is a collection of lumps"""
    def __init__(self, name):
        self.name = name
        self.lumps = dict()
        self.vertices = []
        self.lower_left = None
        self.upper_right = None
        self.shift = None
        self.lines = []
        self.possible_vertices = []
        self.inside_vertices= []
        self.visibility_edges = []

    def is_valid(self):
        return self.name is not None and 'VERTEXES' in self.lumps and 'LINEDEFS' in self.lumps

    def normalize(self, point, padding=5):
        return (self.shift[0]+point[0]+padding,self.shift[1]+point[1]+padding)

    def load(self, wad_format):
        for vertex in packets_of_size(4, self.lumps['VERTEXES']):
            x,y = struct.unpack('<hh', vertex[0:4])
            self.vertices.append((x,y))

        self.lower_left = (min((v[0] for v in self.vertices)), min((v[1] for v in self.vertices)))
        self.upper_right = (max((v[0] for v in self.vertices)), max((v[1] for v in self.vertices)))

        self.shift = (0-self.lower_left[0],0-self.lower_left[1])
        
        packet_size = 16 if wad_format is 'HEXEN' else 14
        for data in packets_of_size(packet_size, self.lumps['LINEDEFS']):
            self.lines.append(Line(data))
    def oppSides(self, p, q, a, b):# line pq, point to test, max point outside
        g = ((b[0] - a[0]) * (p[1] - a[1])) - ((b[1] - a[1]) * (p[0] - a[0]))
        h = ((b[0] - a[0]) * (q[1] - a[1])) - ((b[1] - a[1]) * (q[0] - a[0]))
        return g * h <= 0.0

    def boundingBox(self, p, q, a, b):# line pq, point to test, max point outside
        gx = min(p[0], q[0])
        gy = min(p[1], q[1])
        hx = max(p[0], q[0])
        hy = max(p[1], q[1])
        ix = min(a[0], b[0])
        iy = min(a[1], b[1])
        jx = max(a[0], b[0])
        jy = max(a[1], b[1])

        return jy >= gy and iy <=hy and gx <= jx and ix <= hx

    def there_is_not_an_intersection(self, d1, d2, line_vertices, lines):
        intersections = 0
        for line in lines:
            if self.oppSides(dot, other_dot, line_vertices[line.a], line_vertices[line.b]) and self.oppSides(line_vertices[line.a], line_vertices[line.b], dot, other_dot) and self.boundingBox(dot, other_dot, line_vertices[line.a], line_vertices[line.b]) and line.is_one_sided():
                return false
        return true


    def generate_visibility_graph(self, line_vertices, lines, inside_vertices):
        for dot in inside_vertices:
            for other_dot in inside_vertices:
                if dot[0] != other_dot[0] and dot[1] != other_dot[1]:
                    if there_is_not_an_intersection(dot, other_dot,line_vertices, lines):
                        self.visibility_edges += [(dot, other_dot)]
                    
                     
    def generate_inside_points(self):
        possible_vertices = []
        x = self.lower_left[0] + 100.0
        while x < self.upper_right[0]:
            y = self.lower_left[1] + 100.0
            while y < self.upper_right[1]:
                possible_vertices += [(x,y)]
                y += 100.0
            x += 100.0
            
##        f = open('vertices.txt','w')
        for dot in possible_vertices:
            intersections = 0
            for line in self.lines:
                if self.oppSides(self.vertices[line.a], self.vertices[line.b], dot, (self.upper_right[0] + 20, self.upper_right[1] + 20)) and self.oppSides(dot, (self.upper_right[0] + 20, self.upper_right[1] + 20), self.vertices[line.a], self.vertices[line.b]) and self.boundingBox(self.vertices[line.a], self.vertices[line.b], dot, (self.upper_right[0] + 20, self.upper_right[1] + 20)) and line.is_one_sided():
                    intersections += 1
            if intersections % 2 == 1:
##                f.write(str(dot)+"&")
                self.inside_vertices += [dot]
##        f.close()
    def save_svg(self):
        """ Scale the drawing to fit inside a 1024x1024 canvas (iPhones don't like really large SVGs even if they have the same detail) """
        import svgwrite
        view_box_size = self.normalize(self.upper_right, 10)
        if view_box_size[0] > view_box_size[1]:
            canvas_size = (1024, int(1024*(float(view_box_size[1])/view_box_size[0])))
        else:
            canvas_size = (int(1024*(float(view_box_size[0])/view_box_size[1])), 1024)

        dwg = svgwrite.Drawing(self.name+'.svg', profile='tiny', size=canvas_size , viewBox=('0 0 %d %d' % view_box_size))
        
        self.generate_inside_points()

        old_vertice = self.inside_vertices[-1]
        for dot in self.inside_vertices:
            dwg.add(dwg.line(self.normalize(old_vertice),self.normalize(dot),stroke="#ff0000",stroke_width=30))
            dwg.add(dwg.circle(self.normalize(dot),1, stroke='#00ff00', stroke_width=30))
            old_vertice = dot
            
        
        for line in self.lines:
            a = self.normalize(self.vertices[line.a])
            b = self.normalize(self.vertices[line.b])
			
            if line.is_one_sided():
                dwg.add(dwg.line(a, b, stroke='#333', stroke_width=10))
            else:
                dwg.add(dwg.line(a, b, stroke='#999', stroke_width=3))
            dwg.add(dwg.circle(a,1, stroke='#ff0000', stroke_width=20))

        dwg.save()

class Edge(object):
    def __init__(self, x, y):
        self.p1 = x
        self.p2 = y

class Line(object):
    """Represents a Linedef inside a WAD"""
    def __init__(self,data):
        self.a, self.b = struct.unpack('<hh', data[0:4])
        self.left_side, self.right_side = struct.unpack('<hh', data[-4:])

    def is_one_sided(self):
        return self.left_side == -1 or self.right_side == -1

def packets_of_size(n, data):
    size = len(data)
    index = 0
    while index < size:
        yield data[index : index+n]
        index = index + n
    return

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        wad = Wad(sys.argv[1])
        for level in wad.levels:
            level.save_svg()
    else:
        print('You need to pass a WAD file as the only argument')
