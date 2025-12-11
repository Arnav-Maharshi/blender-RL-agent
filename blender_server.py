import bpy
import bmesh
import socket
import json
import struct

def reset_scene():
    # Ensure in Object Mode before deleting (otherwise deletion can fail)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select and delete everything
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    add_cube()
    bpy.ops.object.mode_set(mode='EDIT')
    
def update(me):
    bmesh.update_edit_mesh(me) # Update the BMesh

def add_cube(loc=(0,0,0), size=1):
    bpy.ops.mesh.primitive_cube_add(location=loc, size=size)
    obj = bpy.context.active_object
    print(f'Added cube:- {obj.name}')
    return obj

def Move(x,y,z):
    bpy.ops.transform.translate(value=(x,y,z))
    
def Scale(x,y,z):
    bpy.ops.transform.resize(value=(x,y,z))
    print("action: SCALE")

def Extrude(x=0,y=0,z=1): # Extrude the selected region along its normals
    # The 'TRANSFORM_OT_translate' operator is used to define the movement after extrusion
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value":(x, y, z)} # Extrude 1 unit along the Z-axis
    )
    print("action: EXTRUDE")
    
def calibrate_bmesh(bm, type: str): # ?? maybe we don't need an input argument??
    match type:
        case "faces":
            bm.faces.ensure_lookup_table()
        case "edges":
            bm.edges.ensure_lookup_table()
        case "verts":
            bm.verts.ensure_lookup_table()
        case "all":
            bm.faces.ensure_lookup_table()
            bm.edges.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

def get_current_bmesh(): # Access mesh data
    obj = bpy.context.edit_object
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    calibrate_bmesh(bm, "faces")
    calibrate_bmesh(bm, "verts")
    return bm, me
    
def select(obj, face, edge, vert, mode: str = "face"):
    if mode == "face":
        obj.faces[face].select = True
    elif mode == "edge":
        obj.edges[edge].select = True
    elif mode == "vert":
        obj.verts[vert].select = True
    
def select_top_face(bm):   # ?? maybe we don't need an input argument??
    top_faces = [f for f in bm.faces if f.normal.z > 0.9]
    for f in top_faces:
        #bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
        f.select = True
    print("action: SELECTED TOP FACE")

def deselect_all():
    bpy.ops.mesh.select_all(action='DESELECT') # deselect the faces in edit mode


def _get_obs():
    bm, _ = get_current_bmesh()
    calibrate_bmesh(bm, "verts")
    calibrate_bmesh(bm, "faces")

    if len(bm.verts) == 0:
        return [0.0,0.0,0.0]

    # Calculate Bounding Box dimensions manually
    x_co = [v.co.x for v in bm.verts]
    y_co = [v.co.y for v in bm.verts]
    z_co = [v.co.z for v in bm.verts]

    width = max(x_co) - min(x_co)
    depth = max(y_co) - min(y_co)
    height = max(z_co) - min(z_co)

    # Calculate Top Face Area
    top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)
    top_area = top_face.calc_area()

    return [width, depth, height, top_area]
     
def perform_action(action):
    bm, me = get_current_bmesh()
    deselect_all()
    
    is_face_selected = any(f.select for f in bm.faces) # Check if any face is currently selected
    
    reward = 0
    
    if action == 0: # SELECT TOP FACE
        select_top_face(bm)
        
    elif action == 1: # SCALE
        if is_face_selected:
            Scale(0.8, 0.8, 1.0)
        else:
            reward -= 1.0 # Punish for trying to scale nothing
            
    elif action == 2: # EXTRUDE
        if is_face_selected:
            Extrude(z=0.5)
        else:
            reward -= 1.0 # Punish for trying to extrude nothing
        
    update(me)
    bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1) # Update Viewport
    

# *SERVER LOOP*

def run_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('localhost', 9999))
    server.listen(1) # queue up to 1 connection if socket/line is busy
    
    print("Blender Server Ready. Waiting for Client (the brain)...")
    client, addr = server.accept() # will wait till another program connects
    print(f"Connected: {addr}")
    
    try:
        while True:
            data = client.recv(4096).decode() # recieving up to 4096 bytes from client and then converting data from bytes to string
            if not data: break # quit if no data coming in
            
            request = json.loads(data) # converting data (in JSON string format) -> python data type (dictionary, list, array etc.)
            command = request["command"]
            
            # 2. Do the physical work
            response_data = []
            
            if command == "RESET":
                reset_scene()
                response_data = _get_obs()
                
            elif command == "STEP":
                perform_action(request["action"])
                response_data = _get_obs()
            
            # Send back raw data/observation only (Client will handle rewards)
            client.send(json.dumps(response_data).encode()) # converts python data type -> string -> bytes and sending it back to client
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client.close()
        server.close()

if __name__ == "__main__": # will run only when file is the main program (won't run when file is imported)
    run_server()