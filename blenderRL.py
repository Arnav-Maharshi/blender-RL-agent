import bpy
import bmesh

def reset_scene():
    # Ensure in Object Mode before deleting (otherwise deletion can fail)
    bpy.ops.object.mode_set(mode='OBJECT')

    # Select and delete everything
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
def update(me):
    bmesh.update_edit_mesh(me) # Update the BMesh

def add_cube(loc=(0,0,0), size=1):
    bpy.ops.mesh.primitive_cube_add(location=loc, size=size)
    obj = bpy.context.active_object
    print(f'Added cube:- {obj.name}')
    return obj

def calibrate_bmesh(bm): # ?? maybe we don't need an input argument??
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

def select_type(t):
    bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type=f'{t}')
    
def select_top_face(bm):   # ?? maybe we don't need an input argument??
    top_faces = [f for f in bm.faces if f.normal.z > 0.9]
    for f in top_faces:
        #bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
        f.select = True

def extrude(x=0,y=0,z=1): # Extrude the selected region along its normals
    # The 'TRANSFORM_OT_translate' operator is used to define the movement after extrusion
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value":(x, y, z)} # Extrude 1 unit along the Z-axis
    )

    
reset_scene()
add_cube()

select_type('FACE')
# Get the active mesh
obj = bpy.context.edit_object
me = obj.data


# Get a BMesh representartion
bm = bmesh.from_edit_mesh(me)
calibrate_bmesh(bm)

bm.faces.active = None
bpy.ops.mesh.select_all(action='DESELECT') # deselect the faces in edit mode

bm.faces[5].select = True

bpy.ops.mesh.select_mode(use_extend=False, use_expand=False, type='FACE')
extrude()

update(me)

