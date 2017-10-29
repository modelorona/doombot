#!/usr/bin/env python3

import struct
import re
import math
import requests
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
        r = requests.get("http://localhost:6001/api/world").json()
        episode = r["episode"]
        maps = r["map"]
        self.name = "E" + str(episode) + "M" + str(maps)
        for level in self.levels:
            if level.name == self.name:
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

    def there_is_not_an_intersection(self, dot, other_dot, line_vertices, lines):
        intersections = 0
        for line in lines:
            if self.oppSides(dot, other_dot, line_vertices[line.a], line_vertices[line.b]) and self.oppSides(line_vertices[line.a], line_vertices[line.b], dot, other_dot) and self.boundingBox(dot, other_dot, line_vertices[line.a], line_vertices[line.b]) and line.is_one_sided():
                return False
        return True


    def generate_visibility_graph(self, line_vertices, lines, inside_vertices):
        inside_vertices_count = [0] * len(inside_vertices)
        edges = []
        index1 = 0
        index2 = 0
        for index1, dot in enumerate(inside_vertices):
            if inside_vertices_count[index1] >= 10 or inside_vertices_count[index2] >= 10:
                continue
            for index2, other_dot in enumerate(inside_vertices):
                if inside_vertices_count[index1] >=10 or inside_vertices_count[index2] >= 10:
                    continue
                if dot[0] != other_dot[0] and dot[1] != other_dot[1]:
                    if self.there_is_not_an_intersection(dot, other_dot,line_vertices, lines):
                        edges += [Edge(index1, index2, math.hypot(other_dot[0] - dot[0], other_dot[1] - dot[1]))]

                        inside_vertices_count[index1] += 1
                        inside_vertices_count[index2] += 1
        return edges
            
    def square_point_pattern(self):
        temp_vertices = []
        x = self.lower_left[0] + 70.0
        while x < self.upper_right[0]:
            y = self.lower_left[1] + 70.0
            while y < self.upper_right[1]:
                temp_vertices += [(x,y)]
                y += 70.0
            x += 70.0
        return temp_vertices

    def hopefully_better_point_pattern(self):
        temp_vertices = []
        for point in self.vertices:
            temp_vertices += [(point[0], point[1] + 50)]
            temp_vertices += [(point[0] + 43, point[1] -25)]
            temp_vertices += [(point[0] - 43, point[1] -25)]
        return temp_vertices

        

    def generate_inside_points(self):
        possible_vertices = self.square_point_pattern()

        for dot in possible_vertices:
            intersections = 0
            for line in self.lines:
                if self.oppSides(self.vertices[line.a], self.vertices[line.b], dot, (self.upper_right[0] + 20, self.upper_right[1] + 20)) and self.oppSides(dot, (self.upper_right[0] + 20, self.upper_right[1] + 20), self.vertices[line.a], self.vertices[line.b]) and self.boundingBox(self.vertices[line.a], self.vertices[line.b], dot, (self.upper_right[0] + 20, self.upper_right[1] + 20)) and line.is_one_sided():
                    intersections += 1
            if intersections % 2 == 1:
                self.inside_vertices += [dot]

    def find_route(self, start, finish):
        inside_vertices_copy = self.inside_vertices[:]
        inside_vertices_copy = [start] + inside_vertices_copy + [finish]

        edges = self.generate_visibility_graph(self.vertices, self.lines, inside_vertices_copy)
        
        inside_vertices_copy[0] = Vertex(start, -1, 0)
        i = 1
        while i < len(inside_vertices_copy):
            inside_vertices_copy[i] = Vertex(inside_vertices_copy[i], None, 65535)
            i += 1
        
        for edge in edges:
            if(edge.a not in inside_vertices_copy[edge.b].adj):
                inside_vertices_copy[edge.b].adj += [edge.a]
                print(edge.a, edge.b)
            if(edge.b not in inside_vertices_copy[edge.a].adj):
                inside_vertices_copy[edge.a].adj += [edge.b]
                print (edge.a, edge.b)
        k_vertex_set = [0]
        inside_vertices_copy[k_vertex_set[0]].distance = 0
        #print inside_vertices_copy[k_vertex_set[0]].distance 
        u_vertex_set = range(1, len(inside_vertices_copy))
        #print u_vertex_set

        
        def update_weights(newest_item):
            #print newest_item, inside_vertices_copy[newest_item].distance
            for vertex in inside_vertices_copy[newest_item].adj:
                print(vertex, inside_vertices_copy[vertex].distance, inside_vertices_copy[newest_item].distance + math.hypot(inside_vertices_copy[vertex].point[0] - inside_vertices_copy[newest_item].point[0], inside_vertices_copy[vertex].point[1] - inside_vertices_copy[newest_item].point[1]))
                if(inside_vertices_copy[vertex].distance > inside_vertices_copy[newest_item].distance + math.hypot(inside_vertices_copy[vertex].point[0] - inside_vertices_copy[newest_item].point[0], inside_vertices_copy[vertex].point[1] - inside_vertices_copy[newest_item].point[1])):
                    inside_vertices_copy[vertex].distance = inside_vertices_copy[newest_item].distance + math.hypot(inside_vertices_copy[vertex].point[0] - inside_vertices_copy[newest_item].point[0], inside_vertices_copy[vertex].point[1] - inside_vertices_copy[newest_item].point[1])
                    inside_vertices_copy[vertex].prev = newest_item
        
        newest_item = k_vertex_set[0]
        update_weights(newest_item)
        #print start, inside_vertices_copy[0].point, inside_vertices_copy[0].adj, "numba1"
        while(len(u_vertex_set) > 0):
            print(len(u_vertex_set))
            min_dis = u_vertex_set[0]
            for vertex in u_vertex_set:
                if inside_vertices_copy[vertex].distance < inside_vertices_copy[min_dis].distance:
                    min_dis = vertex
            k_vertex_set.append(min_dis)
            u_vertex_set.remove(min_dis)
            newest_item = min_dis
            #print newest_item
            update_weights(newest_item)
            if(inside_vertices_copy[newest_item].point == finish):
                #print("{0}  {1}").format(inside_vertices_copy[newest_item].point, finish)
                break
            
       
        path = []
        current = newest_item
        while True:
            #print current
            path.append(inside_vertices_copy[current].point)
            current = inside_vertices_copy[current].prev
            if current == -1:
                break
        return path[::-1]

    def moveStraight(self,distance):
        d= {"type":"forward","amount":distance*5}
        requests.post('http://localhost:6001/api/player/actions', json = d)

    def moveLeft(self,degrees):
        d= {"type":"left","target_angle": int(degrees)}
        requests.post('http://localhost:6001/api/player/turn',json = d)

    def moveRight(self,degrees):
        d= {"type":"right","target_angle": int(degrees)}
        requests.post('http://localhost:6001/api/player/turn',json = d)


    def getEnemies(self):
        env = requests.get('http://localhost:6001/api/world/objects',json={'distance':100}).json()
        enemies=[]
        for obj in env:
            if(obj['type']== obj['type'].lower().upper() and obj['health']>0):
                enemies.append({"id":obj["id"],"distance":obj['distance'],"pos":{"x":obj["position"]["x"],"y":obj["position"]["y"]}})
        return(enemies)

    def getLOS(self,id1,id2):
        return requests.get('http://localhost:6001/api/world/los/'+str(id1)+'/'+str(id2))


    def getNearestEnemy(self):
        distances = []
        ids = []
        for enemy in self.getEnemies():
            distances.append(enemy['distance'])
            ids.append(enemy['id'])
        
        for enemy in self.getEnemies():
            if(enemy['id']==ids[distances.index(min(distances))]):
                return enemy

    def getAngle(self,y,x): 
        return math.atan2(y,x)

    def getPlayerID(self):
        for enemy in requests.get('http://localhost:6001/api/world/objects').json():
            if(enemy['type']=='Player'):
                return enemy['id']

    
    def turn(self,angle):
        pi = math.pi
        if(angle<0):
            self.moveLeft(-1*(angle)*180/pi)
        else:
            self.moveRight((angle)*180/pi)


    
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
        for dot in self.inside_vertices:
            dwg.add(dwg.circle(self.normalize(dot),1, stroke='#00ff00', stroke_width=30))
        
        self.visibility_edges = self.generate_visibility_graph(self.vertices, self.lines, self.inside_vertices)

        r = requests.get("http://localhost:6001/api/player").json()
        start = (r["position"]["x"], r["position"]["y"])
        enemy = self.getNearestEnemy()["pos"]
        route = self.find_route(start, (enemy["x"],enemy["y"]))
        
        prev_dot = start
        i=1
        next_dot = route[i]
        for dot in route:
            print(str(dot) + "---"+ str(next_dot))
            self.turn(self.getAngle(next_dot[1],next_dot[0]))
            self.moveStraight(1)
            if(len(route)-i==1):
                break
            else:
                next_dot= route[i+1]
            i+=1
            a = self.normalize(prev_dot)
            b = self.normalize(dot)
                
            dwg.add(dwg.line(a, b, stroke='#007777', stroke_width=10))
            prev_dot = dot

        if(len(self.getEnemies())!=0):        
            self.save_svg()

##        for line in self.visibility_edges:
##            dwg.add(dwg.circle(self.normalize(start),1, stroke='#ffff00', stroke_width=50))
##            a = self.normalize(self.inside_vertices[line.a])
##            b = self.normalize(self.inside_vertices[line.b])
##            
##            dwg.add(dwg.line(a, b, stroke='#666', stroke_width=3))
##
##        for line in self.lines:
##            a = self.normalize(self.vertices[line.a])
##            b = self.normalize(self.vertices[line.b])
##			
##            if line.is_one_sided():
##                dwg.add(dwg.line(a, b, stroke='#333', stroke_width=10))
##            else:
##                dwg.add(dwg.line(a, b, stroke='#999', stroke_width=3))
##            dwg.add(dwg.circle(a,1, stroke='#ff0000', stroke_width=20))
##
##        dwg.save()

class Edge(object):
    def __init__(self, index1, index2, distance):
        self.a = index1
        self.b = index2
        self.distance = distance

class Vertex(object):
    def __init__(self, point, prev, distance):
        self.point = point
        self.prev = prev
        self.distance = distance
        self.adj = []

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
            if wad.name == level.name:
                level.save_svg()
    else:
        print('You need to pass a WAD file as the only argument')
