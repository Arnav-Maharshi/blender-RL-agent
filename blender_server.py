import bpy
import bmesh
import socket
import json
import struct
from math import radians
from mathutils import Vector

def reset_scene():
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
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
        
def select_by_normal(bm, target_vector, angle_threshold=5):
    target_vector = Vector(target_vector)
    if target_vector.length < 0.001:
        print("Target vector is zero vector! ABORTING!")
        return
    
    angle_threshold = radians(angle_threshold) # converting value from degrees -> radians
    
    # Iterate through faces and select based on normal direction
    for f in bm.faces:
        if f.normal.length < 0.001: # skipping current iteration if the face has a zero normal vector
            continue                # (probably squashed the solid/invalid face)
        
        # calculate the angle between the face normal and the target vector
        angle = f.normal.angle(target_vector)

        # check if the angle is within the defined threshold
        if angle < angle_threshold:
            f.select = True
        
        # we can also use dot product method
        # if face.normal.dot(target_vector) > 0.9:
        #     f.select = True

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
    
    selected_faces = [f for f in bm.faces if f.select]

    if len(selected_faces) > 0:
        # If we have a selection, read its normal
        active_face = selected_faces[0]
        normal = list(active_face.normal)
        # normal.x, normal.y, normal.z
    else:
        # if nothing is selected, the normal is zero
        normal = [0.0, 0.0, 0.0]
        
        '''norm_x = [f.normal.x for f in bm.faces]
        norm_y = [f.normal.y for f in bm.faces]
        norm_z = [f.normal.z for f in bm.faces]'''

    return [width, depth, height, top_area] + normal # for flattened list    #norm_x, norm_y, norm_z]
     
def perform_action(action):
    bm, me = get_current_bmesh()
    #deselect_all()
    
    directions = [
    (-1,0,0), # left
    (1,0,0), # right
    (0,1,0), # front
    (0,-1,0), # back
    (0,0,1), # top
    (0,0,-1) # bottom
    ]
    
    is_face_selected = any(f.select for f in bm.faces)
    
    if action < 6: # SELECT FACE
        target_vector = directions[action]
        deselect_all()
        select_by_normal(bm, target_vector)
        
    elif action == 6: # SCALE DOWN
        if is_face_selected:
            Scale(0.5, 0.5, 0.5)
            
    elif action == 7: # SCALE UP
        if is_face_selected:
            Scale(1.5,1.5,1.5)
        
    elif action == 8: # EXTRUDE
        if is_face_selected:
            #Extrude(z=0.5)
            bpy.ops.transform.shrink_fatten(value=0.5)
            
        
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
    reset_scene()
    
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