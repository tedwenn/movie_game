from flask import Flask, jsonify, request
from flask_cors import CORS
from game import Game

app = Flask(__name__)
game = Game()
CORS(app)

@app.route('/')
def home():
    return "Hello, World!"

@app.route('/submit-guess', methods=['POST'])
def submit_guess():
    print('guess submitted!')
    data = request.json
    guess = data.get('guess')
    game.guess(guess)
    response = {
        'status': 'success',
        'message': f'Your guess was: {guess}',
        'game_status': game.status
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True)
