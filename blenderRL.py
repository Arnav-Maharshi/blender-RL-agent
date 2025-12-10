import bpy
import bmesh
import gymnasium as gym
from gymnasium import spaces
import numpy as np


def reset_scene():
    # Ensure in Object Mode before deleting (otherwise deletion can fail)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select and delete everything
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    add_cube()
    
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



    
class MyBlenderEnv(gym.Env):
    def __init__(self):
        super(MyBlenderEnv, self).__init__()

       
        self.action_space = spaces.Discrete(3) 

        
        self.observation_space = spaces.Box(
            low=-np.inf, 
            high=np.inf, 
            shape=(3,), # x,y,z coordinates
            dtype=np.float32
        )
        
        self.target_height = 4.0
        
    def _get_obs(self):
        bm, _ = get_current_bmesh()
        calibrate_bmesh(bm, "verts")

        if len(bm.verts) == 0:
            return np.array([0,0,0], dtype=np.float32)
        
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
        
        return np.array([width, depth, height, top_area], dtype=np.float32)
 
        
    def step(self, action):
        bm, me = get_current_bmesh()
        deselect_all()
        
        if action == 0:
            select_top_face()
        elif action == 1:
            Scale(2,2,2)
        elif action == 2:
            Extrude(z=0.5)
            
        update(bm)
        
        observation = _get_obs()
        curr_height = observation[2]
        
        distance = abs(self.target_height - curr_height)
        reward = -distance
        
        terminated = False
        if distance < 0.2:
            reward += 100 # BIG BONUS
            terminated = True
            print(f"SUCCESS! Reached Height {curr_height:.2f}")
        
        truncated = {}
        return observation, reward, terminated, truncated, {}
   
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # Reset Blender Scene
        reset_scene()

        # Return the initial look
        observation = self._get_obs()
        info = {}
        return observation, info
            
            
    
reset_scene()
add_cube()

bpy.ops.object.mode_set(mode='EDIT')

# Get the active mesh
obj = bpy.context.edit_object
me = obj.data


# Get a BMesh representartion
bm = bmesh.from_edit_mesh(me)
calibrate_bmesh(bm, "all")

bm.faces.active = None
bpy.ops.mesh.select_all(action='DESELECT') # deselect the faces in edit mode
vert = [v.co for v in bm.verts]
print(vert)

bm.faces[5].select = True

Extrude()


update(me)
vert = [v.co for v in bm.verts]
print(vert)
