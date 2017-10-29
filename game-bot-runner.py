import requests
import math
import time
import threading
import random
from threading import Thread
##from directkeys import A,W,S,D,PressKey, C, LCTRL, LSHIFT

port = "6001"

 
## Thread(target = PressKey(LSHIFT)).start()
enemykilled = False


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)

def moveStraight(distance):
    d= {"type":"forward","amount":distance*20}
    requests.post('http://localhost:'+port+'/api/player/actions', json = d)

def moveLeft(degrees):
    d= {"type":"left","target_angle": int(degrees)}
    requests.post('http://localhost:'+port+'/api/player/turn',json = d)

def moveRight(degrees):
    d= {"type":"right","target_angle": int(degrees)}
    requests.post('http://localhost:'+port+'/api/player/turn',json = d)

def moveBack(distance):
    d= {"type":"backward","amount":distance*2}
    requests.post('http://localhost:'+port+'/api/player/actions', json = d)

def strafe(d,a):
    q = {"type": d, "amount": a}
    requests.post('http://localhost:'+port+'/api/player/actions', json = q)

def getEnemies():
    env = requests.get('http://localhost:'+port+'/api/world/objects',json={'distance':100}).json()
    enemies=[]
    for obj in env:
        if(obj['type']== obj['type'].lower().upper() and obj['health']>0):
            enemies.append({"id":obj["id"],"distance":obj['distance'],"pos":{"x":obj["position"]["x"],"y":obj["position"]["y"]}})
    return(enemies)

def getLOS(id1,id2):
    return requests.get('http://localhost:'+port+'/api/world/los/'+str(id1)+'/'+str(id2))

def shoot():
    d = {'type':'shoot'}
    requests.post('http://localhost:'+port+'/api/player/actions',json=d)

def ifPossibleMove(d):
    d_d=[]
    for i in range(len(d)-1):
       d_d.append(abs(d[i+1]-d[i]))
    return mean(d_d)
    
def findPath():
    moveLeft(90)
    moveStraight(5)
    l_d=getNearestEnemy()["distance"]
    moveStraight(5)
    n_d=getNearestEnemy()["distance"]
    if(n_d>l_d):
        moveLeft(180)

def getNearestEnemy():
    distances = []
    ids = []
    for enemy in getEnemies():
        distances.append(enemy['distance'])
        ids.append(enemy['id'])
    
    for enemy in getEnemies():
        if(enemy['id']==ids[distances.index(min(distances))]):
            return enemy

def getAngle(ene):
    coord={}
    for enemy in requests.get('http://localhost:'+port+'/api/world/objects').json():
        if(enemy['type']=='Player'):
            coord = enemy['position']
    return math.atan2(ene["pos"]['y']-coord["y"],ene["pos"]['x']-coord["x"])


def getPlayerID():
    for enemy in requests.get('http://localhost:'+port+'/api/world/objects').json():
        if(enemy['type']=='Player'):
            return enemy['id']


def turn(angle):
    pi = math.pi
    if(angle<0):
        moveLeft(-1*(angle)*180/pi)
    else:
        moveRight((angle)*180/pi)

def huntcurenemy(enemy):
    l = True
    while(True):
          # you want to turn towards the enemy and then shoot when finished turning
##          turn(getAngle(enemy))
        for enemy in requests.get('http://localhost:'+port+'/api/world/objects').json():
            if(enemy['type']=='Player'):
                coord = enemy['position']
                moveLeft(math.degrees(math.atan2(ene["pos"]['y']-coord["y"],ene["pos"]['x']-coord["x"])))
        shoot()
        r = random.randint(5, 20)
        strafe("strafe_left",r) if l else strafe("strafe_right",r)
        l = not l
enemykilled = True
          

threads = []

##def distance(m,n):
##    x , y = m[1:-1].split(',')
##    print(n)
##    a , b = n[1:-1].split(',')
##    return math.sqrt((float(b)-float(y))**2 + (float(a)-float(x))**2)

if __name__ == "__main__":
##    txt = open('vertices.txt','r').read().split('&')
##
##    for t in txt:
##        print(t)
##        print("-----")
##
##    vertices=[]
##    for i in range(len(txt)-1):
##        vertices.append((txt[i],txt[i+1],distance(txt[i],txt[i+1])))
##
##    print(vertices)
##    

##    t = threading.Thread(target=moveStraight,args=(2,))
##    threads.append(t)
##    t.start()
##    
        
    player_id= getPlayerID()
##    untilAllDead = False

    while(True):
        ene = getNearestEnemy()
          # you want to turn towards the enemy and then shoot when finished turning
##          turn(getAngle(enemy))
        for enemy in requests.get('http://localhost:'+port+'/api/world/objects').json():
            if(enemy['type']=='Player'):
                coord = enemy['position']
                moveLeft(math.degrees(math.atan2(ene["pos"]['y']-coord["y"],ene["pos"]['x']-coord["x"])))
        shoot()
        shoot()
        shoot()

##    while(True):
##        here goes code to go to end. only hunts for enemy if it finds one
##        PressKey(LSHIFT)
##        enemy = getNearestEnemy()
####        if(getLOS(player_id,enemy['id'])):
####            shoot()
##        turn(getAngle(enemy))
##        if(getLOS(player_id,enemy['id'])):
##            shoot()
##        moveStraight(5)
##        if(getLOS(player_id,enemy['id'])):
##            shoot()
    
##        turn(getAngle(enemy))
##        d = []
##        for i in range(2):
##            enemy = getNearestEnemy()
##            moveStraight(3)
##            d.append(enemy["distance"])
##            
##        if(ifPossibleMove(d)>30):
##            moveStraight(20)
##        else:
##            findPath()
##    ##        turn(getAngle(enemy))
##    ##        moveStraight(50)
##        if(getLOS(player_id,enemy['id'])):
##            shoot()
##        time.sleep(0.2)
####    moveLeft(math.pi)
