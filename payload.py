from PIL import Image, ImageDraw
from tqdm import tqdm
import numpy as np
import z3

img = Image.new("RGB", (1220 * 3, 3742 * 3))
img2 = img.copy()

draw = ImageDraw.Draw(img, "RGBA")
bridges = dict()

with open('./map_dump', 'r') as f:
    for line in tqdm(f.readlines(), desc="Dumping Tracks and Bridges"):
        if not line.startswith("dbg: [script] [2] [W]"):    continue
        line = line[len("dbg: [script] [2] [W] "):-1]
        type = line.split()[0]
        
        if type == 'rail':
            x, y, t = eval(line[5:])

            # identify the rail direction and plot it into the 3x3 pixels
            if t & 1:
                for i in range(-1, 2):
                    img.putpixel((x * 3 + 1, y * 3 + 1 + i), (255, 255, 255))
                    img2.putpixel((x * 3 + 1, y * 3 + 1 + i), (255, 255, 255))
            if t & 2:
                for i in range(-1, 2):
                    img.putpixel((x * 3 + 1 + i, y * 3 + 1), (255, 255, 255))
                    img2.putpixel((x * 3 + 1 + i, y * 3 + 1), (255, 255, 255))
            if t & 4:
                img.putpixel((x * 3 + 1, y * 3), (255, 255, 255))
                img.putpixel((x * 3, y * 3 + 1), (255, 255, 255))
                img2.putpixel((x * 3 + 1, y * 3), (255, 255, 255))
                img2.putpixel((x * 3, y * 3 + 1), (255, 255, 255))
            if t & 32:
                img.putpixel((x * 3 + 1, y * 3), (255, 255, 255))
                img.putpixel((x * 3 + 2, y * 3 + 1), (255, 255, 255))
                img2.putpixel((x * 3 + 1, y * 3), (255, 255, 255))
                img2.putpixel((x * 3 + 2, y * 3 + 1), (255, 255, 255))
            if t & 16:
                img.putpixel((x * 3 + 1, y * 3 + 2), (255, 255, 255))
                img.putpixel((x * 3, y * 3 + 1), (255, 255, 255))
                img2.putpixel((x * 3 + 1, y * 3 + 2), (255, 255, 255))
                img2.putpixel((x * 3, y * 3 + 1), (255, 255, 255))
            if t & 8:
                img.putpixel((x * 3 + 1, y * 3 + 2), (255, 255, 255))
                img.putpixel((x * 3 + 2, y * 3 + 1), (255, 255, 255))
                img2.putpixel((x * 3 + 1, y * 3 + 2), (255, 255, 255))
                img2.putpixel((x * 3 + 2, y * 3 + 1), (255, 255, 255))

            img.putpixel((x * 3 + 1, y * 3 + 1), (255, 255, 255))
            img2.putpixel((x * 3 + 1, y * 3 + 1), (255, 255, 255))
        
        if type == 'bridge':
            (x1, y1), (x2, y2) = map(eval, line[7:].split('to'))
            x1 = x1 * 3 + 1
            y1 = y1 * 3 + 1
            x2 = x2 * 3 + 1
            y2 = y2 * 3 + 1

            if x1 == x2:
                y1 += 2 if (y1 > y2) else -2
                y2 += 2 if (y2 > y1) else -2
            if y1 == y2:
                x1 += 2 if (x1 > x2) else -2
                x2 += 2 if (x2 > x1) else -2

            p1 = (x1, y1)
            p2 = (x2, y2)
            bridges[p1] = p2
            bridges[p2] = p1
            draw.line([p1, p2], (255, 0, 0, 150))

img2 = img2.convert('1')
draw2 = ImageDraw.Draw(img2, '1')

w, h = 1220*3, 3742*3
data = np.array(img2.getdata()).reshape((h, w)).transpose()

# identify logic gates, then remove the railtracks of logic gates
notgates, orgates, andgates = [], [], []

for x in tqdm(range(w), "Identifying Logic Gates"):
    for y in range(h):
        if data[x][y]:
            # or gate
            if x + 9 < w and y + 4 < h:
                found = True
                for i in range(10):
                    if not (data[x+i][y] and data[x+i][y+3]):
                        found = False
                        break
                for i in range(4):
                    if not (data[x][y+i] and data[x+9][y+i]):
                        found = False
                        break
                if found:
                    draw.rectangle([(x-1, y), (x+10,y+3)], (0, 0, 255, 150))
                    draw2.rectangle([(x-1,y), (x+10, y+3)], 0)
                    img.putpixel((x, y-1), (0, 0, 255, 150))    # or input
                    img.putpixel((x+9, y-1), (0, 0, 255, 150))  # or input
                    img.putpixel((x+6,y+4),(0, 0, 255, 150))    # or output
                    orgates.append(((x, y-1),(x+9, y-1),(x+6,y+4)))

            # not gate
            if x + 7 < w and y + 7 < h:
                found = True
                for i in range(7):
                    if not (data[x+i][y] and data[x][y+i] and data[x+6][y+i] and data[x+i][y+6]):
                        found = False
                        break
                if found and data[x+3][y+3]:
                    draw.rectangle([(x, y), (x+6,y+6)], (0, 255, 0, 150))
                    draw2.rectangle([(x, y), (x+6, y+6)], 0)    # erase gate wires
                    img.putpixel((x+3,y-1), (0, 255, 0, 150))   # not input
                    img.putpixel((x+7,y+3), (0, 255, 0, 150))   # not output
                    notgates.append(((x+3,y-1),(x+7,y+3)))

            # and gate
            if x + 7 < w and y + 7 < h:
                found = True
                for i in range(4):
                    if not (data[x+i][y] and data[x+3+i][y+3] and data[x+3][y+i] and data[x+6][y+i] and data[x+6][y+3+i]):
                        found = False
                        break
                if found and not data[x][y+1]:
                    draw.rectangle([(x, y), (x+6, y+6)], (0,255,255,150))
                    draw2.rectangle([(x, y), (x+6, y+6)], 0)
                    img.putpixel((x, y - 1), (0, 255,255,150))      # and input
                    img.putpixel((x+6, y - 1), (0, 255,255,150))    # and input
                    img.putpixel((x+6, y+7), (0, 255,255,150))      # and output
                    andgates.append(((x, y - 1), (x+6, y - 1), (x+6, y+7)))

print("bridges: ", len(bridges))
print("not gate: ", len(notgates))
print("or gate: ", len(orgates))
print("and gate: ", len(andgates))

img.save('circuit.png')

data = np.array(img2.getdata()).reshape((h, w)).transpose()
wireid = np.zeros((w, h), dtype=np.uint32)
dx, dy = [-1, 0, 1, 0], [0, 1, 0, -1]

def bfs(x, y, id):
    wireid[x][y], data[x][y] = id, 0
    queue = [(x, y)]

    while len(queue):
        (x, y), queue = queue[0], queue[1:]
        for i in range(4):
            nx, ny = x+dx[i], y+dy[i]
            if data[nx][ny]:
                wireid[nx][ny], data[nx][ny] = id, 0
                queue.append((nx, ny))
        if (x, y) in bridges:
            nx, ny = bridges[(x, y)]
            if data[nx][ny]:
                wireid[nx][ny], data[nx][ny] = id, 0
                queue.append((nx, ny))

wirecnt = 1
for x in tqdm(range(1, w - 1), desc="BFS Tracks and Bridges to get Wires"):
    for y in range(1, h - 1):
        if data[x][y]:
            bfs(x, y, wirecnt)
            wirecnt += 1
print(f"wires: {wirecnt - 1}")

wires = {i: z3.Bool(f"w{i}") for i in range(1, wirecnt)}
solver = z3.Solver()

# adding not relations
for ((ix, iy), (ox, oy)) in notgates:
    wi = wires[wireid[ix][iy]]
    wo = wires[wireid[ox][oy]]
    solver.add(wo == z3.Not(wi))
solver.check()

# adding and relations
for ((x1, y1), (x2, y2), (ox, oy)) in andgates:
    w1 = wires[wireid[x1][y1]]
    w2 = wires[wireid[x2][y2]]
    wo = wires[wireid[ox][oy]]
    solver.add(wo == z3.And(w1, w2))
solver.check()

# adding or relations
for ((x1, y1), (x2, y2), (ox, oy)) in orgates:
    w1 = wires[wireid[x1][y1]]
    w2 = wires[wireid[x2][y2]]
    wo = wires[wireid[ox][oy]]
    solver.add(wo == z3.Or(w1, w2))

solver.check()

inputs = [wires[wireid[16 + 3*i][21]] for i in range(32)]
output = wires[wireid[22][h-13]]
solver.add(output == True)
solver.check()

m = solver.model()
print("CTF{" + "".join(["1" if m[wi] else "0" for wi in inputs]) + "}")
print("Sanity Check: ", "Pass!" if m[output] else "Failed!")