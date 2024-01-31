# import requests
# import pprint as pp

# url = 'http://127.0.0.1:5000/submit-guess'
# headers = {'Content-Type': 'application/json'}
# while True:
#     guess_name = input('guess: ')
#     payload = {'guess': guess_name}
#     response = requests.post(url, json=payload, headers=headers)
#     game_status = response.json()['game_status']
#     pp.pprint(game_status, width=41)

from game import Game

Game()