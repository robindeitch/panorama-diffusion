import os

# Panel basics : https://www.youtube.com/watch?v=0_QskeU8CPo

bl_info = {
    "name": "Panorama diffusion",
    "description": "Use Stable Diffusion to generate textures based on scene depth and project back to geo",
    "blender": (4, 1, 0),
    "category": "3D View",
    "location": "View3D > Sidebar > Pano tab",
}

from random import randint
import bpy
import os
from .sdxl_client import SDXLClient

class LoRAInfo(bpy.types.PropertyGroup):
    bl_label = "LoRA info"
    bl_idname = "panorama_diffusion.lorainfo"

    enabled: bpy.props.BoolProperty(name="x", default=True)
    model_file: bpy.props.StringProperty(subtype="FILE_PATH", name="Model file")
    keywords: bpy.props.StringProperty(name="Keywords")
    weight: bpy.props.FloatProperty(name="Weight")

sdxl = SDXLClient()

def clean_path(file:str) -> str:
    return os.path.normpath(bpy.path.abspath(file))

class InitDiffusionPanoramaOp(bpy.types.Operator):
    bl_idname = "panorama_diffusion.init"
    bl_label = "panorama_diffusion.init"

    def execute(self, context):
        model_file = context.scene.pd_model_file
        print(f"Loading model {model_file}")

        valid_loras = [lora for lora in context.scene.pd_loras if lora.enabled and os.path.exists(clean_path(lora.model_file))]
        loras = [(clean_path(lora.model_file), lora.keywords) for lora in valid_loras ]
        lora_weights = [lora.weight for lora in valid_loras]

        if len(loras) > 0:
            sdxl.init(model_file, loras, lora_weights)
        else:
            sdxl.init(model_file)

        return {"FINISHED"}

class LoraList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        _, tail = os.path.split(clean_path(item.model_file))
        label = f"({round(item.weight, 2)}) {tail}"
        layout.prop(item, "enabled", text='')
        layout.label(text = label)

class LoraAddOp(bpy.types.Operator):
    bl_idname = "panorama_diffusion.lora_add"
    bl_label = "Add"
    
    def execute(self, context):
        s = context.scene
        item = s.pd_loras.add()
        #item.name = ...
        return {'FINISHED'}

class LoraRemoveOp(bpy.types.Operator):
    bl_idname = "panorama_diffusion.lora_remove"
    bl_label = "Remove"
    
    @classmethod
    def poll(cls, context):
        s = context.scene
        return len(s.pd_loras) > s.pd_loras_index >= 0
    
    def execute(self, context):
        s = context.scene
        s.pd_loras.remove(s.pd_loras_index)
        if s.pd_loras_index > 0:
            s.pd_loras_index -= 1
        return {'FINISHED'}

class RenderDiffusionPanoramaOp(bpy.types.Operator):
    bl_idname = "panorama_diffusion.render"
    bl_label = "panorama_diffusion.render"

    def execute(self, context):

        # Setup prompt
        output_image_file = clean_path(context.scene.pd_output_texture_file)
        prompt = context.scene.pd_prompt.as_string()
        negative_prompt = context.scene.pd_prompt_neg.as_string()
        seed = context.scene.pd_seed
        steps = 15
        prompt_guidance=7.5
        depth_image_influence = context.scene.pd_depth_image_influence
        lora_overall_influence = 1.0
        depth_image_file = clean_path(context.scene.pd_depth_texture_file)

        # Render from the correct camera
        temp_cam = context.scene.camera
        context.scene.camera = context.scene.pd_render_cam
        bpy.ops.render.render(write_still = True)
        context.scene.camera = temp_cam

        # Reload depth map
        for img in bpy.data.images :
            this_image_file = clean_path(img.filepath)
            if img.source == 'FILE' and this_image_file == depth_image_file:
                img.reload()

        # Define callback
        def callback(id:int, result_image_file:str):
            
            result_image_file = clean_path(result_image_file)
            print(f"Finished generating id {id} at {result_image_file}, reloading")

            for img in bpy.data.images :
                this_image_file = clean_path(img.filepath)
                if img.source == 'FILE' and (this_image_file == result_image_file or this_image_file == depth_image_file):
                    img.reload()

        # Queue prompt
        id = sdxl.queue_panorama(
            output_image_file,
            callback,
            prompt,
            negative_prompt,
            seed,
            steps,
            prompt_guidance,
            depth_image_file,
            depth_image_influence,
            lora_overall_influence
        )
        print(f"Generating id {id}")
        
        return {"FINISHED"}


class PanoramaDiffusionPanel(bpy.types.Panel):
    bl_idname = "VIEW3D_PT_panorama_diffusion"
    bl_label = "Panorama Diffusion"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Pano'

    @classmethod
    def poll(cls, context):
        return (context.object is not None)

    def draw(self, context):
        layout = self.layout

        # Model
        layout.prop(context.scene, "pd_model_file")

        # LoRAs
        lora_row = layout.split(factor=0.175)
        label_col = lora_row.column()
        label_col.label(text="LoRAs:")
        lora_settings_col = lora_row.column()
        lora_settings_col.template_list("LoraList", "", context.scene, "pd_loras", context.scene, "pd_loras_index")

        if context.scene.pd_loras_index > -1 and len(context.scene.pd_loras) > 0:
            lora = context.scene.pd_loras[context.scene.pd_loras_index]
            box = lora_settings_col.box()
            box.row().prop(lora, "weight" )
            box.row().prop(lora, "model_file" )
            box.row().prop(lora, "keywords" )

        row = lora_settings_col.split()
        col1 = row.column()
        col2 = row.column()
        col1.operator(LoraAddOp.bl_idname, text="Add", icon="ADD")
        col2.operator(LoraRemoveOp.bl_idname, text="Remove", icon="REMOVE")

        layout.operator("panorama_diffusion.init", text="Load models", icon="LIBRARY_DATA_DIRECT")

        layout.prop(context.scene, "pd_prompt")
        layout.prop(context.scene, "pd_prompt_neg")
        layout.prop(context.scene, "pd_depth_texture_file")
        layout.prop(context.scene, "pd_output_texture_file")
        layout.prop(context.scene, "pd_render_cam")
        layout.prop(context.scene, "pd_seed")
        layout.prop(context.scene, "pd_depth_image_influence")
        layout.operator("panorama_diffusion.render", text="Render", icon="RENDER_RESULT")

# https://docs.blender.org/api/current/bpy.props.html
# https://wilkinson.graphics/blender-icons/

def register():

    bpy.utils.register_class(LoraAddOp)
    bpy.utils.register_class(LoraRemoveOp)
    bpy.utils.register_class(RenderDiffusionPanoramaOp)
    bpy.utils.register_class(InitDiffusionPanoramaOp)
    bpy.utils.register_class(PanoramaDiffusionPanel)
    bpy.utils.register_class(LoRAInfo)
    bpy.utils.register_class(LoraList)

    sdxl.start()
    bpy.types.Scene.pd_seed = bpy.props.IntProperty(name="Seed")
    bpy.types.Scene.pd_prompt = bpy.props.PointerProperty(type=bpy.types.Text, name="Prompt")
    bpy.types.Scene.pd_prompt_neg = bpy.props.PointerProperty(type=bpy.types.Text, name="Neg Prompt")
    bpy.types.Scene.pd_model_file = bpy.props.StringProperty(subtype="FILE_PATH", name="Model file")
    bpy.types.Scene.pd_depth_texture_file  = bpy.props.StringProperty(subtype="FILE_PATH", name="Depth texture file")
    bpy.types.Scene.pd_depth_image_influence = bpy.props.FloatProperty(name="Depth Influence")
    bpy.types.Scene.pd_output_texture_file  = bpy.props.StringProperty(subtype="FILE_PATH", name="Output texture file")
    bpy.types.Scene.pd_render_cam = bpy.props.PointerProperty(type=bpy.types.Object, name="Render cam")
    bpy.types.Scene.pd_loras = bpy.props.CollectionProperty(type=LoRAInfo, name="LoRAs")
    bpy.types.Scene.pd_loras_index = bpy.props.IntProperty(name="LoRAs Index")

def unregister():
    sdxl.stop()
    bpy.utils.unregister_class(LoraList)
    bpy.utils.unregister_class(LoRAInfo)
    bpy.utils.unregister_class(PanoramaDiffusionPanel)
    bpy.utils.unregister_class(InitDiffusionPanoramaOp)
    bpy.utils.unregister_class(RenderDiffusionPanoramaOp)
    bpy.utils.unregister_class(LoraAddOp)
    bpy.utils.unregister_class(LoraRemoveOp)
