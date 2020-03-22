from aiohttp import web
import socketio

bots_list = set()
sid_to_bot = {}

sio = socketio.AsyncServer(cors_allowed_origins="*")
app = web.Application()
sio.attach(app)

# async def index(request):
#     """Serve the client-side application."""
#     with open('index.html') as f:
#         return web.Response(text=f.read(), content_type='text/html')

@sio.on('connect')
def connect(sid, environ):
    print("connect ", sid)

@sio.on('running')
async def running(sid, data):
    print("running ", data)
    bots_list.add(data)
    sid_to_bot[sid] = data
    bots_list_string =  " ".join(bots_list)
    print("sending list as: " + bots_list_string)
    await sio.emit("send_list", bots_list_string)

@sio.on('exiting')
async def running(sid, data):
    print("running ", data)
    bots_list.remove(data)
    await sio.emit("send_list", " ".join(bots_list))

@sio.on('get_list')
async def send_list(sid, data):
    print("send_list ", data)
    await sio.emit("send_list", " ".join(bots_list))

@sio.on('disconnect')
async def disconnect(sid):
    idx = sid_to_bot[sid] 
    bots_list.remove(idx)
    await sio.emit("send_list", " ".join(bots_list))
    print('disconnect ', sid)

# app.router.add_static('/static', 'static')
# app.router.add_get('/', index)

if __name__ == '__main__':
    web.run_app(app, port="1234")