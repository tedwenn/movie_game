from flask import Flask, jsonify
from game import Game

app = Flask(__name__)
game = Game(747188)

@app.route('/')
def home():
    return "Hello, World!"

@app.route('/submit_guess', methods=['POST'])
def submit_guess():
    # Extract guess from the request
    data = request.json
    guess = data.get('guess')
    game.guess(guess)
    return jsonify({"message": "Guess submitted!"}), 200

if __name__ == '__main__':
    app.run(debug=True)
