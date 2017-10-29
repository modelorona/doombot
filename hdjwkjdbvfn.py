from directkeys import A,W,S,D,PressKey, C, LCTRL,LSHIFT

import numpy as np
from PIL import ImageGrab
import cv2
import time
import requests

from ctypes import windll


dc= windll.user32.GetDC(0)

sensitivity=10

def getpixel(x,y,w,h):
    screen = []
    for x in range(w):
        xlis=[]
        for y in range(h):            
            xlis.append(windll.gdi32.GetPixel(dc,x+w,y+h))
        screen.append(xlis)
    return np.array(screen)



def process_img(image):
    original_image = image
    # convert to gray
    processed_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # edge detection
    processed_img =  cv2.Canny(processed_img, threshold1 = 200, threshold2=300)
    return processed_img


def screen_record(): 
    last_time = time.time()
    while(True):
        # 800x600 windowed mode
        screen =  np.array(ImageGrab.grab(bbox=(0,40,820,680)))
        last_time = time.time()
        new_screen = process_img(screen)
        cv2.imshow('window',new_screen)
        cv2.imshow('window',cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))
        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break


##env = requests.get('http://localhost:6001/api/world/objects',json={'distance':100}).json()

def getEnemies():
    env = requests.get('http://localhost:6001/api/world/objects',json={'distance':100}).json()
    enemies=[]
    for obj in env:
        if(obj['type']== obj['type'].lower().upper() and obj['health']>0):
            enemies.append({"distance":obj['distance'],"pos":{"x":obj["position"]["x"],"y":obj["position"]["y"]}})
    return(enemies)

def moveRight():
    player = requests.post('http://localhost:6001/api/player/actions',json={"type":"turn-right","amount":sensitivity})

def moveLeft():
    player = requests.post('http://localhost:6001/api/player/actions',json={"type":"turn-left","amount":sensitivity})



def shoot():
    player = requests.post('http://localhost:6001/api/player/actions',json={"type":"shoot"})


center = (400,380)


def direction(x,y,w,h):
    center_obj = ((x+w)/2 , (y+h)/2)
    if((center_obj[0]-center[0])>0 and (center_obj[1]-center[1])>0):
        moveRight()
    elif((center_obj[0]-center[0])<0 and (center_obj[1]-center[1])<0):
        moveLeft()

    if(abs(center_obj[0]-center[0])<5):
        shoot()

def main():
    while(True):
        # 800x600 windowed mode
        image =  np.array(ImageGrab.grab(bbox=(0,40,820,680)))
##        cv2.imshow('window',cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))
##        image = cv2.imread(screen)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.Canny(gray, threshold1=200, threshold2=300)
        faceCascade = cv2.CascadeClassifier(r"C:\Users\Anguel\Desktop\python-bot\haarcascade_frontalface_default.xml")
        faces = faceCascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
            flags = cv2.CASCADE_SCALE_IMAGE
        )
##        print(faces)
        if(len(faces)!=0):
            x,y,w,h = faces[0]
            direction(x,y,w,h)
        
        
##        for (x, y, w, h) in faces:
##            cv2.rectangle(image, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imshow("Faces found" ,image)
##        cv2.waitKey(0)

        if cv2.waitKey(25) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break


main()
