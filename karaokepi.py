

#should redo virtualenv WITH site-packages so it sees the pykaraoke install
#*this worked!!!!

#gevent (i love this technology)
from gevent import monkey
monkey.patch_all()
#from gevent.wsgi import WSGIServer
from gevent.pywsgi import WSGIServer


#python standard imports
import glob
import os
import subprocess
import time

#flask specific imports
from flask import Flask, session, redirect, url_for, escape, request, jsonify, Response, stream_with_context
import vlc_controller


SONG_PATH = '/Users/ralphcaraveo/Karaoke'

#used for karaoke pi admin console, simply just to manage the admin console for KaraokePi
ADMIN_ACCOUNT = 'admin'
ADMIN_PASSWORD = 'password123'

karaoke_controller = vlc_controller.Controller()
song_db = []

app = Flask(__name__)
app.debug = True
app.secret_key = 'Booga Time!' #secret session key more info at Flask documentation site

@app.before_first_request
def initialize():
    karaoke_controller.start()
    build_song_db()

def build_song_db():
    global song_db
    files = glob.glob(os.path.join(SONG_PATH, '*.mp3'))

    for file_path in files:
        name = os.path.basename(file_path)
        artist, song = name.split('-')
        song = song.strip().replace('.mp3', '')
        artist = artist.strip()
        song_db.append({'artist':artist, 'track':{'t':song,'fp':name, 'tid':000}})


#static files test
@app.route("/mobile")
def mobile():
    return redirect(url_for('static', filename='index.html'))

@app.route("/swipe.js")
def swipe():
    return redirect(url_for('static', filename="swipe.js"))

@app.route("/karaoke-star.jpg")
def karaoke_image():
    return redirect(url_for('static', filename="karaoke-star.jpg"))    


@app.route("/")
def index():
    return redirect(url_for("mobile"))
    # if 'username' in session:
    #     return 'Logged in as %s' % escape(session['username'])
    # return "Hello World!, welcome to KaraokePi!"

@app.route("/songs")
def songs():
    files = glob.glob(os.path.join(SONG_PATH, '*.cdg'))
    return jsonify(dict(count=len(files), songs=files))

@app.route("/search/<keyword>")
def search(keyword):
    if keyword is not None:
        keyword = keyword.lower()
    resultlist = []
    
    for coll in song_db:
        if keyword in coll['artist'].lower():  
            resultlist.append(coll)
    return jsonify({'results':resultlist})
     
@app.route('/piaddress')
def piaddress():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("gmail.com",80))
    result = s.getsockname()[0]
    s.close()
    return result

def is_logged_in():
    return not session.get("username") is None

@app.route("/loginstatus")
def login_status():
    if is_logged_in():
        return "User is logged in as: %s" % session['username']
    else:
        return "user is not logged in"

@app.route("/login/<username>/<password>")
def login(username, password):
    if not session.get("username") is None:
        session.pop('username', None)

    session["password"] = password    
    session['username'] = username
    return jsonify({'result':"OK", 'loggedIn':False})

#reference implementation of login
# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         session['username'] = request.form['username']
#         return redirect(url_for('index'))
#     return '''
#         <form action="" method="post"><p><input type="text" name="username" /></p>
#         <p><input type="submit" value="login" /></p></form>'''

@app.route('/logout')
def logout():
    #remove the username from the session if it's there
    session.pop('username', None)
    return jsonify({'result':"OK"})
    #return redirect(url_for('index'))        

#example of generator, this BLOCKS all other requests until finished NOTICE the sleep
#implies that Flask is single threaded by nature.
#with gevent this is working while yielding to other requests (Excellent!)
@app.route('/busy')
def busy_request():
    def generate():
        for x in xrange(10):
            yield "Hello"
            time.sleep(1)
    return Response(generate(), mimetype='text/event-stream', direct_passthrough=True)

#alternative from Flask documentation
@app.route('/stream')
def streamed_response():
    def generate():
        yield 'Hello '
        time.sleep(1)
        yield 'Hi'
        time.sleep(5)
        yield '!'
    return Response(stream_with_context(generate()))    
    
@app.route("/queue/<artist>")
def queue_artist(artist):
    karaoke_controller.enqueue_file(artist)

@app.route("/play/<artist>")
def play_artist(artist):
    karaoke_controller.play_file(artist)
    return jsonify(dict(result="OK"))

@app.route("/resume")
def resume_player():
    karaoke_controller.play()
    return jsonify(dict(result="OK"))

@app.route("/pause")
def pause_player():
    karaoke_controller.toggle_pause()
    return 'Paused'

@app.route("/stop")
def stop_playing():
    karaoke_controller.stop()
    return 'Stopped'

@app.route("/shutdown")
def shutdown():
    karaoke_controller.quit()
    return jsonify(dict(result="OK"))

@app.route("/fullscreen")
def fullscreen():
    karaoke_controller.toggle_fullscreen()
    return 'toggled full screen'    

if __name__ == "__main__":
    http_server = WSGIServer(('', 5555), app)  #can i run gevent on raspberry pi?
    http_server.serve_forever()
    #flask style
    #app.run('0.0.0.0', port=5555)


