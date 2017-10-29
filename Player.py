import requests

class Player(object):
    ## represents the player. will allow basic control
    def __init__(self):
        pass

    ## moves player based on parameters
    def turn(self, direction, angle):
        d = {"type": direction, "target_angle": angle}
        r = requests.post('http://localhost:6001/api/player/turn', params = d)

    def shoot(self):
        d = {"type": "shoot"}
        r = requests.get('http://localhost:6001/api/player/actions', params = d)

p = Player()
## p.shoot()
p.turn("left", 96)
