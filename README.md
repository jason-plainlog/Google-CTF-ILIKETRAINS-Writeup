# Google-CTF-ILIKETRAINS-Writeup
> Jason1024 @ Balsn

![](https://i.imgur.com/subEZmq.jpg)

Open the saved game with OpenTTD, and we will immediately see a complex rail system, which turns out to be a combinational logic circuit with 32-bit input and 1-bit output. The flag is the input bits that can make the output bit true.

After watching many OpenTTD signal logic tutorial videos, we can identify the only three kinds of logic gates (thank gods there are only three) used in the circuit: [not, and, or](https://wiki.openttdcoop.org/Logic#Logic_gates). The problem now becomes extracting the map out of the game, identifying the wires and logic gates, and finding a legitimate input.

To dump the circuit out of OpenTTD, I found that OpenTTD allows users to write [AI scripts](https://wiki.openttd.org/en/Development/Script/). The [API](https://docs.openttd.org/ai-api/annotated.html) enables us to check what's on each tile, whether it's a bridge or rail track, and the direction—noted that we only need the information of rail tracks and bridges to identify wires and logic gates. The dumping costs about 20 min to dump the whole map into a text file. Below is the AI script I used to dump the map info:

```=
class TestAI extends AIController{
  constructor(){} 
}
 
function TestAI::Start(){
  AILog.Info("TestAI Started.");

  // 1220 * 3742
  for(local x = 0; x < 1220; x++){
    for(local y = 0; y < 3742; y++){
      local p = (x << 12) + y;
        
      if(AIRail.IsRailTile(p)){
        AILog.Warning("rail (" + x + ", " + y + ", " + AIRail.GetRailTracks(p) + ")");
      }else if(AIBridge.IsBridgeTile(p)){
        local end = AIBridge.GetOtherBridgeEnd(p)
        AILog.Warning("bridge (" + x + ", " + y + ") to (" + (end >> 12) + ", " + (end % 4096) + ")");
      }
    }
  }
}
 
function TestAI::Save(){
  local table = {};	
  return table;
}
 
function TestAI::Load(version, data){
   AILog.Info(" Loaded");
}
 
function TestAI::SetCompanyName(){}
```

To use it yourself, save this as `main.nut` and the example `info.nut` to the ai script loading folder; on macOS, it’s `~/Documents/OpenTTD/ai/`. Load and start the ai after starting the game with the command: `./openttd -d script=5 &> ~/map_dump`, and viola, you get the dumped map! The dumped text file looks like the below:

```=
...
2022-07-03 20:12:27.531 openttd[85031:14673087] void NSFreeMapTable(NSMapTable * _Nonnull): map table argument is NULL
dbg: [freetype] Font is missing glyphs to display char 0x672A in medium font size
2022-07-03 20:12:39.191 openttd[85031:14673015] TSM AdjustCapsLockLEDForKeyTransitionHandling - _ISSetPhysicalKeyboardCapsLockLED Inhibit
dbg: [script] [2] [I] 0.7 API compatibility in effect:
dbg: [script] [2] [I]  - AITown::GetLastMonthProduction's behaviour has slightly changed.
dbg: [script] [2] [I]  - AISubsidy::GetDestination returns STATION_INVALID for awarded subsidies.
dbg: [script] [2] [I]  - AISubsidy::GetSource returns STATION_INVALID for awarded subsidies.
dbg: [script] [2] [I] TestAI Started.
dbg: [script] [2] [W] rail (1, 2, 8)
dbg: [script] [2] [W] rail (1, 3, 1)
dbg: [script] [2] [W] rail (1, 4, 32)
dbg: [script] [2] [W] rail (2, 2, 2)
dbg: [script] [2] [W] rail (2, 4, 2)
dbg: [script] [2] [W] rail (3, 2, 16)
dbg: [script] [2] [W] rail (3, 3, 3)
dbg: [script] [2] [W] rail (3, 4, 4)
dbg: [script] [2] [W] rail (4, 3, 2)
dbg: [script] [2] [W] rail (5, 7, 1)
dbg: [script] [2] [W] bridge (5, 8) to (5, 26)
dbg: [script] [2] [W] bridge (5, 26) to (5, 8)
dbg: [script] [2] [W] rail (5, 27, 32)
...
```

With the dumped map info, we can reconstruct the map with python and parse the wires and logic gates. I split each tile into 3x3 pixels to describe the rail track in multiple directions. And record the bridge entrance and exit with a python dict. Below is just a tiny upper-left corner of the whole circuit. The white lines are rail tracks, and the red lines are bridges. The other colored parts are logic gates identified. You can find the uncropped image in [my Github repo]().

![](https://i.imgur.com/He01za2.jpg)

After plotting the rail tracks and finding the logic gates, I wipe the logic gate wires off and record the occurrences and position of inputs and output of each logic gate. Then, to identify connected wires and bridges, I BFS the map to get the variables we will use later in z3.

By BFS the map, we get certain wires $w_0, w_1, \dots$, and logic relationships given by logic gates and the wires connected to, for example, $w_2 = w_1 \cap w_2$. To solve the legitimate input for the circuit, I use the z3 solver to solve the constraints composed by 1. the rules of logic gates and 2. the output bit should be true. After z3 answered, I checked it by wiring the answer in OpenTTD, and the output turned on within 2 seconds after I set the input to the answer.

![](https://i.imgur.com/QZNpm45.jpg)

The full content of `payload.py`:

```python=
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
```

The output of the payload script:

```
Dumping Tracks and Bridges: 100%|█████████████████████████████████████████| 741697/741697 [00:14<00:00, 50406.93it/s]
Identifying Logic Gates: 100%|██████████████████████████████████████████████████| 3660/3660 [00:23<00:00, 157.07it/s]
bridges:  26666
not gate:  577
or gate:  1250
and gate:  1497
BFS Tracks and Bridges to get Wires: 100%|██████████████████████████████████████| 3658/3658 [00:19<00:00, 183.23it/s]
wires: 3357
CTF{11100010101000111000101010100011}
Sanity Check:  Pass!
```

Flag: `CTF{11100010101000111000101010100011}`
