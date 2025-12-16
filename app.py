import random
from flask import Flask, render_template, request
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*")

rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('create_game')
def handle_create():
    """創建房間：隨機生成 4 碼 ID，創建者當 X"""
    sid = request.sid
    
    # 生成不重複的 4 碼 ID
    while True:
        room_id = str(random.randint(1000, 9999))
        if room_id not in rooms:
            break
            
    rooms[room_id] = {'players': [sid]}
    join_room(room_id)
    
    # 回傳房間號碼給創建者
    emit('room_created', {'room_id': room_id, 'role': 'X', 'msg': f'房間已創建！號碼：{room_id} (等待對手...)'}, room=sid)

@socketio.on('join_game')
def handle_join(data):
    """加入房間：輸入 ID，加入者當 O"""
    room_id = data['room_id']
    sid = request.sid
    
    # 1. 檢查房間是否存在
    if room_id not in rooms:
        emit('error', {'msg': '找不到此房間號碼，請檢查後重試。'}, room=sid)
        return

    current_room = rooms[room_id]
    
    # 2. 檢查房間是否已滿
    if len(current_room['players']) >= 2:
        emit('error', {'msg': '該房間已滿'}, room=sid)
        return
        
    # 3. 避免重複加入
    if sid in current_room['players']:
        return

    # 加入成功
    current_room['players'].append(sid)
    join_room(room_id)
    
    # 通知加入者 (O)
    emit('init_game', {'role': 'O', 'msg': '加入成功！你是 O (後手)'}, room=sid)
    
    # 通知雙方遊戲開始
    emit('game_start', {'msg': '對手已加入，遊戲開始！', 'room_id': room_id}, room=room_id)

@socketio.on('move')
def handle_move(data):
    room_id = data['room_id']
    emit('update_board', data, room=room_id)

@socketio.on('leave_game')
def handle_leave(data):
    room_id = data.get('room_id')
    destroy_room(room_id)

@socketio.on('disconnect')
def handle_disconnect():
    sid = request.sid
    for room_id in list(rooms.keys()):
        if sid in rooms[room_id]['players']:
            destroy_room(room_id)
            break

def destroy_room(room_id):
    if room_id in rooms:
        players = rooms[room_id]['players']
        socketio.emit('room_closed', {'msg': '有玩家離開，房間已解散。'}, room=room_id)
        for pid in players:
            leave_room(room_id, sid=pid)
        del rooms[room_id]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)