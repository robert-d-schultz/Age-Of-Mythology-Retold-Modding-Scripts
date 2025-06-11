#!/usr/bin/env python3
import struct
import os
import bpy
import math
from mathutils import Matrix, Vector
import numpy as np

os.system("cls")


#TODO:
#Building attachments no worky
#And look into attachments scaling and stuff by the main_matrix
#And... normals don't import (use Blender's autosmooth instead)


#This script expects a .tmm.data file in the same directory
tmm_filename = "/path/to/tmm_file.tmm"


with open(tmm_filename, "rb") as tmm_file:    
    #Header
    BTMM = struct.unpack("<L", tmm_file.read(4))[0]
    assert BTMM == 1296913474, BTMM
    version = struct.unpack("<L", tmm_file.read(4))[0]
    assert version == 35, version
    DP  = struct.unpack("<H", tmm_file.read(2))[0]
    assert DP == 20548, DP



    #"import crap", which I assume isn't used in-game
    tmm_file.read(4) #byte length
    num_import_crap = struct.unpack("<L", tmm_file.read(4))[0]
    for _ in range(num_import_crap):
        import_crap_name_length = struct.unpack("<L", tmm_file.read(4))[0] * 2
        import_crap_name = tmm_file.read(import_crap_name_length).decode('UTF-16-LE')
        tmm_file.read(16) #unknown
    
    
    
    #Bounding box(s)
    bounding_box = struct.unpack("<ffffff", tmm_file.read(24)) #just in bind pose?
    bigger_bounding_box = struct.unpack("<ffffff", tmm_file.read(24)) #maximum range from anims?
    
    
    
    unknown_float = struct.unpack("<f", tmm_file.read(4))[0] #HP bar height or something? seems a bit low
    
    
    
    #Counts of things
    num_mesh_groups = struct.unpack("<L", tmm_file.read(4))[0]
    num_materials = struct.unpack("<L", tmm_file.read(4))[0]
    num_defaults = struct.unpack("<L", tmm_file.read(4))[0] #"default"s, probably shader techniques
    num_bones = struct.unpack("<L", tmm_file.read(4))[0]
    num_unknown2 = struct.unpack("<L", tmm_file.read(4))[0] #unknown, always 0?
    assert num_unknown2 == 0, num_unknown2
    num_attachments = struct.unpack("<L", tmm_file.read(4))[0]
    num_vertices = struct.unpack("<L", tmm_file.read(4))[0]
    num_triangle_verts = struct.unpack("<L", tmm_file.read(4))[0]
    num_triangles = int(num_triangle_verts / 3) #divide by 3 to get # of triangles
    assert (num_triangles * 3 == num_triangle_verts)
    
    
    #Byte addresses and byte lengths of the different blocks (for the .tmm.data file)
    
    #vertices block
    vertices_start = struct.unpack("<L", tmm_file.read(4))[0]
    vertices_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    #triangles block
    triangles_start = struct.unpack("<L", tmm_file.read(4))[0]
    triangles_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    #weights block
    weights_start = struct.unpack("<L", tmm_file.read(4))[0]
    weights_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    #block type unseen?
    unknown1_block_start = struct.unpack("<L", tmm_file.read(4))[0]
    assert unknown1_block_start == 0, unknown1_block_start
    unknown1_block_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    #block type unseen?
    unknown2_block_start = struct.unpack("<L", tmm_file.read(4))[0]
    assert unknown2_block_start == 0, unknown2_block_start
    unknown2_block_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    #height block
    heights_start = struct.unpack("<L", tmm_file.read(4))[0]
    heights_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    #one last block type unseen?
    unknown3_block_start = struct.unpack("<L", tmm_file.read(4))[0]
    assert unknown3_block_start == 0, unknown3_block_start 
    unknown3_block_bytelength = struct.unpack("<L", tmm_file.read(4))[0]
    
    
    
    unknown_bools = struct.unpack("<BB", tmm_file.read(2)) #unknown, bools?
    assert unknown_bools == (0,1), unknown_bools
    
    
    
    #"main" 4x3 matrix
    #some meshes are stored at different scales than their animations
    #so this matrix is applied to animations to make them match the model
    #alternatively, you could think of the mesh's data having this "baked-in"
    #(this stuff has nothing to do with in-game scale modification)
    main_matrix = struct.unpack("<ffffffffffff", tmm_file.read(48)) #4x3 matrix
    main_matrix = Matrix(np.array(list(main_matrix)+[0,0,0,1]).reshape(4, 4))
    #row-ordered, doesn't need to be transposed
    #print(main_matrix)
    
    main_matrix_inverted = main_matrix.inverted()
    #print(main_matrix_inverted)


        
    #Attachments
    attachments = []
    for _ in range(num_attachments):
        unknown_int = struct.unpack("<L", tmm_file.read(4))[0] #unknown
        assert unknown_int == 0, unknown_int
        
        parent_bone_id = struct.unpack("<l", tmm_file.read(4))[0]
        
        attachment_length = struct.unpack("<L", tmm_file.read(4))[0] * 2
        attachment_name = tmm_file.read(attachment_length).decode('UTF-16-LE')
        
        #Probably parent space and then world space
        transform_matrix1 = struct.unpack("<ffffffffffff", tmm_file.read(48)) #4x3 matrix
        transform_matrix2 = struct.unpack("<ffffffffffff", tmm_file.read(48)) #4x3 matrix
        
        unknown_zero1 = struct.unpack("<L", tmm_file.read(4))[0] #unknown, always 0, sometimes 2 for relics/riders?
        assert unknown_zero1 == 0 or unknown_zero1 == 2, unknown_zero1
        unknown_zero2 = struct.unpack("<L", tmm_file.read(4))[0] #unknown, always 0?
        assert unknown_zero2 == 0, unknown_zero2
        
        #unknown, second string?
        second_length = struct.unpack("<L", tmm_file.read(4))[0] * 2
        second_name = tmm_file.read(second_length).decode('UTF-16-LE')
        
        unknown_ints = struct.unpack("<llll", tmm_file.read(16)) #unknown, quaternion?
        assert unknown_ints == (-1,0,0,0), unknown_ints
        
        attachments.append((attachment_name, parent_bone_id, transform_matrix1))
        

    
    #Mesh Groups
    mesh_group_list = []
    for _ in range(num_mesh_groups):
        verts_start = struct.unpack("<L", tmm_file.read(4))[0]
        tris_start = struct.unpack("<L", tmm_file.read(4))[0]
        num_verts = struct.unpack("<L", tmm_file.read(4))[0]
        num_tri_verts = struct.unpack("<L", tmm_file.read(4))[0]
        num_tris = int(num_tri_verts / 3) #divide by 3 to get the triangles
        mat_index = struct.unpack("<L", tmm_file.read(4))[0]
        defaut_index = struct.unpack("<L", tmm_file.read(4))[0] #shader technique from below?
        
        mesh_group_list.append((num_verts,num_tris,mat_index))
        
        
    #Materials
    material_list = []
    for _ in range(num_materials):
        material_length = struct.unpack("<L", tmm_file.read(4))[0] * 2
        material_name = tmm_file.read(material_length).decode('UTF-16-LE')
        material_list.append(material_name)



    #Shader Techniques or something? (it's usually just "default")
    for _ in range(num_defaults):
        default_length = struct.unpack("<L", tmm_file.read(4))[0] * 2
        default_name = tmm_file.read(default_length).decode('UTF-16-LE')
    
    
    
    #Bones, bind pose skeleton
    #It's actually a subset of the full skeleton, leaving-off unused bones (typically finger bones?)
    bone_list = []
    for _ in range(num_bones):
        bone_length = struct.unpack("<L", tmm_file.read(4))[0] * 2
        bone_name = tmm_file.read(bone_length).decode('UTF-16-LE')
        bone_parent_id = struct.unpack("<l", tmm_file.read(4))[0]
        
        quaternion = struct.unpack("<fff", tmm_file.read(12))[0] #unknown
        radius = struct.unpack("<f", tmm_file.read(4))[0] #radius for collision (needed for clicking on the unit)
        
        #4x4 matrices
        parent_space_matrix = struct.unpack("<ffffffffffffffff", tmm_file.read(64))
        world_space_matrix = struct.unpack("<ffffffffffffffff", tmm_file.read(64))
        inverse_bind_matrix = struct.unpack("<ffffffffffffffff", tmm_file.read(64))
        
        bone_list.append((bone_name, bone_parent_id, world_space_matrix, radius))

    
    
    #The stuff at the end is very weird and probably not that relevent, skipping
    
    #End of .tmm file
    



def setup_armature(tmm_data_filename, bone_list):
    print("Setting up armature")
    try:
        anim_collection = bpy.data.collections["imported"]
    except KeyError:
        anim_collection = bpy.data.collections.new("imported")
        bpy.context.scene.collection.children.link(anim_collection)
        
    if (len(bone_list) == 0):
        return False;

    arm_name = os.path.splitext(os.path.basename(tmm_data_filename))[0] + "_armature"

    #Set up armature
    armature = bpy.data.armatures.new(arm_name)
    armature_object = bpy.data.objects.new(arm_name, armature)
    anim_collection.objects.link(armature_object)
    bpy.context.view_layer.objects.active = armature_object
    
    #Correct for the coordinate handedness and y/z axes (I hope this doesn't cause trouble)
    armature_object.rotation_euler = (-math.pi/2,0,0)
    armature_object.scale = (1, -1, 1)
    
    #Thing because of animation/model scale msmatch and stuff
    armature_object.matrix_basis = armature_object.matrix_basis @ main_matrix
    
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    for i, bone in enumerate(bone_list):
        bone_name, parent_index, world_space_mat, radius = bone
        print(f"  Bone: {bone_name}")
        
        world_space_mat = Matrix(np.array(world_space_mat).reshape(4, 4))
        world_space_mat.transpose()
        
        ebs = armature.edit_bones
        try:
            eb = ebs[bone_name]
        except KeyError:
            print(f"    Not in the armature, adding")
            eb = ebs.new(bone_name)
            
        eb.head_radius = radius
        eb.tail_radius = radius
        eb.tail = (0.0, 0.2, 0.0)
        
        if parent_index >= 0:
            eb.parent = armature.edit_bones[parent_index]
        else:
            pass
        
        eb.matrix = main_matrix_inverted @ world_space_mat
        
    bpy.ops.object.mode_set(mode='OBJECT')
    
    return armature_object



def oct_decode(x, y):
    x = x*2 - 1
    y = y*2 - 1
    z = 1.0 - abs(x) - abs(y)
    if z < 0.0:
        # Fold the lower hemisphere
        x_new = (1.0 - abs(y)) * np.sign(x)
        y_new = (1.0 - abs(x)) * np.sign(y)
        x, y, z = x_new, y_new, -z

    # Normalize to unit vector
    normal = np.array([x, y, z])
    return normal / np.linalg.norm(normal)



def read_tmm_data(tmm_data_filename, num_vertices, num_triangles, mesh_group_list, armature_object):
    with open(tmm_data_filename + ".data", "rb") as tmm_data_file:
        print("Reading " + os.path.basename(tmm_data_filename) + ".data")
        
        #Vertices
        print(str(num_vertices) + " Vertices")
        vertex_list = []
        uv_list = []
        norm_list = []
        norm_raw_list = []
        for i, mesh_group in enumerate(mesh_group_list):
            print(f"Mesh group {i}, {mesh_group[0]} vertices")
            for j in range(mesh_group[0]):
                x, y, z, u, v  = struct.unpack("<eeeee", tmm_data_file.read(10))
                vertex_list.append((x, z, y))
                uv_list.append((u, 1-v))



                #Normals are NOT SOLVED AAAAAAAAHHHHHHHHHH!!!!!
                
                def invert_15_bits(raw):
                    # Convert to 16-bit int
                    val = int.from_bytes(raw, byteorder='little')
                    # Preserve bit 15 (0x8000), invert the rest
                    val = (val & 0x8000) | (~val & 0x7FFF)
                    return val.to_bytes(2, byteorder='little')
                
                n_raw = tmm_data_file.read(2)
                if (n_raw[1] & 0x40) != 0:
                    n_raw = invert_15_bits(n_raw)

                t_raw = tmm_data_file.read(2)
                if (t_raw[1] & 0x40) != 0:
                    t_raw = invert_15_bits(t_raw)

                b_raw = tmm_data_file.read(2)
                if (b_raw[1] & 0x40) != 0:
                    b_raw = invert_15_bits(b_raw)

                norm_raw_list.append(n_raw + t_raw + b_raw)
                                
                
                norm_raw = struct.unpack("H", n_raw)[0]
                tan_raw = struct.unpack("H", t_raw)[0]
                bitan_raw = struct.unpack("H", b_raw)[0]

                def unpack_and_normalize(value):
                    # 7 bits for first, 7 bits for second, 2 bits for the remainder
                    a = value & 0x7F             # bits 0–6
                    b = (value >> 7) & 0x7F      # bits 7–13
                    c = (value >> 14) & 0x03   # bits 14–15 (ignored)
                    return a / 127.0, b / 127.0, c
                
                norm_a, norm_b, norm_c = unpack_and_normalize(norm_raw)
                tan_a, tan_b, tan_c = unpack_and_normalize(tan_raw)
                bitan_a, bitan_b, bitan_c = unpack_and_normalize(bitan_raw)                
                
                (norm_x, norm_y, norm_z) = oct_decode(norm_a, norm_b) * (1 if norm_c == 0 else -1)
                (tan_x, tan_y, tan_z) = oct_decode(tan_a, tan_b) * (1 if tan_c == 0 else -1)
                (bitan_x, bitan_y, bitan_z) = oct_decode(bitan_a, bitan_b) * (1 if bitan_c == 0 else -1)
                
                #Junk normals for now
                norm_list.append((0, 0, 0))

        
        
        
        
        
        #Triangles
        print(str(num_triangles) + " Triangles")
        triangle_list = []
        vert_index_offset = 0
        for j, mesh_group in enumerate(mesh_group_list):
            print(f"Mesh group {i}, {mesh_group[1]} triangles")
            for _ in range(mesh_group[1]):
                a, b, c = struct.unpack("<HHH", tmm_data_file.read(6))
                offset_indices = (a + vert_index_offset, b + vert_index_offset, c + vert_index_offset)
                tri_vert_indices = (offset_indices[0], offset_indices[2], offset_indices[1])
                triangle_list.append(tri_vert_indices)
            
            vert_index_offset += mesh_group[0]
        
        
        
        #Bone weights
        weighted_bone_data = []
        if not (armature_object == False):
            for vertex in range(num_vertices):
                weights = struct.unpack("<BBBB", tmm_data_file.read(4))
                bone_ids = struct.unpack("<BBBB", tmm_data_file.read(4))
                weighted_bones = [(bone_id, weight) for bone_id, weight in zip(bone_ids, weights) if weight != 0]
                weighted_bone_data.append(weighted_bones)
            
        #Vertex heights, skip
        #for vertex in range(num_vertices):
            #height = struct.unpack("<H", file.read(2))
            
        
        #Finish up
        print("Setting up mesh")
        model_name = os.path.splitext(os.path.basename(tmm_data_filename))[0]
        current_mesh = bpy.data.meshes.new(model_name)
        current_mesh.from_pydata(vertex_list, [], triangle_list)
        current_mesh.update()
                        
        #UV
        current_mesh.uv_layers.new()
        current_mesh.uv_layers[-1].data.foreach_set("uv", [uv for pair in [uv_list[l.vertex_index] for l in current_mesh.loops] for uv in pair])
        
        #Vertex normals
        current_mesh.normals_split_custom_set_from_vertices(norm_list)
        current_mesh.calc_tangents()
        
        #Object and put in collection
        try:
            collection = bpy.data.collections["imported"]
        except KeyError:
            collection = bpy.data.collections.new("imported")
            bpy.context.scene.collection.children.link(anim_collection)
        current_object = bpy.data.objects.new(model_name, current_mesh)
        collection.objects.link(current_object)
        
        #Armature/Rigging
        if not (armature_object == False):
            print("Rigging to " + armature_object.name)
            for v_idx, bone_weights in enumerate(weighted_bone_data):
                for bone_id, weight in bone_weights:
                    bone_name = armature_object.data.bones[bone_id].name
                    # Create vertex group if it doesn't exist
                    if bone_name not in current_object.vertex_groups:
                        current_object.vertex_groups.new(name=bone_name)
                    group = current_object.vertex_groups[bone_name]
                    group.add([v_idx], weight / 255.0, 'ADD')

            # Add armature modifier
            mod = current_object.modifiers.new(type='ARMATURE', name="Armature")
            mod.object = armature_object
            
    return current_object
    
    
def assign_materials(mesh_object, mesh_group_list, material_list):
    current_mesh = mesh_object.data
    
    for mat_name in material_list:
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
        mesh_object.data.materials.append(mat)
    
    tri_index = 0
    for (_, tri_count, mat_index) in mesh_group_list:
        for _ in range(tri_count):
            if tri_index < len(current_mesh.polygons):
                current_mesh.polygons[tri_index].material_index = mat_index
                tri_index += 1
    
    return True
    
    


#Now to actually make the things

#Make Armature
armature_obj = setup_armature(tmm_filename, bone_list)

#Read and make the mesh
mesh_obj = read_tmm_data(tmm_filename, num_vertices, num_triangles, mesh_group_list, armature_obj)

#Assign materials
assign_materials(mesh_obj, mesh_group_list, material_list)

#Attachments
print("Attachments:")
for attachment in attachments:
    print(f"  Attachment: {attachment[0]}")
    empty = bpy.data.objects.new(attachment[0], None)
    bpy.data.collections["imported"].objects.link(empty)
    
    if armature_obj:
        empty.parent = armature_obj
        if (attachment[1] >= 0):
            empty.parent_type = 'BONE'
            empty.parent_bone = armature_obj.data.bones[attachment[1]].name
    
    else:
        #building attachments... hmmm
        pass
    empty.empty_display_size = 0.25
    
    #I think this can be left as-is, no need to worry about the "main matrix"
    world_space_mat = Matrix(np.array(list(attachment[2])+[0,0,0,1]).reshape(4, 4))
    #print(world_space_mat)
    
    empty.matrix_local = world_space_mat
    